import importlib
import json
from pathlib import Path

import pytest

from seedboxes.domain.serialization import normalize_project

ROOT = Path(__file__).resolve().parents[1]


def adapter():
    try:
        return importlib.import_module('seedboxes.engine.closed_box').ClosedBoxAdapter()
    except ImportError:
        pytest.fail('ClosedBox capture adapter has not been implemented')


def data():
    return json.loads((ROOT / 'tests/fixtures/project.json').read_text())


def bounds(path):
    coords = [c[1:3] for c in path.commands if c[0] in ('M', 'L')]
    return (min(x for x,y in coords), min(y for x,y in coords), max(x for x,y in coords), max(y for x,y in coords))


def test_six_stable_panel_ids():
    result = adapter().generate(normalize_project(data()), 'nominal')
    assert [p.panelId for p in result.panels] == ['front','back','left','right','top','bottom']
    assert [p.displayCode for p in result.panels] == list('ABCDEF')
    assert result.innerDimensions == {'widthMm':120, 'depthMm':80, 'heightMm':60}
    for panel in result.panels:
        assert panel.geometry.outer.closed
        assert panel.geometry.outer.operation == 'cut_outer'
        assert bounds(panel.geometry.outer) == pytest.approx((-3,-3,panel.widthMm+3,panel.heightMm+3))


def test_resize_preserves_roles():
    a=adapter(); d=data()
    first=a.generate(normalize_project(d),'nominal')
    d['parameters'].update(x=200,y=150,h=100,thickness=5)
    second=a.generate(normalize_project(d),'nominal')
    assert [(p.panelId,p.sourceRole) for p in first.panels] == [(p.panelId,p.sourceRole) for p in second.panels]
    assert second.panels[0].widthMm == 200
    assert second.panels[0].heightMm == 100


def test_reference_and_labels_not_panels():
    a=adapter(); d=data()
    expected=a.generate(normalize_project(d),'nominal')
    d['parameters'].update(reference=100,labels=True,qr_code=True)
    actual=a.generate(normalize_project(d),'nominal')
    assert [p.geometry for p in actual.panels] == [p.geometry for p in expected.panels]


def test_capture_does_not_patch_global_class():
    from boxes import Boxes
    from boxes.generators.closedbox import ClosedBox
    methods = (Boxes.rectangularWall,Boxes.cc,ClosedBox.render)
    adapter().generate(normalize_project(data()),'nominal')
    assert methods == (Boxes.rectangularWall,Boxes.cc,ClosedBox.render)


def test_nominal_outline_matches_upstream_canvas():
    from boxes.generators.closedbox import ClosedBox
    from affine import Affine
    a=adapter(); d=data(); result=a.generate(normalize_project(d),'nominal')
    b=ClosedBox(); b.parseArgs(['--x','120','--y','80','--h','60','--outside','0','--thickness','3','--burn','0', '--reference','0','--labels','0','--inner_corners','corner'])
    b.open();b.render()
    # Source wall order is explicit in the pinned ClosedBox generator, not a guessed SVG group order.
    by_role={p.sourceRole:p for p in result.panels}
    for role,part in zip(['Wall 1','Wall 2','Wall 4','Wall 3','Top','Bottom'],[p for p in b.surface.parts if p.pathes]):
        panel=by_role[role]; inverse=Affine(*panel.canvasToLocal)
        points=[inverse*(c[1],c[2]) for path in part.pathes for c in path.path if c[0] in ('M','L')]
        actual=[c[1:3] for c in panel.geometry.outer.commands if c[0] in ('M','L')]
        assert len(points)==len(actual)
        for expected,got in zip(points,actual):
            assert got==pytest.approx(expected,abs=1e-8)
    b.close()


@pytest.mark.parametrize('params', [ {'FingerJoint_style':'snap'}, {'x':float('inf')}, {'x':True}, {'x':10}, {'unknown':2}, {'thickness':25}])
def test_invalid_or_unsupported_parameters_rejected(params):
    a=adapter();d=data();d['parameters'].update(params)
    with pytest.raises(ValueError):
        a.generate(normalize_project(d),'nominal')


def test_stable_joint_pairs_are_reciprocal():
    result=adapter().generate(normalize_project(data()),'nominal')
    joints={(p.panelId,j['edgeId']):j for p in result.panels for j in p.jointDescriptors}
    assert len(joints)==24
    for (panel_id,edge_id),j in joints.items():
        mate=joints[j['matePanelId'],j['mateEdgeId']]
        assert (mate['matePanelId'],mate['mateEdgeId'])==(panel_id,edge_id)
        assert mate['jointId']==j['jointId']


def test_local_frame_survives_canvas_rotation_and_mirroring():
    from seedboxes.engine.capture import CapturingClosedBox
    from seedboxes.engine.paths import capture_path
    results=[]
    for move in ('right','rotated right','mirror right','rotated mirror right'):
        box=CapturingClosedBox()
        box.parseArgs(['--burn','0','--reference','0','--labels','0','--inner_corners','corner'])
        box.open()
        box.moveTo(73,41,17)
        box.rectangularWall(120,60,'FFFF',move=move,label='Wall 1')
        wall=box.captured_walls[0]
        path=capture_path(wall['paths'][0],wall['canvasToLocal'],'front:outer','cut_outer','corner')
        results.append(path)
        box.ctx=None
    for path in results[1:]:
        assert len(path.commands)==len(results[0].commands)
        for actual,expected in zip(path.commands,results[0].commands):
            assert actual[0]==expected[0]
            assert actual[1:]==pytest.approx(expected[1:],abs=1e-8)


def test_move_only_does_not_create_panel():
    from seedboxes.engine.capture import CapturingClosedBox
    box=CapturingClosedBox();box.parseArgs(['--reference','0','--labels','0']);box.open()
    box.rectangularWall(120,60,'FFFF',move='right only',label='ignored')
    assert box.captured_walls==[]
    box.ctx=None
