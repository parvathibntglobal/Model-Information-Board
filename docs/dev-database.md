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

Nothing lives in the repository and nothing is committed: binaries are about
134 MB, the data directory grows.

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

## Two more, found bringing the instance back up

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
