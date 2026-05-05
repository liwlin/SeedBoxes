"""Boxes.py 桌面客户端入口."""
from __future__ import annotations

import os
import sys

import webview

from backend import Api


def _apply_win_icon(window: webview.Window, ico_path: str, title: str) -> None:
    """开发模式下把 Windows 窗口图标设为指定 .ico
    （PyWebView 6.2.1 的 create_window 不支持 icon 参数）."""
    if sys.platform != "win32" or not os.path.isfile(ico_path):
        return
    def _apply() -> None:
        try:
            import ctypes
            user32 = ctypes.windll.user32
            WM_SETICON, ICON_BIG, ICON_SMALL = 0x0080, 1, 0
            IMAGE_ICON, LR_LOADFROMFILE = 1, 0x10
            big = user32.LoadImageW(0, ico_path, IMAGE_ICON, 256, 256, LR_LOADFROMFILE)
            small = user32.LoadImageW(0, ico_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
            hwnd = user32.FindWindowW(None, title)
            if hwnd:
                if big:
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, big)
                if small:
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, small)
        except Exception:
            pass
    try:
        window.events.shown += _apply
    except Exception:
        pass


def get_web_path() -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "web")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


def main() -> None:
    api = Api()
    web_dir = get_web_path()
    title = "SeedBoxes v0.1"
    window = webview.create_window(
        title=title,
        url=os.path.join(web_dir, "index.html"),
        js_api=api,
        width=1400,
        height=880,
        min_size=(1080, 680),
        background_color="#FAFAF7",
        text_select=False,
    )
    api.set_window(window)
    # 开发模式下用 Win32 API 替换标题栏 + 任务栏图标。
    # PyInstaller 打包后由 .spec 的 icon 参数控制（不依赖此函数）。
    if hasattr(sys, "_MEIPASS"):
        ico = os.path.join(sys._MEIPASS, "logo.ico")
    else:
        ico = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.ico")
    _apply_win_icon(window, ico, title)
    debug = os.environ.get("SEEDBOXES_DEBUG", "0") == "1"
    webview.start(debug=debug)


if __name__ == "__main__":
    main()
