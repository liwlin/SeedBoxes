"""Desktop persistence boundary, ready for the editor to call in T06."""
from functools import wraps
import logging
from pathlib import Path
from threading import RLock

from seedboxes.domain.serialization import normalize_project, to_json
from seedboxes.manufacturing.profiles import ProfileStore, new_profile, normalize_profile
from seedboxes.storage.migrations import ReadOnlyProject
from seedboxes.storage.projects import ProjectStore
from .dialogs import ProjectDialogs


def response(method):
    @wraps(method)
    def wrapped(self,*args,**kwargs):
        try:
            with self._lock:
                result=method(self,*args,**kwargs)
            return {'ok':True,'data':to_json(result)}
        except (ValueError,OSError,RuntimeError) as exc:
            return {'ok':False,'error':{'code':'PERSISTENCE_ERROR','messageZh':str(exc),'retryable':False}}
        except Exception as exc:
            logging.error('Persistence operation %s failed (%s)',method.__name__,type(exc).__name__)
            return {'ok':False,'error':{'code':'PERSISTENCE_ERROR','messageZh':'存储操作失败，请检查输入和日志。','retryable':False}}
    return wrapped


class DesktopPersistence:
    def __init__(self,window_getter,data_dir=None):
        self._window=window_getter
        self._projects=ProjectStore(data_dir)
        self._profiles=ProfileStore(data_dir)
        self._paths={}
        self._lock=RLock()

    @staticmethod
    def _loaded(project,path):
        if isinstance(project,ReadOnlyProject):
            return {'project':project.document,'path':str(path) if path is not None else None,'readOnly':True,
                    'warning':'此工程来自较新版本，仅可查看原始数据，不能编辑保存。'}
        return {'project':to_json(project),'path':str(path) if path is not None else None,'readOnly':False}

    @response
    def load_project(self):
        path=ProjectDialogs(self._window()).open_path()
        if path is None:return {'cancelled':True}
        project=self._projects.load(path)
        if not isinstance(project,ReadOnlyProject):
            # Opening a backup is a recovery operation, not permission to overwrite the backup.
            if path.name.endswith('.bak'):
                self._paths.pop(project.projectId,None)
            else:self._paths[project.projectId]=path
        return self._loaded(project,path)

    @response
    def save_project(self,payload,save_as=False):
        if type(save_as) is not bool:raise ValueError('save_as 必须为布尔值')
        project=normalize_project(payload)
        path=None if save_as else self._paths.get(project.projectId)
        if path is None:path=ProjectDialogs(self._window()).save_path()
        if path is None:return {'cancelled':True}
        receipt=self._projects.save(project,path)
        self._paths[project.projectId]=Path(receipt.path)
        self._projects.clear_recovery(receipt)
        return receipt

    @response
    def save_recovery(self,payload):
        return self._projects.write_recovery(normalize_project(payload))

    @response
    def list_recovery(self):
        return self._projects.list_recovery()

    @response
    def load_recovery(self,project_id):
        project=self._projects.load_recovery(project_id)
        # Restored content has no implicit permission to overwrite an old formal path.
        if not isinstance(project,ReadOnlyProject):self._paths.pop(project.projectId,None)
        return self._loaded(project,None)

    @response
    def create_profile(self,kind):
        return new_profile(kind)

    @response
    def save_profile(self,payload):
        return self._profiles.save(normalize_profile(payload))

    @response
    def list_profiles(self):
        return self._profiles.list_profiles()
