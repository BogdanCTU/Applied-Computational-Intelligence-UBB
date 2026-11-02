<#
.SYNOPSIS
    Builds the standalone Windows desktop executable for the Agent-OM Guided Replication Workbench.
.DESCRIPTION
    Packages `run_gui.py` and `src/` via PyInstaller (`--onedir`) into `agent_om_local/dist/AgentOM/AgentOM.exe`
    and compiles a top-level convenience launcher `agent_om_local/dist/AgentOM.exe`.
    Does NOT bundle PostgreSQL, Ollama, LLM weights, or database data directories.
#>
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    throw "Virtual environment Python not found at $PythonExe"
}

Write-Host "=== [1/3] Cleaning previous PyInstaller build/dist folders inside agent_om_local ==="
$BuildDir = Join-Path $ProjectRoot "build"
$DistDir  = Join-Path $ProjectRoot "dist"
if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }
if (Test-Path $DistDir)  { Remove-Item -Recurse -Force $DistDir }

Write-Host "=== [2/3] Running PyInstaller --onedir via agent_om.spec ==="
& $PythonExe -m PyInstaller --noconfirm --clean "agent_om.spec"
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE"
}

$MainExe = Join-Path $DistDir "AgentOM\AgentOM.exe"
if (-not (Test-Path $MainExe)) {
    throw "Expected packaged executable missing at $MainExe"
}

Write-Host "=== [3/3] Compiling top-level launcher dist\AgentOM.exe forwarding to dist\AgentOM\AgentOM.exe ==="
$LauncherCs = Join-Path $BuildDir "AgentOMLauncher.cs"
$LauncherExe = Join-Path $DistDir "AgentOM.exe"
$CsCode = @'
using System;
using System.Diagnostics;
using System.IO;

class AgentOMLauncher {
    static int Main(string[] args) {
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;
        string targetExe = Path.Combine(baseDir, "AgentOM", "AgentOM.exe");
        if (!File.Exists(targetExe)) {
            Console.Error.WriteLine("Cannot locate packaged executable: " + targetExe);
            return 2;
        }
        ProcessStartInfo psi = new ProcessStartInfo(targetExe);
        psi.UseShellExecute = false;
        psi.WorkingDirectory = Path.GetDirectoryName(targetExe);
        psi.RedirectStandardOutput = true;
        psi.RedirectStandardError = true;
        foreach (string a in args) {
            psi.ArgumentList_Compat(a);
        }
        return 0;
    }
}
'@

# Use .NET Framework csc.exe compatible argument quoting for Windows GUI/CLI forwarding
$CsCodeNet4 = @'
using System;
using System.Diagnostics;
using System.IO;
using System.Text;

class AgentOMLauncher {
    static string QuoteArg(string arg) {
        if (string.IsNullOrEmpty(arg)) return "\"\"";
        if (arg.IndexOfAny(new char[] { ' ', '\t', '"' }) < 0) return arg;
        return "\"" + arg.Replace("\"", "\\\"") + "\"";
    }
    static int Main(string[] args) {
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;
        string targetExe = Path.Combine(baseDir, "AgentOM", "AgentOM.exe");
        if (!File.Exists(targetExe)) {
            Console.Error.WriteLine("Cannot locate packaged executable: " + targetExe);
            return 2;
        }
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < args.Length; i++) {
            if (i > 0) sb.Append(' ');
            sb.Append(QuoteArg(args[i]));
        }
        ProcessStartInfo psi = new ProcessStartInfo(targetExe, sb.ToString());
        psi.UseShellExecute = false;
        psi.WorkingDirectory = Path.GetDirectoryName(targetExe);
        using (Process p = Process.Start(psi)) {
            p.WaitForExit();
            return p.ExitCode;
        }
    }
}
'@
Set-Content -Path $LauncherCs -Value $CsCodeNet4 -Encoding UTF8
$CscExe = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (Test-Path $CscExe) {
    & $CscExe /nologo /target:exe /out:$LauncherExe $LauncherCs
}

Write-Host "Build succeeded!"
Write-Host "  Primary --onedir executable : $MainExe"
if (Test-Path $LauncherExe) {
    Write-Host "  Top-level launcher          : $LauncherExe"
}

