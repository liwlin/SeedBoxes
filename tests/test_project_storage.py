"""Persistent-file behavior: interruption, compatibility, and recovery identity."""
import importlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
from seedboxes.domain.serialization import normalize_project, to_json

ROOT = Path(__file__).resolve().parents[1]


def storage(tmp_path):
    try:
        return importlib.import_module('seedboxes.storage.projects').ProjectStore(tmp_path/'app-data')
    except ImportError:
        pytest.fail('Project persistence is not implemented')


def project():
    return normalize_project(json.loads((ROOT/'tests/fixtures/project.json').read_text()))


def test_unicode_round_trip_and_previous_backup(tmp_path):
    store=storage(tmp_path);path=tmp_path/'碉楼.seedbox.json';first=project()
    receipt=store.save(first,path)
    assert receipt.projectId==first.projectId and receipt.backupPath is None
    assert store.load(path)==first
    second=replace(first,name='碉楼第二版',revision=1)
    receipt=store.save(second,path)
    assert store.load(path)==second
    assert store.load(Path(receipt.backupPath))==first
    assert not list(tmp_path.glob('*.tmp'))


@pytest.mark.parametrize('failure',['flush','backup','replace'])
def test_atomic_save_failure_keeps_previous(tmp_path,monkeypatch,failure):
    store=storage(tmp_path);path=tmp_path/'box.seedbox.json';first=project()
    store.save(first,path);old=path.read_bytes()
    atomic=importlib.import_module('seedboxes.storage.atomic')
    original=atomic.os.replace
    def fail_replace(src,dst):
        if (failure=='backup' and str(dst).endswith('.bak')) or (failure=='replace' and Path(dst)==path):
            raise OSError('simulated full disk / sharing violation')
        return original(src,dst)
    if failure=='flush':
        def fail_sync(fd):raise OSError('simulated flush failure')
        monkeypatch.setattr(atomic.os,'fsync',fail_sync)
    else:monkeypatch.setattr(atomic.os,'replace',fail_replace)
    with pytest.raises(OSError):store.save(replace(first,revision=1),path)
    assert path.read_bytes()==old
    assert not list(tmp_path.glob('*.tmp'))


def test_future_schema_is_read_only(tmp_path):
    store=storage(tmp_path);path=tmp_path/'future.seedbox.json'
    raw=to_json(project());raw['schemaVersion']=99;raw['unknownFutureField']={'keep':[1,2,3]}
    path.write_text(json.dumps(raw),encoding='utf-8');before=path.read_bytes()
    loaded=store.load(path)
    assert loaded.readOnly and loaded.document==raw
    with pytest.raises(ValueError,match='只读|版本'):store.save(loaded,tmp_path/'copy.seedbox.json')
    with pytest.raises(ValueError,match='只读|版本'):store.save(project(),path)
    assert path.read_bytes()==before


@pytest.mark.parametrize('text',['{"schemaVersion":1,','{"schemaVersion":1,"schemaVersion":99}','{"schemaVersion":NaN}','[]'])
def test_invalid_json_never_overwrites_source(tmp_path,text):
    store=storage(tmp_path);path=tmp_path/'broken.seedbox.json';path.write_text(text)
    with pytest.raises(ValueError):store.load(path)
    assert path.read_text()==text


def test_import_and_save_size_limit(tmp_path):
    store=storage(tmp_path);path=tmp_path/'large.seedbox.json'
    with path.open('wb') as stream:stream.truncate(20*1024*1024+1)
    with pytest.raises(ValueError,match='20 MiB'):store.load(path)
    good=tmp_path/'small.seedbox.json';store.save(project(),good);original=good.read_bytes()
    huge=replace(project(),name='x'*(20*1024*1024))
    with pytest.raises(ValueError,match='20 MiB'):store.save(huge,good)
    assert good.read_bytes()==original


def test_recovery_is_separate_and_only_matching_saved_snapshot_is_cleared(tmp_path):
    store=storage(tmp_path);path=tmp_path/'formal.seedbox.json';first=project()
    receipt=store.save(first,path)
    newer=replace(first,revision=1,name='未保存编辑')
    store.write_recovery(newer)
    candidates=store.list_recovery()
    assert len(candidates)==1 and candidates[0]['revision']==1
    assert store.load(path)==first
    assert not store.clear_recovery(receipt)
    receipt=store.save(newer,path)
    assert store.clear_recovery(receipt)
    assert store.list_recovery()==[]


def test_recovery_listing_survives_one_corrupt_file_and_rejects_stale_write(tmp_path):
    store=storage(tmp_path);p=project();store.write_recovery(replace(p,revision=2))
    with pytest.raises(ValueError,match='过期'):store.write_recovery(p)
    folder=tmp_path/'app-data'/'recovery'
    (folder/'broken.seedbox.json').write_text('{')
    items=store.list_recovery()
    assert len(items)==2 and sum(item['error'] is not None for item in items)==1
    assert any(item['revision']==2 for item in items)


def test_external_change_prevents_recovery_cleanup(tmp_path):
    store=storage(tmp_path);p=project();path=tmp_path/'formal.seedbox.json'
    store.write_recovery(p);receipt=store.save(p,path)
    path.write_text('{}')
    assert not store.clear_recovery(receipt)
    assert len(store.list_recovery())==1


def test_newer_recovery_survives_cleanup_for_older_save(tmp_path):
    store=storage(tmp_path);p=project();formal=tmp_path/'box.seedbox.json'
    store.write_recovery(p);receipt=store.save(p,formal)
    store.write_recovery(replace(p,revision=1))
    assert not store.clear_recovery(receipt)
    assert store.list_recovery()[0]['revision']==1
