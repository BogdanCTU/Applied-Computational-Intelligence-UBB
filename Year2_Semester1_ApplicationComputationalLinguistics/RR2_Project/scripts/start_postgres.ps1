# Script to start the local PostgreSQL server for agent_om_local in detached mode
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$PgBin = Join-Path $ProjectDir ".pg\pgsql\bin"
$PgData = Join-Path $ProjectDir ".pgdata"
$PgExe = Join-Path $PgBin "postgres.exe"
$PgCtl = Join-Path $PgBin "pg_ctl.exe"

if (-not (Test-Path $PgExe)) {
    Write-Error "PostgreSQL binaries not found at $PgExe."
    exit 1
}

# Check if port 5432 is already listening
$conn = Get-NetTCPConnection -LocalPort 5432 -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    Write-Host "PostgreSQL server is already active and listening on port 5432."
    exit 0
}

# Remove stale pid file if server is not actually running
$pidFile = Join-Path $PgData "postmaster.pid"
if (Test-Path $pidFile) {
    Remove-Item $pidFile -Force
}

Write-Host "Starting PostgreSQL server on 127.0.0.1:5432 (detached)..."
Start-Process -FilePath $PgExe -ArgumentList "-D `"$PgData`" -p 5432 -h 127.0.0.1" -WindowStyle Hidden

Start-Sleep -Seconds 2
$conn = Get-NetTCPConnection -LocalPort 5432 -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    Write-Host "PostgreSQL server started successfully on 127.0.0.1:5432."
} else {
    Write-Warning "PostgreSQL port 5432 not listening yet. Check agent_om_local\.pgdata\log for details."
}
