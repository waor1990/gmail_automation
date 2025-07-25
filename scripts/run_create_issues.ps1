# PowerShell script to reliably execute a bash script from VS Code tasks
$ErrorActionPreference = "Stop"

# Define paths
$scriptPath = $MyInvocation.MyCommand.Path
$workspaceRoot = Split-Path -Path $scriptPath -Parent | Split-Path -Parent
$bashScriptPath = Join-Path -Path $workspaceRoot -ChildPath "scripts\create_issues.sh"
$gitBashPath = "C:\Program Files\Git\bin\bash.exe"

# Check if Git Bash exists
if (-not (Test-Path -Path $gitBashPath)) {
    Write-Error "Git Bash not found at $gitBashPath. Please ensure Git for Windows is installed in the default location."
    exit 1
}

# Check if the target script exists
if (-not (Test-Path -Path $bashScriptPath)) {
    Write-Error "Target script not found at $bashScriptPath."
    exit 1
}

# Add workspace root to PATH so jq.exe can be found
$env:PATH = "$workspaceRoot;$env:PATH"

# Execute the script
Write-Host "Executing '$bashScriptPath' with Git Bash..."
& $gitBashPath -c "cd '$workspaceRoot' && PATH='$workspaceRoot':`$PATH scripts/create_issues.sh"

Write-Host "Script execution finished."
