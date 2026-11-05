# ==============================================================================
# Windows Build Script: Report SQL Agent (.exe Standalone Distribution)
# ==============================================================================
# Usage (run from project root in PowerShell):
#   .\scripts\build_windows.ps1
#
# If script execution is restricted on your machine, enable it for this process:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\scripts\build_windows.ps1
# ==============================================================================

$ErrorActionPreference = "Stop"

# 1. Locate project root automatically
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ScriptDir) {
    $ScriptDir = $PSScriptRoot
}
$ProjectRoot = (Get-Item $ScriptDir).Parent.FullName
Set-Location $ProjectRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Building Report SQL Agent for Windows" -ForegroundColor Cyan
Write-Host " Project root: $ProjectRoot" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 2. Check virtual environment
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Error "Virtual environment not found at $VenvPython.`nPlease ensure the virtual environment (.venv) is created before building.`nExample: py -3.13 -m venv .venv; .venv\Scripts\pip install -r requirements.txt"
    exit 1
}

# 3. Verify / install build dependency (PyInstaller) in .venv
& $VenvPython -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller not found in .venv. Installing build dependency..." -ForegroundColor Yellow
    & $VenvPython -m pip install "pyinstaller>=6.10"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install PyInstaller build dependency."
        exit 1
    }
}

# 4. Verify environment and database integrity
Write-Host "[1/5] Verifying environment and database integrity..." -ForegroundColor Green
& $VenvPython scripts\verify_environment.py --build
if ($LASTEXITCODE -ne 0) {
    Write-Error "Environment verification failed."
    exit 1
}

# 5. Run automated tests before building
Write-Host "[2/5] Running automated tests (excluding live Ollama test)..." -ForegroundColor Green
& $VenvPython -m pytest tests\ -k "not test_live_local_ollama_integration_end_to_end" -q
if ($LASTEXITCODE -ne 0) {
    Write-Error "Automated test suite failed. Build aborted to prevent packaging broken code."
    exit 1
}

# 6. Clean previous build artifacts safely
Write-Host "[3/5] Cleaning previous build artifacts..." -ForegroundColor Green
$BuildDir = Join-Path $ProjectRoot "build"
$DistDir = Join-Path $ProjectRoot "dist"
if (Test-Path $BuildDir) {
    Remove-Item -Recurse -Force $BuildDir
}
if (Test-Path $DistDir) {
    Remove-Item -Recurse -Force $DistDir
}

# 7. Package standalone Windows executable with PyInstaller
Write-Host "[4/5] Packaging Windows standalone application with PyInstaller..." -ForegroundColor Green
& $VenvPython -m PyInstaller --clean --noconfirm ReportSQLAgent.spec
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller packaging failed."
    exit 1
}

# 8. Validate build artifacts
$ExeDir = Join-Path $ProjectRoot "dist\ReportSQLAgent"
$ExePath = Join-Path $ExeDir "ReportSQLAgent.exe"

Write-Host "[5/5] Validating Windows build output..." -ForegroundColor Green
if (Test-Path $ExePath) {
    Write-Host ""
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host " BUILD SUCCESSFUL!" -ForegroundColor Green
    Write-Host " Output Directory:   $ExeDir" -ForegroundColor Green
    Write-Host " Windows Executable: $ExePath" -ForegroundColor Green
    Write-Host ""
    Write-Host " Run with:" -ForegroundColor Green
    Write-Host "   .\dist\ReportSQLAgent\ReportSQLAgent.exe" -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
} else {
    Write-Error "Build completed, but $ExePath was not found."
    exit 1
}
