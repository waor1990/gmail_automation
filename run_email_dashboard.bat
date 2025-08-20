@echo off
setlocal enabledelayedexpansion

pushd "%~dp0"

set "_VENV_PY=.venv\Scripts\python.exe"
if exist "%_VENV_PY%" (
    set "_PY=%_VENV_PY%"
) else (
    set "_PY=python"
)

echo ==========================================
echo Gmail Config - Dashboard and Reports
echo ==========================================
echo [1] Generate BOTH reports (ESAQ_Report.txt and email_differences_by_label.json) and exit
echo [2] Generate ONLY ESAQ_Report.txt and exit
echo [3] Generate ONLY email_differences_by_label.json and exit
echo [4] Launch Dash Dashboard (no reports pre-generated)
echo ==========================================
choice /C 1234 /N /M "Select 1-4: "

if errorlevel 4 goto RUN_DASH
if errorlevel 3 goto RUN_DIFF
if errorlevel 2 goto RUN_ESAQ
if errorlevel 1 goto RUN_ALL

:RUN_ALL
"%_PY%" "scripts\dashboard\reports.py" --report all
set code=%ERRORLEVEL%
goto END

:RUN_ESAQ
"%_PY%" "scripts\dashboard\reports.py" --report esaq
set code=%ERRORLEVEL%
goto END

:RUN_DIFF
"%_PY%" "scripts\dashboard\reports.py" --report diff
set code=%ERRORLEVEL%
goto END

:RUN_DASH
"%_PY%" -m scripts.dashboard.app
set code=%ERRORLEVEL%
goto END

:END
popd
endlocal & exit /b %code%
