# Nilavu one-line installer for Windows PowerShell: reuse the current checkout
# (or clone into .\nilavu), set up .venv, install, first run.
# Quick start (run from the directory where you want .\nilavu created):
#   irm https://raw.githubusercontent.com/jonathan-16bit/nilavu/main/install.ps1 | iex
# Manual fallback instead (run from inside the checkout; the script reuses it):
#   git clone https://github.com/jonathan-16bit/nilavu.git
#   cd nilavu
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
$ErrorActionPreference = 'Stop'

$RepoUrl = 'https://github.com/jonathan-16bit/nilavu.git'
$TargetDir = '.\nilavu'
$ProjectDir = ''

function Fail([string]$Message) {
    [Console]::Error.WriteLine("Error: $Message")
    exit 1
}

function Test-Origin([string]$Dir) {
    $originUrl = git -C $Dir remote get-url origin 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $originUrl) {
        Fail "No 'origin' remote in $Dir. Clone $RepoUrl first, then re-run."
    }
    if ($originUrl -notmatch 'nilavu(\.git)?/?$') {
        Fail "Unexpected origin '$originUrl' in $Dir; expected a nilavu checkout."
    }
    Write-Host "Remote origin: $originUrl"
}

function Test-Clean([string]$Dir) {
    $porcelain = git -C $Dir status --porcelain
    if ($porcelain) {
        Fail "$Dir has uncommitted changes. Commit, stash, or discard them, then re-run."
    }
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

# Reuse the current checkout when run from inside one, so the manual fallback
# (clone, cd nilavu, run install.ps1) does not nest a nilavu\nilavu checkout.
if ((Test-Path '.\.git') -and (Test-Path '.\pyproject.toml') -and (Test-Path '.\src\nilavu')) {
    Write-Host 'Reusing current checkout (.) ...'
    $ProjectDir = '.'
} elseif (Test-Path "$TargetDir\.git") {
    Write-Host "Found existing checkout at $TargetDir, updating it..."
    $ProjectDir = $TargetDir
} elseif (Test-Path $TargetDir) {
    Fail "$TargetDir already exists and is not a git checkout. Rename or remove it, then re-run this script."
} else {
    Write-Host "Cloning Nilavu into $TargetDir ..."
    git clone $RepoUrl $TargetDir
    if ($LASTEXITCODE -ne 0) { Fail 'git clone failed. Check your network connection, then re-run.' }
    $ProjectDir = $TargetDir
}

Test-Origin $ProjectDir
Test-Clean $ProjectDir
git -C $ProjectDir pull --ff-only
if ($LASTEXITCODE -ne 0) { Fail "Could not fast-forward $ProjectDir. Resolve any diverged history, then re-run." }

Set-Location $ProjectDir

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
