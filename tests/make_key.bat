@echo off
rem Writes the draft answer key of every test case that has none yet (and rows for new files). Never changes a row already there.
cd /d "%~dp0.."
set PY=python
if exist ".venv\Scripts\python.exe" set PY=".venv\Scripts\python.exe"
rem the tests run the engine on this computer's Python (PyMuPDF as the PDF engine); the libraries: requirements-dev.txt
%PY% -m pip install -q --disable-pip-version-check -r requirements-dev.txt
%PY% tests\make_key.py %*
echo.
pause
