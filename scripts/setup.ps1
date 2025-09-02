# Ensure the virtual environment is ready and enter it.
python -m scripts.setup $args

if ($env:VIRTUAL_ENV) {
    Write-Host "Already in a virtual environment: $env:VIRTUAL_ENV"
    return
}

$activate = ".venv\\Scripts\\Activate.ps1"
if (-not (Test-Path $activate)) {
    Write-Host "[error] Activation script not found. Setup may have failed."
    return
}

. $activate
function prompt { "(.venv) " + (Get-Location) + "> " }
