# Gmail Labels Extraction Script (PowerShell)
# 
# This script extracts Gmail labels and associated email addresses to generate
# a configuration file that can be used by the Gmail automation tool.
#
# Usage:
#   .\scripts\extract_gmail_labels.ps1 [-OutputFile "config\my_labels.json"] [-BatchSize 10] [-Verbose]

param(
    [string]$OutputFile = $null,
    [int]$BatchSize = 5,
    [switch]$Verbose = $false
)

# Get the script directory and project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

# Change to project root directory
Set-Location $ProjectRoot

Write-Host "Gmail Labels Extraction Script" -ForegroundColor Green
Write-Host "==============================" -ForegroundColor Green

# Check if virtual environment exists
$VenvPath = Join-Path $ProjectRoot ".venv"
if (Test-Path $VenvPath) {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    $ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
    if (Test-Path $ActivateScript) {
        & $ActivateScript
    }
    else {
        Write-Warning "Virtual environment found but activation script missing."
    }
}
else {
    Write-Warning "Virtual environment not found. Please run setup.ps1 first."
}

# Build the command
$Command = "python -m gmail_automation extract-labels"

if ($OutputFile) {
    $Command += " --output `"$OutputFile`""
}

if ($BatchSize -ne 5) {
    $Command += " --batch-size $BatchSize"
}

if ($Verbose) {
    $Command += " --verbose"
}

Write-Host "Running: $Command" -ForegroundColor Cyan

# Execute the command
try {
    Invoke-Expression $Command
    $ExitCode = $LASTEXITCODE
    
    if ($ExitCode -eq 0) {
        Write-Host "`nLabel extraction completed successfully!" -ForegroundColor Green
        if ($OutputFile) {
            Write-Host "Configuration saved to: $OutputFile" -ForegroundColor Green
        }
        else {
            Write-Host "Configuration saved to: config\gmail_labels_data.json" -ForegroundColor Green
        }
    }
    else {
        Write-Error "Label extraction failed with exit code: $ExitCode"
    }
}
catch {
    Write-Error "Error running the extraction script: $_"
}

Write-Host "`nPress any key to continue..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
