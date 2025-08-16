# Development Scripts for Gmail Automation
# PowerShell script for running tests and linting

param(
    [string]$Action = "help"
)

function Show-Help {
    Write-Host "Gmail Automation Development Commands"
    Write-Host "Usage: .\dev.ps1 [action]"
    Write-Host ""
    Write-Host "Actions:"
    Write-Host "  test       - Run all tests"
    Write-Host "  test-cov   - Run tests with coverage report"
    Write-Host "  lint       - Run flake8 linting"
    Write-Host "  format     - Format code with black"
    Write-Host "  format-check - Check if code needs formatting"
    Write-Host "  mypy       - Run mypy type checking"
    Write-Host "  all        - Run all checks (lint, format-check, mypy, test)"
    Write-Host "  install    - Install development dependencies"
    Write-Host "  clean      - Clean up cache and temporary files"
}

function Install-Dependencies {
    Write-Host "Installing dependencies..."
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
}

function Invoke-Tests {
    Write-Host "Running tests..."
    python -m pytest
}

function Invoke-TestsWithCoverage {
    Write-Host "Running tests with coverage..."
    python -m pytest --cov=src/gmail_automation --cov-report=term-missing
}

function Invoke-Lint {
    Write-Host "Running flake8 linting..."
    python -m flake8 src/ tests/ main.py
}

function Format-Code {
    Write-Host "Formatting code with black..."
    python -m black src/ tests/ main.py
}

function Test-CodeFormat {
    Write-Host "Checking code formatting..."
    python -m black --check --diff src/ tests/ main.py
}

function Invoke-MyPy {
    Write-Host "Running mypy type checking..."
    python -m mypy src/ main.py
}

function Invoke-AllChecks {
    Write-Host "Running all checks..."
    Invoke-Lint
    Test-CodeFormat
    Invoke-MyPy
    Invoke-Tests
}

function Clear-ProjectFiles {
    Write-Host "Cleaning cache and temporary files..."
    if (Test-Path ".pytest_cache") { Remove-Item -Recurse -Force ".pytest_cache" }
    if (Test-Path "htmlcov") { Remove-Item -Recurse -Force "htmlcov" }
    if (Test-Path "coverage.xml") { Remove-Item -Force "coverage.xml" }
    if (Test-Path ".coverage") { Remove-Item -Force ".coverage" }
    if (Test-Path ".mypy_cache") { Remove-Item -Recurse -Force ".mypy_cache" }
    Get-ChildItem -Recurse -Name "__pycache__" | ForEach-Object { Remove-Item -Recurse -Force $_ }
    Get-ChildItem -Recurse -Name "*.pyc" | ForEach-Object { Remove-Item -Force $_ }
    Write-Host "Cleanup complete."
}

switch ($Action.ToLower()) {
    "help" { Show-Help }
    "test" { Invoke-Tests }
    "test-cov" { Invoke-TestsWithCoverage }
    "lint" { Invoke-Lint }
    "format" { Format-Code }
    "format-check" { Test-CodeFormat }
    "mypy" { Invoke-MyPy }
    "all" { Invoke-AllChecks }
    "install" { Install-Dependencies }
    "clean" { Clear-ProjectFiles }
    default {
        Write-Host "Unknown action: $Action"
        Show-Help
    }
}
