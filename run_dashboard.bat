@echo off
setlocal

rem Change to repo root (directory containing this script)
cd /d "%~dp0"

rem Ensure the virtual environment exists before attempting to activate it.
if not exist ".venv\Scripts\activate.bat" (
    echo [error] Virtual environment not found. Run scripts\setup.cmd first.
    exit /b 1
)

rem Activate the virtual environment and launch the dashboard.
call ".venv\Scripts\activate.bat"
python -m scripts.dashboard --launch --port 8051

exit /b %ERRORLEVEL%
