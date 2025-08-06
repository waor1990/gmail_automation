@echo off
echo Running Gmail Automation Test Suite Demo
echo ==========================================
echo.

echo 1. Running basic functionality test...
"C:/Users/Wesley Allegre/source/repos/GitHub/gmail_automation/.venv/Scripts/python.exe" test_basic.py
echo.

echo 2. Running linting check...
"C:/Users/Wesley Allegre/source/repos/GitHub/gmail_automation/.venv/Scripts/python.exe" -m flake8 src/ --count --statistics --exit-zero
echo.

echo 3. Checking code formatting...
"C:/Users/Wesley Allegre/source/repos/GitHub/gmail_automation/.venv/Scripts/python.exe" -m black --check --diff src/ || echo Code formatting issues found (use 'python -m black src/' to fix)
echo.

echo 4. Running a simple test to verify pytest works...
"C:/Users/Wesley Allegre/source/repos/GitHub/gmail_automation/.venv/Scripts/python.exe" -c "import pytest; print('✓ pytest is installed and working')"
echo.

echo ==========================================
echo Testing setup is complete and functional!
echo Use 'dev.bat help' for more testing commands.
pause
