@echo off
setlocal

REM Determine repository root (folder of this script)
set "REPO_ROOT=%~dp0"
set "VENV_DIR=%REPO_ROOT%.venv"
set "ACTIVATE_CMD=%VENV_DIR%\Scripts\activate.bat"
set "ACTIVATE_PS=%VENV_DIR%\Scripts\Activate.ps1"

REM Ensure the virtual environment exists (create via setup if missing)
if not exist "%ACTIVATE_CMD%" (
  echo [info] Virtual environment not found. Creating it now...
  where py >NUL 2>&1 && (
    py -m scripts.setup || goto :venv_error
  ) || (
    python -m scripts.setup || goto :venv_error
  )
)

if not exist "%ACTIVATE_CMD%" (
  echo [error] Activate script not found at: "%ACTIVATE_CMD%"
  echo         Make sure the venv exists and try again.
  exit /b 1
)

REM If running inside VS Code's integrated terminal (cmd), activate in-place
if defined VSCODE_PID (
  echo [ok] Detected VS Code terminal. Activating here...
  endlocal & call "%ACTIVATE_CMD%"
  exit /b %ERRORLEVEL%
)
if /I "%TERM_PROGRAM%"=="vscode" (
  echo [ok] Detected VS Code terminal. Activating here...
  endlocal & call "%ACTIVATE_CMD%"
  exit /b %ERRORLEVEL%
)

REM Detect the caller shell by inspecting the parent of the cmd.exe running this script
REM Try pwsh first, then Windows PowerShell; if neither exists, skip detection silently
set "BATCH_PATH=%~f0"
set "PARENT_NAME="
where pwsh >NUL 2>&1 && (
  for /f "usebackq delims=" %%I in (`pwsh -NoProfile -ExecutionPolicy Bypass -Command "try { $bp = $env:BATCH_PATH; $me = Get-CimInstance Win32_Process -Filter 'Name=''cmd.exe''' | Where-Object { $_.CommandLine -like ('*' + $bp + '*') } | Select-Object -First 1; if ($me) { (Get-CimInstance Win32_Process -Filter ('ProcessId=' + $me.ParentProcessId)).Name } } catch { '' }"`) do set "PARENT_NAME=%%I"
) || (
  where powershell >NUL 2>&1 && (
    for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $bp = $env:BATCH_PATH; $me = Get-CimInstance Win32_Process -Filter 'Name=''cmd.exe''' | Where-Object { $_.CommandLine -like ('*' + $bp + '*') } | Select-Object -First 1; if ($me) { (Get-CimInstance Win32_Process -Filter ('ProcessId=' + $me.ParentProcessId)).Name } } catch { '' }"`) do set "PARENT_NAME=%%I"
  )
)

REM Normalize to lower-case (crude: compare case-insensitively with IF /I)

REM Case 1: Called from PowerShell (Windows PowerShell)
echo %PARENT_NAME% | findstr /I "powershell.exe" >NUL 2>&1
if %errorlevel%==0 (
  if exist "%ACTIVATE_PS%" (
    echo [ok] Launching new PowerShell with venv activated...
    start "gmail_automation venv" /D "%REPO_ROOT%" powershell -NoExit -ExecutionPolicy Bypass -NoLogo -Command "& '%ACTIVATE_PS%'"
    exit /b 0
  ) else (
    echo [warn] PowerShell activate script not found; falling back to cmd activation.
    goto :activate_cmd_here
  )
)

REM Case 2: Called from PowerShell (PowerShell 7+ / pwsh)
echo %PARENT_NAME% | findstr /I "pwsh.exe" >NUL 2>&1
if %errorlevel%==0 (
  if exist "%ACTIVATE_PS%" (
    echo [ok] Launching new PowerShell (pwsh) with venv activated...
    start "gmail_automation venv" /D "%REPO_ROOT%" pwsh -NoExit -ExecutionPolicy Bypass -NoLogo -Command "& '%ACTIVATE_PS%'"
    exit /b 0
  ) else (
    echo [warn] PowerShell activate script not found; falling back to cmd activation.
    goto :activate_cmd_here
  )
)

REM Case 3: Called from Git Bash / MSYS bash
echo %PARENT_NAME% | findstr /I "bash.exe" >NUL 2>&1
if %errorlevel%==0 (
  where bash >NUL 2>&1 && (
    echo [ok] Launching new Git Bash with venv activated...
    for /f "usebackq delims=" %%B in (`where bash`) do set "BASH_EXE=%%B" & goto :have_bash
    :have_bash
    if not defined BASH_EXE (
      echo [warn] Could not locate bash.exe on PATH; falling back to cmd.
      goto :activate_cmd_here
    )
    REM Use cygpath in bash to get a POSIX path for the repo root and activate
    start "gmail_automation venv" "%BASH_EXE%" -lc "cd \"$(cygpath '%REPO_ROOT%')\"; source .venv/Scripts/activate; exec bash -i"
    exit /b 0
  ) || (
    echo [warn] bash.exe not found on PATH; falling back to cmd.
    goto :activate_cmd_here
  )
)

REM Case 4: Called from cmd.exe (or unknown) — always open a new Command Prompt
:activate_cmd_here
REM Prefer the known-good helper which also ensures the venv exists
set "SCRIPT_DIR=%~dp0scripts"
set "FALLBACK=%SCRIPT_DIR%\enter_venv.cmd"
if exist "%FALLBACK%" (
  echo [ok] Opening Command Prompt via scripts\enter_venv.cmd...
  call "%FALLBACK%"
  exit /b %ERRORLEVEL%
)

echo [warn] scripts\enter_venv.cmd not found; trying direct START...
start "" /I /D "%REPO_ROOT%" "%ComSpec%" /k ""%ACTIVATE_CMD%""
if errorlevel 1 (
  echo [error] Failed to open new Command Prompt. You can manually run:
  echo        "%ACTIVATE_CMD%"
  exit /b 1
)
exit /b 0

:venv_error
echo [error] Failed to create the virtual environment.
exit /b 1
