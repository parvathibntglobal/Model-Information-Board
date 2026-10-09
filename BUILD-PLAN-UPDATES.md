# Build plan updates: what changed since the original plan

**Companion to:** `BUILD-PLAN.md`, the foundation plan, last changed 2026-08-18 (`88d3b5d`). That file is **left as written**. This one records how each requirement stands today.
**State as of:** 2026-10-08, `main` at `e73a4da`.
**Cleanup merged:** #515 (harvested platform data removed from the tree) and #516 (unwired routes, modules and scripts removed), both 2026-10-08.
**Sources checked:** the code on `main`, `contract/`, `.github/workflows/`, `CLAUDE.md`, and the local restore of the shared-database backup (2026-10-07). The cleanup review's figures and Anooj's corrections of 2026-10-08 are included.

---

## 1. Why the plan moved

The original plan was a registry, a harvest, and an evidence pipeline that turned verified claims into weighted, gated **labels and cells**, plus an **Ask box** that answered "which model for my task?". The project changed direction along the way:

| Change | When | What it means for the plan |
|---|---|---|
| **The board is built by a classifier** | 2026-09-08 | Evidence is filed into three sections, Best for (jobs), Capabilities and Metrics, as `board_entry` rows. Entries are **ungated observations**, counted by distinct voices. |
| **The legacy claims and cells path is off by default** | 2026-09-24 | With `LEGACY_CELLS` off, no claim, weight or cell is written (`judge/legacy.py`, `judge/pipeline.py`). Existing cells are frozen at that date. |
| **The Ask box is on hold** | — | The UI was removed in `4248bb7`. The backend is kept as future scope. |
| **More sources** | Sept 2026 | Eight sources instead of three: Reddit, Hacker News, GitHub, dev.to, Hugging Face, X, arXiv and blogs. |
| **Publication policy** | 2026-10-05 | `contract/publication.yaml`: Reddit, arXiv and X are collected but **never shown on public pages**. |
| **The extractor changed model** | 2026-09-01 | `google/gemini-2.5-flash` was replaced by `deepseek/deepseek-v4-flash` after an A/B test. |
| **New surfaces** | Sept–Oct 2026 | Blogs (generated drafts with review), Compare, Admin, the daily scheduler, and the spend ledger. |

**Key used below:**

| Mark | Meaning |
|---|---|
| ✅ **Still holds** | As written in `BUILD-PLAN.md`. |
| ✏️ **Updated** | Still wanted. The text below replaces the plan's wording. |
| ❓ **Open** | Needs a lead decision: keep, rebuild or retire. |
| ⏸ **On hold** | Belongs to the Ask box, which is future scope. |

---

## 2. Registry and harvest (E1)

| ID | Original requirement | Status | How it stands now |
|---|---|---|---|
| FR-1 | List 100% of models released in the trailing 18 months, within 24 hours of release | ✏️ Updated | **The registry is polled every 3 days** (`registry-poll.yml`, cron `23 5 */3 * *`). New models from tracked providers are admitted by rule (`auto_track`, `contract/tracked_models.yaml`, since #504). **The 24-hour target is not met by design.** Either move the poll to daily, or drop the 24 h from the target. |
| FR-2 | Record a source URL and retrieval timestamp for every registry field | ✅ Still holds | Registry rows carry their provenance (`model_version.provenance`, including `polled`). |
| FR-3 | Detect model changes by diffing raw provider API responses daily | ✏️ Updated | **Diffed every 3 days**, as a step of `registry-poll.yml` (`scripts/registry_diff.py`). The diff is posted to issue #450. It is daily only if the poll becomes daily. |
| FR-4 | Append-only, time-aware alias table; resolution uses the post's timestamp | ✅ Still holds | The alias table carries `valid_from`. Aliases are seated only in versioned forms, and collisions are refused. |
| FR-5 | Community content may trigger a registry re-check, never write to it | ✅ Still holds | — |
| FR-6 | Harvest from three platforms, one of them structurally positive | ✏️ Updated | **Harvest from eight sources**: Reddit, Hacker News, GitHub, dev.to, Hugging Face, X, arXiv and blogs. **What may be shown publicly follows `contract/publication.yaml`.** Reddit, arXiv and X are withheld from public views (no quote, link, handle or count), and a public page says that sources are withheld. |
| FR-7 | Every tracked capability has at least one harvest query | ✅ Still holds | `contract/queries.yaml`. |
| FR-8 | Negative-stance queries for every capability | ✅ Still holds | `contract/queries.yaml`. |
| FR-9 | Persist pagination cursors durably; resume exactly where consumption paused | ✅ Still holds | — |
| FR-10 | Every adapter reports its own yield per run | ✅ Still holds | The per-adapter counts are in each fetch's run log. |
| FR-11 | Log and display any harvest truncated by a budget cap | ✏️ Updated | Truncation is logged per fetch, and **shown in Admin → Runs and Scheduler**. The caps are `FETCH_MAX_THREADS` and `EXTRACTION_DAILY_BUDGET_USD`, shown in Admin → Settings with "default or override". On branch `parvathi_01`, `run-backend.py` sets 500 threads and $3. **The GitHub Actions variable reads 2.00** and Railway's value is unconfirmed, so the team should agree one figure and say where it is set. |
| FR-14 | Flatten each thread: root plus 3–5 specificity-ranked children | ✏️ Updated | **Root plus up to `max_children` ranked children: 40** (`contract/harvest.yaml`, since 2026-10-05; 25 from 09-24, 5 before). The ranking is an additive specificity score. A Reddit audit found 52 of 444 dropped comments carrying evidence, so the ranking rule is open work. |
| FR-15 | Emit an offset map linking every flattened span to its source document and raw span | ✅ Still holds | — |
| FR-16 | Deduplicate before anything is counted; syndicated copies count toward reach, never weight | ✅ Still holds | Dedupe runs per source, by platform declaration, exact text and MinHash (`collect/assemble/dedupe.py`, `dedupe_write.py`). **Canonical-URL matching (`collect/assemble/urls.py`) is not used, and should not be used for merging.** Measured 2026-10-08: it would merge 15,724 documents (every GitHub comment into its issue) and catch no real duplicates. The decision on that file is with the team. |
| FR-17 | Cluster author identities across platforms before counting voices | ❓ Open | **Not implemented, on evidence.** `collect/assemble/authors.py` counts distinct authors per platform and records that there was *"not one observed instance"* of a cross-platform author: zero cross-kind clusters over 4,153 documents. **Lead:** retire it, or keep it as a known gap with that measurement as the reason. |

## 3. Evidence and vetting (E2)

| ID | Original requirement | Status | How it stands now |
|---|---|---|---|
| FR-12 | Every claim carries a verbatim quote, verified in code by exact substring match | ✅ Still holds | `CLAUDE.md` rule 1. `board_entry.quote_verified` is required. |
| FR-13 | Discard any claim whose quote fails verification; flag its document | ✅ Still holds | — |
| FR-18 | Hard-reject promotional documents; retain and display them with the trigger named | ✏️ Updated | **Moved to E4b/E6. Rejections are counted per fetch, not yet shown per document.** The pre-LLM screen (`judge/screen.py`) drops discount codes, bot self-identification and non-English text. The E6 check (`judge/vet/reject.py`) rejects affiliate links and claims dated before the model existed. Both are counted per trigger in the fetch's run log and Admin → Evidence stages. **`/filtered` was removed in #516**, because it listed `document.status`, which is not where these rejections happen. Showing each rejected document with its trigger remains open work. |
| FR-19 | Weight every surviving claim by seven documented factors, itemised per claim | ❓ Open | **Not applied since 2026-09-24.** The factors run only on the legacy claims path, which is off (`LEGACY_CELLS`). `board_entry` has no weight columns; the board shows counts of voices and reports. **Lead:** retire the weighting, or turn the legacy path back on. |
| FR-20 | Compute the launch-window factor at extraction and freeze it | ❓ Open | Part of the seven factors, so it is decided together with FR-19. |

## 4. Curation and the board (E2)

| ID | Original requirement | Status | How it stands now |
|---|---|---|---|
| FR-21 | Publish a consensus phrase only when the publication gate passes | ✏️ Updated | **The board is deliberately ungated.** Board entries are observations, shown as counts and how they were phrased. The gated part (cells) has been **frozen since 2026-09-24**, so where a Models page shows a gated phrase, it dates from then. The lead may turn `LEGACY_CELLS` back on, or the gated phrases should be labelled as frozen. |
| FR-22 | State consensus in words assembled from counts; never compute or display a score | ✅ Still holds | `CLAUDE.md` rule 3. Compare shows "how it was phrased" beside the counts, with no score. |
| FR-23 | Display quotes exactly as written: the raw span, never the normalised form | ✅ Still holds | — |
| FR-24 | Report silence explicitly, rendered distinctly from criticism | ✅ Still holds | `CLAUDE.md` rule 4. |
| FR-25 | Preserve conditional consensus rather than flattening it to an average | ❓ Open | `contract/conditions.yaml` exists, but the board's "conditions" blocks are **not built** (left empty, never invented). **Lead:** is it still wanted on the board? |
| FR-26 | Every label stores and links the quote IDs that earned it | ✏️ Updated | **Every board entry links the quote that earned it.** Labels are no longer used: the `label` table has 0 rows. |
| FR-27 | Record every label gained or lost in a changelog, with its cause | ❓ Open | `/changelog` reads `label` and `label_change`, which both have **0 rows**. The classifier board doesn't write labels. **Lead:** retire it, or rebuild it as "every board-entry change, with its cause". `judge/pages/changelog.py` is kept unwired until then. |

## 5. The Ask box: on hold (FR-28 to FR-36, NFR-1, NFR-2)

The Ask box UI was removed in `4248bb7`. Its backend (`judge/ask/*`, `judge/store/answers.py`, `/ask/*`) is **kept as future scope**. These requirements are not current work.

| ID | Original requirement | Status |
|---|---|---|
| FR-28 | Accept three input shapes: a task, a product brief, or a pasted agent config | ⏸ On hold |
| FR-29 | Decompose a brief into roles, each with a runs-per-request figure | ⏸ On hold |
| FR-30 | Show every inferred assumption as an editable field; re-run on edit | ⏸ On hold |
| FR-31 | Filter on reported effective context, never the advertised window | ⏸ On hold |
| FR-32 | Gate on evidence before ranking; rank qualified candidates by cost alone | ⏸ On hold |
| FR-33 | Segregate unevidenced candidates from the ranked list | ⏸ On hold |
| FR-34 | Bind every sentence of justification to a quote ID | ⏸ On hold |
| FR-35 | Abstain when evidence is insufficient, naming the capability that lacks it | ⏸ On hold |
| FR-36 | Answer "why not X?" and "show me the evidence against it" as first-class queries | ⏸ On hold |
| NFR-1 | Answer path p95 under 800 ms cold | ⏸ On hold |
| NFR-2 | Query time never touches the evidence pipeline | ⏸ On hold. The principle still applies to the board: a broken harvest must never take the board down. |

## 6. Non-functional (NFR-3 to NFR-10)

| ID | Original requirement | Status | How it stands now |
|---|---|---|---|
| NFR-3 | A hard daily extraction budget that degrades to triage-only rather than overrunning | ✏️ Updated | Still the design: `EXTRACTION_DAILY_BUDGET_USD`, with no default in code on purpose (rule 12). **The value needs agreeing.** This branch runs $3; the GitHub Actions variable reads 2.00; Railway's is unconfirmed. Every model call is recorded in the spend ledger. Blog generation is recorded there but sits outside this cap. |
| NFR-4 | `pipeline_version` on every derived row; full rebuild from the raw store always possible | ✅ Still holds | `board_entry` carries `pipeline_version`. |
| NFR-5 | Official APIs and public feeds only, robots.txt, identifying User-Agent, no paywall circumvention, quote + attribution + link, never full text | ✏️ Updated | All of that still holds, **plus the publication policy**: Reddit, arXiv and X are collected for internal work but never shown on public pages (`contract/publication.yaml`). Blog drafts may draw on them as prose and short fragments, with no link, handle or platform name. |
| NFR-6 | Honour upstream deletion and takedown through a tombstone path | ✅ Still holds | `contract/tombstoned_models.yaml` and the tombstoned document status. |
| NFR-7 | Extraction hardened against prompt injection | ✅ Still holds | The untrusted-text wrapper, a forced schema, no tools and no network. |
| NFR-8 | Exactly two stages use a language model: `judge/extract/` and `judge/ask/` | ✏️ Updated | **Three callers.** The blog generator was **agreed as a third caller on 2026-10-06** (#508, Parvathi; agreed by Anooj), with conditions: drafts only, every call in the spend ledger, outside the extraction cap. Still no model in counting, weighting, gating, ranking, filtering or phrase assembly. *(`CLAUDE.md` rule 2's heading still says "Exactly two stages" above the paragraph that adds the third.)* |
| NFR-9 | One extractor, pinned in config: `google/gemini-2.5-flash`, with halt-and-flag on silent regression | ✏️ Updated | **`deepseek/deepseek-v4-flash`**, chosen by the 2026-09-01 A/B test. It is now a **classifier** that files evidence into board sections. It is sent as the **undated alias**: all 3,077 ledger rows read `deepseek-v4-flash`, and which build served the calls is **not yet verified** (`judge/extract/client.py`). Halt-and-flag stays in the requirement, but can't fire until the served build is recorded. |
| NFR-10 | Thresholds, weights, capabilities, aliases and filter rules in versioned config, not code | ✅ Still holds | `CLAUDE.md` rule 5, `contract/`. |

---

## 7. Built since the plan, with no requirement yet

These features are reviewed and running, but `BUILD-PLAN.md` has no requirement saying what "done" means for them. **The numbers below are proposals for the team to confirm.** They continue after FR-36 so no existing ID changes meaning.

| Proposed ID | Requirement | What exists today |
|---|---|---|
| FR-37 | **Board sections.** Evidence is filed by the classifier into Best for (jobs), Capabilities and Metrics, from a versioned vocabulary, as ungated observations counted by distinct voices. | `contract/board_surfaces.yaml`, `board_entry`, `GET /board`. |
| FR-38 | **Publication policy.** A withheld source never appears on a public view as a quote, link, handle or count, and a page built without it says so. | `contract/publication.yaml`, `judge/publication.py`, `PUBLICATION_VIEW`. |
| FR-39 | **Blogs.** Drafts generated from the evidence are stored as pending, approved or rejected. Only approved posts are public. The public read fails closed. Every generation run is recorded with its cost. | `blog_post`, `GET /blog-posts`, Admin → Blogs, `/admin/blog-logs`. |
| FR-40 | **Compare.** Up to three models side by side, by the sections they share, with counts and phrasing and no score. | `/compare`. |
| FR-41 | **Scheduled fetch.** A daily fetch per tracked model, within the caps, with run history and failures shown in Admin. | `scheduled-fetches.yml` (daily), Admin → Scheduler and Runs. |
| FR-42 | **Admin.** Read-only operational views. Credentials are shown only as "set" or "not set", never their values. | `/admin`. |
| NFR-11 | **Spend ledger.** Every model call is recorded at the provider's reported cost, by stage. Extraction and Ask fall under the daily cap; blog generation is recorded but outside it. | `spend_ledger`, Admin → API usage. |
| NFR-12 | **Shared raw store.** Payloads are content-addressed and immutable, and shared between machines. A run says what it could not read, and never treats it as empty. | Postgres `raw_blob` (since #510), `collect/rawstore_reader.py`. |
| FR-43 | **Automatic seating.** New models from tracked providers are admitted by rule, and aliases are seated only in versioned forms, with collisions refused. *(Could instead be folded into FR-1.)* | `auto_track`, `contract/tracked_models.yaml`. |

---

## 8. Summary

| Status | Count | IDs |
|---|---|---|
| ✅ Still holds | 18 | FR-2, 4, 5, 7, 8, 9, 10, 12, 13, 15, 16, 22, 23, 24; NFR-4, 6, 7, 10 |
| ✏️ Updated | 12 | FR-1, 3, 6, 11, 14, 18, 21, 26; NFR-3, 5, 8, 9 |
| ❓ Open (lead) | 5 | FR-17, FR-19 + FR-20 (together), FR-25, FR-27 |
| ⏸ On hold (Ask box) | 11 | FR-28 to FR-36, NFR-1, NFR-2 |
| **Total in the plan** | **46** | |
| ➕ Proposed new | 9 | FR-37 to FR-43, NFR-11, NFR-12 |

## 9. Open decisions in one place

| # | Decision | Owner |
|---|---|---|
| 1 | FR-1 and FR-3: poll the registry daily, or drop the 24-hour target | Team |
| 2 | FR-11 and NFR-3: the agreed daily budget, and where it is set (branch $3, GitHub variable 2.00, Railway unconfirmed) | Team |
| 3 | FR-17: retire cross-platform author clustering, or keep it as a known gap | Lead |
| 4 | FR-19 and FR-20: retire the seven weighting factors, or turn `LEGACY_CELLS` back on | Lead |
| 5 | FR-21: turn the gated cells back on, or label them as frozen since 2026-09-24 | Lead (follows 4) |
| 6 | FR-25: build conditions on the board, or retire them | Lead |
| 7 | FR-27: retire the changelog, or rebuild it on board entries | Lead |
| 8 | NFR-9: record which build of the extractor actually serves our calls | Team |
| 9 | Confirm the proposed FR-37 to FR-43, NFR-11 and NFR-12 | Team |
