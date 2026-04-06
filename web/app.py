import sys
from pathlib import Path
import ctypes
import logging

# Add project root to sys.path to allow imports from src and utils
# This is needed when running from the web directory or packaged app
if getattr(sys, 'frozen', False):
    # Running as compiled exe
    project_root = Path(sys.executable).parent
else:
    # Running from source
    project_root = Path(__file__).parent.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from web.routes import router

logger = logging.getLogger(__name__)
WINDOWS_APP_USER_MODEL_ID = "jp.seizo.auto_arranger.desktop"

app = FastAPI(title="Auto Arranger")

# Mount static files
# In frozen app, resources are under sys._MEIPASS
def get_resource_root() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return project_root


def get_static_dir() -> Path:
    return get_resource_root() / "web" / "static"


def get_icon_path() -> Path:
    return get_static_dir() / "resources" / "auto_arranger.ico"


def configure_windows_app_identity() -> None:
    if sys.platform != "win32":
        return

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            WINDOWS_APP_USER_MODEL_ID
        )
        logger.info("AppUserModelID configured: %s", WINDOWS_APP_USER_MODEL_ID)
    except Exception:
        logger.exception("Failed to configure AppUserModelID")


def apply_windows_window_icon(window, icon_path: Path) -> None:
    if sys.platform != "win32" or not icon_path.exists():
        return

    try:
        native = getattr(window, "native", None)
        handle = getattr(native, "Handle", None)
        if handle is None:
            logger.warning("Window handle is not available. Skip window icon apply.")
            return

        hwnd = int(handle.ToInt64()) if hasattr(handle, "ToInt64") else int(handle)
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x00000010
        LR_DEFAULTSIZE = 0x00000040
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1

        hicon = ctypes.windll.user32.LoadImageW(
            0,
            str(icon_path),
            IMAGE_ICON,
            0,
            0,
            LR_LOADFROMFILE | LR_DEFAULTSIZE,
        )
        if not hicon:
            logger.warning("Failed to load icon file: %s", icon_path)
            return

        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon)
        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon)
        logger.info("Window icon applied from: %s", icon_path)
    except Exception:
        logger.exception("Failed to apply window icon")

app.mount("/static", StaticFiles(directory=str(get_static_dir())), name="static")
app.include_router(router)

def launch_desktop_app() -> None:
    import uvicorn
    import threading
    import webview

    def start_server():
        """uvicornサーバーをバックグラウンドで起動"""
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

    # サーバーをバックグラウンドスレッドで起動
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    configure_windows_app_identity()
    icon_path = get_icon_path()

    # pywebviewでウィンドウを作成
    # ウィンドウを閉じるとアプリケーションが終了する
    window = webview.create_window(
        "Auto Arranger",
        "http://127.0.0.1:8000",
        width=1200,
        height=800,
        min_size=(800, 600)
    )
    window.events.shown += lambda: apply_windows_window_icon(window, icon_path)
    webview.start()


if __name__ == "__main__":
    launch_desktop_app()
