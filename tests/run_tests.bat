@echo off
rem Runs every test case in tests\samples against its answer key (pass / fail per case and sheet; every row that differs).
cd /d "%~dp0.."
set PY=python
if exist ".venv\Scripts\python.exe" set PY=".venv\Scripts\python.exe"
rem the tests run the engine on this computer's Python (PyMuPDF as the PDF engine); the libraries: requirements-dev.txt
%PY% -m pip install -q --disable-pip-version-check -r requirements-dev.txt
%PY% -m pytest tests -q -p no:cacheprovider -rf --tb=short %*
echo.
pause
