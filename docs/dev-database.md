# The development database

**The write-path tests need Postgres. This is how to get one, and why a
missing one is a failure rather than a skip.**

---

## Why this exists

Six real defects in `collect/registry/` reached a commit while the suite
reported **139 passed, 9 skipped**. The nine skipped tests were
`tests/test_registry_load_db.py`, the only coverage of the registry write
path, and they skipped because no Postgres existed on the machine. All six
defects lived under exactly those nine tests. See
[the defect report](phase1-defect-report.md).

**A skip reads as success, and the problem gets worse as the suite grows.**
247 passed with 9 silent skips looks healthier than the 139 that originally
hid the bugs. The failure mode strengthens over time, which is why the fix is
not "remember to run Postgres" but "a missing database fails the run".

---

## Quick start

```powershell
.\scripts\dev-postgres.ps1
.venv\Scripts\python.exe -m pytest tests -q
```

The script creates a disposable PostgreSQL 17.6 instance under
`%LOCALAPPDATA%\modelboard-pg`, on **port 5433**, and writes
`TEST_DATABASE_URL` into a gitignored `.env.test` that `tests/conftest.py`
reads. A new shell needs no further setup.

```powershell
.\scripts\dev-postgres.ps1 -Stop      # stop the server
.\scripts\dev-postgres.ps1 -Destroy   # stop, drop the data directory, keep binaries
```

Nothing lives in the repository and nothing is committed. Measured 2026-08-18
on one machine, after several test runs:

| | files | size |
|---|---|---|
| `pg\` — extracted binaries | 1,562 | **130.5 MB** |
| `pgdata\` — the data directory | 24,487 | **898.8 MB** |
| total under `%LOCALAPPDATA%\modelboard-pg` | 26,051 | **1,029.6 MB** |

**Budget a gigabyte, not a hundred megabytes.** The sentence this replaces said
"binaries are about 134 MB, the data directory grows", which was roughly right
about the half that does not matter and silent about the half that does: the
binaries are fixed and small, and `pgdata` is eight times larger and still
growing, because the suite drops and recreates schemas rather than vacuuming.

⚠ **Two figures disagree and this is not resolved.** 301 MB was reported for the
binaries; this machine measures 130.5 MB for `pg\` and nothing under the tree
near 301 MB. Possible causes not investigated: size-on-disk versus logical size,
a partially-extracted or unfiltered archive, or a different measurement root.
Recorded rather than averaged or picked between - the number a reader should act
on is the total, and that is a gigabyte on either account.

**Windows PowerShell 5.1 is enough**, and the script now enforces it with
`#requires -Version 5.1` rather than leaving the floor to this page. Verified by
reading the script rather than by impression - no `&&`, `||`, `??`, `?.`, no
ternary, no `-AsHashtable`, `-Parallel`, `$PSStyle`, `Get-Error` or
`Join-String` - and run end to end under 5.1 through download, extraction,
`initdb` and start. It was always a 5.1 script: two of its comments reason about
5.1's native-stderr wrapping and its UTF-8 BOM, both of which 7 does not have.
The `pwsh` invocations were in the script's own `.EXAMPLE` block and final
`Write-Host`, so the file disagreed with itself rather than with this doc.

**Port 5433, not 5432, on purpose.** It cannot collide with a real local
server somebody is using for something else.

---

## The three states of a test run

| State | Result |
|---|---|
| `TEST_DATABASE_URL` set (or `.env.test` present) | tests run — **266 passed** |
| unset | **35 errors**, with instructions |
| unset and `ALLOW_MISSING_TEST_DB=1` | 35 skipped, plus a banner in the summary |

The third state exists so a laptop with no server is not blocked. It is
deliberately noisy:

```
=========================== WRITE PATH NOT COVERED ============================
  The registry write-path tests did not run: ALLOW_MISSING_TEST_DB is set
  and TEST_DATABASE_URL is unset.
  A green result here does NOT mean the database write path works.
```

A skip reason alone would need `pytest -rs` to surface, and **an override
whose consequence is invisible becomes permanent the first time somebody puts
it in a shell profile.** Same principle as `--allow-missing-spellings` on the
seed loader.

---

## Why the suite may destroy this database, and nothing else

Every test in `test_registry_load_db.py` runs `DROP SCHEMA public CASCADE`
before it starts. Three layers decide whether that is allowed, ordered so the
error message matches the mistake.

**Layer 1 — host allowlist.** `localhost`, `127.0.0.1` or `::1` only. Checked
**before a connection is opened**, so a DSN aimed at RDS is refused without
ever authenticating against it.

**Layer 2 — the database name must end `_test`.** Catches a local database
that is real but misaddressed.

**Layer 3 — the sentinel, which is the layer that actually works.** The
bring-up script creates:

```sql
CREATE SCHEMA modelboard_meta;
CREATE TABLE modelboard_meta.disposable (dsn text PRIMARY KEY, created_at timestamptz);
```

and records the DSN it created. The fixture refuses unless that table exists
**and** its recorded DSN matches the host, port and database being connected
to.

Three details are load-bearing:

- **It lives in `modelboard_meta`, not `public`.** The fixture drops `public`
  on every test, which would take the mark with it and break the second run.
- **It records the DSN**, so lifting the table into a real database to unblock
  yourself does not work.
- **Layers 1 and 2 are kept even though layer 3 subsumes them.** They are
  guessable — somebody runs a local proxy, or names a real database
  `modelboard_test` — but they fail earlier and more clearly. Someone who
  pointed `TEST_DATABASE_URL` at RDS should read *"this is not localhost"*,
  not *"no sentinel table found"*, which sounds like a setup problem rather
  than the near miss it is.

The guard is tested in `tests/test_dev_database_guard.py`, without a database.

---

## Traps

All of these cost real time to diagnose. The first three are encoded in the
script, which comments each at the point it matters; the last two bite
whoever restarts the instance, so they are written down here.

**`Expand-Archive -Force` fails during its own cleanup**, with
`Cannot find path ... because it does not exist` on files it is midway
through replacing. The script uses `System.IO.Compression` directly.

**The EDB archive blows Windows MAX_PATH.** It bundles pgAdmin 4, whose
vendored Python packages nest deep enough that .NET
`ExtractToDirectory` throws `DirectoryNotFoundException`. We need the server,
not pgAdmin, so extraction filters to `pgsql/bin`, `pgsql/lib` and
`pgsql/share` — 1562 files instead of the whole archive.

**`pg_ctl start` never returns when its stdout is piped.** The `postgres`
child inherits the handle and holds the pipe open for the life of the server,
so any `| Select-Object` or `2>&1 |` on that call hangs forever. The server
does start; the wrapper just never exits.

A fourth, found while writing this: **`Set-Content -Encoding utf8` on Windows
PowerShell 5.1 writes a UTF-8 BOM.** That made `.env.test`'s first key parse
as `﻿TEST_DATABASE_URL` and silently not match. The script now writes
with an explicit no-BOM encoder, and the reader uses `utf-8-sig` so a
hand-written file with a BOM also works. Worth knowing generally: the repo's
`.gitattributes` has the same BOM and currently gets away with it.

---

## Three more, found bringing the instance back up

**Four of the five have now fired for somebody**, which is the argument for
this section existing rather than the individual entries. Trap 4 fired for
Engineer 2 exactly as written — and it did not save her time, it saved her a
WRONG DIAGNOSIS, which is the more valuable of the two and the harder to
notice. Without the note, `accepting connections: no response` beside a
`postmaster.pid` naming a live-looking PID reads as *a running server that is
busy or wedged*. That reading sends you to the server. The truth was that
nothing was listening, and the check itself was lying.

**A stale `postmaster.pid` blocks the restart, and will recur.** If the
machine sleeps or the server dies mid-session, `pgdata\postmaster.pid`
survives naming a PID that no longer exists. The next start says:

```
pg_ctl: another server might be running; trying to start server anyway
```

and then does not start. Confirm the process is genuinely gone before
removing the file — a pid file removed while a live postmaster holds the data
directory invites two servers onto one directory, which is how the data
directory gets corrupted:

```powershell
Get-Process -Id <pid from the file> -ErrorAction SilentlyContinue   # nothing
Get-Process -Name postgres -ErrorAction SilentlyContinue            # nothing
Get-NetTCPConnection -LocalPort 5433 -State Listen                  # nothing
Remove-Item "$env:LOCALAPPDATA\modelboard-pg\pgdata\postmaster.pid"
```

**Do not test the port with `TcpClient.BeginConnect` + `WaitOne`.** It is the
obvious check and it is wrong: `WaitOne` returning `$true` means *the wait
completed*, not that the connection succeeded. It reported port 5433
"reachable" while nothing was listening at all, which turned an obvious "no
server" into an ambiguous hang and cost an afternoon. Two checks that do tell
the truth:

```powershell
Get-NetTCPConnection -LocalPort 5433 -State Listen    # is anything listening
```

```python
psycopg.connect(dsn, connect_timeout=5)    # does it speak Postgres
```

The second is the one that matters. Something can listen on 5433 without
being a Postgres that will answer, and only a protocol-level connect
distinguishes them. `collect.db.connect` sets no `connect_timeout`, so a
diagnostic connect should always pass one explicitly — otherwise the check
you are using to diagnose a hang hangs too.

**`pg_isready` without `-U postgres` writes FATAL lines into `pg.log`.** The
server runs as the `postgres` role; `pg_isready` defaults the user to the
current OS account, so on Windows it asks for a role named after your Windows
username and the server logs:

```
FATAL:  role "<your Windows username>" does not exist
```

The readiness answer is still correct — `pg_isready` reports the server is
accepting connections, because it got a protocol-level response, which is all
it claims to measure. But the FATAL sits in `pg.log` **beside real failures**,
newest-last, in the file you are reading precisely because something is wrong.
It is harmless, self-inflicted, and it will cost somebody twenty minutes of
chasing a permissions problem that does not exist.

```powershell
& "$bin\pg_isready.exe" -p 5433 -U postgres      # no FATAL in the log
```

Worth generalising, because this is the third entry in this file with the same
shape: **a diagnostic that writes to the evidence it is diagnosing.** The
`BeginConnect` check reported a reachable port that was not; this one adds
noise to the log; both were reached for while something else was broken. A
diagnostic gets read at the worst possible moment, so its own side effects are
part of its cost.

---

## CI does the same three layers

`.github/workflows/ci.yml` runs the suite against a `postgres:17` service, and
it has to satisfy the same guard. Three things, matching the three layers:

- the service is reached on `localhost` (layer 1);
- the database is named `modelboard_test` (layer 2);
- a step creates `modelboard_meta.disposable` and records the exact
  `TEST_DATABASE_URL` (layer 3).

`ALLOW_MISSING_TEST_DB` is deliberately unset there. If the service does not
come up the run fails, because a skip reads as success and that is the failure
this whole file exists to prevent.

**Do not name the CI variable `DATABASE_URL`.** `_same_target` compares host,
port and database name, so the recorded DSN and the connecting DSN must agree
including the port — write the same string in both places.

### Postgres `ERROR` lines in a **green** run are the tests working

At teardown the job prints the container log, and a passing run is full of
this:

```
ERROR:  duplicate key value violates unique constraint "document_pkey"
ERROR:  new row for relation "harvest_run" violates check constraint "harvest_run_truncated_ck"
ERROR:  new row for relation "reported_context" violates check constraint "reported_context_provenance_ck"
ERROR:  new row for relation "source" violates check constraint "source_discovered_needs_ruling_ck"
```

**Every one of those is a test asserting that a constraint rejects a bad
row.** Postgres logs a rejected statement at ERROR whether or not something
was expecting it, so the log cannot tell the two apart — and a green run full
of `ERROR` reads alarming enough that somebody will eventually "fix" it.
Read the job's conclusion, not the container log.

`source_discovered_needs_ruling_ck` is worth recognising: it is
`CHECK (provenance = 'seed' OR terms_ruling IS NOT NULL)`, and it is the
schema correction from the source-writer work — a feed discovered from a link
must carry a terms ruling made about *its* host, where only the hand-curated
seed may record an honest "nobody has read these terms yet". That line in the
log is the first time it was exercised against a real Postgres in CI rather
than only on a laptop.

If you ever want the log quiet, the change is to the tests, not to the
constraints: nothing here logs an ERROR that a test did not deliberately
provoke.

---

## Docker Compose — deferred, not rejected

A Compose service was considered and declined **on cost, not on principle**:

```yaml
services:
  postgres:
    image: postgres:17.6
    environment:
      POSTGRES_PASSWORD: modelboard
      POSTGRES_DB: modelboard_test
    ports: ["5433:5432"]
    volumes: ["modelboard-pgdata:/var/lib/postgresql/data"]
volumes:
  modelboard-pgdata:
```

`pyproject.toml` forbids workflow engines, Kafka, Timescale, ClickHouse and
headless browsers. Every one of those is a *runtime* dependency that would
reach production. Compose here is a local test harness: it ships nothing to
production and adds nothing importable, so it does not violate the letter or
the spirit of that rule.

It was declined because on this machine it costs a Docker Desktop install,
WSL2, administrator rights and a reboot — a large ask to solve a problem the
loud-failure guard solves in fifteen lines.

> **Revisit if Engineer 2 is on Linux or macOS**, where Compose costs them
> almost nothing and the fourteen lines above replace a Windows-only script.
> The guard in `tests/conftest.py` is cross-platform and stays correct either
> way, so switching later changes only how the database is obtained.

**The bring-up script is Windows-only. The guarantee is not.** On any other
platform, run Postgres however you like, create a database whose name ends
`_test`, apply the sentinel SQL above with the DSN you will connect with, and
set `TEST_DATABASE_URL`.
