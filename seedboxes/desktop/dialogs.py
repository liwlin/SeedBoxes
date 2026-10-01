"""Native file selection; cancellation is distinct from failure."""
from pathlib import Path
import webview


class ProjectDialogs:
    def __init__(self,window):
        if window is None:
            raise RuntimeError('窗口未初始化，无法选择工程文件')
        self.window=window

    @staticmethod
    def _picked(value):
        if not value:
            return None
        if isinstance(value,(list,tuple)):
            value=value[0]
        return Path(value)

    def open_path(self):
        return self._picked(self.window.create_file_dialog(webview.OPEN_DIALOG,allow_multiple=False,
            file_types=('SeedBoxes (*.seedbox.json)','SeedBoxes backup (*.bak)','All files (*.*)')))

    def save_path(self):
        path=self._picked(self.window.create_file_dialog(webview.SAVE_DIALOG,
            save_filename='SeedBoxes.seedbox.json',file_types=('SeedBoxes (*.seedbox.json)',)))
        if path is not None and not path.name.lower().endswith('.seedbox.json'):
            path=path.with_name(path.name+'.seedbox.json')
        return path
