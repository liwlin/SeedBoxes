"""Immutable process versions with explicit calibration provenance."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import median
from uuid import UUID, uuid4

from seedboxes.domain.models import ProcessProfile
from seedboxes.domain.serialization import to_json, validate_contract, _canonical
from seedboxes.storage.atomic import IO_LOCK, atomic_write, decode, encode, read_bytes
from seedboxes.storage.projects import app_data_dir

MATERIAL_NAMES = {'basswood':'椴木板','acrylic':'亚克力','mdf':'密度板','custom':'自定义材料'}
PROCESS_FIELDS = ('machine','material','process','compensation','machineBed','rules')


def new_profile(kind: str) -> ProcessProfile:
    if kind not in MATERIAL_NAMES:
        raise ValueError('未知材料种类')
    return normalize_profile({
        'schemaVersion':1,'profileId':str(uuid4()),'version':0,
        'name':MATERIAL_NAMES[kind]+' · 未校准','status':'reference',
        'machine':{'name':'','model':'','laserType':'unknown','ratedPowerW':None,'opticsNotes':''},
        'material':{'kind':kind,'name':MATERIAL_NAMES[kind],'supplier':'','batch':'',
                    'nominalThicknessMm':None,'thicknessSamplesMm':[],
                    'minThicknessMm':None,'maxThicknessMm':None,'representativeThicknessMm':None,
                    'measurementMethod':'median'},
        'process':{'speed':None,'speedUnit':'mm/s','powerPercent':None,'passes':None,
                   'focusNotes':'','airAssist':None,'airPressureKpa':None,'surfaceNotes':''},
        'compensation':{'physicalKerfMm':None,'boxesBurnMm':None,'jointClearanceMm':0.,'source':'reference'},
        'machineBed':{'widthMm':None,'heightMm':None,'marginMm':None},'rules':{},
        'evidence':{'calibration':None,'history':[]},
    })


def normalize_profile(value) -> ProcessProfile:
    data=to_json(value)
    validate_contract('process-profile',data)
    data['schemaVersion']=int(data['schemaVersion'])
    data['version']=int(data['version'])
    material=data['material'];samples=material['thicknessSamplesMm']
    material.update(minThicknessMm=min(samples) if samples else None,
                    maxThicknessMm=max(samples) if samples else None,
                    representativeThicknessMm=median(samples) if samples else None)
    data['profileId']=str(UUID(data['profileId']))
    return ProcessProfile(**data)


def process_hash(profile: ProcessProfile) -> str:
    data=to_json(normalize_profile(profile))
    payload=json.dumps(_canonical({k:data[k] for k in PROCESS_FIELDS}),sort_keys=True,
                       separators=(',',':'),ensure_ascii=False,allow_nan=False)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def _check_calibration(profile: ProcessProfile):
    if profile.status!='calibrated':
        return
    calibration=profile.evidence['calibration']
    if (not calibration or calibration['profileHash']!=process_hash(profile)
        or len(profile.material['thicknessSamplesMm'])<5
        or profile.compensation['boxesBurnMm'] is None
        or profile.compensation['source']=='reference'
        or not profile.machine['name'].strip()
        or any(profile.process[k] is None for k in ('speed','powerPercent','passes'))):
        raise ValueError('校准证据缺失、已过期或加工条件未填写')


def profile_snapshot(profile: ProcessProfile) -> dict:
    profile=normalize_profile(profile)
    _check_calibration(profile)
    if profile.compensation['boxesBurnMm'] is None:
        raise ValueError('请明确填写 burn 补偿后再用于工程，不自动代入默认值')
    return to_json(profile)


class ProfileStore:
    def __init__(self,data_dir: Path | None = None):
        self.directory=(Path(data_dir) if data_dir is not None else app_data_dir())/'profiles'

    def _directory(self,profile_id: str) -> Path:
        try:identity=str(UUID(profile_id))
        except (ValueError,TypeError,AttributeError) as exc:raise ValueError('档案 ID 无效') from exc
        return self.directory/identity

    def _versions(self,profile_id: str) -> list[int]:
        return sorted(int(p.stem) for p in self._directory(profile_id).glob('*.json')
                      if p.stem.isdecimal() and int(p.stem)>0)

    def load(self,profile_id: str,version: int | None = None) -> ProcessProfile:
        folder=self._directory(profile_id)
        if version is None:
            versions=self._versions(profile_id)
            if not versions:raise FileNotFoundError('加工档案不存在')
            version=versions[-1]
        if type(version) is not int or version<1:
            raise ValueError('档案版本无效')
        profile=normalize_profile(decode(read_bytes(folder/f'{version}.json')))
        if profile.profileId!=folder.name or profile.version!=version:
            raise ValueError('档案文件身份或版本不匹配')
        _check_calibration(profile)
        return profile

    def list_profiles(self) -> list[ProcessProfile]:
        if not self.directory.exists():
            return []
        result=[]
        for folder in sorted(self.directory.iterdir()):
            if folder.is_dir():
                # Empty folders can remain after an interrupted first write.
                if self._versions(folder.name):result.append(self.load(folder.name))
        return result

    def save(self,profile: ProcessProfile) -> ProcessProfile:
        profile=normalize_profile(profile)
        with IO_LOCK:
            versions=self._versions(profile.profileId)
            current=self.load(profile.profileId) if versions else None
            expected=current.version if current else 0
            if profile.version!=expected:
                raise ValueError('档案版本已过期，请重新加载后修改')
            changed=current is not None and process_hash(current)!=process_hash(profile)
            if changed:
                evidence=deepcopy(profile.evidence)
                # Keep the known original calibration, not a caller's replacement for it.
                calibration=current.evidence['calibration']
                if calibration:
                    evidence['history'].append({'calibration':deepcopy(calibration),
                        'invalidatedAt':datetime.now(timezone.utc).isoformat(),
                        'reason':'processChanged','previousVersion':current.version})
                evidence['calibration']=None
                profile=replace(profile,status='retired' if profile.status=='retired' else 'reference',evidence=evidence)
            _check_calibration(profile)
            saved=normalize_profile(replace(profile,version=expected+1))
            path=self._directory(saved.profileId)/f'{saved.version}.json'
            try:atomic_write(path,encode(saved),exclusive=True)
            except FileExistsError as exc:raise ValueError('档案版本已被其他写入占用，请重新加载') from exc
            return saved
