# Content workspace: how it is built, and what to review

*Written 2026-11-19 for the review of the content-workspace PR. It describes the
code on this branch; anything not built is under "Not in this PR".*

## What it is, and what it is not

A signed-in space, at Admin → Content workspace (`/admin/content`), that keeps:

- the rules for posting on each platform;
- topic suggestions drawn from the board's own data;
- drafts checked against those rules.

**It posts nowhere.** It is there so that the rules, formats and checks exist
before anyone makes content (anooj, 2026-11-19).

**It is always behind the login.**
- Every route sits under `/admin/content` and is wrapped in `Require`.
- No path is added to `judge/gate.py`'s public lists, the sitemap or indexing.

**Its rows are not evidence.** The board never reads them. The workspace reads
the board, and writes only its own `cw_*` tables.

## Where things are

**Code, in `judge/content_workspace/`:**

| Module | What it does |
|---|---|
| `store.py` | Platforms, notes (with edit history in `cw_note_edit`), drafts, check runs |
| `checks.py` | The coded fit checks: length, title, hashtags, denominator, links, quotes, handles, disclosure… |
| `recommend.py` | Topic suggestions from board data (details below) |
| `recipes.py` | Checks the topic recipes and pain angles in the config |
| `writer.py` | The AI writer. **Off**; recorded under rule 2 as proposed |
| `media.py` | Files attached to drafts: carousel PDF and card, chart or cover PNG, each checked to be a real PNG or PDF and under a size limit |
| `results.py` | Results a person records after posting |
| `templates.py` | Starting templates that fill placeholders only |
| `__main__.py` | The command line: `seed`, `status`, `material`, `ingest`, `draft-json`, `media-add` |

**Elsewhere:**
- **Config:** `judge/content_workspace/config/`:
  - `workspace.yaml`: settings, topic kinds, looks, recipes, pain angles, writer;
  - `seed_platforms.yaml`: 11 platforms with their philosophy, research, rules and recommendations;
  - `templates.yaml`;
  - the writer's prompt and playbooks.
- **Endpoints:** 23 under `/admin/content` in `judge/app.py`, all signed-in.
- **Page:** `web/src/routes/ContentWorkspace.jsx`.
- **Tables:** nine, in the board's database (anooj decided on 2026-11-19 to share it): `cw_platform`, `cw_note`, `cw_note_edit`, `cw_draft`, `cw_check_run`, `cw_writer_run`, `cw_result`, `cw_tick`, `cw_media`. They are created by `contract/migrations/20261119T1200_content_workspace.sql`, mirrored in `contract/tables.sql`, and their 108 columns are declared in `contract/column_states.yaml`. No workspace table references a board table.

## How the board's rules are kept

| Rule | How |
|---|---|
| 1. Quote verified | The workspace stores no claims. Suggestions use the board's verified counts and the evidence feed's paraphrases, never a user's words |
| 2. LLM callers | The AI writer proposes and code checks every number and link. A person decides, and posting is by hand. It is **off**, and recorded in CLAUDE.md as *proposed* |
| 3. No synthesised number | Every figure shown is a count. Capability and pain labels are words ("mostly for", "mixed reports", "too few to say"), assembled from counts with the board's own E7 thresholds (`judge/curate/gate.py`). The page says they are not the board's published consensus |
| 4. Silence | "Nobody reported on it" is said in words. A calendar event with no reports is **labelled**, not hidden. The pains the board cannot count are listed by name |
| 5. Config | In `judge/content_workspace/config/`, not `contract/` (see review point 3) |
| 6. Missing data | A failed board read says so, never "nobody". A model missing from the registry is named as such. A price that isn't listed stays not listed |
| 7. Denominators | Every count line states its span and population: "N people in the 30 days to DATE", "of M posts" |
| 8. Weight before gate | No filter drops a suggestion. Small samples, no-report events and thin angles are labelled |
| 9. Consumers | Every new payload field has a reader in `ContentWorkspace.jsx`. The new columns are declared in `column_states.yaml` |
| 10. Identifiers | The capability split and pain angles group by `section:slug`, never by display name |
| 12. Fallbacks | A config key with no value refuses to run. The recipe table is checked against the seed by `recipes.problems()`, which the tests run |

## How suggestions are chosen (topic selection, decided 2026-11-19)

**A, evidence-led: `capability_split`.**
- What it gives: one model's reports over a span, by capability and job, with people for, against and neutral on each.
- Counted exactly as public counts: `judge/verdict.py` `COUNTED` and `POST_DAY`, plus `publication.sql_counted_document`.
- Check: on the shared database it reproduces Claude Fable 5.2 from 5–19 Nov. Code generation has 28 people, 25 for and 3 against.

**B, calendar-led: launches, price moves, retirements.**
- The events come from `judge.updates.build`.
- Each one shown carries, per model: the people who reported in the last 30 days, and how many of them posted since the event.
- An event nobody reported on stays listed, tagged as a calendar item only.
- `retirement` is a new topic kind, on X and LinkedIn.

**C, the angle: `pain_angles`.**
- 15 themes from the team's private pain research, each mapped to `section:slug` keys.
- Counts are read live, each person once per theme. Only paraphrases are stored.
- 10 pains with no board capability are listed in `pain_not_counted`.

**The order of suggestions** is newest first within each kind, and the capability split orders by people. The page says so in words. There is no score.

## Topic recipes and looks

- **Recipes:** each topic kind gets a look (field report, data card, evidence board, or text only with a reason). Each platform that uses it gets a format and media kinds.
- **The check:** `recipes.problems()` confirms every (platform, topic) pair in the seed has a recipe, every format exists on its platform, and every media kind is one `media.py` stores.
- **The generators** (added in the PR stacked on this one) are in `tools/media/`, one per look, named by each look's `generator` in `workspace.yaml` and checked to exist by `recipes.problems()`. `python -m judge.content_workspace media-spec <look>` (`media_specs.py`) writes a generator's spec from the board, read-only and counted as public pages count. They render on a person's machine (Node and Chromium), never on Railway or in CI, and their files reach a draft through `media-add`. How-to: `tools/media/README.md`.

## The AI writer

**Inputs.** It sees:
- the draft's material, meaning its suggestion and evidence;
- the platform's notes as they stand now;
- its links.

**Code refuses a proposal that has:**
- a number in digits that isn't in the material;
- a URL or domain that isn't one of its links;
- any handle.

A refused proposal is stored with its reasons, never corrected.

**A passing proposal** goes through the same fit check as any draft. It reaches the draft only when a person uses it, and the draft is then marked AI-assisted.

**Spend** is recorded in `cw_writer_run`, under `writer.daily_budget_usd`. It is not in `spend_ledger`.

**Off** (`api_enabled: false`): Claude Code writes from `material` exports, and the result comes back through `ingest` under the same checks.

## What to review

1. **The contract changes:** the new tables in `contract/tables.sql`, the migration, and the `column_states.yaml` entries.
2. **The rule-2 entry for the writer** in CLAUDE.md, which is marked proposed.
3. **Config outside `contract/`.** The workspace's thresholds, for example `evidence_days: 30`, sit in `judge/content_workspace/config/`, a choice phase 1 made because nothing on the board reads them. Rule 5 says config lives in `contract/`. Should they move there?
4. **Platform names on paraphrases.**
   - Suggestions show the evidence feed's paraphrases cited by platform, including Reddit and X. This follows `contract/publication.yaml` `evidence_feed` terms, which are still a proposal (#558).
   - Nothing in the workspace shows a per-platform count for a withheld source.
   - Media made from these needs the #558 decision before any public use.
5. **The write guard** on the workspace's write commands, now that they write to the shared database.

## Not in this PR

- The media generators: they are in the PR stacked on this one (`tools/media/`).
- The writer's API model.
- `SITE_URL` and analytics (to be decided by the team).
- Measuring our own posts.
- Research on platforms we haven't fetched (LinkedIn, Substack, Medium, YouTube, Instagram, Facebook).
