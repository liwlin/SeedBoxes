"""Formal projects, previous-file backups, and separate crash-recovery snapshots."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import sys
from uuid import UUID

from seedboxes.domain.models import Project
from seedboxes.domain.serialization import normalize_project, to_json
from .atomic import IO_LOCK, atomic_write, decode, encode, read_bytes
from .migrations import CURRENT_SCHEMA, ReadOnlyProject, load_document


def app_data_dir() -> Path:
    if sys.platform == 'win32':
        base = Path(os.environ.get('LOCALAPPDATA',Path.home()/'AppData'/'Local'))
    else:
        base = Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local'/'share'))
    return base/'MakerSeed'/'SeedBoxes'


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class SaveReceipt:
    projectId: str
    revision: int
    path: str
    savedAt: str
    backupPath: str | None
    contentHash: str


class ProjectStore:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = Path(data_dir) if data_dir is not None else app_data_dir()
        self.recovery_dir = self.data_dir/'recovery'

    def load(self, path: Path) -> Project | ReadOnlyProject:
        path = Path(path).resolve()
        return load_document(decode(read_bytes(path)),path)

    def save(self, project: Project, path: Path) -> SaveReceipt:
        if not isinstance(project,Project):
            raise ValueError('未知版本工程只读，不能保存')
        raw = encode(project)
        snapshot = normalize_project(decode(raw))
        raw = encode(snapshot)
        path = Path(path).resolve()
        with IO_LOCK:
            backup_target = True
            if path.exists():
                try:
                    previous = load_document(decode(read_bytes(path)),path)
                except ValueError:
                    # Do not destroy the last good .bak while repairing a corrupt formal file.
                    # Keep the damaged bytes separately, including on final replacement failure.
                    backup_target = path.with_name(path.name+'.corrupt.bak')
                else:
                    if isinstance(previous,ReadOnlyProject):
                        raise ValueError('目标文件为较新版本，只读，不能覆盖')
            backup = atomic_write(path,raw,backup=backup_target)
        return SaveReceipt(snapshot.projectId,snapshot.revision,str(path),
            datetime.now(timezone.utc).isoformat(),str(backup) if backup else None,_digest(raw))

    def _recovery_path(self, project_id: str) -> Path:
        return self.recovery_dir/(str(UUID(project_id))+'.seedbox.json')

    def load_recovery(self, project_id: str) -> Project | ReadOnlyProject:
        try:
            path = self._recovery_path(project_id)
        except (ValueError,TypeError,AttributeError) as exc:
            raise ValueError('恢复工程 ID 无效') from exc
        return self.load(path)

    def write_recovery(self, project: Project) -> SaveReceipt:
        if not isinstance(project,Project):
            raise ValueError('只读工程不能写入恢复区')
        raw = encode(project)
        project = normalize_project(decode(raw))
        path = self._recovery_path(project.projectId)
        with IO_LOCK:
            if path.exists():
                previous = self.load(path)
                if isinstance(previous,ReadOnlyProject):
                    raise ValueError('恢复工程版本较新，只读')
                if previous.revision > project.revision:
                    raise ValueError('过期编辑不能覆盖较新的恢复记录')
            atomic_write(path,raw)
        return SaveReceipt(project.projectId,project.revision,str(path),
                           datetime.now(timezone.utc).isoformat(),None,_digest(raw))

    def list_recovery(self) -> list[dict]:
        result = []
        for path in sorted(self.recovery_dir.glob('*.seedbox.json')):
            item = {'path':str(path),'projectId':None,'revision':None,'name':None,
                    'readOnly':True,'contentHash':None,'error':None}
            try:
                raw = read_bytes(path);data=decode(raw);loaded=load_document(data,path)
                item.update(projectId=data.get('projectId'),revision=data.get('revision'),name=data.get('name'),
                            readOnly=isinstance(loaded,ReadOnlyProject),contentHash=_digest(raw))
            except (ValueError,OSError) as exc:
                item['error']=str(exc)
            result.append(item)
        return result

    def clear_recovery(self, receipt: SaveReceipt) -> bool:
        """Only clear the exact snapshot confirmed present in its formal file."""
        path = self._recovery_path(receipt.projectId)
        with IO_LOCK:
            try:
                if path.resolve()==Path(receipt.path).resolve():
                    return False
                if _digest(read_bytes(Path(receipt.path)))!=receipt.contentHash:
                    return False
                if _digest(read_bytes(path))!=receipt.contentHash:
                    return False
                path.unlink()
                return True
            except (OSError,ValueError):
                return False
