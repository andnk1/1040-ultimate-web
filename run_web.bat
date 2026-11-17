@echo off
rem 1040 Ultimate - the browser app (design\web_version.md). Python runs inside the browser tab (Pyodide); this window is
rem only a tiny local server that hands out the files. Nothing is uploaded.
cd /d "%~dp0"
set PY=python
if exist ".venv\Scripts\python.exe" set PY=".venv\Scripts\python.exe"
if not exist "web\vendor\manifest.json" (
  echo First start: downloading Pyodide, the libraries and MuPDF.js into web\vendor - about 40 MB, needs internet once...
  %PY% web\get_vendor.py
  if errorlevel 1 goto :stopped
)
echo Starting the browser version - open http://127.0.0.1:5070 in Chrome or Edge if it does not open by itself.
%PY% web\serve.py --quiet
:stopped
echo.
echo The program stopped - the message above says why.
pause
