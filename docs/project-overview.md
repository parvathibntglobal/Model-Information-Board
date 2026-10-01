# Model Information Board — What We've Built So Far

*As of 2026-09-29. A plain-language overview of the whole system: what it is, how
it's built, what runs today, and what's still pending. No credentials, keys, hosts,
or other confidential details are included.*

---

## 1 · What it is

**You describe the work; the board names the models engineers have actually made
that work with — cheapest first — and shows you their exact words.**

Coding agents pick their own model for every sub-agent they spawn, and they reach
for the strongest one almost everywhere. Most sub-agents don't need it; something
10–40× cheaper usually does the job. But "use something cheaper" is a hope, not a
decision — and benchmarks can't tell you *which* sub-agents are safe to downgrade.

Engineers who already shipped can, and they publish constantly — in GitHub issues,
on Reddit, on engineering blogs, on Hacker News, dev.to, arXiv and Hugging Face.
That evidence is buried in marketing and decays as providers silently update models
behind the same names. This system collects it, strips paid and fake content, and
states what people actually found — **in their words, with a link to the source**.

The output is a board of models organised three ways — **Jobs**, **Capabilities**,
**Metrics** — where every claim carries a verbatim quote and no number is invented.

---

## 2 · The rules that shape everything

Five non-negotiable rules govern the entire codebase (full text in `CLAUDE.md`):

1. **No claim without a verbatim quote**, verified in code by exact substring match
   against the text the extractor was shown. No quote, no claim. The check is plain
   Python — never a model checking a model.
2. **Exactly two stages may call a language model:** `judge/extract/` and
   `judge/ask/` (task understanding only). Nothing else counts, weights, gates,
   ranks, filters or assembles phrases with a model. **An LLM may propose; it may
   never decide.**
3. **No synthesised number reaches a page.** Every figure is *counted* (people,
   quotes, days) or *measured* (price, tokens). Consensus is a phrase assembled
   from counts, never a 0–100 score.
4. **Silence is not criticism.** "Nobody has discussed this" must render distinctly
   from "engineers report problems." Absence of evidence must never read as evidence
   of capability.
5. **Config in versioned YAML, not code.** Thresholds, weights, half-lives, the
   capability list, aliases and filter rules all live in `contract/`.

Several more rules extend these (missing values stay missing; every figure travels
with its denominator; an unmeasured check ships as a weight, not a gate; every
produced value has a named consumer). They exist because each was violated at least
once and cost real work.

---

## 3 · Architecture

Two lanes, one contract, and data crosses the boundary exactly once:

```
contract/     the shared interface (config + schema); changes go via PR, two eyes
collect/      registry, harvest, assemble, triage, ops   (Engineer 1's lane)
judge/        extract, vet, curate, publish, answer path  (Engineer 2's lane)

collect/  ---->  document + thread_context (offset map)  ---->  judge/
```

`collect/` fills the tables; `judge/` reads them; nothing flows back. (The formal
lane *ownership* was dropped 2026-08-28 — anyone may touch anything and tell the
others after — but the `collect → judge` data-flow architecture stays, and
`contract/` still requires two reviewers.)

**Stack (decided, not to be relitigated):**
- Python 3.11+, PostgreSQL + an object store, `httpx` for fetching.
- Cron + a jobs table. **No workflow engine, no Kafka, no time-series DB.**
- One adapter class per platform. **Official APIs and public feeds only** — no
  scraping, `robots.txt` respected, identifying User-Agent with a contact URL.
- The evidence pipeline is a **nightly batch**; the answer path reads a
  materialised view and never touches the pipeline.
- Backend: a **FastAPI** app (`judge/app.py`, served by uvicorn) exposing the board,
  models, compare, FAQ and admin endpoints under `/api`.
- Frontend: a **React 19 + Vite** single-page app (`web/`).
- Published content is always *quote + attribution + link*, never full text.

---

## 4 · The evidence pipeline (nightly batch)

A fetch runs a sequence of stages (ids as they appear in the fetch log; prose in
`contract/pipeline_stages.yaml`). In order:

| Stage | What it does |
|---|---|
| **E1** | Resolves the chosen model into the search surfaces its evidence is found under (`model_alias`). No alias → zero terms → the run says so and stops. |
| **E2** | Searches **GitHub** issues/PRs for each name variant across capability queries (bounded per-run cap). |
| **E2R** | Searches **Reddit** and fetches comment trees (metered/paid; quota recorded per call). |
| **E2A** | Searches **arXiv** (papers carry measured numbers; free). |
| **E2X** | One clubbed query on **X** (via a reseller scrape, stated plainly). |
| **E2B** | Reads engineering **blogs** — the one positive-evidence channel; feeds read whole, skipped on a per-model fetch. |
| **E2D** | Searches **dev.to** articles. |
| **E2H** | Searches **Hacker News** via Algolia's index. |
| **E2F** | Searches **Hugging Face** discussion. |
| **E3** | Flattens documents into threads (root + replies) and stores an **offset map** so a quote can be resolved back to an exact span. |
| **E3d** | Groups near-duplicate documents so a syndicated copy counts as reach, not a second voice. Nothing deleted. |
| **E3b** | Fills **signal columns** (numbers, code, error strings, stated conditions, version-named) — counted, not judged. |
| **E4** | Hard gates over each document: bots, bare links, too-short, names no resolvable model. Every drop records which gate fired. |
| **E4b** | The same vetting at thread level — the last check that costs no tokens. |
| **E5** | **The one paid, model-using stage.** Reads each selected thread and files claims, each with a verbatim quote and character offsets. Every quote is substring-checked against the text shown. |
| **E5c** | Records the board sections the model **discovered** (jobs, behaviours, metrics it *named*), not chosen from a fixed list. |
| **E5d** | Measures whether each metric figure can quote its benchmark and its model (measure-only; nothing stored or refused). |
| **E5b** | Maps claims onto the ratified capability list (a legacy scoring path; kept separate because that list is *closed* and the board's sections are *open*). |
| **E6** | Drops claims that are promotional, affiliate, sarcastic, or about a model before release — after the model, because judging sarcasm needs the quote. |
| **E7** | Recomputes the cells the board renders from surviving claims. **The board is derived, never hand-written** — a run that dies before E7 stored claims but changed nothing on the page. |

Supporting facts: raw payloads are immutable and content-hash addressed (reprocess,
don't re-fetch); every derived row carries a `pipeline_version` so scoring changes
are re-runnable and diffable; seeded/hand-curated rows carry `provenance` and every
write path refuses them outside development.

---

## 5 · The data model

The schema (`contract/tables.sql`) has ~40 tables. The load-bearing ones:

- **Registry:** `model_version` (every model the poll carries, with prices,
  context, flags), `model_alias` (the surfaces people write — "opus 5", "gpt 5.5"),
  `model_event`, `price_tier`, `pricing_history`.
- **Evidence in:** `document` (harvested posts/comments/articles, immutable),
  `dedup_cluster`, `thread_context` (flattened threads + offset maps), `author` /
  `author_identity_cluster` (counting people, not posts).
- **Extraction:** `claim` (one filed claim + verbatim quote + offsets),
  `claim_weight`, `thread_extraction`, `capability` / `capability_candidate`.
- **The board:** `board_entry` (the discovered-section rows the board renders),
  `cell` (legacy capability-keyed scores), `reported_context`.
- **Answer path (built, parked):** `task_profile`, `role`, `answer`, `outcome`.
- **Labelling / QA:** `label`, `label_change`, `golden_label`, `audit`.
- **Ops:** `source`, `watermark`, `harvest_run`, `coverage_gap`, `job_run`,
  `spend_ledger`, `fetch_log`, `rapidapi_quota` (+ readings), `schema_migration`.

Migrations apply once, in order, recorded in `schema_migration` — coordinated among
engineers because the shared staging DB is written by more than one machine.

---

## 6 · The contract (shared config)

Everything reviewable-in-a-diff lives in `contract/`:

- `tracked_models.yaml` — which models the registry page lists (editorial).
- `seed_models.yaml`, `unpolled_models.yaml`, `awaiting_poll_models.yaml` — model
  seeds and the three provenance states (`polled`, `unpolled`, build `seed`).
- `capabilities.yaml`, `board_surfaces.yaml`, `board_ordering.yaml`,
  `slug_parents.yaml`, `conditions.yaml` — the board's vocabulary and ordering.
- `sources.yaml` — every source, its terms ruling, and the **use-basis
  undertaking** (see §8).
- `queries.yaml`, `harvest.yaml`, `bots.yaml` — how harvest searches and filters.
- `faq.yaml`, `api_fields.yaml`, `column_states.yaml`, `pipeline_stages.yaml`,
  `tombstoned_models.yaml`, `tables.sql`, `migrations/`.

The proposed alias surfaces the seating path reads live in
`docs/proposals/alias-surfaces-tracked-set.yaml` (reviewed per model).

---

## 7 · The frontend

A React 19 + Vite SPA (`web/`) behind a demo auth gate. The surface:

- **Landing** (`/`) with an evidence-first pitch and an 11-question FAQ.
- **The board** (`/board`) — three tabs: **Jobs**, **Capabilities**, **Metrics** —
  each a grid of discovered sections; drill into a section, then into one model's
  reports on it.
- **The registry** (`/models`) — the tracked set, searchable, with a 2–3 model
  **compare** flow (`/compare?ids=…`).
- **Model pages** (`/models/{id}`) — what engineers said, grouped by discovered
  section, plus a fetch panel.
- **Blogs** (`/blogs`) — working notes (demo path today).
- **Admin** (`/admin`) — an internal ops console (fetch, runs, sources, prompts,
  stages, usage, board review, model proposals).

A full page-by-page SEO/structure map is in
[docs/ui-page-inventory-seo.md](ui-page-inventory-seo.md). The short version: it is
**client-rendered with no SSR**, all routes sit behind the auth gate, and there is
currently no `robots.txt` or `sitemap.xml` — consistent with its
internal-development-only status.

---

## 8 · Access & safety posture

The board is **internal-development-only** today, enforced through a versioned
"use-basis undertaking" in `contract/sources.yaml`, checked at run time by
`collect/adapters/basis.py` (`_undertaking_basis()`):

- Asserted conditions: authenticated behind a wall, no external users, not publicly
  linked, not monetized, nothing derived-from-corpus published outside the team.
- Any one of those changing **voids** the basis and refuses harvest — the guard is
  fail-closed. The undertaking carries an expiry that forces periodic re-review.

Harvest is polite by construction: official APIs and public feeds only,
`robots.txt` respected, per-source terms rulings, identifying User-Agent, and paid
arms (Reddit, X) meter and record their quota.

---

## 9 · Current state (real numbers)

Read from staging on 2026-09-29:

- **244** models in the registry (all in-window); **17** on the tracked list;
  **78** models have at least one board entry.
- **1,873** non-declined board entries behind the board.
- Discovered section pages: **98** jobs, **298** capabilities, **144** metrics,
  plus ~**1,030** model drill-down pages — roughly **1,820** distinct board URLs.
- The whole corpus extracts for about **$1.84** at the measured per-thread cost —
  the model call is a small, bounded expense by design.

---

## 10 · Built vs. pending

**Working today:**
- The full harvest → extract → publish pipeline (E1–E7) across eight sources.
- The registry poll, alias resolution, dedup, signal columns, hard gates.
- LLM extraction with in-code verbatim-quote verification and offset mapping.
- The derived board (Jobs / Capabilities / Metrics), model pages, compare, FAQ
  (with client-side FAQ structured data), and the admin ops console.
- The FastAPI backend and the React frontend, with the internal-only undertaking
  enforced at run time.
- Coordinated shared-staging writes, migrations ledger, spend and quota tracking.

**Built but parked / partial:**
- **The Ask box / answer path** (`judge/ask/`, `task_profile` / `role` / `answer` /
  `outcome`) exists in code but is parked — not wired into the current UI.
- **Legacy capability cells** (`cell`, the closed 12-key vocabulary) are written but
  effectively unused for display: the current extractor writes `capability_key`
  NULL and no cell clears the publication bar, so the board relies on the open
  discovered sections instead.
- Per-model alias **seating** into the database (`seat()` / the reviewed-surfaces
  path) and the search **over-match fix** are in progress — needed before newly
  added models (e.g. DeepSeek V4 Flash) are harvested cleanly.
- Blogs are a demo path (no posts table populated in staging).

**Deployment:** a `Dockerfile`, `run-backend.py` / `serve.py`, and deployment notes
(`docs/railway-deployment-plan-*.md`, `docs/ops-*.md`) exist; the nightly chain and
scheduled fetches are documented in `docs/ops-nightly-chain.md` and
`docs/ops-scheduled-fetches.md`.

---

## 11 · Where to read more

| Topic | Document |
|---|---|
| Requirements (36 FR, 10 NFR), plan | `BUILD-PLAN.md` |
| How the machinery works, stage by stage | `docs/logic-and-workflow.md` |
| Conventions and the non-negotiable rules | `CLAUDE.md` |
| Frontend page-by-page (SEO) | `docs/ui-page-inventory-seo.md` |
| Measurements and evidence for decisions | `docs/measurements/` |
| Ops / nightly chain / deployment | `docs/ops-*.md`, `docs/railway-deployment-plan-*.md` |

*This overview omits all credentials, connection strings, hosts/IPs, API keys and
personal contact details by design. Where a real value would be needed, see the
`.env.example` template and the setup notes in `README.md`.*
