"""Bounded JSON IO and same-directory atomic replacement.

IO_LOCK serializes writers in this desktop process. os.replace is atomic on
supported local filesystems; this is not a multi-process database or a guarantee
against storage-device/power failure. Temporary files are closed before rename
for Windows compatibility.
"""
import json
import os
from pathlib import Path
import tempfile
from threading import RLock

from seedboxes.domain.serialization import ensure_json, to_json

MAX_BYTES = 20*1024*1024
IO_LOCK = RLock()


def read_bytes(path: Path) -> bytes:
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_BYTES+1)
    if len(raw) > MAX_BYTES:
        raise ValueError('文件超过 20 MiB 限制')
    return raw


def decode(raw: bytes):
    def unique(pairs):
        result = {}
        for key,value in pairs:
            if key in result:
                raise ValueError('JSON 包含重复字段：'+key)
            result[key] = value
        return result
    try:
        result = json.loads(raw.decode('utf-8-sig'),object_pairs_hook=unique)
        ensure_json(result)
    except (UnicodeError,json.JSONDecodeError,RecursionError) as exc:
        raise ValueError('文件不是有效的 UTF-8 JSON') from exc
    if not isinstance(result,dict):
        raise ValueError('文件顶层必须为对象')
    return result


def encode(value) -> bytes:
    raw = (json.dumps(to_json(value),ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')
    if len(raw) > MAX_BYTES:
        raise ValueError('文件超过 20 MiB 限制')
    return raw


def _stage(path: Path, raw: bytes) -> Path:
    fd,name = tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.tmp',dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        return temp
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def atomic_write(path: Path, raw: bytes, *, backup: bool | Path = False, exclusive=False) -> Path | None:
    path = Path(path)
    if len(raw) > MAX_BYTES:
        raise ValueError('文件超过 20 MiB 限制')
    path.parent.mkdir(parents=True,exist_ok=True)
    with IO_LOCK:
        previous = read_bytes(path) if backup and path.exists() else None
        staged = _stage(path,raw)
        backup_path = None
        backup_temp = None
        try:
            if previous is not None:
                backup_path = backup if isinstance(backup,Path) else path.with_name(path.name+'.bak')
                backup_temp = _stage(backup_path,previous)
                os.replace(backup_temp,backup_path)
            if exclusive:
                # Publishing an immutable profile version must never replace another writer.
                # App-data storage is local; unsupported hard-link filesystems fail explicitly.
                os.link(staged,path)
            else:
                os.replace(staged,path)
            return backup_path
        finally:
            staged.unlink(missing_ok=True)
            if backup_temp is not None:
                backup_temp.unlink(missing_ok=True)
