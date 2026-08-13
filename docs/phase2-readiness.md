# Phase 2 readiness — what harvest needs that does not exist

**A gap list, not an implementation.** No adapter code has been written.

*Engineer 1 · assessed at commit `a8d4635` plus the uncommitted dev-database work*

---

## Summary

| | Status |
|---|---|
| Credentials to create | `GITHUB_TOKEN`, `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` |
| `.env.example` | covers all three; **missing two test variables** |
| FR-7 harvest queries | **do not exist.** Proposed home and shape below |
| FR-9 durable cursors | `watermark` exists; **four gaps**, one of them blocking |
| NFR-5 User-Agent | variable exists, **is not enforced and nothing reads it** |
| Beyond the brief | raw store, `source` seeding, jobs table, robots.txt — all absent |

Nothing here needs deciding today except the credentials, which take longer to
obtain than to use.

> ### Running the seed loader on this branch
>
> **`registry load-seed` needs two flags, not one:**
>
> ```
> python -m collect.cli registry load-seed --allow-unsourced --allow-missing-spellings
> ```
>
> The FR-2 source gate runs **before** the spelling gate, so
> `--allow-missing-spellings` alone still fails, and it fails with a message
> about *sources* — which reads like the wrong problem and sends you to the
> wrong file. Both gates are unapplied contract fixes, not code defects, and
> both clear when sign-off items 5 to 7 and 10 land. Full exit-code matrix in
> §7.
>
> Separately: **`registry check-sources` exits 1 by design.** The exit code is
> the gap signal. Do not wire it into CI as a pass/fail step without knowing
> that, or a working command reads as a broken build forever.

---

## 1 · Credentials the adapters will require

Named exactly, so they can be created while the contract PR is in review.

### GitHub — `GITHUB_TOKEN`

A personal access token. **`public_repo` scope is sufficient**; the adapter
only reads public issues and discussions. Five minutes to create.

Rate limit is the reason it is not optional: unauthenticated search is 10
requests per minute, authenticated is 30. At the current budget of 648 queries
per platform (see the defect report, defect 6), that is 22 minutes
authenticated against 65 unauthenticated.

### Reddit — `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`

A **script** app registered at `reddit.com/prefs/apps`. Both values appear on
that page immediately after creation.

**No username or password variable is proposed**, and this is a decision worth
confirming rather than assuming. Reddit's OAuth offers an application-only
grant that needs just the id and secret, which is enough for read-only
harvesting. A user-context grant would additionally need `REDDIT_USERNAME` and
`REDDIT_PASSWORD`.

> **To verify before building the adapter**, because it moves and the repo
> cannot tell us: the current grant types available to a script app, the
> current rate limit, and whether the intended use falls inside Reddit's free
> tier. `BUILD-PLAN.md` records 60 requests per minute; that figure should be
> re-read off Reddit's current API terms rather than trusted. NFR-5 requires
> the terms be reviewed and recorded per source anyway, and `source.tos_notes`
> is `NOT NULL` precisely so that cannot be skipped.

### Blogs — none

RSS and sitemaps, no authentication. This is why `docs/logic-and-workflow.md`
calls it the cheapest adapter and schedules it early. It needs a **seed feed
list** rather than a credential; see gap 6 below.

---

## 2 · `.env.example` coverage

Present and correct for all three platforms: `GITHUB_TOKEN`,
`REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `USER_AGENT`, `RAW_STORE_PATH`.

**Two variables are missing**, both introduced by the dev-database work:

```bash
# ── tests ────────────────────────────────────────────────────────────────
# The write-path tests DROP SCHEMA public CASCADE, so this is deliberately
# separate from DATABASE_URL. `scripts/dev-postgres.ps1` writes it into a
# gitignored .env.test for you. See docs/dev-database.md.
TEST_DATABASE_URL=

# Set to 1 to downgrade a missing test database from a failure to a skip.
# The run then prints WRITE PATH NOT COVERED. Do not put this in a shell
# profile: it is how six defects reached a commit.
ALLOW_MISSING_TEST_DB=
```

`.env.example` is at the repository root, outside the collection lane, so this
is proposed rather than applied. It is small enough to fold into the contract
PR as a twelfth item, or to hand to whoever applies item 1.

---

## 3 · FR-7 · the harvest query set does not exist

**FR-7:** every tracked capability has at least one harvest query, checked
automatically, failing the build otherwise.
**FR-8:** every capability has negative-stance queries.

`contract/capabilities.yaml` defines **12 capabilities**. There are **zero
queries** anywhere in the repository. Harvest is entirely query-driven, so a
capability nobody searches for has empty cells forever — which means the FR-7
check currently fails 12 out of 12.

### Where it belongs

**`contract/queries.yaml`.** Rule 5 puts filter rules and config in versioned
YAML, and this is the highest-leverage config in the pipeline: it decides what
the board can ever know. It is also shared in effect, because a capability
added by either lane is a no-op until a query exists for it.

### What shape it takes

Keyed by capability, with an explicit stance, because FR-8's check needs to
distinguish them mechanically rather than by reading the template:

```yaml
version: "1.0"

queries:
  - capability: tool_calling.schema_accuracy
    stance: negative
    template: >-
      "{alias}" (tool calling OR function calling)
      (fails OR broken OR "invalid json" OR schema OR "infinite loop")

  - capability: summarization.fidelity
    stance: negative
    template: >-
      "{alias}" (summar* OR condense OR digest)
      (missed OR "left out" OR "made up" OR hallucinat* OR dropped)

  - capability: summarization.fidelity
    stance: positive
    template: >-
      "{alias}" (summar* OR condense) (works OR "good enough" OR replaced)

# The substitution pattern is cross-capability and gets its own pass plus a
# vetting bonus. "We moved our summariser to X and it held" is a direct report
# of the decision this product exists to inform.
substitution:
  - template: >-
      ("replaced {alias_b} with {alias}" OR "switched from {alias_b} to {alias}")
```

Templates for all twelve already exist in prose in
`docs/logic-and-workflow.md` §6 and can be lifted directly.

### The automated check

A test asserting two things, both trivially checkable:

1. every `key` in `capabilities.yaml` appears as a `capability` in
   `queries.yaml` — **FR-7**
2. every capability has at least one entry with `stance: negative` — **FR-8**

Failing that test is the "fails the build" FR-7 asks for. Adding a capability
without its query then stops being a silent no-op.

**Not created.** `contract/` needs sign-off, and the templates want a review
pass from whoever knows what practitioners actually write.

---

## 4 · FR-9 · `watermark` exists, with four gaps

**FR-9:** persist pagination cursors durably; resume exactly where consumption
paused. *Accept:* kill a harvest mid-run; it resumes from the stored cursor
with no gap and no refetch.

```sql
CREATE TABLE watermark (
  source_id       text NOT NULL REFERENCES source(id),
  query_key       text NOT NULL,
  last_run_at     timestamptz,
  cursor          text,
  PRIMARY KEY (source_id, query_key)
);
```

The shape is right: per source, per query, one durable cursor. `cursor text`
holds a GitHub page number or a Reddit `after` fullname equally well.

### Gap A — nothing seeds `source`, and the FK blocks writes · **BLOCKING**

`watermark.source_id` references `source(id)`, and **no `source` row exists or
can be created by any current code path**. The first `INSERT INTO watermark`
fails on the foreign key.

`source.base_trust` and `source.tos_notes` are both `NOT NULL`, which is
deliberate — the trust weights (github 0.95, blog 0.90, reddit 0.85) and the
NFR-5 terms review cannot be skipped. But base trust values are *weights*, so
rule 5 puts them in `contract/`, and nothing there defines them.

**Proposal:** `contract/sources.yaml` carrying the three platforms with
`base_trust` and `tos_notes`, loaded by `collect/` the same way
`seed_models.yaml` is. This is a contract addition and needs sign-off — it is
**item 13** of [the sign-off package](contract-signoff-phase1.md).

> **The per-source terms review gates this fix, and therefore gates FR-9.**
> `tos_notes` is `NOT NULL`, and it cannot honestly be filled before someone
> has read each platform's current terms and recorded what they say. So the
> review is not a task that runs in parallel with building the adapters: it
> stands between here and the first `watermark` row. It is also where the
> Reddit rate limit gets established rather than inherited from
> `BUILD-PLAN.md`.

### Gap B — no way to tell "paused" from "finished"

FR-9's acceptance says *resume with no gap and no refetch*. A cursor alone
cannot distinguish a query that stopped halfway through pagination from one
that reached the end of its results. On resume the first is continued and the
second must not be.

**Proposal:** add `exhausted boolean NOT NULL DEFAULT false` to `watermark`.

### Gap C — FR-10 cannot compute a trend

**FR-10:** every adapter reports its own yield per run; a sudden drop means
broken markup. `source.last_yield int` stores **one** number with no history,
so there is nothing to compare against. A drop is only visible as a drop
relative to what came before.

`collect/CLAUDE.md` also specifies a **14-day burn-in** before the triage
survival alert arms, because there is no baseline to compute σ against on day
one. The same reasoning applies here and needs the same thing: history.

**Proposal:** a `harvest_run` table recording per run, per source, per query:
started, finished, items fetched, items kept, HTTP errors, and whether it was
truncated. That single table serves FR-10's trend, FR-11's truncation display
and the coverage page at once.

### Gap D — FR-11 has nowhere to record truncation

**FR-11:** log and display any harvest truncated by a budget cap, naming the
model and query. Nothing in the schema stores that. Covered by the
`harvest_run` proposal above via a `truncated_by` column.

> This is the same class of gap as coverage sign-off item 11: a consequence
> that exists only in logs becomes invisible, and silent truncation reads as
> "we looked everywhere" when we did not.

### A note on `query_key`, which is collect's decision and not a schema gap

`query_key` must be **stable across runs and across a change to the alias
list**, or resumption silently restarts. It needs a documented convention —
something like `{platform}:{alias_normalized}:{capability}:{stance}` — using
the normalised alias rather than the surface, so re-spelling a variant does
not orphan its cursor.

---

## 5 · NFR-5 · the User-Agent is declared but not enforced

**NFR-5:** identifying User-Agent with a contact URL, on every request, to
every platform. Not optional.

`collect/config.py` carries the field:

```python
user_agent: str
...
user_agent=os.getenv("USER_AGENT", ""),
```

Two problems:

1. **The default is the empty string.** An unset variable produces a request
   with no identifying header rather than a refusal.
2. **Nothing reads it.** Confirmed by grep: `user_agent` appears only in
   `config.py`. There is no HTTP client yet, so this is expected — but it
   means the first adapter is where the guarantee is either built in or lost.

**Proposal, matching the two assertions this lane already has.**
`assert_no_fixtures` refuses to start on seeded rows; `assert_contract_backed`
refuses on unversioned config. This wants the same shape:

```python
def assert_identifying_user_agent(settings) -> None:
    """NFR-5. Refuse to make any request without an identifying UA."""
```

Checking non-empty, and that it contains a contact URL (`http://` or
`https://`), since "modelboard/0.1" alone identifies nobody. It should fire in
the HTTP client constructor rather than at startup, so no code path can build
a client that lacks it.

The three-layer pattern from `docs/dev-database.md` applies: a rule with no
enforcement is a comment.

---

## 6 · Gaps beyond the five questions asked

Found while checking the above. All block or shape Phase 2.

### The raw store does not exist · **BLOCKING**

`document.text_ref` is `NOT NULL` and points into an immutable,
content-hash-addressed store. `RAW_STORE_PATH` is in `.env.example` and
`Settings.raw_store_path` is populated, but **there is no store
implementation** — `collect/` contains only `config`, `db`, `ids`, `cli` and
`registry/`.

Adapters fetch payloads and must persist them immutably before anything else
happens, so this is a prerequisite for the first adapter rather than a Phase 3
concern. `collect/ids.py::content_hash` already provides the addressing.

Small, and needed first.

### No jobs table

`pyproject.toml` and `CLAUDE.md` both record the decision: *cron plus a jobs
table, no workflow engine.* `contract/tables.sql` defines 24 tables and
**none of them is a jobs table.** Harvest cadence (daily GitHub, weekly Reddit
and blogs, immediate sweep on launch, re-harvest on `possibly-changed`) has
nowhere to record what ran.

Arguably it merges with the `harvest_run` proposal in gap C. Worth deciding
once rather than adding two tables that overlap.

### No blog seed list

`docs/logic-and-workflow.md` calls for provider engineering blogs, agent
framework blogs and ~40 hand-picked practitioner blogs, growing from links
found in already-harvested content.

That last clause matters for where it lives: the **initial** list is config,
but discovered feeds are data and belong in the database. Proposal: seed from
`contract/sources.yaml` (gap A), then write discovered feeds as `source` rows.
Worth agreeing before either is built, because a list that lives in two places
diverges.

### No robots.txt handling

NFR-5 requires it, and it applies to the blog adapter specifically — GitHub
and Reddit are official APIs. Python's standard library has
`urllib.robotparser`, so **this adds no dependency**. Noting it because it is
easy to defer past the point where content has already been fetched.

---

## 7 · What Engineer 2 hits on first running this branch

`check_spelling_coverage` fails on the real seed file, because
`deepseek-v4-flash` declares no concatenated form (sign-off item 10). Measured
exit codes, so nobody has to guess:

| Command | Exit | Fails on |
|---|---|---|
| `registry load-seed` | 1 | `SourceCoverageError` |
| `registry load-seed --allow-unsourced` | 1 | `SpellingCoverageError` |
| `registry load-seed --allow-missing-spellings` | 1 | `SourceCoverageError` |
| **`registry load-seed --allow-unsourced --allow-missing-spellings`** | **0** | — |
| `registry load-seed --dry-run` | 0 | — |
| `registry check-sources` | 1 | by design; it reports the gap |
| `registry aliases` | 0 | — |
| `registry recompute-window` | 0 | — |
| `db init` | 0 | — |

**Both flags are needed, not just the spelling one.** The FR-2 source gate
runs first, so `--allow-missing-spellings` alone still fails — and it fails
with a message about sources, which reads like the wrong problem.

`check_spelling_coverage` has exactly one caller: `load_seed(strict_spelling=True)`.
Nothing else in the codebase touches it. The dry-run path builds rows without
calling `load_seed`, which is why it is unaffected.

The test suite is unaffected: the `_load` helper in
`tests/test_registry_load_db.py` passes both gates off with a docstring
naming them as contract items, and `tests/test_registry_spelling.py` asserts
the failure deliberately.

`registry check-sources` exiting 1 is intended — it is a gap report, and the
exit code is the gap signal. Worth knowing before it is wired into CI as a
pass/fail step.

Both gates disappear once items 5 to 7 and item 10 are applied. Neither is a
code defect.

---

## What is actually blocking

Two things stop the first adapter from being written at all:

1. **The raw store**, since a fetched payload has nowhere to go.
2. **`source` seeding**, since `watermark` cannot take a row without it, so
   FR-9 cannot be satisfied.

Everything else can be built alongside. Neither is large; both are easy to
discover late, at which point the adapter has to be restructured around them.
