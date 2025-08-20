@echo off
REM Simple batch file to activate the virtual environment
echo Activating Gmail Automation virtual environment...

if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found. Run 'python -m venv .venv' first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
echo SUCCESS: Virtual environment activated!
echo You can now run: python gmail_automation.py --help
cmd /k
