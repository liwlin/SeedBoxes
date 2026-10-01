"""Generate paired nominal/toolpath snapshots, with bounded detached storage."""
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime, timezone
import json
from threading import RLock
from uuid import uuid4

from seedboxes.domain.models import GeneratedModel, Panel, Project
from seedboxes.domain.serialization import normalize_project, project_input_hash, to_json, validate_contract
from .bridge import engine_fingerprint, ENGINE_LOCK
from .registry import get_adapter


class GeometryService:
    def __init__(self, max_entries=8, max_bytes=64*1024*1024):
        if type(max_entries) is not int or max_entries < 1 or type(max_bytes) is not int or max_bytes < 1:
            raise ValueError('缓存上限必须为正整数')
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self._cache = OrderedDict()
        self._bytes = 0
        self._lock = RLock()

    def generate(self, project: Project) -> GeneratedModel:
        snapshot = normalize_project(to_json(project))
        adapter = get_adapter(snapshot.generatorId)
        fingerprint = dict(engine_fingerprint())
        with ENGINE_LOCK:
            nominal = adapter.generate(snapshot, 'nominal')
            toolpath = adapter.generate(snapshot, 'toolpath')
        if {p.panelId for p in nominal.panels} != {p.panelId for p in toolpath.panels}:
            raise ValueError('名义与切割板件身份不匹配')
        tool_panels = {p.panelId:p for p in toolpath.panels}
        panels = []
        for panel in nominal.panels:
            cut = tool_panels[panel.panelId]
            if {p.pathId for p in panel.geometry.holes} != {p.pathId for p in cut.geometry.holes}:
                raise ValueError('名义与切割开孔身份不匹配')
            panels.append(Panel(
                panelId=panel.panelId, displayCode=panel.displayCode, label=panel.sourceRole,
                thicknessMm=panel.thicknessMm, nominalGeometry=panel.geometry,
                cutGeometry={'operations':(cut.geometry.outer,*cut.geometry.holes,*cut.geometry.engravings)},
                localFrame={'origin':'inner-face joint-root reference','units':'mm',
                            'xAxis':'panel width','yAxis':'panel height','zAxis':'outward normal',
                            'referenceWidthMm':panel.widthMm,'referenceHeightMm':panel.heightMm},
                assemblyTransform={'matrixColumnMajor':panel.assemblyTransform,'conventionVersion':1},
                layoutTransform=None, joints=panel.jointDescriptors,
                provenance={'generatorId':snapshot.generatorId,'sourceRole':panel.sourceRole,
                            'adapterId':adapter.adapter_id,'adapterVersion':adapter.version},
            ))
        model = GeneratedModel(
            generationId=str(uuid4()), projectId=snapshot.projectId, revision=snapshot.revision,
            inputHash=project_input_hash(snapshot,fingerprint), engineFingerprint=fingerprint,
            adapterVersion=adapter.version, units='mm', panels=tuple(panels), sheets=(),
            diagnostics=(*nominal.diagnostics, {'code':'MANUFACTURING_UNCHECKED',
                'messageZh':'尚未执行制造体检、排版或试切验证；当前结果不可视为切割放行。'}),
            generatedAt=datetime.now(timezone.utc).isoformat(),
            geometries={'nominal':True,'compensatedToolpaths':True},
            innerDimensions=nominal.innerDimensions,
        )
        payload = to_json(model)
        validate_contract('generated-model',payload)
        size = len(json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode('utf-8'))
        if size > self.max_bytes:
            raise ValueError('生成结果超出缓存容量')
        with self._lock:
            while self._cache and (len(self._cache) >= self.max_entries or self._bytes+size > self.max_bytes):
                _,(_,old_size) = self._cache.popitem(last=False)
                self._bytes -= old_size
            self._cache[model.generationId] = (deepcopy(model),size)
            self._bytes += size
        return model

    def get_generation(self, generation_id: str) -> GeneratedModel:
        with self._lock:
            model,_ = self._cache[generation_id]
            self._cache.move_to_end(generation_id)
            return deepcopy(model)
