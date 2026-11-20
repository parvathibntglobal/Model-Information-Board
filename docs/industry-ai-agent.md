# Industry AI agent: AI data from five industries

*Design and handover for the lane built in #644 (2026-11-20). Plan by Parvathi; the
code points here as "docs/industry-ai-agent.md §N". Keep this file in step with the
code: a change to how a stage works is a change here too.*

## 1. Goal

The **Industry AI agent** is a **separate part of the modelboard** that collects as
much data as possible about **AI in five industries**:
- **Finance**
- **Healthcare**
- **Hospitality**
- **Engineering**
- **Governance**

It harvests from Reddit, X, GitHub, Hacker News, dev.to, Bluesky and blog/RSS feeds,
driven by **keywords per domain per platform** in `contract/industry_ai.yaml`.

A signed-in **AI in industries** page (`/ai-in-industries`) shows how much data has
been collected for each domain, by content type. It shows **counts only, never post
text.**

**Code only:** no language model, no LLM-named subcategories, no polarity. An LLM is
an optional later step (§9), added only if the sample check (§7) shows the code
labels are too inaccurate.

### What is kept, and how it is labelled

Every kept item gets a **content type**, assigned by code (`type_patterns`; the first
type in `type_order` that matches wins):

| Type | Examples |
|---|---|
| `use_case` | AI deployed, piloted or tried first-hand for a real task |
| `how_to` | tips, prompt lists, guides, tutorials, and courses that teach something |
| `tool_or_product` | an AI tool, product or open-source project for the domain; GitHub items by default |
| `news` | announcements, launches, plans |
| `discussion` | questions, opinions, predictions; also an item that matches no type |
| `research` | papers, studies, reports |

A `use_case` also gets a **stage guess**: `deployed`, `pilot` or `first_hand`.

### What is dropped (and counted by reason)

Anything that is not data about AI in these industries:
- spam and scams;
- sponsored, affiliate or discount content;
- course or webinar **sign-up ads** (a post that teaches something is kept as
  `how_to`);
- hiring posts;
- bots;
- non-English posts;
- off-topic matches from ambiguous words;
- duplicates, which count as reach on the item they copy.

---

## 2. Principles

1. **Stages are numbered in the order they run** (§3). The model pipeline's numbering
   is misleading (its "vet" checks run before extraction), and this lane does not
   repeat that.
2. **Every check runs in code, before anything that costs money.** Today the only
   cost is metered API requests (Reddit and X, via RapidAPI). If an LLM is ever
   added (§9), it is the **last** step and sees only items that passed every filter.
3. **A dropped item is really dropped.**
   - In the model pipeline, triage's "dropped" verdict is ignored by the selection
     that feeds the LLM. Here, no later stage looks at a dropped item.
   - **Dropped items are stored with their stage and reason.** They are the page's
     denominator (rules 4 and 7), and `--relabel` re-applies changed rules to them.
4. **Noise is cut as early as possible:** at the search (definite-noise exclusions,
   language filter), at the sieve (AI term plus industry term, with context rules),
   then at the filters.
5. **When the domain is doubtful, the item goes to "domain unconfirmed"** (rule 6).
   It is never forced into a domain.
6. **A separate lane,** like `news_item` / `topic_item`.
   - It writes `iai_item` and `iai_run` only.
   - The model pipeline never reads them.
   - This lane reads only the model registry's names, read-only, as extra AI terms.
7. **Every kept item's text and link are stored**, so a classifier or subcategories can
   be added later without re-harvesting.
8. **Config lives in `contract/`** (rule 5). The loader refuses a missing key or a
   broken pattern by name (rule 12).
9. **No spend without a go-ahead.** Each platform has a request cap per run, `--plan`
   and `--relabel` make no request, and `--dry-run` writes nothing.

---

## 3. Stages (in run order)

```
1 Harvest ─▶ 2 Sieve ─▶ 3 Dedupe ─▶ 4 Filter ─▶ 5 Label ─▶ 6 Store
```

Code: `collect/industry_ai/` (`harvest.py`, `rules.py`, `pipeline.py`, `store.py`),
composed by `scripts/run_industry_ai.py`. Stages 2–5 run over **the whole stored
collection** on every run, so dedupe sees every copy and a rule change applies to old
items too.

### 1. Harvest (`harvest.py`)

- **Queries:** the contract's queries per domain × platform:
  - Reddit: subreddit listings and searches;
  - X: searches, with `query_suffix` (`lang:en -is:retweet -hiring -giveaway`);
  - GitHub: issue searches;
  - Hacker News, dev.to, Bluesky: searches;
  - feeds: ids from `contract/sources.yaml` `feeds:`.
- **Gates:** each platform is built through its **own gated entry point**
  (`harvester_for_source`, or `fetcher_for_source` for feeds). Terms rulings,
  robots.txt, rate limits and RapidAPI quota recording therefore apply exactly as in
  the model fetch. A refused or unconfigured platform is reported and skipped; the
  others still run.
- **The request cap** (`run.max_requests`) is checked **before each query**. A query
  that would pass it is not run, and the run log says "capped". Every raw page is
  stored in the raw store before it is read.
- **One item per id**, however many queries found it. Each finding domain becomes a
  **hint**, never a label.
- **Not in this version: Reddit comments.** Only posts are read, which saves RapidAPI
  requests. Domain and type are decided from the post itself anyway.

### 2. Sieve (`rules.sieve`, `rules.outside_window`)

- **Window:** an item posted before `run.window_days` is dropped (`outside_window`).
  An undated item is kept (rule 6).
- **AI term:** the item's **title or body** (never comments) names one of `ai_terms`
  or a registry model name.
  - **"AI" in capitals counts on its own, as a whole word.** Lower-case "ai" and
    `.ai` (a file type or web domain) do not.
- **Industry term:** a term of **any** domain, matched **outside** the excluded
  phrases (`global_exclude_phrases`, each domain's `exclude_phrases`):
  - "prompt / context / social / reverse / software engineering" are not Engineering;
  - "AI governance" is not Governance while the scope excludes it (§11);
  - `.ai` and "artificial insemination" are not AI.
- **Ambiguous terms** (`ambiguous_terms`, e.g. bank, claims, trading, patient, guests)
  count only with one of their context words within `run.context_window_words`.
- **Drops:** `no_ai_term`, `no_domain_term`.

### 3. Dedupe (`pipeline._dedupe`)

Three passes, each over what the previous pass left:

1. **The same article on several platforms** is one item. Links are compared after
   `canonical_url`: tracking parameters, `www.` and trailing slashes are removed.
   The copies are dropped as `shared_link` and counted on the kept item as **reach**
   (`share_count`).
2. **The same author posting the same text again:** one is kept, the rest are dropped
   as `repeat_post`, and the author is flagged `repeat_author`.
3. **Near-duplicate text** is clustered by the corpus's own MinHash
   (`collect/assemble/dedupe.py`) and dropped as `near_duplicate`. Texts below its
   token floor are never merged, because over-merging is the worse failure.

### 4. Filter (`rules.filter_reason`)

In order. The first that matches drops the item:

| Reason | What |
|---|---|
| `too_short` | under `run.min_text_chars` of text with links removed. **A pure link to an article is kept** (flag `link_share`) and deduped onto the article. |
| `bot` | an author the bot list declares (`contract/bots.yaml`), only on platforms the list covers |
| `non_english` | the platform's declared language, or a small function-word check where none is declared |
| `spam` | `spam_patterns`: trading bots, "1000% returns", signals groups, engagement bait, giveaways |
| `promo` | `promo_patterns`: sponsored, affiliate parameters, promo or discount codes |
| `hiring` | `hiring_patterns` |
| `signup_ad` | `ad_patterns`, **unless** `teach_patterns` also match (then it is kept as `how_to`) |

**Flag, never a drop:** `low_engagement`, for score, likes or points at or below
`run.low_engagement_max`.

### 5. Label (`rules.label`)

- **Domain:** the hinted domains whose own terms matched. If none was confirmed, the
  item goes to **domain unconfirmed** (empty `domains`). Another domain whose terms
  matched is recorded as the flag `also_matches:<domain>`. An item confirmed for two
  domains counts in both, and the page says so.
- **Type:** the first of `type_order` with a matching pattern. GitHub items are
  `tool_or_product` unless a use-case pattern matches. No match means `discussion`.
- **Stage** (use cases only): the first of `stage_patterns`, in the contract's order.

### 6. Store (`store.py`)

- **Inserting:** a new item is inserted. One found again refreshes `last_seen_at` and
  its engagement, and widens its domain hints and query keys.
- **Labels:** the label columns are rewritten by every run and every `--relabel`.
- **Nothing is ever deleted.**
- **Each run** is a row in `iai_run`, holding requests, quota, per-query yields,
  counts and status.

---

## 4. The "AI in industries" page

- **Route:** `/ai-in-industries`, signed-in (`web/src/routes/IndustryAI.jsx`).
- **API:** `GET /industry-ai` (`judge/industry_ai/view.py`), which reads `iai_item` and
  `iai_run` live.
- **Per domain:**
  - kept, and found by its queries;
  - distinct authors;
  - reach;
  - kept by content type, by platform, by use-case stage, and by month posted;
  - undated items.
- **Also:** totals collected, kept and filtered out; the domain-unconfirmed bucket;
  filtered out by reason; the last run.
- **No post text, link or author** leaves the API (`tests/test_industry_ai.py`
  checks this).
- **Empty states:** "Nothing collected yet" when there is no data, and a clear message
  if the migration has not run.

---

## 5. Storage

Migration `contract/migrations/20261120T1000_industry_ai.sql`, mirrored in
`contract/tables.sql`. Every column is declared in `contract/column_states.yaml`.

- **`iai_item`:** one row per harvested root post or article.
  - Identity, text and engagement: id, platform, url, title, body, created_at,
    author_id, lang, engagement.
  - What found it: link, domain_hints, query_keys.
  - The verdict: verdict, drop_stage, drop_reason, flags.
  - The labels: domains, content_type, matched_pattern, stage_guess.
  - Dedupe: canonical_of, share_count, canonical_url.
  - pipeline_version.
- **`iai_run`:** one row per run (harvest or relabel), holding status, requests per
  platform, RapidAPI quota, per-query yields and the counts.

---

## 6. Operations and logs

- **`scripts/run_industry_ai.py`:**
  - `--plan`: lists every query and cap; no network;
  - `--dry-run`: harvests and prints counts; writes nothing;
  - no flag: harvests, labels and stores;
  - `--relabel`: re-applies the rules to stored items; no network;
  - `--domains`, `--platforms`: narrow any of them;
  - `--post-summary`: posts the counts to `INDUSTRY_AI_ISSUE`.
- **The run log** prints every stage: requests and items per platform, capped or
  skipped queries, quota, drops by stage and reason, and kept items per domain by
  type and platform.
- **Workflow:** `.github/workflows/industry-ai-harvest.yml`.
  - Weekly, Wednesdays 09:00 UTC, with its own concurrency group.
  - **Off until `INDUSTRY_AI_ENABLED=1`.** A manual start defaults to a dry run.
  - Shared staging database; `RAW_STORE_REMOTE=postgres` so payloads reach the
    shared raw store.
- **Admin:** the "Industry AI" scheduler tab (`judge/sections_status.py` `FEEDS`).

---

## 7. Measure once, before trusting the counts

1. **Run** a dry run, then a capped real run. Read the yields and prune queries that
   return nothing.
2. **Hand-check a sample:** about 150–200 **kept** items and about 50 **dropped** ones,
   across domains, platforms and types. Mark each one's correct domain and type, and
   whether its drop was right. The `flags` and `matched_pattern` columns show why
   each was labelled as it was.
3. **Report on the lane's issue:**
   - domain accuracy;
   - type accuracy (especially `use_case`);
   - wrong drops, by reason;
   - the size of "domain unconfirmed".
4. **Tune** the contract, then run `--relabel` (no requests) and re-check.

---

## 8. Known risks

| Risk | Handling |
|---|---|
| "prompt engineering" floods Engineering | excluded phrase |
| "AI governance" floods Governance | scope set in the contract (§11) |
| `.ai` files, "artificial insemination" | excluded phrases; "AI" in capitals only |
| finance scam spam | `spam_patterns` |
| one article counted many times across platforms | link dedupe; shares count as reach |
| a doubtful domain inflating a count | the "domain unconfirmed" bucket |
| false drops from patterns | the sample check (§7), then `--relabel` |
| metered requests | caps per run, weekly cadence, dry run first |

---

## 9. Optional later step: an LLM

**Only if §7 shows the code labels are too inaccurate after tuning.** If added:
- **It is the last step.** One short call per **kept** item, to correct domain and type.
- **Its supporting quote is checked word for word** in code (`judge/extract/verify.py`).
- **Prompt caching:** a fixed prompt prefix with the post text last. Cached tokens,
  billed cost and cache hit rate go in the run log.
- **Spend:** a per-run ceiling inside the shared daily cap, and its own `spend_ledger`
  stage.

That is a separate decision, and a separate build.

**Subcategories, also optional:** keyword groups per domain in the contract, assigned
in code.

---

## 10. Tuning notes from the build's test runs

From starter queries only, on Hacker News and dev.to, 2026-11-20: pointers, not
measurements.

1. **AI terms with other meanings.**
   - Acronyms ("RAG", "NLP", "LLM") match in any case, so "rag" counts as AI.
   - Gemini, Llama, Claude and Mistral are also ordinary words.
2. **Broad industry terms:** "agency", "engineers", "booking", "tax", "payments",
   "simulation" and "council" are candidates for `ambiguous_terms`.
3. **Type patterns.**
   - "launched", "introducing" and "meet" over-count `tool_or_product`.
   - The `use_case` phrasings are narrow.
4. **Hacker News items are often a title only,** so they are judged on the headline.
5. **Retention.** `iai_item.body` stores post text, Reddit's included, in the shared
   database. It is never shown, but the main pipeline's Reddit data-retention
   question applies here too.

---

## 11. Open points

- **Governance scope:** public-sector use of AI only (the starter contract), or
  AI-governance practice as well. To widen it, drop the `AI governance` exclusion
  and add its terms.
- **First-harvest lookback** (`run.window_days`, 365 to start).
- **Domain feed lists.** Add feeds to `contract/sources.yaml` `feeds:` (each needs a
  terms ruling), then list them per domain.
- **Vendor case studies:** whether to count them separately within `use_case`.

---

## 12. Verification

- **`tests/test_industry_ai.py`:**
  - the fixture cases (prompt tips → `how_to`; deployment and pilot → `use_case` with
    stage; "prompt engineering", `.ai`, "artificial insemination", trading-bot spam,
    sign-up ad, hiring, "AI governance");
  - cross-platform link dedupe; repeated posts; two domains; the unconfirmed bucket;
    the window;
  - the request cap; strict config;
  - a database round trip through the page builder that checks no text leaks.
- **Repo guards:** lane boundary, migrations, column states, API fields, routes, SEO
  files, CSS classes, Admin surfaces, script encoding.
- **End to end:** a dry run, then a capped run on the shared database. Compare the
  run log, the page and direct SQL counts.

---

## 13. After merge: what the team does next

**There are no prompts to adjust:** this version uses no LLM. Everything below is
configuration and running.

### 1. Set up

- **Run the migration on the shared database straight after merge**
  (`python -m collect.cli db migrate`), and announce it.
- **Create the lane's summary issue and set the repository variables:**
  - `INDUSTRY_AI_ISSUE`: that issue's number;
  - `INDUSTRY_AI_ENABLED`: **leave unset (off)** until the tuning below is done.
- **Confirm `RAW_STORE_REMOTE=postgres`** wherever the pipeline runs, including the
  hosted app if runs are started there.
- **Confirm the RapidAPI keys** (Reddit, X) are in the repository secrets.

### 2. Fill the config (`contract/industry_ai.yaml`)

- **Queries per domain per platform:**
  - Reddit: subreddits plus searches;
  - X: searches;
  - GitHub: narrow searches;
  - Hacker News, dev.to, Bluesky: searches.
- **Feed lists per domain.** Each feed needs a terms ruling in `contract/sources.yaml`
  first.
- **Terms, context terms and excluded phrases**, including the Governance scope
  (§11), and the tuning notes in §10.
- **Patterns:** spam, ad, hiring, promo and type patterns.
- **Run settings:** `window_days` and `max_requests` per platform, which keeps
  RapidAPI spend capped.
- **Every change goes through a PR**, since the file is under `contract/`. After it
  merges, run `--relabel`.

### 3. Run and check

- **Dry run first**, then a small capped real run for one domain, then all five.
- **Prune** queries that return nothing.
- **Do the sample check (§7)**, record the rates on the lane's issue, tune the rules,
  and run `--relabel`.
- **Compare the page's counts with direct database counts.**

### 4. Turn it on

- **Set `INDUSTRY_AI_ENABLED`** for the weekly schedule, only after the sample check.
- **Watch RapidAPI usage.** This lane shares the monthly quota with the model fetches.

### 5. Rules for whoever tunes it

- **Change the YAML, not the code.**
- **Never put Reddit or X text on a public page.** The page is signed-in and
  counts-only.
- **No LLM step without a separate decision** (§9).
- **Anything that spends beyond the caps is announced first.**
