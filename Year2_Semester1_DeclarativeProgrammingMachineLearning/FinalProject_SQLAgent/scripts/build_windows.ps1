# ==============================================================================
# Windows Build Script: Report SQL Agent (.exe Standalone Distribution)
# ==============================================================================
# Usage (run from project root in PowerShell):
#   powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
# ==============================================================================

$ErrorActionPreference = "Stop"

$ProjectRoot = (Get-Item $PSScriptRoot).Parent.FullName
Set-Location $ProjectRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Building Report SQL Agent for Windows" -ForegroundColor Cyan
Write-Host " Project root: $ProjectRoot" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Locate Python 3.13
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$VenvPyInstaller = Join-Path $ProjectRoot ".venv\Scripts\pyinstaller.exe"
$VenvPytest = Join-Path $ProjectRoot ".venv\Scripts\pytest.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[1/4] Virtual environment not found. Checking system Python 3.13..." -ForegroundColor Yellow
    $SystemPython = Get-Command "py" -ErrorAction SilentlyContinue
    if ($SystemPython) {
        Write-Host "Creating .venv using py -3.13..."
        py -3.13 -m venv .venv
    } else {
        $PythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
        if ($PythonCmd) {
            Write-Host "Creating .venv using python..."
            python -m venv .venv
        } else {
            Write-Error "Python 3.13 is required but was not found in PATH."
            exit 1
        }
    }
    Write-Host "Installing dependencies..."
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r requirements.txt
}

Write-Host "[1/4] Verifying runtime environment and database integrity..." -ForegroundColor Green
& $VenvPython scripts\verify_environment.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Environment verification failed."
    exit 1
}

Write-Host "[2/4] Running automated tests..." -ForegroundColor Green
& $VenvPytest tests\ -q
if ($LASTEXITCODE -ne 0) {
    Write-Error "Automated test suite failed."
    exit 1
}

Write-Host "[3/4] Building Windows binary with PyInstaller..." -ForegroundColor Green
& $VenvPyInstaller --clean --noconfirm ReportSQLAgent.spec
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller build failed."
    exit 1
}

$ExePath = Join-Path $ProjectRoot "dist\ReportSQLAgent\ReportSQLAgent.exe"
Write-Host "[4/4] Validating build artifacts..." -ForegroundColor Green
if (Test-Path $ExePath) {
    Write-Host ""
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host " BUILD SUCCESSFUL!" -ForegroundColor Green
    Write-Host " Windows Executable: $ExePath" -ForegroundColor Green
    Write-Host " Run with: .\dist\ReportSQLAgent\ReportSQLAgent.exe" -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
} else {
    Write-Error "Build finished but $ExePath was not found."
    exit 1
}
