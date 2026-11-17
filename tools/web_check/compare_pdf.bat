@echo off
rem Compares what the PDF door gives on the desktop (PyMuPDF) and in the browser version (MuPDF.js) for every PDF of a folder:
rem text, words, blocks, "dict" lines, filled shapes - page by page. Needs Node.js and web\vendor (run_web.bat once).
rem     tools\web_check\compare_pdf.bat "<folder with PDFs>"
cd /d "%~dp0..\.."
if "%~1"=="" ( echo Give a folder:  tools\web_check\compare_pdf.bat "C:\path\to\PDFs" & pause & exit /b 1 )
set PY=python
if exist ".venv\Scripts\python.exe" set PY=".venv\Scripts\python.exe"
set PYTHONIOENCODING=utf-8
set OUT=%TEMP%\u1040_web_check
if not exist "%OUT%" mkdir "%OUT%"
%PY% tools\web_check\dump.py "%~1" "%OUT%\desktop.json"
node tools\web_check\run.mjs tools\web_check\dump.py "data=%~1" "out=%OUT%" -- /data /out/web.json
%PY% tools\web_check\compare.py "%OUT%\desktop.json" "%OUT%\web.json" > tools\web_check\compare_report.txt
type tools\web_check\compare_report.txt
echo.
echo The report is in tools\web_check\compare_report.txt
pause
