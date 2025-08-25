# Script to remove sensitive credentials from Git history
# This script uses git filter-repo to rewrite Git history and remove sensitive files

Write-Host "🚨 WARNING: This script will rewrite Git history!" -ForegroundColor Red
Write-Host "Make sure you have a backup of your repository before proceeding." -ForegroundColor Yellow
Write-Host ""

# Check if git filter-repo is available
git filter-repo --help 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ git filter-repo is not installed." -ForegroundColor Red
    Write-Host "Install it with: pip install git-filter-repo" -ForegroundColor Yellow
    Write-Host "Or download from: https://github.com/newren/git-filter-repo/" -ForegroundColor Yellow
    exit 1
}

# Define sensitive files to remove from history
$sensitiveFiles = @(
    "client_secret_*.json",
    "gmail-python-email.json",
    "data/gmail-python-email.json",
    "gmail_config-final.json",
    "config/gmail_config-final.json",
    "*.log",
    "logs/*.log",
    "gmail_automation.log",
    "gmail_automation_debug*.log",
    "last_run.txt",
    "data/last_run.txt",
    "processed_email_ids.txt",
    "data/processed_email_ids.txt"
)

Write-Host "📋 Files/patterns that will be removed from Git history:" -ForegroundColor Cyan
$sensitiveFiles | ForEach-Object { Write-Host "  - $_" }
Write-Host ""

$confirmation = Read-Host "Do you want to proceed? This action cannot be undone! (yes/no)"
if ($confirmation -ne "yes") {
    Write-Host "❌ Operation cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host "🔄 Creating backup branch..." -ForegroundColor Green
git branch backup-before-cleanup 2>&1

Write-Host "🧹 Removing sensitive files from Git history..." -ForegroundColor Green

# Create a temporary file with patterns to remove
$tempFile = New-TemporaryFile
$sensitiveFiles | Out-File -FilePath $tempFile.FullName -Encoding utf8

try {
    # Use git filter-repo to remove the files
    foreach ($pattern in $sensitiveFiles) {
        Write-Host "Removing pattern: $pattern" -ForegroundColor Yellow
        git filter-repo --path-glob "$pattern" --invert-paths --force
        if ($LASTEXITCODE -ne 0) {
            Write-Host "⚠️  Warning: Could not remove pattern $pattern (may not exist in history)" -ForegroundColor Yellow
        }
    }

    Write-Host "✅ Git history cleaned successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 Repository statistics:" -ForegroundColor Cyan

    # Show repository size reduction
    $repoSize = (Get-ChildItem .git -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Host "Repository size: $([math]::Round($repoSize, 2)) MB" -ForegroundColor White

    Write-Host ""
    Write-Host "🔄 Next steps:" -ForegroundColor Green
    Write-Host "1. Verify the cleanup with: git log --name-only" -ForegroundColor White
    Write-Host "2. Force push to remote (if needed): git push --force-with-lease origin main" -ForegroundColor White
    Write-Host "3. Inform collaborators to re-clone the repository" -ForegroundColor White
    Write-Host "4. Delete the backup branch when satisfied: git branch -D backup-before-cleanup" -ForegroundColor White

}
catch {
    Write-Host "❌ Error during cleanup: $_" -ForegroundColor Red
    Write-Host "You can restore from backup with: git reset --hard backup-before-cleanup" -ForegroundColor Yellow
}
finally {
    Remove-Item $tempFile.FullName -ErrorAction SilentlyContinue
}
