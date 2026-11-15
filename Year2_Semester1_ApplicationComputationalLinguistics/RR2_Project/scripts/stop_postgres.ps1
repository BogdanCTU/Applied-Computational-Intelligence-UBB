# Script to stop the local PostgreSQL server for agent_om_local
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$PgBin = Join-Path $ProjectDir ".pg\pgsql\bin"
$PgData = Join-Path $ProjectDir ".pgdata"
$PgCtl = Join-Path $PgBin "pg_ctl.exe"

if (-not (Test-Path $PgCtl)) {
    Write-Error "PostgreSQL binaries not found at $PgCtl."
    exit 1
}

Write-Host "Stopping PostgreSQL server..."
& $PgCtl -D $PgData stop -m fast

