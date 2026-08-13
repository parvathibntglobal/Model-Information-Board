# Contract sign-off — Phase 1

**Fifteen items for Engineer 2. One PR, not fifteen.**

*Raised from Engineer 1's Phase 1 remediation · branch `phase1-collection-foundation` · commit `4bd322d`*

---

`CLAUDE.md` says `contract/` should change perhaps five times in eight weeks,
each time on purpose. This is one of those times. Batching these into a single
PR is deliberate: eleven separate reviews of a shared interface is how two
people working in parallel start disagreeing about what the interface is.

**Nothing below has been applied.** `contract/tables.sql` and
`contract/seed_models.yaml` are untouched on the branch. The only contract file
Engineer 1 has written is `contract/registry.yaml`, which was approved
separately and is already committed.

Each item gives the exact edit. Apply them without inferring anything; where a
value cannot be supplied without a provider page, the item says so rather than
guessing.

| # | File | Status |
|---|---|---|
| 1 | `pyproject.toml` | ready to apply |
| 2 | `.python-version` (new) | ready to apply |
| 3 | `contract/seed_models.yaml` | **awaiting verification — do not apply** |
| 4 | `contract/seed_models.yaml`, `BUILD-PLAN.md` | rule ready; value needs a source |
| 5 | `contract/seed_models.yaml` | needs re-sourcing, no URLs supplied |
| 6 | `contract/seed_models.yaml` + `collect/registry/models.py` | ready, two files must land together |
| 7 | `contract/seed_models.yaml` | ready to apply |
| 8 | `contract/seed_models.yaml` | **blocker cleared**, needs a model choice |
| 9 | none | resolved, note only |
| 10 | `contract/seed_models.yaml` | ready to apply |
| 11 | `contract/tables.sql` | ready to apply |
| 12 | `.env.example` | ready to apply |
| 13 | `contract/sources.yaml` (new) | **blocks FR-9**; needs the ToS review first |
| 14 | `contract/tables.sql` | **blocks FR-10 and FR-11** |
| 15 | `contract/tables.sql` | comment only, no DDL; **lane interface** |

Items 12 to 15 were raised after the first eleven, from the Phase 2 readiness
assessment in [`phase2-readiness.md`](phase2-readiness.md) and from building
the raw store. Items 13 and 14 block harvest, so they matter more than their
position suggests. Item 15 blocks nothing but is the one item where
`collect/` and `judge/` must actually agree rather than merely not conflict.

---

## Before you apply anything: running the branch as it stands

**Items 5, 6, 7 and 10 are the ones that clear the two seed-loader gates.**
Until they land:

```
python -m collect.cli registry load-seed --allow-unsourced --allow-missing-spellings
```

**Both flags, not one.** The FR-2 source gate runs before the spelling gate,
so `--allow-missing-spellings` alone still fails — and it fails with a message
about *sources*, which reads like the wrong problem and sends you looking in
the wrong place. Neither is a code defect; both are these unapplied contract
fixes showing through.

| Command | Exit | Fails on |
|---|---|---|
| `registry load-seed` | 1 | `SourceCoverageError` (items 5 to 7) |
| `registry load-seed --allow-unsourced` | 1 | `SpellingCoverageError` (item 10) |
| `registry load-seed --allow-missing-spellings` | 1 | `SourceCoverageError` (items 5 to 7) |
| **both flags** | **0** | — |
| `registry load-seed --dry-run` | 0 | — |
| `registry check-sources` | **1** | **by design** — the exit code is the gap signal |
| `registry aliases` | 0 | — |
| `registry recompute-window` | 0 | — |
| `db init` | 0 | — |

`check-sources` exiting 1 is intended and worth knowing before it is wired
into CI as a pass/fail step, or a working command reads as a broken build
forever. The test suite is unaffected either way: it waives both gates
explicitly, with a docstring naming them as contract items.

---

## Item 1 · `pyproject.toml` declares no package discovery

`pip install -e .` fails outright. Setuptools refuses the flat layout because
four top-level directories are present (`collect`, `judge`, `contract`,
`fixtures`) and none is declared.

**Exact edit** — add to `pyproject.toml`:

```toml
[tool.setuptools.packages.find]
include = ["collect*", "judge*"]
```

Use the `find` directive. `packages = ["collect", "judge"]` looks equivalent
and is not: it misses every subpackage, so `collect.registry` and `judge.ask`
would not be installed.

> ### Warning for whoever applies this
>
> Today the dev extras cannot silently vanish, because the working install
> path is a requirements file generated from
> `dependencies + optional-dependencies['dev']`. **The moment `-e .` works,
> anyone who runs it without `[dev]` silently loses `ruff`, `mypy` and
> `pytest-asyncio`.**
>
> The failure mode is quiet: in week 2 the async adapter tests would not fail,
> they would not run. Whatever replaces the current workaround must install
> `.[dev]`, and CI should assert that `pytest-asyncio` imports.

## Item 2 · Pin the interpreter where tooling reads it

**Exact edit** — new file `.python-version` at repo root, one line:

```
3.11.9
```

`pyenv` and `uv` read it, so it enforces itself rather than documenting itself.

No change to `requires-python = ">=3.11"` or ruff's `target-version = "py311"`.
Those already carry the pin and are the values tooling actually consults. A
third location (a `contract/toolchain.yaml`, say) was considered and rejected:
three places that can disagree is worse than two, and an interpreter version is
not something the code reads at runtime, so it does not belong in `contract/`.

## Item 3 · `openai/gpt-4.1-mini` release date · AWAITING VERIFICATION

**Do not apply. This is not a proposed edit.**

`contract/seed_models.yaml:267` carries `release_date: 2025-07-18`. A
recollection of 14 April 2025 exists but has not been checked against the
OpenAI page, and nothing in this repository confirms either value.

`release_date` drives `f_launch` (the 21-day launch discount, frozen at
extraction) and `in_window`. An unsourced correction is worse than a
known-suspect value, because it looks settled.

**Action:** someone opens the provider page, records the URL and the date read,
and fills both the field and its `sources` entry together.

## Item 4 · `release_date` has no documented meaning

Two files disagree about the same model:

| | |
|---|---|
| `contract/seed_models.yaml:209` | `gemini-2.5-flash` → `2025-05-19` |
| `BUILD-PLAN.md:391` | `gemini-2.5-flash` → `2025-06-17` |

One is preview, one is GA. The field is load-bearing for two mechanisms, so the
ambiguity is not cosmetic.

**Exact edit** — add above `models:` in `contract/seed_models.yaml`:

```yaml
# ----------------------------------------------------------------------------
#  `release_date` means the date this version became GENERALLY AVAILABLE at
#  its canonical id. Not the preview date, not the announcement date.
#
#  It drives two things, which is why the distinction matters:
#    - f_launch, the 21-day launch-window discount, frozen at extraction
#    - in_window, the trailing-window filter (contract/registry.yaml)
#
#  Where a model previewed first, record the GA date here and note the
#  preview date in a comment beside it.
# ----------------------------------------------------------------------------
```

Then reconcile the two files to whichever value the rule selects. **Naming the
rule needs no source; choosing the value does.**

## Item 5 · Two price citations point at the wrong model

| Lines | Model | Currently cites |
|---|---|---|
| 169, 170 | `deepseek/deepseek-r1` | a **Gemini** cost-analysis blog |
| 256, 257 | `anthropic/claude-haiku-4-5` | a **Claude Opus 5** pricing blog |

Both `price_in` and `price_out` on both models. A citation pointing at a
different model is worse than no citation: it passes the FR-2 coverage check
while asserting nothing about the value it supposedly sources.

**No replacement URLs are supplied here.** Inventing a source is the one
failure this project cannot absorb. Each needs the provider's own pricing page,
with the retrieval date set to the day it is read.

Lower priority, same family of problem: line 109,
`gemini-2.5-pro.advertised_context`, cites the same third-party Gemini blog. At
least it is the right model, but a provider page would be better.

## Item 6 · The trailing `#` carries meaning nothing can read

32 of the 40 `sources` lines end with a bare `#`. The 8 without are provider
pages — `mistral.ai/news`, `api-docs.deepseek.com`, `anthropic.com/pricing`,
`anthropic.com/news` — with one exception: `gemini-2.5-flash.release_date`
cites Wikipedia and carries no marker.

So the convention means "not read off a provider page", and it is already
inconsistent after one editing pass. A convention that a loader cannot read
degrades silently.

**Exact edit** — promote it to a field:

```yaml
# before
price_in:  { url: "https://example.com/blog", retrieved_at: "2026-08-12" } #
# after
price_in:  { url: "https://example.com/blog", retrieved_at: "2026-08-12", provider_page: false }
```

**These two files must land in the same commit.** `SourceRef` is
`extra="forbid"`, so the YAML change alone breaks the load. Engineer 1 will add
to `collect/registry/models.py`:

```python
class SourceRef(BaseModel):
    url: str
    retrieved_at: date
    #: False when the value came from a third party rather than the provider's
    #: own page. Third-party prices go stale silently.
    provider_page: bool = True
```

**Alternative if you prefer:** delete all 32 markers and accept that source
quality is untracked. That is a worse answer, but it is a coherent one, and it
is better than a marker nobody can query.

## Item 7 · The header contradicts the checklist below it

`contract/seed_models.yaml` opens by saying slot 10 is "deliberately empty" and
that every number needs verifying before the first run. The checklist at the
foot is fully ticked, including *"Every `# VERIFY` replaced with a value read
off a provider page"* and *"Every `sources` entry has a real URL and a real
date"*.

Both cannot be true. The measured position says the checklist is the wrong one:

```
$ py -m collect.cli registry check-sources
seed file : 10 models, version 1.0
FR-2      : 40/130 populated fields carry a source
```

**Exact edit** — untick checklist items 2, 3 and 5, and replace the header
paragraph beginning "⚠ VERIFY EVERY NUMBER" with a statement of the real
position: 40 of 130 populated fields carry a source, 32 of those 40 cite third
parties rather than provider pages, and the file is loaded with
`--allow-unsourced` until that changes.

Slot 10 is in fact filled (`deepseek/deepseek-v4-flash`), so that sentence in
the header is simply stale and should go.

## Item 8 · Swap the open-weight fixture · **BLOCKER CLEARED**

`deepseek/deepseek-v3` was released 2024-12-26 and falls outside the trailing
18-month window as of 2026-08-12. It is the only open-weight fixture, so that
slot is now untested: open weights are the case where price and latency are
properties of the serving host rather than the model.

**Exact edit** — replace the `deepseek/deepseek-v3` entry with an open-weight
model released after **2025-02-12**, keeping `slot: open-weight` and the
comment about `hosted_by` being required in claims.

> ### The timing constraint on this item is satisfied
>
> This was previously blocked behind Task 1, because swapping the fixture
> changes a `release_date`, and alias ids used to be keyed on `valid_from` —
> so the swap would have duplicated every alias row for that model.
>
> **Task 1 landed in `4bd322d`.** Alias ids are now keyed on content, not on
> the validity window, and `_sync_alias` closes any superseded live row before
> appending. Changing a `release_date` no longer touches alias rows at all.
>
> **Do not stop at the caveat. It no longer applies.**

One expected consequence: `tests/test_registry_window.py::test_the_open_weight_slot_leaves_the_window`
**will fail by design** once this is applied. Its failure message begins
"THIS IS NOT A REGRESSION" and tells you to delete it. That test exists only to
keep this gap visible until it is closed.

## Item 9 · The declared Python floor was never tested · RESOLVED, NOTE ONLY

**No edit required.** `requires-python = ">=3.11"` and `target-version = "py311"`
were never exercised — development ran on 3.14 while claiming 3.11 support.
PEP 701 means f-string syntax valid on 3.12 is a `SyntaxError` on 3.11, and
`tests/test_lane_boundary.py` calls `ast.parse` on every file in `collect/`, so
a 3.12-only construct would have surfaced on Engineer 2's machine as a parse
failure inside a lane-boundary test — a confusing way to learn about a syntax
problem.

The full suite now passes on **3.11.9 / pytest 9.1.1**, matching Engineer 2's
interpreter. CI should pin the same version; item 2 makes that self-enforcing.

## Item 10 · `deepseek-v4-flash` is unsearchable, and declares a duplicate

`contract/seed_models.yaml:342`. **Two problems in one model, one edit.**

1. **No concatenated form.** `deepseekv4flash` can never be found. Search APIs
   have no fuzzy operator, so an undeclared spelling is not a degraded result,
   it is silence — which renders identically to nobody having discussed the
   model.
2. **`"deepseek v4 flash"` repeats the `surface`**, so the model declares four
   distinct spellings rather than five.

This is the fixture whose entire purpose is exercising the `just-launched`
path, so it is the one that most needs to be findable.

**Exact edit:**

```yaml
# before
variants: ["deepseek-v4-flash", "v4 flash", "deepseek v4", "deepseek v4 flash"]
# after
variants: ["deepseek-v4-flash", "deepseekv4flash", "v4 flash", "deepseek v4"]
```

Until this lands, `registry load-seed` requires `--allow-missing-spellings`,
and `tests/test_registry_spelling.py::test_exactly_one_model_is_missing_a_spelling`
pins the gap so it cannot be forgotten. That test should be updated, not
deleted, when a second model ever fails the same check.

## Item 11 · `coverage_gap` table · new, in `contract/tables.sql`

`collect/registry/load.py` already emits `CoverageGap(kind, subject, detail)`
records from `LoadReport.coverage_gaps()`. They currently have nowhere to go.

Writing them to a JSON artifact for the coverage page to read was considered
and rejected: it would invent a second interface across the lane boundary,
which `CLAUDE.md` is most explicit about. The sanctioned crossing is
`document` plus `thread_context`, and widening it is a contract decision rather
than an implementation one.

**Exact edit** — append to `contract/tables.sql`:

```sql
-- ============================================================================
--  COVERAGE — what the board does not know.
--  collect/ fills this. judge/ reads it for the coverage page.
--
--  Gaps that live only in CLI output become permanent the first time somebody
--  scripts the load. FR-11's principle generalises past budget caps: a gap
--  nobody can see reads as "we looked everywhere" when we did not.
-- ============================================================================

CREATE TABLE coverage_gap (
  id               text PRIMARY KEY,
  kind             text NOT NULL,
  subject          text NOT NULL,   -- canonical_id. Deliberately NOT a foreign
                                    -- key: a gap can concern a model that is
                                    -- not in the registry, which is itself one
                                    -- of the things worth reporting.
  detail           text NOT NULL,
  observed_at      timestamptz NOT NULL DEFAULT now(),
  pipeline_version text NOT NULL,   -- every derived row carries one, so a
                                    -- reporting change is re-runnable

  -- An unconstrained `kind` is how a fifth gap type gets added later without
  -- the coverage page knowing it exists. Adding one is then a deliberate
  -- contract change with a review attached.
  CONSTRAINT coverage_gap_kind_ck CHECK (kind IN (
    'unsourced-field',
    'missing-spelling',
    'out-of-window',
    'unknown-release-date'
  )),

  -- A nightly re-run must not multiply the same gap.
  CONSTRAINT coverage_gap_unique UNIQUE (kind, subject, detail, pipeline_version)
);
CREATE INDEX coverage_gap_kind_idx ON coverage_gap (kind);
```

**Current gap volume**, so the size of the table is not a surprise:

| kind | count |
|---|---|
| `unsourced-field` | 90 |
| `missing-spelling` | 1 |
| `out-of-window` | 3 |
| `unknown-release-date` | 0 |
| **total** | **94** |

Items 3 to 8 and 10 shrink that number. Item 11 is what makes the shrinking
visible to anyone who is not reading the terminal.

---

## Item 12 · `.env.example` is missing two variables

Both were introduced by the dev-database work in this session and are already
referenced by committed code (`tests/conftest.py`).

**Exact edit** — append to `.env.example`:

```bash
# ── tests ────────────────────────────────────────────────────────────────
# The write-path tests DROP SCHEMA public CASCADE, so this is deliberately
# separate from DATABASE_URL. `scripts/dev-postgres.ps1` writes it into a
# gitignored .env.test for you. See docs/dev-database.md.
TEST_DATABASE_URL=

# Set to 1 to downgrade a missing test database from a failure to a skip.
# The run then prints WRITE PATH NOT COVERED in the summary. Do not put this
# in a shell profile: a silently skipped write path is how six defects
# reached a commit.
ALLOW_MISSING_TEST_DB=
```

Kept separate from item 1 on purpose. Item 1 edits `pyproject.toml`; mixing
two root files into one item makes the review harder rather than shorter.

---

## Item 13 · `contract/sources.yaml` · **BLOCKS FR-9**

`watermark.source_id` references `source(id)`. **No `source` row exists, and
no code path can create one**, so the first `INSERT INTO watermark` fails on
the foreign key. FR-9's durable cursors cannot store their first row.

This would surface on the first adapter run as a foreign key violation and
read as an adapter bug rather than a missing seed.

`source.base_trust` and `source.tos_notes` are both `NOT NULL`, deliberately.
Base trust values are **weights**, so rule 5 puts them in `contract/`.

**Exact edit** — new file `contract/sources.yaml`:

```yaml
# ============================================================================
#  Harvest sources — the three platforms, their trust weight, and the terms
#  review NFR-5 requires.
#
#  SHARED. Changes go through a PR.
#
#  Rule 5: base_trust is a weight, so it lives here rather than in code.
#  Loaded into the `source` table by collect/, the same way seed_models.yaml
#  is loaded into model_version.
#
#  `tos_notes` is NOT NULL in the schema on purpose: NFR-5 requires the terms
#  be reviewed and recorded per source, and a nullable column would let that
#  be skipped.
# ============================================================================

version: "1.0"

sources:
  - id: github
    platform: github
    endpoint: https://api.github.com
    base_trust: 0.95
    tos_notes: >-
      REVIEW REQUIRED before first harvest. Record: API terms URL, date read,
      rate limit observed, and whether quote-plus-attribution republication
      is permitted.

  - id: blogs
    platform: blog
    endpoint: null           # per-feed; discovered feeds become source rows
    base_trust: 0.90
    tos_notes: >-
      REVIEW REQUIRED. RSS and sitemaps only, robots.txt respected, no
      paywall circumvention. A source whose terms forbid this use is dropped,
      not worked around.

  - id: reddit
    platform: reddit
    endpoint: https://oauth.reddit.com
    base_trust: 0.85
    tos_notes: >-
      REVIEW REQUIRED. Their terms prohibit scraping, so the official API is
      mandatory. Record the current rate limit and free-tier eligibility
      rather than trusting BUILD-PLAN's 60/min figure.
```

> **The ToS review gates this item.** `tos_notes` cannot honestly be filled
> before someone reads each platform's current terms, and the column is
> `NOT NULL` precisely so that cannot be deferred. So the review is not a
> parallel task — it is the thing standing between here and a working
> `watermark` row.

Whether the ~40 practitioner blog feeds seed from this file or from a separate
one is an open question worth settling here: the **initial** list is config,
but feeds discovered from harvested links are data and belong in the `source`
table. A list that lives in two places diverges.

---

## Item 14 · `harvest_run` table · **BLOCKS FR-10 AND FR-11**

Three requirements have nowhere to write, and one table serves all three.

- **FR-9** *resume with no gap and no refetch*: a cursor alone cannot say
  whether a query paused mid-pagination or reached the end of its results. On
  resume the first must be continued and the second must not.
- **FR-10** *every adapter reports its own yield per run*: `source.last_yield`
  is a single `int` with no history, so there is nothing to compare against. A
  drop is only visible relative to what came before. `collect/CLAUDE.md`
  requires a 14-day burn-in before the related alert arms, for exactly this
  reason — you cannot compute σ without a baseline.
- **FR-11** *log and display any harvest truncated by a budget cap, naming the
  model and query*: nothing in the schema stores it.

**Exact edit** — append to `contract/tables.sql`:

```sql
-- ============================================================================
--  HARVEST RUNS — one row per source, per query, per run. collect/ fills it.
--
--  Serves three requirements that would otherwise each need their own place:
--    FR-9   whether a query finished or paused mid-pagination
--    FR-10  yield history, so a drop is visible as a drop
--    FR-11  truncation by a budget cap, named rather than silent
-- ============================================================================

CREATE TABLE harvest_run (
  id               text PRIMARY KEY,
  source_id        text NOT NULL REFERENCES source(id),
  query_key        text NOT NULL,   -- matches watermark.query_key

  started_at       timestamptz NOT NULL DEFAULT now(),
  finished_at      timestamptz,

  items_fetched    int NOT NULL DEFAULT 0,
  items_kept       int NOT NULL DEFAULT 0,   -- FR-10: yield
  http_errors      int NOT NULL DEFAULT 0,

  -- FR-9. NULL while running; false when paused mid-pagination; true when
  -- the query reached the end of its results and must not be resumed.
  exhausted        boolean,

  -- FR-11. NULL when the harvest ran to completion. Naming the cap that cut
  -- it short is what stops silent truncation reading as "we looked
  -- everywhere".
  truncated_by     text,

  pipeline_version text NOT NULL,

  CONSTRAINT harvest_run_truncated_ck
    CHECK (truncated_by IS NULL OR truncated_by IN ('query-budget', 'rate-limit',
                                                    'time-budget', 'extraction-budget'))
);
CREATE INDEX harvest_run_source_query_idx ON harvest_run (source_id, query_key, started_at DESC);
CREATE INDEX harvest_run_truncated_idx ON harvest_run (truncated_by)
  WHERE truncated_by IS NOT NULL;
```

**Also add to `watermark`**, so resumption can read the distinction without
joining:

```sql
ALTER TABLE watermark ADD COLUMN exhausted boolean NOT NULL DEFAULT false;
```

> This overlaps with the "cron plus a jobs table" decision recorded in
> `CLAUDE.md` and `pyproject.toml`. See the known-gaps note below: the two
> should be settled together rather than becoming two tables that half
> overlap.

---

## Item 15 · `text_ref` has no documented convention · **LANE INTERFACE**

`contract/tables.sql` gives `document.text_ref text NOT NULL -- pointer into
the raw store` and, separately, `content_hash text NOT NULL` with no comment.
Two columns, and the schema never says how they differ. `collect/` writes
both; `judge/` reads `text_ref` to fetch the text it verifies quotes against.
That makes the convention a **lane interface**, so it is agreed rather than
assumed.

Two readings are coherent:

- **A — `text_ref` is the hash.** The store is content-addressed, so a
  pointer into it *is* the hash. But then the two columns hold the same value
  and one is dead weight.
- **B — `text_ref` is a location, `content_hash` is identity.** Storage can
  move (filesystem now, an object store later) without rewriting what
  anything *is*.

**B is implemented, and NFR-6 is why it is not a preference.** Its acceptance
reads *"tombstone a document; its quotes vanish next run, only the content
hash remains."* That only parses if the hash and the stored bytes are
separable — under A there is nothing to delete that leaves a hash behind, so
A cannot satisfy an acceptance criterion the plan has already committed to.

**Exact edit** — comment only, **no DDL**:

```sql
  -- `text_ref` LOCATES the payload; `content_hash` IDENTIFIES it. They are
  -- separate columns because NFR-6 requires the hash to outlive the bytes:
  -- tombstoning deletes the payload and keeps the hash as the audit record.
  -- Storage can therefore move without rewriting identity.
  --   text_ref     "raw/sha256/ab/cd/abcd...ef"   (collect/rawstore.py)
  --   content_hash "abcd...ef"
  text_ref                text NOT NULL,
  content_hash            text NOT NULL,
```

The same convention applies to `thread_context.flattened_text_ref`, which
uses the `flattened/` namespace of the same store.

> **Disagreeing is cheap.** `collect/rawstore.py` keeps its public surface
> hash-first: `put()` returns both the ref and the hash, and `parse_ref()`
> recovers the hash from any ref. If you prefer reading A, the change is
> **one column write** at the call site, not a redesign of the store. Say so
> and it will be changed.

This is the only outstanding question on the raw store. Everything else about
it is `collect/`'s own business and needs no sign-off.

---

## Known gaps, recorded but not proposed

Not everything found needs a decision now. These are written down so they are
not rediscovered.

| Gap | Blocking from | Note |
|---|---|---|
| **Reddit access deferred** | **Week 3** | The company holds the account; access requested later. Adapter not being built. Week 3 because FR-6's acceptance is all three adapters returning content, and FR-17's cross-platform identity clustering cannot be tested with one social platform. Blogs, not Reddit, carry the structurally-positive channel FR-6 depends on. Detail in [`phase2-readiness.md`](phase2-readiness.md) §6 |
| **No jobs table** | **Week 7**, the nightly job chain | `CLAUDE.md` and `pyproject.toml` both record *cron plus a jobs table, no workflow engine*. `contract/tables.sql` defines 24 tables and none is that. Nothing needs it until the nightly chain, but it overlaps with `harvest_run` (item 14) and the two should be designed together rather than separately |
| **Blog feed list has no home** | Week 2, the blog adapter | Initial list is config, discovered feeds are data. Settle alongside item 13 |
| **No robots.txt handling** | Week 2, the blog adapter | NFR-5 requires it. `urllib.robotparser` is stdlib, so no dependency. Collection lane's own work, not a contract item |
| **Raw store does not exist** | **Immediately**, before any adapter | `document.text_ref` is `NOT NULL` and points into it. Collection lane's own work, top of Phase 2 |
