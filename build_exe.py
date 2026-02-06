import PyInstaller.__main__
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
ICON_PATH = PROJECT_ROOT / 'web' / 'static' / 'resources' / 'auto_arranger.ico'

# Clean previous build
if Path("dist").exists():
    shutil.rmtree("dist")
if Path("build").exists():
    shutil.rmtree("build")

args = [
    'web/app.py',
    '--name=AutoArranger',
    '--onefile',
    '--noconsole',  # コンソールウィンドウを非表示
    '--add-data=web/templates;web/templates',
    '--add-data=web/static;web/static',
    '--add-data=config;config',  # Default configs
    '--hidden-import=uvicorn.logging',
    '--hidden-import=uvicorn.loops',
    '--hidden-import=uvicorn.loops.auto',
    '--hidden-import=uvicorn.protocols',
    '--hidden-import=uvicorn.protocols.http',
    '--hidden-import=uvicorn.protocols.http.auto',
    '--hidden-import=uvicorn.lifespan',
    '--hidden-import=uvicorn.lifespan.on',
    '--hidden-import=engineio.async_drivers.asgi',
    '--hidden-import=pandas',
    '--hidden-import=yaml',
    '--hidden-import=webview',  # pywebview
    '--clean',
]

# Check for icon
if ICON_PATH.exists():
    print(f"Icon found at: {ICON_PATH}")
    args.append(f'--icon={str(ICON_PATH)}')
else:
    print(f"WARNING: Icon file not found at {ICON_PATH}. Please convert the PNG to ICO to have a custom icon.")

PyInstaller.__main__.run(args)

print("Build complete. Executable is in 'dist' folder.")
