@echo off
REM Simple batch file to activate the virtual environment
echo Activating Gmail Automation virtual environment...

if not exist ".venv" (
    echo ERROR: Virtual environment not found. Run setup_and_help.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
echo SUCCESS: Virtual environment activated!
echo You can now run: python main.py --help
cmd /k
