# ==============================================================================
# Windows Build Script: Report SQL Agent (.exe Standalone Distribution)
# Restructured Repository: Output directed to 6_Builds\Windows\
# ==============================================================================
# Usage (run from project root in PowerShell):
#   .\1_Source\scripts\build_windows.ps1
#
# If script execution is restricted on your machine, enable it for this process:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\1_Source\scripts\build_windows.ps1
# ==============================================================================

$ErrorActionPreference = "Stop"

# 1. Locate project root automatically
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ScriptDir) {
    $ScriptDir = $PSScriptRoot
}
$SourceDir = (Get-Item $ScriptDir).Parent.FullName
$ProjectRoot = (Get-Item $SourceDir).Parent.FullName
Set-Location $ProjectRoot

$BuildsDir = Join-Path $ProjectRoot "6_Builds"
$DistDir = Join-Path $BuildsDir "Windows"
$BuildLogsDir = Join-Path $BuildsDir "build_logs"
$BuildTmpDir = Join-Path $BuildsDir "build_tmp"

if (-not (Test-Path $BuildLogsDir)) {
    New-Item -ItemType Directory -Path $BuildLogsDir -Force | Out-Null
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Building Report SQL Agent for Windows" -ForegroundColor Cyan
Write-Host " Project root: $ProjectRoot" -ForegroundColor Cyan
Write-Host " Source dir:   $SourceDir" -ForegroundColor Cyan
Write-Host " Output dir:   $DistDir" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 2. Check virtual environment
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Error "Virtual environment not found at $VenvPython.`nPlease ensure the virtual environment (.venv) is created before building.`nExample: py -3.13 -m venv .venv; .venv\Scripts\pip install -r 1_Source\requirements.txt"
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
& $VenvPython (Join-Path $SourceDir "scripts\verify_environment.py") --build
if ($LASTEXITCODE -ne 0) {
    Write-Error "Environment verification failed."
    exit 1
}

# 5. Run automated tests before building (excluding live Ollama tests)
Write-Host "[2/5] Running automated tests (excluding live Ollama tests)..." -ForegroundColor Green
& $VenvPython -m pytest (Join-Path $SourceDir "tests\") -k "not test_live_local_ollama_integration_end_to_end and not test_13_live_ollama_qwen_reporting_workflow" -q
if ($LASTEXITCODE -ne 0) {
    Write-Error "Automated test suite failed. Build aborted to prevent packaging broken code."
    exit 1
}

# 6. Clean previous build artifacts safely
Write-Host "[3/5] Cleaning previous build artifacts..." -ForegroundColor Green
if (Test-Path $DistDir) {
    Remove-Item -Recurse -Force $DistDir
}
if (Test-Path $BuildTmpDir) {
    Remove-Item -Recurse -Force $BuildTmpDir
}

# 7. Package standalone Windows executable with PyInstaller
Write-Host "[4/5] Packaging Windows standalone application with PyInstaller..." -ForegroundColor Green
& $VenvPython -m PyInstaller --clean --noconfirm --distpath $DistDir --workpath $BuildTmpDir (Join-Path $ProjectRoot "ReportSQLAgent.spec")
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller packaging failed."
    exit 1
}

# 8. Validate build artifacts
$ExeDir = Join-Path $DistDir "ReportSQLAgent"
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
    Write-Host "   .\6_Builds\Windows\ReportSQLAgent\ReportSQLAgent.exe" -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
} else {
    Write-Error "Build completed, but $ExePath was not found."
    exit 1
}
