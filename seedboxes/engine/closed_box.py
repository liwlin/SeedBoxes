"""Restricted ClosedBox adapter: explicit topology, real upstream paths."""
import math

from seedboxes.domain.models import CapturedModel, CapturedPanel, PanelGeometry, Project
from seedboxes.domain.serialization import normalize_project, to_json
from .bridge import engine_fingerprint, serialized_render
from .capture import CapturingClosedBox
from .paths import capture_path

ROLES = {'front':'Wall 1','back':'Wall 3','left':'Wall 4','right':'Wall 2','top':'Top','bottom':'Bottom'}
EDGE_NAMES = ('bottom','right','top','left')
MATES = {
 'front': (('bottom','top'),('right','left'),('top','bottom'),('left','right')),
 'back': (('bottom','bottom'),('left','left'),('top','top'),('right','right')),
 'left': (('bottom','left'),('front','left'),('top','left'),('back','right')),
 'right': (('bottom','right'),('back','left'),('top','right'),('front','right')),
 'top': (('front','top'),('right','top'),('back','top'),('left','top')),
 'bottom': (('back','bottom'),('right','bottom'),('front','bottom'),('left','bottom')),
}


def assembly_frame(role, width, depth, height):
    frames = {
      'front': ((-width/2,0,depth/2),(1,0,0),(0,1,0),(0,0,1)),
      'back': ((width/2,0,-depth/2),(-1,0,0),(0,1,0),(0,0,-1)),
      'left': ((-width/2,0,-depth/2),(0,0,1),(0,1,0),(-1,0,0)),
      'right': ((width/2,0,depth/2),(0,0,-1),(0,1,0),(1,0,0)),
      'top': ((-width/2,height,depth/2),(1,0,0),(0,0,-1),(0,1,0)),
      'bottom': ((-width/2,0,-depth/2),(1,0,0),(0,0,1),(0,-1,0)),
    }
    origin,u,v,n = frames[role]
    return (*u,0.,*v,0.,*n,0.,*origin,1.)


def _number(value, name, low, high):
    if type(value) not in (int,float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{name} 必须为 {low}–{high} 范围内的有限数值')
    return float(value)


def parameters_for(project: Project, mode: str) -> dict:
    p = project.parameters
    allowed = {'x','y','h','outside','thickness','reference','labels','qr_code','inner_corners'}
    if set(p)-allowed:
        raise ValueError('增强模式未支持参数：' + ', '.join(sorted(set(p)-allowed)))
    required = {'x','y','h','outside','thickness'}
    if not required <= set(p):
        raise ValueError('缺少必需尺寸参数')
    result={k:_number(p[k],k,20,1000) for k in ('x','y','h')}
    result['thickness']=_number(p['thickness'],'thickness',.5,20)
    if type(p['outside']) is not bool:
        raise ValueError('outside 必须为布尔值')
    result['outside']=p['outside']
    if p.get('inner_corners','corner') != 'corner':
        raise ValueError('首批增强模式仅支持 inner_corners=corner')
    comp=project.profileSnapshot['compensation']
    if comp['jointClearanceMm'] != 0:
        raise ValueError('首批暂不支持额外装配间隙')
    result['burn']=0. if mode=='nominal' else comp['boxesBurnMm']
    result.update(format='svg',reference=0,labels=False,qr_code=False,inner_corners='corner')
    t=result['thickness']
    inner={k:result[k]-(2*t if result['outside'] else 0) for k in ('x','y','h')}
    # Fail closed for dimensions too small to exercise the validated full finger pattern.
    if min(inner.values()) < 4*t:
        raise ValueError('首批要求内腔各尺寸不小于 4 倍板厚')
    return result


class ClosedBoxAdapter:
    adapter_id = 'closed-box'
    version = '1.0.0'

    @serialized_render
    def generate(self, project: Project, mode: str) -> CapturedModel:
        project=normalize_project(to_json(project))
        if mode not in ('nominal','toolpath'):
            raise ValueError('未知几何模式')
        fp=dict(engine_fingerprint())
        if project.generatorId!='ClosedBox' or project.adapter != {'id':self.adapter_id,'version':self.version}:
            raise ValueError('未支持的生成器或适配器版本')
        if project.engine != {k:fp[k] for k in ('name','version','commit')}:
            raise ValueError('工程引擎版本不匹配；请显式迁移工程')
        params=parameters_for(project,mode)
        box=CapturingClosedBox()
        for feature in project.features:
            if not feature['enabled']:
                continue
            if feature['rotationDeg'] != 0:
                raise ValueError('首批开孔仅支持零旋转')
            sizes = feature['parameters'].values()
            burn = project.profileSnapshot['compensation']['boxesBurnMm']
            if any(size <= 2*burn for size in sizes):
                raise ValueError('开孔尺寸必须大于两倍 burn 补偿')
            box.panel_features.setdefault(ROLES[feature['panelId']], []).append(feature)
        def fail(message): raise ValueError('参数无效：'+message)
        box.argparser.error=fail
        args=[]
        for k,v in params.items():
            args.extend(['--'+k,str(int(v)) if type(v) is bool else str(v)])
        try:
            box.parseArgs(args)
            box.metadata.update(url='',url_short='')
            box.open();box.render()
            if len(box.captured_walls)!=6:
                raise ValueError('ClosedBox 板件数量不是六片')
            walls={w['role']:w for w in box.captured_walls}
            if set(walls)!=set(ROLES.values()):
                raise ValueError('ClosedBox 源板件角色变化')
            width=walls['Wall 1']['width'];depth=walls['Wall 2']['width'];height=walls['Wall 1']['height']
            panels=[]
            for i,(role,source) in enumerate(ROLES.items()):
                wall=walls[source]
                tagged = list(zip(wall['paths'], wall['featureIds']))
                outlines = [path for path, feature_id in tagged if feature_id is None]
                if len(outlines) != 1:
                    raise ValueError('未预期的基础板件路径数')
                outer=capture_path(outlines[0],wall['canvasToLocal'],role+':outer','cut_outer',box.inner_corners)
                holes=tuple(capture_path(path,wall['canvasToLocal'],role+':feature:'+feature_id,
                                         'cut_inner',box.inner_corners)
                            for path,feature_id in tagged if feature_id is not None)
                joints=[]
                for edge,(mate,mate_edge),kind in zip(EDGE_NAMES,MATES[role],wall['edges']):
                    joint_id='|'.join(sorted((role+':'+edge,mate+':'+mate_edge)))
                    joints.append({'jointId':joint_id,'panelId':role,'edgeId':edge,
                                   'matePanelId':mate,'mateEdgeId':mate_edge,
                                   'type':'tab' if kind=='f' else 'slot', 'sourceEdgeType':kind,
                                   'intervals':None,'nominalClearanceMm':0.})
                panels.append(CapturedPanel(role,chr(65+i),source,box.thickness,wall['width'],wall['height'],
                    PanelGeometry(outer,holes),tuple(wall['canvasToLocal'])[:6],wall['edges'],
                    assembly_frame(role,width,depth,height),tuple(joints)))
            return CapturedModel(mode,project.projectId,project.revision,tuple(panels),fp,
                                 {'widthMm':width,'depthMm':depth,'heightMm':height},
                                 ({'code':'FOUNDATION_ONLY','messageZh':'尚未执行制造体检或装配路径验证；接合区间尚未提取。'},))
        finally:
            # No export is needed for capture. Drop per-instance drawing state even after failure.
            box.ctx=None
            box.surface=None
