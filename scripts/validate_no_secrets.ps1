# Script to validate that no sensitive files are present in the repository
# This can be run before commits to ensure sensitive data isn't accidentally included

Write-Host "🔍 Validating repository for sensitive files..." -ForegroundColor Cyan
Write-Host ""

# Define critical sensitive file patterns that should block commits
$criticalPatterns = @(
    "client_secret_*.json",
    "*token*.json",
    "gmail_config-final.json", 
    "last_run.txt",
    "processed_email_ids.txt"
)

# Define patterns that are OK in working directory if gitignored
$warningPatterns = @(
    "*.log"
)

# Check working directory for critical sensitive files that are NOT gitignored
Write-Host "📁 Checking working directory..." -ForegroundColor Cyan
$foundSensitive = $false

foreach ($pattern in $criticalPatterns) {
    $files = Get-ChildItem -Path . -Name $pattern -Recurse -ErrorAction SilentlyContinue | Where-Object { $_ -notlike ".git*" }
    if ($files) {
        # Check if these files are actually ignored by git
        $unignoredFiles = @()
        foreach ($file in $files) {
            $relativePath = $file -replace '^\.\\', './'
            $checkResult = & git check-ignore $relativePath 2>$null
            if ($LASTEXITCODE -ne 0) {
                $unignoredFiles += $file
            }
        }
        
        if ($unignoredFiles.Count -gt 0) {
            Write-Host "❌ Found untracked sensitive files matching pattern '$pattern':" -ForegroundColor Red
            $unignoredFiles | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
            $foundSensitive = $true
        }
    }
}

# Check for warning patterns and show if they exist (but verify they're gitignored)
foreach ($pattern in $warningPatterns) {
    $files = Get-ChildItem -Path . -Name $pattern -Recurse -ErrorAction SilentlyContinue | Where-Object { $_ -notlike ".git*" }
    if ($files) {
        # Check if any are NOT gitignored
        $unignoredFiles = @()
        foreach ($file in $files) {
            $relativePath = $file -replace '^\.\\', './'
            $checkResult = & git check-ignore $relativePath 2>$null
            if ($LASTEXITCODE -ne 0) {
                $unignoredFiles += $file
            }
        }
        
        if ($unignoredFiles.Count -gt 0) {
            Write-Host "❌ Found untracked files matching pattern '$pattern':" -ForegroundColor Red
            $unignoredFiles | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
            $foundSensitive = $true
        }
        else {
            Write-Host "✅ Found files matching pattern '$pattern' but they are properly gitignored" -ForegroundColor Green
        }
    }
}

# Check staged files
Write-Host ""
Write-Host "📋 Checking staged files..." -ForegroundColor Cyan
try {
    $stagedFiles = git diff --cached --name-only 2>$null
    if ($stagedFiles) {
        $stagedSensitive = $false
        foreach ($file in $stagedFiles) {
            foreach ($pattern in $sensitivePatterns) {
                # Convert shell glob to PowerShell wildcard
                if ($file -like $pattern) {
                    Write-Host "❌ Staged file matches sensitive pattern '$pattern': $file" -ForegroundColor Red
                    $stagedSensitive = $true
                    $foundSensitive = $true
                }
            }
        }
        
        if (-not $stagedSensitive) {
            Write-Host "✅ No sensitive files in staging area" -ForegroundColor Green
        }
    }
    else {
        Write-Host "ℹ️  No files currently staged" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "⚠️  Could not check staged files (not a git repository?)" -ForegroundColor Yellow
}

# Check Git history for sensitive files (basic check)
Write-Host ""
Write-Host "🕒 Checking recent Git history..." -ForegroundColor Cyan
try {
    $historyFiles = git log --name-only --pretty=format: -10 2>$null | Where-Object { $_ -ne "" } | Sort-Object -Unique
    
    if ($historyFiles) {
        $historySensitive = $false
        foreach ($file in $historyFiles) {
            foreach ($pattern in $sensitivePatterns) {
                if ($file -like $pattern) {
                    Write-Host "❌ Recent history contains sensitive file: $file" -ForegroundColor Red
                    $historySensitive = $true
                    $foundSensitive = $true
                }
            }
        }
        
        if (-not $historySensitive) {
            Write-Host "✅ No sensitive files found in recent history" -ForegroundColor Green
        }
    }
}
catch {
    Write-Host "⚠️  Could not check git history" -ForegroundColor Yellow
}

# Final result
Write-Host ""
Write-Host "=================================="
if ($foundSensitive) {
    Write-Host "❌ VALIDATION FAILED: Sensitive files detected!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Recommended actions:" -ForegroundColor Yellow
    Write-Host "1. Remove sensitive files from working directory" -ForegroundColor White
    Write-Host "2. Unstage any sensitive files: git reset HEAD <file>" -ForegroundColor White
    Write-Host "3. Add patterns to .gitignore if needed" -ForegroundColor White
    Write-Host "4. If files are in history, run the cleanup script" -ForegroundColor White
    Write-Host ""
    exit 1
}
else {
    Write-Host "✅ VALIDATION PASSED: No sensitive files detected" -ForegroundColor Green
    Write-Host ""
    Write-Host "Repository appears clean of sensitive data." -ForegroundColor Cyan
    exit 0
}
