@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Usage:
REM   setup.cmd --cmd   -> open Cmd pre-activated
REM   setup.cmd --pwsh  -> open PowerShell (pwsh if available) pre-activated
REM   setup.cmd --bash  -> open Git Bash pre-activated
REM   setup.cmd         -> default to Cmd

REM Repo root (parent of this script), resolve to absolute with no trailing backslash
for %%i in ("%~dp0..") do set "ROOT=%%~fi"
set "ACTIVATE_BAT=%ROOT%\.venv\Scripts\activate.bat"
set "ACTIVATE_PS1=%ROOT%\.venv\Scripts\Activate.ps1"

REM Parse args for optional --rebuild flag (can be combined with shell flag)
set "REBUILD=0"
echo %* | findstr /I /C:"--rebuild" >nul && set "REBUILD=1"

REM If activator exists but appears broken (noop/too small), mark for rebuild
set "BROKEN=0"
if exist "%ACTIVATE_PS1%" (
  for %%A in ("%ACTIVATE_PS1%") do set "_SZ=%%~zA"
  if not defined _SZ set "_SZ=0"
  if !_SZ! LSS 16 set "BROKEN=1"
  if !BROKEN!==0 (
    findstr /I /C:"# noop" "%ACTIVATE_PS1%" >nul && set "BROKEN=1"
  )
)

REM Rebuild venv if requested or broken
if "%REBUILD%"=="1" (
  echo [warn] --rebuild requested; removing existing venv at "%ROOT%\.venv"
  rmdir /s /q "%ROOT%\.venv" 2>nul
)
if "%BROKEN%"=="1" (
  echo [warn] Detected broken activator; rebuilding venv at "%ROOT%\.venv"
  rmdir /s /q "%ROOT%\.venv" 2>nul
)

REM Ensure venv and deps
pushd "%ROOT%" >nul
py -m scripts.setup
if errorlevel 1 (
  echo [error] Environment setup failed. If you requested a rebuild, ensure no shells or processes are using "%ROOT%\.venv" and try again.
  exit /b 1
)
popd >nul

REM Exit if already inside a venv only when no shell was explicitly requested
if defined VIRTUAL_ENV (
  if /I not "%1"=="--bash" if /I not "%1"=="--pwsh" if /I not "%1"=="--cmd" (
    exit /b 0
  )
)

REM Verify activators
if not exist "%ACTIVATE_BAT%" (
  echo [error] %ACTIVATE_BAT% not found
  exit /b 1
)
if not exist "%ACTIVATE_PS1%" (
  echo [warn] %ACTIVATE_PS1% not found (PowerShell activation may fail)
)

REM Route
if /I "%1"=="--bash" goto :bash
if /I "%1"=="--pwsh" goto :pwsh
if /I "%1"=="--cmd"  goto :cmd
rem If running from Git Bash, prefer :bash as the default route
if defined MSYSTEM goto :bash
goto :cmd

:bash
rem Prefer Git Bash installed with Git for Windows
set "BASH_EXE="
rem Prefer the launcher which reliably opens a new window
if exist "%ProgramFiles%\Git\git-bash.exe" set "BASH_EXE=%ProgramFiles%\Git\git-bash.exe"
if not defined BASH_EXE if exist "%ProgramFiles(x86)%\Git\git-bash.exe" set "BASH_EXE=%ProgramFiles(x86)%\Git\git-bash.exe"
rem Fallbacks to bash.exe locations if launcher not found
if not defined BASH_EXE if exist "%ProgramFiles%\Git\bin\bash.exe" set "BASH_EXE=%ProgramFiles%\Git\bin\bash.exe"
if not defined BASH_EXE if exist "%ProgramFiles%\Git\usr\bin\bash.exe" set "BASH_EXE=%ProgramFiles%\Git\usr\bin\bash.exe"
if not defined BASH_EXE (
  rem Last resort: pick a bash from PATH that is under Git (avoid WSL/system32)
  for /f "usebackq delims=" %%B in (`where bash 2^>nul`) do (
    echo %%B | findstr /I "\\Git\\" >nul && (
      set "BASH_EXE=%%B"
      goto :have_bash
    )
  )
)
if not defined BASH_EXE (
  echo [error] Git Bash not found (expected Git\\git-bash.exe or Git\\bin\\bash.exe)
  exit /b 1
)
:have_bash
rem If running from Git Bash already (MSYSTEM), enter venv in current window
set "RUN_IN_PLACE=0"
if defined MSYSTEM set "RUN_IN_PLACE=1"
if "%RUN_IN_PLACE%"=="1" (
  "%BASH_EXE%" -l -i -c "cd \"$(cygpath -u \"%ROOT%\")\"; source .venv/Scripts/activate; exec bash -i"
) else (
  rem Prefer mintty if available to guarantee a new window
  set "MINTTY_EXE="
  if exist "%ProgramFiles%\Git\usr\bin\mintty.exe" set "MINTTY_EXE=%ProgramFiles%\Git\usr\bin\mintty.exe"
  if not defined MINTTY_EXE if exist "%ProgramFiles(x86)%\Git\usr\bin\mintty.exe" set "MINTTY_EXE=%ProgramFiles(x86)%\Git\usr\bin\mintty.exe"
  if defined MINTTY_EXE (
    start "" "%MINTTY_EXE%" -t "Git Bash (.venv)" /usr/bin/bash -l -i -c "cd \"$(cygpath -u \"%ROOT%\")\"; source .venv/Scripts/activate; exec bash -i"
  ) else (
    rem Fallback to bash.exe; convert path for cd to handle spaces
    start "" "%BASH_EXE%" -l -i -c "cd \"$(cygpath -u \"%ROOT%\")\"; source .venv/Scripts/activate; exec bash -i"
  )
)
exit /b 0

:pwsh
set "TMP_PS1=%TEMP%\enter_venv.ps1"
> "%TMP_PS1%" (
  echo Param(^[string^]$proj,^ [string^]$act^)
  echo Set-Location -LiteralPath $proj
  echo if ^(Test-Path -LiteralPath $act^) ^{ . "$act" ^}
  echo $ok = $env:VIRTUAL_ENV -and ^(Test-Path -LiteralPath $env:VIRTUAL_ENV^)
  echo if ^(-not $ok^) ^{
  echo 	$venv = Join-Path $proj '.venv'
  echo 	$scripts = Join-Path $venv 'Scripts'
  echo 	if ^(-not ^(Test-Path -LiteralPath $scripts^)^) ^{ Write-Error "Venv Scripts folder not found: $scripts"; return ^}
  echo 	$env:VIRTUAL_ENV = ^(Resolve-Path -LiteralPath $venv^).Path
  echo 	$env:PATH = "$scripts;" + $env:PATH
  echo 	function global:prompt ^{ "(.venv) " + ^(Get-Location^) + "> " ^}
  echo 	Write-Host "[fallback] Activated venv: $env:VIRTUAL_ENV"
  echo ^} else ^{
  echo 	Write-Host "[activator] Activated venv: $env:VIRTUAL_ENV"
  echo ^}
)
if exist "%ProgramFiles%\PowerShell\7\pwsh.exe" (
  start "" "%ProgramFiles%\PowerShell\7\pwsh.exe" -NoLogo -NoExit -NoProfile -ExecutionPolicy Bypass -File "%TMP_PS1%" "%ROOT%" "%ACTIVATE_PS1%"
) else (
  start "" "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoExit -ExecutionPolicy Bypass -NoProfile -File "%TMP_PS1%" "%ROOT%" "%ACTIVATE_PS1%"
)
exit /b 0

:cmd
if not exist "%ACTIVATE_BAT%" (
  echo [error] Could not find "%ACTIVATE_BAT%"
  exit /b 1
)
rem Create a small helper so quoting with spaces is reliable
set "TMP_CMD=%TEMP%\enter_venv.cmd"
>  "%TMP_CMD%" echo @echo off
>> "%TMP_CMD%" echo title ^(.venv^) %ROOT%
>> "%TMP_CMD%" echo cd /D "%ROOT%"
>> "%TMP_CMD%" echo call "%ACTIVATE_BAT%"
rem Open a new Command Prompt and run the helper, keeping the window open
start "" "%ComSpec%" /K "%TMP_CMD%"
exit /b 0
:end
