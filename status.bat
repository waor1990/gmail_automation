@echo off
REM Batch file to show gmail_automation.py help and setup instructions

echo ==========================================
echo Gmail Automation - Help and Setup Guide
echo ==========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo SETUP REQUIRED:
    echo 1. Install Python 3.8 or higher from https://python.org
    echo 2. Make sure Python is added to your system PATH
    echo.
    pause
    exit /b 1
)

echo Python version:
python --version
echo.

echo SETUP INSTRUCTIONS FOR GMAIL AUTOMATION:
echo ==========================================
echo.
echo 1. VIRTUAL ENVIRONMENT SETUP (REQUIRED):
echo    - Activate: activate_env.bat (if available)
echo    - If not available, set up environment:
echo       - Run: python -m venv .venv
echo       - Activate: .venv\Scripts\activate.bat
echo.
echo 2. INSTALL DEPENDENCIES:
echo    - With venv active, run: pip install -r requirements.txt
echo.
echo 3. CONFIGURE GMAIL API:
echo    - Place your Gmail API credentials in config\client_secret.json
echo    - Copy config\config-sample\gmail_config.sample.json to config\gmail_config-final.json
echo    - Edit gmail_config-final.json with your preferences
echo.
echo 4. FIRST RUN:
echo    - Run: python gmail_automation.py --help (to see all options)
echo    - Run: python gmail_automation.py (to start automation)
echo.

echo CHECKING CURRENT ENVIRONMENT:
echo ==========================================

REM Check if virtual environment exists
if exist ".venv" (
    echo SUCCESS: Virtual environment found at .venv\
) else (
    echo WARNING: Virtual environment not found - create with: python -m venv .venv
)

REM Check if virtual environment is active
if defined VIRTUAL_ENV (
    echo SUCCESS: Virtual environment is currently active
    echo Active environment: %VIRTUAL_ENV%
) else (
    echo WARNING: Virtual environment not active - activate with: .venv\Scripts\activate.bat
)

REM Check if dependencies are likely installed (check for google-api-python-client)
python -c "import googleapiclient" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo SUCCESS: Google API Python client appears to be installed
) else (
    echo WARNING: Dependencies not installed - run: pip install -r requirements.txt
)

REM Check for Gmail API credentials (client_secret_*)
setlocal enabledelayedexpansion
set found_cred=false
for %%f in ("config\client_secret_"*) do (
    if exist "%%~f" (
        set found_cred=true
        goto :CheckDone
    )
)
:CheckDone
if "!found_cred!"=="true" (
    echo SUCCESS: Gmail API credentials found
) else (
    echo WARNING: Gmail API credentials missing - place in config\client_secret.json
)

endlocal

REM Check if config file exists
if exist "config\gmail_config-final.json" (
    echo SUCCESS: Configuration file found
) else (
    echo WARNING: Configuration missing - copy and edit config\gmail_config.sample.json
)

echo.
echo HELP MENU FOR GMAIL AUTOMATION:
echo ==========================================
python gmail_automation.py --help 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Cannot run gmail_automation.py - check setup requirements above
    echo Try running the setup steps first, then run this script again.
)

echo.
echo ==========================================
echo For detailed setup instructions, see: docs\setup.md
echo For configuration examples, see: docs\configuration_examples.md
echo ==========================================
pause
