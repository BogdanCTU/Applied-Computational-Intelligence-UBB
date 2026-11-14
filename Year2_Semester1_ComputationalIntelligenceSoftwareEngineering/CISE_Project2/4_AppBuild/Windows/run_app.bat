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

REM Check if Python virtual environment exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating Python virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo [WARNING] No local .venv found. Attempting to use system python...
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
streamlit run app.py

pause

