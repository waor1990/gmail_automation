# PowerShell setup script for Windows users
param(
    [string]$VenvDir = ".venv"
)

Write-Host "🚀 Setting up Gmail Automation environment..." -ForegroundColor Green

# Check if Python is available
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating virtual environment in $VenvDir..." -ForegroundColor Yellow
    python -m venv $VenvDir
    Write-Host "✅ Created virtual environment" -ForegroundColor Green
}

# Activate virtual environment
$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
if (Test-Path $ActivateScript) {
    & $ActivateScript
    Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Compile the main script to ensure it's valid
    Write-Host "🔍 Validating gmail_automation.py..." -ForegroundColor Yellow
    $process = Start-Process -FilePath "python" -ArgumentList "-m", "py_compile", "gmail_automation.py" -Wait -PassThru -NoNewWindow
    if ($process.ExitCode -eq 0) {
        Write-Host "✅ gmail_automation.py compiles successfully" -ForegroundColor Green
    }
    else {
        Write-Host "❌ gmail_automation.py has compilation errors" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ Setup complete!" -ForegroundColor Green
    Write-Host "To activate the environment in the future, run: $VenvDir\Scripts\Activate.ps1" -ForegroundColor Cyan
}
else {
    Write-Host "❌ Failed to find activation script" -ForegroundColor Red
    exit 1
}
