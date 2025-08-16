@echo off
REM Gmail Automation Development Commands
REM Usage: dev.bat [action]

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="test" goto test
if "%1"=="test-cov" goto test-cov
if "%1"=="lint" goto lint
if "%1"=="format" goto format
if "%1"=="format-check" goto format-check
if "%1"=="mypy" goto mypy
if "%1"=="all" goto all
if "%1"=="install" goto install
if "%1"=="clean" goto clean

echo Unknown action: %1
goto help

:help
echo Gmail Automation Development Commands
echo Usage: dev.bat [action]
echo.
echo Actions:
echo   test       - Run all tests
echo   test-cov   - Run tests with coverage report
echo   lint       - Run flake8 linting
echo   format     - Format code with black
echo   format-check - Check if code needs formatting
echo   mypy       - Run mypy type checking
echo   all        - Run all checks (lint, format-check, mypy, test)
echo   install    - Install development dependencies
echo   clean      - Clean up cache and temporary files
goto end

:install
echo Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
goto end

:test
echo Running tests...
python -m pytest
goto end

:test-cov
echo Running tests with coverage...
python -m pytest --cov=src/gmail_automation --cov-report=term-missing
goto end

:lint
echo Running flake8 linting...
python -m flake8 src/ tests/ main.py
goto end

:format
echo Formatting code with black...
python -m black src/ tests/ main.py
goto end

:format-check
echo Checking code formatting...
python -m black --check --diff src/ tests/ main.py
goto end

:mypy
echo Running mypy type checking...
python -m mypy src/ main.py
goto end

:all
echo Running all checks...
call :lint
if errorlevel 1 goto end
call :format-check
if errorlevel 1 goto end
call :mypy
if errorlevel 1 goto end
call :test
goto end

:clean
echo Cleaning cache and temporary files...
if exist ".pytest_cache" rmdir /s /q ".pytest_cache"
if exist "htmlcov" rmdir /s /q "htmlcov"
if exist "coverage.xml" del /q "coverage.xml"
if exist ".coverage" del /q ".coverage"
if exist ".mypy_cache" rmdir /s /q ".mypy_cache"
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
for /r . %%f in (*.pyc) do @if exist "%%f" del /q "%%f"
echo Cleanup complete.
goto end

:end
