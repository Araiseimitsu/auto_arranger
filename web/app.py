import sys
import os
from pathlib import Path

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

app = FastAPI(title="Auto Arranger")

# Mount static files
# In frozen app, static files are in sys._MEIPASS/web/static
def get_static_dir():
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / "web" / "static"
    return Path("web/static")

app.mount("/static", StaticFiles(directory=str(get_static_dir())), name="static")
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import threading
    import time

    def open_browser():
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:8000")

    print("Starting server at http://127.0.0.1:8000")
    
    # Launch browser in a separate thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run server
    uvicorn.run(app, host="127.0.0.1", port=8000)
