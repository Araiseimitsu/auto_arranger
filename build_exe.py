import PyInstaller.__main__
import shutil
from pathlib import Path

# Clean previous build
if Path("dist").exists():
    shutil.rmtree("dist")
if Path("build").exists():
    shutil.rmtree("build")

PyInstaller.__main__.run([
    'web/app.py',
    '--name=AutoArranger',
    '--onefile',
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
    '--clean',
])

print("Build complete. Executable is in 'dist' folder.")

