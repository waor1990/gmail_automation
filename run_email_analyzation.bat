@echo off
setlocal enabledelayedexpansion

REM Ensure working directory is repo root (this .bat resides here)
pushd "%~dp0"

REM Prefer venv Python if available
set "_VENV_PY=.venv\Scripts\python.exe"
if exist "%_VENV_PY%" (
    set "_PY=%_VENV_PY%"
) else (
    set "_PY=python"
)

REM Execute analyzer inside scripts/
"%_PY%" "scripts\analyze_email_config.py" %*
set "code=%ERRORLEVEL%"

popd
endlocal & exit /b %code%