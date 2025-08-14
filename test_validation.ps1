# Simple PowerShell validation test
Write-Host "Testing PowerShell validation logic..." -ForegroundColor Cyan

# Test log files
$logFiles = Get-ChildItem -Path . -Name "*.log" -Recurse -ErrorAction SilentlyContinue | Where-Object { $_ -notlike ".git*" }
if ($logFiles) {
    Write-Host "Found log files:" -ForegroundColor Yellow
    foreach ($file in $logFiles) {
        Write-Host "  Checking: $file" -ForegroundColor Gray
        $result = & git check-ignore $file 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ $file (properly gitignored)" -ForegroundColor Green
        }
        else {
            Write-Host "  ❌ $file (NOT gitignored)" -ForegroundColor Red
        }
    }
}
else {
    Write-Host "No log files found" -ForegroundColor Green
}

Write-Host "Test completed." -ForegroundColor Cyan
