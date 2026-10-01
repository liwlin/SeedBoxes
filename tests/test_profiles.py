"""Global profile edits must never rewrite historical manufacturing context."""
import importlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
from seedboxes.domain.serialization import normalize_project,to_json


def module():
    try:return importlib.import_module('seedboxes.manufacturing.profiles')
    except ImportError:pytest.fail('Versioned process profiles are not implemented')


def measured_profile():
    m=module();p=to_json(m.new_profile('basswood'))
    p['material'].update(batch='batch-A',nominalThicknessMm=3,thicknessSamplesMm=[2.9,3.0,3.1,3.0,3.2])
    p['machine'].update(name='工坊激光机',model='Test machine',laserType='diode')
    p['process'].update(speed=10,speedUnit='mm/s',powerPercent=70,passes=1)
    p['compensation'].update(boxesBurnMm=.1,source='fitTest')
    return m.normalize_profile(p)


def calibrated_profile():
    m=module();p=to_json(measured_profile());p['status']='calibrated'
    p['evidence']['calibration']={'profileHash':m.process_hash(m.normalize_profile(p)),
        'calibratedAt':'2026-10-01T05:00:00Z','operator':'老师','result':'slipFit','cardHash':'a'*64}
    return m.normalize_profile(p)


def test_material_presets_do_not_invent_machine_settings():
    m=module()
    for kind in ('basswood','acrylic','mdf'):
        p=m.new_profile(kind)
        assert p.status=='reference' and p.compensation['boxesBurnMm'] is None
        assert p.process['speed'] is None and p.process['powerPercent'] is None
        assert p.material['thicknessSamplesMm']==[]


def test_profile_edit_does_not_mutate_project_snapshot(tmp_path):
    m=module();store=m.ProfileStore(tmp_path);first=store.save(measured_profile())
    raw=json.loads((Path(__file__).parent/'fixtures/project.json').read_text())
    raw['profileSnapshot']=m.profile_snapshot(first);p=normalize_project(raw)
    changed=to_json(first);changed['material']['batch']='batch-B'
    second=store.save(m.normalize_profile(changed))
    assert (first.version,second.version)==(1,2)
    assert p.profileSnapshot['material']['batch']=='batch-A'
    assert store.load(first.profileId,1).material['batch']=='batch-A'
    assert store.list_profiles()[0].material['batch']=='batch-B'
    changed['material']['batch']='mutated after save'
    assert store.load(first.profileId).material['batch']=='batch-B'


@pytest.mark.parametrize('section,key,value',[('machine','model','another'),('material','batch','B'),('material','thicknessSamplesMm',[3.1]*5),('process','speed',11),('compensation','boxesBurnMm',.2)])
def test_process_edit_invalidates_calibration(tmp_path,section,key,value):
    m=module();store=m.ProfileStore(tmp_path);first=store.save(calibrated_profile())
    d=to_json(first);d[section][key]=value
    second=store.save(m.normalize_profile(d))
    assert second.status=='reference'
    assert second.evidence['calibration'] is None
    assert second.evidence['history'][-1]['calibration']['cardHash']=='a'*64
    assert store.load(first.profileId,1).status=='calibrated'


def test_rename_keeps_calibration_and_stale_save_is_rejected(tmp_path):
    m=module();store=m.ProfileStore(tmp_path);first=store.save(calibrated_profile())
    second=store.save(replace(first,name='新名称'))
    assert second.status=='calibrated'
    with pytest.raises(ValueError,match='版本|过期'):store.save(replace(first,name='迟到的编辑'))
    assert store.load(first.profileId).name=='新名称'


def test_five_point_measurement_summaries_and_short_sample_rejection():
    m=module();p=measured_profile()
    assert p.material['minThicknessMm']==2.9
    assert p.material['maxThicknessMm']==3.2
    assert p.material['representativeThicknessMm']==3.0
    raw=to_json(p);raw['material']['thicknessSamplesMm']=[3,3,3]
    with pytest.raises(ValueError):m.normalize_profile(raw)


def test_calibrated_profile_requires_matching_evidence(tmp_path):
    m=module();store=m.ProfileStore(tmp_path);p=to_json(measured_profile());p['status']='calibrated'
    with pytest.raises(ValueError,match='校准'):store.save(m.normalize_profile(p))
    p=to_json(calibrated_profile());p['evidence']['calibration']['profileHash']='b'*64
    with pytest.raises(ValueError,match='校准'):store.save(m.normalize_profile(p))


def test_profile_snapshot_requires_explicit_burn():
    m=module()
    with pytest.raises(ValueError,match='burn|补偿'):m.profile_snapshot(m.new_profile('mdf'))


def test_invalid_profile_identity_cannot_escape_storage(tmp_path):
    m=module();p=to_json(measured_profile());p['profileId']='../../outside'
    with pytest.raises(ValueError):m.ProfileStore(tmp_path).save(m.normalize_profile(p))
    with pytest.raises(ValueError):m.ProfileStore(tmp_path).load('../../outside')


def test_profile_publish_failure_keeps_last_version(tmp_path,monkeypatch):
    m=module();store=m.ProfileStore(tmp_path);first=store.save(measured_profile())
    atomic=importlib.import_module('seedboxes.storage.atomic')
    def fail_link(src,dst):raise OSError('simulated disk failure')
    monkeypatch.setattr(atomic.os,'link',fail_link)
    with pytest.raises(OSError):store.save(replace(first,name='not published'))
    assert store.load(first.profileId).version==1
    assert store.load(first.profileId).name==first.name
    assert not list(tmp_path.rglob('*.tmp'))
