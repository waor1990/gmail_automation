@echo off
setlocal

REM Run scripts\enter_env.cmd if present; fallback to enter_venv.cmd
set "SCRIPT_DIR=%~dp0scripts"
set "TARGET=%SCRIPT_DIR%\enter_env.cmd"

if exist "%TARGET%" (
  call "%TARGET%"
  exit /b %ERRORLEVEL%
)

set "FALLBACK=%SCRIPT_DIR%\enter_venv.cmd"
if exist "%FALLBACK%" (
  echo [info] scripts\enter_env.cmd not found; using enter_venv.cmd
  call "%FALLBACK%"
  exit /b %ERRORLEVEL%
)

echo [error] Neither scripts\enter_env.cmd nor scripts\enter_venv.cmd found.
exit /b 1
