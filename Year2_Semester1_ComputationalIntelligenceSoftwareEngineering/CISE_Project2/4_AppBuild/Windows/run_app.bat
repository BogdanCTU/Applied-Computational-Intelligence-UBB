@echo off
REM ==============================================================================
REM CISE Project 2 — C# Defect Predictor Launcher
REM Babeș-Bolyai University — Applied Computational Intelligence
REM ==============================================================================

cd /d "%~dp0\..\.."

echo ==============================================================================
echo Launching C# Defect Predictor (Streamlit Workbench)...
echo Repository Root: %CD%
echo ==============================================================================

REM Locate Python executable (prefer local virtual environment)
set "PYTHON_CMD="
if exist ".venv\Scripts\python.exe" (
    echo Activating Python virtual environment...
    call .venv\Scripts\activate.bat
    set "PYTHON_CMD=.venv\Scripts\python.exe"
) else (
    echo [WARNING] No local .venv found. Using system python...
    set "PYTHON_CMD=python"
)

REM Build Roslyn Analyzer if DLL is missing
if not exist "2_SourceCode\RoslynAnalyzer\bin\Release\net9.0\RoslynAnalyzer.dll" (
    echo [INFO] RoslynAnalyzer binary not found. Building via dotnet...
    dotnet build 2_SourceCode\RoslynAnalyzer\RoslynAnalyzer.csproj -c Release
    if errorlevel 1 (
        echo [ERROR] Failed to compile Roslyn Analyzer. Please ensure .NET 9 SDK is installed.
        pause
        exit /b 1
    )
)

echo Starting Streamlit server...
"%PYTHON_CMD%" -m streamlit run app.py

if errorlevel 1 (
    echo [ERROR] Application exited with error code %errorlevel%.
)

pause

