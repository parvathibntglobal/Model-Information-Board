# Railway deployment: the decisions, and three of them are the work

**2026-09-14, anooj. Nothing provisioned. Every figure measured on this host
and the shared database today; where I could not measure, it says so.**

Full deployment with fetch running on Railway. The three blockers are §1–§3;
the rest is configuration with two teeth in it (§4) and one question only you
can answer (§6).

---

## 0 · The finding that resizes §1

**"Move run state to Postgres" is mostly already done, and the half that is not
done is the half that matters.**

`fetch_log` exists — **425 rows, 24 distinct run ids** — and `Progress._write`
already mirrors every line into it. `/fetch/log` already falls back to it:

> *"THE LOCAL FILE FIRST, THE SHARED TABLE SECOND. … A run id this machine has
> never seen belongs to somebody else's laptop, and `fetch_log` is where it can
> be read from; `source` says which happened."*

So the log survives a restart **today**, and a second replica can already read
another replica's run. What cannot: **`/fetch/stop` is file-only**, and
`was_running` is computed from the local file alone.

That shrinks §1 from a migration to one channel — and it means the thing to
protect during it is a capability that has already been used twice.

---

## 1 · Run state: move the STOP signal, keep the log dual-written

### What must not be lost

`Progress`'s docstring records why the file is primary, and it is not a
preference:

> *"a run which dies BECAUSE THE DATABASE IS UNREACHABLE must still be able to
> say so. That is not hypothetical: it is how the 2026-09-09 and 2026-09-10 runs
> were diagnosed, the second of them while the shared database was down for a
> day. A log that needs the database to record the database being unreachable
> records nothing, exactly when it matters most."*

**A plan that makes Postgres the only log deletes the instrument that diagnosed
the last two incidents.** Keep the dual write. The file becomes a per-container
scratch buffer rather than the survivor; the table becomes authoritative for
*reading*; neither becomes the only writer.

### What changes

| | today | after |
|---|---|---|
| progress lines | file, mirrored to `fetch_log` best-effort | unchanged |
| `/fetch/log` | local file, else `fetch_log` | **`fetch_log` first**, local file as the fallback for a run whose mirror failed |
| stop request | `var/fetch/<id>.stop` | a row/column the run polls |
| `was_running` | local file only | `fetch_log` |

Reversing the read order is the only change to the log path, and it is one
branch. The `source` field already exists to say which answered.

### Can the stop check stay cooperative? Yes, and it should

Nothing about cooperative stopping depends on the file. The design note is
about *signals*, not storage:

> *"COOPERATIVE, NOT A KILL, and that is the whole design… No signal, no PID,
> nothing that breaks when the backend restarts between the request and the run
> noticing it."*

A stop flag in Postgres keeps every one of those properties and adds
cross-replica delivery, which the file cannot have. The run polls it at the
same stage boundary it polls the file at now, writes its own `stopped` end
record, and closes its connection on the way out. `Progress.stage()` is the
only place that changes.

**One property is genuinely lost and should be stated rather than discovered:**
a stop request cannot be delivered while the database is unreachable. That is
acceptable in a way the log is not — a run that cannot reach the database is
already failing and will stop on its own; a run you cannot *diagnose* is the
expensive case, and that is the capability we are keeping.

**Fallback worth keeping:** the run polls the table, and *also* the local file
if one exists. Same-container stop then works with the database down, which is
the only case where it is needed.

### Where the stop flag lives — a real choice

`job_run` is the wrong table as it stands. **A UI fetch writes no `job_run` row
at all** — grep finds none — so there is nothing to attach a flag to. Two
options:

- **(a) Open a `job_run` row per fetch.** Matches BUILD-PLAN's "cron plus a jobs
  table", gives §2 a target, and makes fetches visible beside chain stages.
  Costs a schema column (`stop_requested_at`) and a writer in `fetch_model.py`.
- **(b) A `fetch_run` table.** `fetch_log` already carries `run_id`, `machine`
  and `model_version_id`; a header table is a small addition and keeps UI
  fetches off the chain's ledger.

**(a) is the better fit** because §2 needs a per-run row with a `started_at` and
a `finished_at` regardless, and `job_run` already has both plus the
`job_run_finish_ck` constraint that keeps outcome and finishing time moving
together. Building a second table with the same columns is the thing
`unfinished()` exists to prevent.

---

## 2 · Reaping orphans — the problem is already here

**Measured today, before any container restarts:**

| | total | unfinished | |
|---|---:|---:|---:|
| fetch runs in `fetch_log` | 24 | **4 with no `end` record** | **17%** |
| `harvest_run` | 1,163 | **127** started and never concluded | **11%** |
| `job_run` | 28 | 0 | — |

The four orphan fetches are all from 2026-09-11, on **both** machines. The
oldest unfinished `harvest_run` is from 2026-08-24. So this is not a risk
Railway introduces; it is a defect Railway will multiply.

### What marks a run abandoned

The ledger already refuses to guess, and it is right to:

> ```
> finished_at IS NULL, outcome IS NULL     still running, or killed
> outcome = 'error'                        ran, and raised
> ```
> *"A killed process cannot write its own failure, so the first has to be
> carried by an absence… a reader showing both as red has thrown away which one
> to do."*

`unfinished()` deliberately **does not invent a staleness threshold**, and its
one caller (`collect/cli.py`) reports and refuses rather than cleaning. That is
correct for an operator at a terminal and useless for a container platform,
because there is no operator.

**So the threshold is the decision, and it has to come from evidence rather than
a round number.** What we have: the longest-lived orphan wrote lines for 4m11s
before dying; the longest real run in `fetch_log` is a better bound and should
be measured before a number is chosen. The honest shape is:

```
abandoned := started_at < now() - <T>
             AND finished_at IS NULL
             AND no fetch_log line for this run within <T>
```

The second clause is what makes it safe: a long run that is still *writing* is
not abandoned however long it has been going, and heartbeat-by-log-line needs no
new mechanism — `Progress` already writes one per stage.

### Who runs it

Three candidates, and the choice follows from §1(a):

- **A Railway cron service** running `collect ops reap` nightly. Cheapest, and
  BUILD-PLAN already says "cron plus a jobs table".
- **Backend startup.** Tempting on a platform that restarts often, and wrong:
  with two replicas both reap, and a restart *during* a legitimate run would
  mark it abandoned.
- **The chain's own preflight.** Already calls `unfinished()`; would only fire
  when the chain runs, which is not a schedule today.

**Cron, and it marks rather than deletes.** `outcome = 'abandoned'` is a third
value beside `ok` and `error`, distinct from both, and it preserves the
distinction the ledger's docstring is built around. Deleting the row would
destroy the only record that the run happened.

**This needs a migration** (`job_run.outcome` vocabulary, `stop_requested_at`)
and therefore a PR body that says who applies it — the convention added in #268.

---

## 3 · The storage split — decide before provisioning

### What is actually in there

| | objects | bytes | share |
|---|---:|---:|---:|
| `raw_store/raw` — **document payloads** | 7,165 present | **54.5 MB** | 24.5% |
| `raw_store/raw` — **listing & search pages** | ~4,678 | **~168 MB** | **75.5%** |
| `raw_store/flattened` | 3,680 | 12.9 MB | |
| **`raw_store` total** | 15,523 | **235.6 MB** (257 MB on disk) | |
| `_sweep_store` | 583 | **399.8 MB** | mean **686 KB**/object |

### Do listing pages belong in the same store?

**No, and the reason is stronger than size: nothing can name them.**

`discovery_refs` is an in-memory field on the adapter dataclass and **is never
written**. `harvest_run` carries `pages_stored` — a count — and there is no
`discovery_refs` column. So 168 MB of objects exist that **no database row can
address**; they are reachable only by scanning the store, which is exactly how
`restore_reddit_payload_refs.py` finds them.

That makes them a different kind of artifact from a document payload:

- a **payload** is addressed by `document.text_ref`, is required by NFR-4 to
  reprocess from, and is 24.5% of the bytes;
- a **page** is addressed by nothing, is a retrieval audit trail, and is 75.5%.

**Recommendation: separate namespace, separate lifecycle, and a TTL on pages.**
They are the growth curve — an active sweep day adds 26–115 MB and most of it is
pages. Keeping them is defensible (they are how a repair finds a payload under
another sweep's hash); keeping them *forever, on the same volume as the thing
NFR-4 protects* is not a decision anyone has made.

**What it is NOT safe to do:** delete them before §3's second half is settled,
because they are currently the only route to a payload whose `text_ref` is
wrong.

### Does `_sweep_store` migrate?

**Measured: `_sweep_store` contributes 1 payload spelling out of 9,379 to the
repair index — for 62% of the bytes.**

```
payload spellings indexed by store: {'raw_store': 9378, '_sweep_store': 1}
```

So as a repair path it has earned 400 MB to fix one row. **But it is not only
historical:** `collect/cli.py:1251` gives `sweep-github` the default
`--store ./_sweep_store`, so a sweep run with default arguments writes there. If
it does not migrate, that command on Railway writes outside the volume and the
objects vanish on the next restart.

**Recommendation: do not migrate the bytes; do change the default.** Point
`sweep-github --store` at the same store as everything else (or at
`RAW_STORE_PATH`), archive `_sweep_store` off-volume, and keep the one payload
by copying it across. A default that writes to a second store is how this split
happened in the first place.

### Volume sizing, once the above is decided

| scenario | migrate | headroom in 5 GB | at 27 MB/day median | at 115 MB/day heavy |
|---|---:|---:|---:|---:|
| everything | 640 MB | 4.4 GB | ~160 days | ~38 days |
| `raw_store` only | 257 MB | 4.7 GB | ~175 days | ~41 days |
| payloads + flattened only | 67 MB | 4.9 GB | far longer; pages are the curve |

⚠ **All three understate it.** 2,205 of 9,370 documents (23.5%) have payloads
absent from this host. Consolidating three stores is the point of the exercise,
and **I cannot measure the other two.** 640 MB is a lower bound on the union,
not an estimate of it. Ask both machines to run `du -sh raw_store` before a
volume is sized.

---

## 4 · The rest of the plan, with the two teeth

### Services

- **Backend** — `judge/app.py` via uvicorn. **No Dockerfile, Procfile,
  `railway.json` or nixpacks config exists**; all are new.
- **Frontend** — Vite build to static `dist/`.
- **Database** — see below.

### CORS: currently none, and it is deliberate

`web/vite.config.js`: *"The backend runs no CORS middleware, so in dev we proxy
rather than ask them to add one."*

Two Railway services are two origins. Three ways out, in ascending cost:

1. **Serve `dist/` from FastAPI** — one origin, no CORS, no second service.
   Loses independent frontend deploys.
2. **One proxy in front of both** — keeps two services, no CORS.
3. **Add CORS middleware** — the only one that widens what can call the API,
   and it interacts with the token below.

### `API_TOKEN` in the browser bundle: the tooth

`vite.config.js` injects `API_TOKEN` into the bundle at build time, and its own
comment explains the care taken to inject **exactly one** value because *"`define`
puts whatever it is given into the browser bundle in clear text."*

So the token is readable by anyone who loads the page. `judge/gate.py` is candid
about what that is:

> *"A shared bearer token is one secret for all callers, with no identity, no
> revocation and no audit. It is the smallest thing that closes an open door,
> not an authentication system."*

**And on Railway it is mandatory**, because gate.py's rule is:

```
API_TOKEN set                    every route needs a bearer token
unset, ENVIRONMENT=development   open, and /health SAYS it is open
unset, anywhere else             REFUSED, because nobody chose
```

`ENVIRONMENT=production` + no `API_TOKEN` = an API that refuses to serve. That
is the right failure and it needs to be an intentional choice before the first
deploy, not a 503 discovered afterwards.

**The decision:** a public board with a token in the bundle is a public board.
If that is intended, say so on the page. If it is not, the session login
(`AUTH_EMAIL` / `AUTH_PASSWORD_HASH` / `SESSION_SECRET`) is the real gate and
the bearer token should not be in the bundle at all. **These two mechanisms
currently overlap and nobody has ruled on which is the door.**

### Does the database move off AWS?

Today both DSNs point at `52.17.75.29:5432`, and **`DATABASE_URL` and
`STAGING_DATABASE_URL` are byte-identical** — the hazard `run-backend.py`
already refuses to default around.

| | stay on AWS | move to Railway Postgres |
|---|---|---|
| migration | none | dump/restore + ledger verification |
| egress | Railway → public IP, every query | in-network |
| the identical-DSN problem | persists | **fixable during the move** |
| laptops keep working | yes, unchanged | yes, new DSN |
| `schema_migration` | unchanged | must be verified after restore |

**Recommendation: stay on AWS for the first deploy.** Moving the database and
introducing hosted fetch in one step means a failure has two candidate causes.
Move it second, and use the move to give staging a genuinely separate DSN —
which is worth more than the egress saving.

---

## 5 · Environment variables

**Per-deployment** — one value, set once: `DATABASE_URL`,
`STAGING_DATABASE_URL`, `RAW_STORE_PATH`, `ENVIRONMENT`, `PIPELINE_VERSION`,
`API_TOKEN`, `SESSION_SECRET`, `AUTH_EMAIL`, `AUTH_PASSWORD_HASH`,
`SESSION_TTL_HOURS`, `ALLOW_DEMO_LOGIN`, `USER_AGENT`, `REDDIT_PROVIDER`
(`reddit34`), `SCRAPER_PROVIDER` (`twitter241`), `RAPIDAPI_HOST`,
`OPENROUTER_BASE_URL`, `EXTRACTOR_MODEL`, `EXTRACTION_DAILY_BUDGET_USD`,
`ASK_RATE_PER_HOUR`, `FETCH_MAX_THREADS`, `FETCH_MAX_GITHUB_SEARCHES`.

**Per-person today** — `RAPIDAPI_KEY` (Reddit), `X_RAPIDAPI_KEY` (X),
`OPENROUTER_API_KEY`, `GITHUB_TOKEN`, `REDDIT_CLIENT_ID` /
`REDDIT_CLIENT_SECRET`. See §6.

---

## 6 · The keys — a decision, not a configuration

A hosted backend has one environment. **The moment it deploys, the three of you
stop having separate keys.** Four consequences, and the last one is the one to
rule on.

**1 · The quotas become shared.** 1,000,000 Reddit and 100,000 X per month stop
being per-person. Whoever's subscription goes in is the one that gets exhausted,
and `rapidapi_quota` starts reporting a single shared number — which it was
always shaped to do.

**2 · `/admin/usage` starts being true.** It reports spend for *"every machine
using this API key"*. With three keys that sentence has been quietly wrong;
with one it is right.

**3 · Whose subscriptions?** This is a billing question and I have no basis to
answer it. The options are: one person's keys (simple, unfair, and a single
point of both failure and expense), a project account (correct, and someone has
to create and pay for it), or per-service keys where the hosted backend gets its
own subscription and laptops keep theirs (most control, most to maintain).

**4 · `EXTRACTION_DAILY_BUDGET_USD` becomes four caps on one wallet, and that
is a defect rather than a trade-off.**

The cap is **per-process**. `judge/gate.py` already says this of the Ask box:
*"its cap is per-process, so an open one is an open wallet."* With a hosted
backend plus three laptops sharing one `OPENROUTER_API_KEY`, the effective daily
ceiling is **4 × the configured value**, and nothing anywhere computes that
number or would notice it being exceeded.

Three ways to resolve it, and they differ in more than effort:

- **(a) Accept it and divide the number.** Set each to a quarter. Cheapest,
  and wrong in the usual direction: it caps the *hosted* backend — the one that
  runs unattended — at the same share as a laptop somebody is watching.
- **(b) Give the hosted backend its own OpenRouter key.** The cap is then real
  for the unattended path, and the laptops share the other. No code change.
  **This is the smallest thing that makes the cap mean something.**
- **(c) Make the cap shared.** `spend_ledger` already records every call with
  `machine` and `usd`, so a cross-process daily total is a query, not a new
  mechanism. Correct, and the only option that survives adding a fifth caller.

**Recommendation: (b) now, (c) when a fifth caller appears.** But note what (b)
costs: two keys means `/admin/usage`'s cross-machine total covers one of them,
so the number that just became true in consequence 2 becomes partial again
unless the panel is taught about both.

---

## 7 · Order of work

1. **§3 decisions** — they determine what a volume has to hold, and everything
   else assumes a volume.
2. **§1 stop channel + §2 reaper** — one migration, one PR, because both add
   columns to `job_run` and the ledger's two-state rule is easier to keep right
   in one change than two.
3. Deploy backend with `ENVIRONMENT=production` and `API_TOKEN` set, database
   still on AWS, **fetch disabled** — confirms everything except the part that
   needed §1.
4. Enable fetch; confirm a deliberate restart mid-run leaves an `abandoned` row
   and a readable log.
5. Frontend, with §4's CORS decision made.
6. Database move, if it is happening, on its own.

**Not in this plan and needing their own decisions:** the nightly chain has no
scheduler today (nothing runs it), and `judge/ask` spends money from the backend
— a hosted one is reachable by anyone holding the bundled token.

---

*Measured 2026-09-14 against `DATABASE_URL` (shared staging) and this host's
`./raw_store` and `./_sweep_store`. Store composition from file sizes and
mtimes; orphan counts from `fetch_log`, `harvest_run` and `job_run`. The
per-store payload index is `restore_reddit_payload_refs.build_index()`.*
