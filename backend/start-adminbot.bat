@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo No .venv found in %SCRIPT_DIR%
    echo Create it first:
    echo     cd /d "%SCRIPT_DIR%"
    echo     py -3.13 -m venv .venv
    echo     .venv\Scripts\python.exe -m pip install -r requirements.txt
    exit /b 1
)

if not exist "%SCRIPT_DIR%.env" (
    echo No backend\.env found. Copy .env.example to .env and fill in real values first.
    exit /b 1
)

cd /d "%SCRIPT_DIR%"
"%PYTHON_EXE%" -m app.telegram.bot
exit /b %ERRORLEVEL%
