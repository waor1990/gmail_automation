@echo off

:: Exit if we're already in a virtual environment
if not "%VIRTUAL_ENV%"=="" (
    echo Already in a virtual environment: %VIRTUAL_ENV%
    goto :eof
)

:: Ensure the project virtual environment exists and is set up
if not exist .venv\Scripts\activate.bat (
    echo [info] Setting up virtual environment and dependencies...
    call scripts\setup.cmd || goto :eof
)
if not exist .venv\Scripts\activate.bat (
    echo [error] Activation script not found. Setup may have failed.
    goto :eof
)

:: Detect shell and activate appropriately
set "SHELL_NAME=%SHELL%"

:: Git Bash uses SHELL env var that includes 'bash'
echo %SHELL_NAME% | findstr /I "bash" >nul
if %errorlevel%==0 (
    echo Detected Git Bash.
    bash --login -c "source .venv/Scripts/activate && export PS1='(.venv) \w \$ ' && exec bash"
    goto :eof
)

:: PowerShell (from VSCode or Windows Terminal)
echo %ComSpec% | findstr /I "powershell" >nul
if %errorlevel%==0 (
    echo Detected PowerShell.
    start powershell -NoExit -Command ". .venv\\Scripts\\Activate.ps1; function prompt { '(.venv) ' + (Get-Location) + '> ' }"
    goto :eof
)

:: Default to Command Prompt
if exist .venv\\Scripts\\activate.bat (
    echo Activating in new Command Prompt window...
    start cmd /k ".venv\\Scripts\\activate.bat && set PROMPT=(.venv) $P$G"
) else (
    echo Activation script not found.
)

goto :eof
