@echo off
setlocal

REM Open a new Command Prompt with the repository venv activated.
REM Creates the venv via the setup script if it doesn't exist.

set "REPO_ROOT=%~dp0.."
set "ACTIVATE=%REPO_ROOT%\.venv\Scripts\activate.bat"

if not exist "%ACTIVATE%" (
  echo [info] Virtual environment not found. Creating it now...
  where py >NUL 2>&1 && (
    py -m scripts.setup || goto :error
  ) || (
    python -m scripts.setup || goto :error
  )
)

if not exist "%ACTIVATE%" (
  echo [error] Activate script not found at: "%ACTIVATE%"
  echo        Make sure the venv exists and try again.
  exit /b 1
)

echo [ok] Launching new Command Prompt with venv activated...
start "gmail_automation venv" /D "%REPO_ROOT%" cmd /k ""%ACTIVATE%""
exit /b 0

:error
echo [error] Failed to create the virtual environment.
exit /b 1
