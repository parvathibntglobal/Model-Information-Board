#requires -Version 5.1
#
# THE FLOOR IS 5.1 AND IT IS ENFORCED HERE RATHER THAN DESCRIBED IN A DOC.
# A version error naming the requirement beats a syntax error partway through
# a download, and a reader who never opens docs/dev-database.md still gets it.
#
# 5.1 is genuinely enough, verified by reading rather than by impression: no
# `&&`, `||`, `??`, `?.`, no ternary, no `-AsHashtable`, no `-Parallel`, no
# `$PSStyle`, `Get-Error` or `Join-String`. And the script was already WRITTEN
# for 5.1 - the two comments below reason explicitly about 5.1's native-stderr
# ErrorRecord wrapping and its UTF-8 BOM, which are 5.1 problems that 7 does
# not have. The `.EXAMPLE` block used to say `pwsh`, so the only thing
# claiming 7 was this file's own help, contradicting its own body.

<#
.SYNOPSIS
  Bring up a disposable local Postgres for the write-path tests.

.DESCRIPTION
  `tests/test_registry_load_db.py` covers the registry write path, and it
  cannot run without a database. Six real defects survived a green suite
  because those tests skipped for want of one, so this exists to make the
  database boring to obtain rather than a per-session chore.

  Everything lives under %LOCALAPPDATA%\modelboard-pg, outside the repo and
  outside any session-scoped temp directory. Nothing here is committed.

  MEASURED 2026-08-18 on one machine, after several test runs:
      pg\      1,562 files    130.5 MB   the extracted binaries
      pgdata\ 24,487 files    898.8 MB   the data directory
      total   26,051 files  1,029.6 MB
  The binaries are the small half. `pgdata` is what actually fills a disk, and
  it grows with every run because the suite creates and drops schemas rather
  than vacuuming. Budget a gigabyte, not a hundred megabytes.

  THIS DATABASE IS DESTROYED BY THE TEST SUITE. The `conn` fixture runs
  DROP SCHEMA public CASCADE on every test. The script marks the instance as
  disposable in a `modelboard_meta` schema that survives that drop, and the
  fixture refuses to run against any database lacking the mark. See
  docs/dev-database.md.

.PARAMETER Stop
  Stop the server and exit.

.PARAMETER Destroy
  Stop the server and delete the data directory. Binaries are kept.

.EXAMPLE
  .\scripts\dev-postgres.ps1
  .\scripts\dev-postgres.ps1 -Stop

  Runs under Windows PowerShell 5.1 or PowerShell 7. Invoked by path rather
  than through `pwsh`, which named a binary the script never needed.
#>
[CmdletBinding()]
param(
    [switch]$Stop,
    [switch]$Destroy
)

$ErrorActionPreference = "Stop"

$PG_VERSION = "17.6-1"
$PORT       = 5433
$DBNAME     = "modelboard_test"
$USER       = "postgres"

$root    = Join-Path $env:LOCALAPPDATA "modelboard-pg"
$binRoot = Join-Path $root "pg"
$bin     = Join-Path $binRoot "pgsql\bin"
$data    = Join-Path $root "pgdata"
$log     = Join-Path $root "pg.log"
$zip     = Join-Path $root "pg.zip"

$repo   = Split-Path $PSScriptRoot -Parent
$envTest = Join-Path $repo ".env.test"

$DSN = "postgresql://$USER@localhost:$PORT/$DBNAME"

New-Item -ItemType Directory -Force -Path $root | Out-Null


function Invoke-PgCtl {
    param([string[]]$PgArgs)
    # `pg_ctl start` NEVER RETURNS when its stdout is piped or captured: the
    # postgres child inherits the handle and holds the pipe open for the life
    # of the server. Redirect to a file and let it detach.
    & (Join-Path $bin "pg_ctl.exe") @PgArgs
}

function Test-ServerRunning {
    if (-not (Test-Path $data)) { return $false }
    & (Join-Path $bin "pg_ctl.exe") -D $data status *> $null
    return ($LASTEXITCODE -eq 0)
}


# ── stop / destroy ────────────────────────────────────────────────────────

if ($Stop -or $Destroy) {
    if (Test-ServerRunning) {
        Invoke-PgCtl @("-D", $data, "-m", "fast", "stop") > $null 2>&1
        Write-Host "server stopped"
    } else {
        Write-Host "server was not running"
    }
    if ($Destroy) {
        Remove-Item -Recurse -Force $data -ErrorAction SilentlyContinue
        Remove-Item -Force $envTest -ErrorAction SilentlyContinue
        Write-Host "data directory and .env.test removed"
    }
    exit 0
}


# ── binaries ──────────────────────────────────────────────────────────────

if (-not (Test-Path (Join-Path $bin "initdb.exe"))) {

    if (-not (Test-Path $zip)) {
        Write-Host "downloading PostgreSQL $PG_VERSION (about 315 MB, once) ..."
        $ProgressPreference = "SilentlyContinue"
        Invoke-WebRequest -UseBasicParsing -TimeoutSec 1800 `
            -Uri "https://get.enterprisedb.com/postgresql/postgresql-$PG_VERSION-windows-x64-binaries.zip" `
            -OutFile $zip
    }

    Write-Host "extracting server binaries ..."
    # Two traps here, both cost real time to diagnose:
    #
    #   1. `Expand-Archive -Force` fails partway through its own cleanup with
    #      "Cannot find path ... because it does not exist" on files it is in
    #      the middle of replacing. Do not use it.
    #
    #   2. The archive bundles pgAdmin 4, whose vendored Python packages nest
    #      deep enough to blow Windows MAX_PATH, and .NET ExtractToDirectory
    #      throws DirectoryNotFoundException on them. We need the server, not
    #      pgAdmin, so extract only pgsql/bin, pgsql/lib and pgsql/share.
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $wanted  = @("pgsql/bin/", "pgsql/lib/", "pgsql/share/")
    $archive = [System.IO.Compression.ZipFile]::OpenRead($zip)
    try {
        $taken = 0
        foreach ($entry in $archive.Entries) {
            if ($entry.FullName.EndsWith("/")) { continue }
            $keep = $false
            foreach ($prefix in $wanted) {
                if ($entry.FullName.StartsWith($prefix)) { $keep = $true; break }
            }
            if (-not $keep) { continue }

            $target = Join-Path $binRoot ($entry.FullName -replace "/", "\")
            $parent = Split-Path $target -Parent
            if (-not (Test-Path $parent)) {
                New-Item -ItemType Directory -Force -Path $parent | Out-Null
            }
            [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $target, $true)
            $taken++
        }
        Write-Host "extracted $taken files"
    }
    finally { $archive.Dispose() }
}

if (-not (Test-Path (Join-Path $bin "initdb.exe"))) {
    throw "initdb.exe not found under $bin after extraction"
}


# ── cluster ───────────────────────────────────────────────────────────────

if (-not (Test-Path $data)) {
    Write-Host "initdb ..."
    # trust auth: this instance is disposable, listens on localhost only, and
    # holds nothing but test fixtures.
    & (Join-Path $bin "initdb.exe") -D $data -U $USER --auth=trust --encoding=UTF8 `
        > (Join-Path $root "initdb.log") 2>&1
    if ($LASTEXITCODE -ne 0) { throw "initdb failed, see $root\initdb.log" }
}

if (-not (Test-ServerRunning)) {
    Write-Host "starting on port $PORT ..."
    Invoke-PgCtl @("-D", $data, "-l", $log, "-o", "-p $PORT", "-w", "start") > $null 2>&1
    if (-not (Test-ServerRunning)) { throw "server did not start, see $log" }
}


# ── database and the disposable mark ──────────────────────────────────────

$psql = Join-Path $bin "psql.exe"

$exists = & $psql -h localhost -p $PORT -U $USER -tAc `
    "SELECT 1 FROM pg_database WHERE datname='$DBNAME'"
if (-not $exists) {
    & (Join-Path $bin "createdb.exe") -h localhost -p $PORT -U $USER $DBNAME
    Write-Host "created database $DBNAME"
}

# The mark lives in its own schema on purpose. The test fixture runs
# DROP SCHEMA public CASCADE, which would take the mark with it if it sat in
# public, and the second test run would then refuse to start.
#
# It records the DSN this script created. The fixture compares host, port and
# database name against the DSN it is connecting with, so copying the table
# into a real database to unblock yourself does not work either.
# client_min_messages: `CREATE ... IF NOT EXISTS` emits a NOTICE on stderr,
# and Windows PowerShell 5.1 wraps any native stderr line in an ErrorRecord,
# which $ErrorActionPreference = "Stop" then turns into a terminating error.
# The notice is noise; silence it rather than papering over stderr generally.
& $psql -h localhost -p $PORT -U $USER -d $DBNAME -q -v ON_ERROR_STOP=1 -c @"
SET client_min_messages = warning;
CREATE SCHEMA IF NOT EXISTS modelboard_meta;
CREATE TABLE IF NOT EXISTS modelboard_meta.disposable (
  dsn        text PRIMARY KEY,
  created_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO modelboard_meta.disposable (dsn) VALUES ('$DSN')
  ON CONFLICT (dsn) DO NOTHING;
"@

# .env.test is gitignored via the `.env.*` rule. tests/conftest.py reads it
# when TEST_DATABASE_URL is not already set, so a new shell needs no setup.
#
# WriteAllText with an explicit no-BOM encoder, NOT `Set-Content -Encoding
# utf8`: Windows PowerShell 5.1 writes a UTF-8 BOM, and the reader would then
# see the first key as "<BOM>TEST_DATABASE_URL" and quietly not match it.
# The reader also tolerates a BOM, but two defences are cheap and this one
# stops the bad file being created at all.
[System.IO.File]::WriteAllText(
    $envTest, "TEST_DATABASE_URL=$DSN`n", (New-Object System.Text.UTF8Encoding($false)))

& $psql -h localhost -p $PORT -U $USER -tAc "SELECT version();"
Write-Host ""
Write-Host "TEST_DATABASE_URL=$DSN"
Write-Host "written to $envTest (gitignored)"
Write-Host ""
Write-Host "run:   .venv\Scripts\python.exe -m pytest tests -q"
Write-Host "stop:  .\scripts\dev-postgres.ps1 -Stop"
