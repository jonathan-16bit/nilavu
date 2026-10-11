# Nilavu one-line installer for Windows PowerShell: clone (into .\nilavu), set up .venv, install, first run.
# Quick start (run from the directory where you want .\nilavu created):
#   irm https://raw.githubusercontent.com/jonathan-16bit/nilavu/main/install.ps1 | iex
# Manual fallback instead:
#   git clone https://github.com/jonathan-16bit/nilavu.git
#   cd nilavu
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
$ErrorActionPreference = 'Stop'

$RepoUrl = 'https://github.com/jonathan-16bit/nilavu.git'
$TargetDir = '.\nilavu'

function Fail([string]$Message) {
    Write-Error $Message
    exit 1
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Fail 'git is not installed. Install Git for Windows, then re-run this script.'
}

# Prefer the Python launcher (py -3), fall back to python/python3 on PATH.
$PythonLaunchers = @(
    @{ Exe = 'py'; Args = @('-3') },
    @{ Exe = 'python'; Args = @() },
    @{ Exe = 'python3'; Args = @() }
)
$PythonExe = $null
$PythonArgs = @()
foreach ($launcher in $PythonLaunchers) {
    try {
        & $launcher.Exe @($launcher.Args) --version 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $PythonExe = $launcher.Exe
            $PythonArgs = $launcher.Args
            break
        }
    } catch {
        continue
    }
}
if (-not $PythonExe) {
    Fail 'Python is not installed. Install Python 3.11 or newer (python.org), then re-run this script.'
}

# Enforce the same floor as pyproject.toml (requires-python >= 3.11).
& $PythonExe @PythonArgs -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'
if ($LASTEXITCODE -ne 0) {
    & $PythonExe @PythonArgs --version
    Fail 'Python 3.11+ is required. Update Python, then re-run this script.'
}

# Clone into the current directory (.\nilavu), or reuse an existing checkout.
if ((Test-Path "$TargetDir\.git")) {
    Write-Host "Found existing checkout at $TargetDir, updating it..."
    git -C $TargetDir pull --ff-only
    if ($LASTEXITCODE -ne 0) { Fail "Could not update $TargetDir. Resolve any local changes, then re-run." }
} elseif (Test-Path $TargetDir) {
    Fail "$TargetDir already exists and is not a git checkout. Rename or remove it, then re-run this script."
} else {
    Write-Host "Cloning Nilavu into $TargetDir ..."
    git clone $RepoUrl $TargetDir
    if ($LASTEXITCODE -ne 0) { Fail 'git clone failed. Check your network connection, then re-run.' }
}

Set-Location $TargetDir

$VenvPython = '.\.venv\Scripts\python.exe'
$GameExe = '.\.venv\Scripts\nilavu.exe'

# Same steps as the README manual install, just automated.
if (-not (Test-Path $VenvPython)) {
    Write-Host 'Creating virtual environment (.venv) ...'
    & $PythonExe @PythonArgs -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Fail "Could not create .venv. Reinstall Python with the 'py launcher' option, then re-run."
    }
} else {
    Write-Host 'Reusing existing virtual environment (.venv) ...'
}

Write-Host 'Installing Nilavu dependencies ...'
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { Fail 'pip upgrade failed. Check your network connection, then re-run.' }
& $VenvPython -m pip install .
if ($LASTEXITCODE -ne 0) { Fail 'pip install failed. Check the error above, then re-run.' }

Write-Host 'Starting Nilavu for the first time ...'
if (Test-Path $GameExe) {
    & $GameExe --game --seed fern
} else {
    & $VenvPython -m nilavu --game --seed fern
}
