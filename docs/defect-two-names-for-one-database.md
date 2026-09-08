# Defect: `DATABASE_URL` and `STAGING_DATABASE_URL` are the same remote instance

**Found 2026-09-07 while building the new-platform adapters. Independent of that
work, and it would have been found by anything that wrote a row.** Not fixed —
the fix is a decision about how the shared database is addressed, and it belongs
to whoever owns the deployment.

---

## What is true

In `.env`:

```
DATABASE_URL=postgresql://bv_agent:***@52.17.75.29:5432/Model-information-Board
STAGING_DATABASE_URL=postgresql://bv_agent:***@52.17.75.29:5432/Model-information-Board
ENVIRONMENT=development
```

Same host, same port, same database, same user. **Two names for one instance**,
and one of the two names says "staging" while the other is what every default
resolves to.

`.env.example` describes `STAGING_DATABASE_URL` as being for *"read-only viewing
of the shared database via `run-backend.py --staging`, which appends
`-c default_transaction_read_only=on` so no code path in the process can
write"*. That protection is real and it is attached to the **variable a person
chooses**, not to the database. Anything reading `DATABASE_URL` — which is
`collect.db.connect`'s default, so every CLI command, every script and every
chain stage — reaches the same rows with writes enabled.

## Why it is a defect and not a naming preference

**`ENVIRONMENT=development` is doing no work here.** Every assertion that keys
on it — `assert_no_fixtures`, `assert_no_phantom_sweeps`,
`assert_contract_backed` — returns early in `development`. So the guards that
exist to protect a shared database are switched off on the machine pointed at
it, by the same file that points at it.

**The one guard that does work is guarding a different thing.**
`collect/db.py:reset_schema` refuses a non-local host, and it reads the host
**from the open connection** rather than from the DSN it was handed:

> *"The host is read from the open connection, not from any DSN passed in, so
> this cannot be overridden by argument."*

That is the correct construction and it is the reason the destructive path is
safe. It is also the only place in the repository that checks a host.

**And that is how this surfaced.** `scripts/smoke_new_adapters.py` had to refuse
a non-local database, because it creates `source` rows for platforms whose terms
rulings are unratified drafts — and a seeded `source` row is what
`assert_terms_reviewed` reads to decide whether we may fetch at all. I copied
`reset_schema`'s construction and checked `conn.info.host`. **It refused
immediately on the default connection**, which is what showed that the default
connection is the shared instance.

Had I checked the variable name instead — "is this `STAGING_DATABASE_URL`?" —
the script would have written five unratified `source` rows to the shared
database and reported success. The variable name is not the property; the host
is. Recorded because the next person writing a write-path script will reach for
the name.

## Why it matters beyond one script

`CLAUDE.md` requires shared-database writes to be coordinated and append-only,
and evidence writes to use `ON CONFLICT DO NOTHING` rather than a global
rebuild. Those rules can only be followed by somebody who knows they are
writing to the shared instance. Today that knowledge is not in the environment:
it is in remembering which of two identical URLs somebody typed.

The corpus this affects is not hypothetical — 6,502 `document` rows, 1,163
`harvest_run` rows, 12 `source` rows.

## What I would change, and what I would not

**Would change — one of these two, not both:**

- **Point `DATABASE_URL` at a local instance and require the shared one to be
  named explicitly.** `scripts/dev-postgres.ps1` already provides a disposable
  local Postgres on `localhost:5433`, and the test suite already expects one.
  A default that reaches a throwaway database makes the shared one a deliberate
  argument, which is what it is.
- **Or make the shared instance read-only by default at the connection.** Move
  `-c default_transaction_read_only=on` from `run-backend.py --staging` onto the
  DSN itself, and have the write paths opt out by naming a separate writable
  variable. The protection then travels with the database rather than with the
  invocation.

The first is cheaper and matches how the tests already work. The second is
stronger, because it survives somebody copying a URL.

**Would not change — and this is the part worth arguing about.** I would **not**
add a variable-name check anywhere. `reset_schema` gets this right by reading
the open connection, and a second mechanism that trusts a name would be a guard
that a copy-paste defeats while looking like protection. If a check is added,
read `conn.info.host`.

**Would also not** rename `STAGING_DATABASE_URL` and stop there. Renaming makes
the two names differ and leaves both pointed at one instance, which fixes the
confusion and none of the exposure.

## What I did instead, for now

`scripts/smoke_new_adapters.py:assert_local` refuses any host that is not
localhost, read from the open connection, and says why in the message. That is
one script. Every other write path in `collect/` still defaults to the shared
instance.
