import json
from pathlib import Path

import pytest
from seedboxes.domain.serialization import validate_contract


def payload():
    return json.loads((Path(__file__).parent/'fixtures/project.json').read_text())


class Window:
    """Only the native picker is substituted; all persistence is real."""
    def __init__(self,*answers):self.answers=iter(answers)
    def create_file_dialog(self,*args,**kwargs):return next(self.answers)


def api(tmp_path):
    from backend import Api
    try:return Api(data_dir=tmp_path/'app-data')
    except TypeError:pytest.fail('Desktop storage interfaces are not implemented')


def test_save_open_and_cancel_keep_legacy_available(tmp_path):
    a=api(tmp_path);path=tmp_path/'中文工程.seedbox.json'
    a.set_window(Window([str(path)],None))
    saved=a.save_project(payload(),save_as=True)
    assert saved['ok'] and path.exists()
    validate_contract('response',saved)
    assert a.save_project(payload(),save_as=True)=={'ok':True,'data':{'cancelled':True}}
    a.set_window(Window((str(path),)))
    opened=a.load_project()
    assert opened['ok'] and opened['data']['project']==payload()
    assert opened['data']['readOnly'] is False
    assert 'svg' in a.preview('ClosedBox',{'x':120,'y':80,'h':60})


def test_save_current_path_and_backup_without_a_second_dialog(tmp_path):
    a=api(tmp_path);path=tmp_path/'project.seedbox.json';a.set_window(Window(str(path)))
    d=payload();assert a.save_project(d)['ok']
    d['revision']=1;d['name']='第二版'
    assert a.save_project(d)['ok']
    assert json.loads(path.read_text())['revision']==1
    assert json.loads(Path(str(path)+'.bak').read_text())['revision']==0


def test_future_project_api_returns_read_only_raw_document(tmp_path):
    a=api(tmp_path);path=tmp_path/'future.seedbox.json';d=payload();d['schemaVersion']=42;d['newField']=[3]
    path.write_text(json.dumps(d));a.set_window(Window([str(path)]))
    loaded=a.load_project()
    assert loaded['ok'] and loaded['data']['readOnly']
    assert loaded['data']['project']['newField']==[3]
    failed=a.save_project(loaded['data']['project'])
    assert not failed['ok'];validate_contract('response',failed)


def test_recovery_and_profile_endpoints_need_no_window(tmp_path):
    a=api(tmp_path);d=payload()
    assert a.save_recovery(d)['ok']
    assert a.list_recovery()['data'][0]['projectId']==d['projectId']
    assert a.load_recovery(d['projectId'])['data']['project']==d
    assert not a.load_recovery('../../outside')['ok']
    draft=a.create_profile('mdf')['data']
    saved=a.save_profile(draft)
    assert saved['ok'] and saved['data']['version']==1
    assert a.list_profiles()['data'][0]['profileId']==draft['profileId']


def test_native_save_failure_is_reported_without_erasing_recovery(tmp_path):
    a=api(tmp_path);d=payload();assert a.save_recovery(d)['ok']
    result=a.save_project(d)
    assert not result['ok']
    assert len(a.list_recovery()['data'])==1


def test_validation_errors_do_not_echo_user_documents():
    from seedboxes.domain.serialization import normalize_project
    d=payload();d['name']='private-content-'*100
    with pytest.raises(ValueError) as error:normalize_project(d)
    assert 'private-content' not in str(error.value)
