# Contract sign-off — Phase 1

**Twenty items for Engineer 2. One PR, not twenty.**

*Raised from Engineer 1's Phase 1 remediation · branch `phase1-collection-foundation` · commit `4bd322d`*

---

`CLAUDE.md` says `contract/` should change perhaps five times in eight weeks,
each time on purpose. This is one of those times. Batching these into a single
PR is deliberate: eleven separate reviews of a shared interface is how two
people working in parallel start disagreeing about what the interface is.

**All twenty are applied or resolved.** Items 17, 18 and 20 were ruled on in
[`contract-signoff-phase1-response.md`](contract-signoff-phase1-response.md) and
built on `phase2-harvest-foundation`.

Each item gives the exact edit and its current state. Where a value cannot be
supplied without a provider page, the item says so rather than guessing.

| # | File | Status |
|---|---|---|
| 1 | `pyproject.toml`, `.gitignore` | ✅ **applied** — `pip install -e .` verified working |
| 2 | `.python-version` (new) | ✅ **applied** |
| 3 | `contract/seed_models.yaml` | ✅ **applied** — OpenAI's page says 2025-04-14 |
| 4a | `contract/seed_models.yaml` | ✅ **applied** — the rule is documented |
| 4b | `contract/seed_models.yaml` | ✅ **resolved** — both files now say 2025-06-17 |
| 5 | `contract/seed_models.yaml` | ✅ **applied** — both models turned out retired |
| 6 | `contract/seed_models.yaml` + `collect/registry/models.py` | ✅ **applied** — 9 true / 31 false, derived |
| 7 | `contract/seed_models.yaml` | ✅ **applied** — three boxes unticked |
| 8 | `contract/seed_models.yaml` | ✅ **applied** — `mistral-large-3`, Apache 2.0 |
| 9 | none | ✅ resolved, no edit |
| 10 | `contract/seed_models.yaml` | ✅ **applied** — spelling gate now passes |
| 11 | `contract/tables.sql` | ✅ **applied** — `coverage_gap` |
| 12 | `.env.example` | ✅ **applied** |
| 13 | `contract/sources.yaml` (new) | ✅ **applied** with placeholders + a gate |
| 14 | `contract/tables.sql` | ✅ **applied** — `harvest_run`, `watermark.exhausted` |
| 15 | `contract/tables.sql` | ✅ **applied** — comment only |
| 16 | `contract/seed_models.yaml` | ✅ **applied** — FR-2 now 88/88 |
| 17 | `contract/tables.sql` | ✅ **applied** — comment only, no DDL |
| 18 | `contract/tables.sql` + `collect/` | ✅ **applied** — `price_tier` built, `price_in` NULL when tiers exist |
| 19 | none | ✅ **resolved** — advertised half sourced; contradiction is week 5 |
| 20 | `contract/tables.sql` + `assertions.py` | ✅ **applied** — column + `assert_no_fixtures` extension |

**All twenty applied or resolved.**

The 2026-08-13 sourcing pass closed 3, 4a, 5, 8 and 16 by reading provider
pages. **FR-2 went from 40/130 to 88/88 and `registry load-seed` now runs
with no flags at all.** The file got smaller: 48 fields were removed rather
than sourced, because a claim with no source is worse than an absence.

**The figure is 88, not 82, and it grew for a structural reason rather than a
sourcing one.** It is **82 `model_version` fields plus 6 `price_tier` fields**.
Item 18 moved Gemini 2.5 Pro's prices out of `model_version` and into tier
rows, and `check_source_coverage` now walks those rows: a sourced value the
provenance check cannot see would be rule 6 in a different costume. No new
sourcing was done to reach 88.

Items 17, 18, 19 and 20 were all raised *by* that pass. Reading the pages is
what revealed that Anthropic publishes two knowledge cutoffs, that Google's
prices are tiered, that Google publishes no token limits at all, and that
`reported_context` has no `provenance` column to stop a hand-seeded
threshold looking like harvested evidence.

### Items 5, 8 and 16 were one job, and were done as one

All three needed somebody with provider pages open and all three touched the
same file, so they were done in a single pass on 2026-08-13 rather than three.
That pass is also what raised 17, 18 and 19: reading the pages is what
revealed that Anthropic publishes two cutoffs, that Google's prices are
tiered, and that Google publishes no token limits at all.

Items 12 to 15 were raised after the first eleven, from the Phase 2 readiness
assessment in [`phase2-readiness.md`](phase2-readiness.md) and from building
the raw store. Items 13 and 14 block harvest, so they matter more than their
position suggests. Item 15 blocks nothing but is the one item where
`collect/` and `judge/` must actually agree rather than merely not conflict.

---

## Running the branch

```
python -m collect.cli registry load-seed
```

**No flags.** Both gates are clear. Measured on 2026-08-13:

| Command | Exit |
|---|---|
| `registry load-seed` | **0** |
| `registry load-seed --dry-run` | 0 |
| `registry check-sources` | **0** — 88/88 sourced (82 model fields + 6 tier fields) |
| `registry aliases` | 0 |
| `registry recompute-window` | 0 |

`--allow-unsourced` and `--allow-missing-spellings` still exist and now do
nothing to this file. They stay because the poller will reintroduce both
kinds of gap from week 5.

> ### Two corrections this document previously carried
>
> **First:** it said items 5, 6, 7 and 10 clear both seed-loader gates. That
> was wrong for the source gate, and verified wrong by running the check
> rather than reading the code. Item 5 replaced four URLs, item 6 added a
> boolean, item 7 edited comments; none added a source. Only item 16 cleared
> it, and item 16 did not exist until that correction.
>
> **Second:** it said `check-sources` exits 1 by design as a gap signal.
> That was true while gaps existed. It now exits **0**, so a CI step wired to
> it will pass and will start failing again the moment the poller introduces
> an unsourced field. That is the intended behaviour, but it is the opposite
> of what the earlier text described.

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

## Item 3 · `openai/gpt-4.1-mini` release date · **APPLIED**

The file carried `release_date: 2025-07-18`. A recollection of 14 April 2025
existed but was explicitly held back as recollection rather than a source.

[OpenAI's model page](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
states the default snapshot is **`2025-04-14`**, three months earlier than the
file and matching the recollection. The page settled it; the recollection was
never used as the basis.

| Source | Date |
|---|---|
| Recollection | 14 April 2025 |
| **OpenAI's page** | **2025-04-14** |
| Seed file, before | `2025-07-18` |

`release_date` drives `f_launch` and `in_window`, which is why an unsourced
correction would have been worse than a known-suspect value: it looks settled.

## Item 4 · `release_date` has no documented meaning

**This item is in two halves, and only the first has shipped.** Do not read
the comment landing as the whole item being done.

| | |
|---|---|
| **4a — the rule** | **APPLIED.** Naming what `release_date` means needs no source |
| **4b — the value** | **OPEN.** Choosing between `2025-05-19` and `2025-06-17` needs a provider page, and reconciling `BUILD-PLAN.md` is Engineer 2's file |


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

> ### Derived from the URLs, not transcribed from the hashes
>
> Transcribing the bare-hash markers would have preserved the bug this item
> exists to fix. `provider_page` is computed by comparing each URL's host
> against the model's own provider:
>
> | | count |
> |---|---|
> | `provider_page: true` | **9** |
> | `provider_page: false` | **31** |
>
> The hand convention marked **32**, so the two disagree on one entry.
> **`google/gemini-2.5-flash.release_date` cites `en.wikipedia.org` and
> carries no marker**, so a transcription would have recorded Wikipedia as a
> provider page. Recorded here rather than silently corrected.
>
> Third-party hosts currently cited: `openrouter.ai` ×7, `en.wikipedia.org`
> ×6, `opslyft.com` ×5, `finout.io` ×4, `chatlyai.app` ×3, plus six
> singletons.

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

> ### The placeholder ships, and a gate fires on it
>
> `tos_notes` is `NOT NULL`, and it cannot honestly be filled before someone
> reads each platform's current terms. Holding a schema fix hostage to a
> reading task with no owner and no date is worse, so
> `"REVIEW REQUIRED before first harvest …"` ships as the value. It states
> plainly that the review has not happened, and it unblocks FR-9's foreign
> key.
>
> **A placeholder a human has to notice is a lie you will forget.** So it is
> detectable by code: `assert_terms_reviewed()` in
> `collect/registry/assertions.py` refuses to harvest from any source whose
> `tos_notes` still carries the marker. Same shape as `assert_no_fixtures`
> and `assert_contract_backed`, and for the same reason — NFR-5's acceptance
> is that terms are *reviewed and recorded per source*, so a placeholder
> surviving to first harvest is a requirement failure and should stop the
> run rather than be noticed afterwards.
>
> **Blocking from week 2**, when the blog adapter lands. Recorded in the
> known-gaps table below.

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

## Item 16 · 90 populated fields carry no source · **CLEARS THE FR-2 SOURCE GATE**

FR-2: *record a source URL and retrieval timestamp for every registry field,
and it applies to seeded rows too.* Measured:

```
$ python -m collect.cli registry check-sources
FR-2      : 40/130 populated fields carry a source
```

**90 gaps, nine per model**, the same nine every time: `lifecycle`,
`max_output_tokens`, `knowledge_cutoff`, `price_cached_read` and the five
`supports_*` flags.

This was recorded in [the defect report](phase1-defect-report.md) as
deliberately deferred, but no item here closed it, so the package implied the
FR-2 gate would clear when items 5 to 7 landed. It will not. **This is the
only item that clears it.**

**Exact edit** — for each of the 90, open the provider's page, record what it
says, and add a `sources` entry with the URL and the date read:

```yaml
    sources:
      max_output_tokens:  { url: "…", retrieved_at: "YYYY-MM-DD", provider_page: true }
      knowledge_cutoff:   { url: "…", retrieved_at: "YYYY-MM-DD", provider_page: true }
      lifecycle:          { url: "…", retrieved_at: "YYYY-MM-DD", provider_page: true }
      price_cached_read:  { url: "…", retrieved_at: "YYYY-MM-DD", provider_page: true }
      supports_tools:     { url: "…", retrieved_at: "YYYY-MM-DD", provider_page: true }
      # … and the other four flags
```

**No URLs are supplied.** Generating them is the one failure this project
cannot absorb: a fabricated source passes the coverage check while asserting
nothing, which is strictly worse than a recorded gap.

Alternatively, drop the values you cannot source. An unsourced `supports_batch`
is not more useful than a null one, and a null is honest.

When this lands, `--allow-unsourced` stops being necessary and
`check-sources` exits 0.

---

## Item 17 · `knowledge_cutoff` means *reliable*, not *training*

Anthropic publishes **two** cutoffs and they are not the same date:

| Model | Reliable knowledge cutoff | Training data cutoff |
|---|---|---|
| Claude Haiku 4.5 | **Feb 2025** | Jul 2025 |
| Claude Opus 5 | May 2026 | May 2026 |

Five months apart for Haiku. `knowledge_cutoff` is one column, and the next
person will assume it means training data, because most providers publish
only that.

**It means the reliable cutoff.** The column exists so the answer path can
reason about what a model actually knows, and the reliable cutoff is the
honest answer to that question. The training cutoff overstates it, and
**overstating what a model knows is the error that costs somebody a wrong
recommendation.**

**Exact edit** — comment only, no DDL:

```sql
  -- The RELIABLE knowledge cutoff, not the training-data cutoff, where a
  -- provider publishes both. They differ: Claude Haiku 4.5 is Feb 2025
  -- reliable and Jul 2025 training. The answer path uses this to reason
  -- about what a model knows, and overstating that costs a wrong
  -- recommendation.
  knowledge_cutoff            date,
```

---

## Item 18 · The schema cannot express tiered pricing

Gemini 2.5 Pro is priced by input length:

| | ≤ 200k tokens | > 200k tokens |
|---|---|---|
| input | $1.25 | **$2.50** |
| output | $10.00 | **$15.00** |
| cached read | $0.125 | $0.25 |

`price_in` is a single `numeric(12,6)`. **All three of Gemini 2.5 Pro's
prices have been removed rather than picking a tier**, and that is the whole
of the model's pricing gone.

Taking the cheap tier would understate cost by 2x on exactly the
long-context tasks the board exists to get right — FR-31 already exists
because advertised context overstates usable context, and a cost model that
silently halves the price above 200k is a **false qualification**, which §9
names as the worst possible output.

Tiered pricing is not exotic. Any provider may add it, and the poller will
meet it from week 5.

**Proposed shape, not built** — this is DDL on a shared table and Engineer
2's cost logic reads it:

```sql
CREATE TABLE price_tier (
  model_version_id  text NOT NULL REFERENCES model_version(id),
  dimension         text NOT NULL,   -- input_tokens | output_tokens
  min_tokens        int NOT NULL DEFAULT 0,
  max_tokens        int,             -- NULL = no upper bound
  price             numeric(12,6) NOT NULL,
  price_cached_read numeric(12,6),
  sources           jsonb NOT NULL,
  PRIMARY KEY (model_version_id, dimension, min_tokens),
  CONSTRAINT price_tier_dimension_ck CHECK (dimension IN ('input_tokens','output_tokens'))
);
```

`model_version.price_in` then means *the rate at the lowest tier*, or stays
NULL when tiers exist, and Q6 reads `price_tier` when a row is present. Which
of those two it is needs deciding with the cost logic, not against it.

---

## Item 20 · `reported_context` has no `provenance` column · **PROPOSED, NOT APPLIED**

`cell` carries `provenance text NOT NULL CHECK (provenance IN ('harvested',
'hand_curated'))` so that hand-written fixtures cannot render identically to
harvested evidence, and so week 8 can delete them by that column.
`reported_context` carries no such column, and it should.

**Why it is worse here than the case it mirrors.** `reported_context` feeds
**FR-31, a hard filter**: the answer path matches against `reported_low`,
never the advertised window. A fabricated `reported_low` silently excludes
qualified models from every long-context recommendation, and nothing ever
surfaces why.

> A wrong `cell` shows up as a phrase somebody can read and disagree with.
> **A wrong `reported_low` shows up as an absence**, and nobody audits a
> model that was never in the list.

This is not hypothetical. Item 19 tempts exactly this: the advertised figure
is sourced, no source gives a threshold, and the shortest path to a working
context-gap fixture is to hand-seed a `reported_low`. With no `provenance`
column that hand-seeded integer is permanent and undetectable.

**Exact edit** — in `contract/tables.sql`:

```sql
CREATE TABLE reported_context (
  model_version_id text PRIMARY KEY REFERENCES model_version(id),
  advertised       int,
  reported_low     int,
  reported_high    int,
  quote_ids        text[],

  -- FR-31 reads reported_low as a HARD FILTER, so a hand-seeded value
  -- silently excludes models from every long-context recommendation and
  -- shows up as an absence rather than as a claim anyone can read.
  -- Same guard as cell.provenance, for a stronger reason.
  provenance       text NOT NULL DEFAULT 'harvested',

  computed_at      timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT reported_context_provenance_ck
    CHECK (provenance IN ('harvested', 'hand_seeded'))
);
```

**And the startup assertion has to check it.** `assert_no_fixtures()`
currently counts seeded `model_version` rows and hand-curated `cell` rows.
Adding the column without extending the assertion leaves the guard the
column exists to provide:

```python
seeded    = "SELECT count(*) FROM model_version WHERE provenance = 'seed'"
handmade  = "SELECT count(*) FROM cell WHERE provenance = 'hand_curated'"
reported  = "SELECT count(*) FROM reported_context WHERE provenance = 'hand_seeded'"
```

Engineer 1 will make that change in `collect/registry/assertions.py` in the
same commit as the DDL, since the two are only useful together.

---

## Item 19 · The context-gap fixture · **ADVERTISED HALF DONE, CONTRADICTING HALF IS WEEK 5**

**Do not read this as unfinished work.** The half that belongs in the seed
file is done. The other half is evidence, and evidence arrives in week 5.

BUILD-PLAN §3.6 asks for *"at least one with a known advertised-vs-real
context gap, otherwise the inflation logic sits untested until week 7."*
That is **two claims with different sourcing requirements**, and the word
"known" was doing work nobody costed:

| Claim | Where it comes from | State |
|---|---|---|
| the advertised figure | a provider page | ✅ **sourced** |
| the contradiction | harvested practitioner evidence | ⏳ **week 5** |

**`openai/gpt-4.1-mini` satisfies the heuristic.** It carries
`advertised_context: 1047576`, sourced to OpenAI's own model page. And
OpenAI acknowledges the gap in its own words:

> "long context performance can degrade as more items are required to be
> retrieved, or perform complex reasoning that requires knowledge of the
> state of the entire context"
>
> — [OpenAI, GPT-4.1 prompting guide](https://developers.openai.com/cookbook/examples/gpt4-1_prompting_guide)

**A provider stating that long-context performance degrades while naming no
number is this product's thesis in one sentence.** The number only exists
where people hit it.

Three independent parties report the same thing without producing a
threshold: [Zep](https://blog.getzep.com/gpt-4-1-and-o4-mini-is-openai-overselling-long-context/)
measured 56.72% on LongMemEval_S at ~115k-token conversations, *below*
GPT-4o-mini; ChromaDB's *Context Rot* report covers 18 models including
GPT-4.1; and the RULER / NIAH-2 / MRCR families agree effective context is
far shorter than advertised. None gives a figure to seed.

**Why nothing is being seeded.** `reported_context.reported_low` is an
`int`. Nothing above yields one, so seeding it would mean inventing an
integer from qualitative reports, which is the same act as inventing a
source URL — the thing this file just spent a whole pass undoing.

**And the contradiction was never seed data.** The schema already routes it:

```sql
CREATE TABLE reported_context (
  advertised int, reported_low int, reported_high int,
  quote_ids  text[],   -- it comes from CLAIMS
  ...);
```

It arrives through `document` → `claim` → `reported_context.quote_ids` like
every other piece of evidence, at blogs' `base_trust` of 0.90. A blog
claiming degradation is **not** a registry fact and does not belong in
`sources`, which is FR-2 provenance.

**Still open, and only this:** `gemini-2.5-flash` lost its
`advertised_context` because Google publishes no token-limit table on
`ai.google.dev/gemini-api/docs/models`, its per-model pages, its pricing
page, or `docs.cloud.google.com`'s Vertex model pages. Restoring it needs a
Google page that states the figure. That is a documentation problem, not a
fixture problem, and the fixture no longer depends on it.

> **Read item 20 before acting on this one.** The shortest path to a
> "working" context-gap fixture is to hand-seed a `reported_low`, and
> `reported_context` has no `provenance` column to mark it as fabricated.

---

## Known gaps, recorded but not proposed

Not everything found needs a decision now. These are written down so they are
not rediscovered.

| Gap | Blocking from | Note |
|---|---|---|
| **`tos_notes` placeholders unreviewed** | **Week 2**, the blog adapter | Item 13 ships `REVIEW REQUIRED` as the value so the schema fix is not held hostage to a reading task. `assert_terms_reviewed()` refuses to harvest while the marker survives, so this fails closed rather than quietly. Clearing it means reading GitHub's, Reddit's and each blog host's terms and recording what they say — NFR-5's acceptance |
| **Reddit access deferred** | **Week 3** | The company holds the account; access requested later. Adapter not being built. Week 3 because FR-6's acceptance is all three adapters returning content, and FR-17's cross-platform identity clustering cannot be tested with one social platform. Blogs, not Reddit, carry the structurally-positive channel FR-6 depends on. Detail in [`phase2-readiness.md`](phase2-readiness.md) §6 |
| **No jobs table** | **Week 7**, the nightly job chain | `CLAUDE.md` and `pyproject.toml` both record *cron plus a jobs table, no workflow engine*. `contract/tables.sql` defines 24 tables and none is that. Nothing needs it until the nightly chain, but it overlaps with `harvest_run` (item 14) and the two should be designed together rather than separately |
| **Blog feed list has no home** | Week 2, the blog adapter | Initial list is config, discovered feeds are data. Settle alongside item 13 |
| **No robots.txt handling** | Week 2, the blog adapter | NFR-5 requires it. `urllib.robotparser` is stdlib, so no dependency. Collection lane's own work, not a contract item |
| **Raw store does not exist** | **Immediately**, before any adapter | `document.text_ref` is `NOT NULL` and points into it. Collection lane's own work, top of Phase 2 |
