import PyInstaller.__main__
import shutil
from pathlib import Path

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
icon_path = Path('web/static/resources/auto_arranger.ico').resolve()
if icon_path.exists():
    print(f"Icon found at: {icon_path}")
    args.append(f'--icon={str(icon_path)}')
else:
    print(f"WARNING: Icon file not found at {icon_path}. Please convert the PNG to ICO to have a custom icon.")

PyInstaller.__main__.run(args)

print("Build complete. Executable is in 'dist' folder.")

