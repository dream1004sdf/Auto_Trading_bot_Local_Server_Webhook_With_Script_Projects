# Bootstrap the portfolio demo in a Windows Python virtual environment.
# Run from a PowerShell terminal after reviewing this file:
#   powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1
# The script does not require admin rights and does not install into system Python.

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
        throw "Python launcher 'py' not found. Install Python 3.11 or 3.12, then rerun."
    }

    $selected = $null
    foreach ($version in @('3.12', '3.11')) {
        & py "-$version" -c "import sys; print(sys.version)" *> $null
        if ($LASTEXITCODE -eq 0) {
            $selected = $version
            break
        }
    }
    if (-not $selected) {
        Write-Host "Available Python installations:"
        & py -0p
        throw "No verified Python 3.11 / 3.12 interpreter found. Install a supported version before setup."
    }

    Write-Host "Using Python $selected (verified in GitHub Actions)"
    & py "-$selected" -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Unable to create virtual environment" }

    $venvPython = Join-Path $root '.venv\Scripts\python.exe'
    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }

    & $venvPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed" }

    & $venvPython -c "import sys, importlib.metadata; print('Python:', sys.version.split()[0]); print('Flask:', importlib.metadata.version('flask'))"
    if ($LASTEXITCODE -ne 0) { throw "Version verification failed" }

    & $venvPython -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "Test suite failed" }

    Write-Host "Setup completed. To start: .\.venv\Scripts\python.exe Server.py"
}
finally {
    Pop-Location
}
