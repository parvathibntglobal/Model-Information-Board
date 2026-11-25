# Industry AI agent: AI data from industries and functions

*Design and handover for the lane built in #644 (2026-11-20). Plan by Parvathi; the
code points here as "docs/industry-ai-agent.md §N". The domains, keywords and queries
are the team's, loaded in #645 (anooj). Keep this file in step with the code: a change
to how a stage works is a change here too. The contract file itself is the source for
which domains, terms and queries exist; this document describes how they are used.*

## 1. Goal

The **Industry AI agent** is a **separate part of the modelboard** that collects as
much data as possible about **AI in industries and functions**.

**The domains** (as loaded by #645, 2026-11-20; `contract/industry_ai.yaml` is the
source):
- **20 umbrellas:** 11 industries (`kind: industry`) and 9 functions (`kind:
  function`, roles that cut across industries), with about 536 two-word workflow
  keywords as their terms.
- **Five are `active` for the first test run:** Marketing, Content & SEO; Design &
  Creative; Security & IT; Retail & E-commerce; Personal & Everyday Life. They were
  chosen as the umbrellas with the highest share of keywords showing strong AI
  evidence on Reddit and Hacker News (#645).
  - **Recounted in #646:** a keyword that carries "AI" itself passes that evidence
    test by construction, so those keywords are left out of the count.
  - That took Leaders & Founders from 14/23 to 10/19 strong, so Personal & Everyday
    Life (15/25) replaced it.
- **The build's starter five** (Finance, Healthcare, Hospitality, Engineering,
  Governance) stay in the file, complete, with `active: false`. Each is one line to
  switch back on.
- **Groups:** Engineering (*Software & AI*, *Physical*), Film (four groups) and
  Governance (*Public Sector & Nonprofit*, *AI Policy & Governance*).

It harvests from Reddit, X, GitHub, Hacker News, dev.to, Bluesky and blog/RSS feeds,
driven by **keywords per domain per platform** in `contract/industry_ai.yaml`.

**How the contract expresses this** (#644 review):
- **`kind`:** each domain is an `industry` or a `function` (a role that cuts across
  industries, like marketing or support).
- **`active`:** only `active: true` domains are harvested, so the file can hold every
  umbrella while a few run.
- **`groups`:** a domain may hold groups, each with its own terms, exclusions and
  queries. Engineering has two: *Software & AI* and *Physical*.

A signed-in **AI in industries** page (`/ai-in-industries`) shows how much data has
been collected for each domain, by content type. It shows **counts only, never post
text.** Each card opens that domain's own page (§4), which lists the posts as excerpts.

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

### The observer: the keyword agent's twin (watch lists; anooj, 2026-11-20)

The queries under `domains:` find posts **by keyword**. The observer finds them **by
who or where**: the newest posts of chosen communities, accounts and lists, with no
keyword. It catches what our keywords would never have guessed: new tools and
workflows, launches, and opinions from the people who shape the field.

**One lane, one pipeline, one page.** It runs the same stages (§3) into the same
tables. A post found by both a keyword query and a watch source is **one row with
both query keys**.

**Where it differs:**
- **The sieve:** a watched post needs an AI term; an industry term is optional.
- **The label (option A), for a post found ONLY by watch lists:**
  - one that names industry terms is filed under **every domain whose terms it
    names**, flagged `domain_from_terms:<domain>`;
  - one that names none is kept as **General AI** (flag `general_ai`).
  - General AI is counted apart from "domain unconfirmed", which means a keyword
    query's own domain was not confirmed. They are two different absences (rule 4).
  - **A post a keyword query also found keeps the keyword agent's label and window**
    (#650 review), so a post is never labelled differently just because a watch list
    also saw it.
- **The watch window** (#650 review, point 1):
  - a post found only by watch lists is kept if it was posted within
    `watch.lookback_days` of when the lane **first saw it** (`first_seen_at`);
  - otherwise it is dropped as `outside_watch_window`.
  - **Why it is needed:** Reddit's newest page and Bluesky's `from:` feed return posts
    of any age. X (`since:`) and Hacker News (`created_at_i>`) already ask for the
    window.
  - **Measured from first sight, not from today,** so a later `--relabel` never drops
    a watched post just because time has passed.
- **Its own switch and caps:** `watch.enabled` and `watch.max_requests`, so watching
  can never spend the keyword queries' budget.
  - **Quota:** with the watch lists on, a weekly run spends up to 30 more X and 25
    more Reddit requests, on top of the keyword queries' 110 and 40, from the same
    monthly RapidAPI quota the model fetches use.
- **One query loop:** both loops run each query through `_run_query`, so watched
  sources get #648's failure handling too. A failed request is marked `error`, never
  "0 items".

**The lists** (`contract/industry_ai.yaml` `watch:`, at most 20 per platform for now):

| Platform | What is watched | How |
|---|---|---|
| Reddit | communities | `list_subreddit`, newest first |
| X | AI personalities (accounts) | `(from:a OR from:b …) since:<date>`, paged over `watch.lookback_days` (`watch.x_pages`), with `watch.x_suffix` (replies excluded in the first test runs) |
| Bluesky | accounts | `from:<handle>` search |
| Hacker News | Show HN, Ask HN, front page, and authors | Algolia tags; an author's stories **and** comments |

- **Each source has a query key,** `watch:<platform>:<source>`, and its own yield in
  the run log, so a source that brings nothing gets flagged for pruning.
- **Designed, not built yet:** dev.to tags, GitHub repos, and newsletters. Until each
  one's runner exists, a list for it is refused, not ignored.

**One person, several handles** (`watch.people`, 2026-11-24). Six watched people post
on two or three platforms. Without a map, a person counted as one author per platform,
and their same post on X and Bluesky stayed two items.
- **Measured 2026-11-20,** over one 7-day window of the X, Bluesky and Hacker News
  watch lists: Ethan Mollick's kept posts (18 Bluesky, 17 X) counted as 2 authors and
  Simon Willison's as 3; of 3 same-text cross-posts, the dedupe caught 1.
- **How a post finds its person:**
  - X: the handle in the post's URL;
  - Bluesky: the author's DID, which the map holds as `bluesky_did` (resolved by hand
    on 2026-11-24), so a post found by a keyword query links too. A post found by the
    `from:<handle>` query whose author is a different DID links to no one: the handle
    has passed to another account. A person written without a DID links by handle;
  - Hacker News: the author's username.
- **A quiet handle is noted.** When a mapped handle's watch query answers and finds
  nothing in `watch.lookback_days`, the run log says so: the person was quiet, or the
  handle changed. "Nothing" is counted before the sieve: the account posted nothing at
  all. A note, never a gate. A skipped, capped or failed query says nothing about the
  handle, so it gives no note.
- **A handle that changed hands is noted too.** When a mapped Bluesky handle's `from:`
  query returns posts by an account other than the person's DID, the run log says so,
  with the count, and asks for the DID to be re-resolved. Those posts already link to
  no one; the note makes visible that the watch list is harvesting a stranger.
- **What it changes:**
  - the post carries a `person:<key>` flag, and a person is **one author** in the run
    log and on the page;
  - a person's same text on two platforms, posted within `watch.cross_post_hours`, is
    folded as `cross_post` (dedupe pass 3).
- **Never guessed:** only a person written in the map links two handles. Every handle
  must already be in its platform's watch list, a person needs at least two platforms,
  and a handle can belong to only one person.

**Runs:**
- `--watch` adds the watch lists to a run.
- `--watch-only` runs only them; it's the observer's own dry run.
- A scheduled run includes them once `watch.enabled` is true.

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

- **Queries:** the contract's queries per **active** domain, and per group, × platform:
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
- **Queries are taken round-robin across domains** within each platform, so every
  domain gets its first query before any gets its second. Walked in file order, one
  cap per platform would starve whichever domains come last.
- **X pages per query:** a query clubbing at least `run.x_clubbed_min_keywords` (5
  since #645; a list rarely splits into sixes) quoted keywords gets
  `pages_per_query.x_clubbed` (5) pages; any other gets
  `pages_per_query.x`.
  - Measured 2026-11-20 on our X route: a six-keyword `("a" OR "b" ...) (AI OR LLM
    ...)` query returned 100 distinct posts over 5 pages, with more after.
  - **An X query plus its suffix must stay within 480 characters.** X cuts a longer
    query off rather than refusing it, so the loader refuses it instead.
- **Platform quirks:**
  - **The X suffix** (`lang:en -is:retweet ...`) is untested on our route (a
    scraper). Record one query with and without it on the first dry run.
  - **Reddit search ignores quotes, minus signs and OR** on our route, so a Reddit
    query is loose words, and the sieve decides. Judge a Reddit query by its yield
    in the run log.
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
- **Industry term:** a term of **any** domain or group, matched **outside** the
  excluded phrases. The order is: global exclusions, then the domain's (for all its
  terms), then a group's (for that group's own terms only):
  - "prompt engineering" counts for Engineering's *Software & AI* group (anooj,
    #645) and never for *Physical*; "context engineering" matches neither;
  - "software engineering" and its relatives are excluded from *Physical* only;
    they are *Software & AI*'s own terms;
  - a term must never be cancelled by its own exclusions: a test checks every
    domain and group (#645);
  - "data / corporate governance" are not Governance;
  - `.ai` and "artificial insemination" are not AI.
- **The matched terms are kept** (`matched_terms`, `ai_terms`): which terms of which
  domain and group an item named. One post can count for several keywords.
- **Ambiguous terms** (`ambiguous_terms`, e.g. bank, claims, trading, patient, guests)
  count only with one of their context words within `run.context_window_words`.
- **Drops:** `no_ai_term`, `no_domain_term`.

### 3. Dedupe (`pipeline._dedupe`)

Four passes, each over what the previous pass left:

1. **The same article on several platforms** is one item. Links are compared after
   `canonical_url`: tracking parameters, `www.` and trailing slashes are removed.
   The copies are dropped as `shared_link` and counted on the kept item as **reach**
   (`share_count`).
2. **The same author posting the same text again:** one is kept, the rest are dropped
   as `repeat_post`, and the author is flagged `repeat_author`.
3. **One person, the same text, two platforms** (`watch.people`): one is kept, the
   rest are dropped as `cross_post` and counted as its reach, and the kept one is
   flagged `cross_post`. Mentions, tags and links are left out of the text
   comparison, since each platform spells them differently. A copy is folded only
   when all of these hold (#653 review):
   - it is on a **different platform** from the earlier post (a same-platform repeat
     is pass 2's);
   - it was posted within **`watch.cross_post_hours`** of it (6; the 3 folds read by
     eye on 2026-11-24 were 0 to 4 minutes apart);
   - when **both** carry an article link, it is the **same link**;
   - both are **dated** and the text is **20 characters or more**.
4. **Near-duplicate text** is clustered by the corpus's own MinHash
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

- **Domain:** the hinted domains whose own terms (or their groups' terms) matched.
  If none was confirmed, the item goes to **domain unconfirmed** (empty `domains`).
- **Groups:** within a confirmed domain, every group whose own terms matched, stored
  as `"<domain>/<group>"`. Another domain whose terms
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
- **Per domain** (active domains, and any switched-off domain that still holds data):
  - kept, and found by its queries;
  - kept per group;
  - distinct authors;
  - reach;
  - kept by content type (the top four, the rest named), by platform (one sorted line),
    and by use-case stage;
  - **in tabs, one population each:** *Collecting* (domains whose own searches run, as
    cards, most kept first), *Watch lists only* (switched-off domains holding only
    watch-list posts, as one-line tiles), *Not filed under a domain*, *Filtered out* (by
    reason) and *Nothing collected*. The whole card opens the domain's page. No month
    chart on the cards (2026-11-24): nearly every post is from the harvest window, so it
    drew one spike; the domain's page shows the months;
  - undated items.
- **Also:** totals collected, kept and filtered out; the domain-unconfirmed bucket;
  filtered out by reason; the last run.
- **No post text, link or author** leaves the API (`tests/test_industry_ai.py`
  checks this).
- **Empty states:** "Nothing collected yet" when there is no data, and a clear message
  if the migration has not run.

- **Kept for a few minutes** (`judge/industry_ai/cache.py`, 2026-11-24): each view (the
  summary; each domain's tab, filters, order and page) is worked out once and kept for
  10 minutes. After that the old answer is still sent at once while ONE background
  refresh replaces it. Refreshes happen only when someone asks, so an answer older than
  an hour is recounted while the visitor waits (~5 s), ONE recount per view (anyone
  arriving meanwhile gets the old answer at once); the old one is sent only if that
  recount fails, its `counted_at` showing its age. The summary and each collecting domain's first view are worked
  out at API startup. Every answer carries `counted_at`, shown on the page. Measured on
  2026-11-24 from a developer machine against the shared database: ~5 s uncached,
  under 0.04 s kept.

### One domain's page (2026-11-24, Parvathi)

- **Route:** `/ai-in-industries/<key>`, signed-in (`web/src/routes/IndustryAIDomain.jsx`),
  opened from the domain's card. `general` and `unconfirmed` open the two buckets.
- **API:** `GET /industry-ai/{key}` (`industry_ai_domain_view`), live, signed in.
  Unlike the summary, **it carries post text**: each post's text up to its first
  600 characters, with its link, author id, dates and engagement. **Most posts are
  shorter, so are shown whole** (on 2026-11-25, 5,476 of 7,693 stored posts with
  text: every Bluesky and dev.to post, 1,571 of 2,184 X posts, 647 of 1,341 Reddit
  posts); a longer one is cut, and the link leads to the rest.
- **Three populations, never added together:** kept by the domain's own queries
  (the card's "kept"), kept from the watch lists and filed here by their terms, and
  filtered out (found by the domain's queries), each with its count.
- **Two view tabs:** *Posts* (a row of dropdown filters, more under "More filters", and
  compact posts whose extra labels fold under "Details") and *Breakdowns* (collapsible
  sections; clicking a bar filters the posts and opens them).
- **Breakdowns, each one a filter:** content type, what the row is, platform,
  use-case stage, drop reason, group, the industry words and AI terms that matched,
  flags, month posted, and the search or watch list that found it. Plus a text search
  and four orders (newest, oldest, most engaged, newest found). *Most engaged* adds up
  each platform's own counts, views included, so on a mixed list it mostly means X
  (the page says so); filter to one platform for a fair order. The filters live in
  the address, so a filtered view can be shared.
- **What a row is** is not stored; it is read from each platform's own id and link:
  Reddit `t3_` post / `t1_` comment; GitHub issue, pull request or discussion by its
  link; a Hacker News item with a title is a story, without one a comment; dev.to and
  feeds are articles. **X and Bluesky replies are not told apart from posts**, since
  nothing stored says which is which. On 2026-11-24, of the 7,693 stored items, all
  1,341 Reddit items were posts, all 792 GitHub items issues, and 71 of 540 Hacker News
  items comments.

---

## 5. Storage

Migration `contract/migrations/20261120T1000_industry_ai.sql`, mirrored in
`contract/tables.sql`. Every column is declared in `contract/column_states.yaml`.

- **`iai_item`:** one row per harvested root post or article.
  - Identity, text and engagement: id, platform, url, title, body, created_at,
    author_id, lang, engagement.
  - What found it: link, domain_hints, query_keys.
  - The verdict: verdict, drop_stage, drop_reason, flags.
  - The labels: domains, groups, content_type, matched_pattern, stage_guess.
  - What matched: matched_terms (`{domain: {"terms": [...], "groups": {group:
    [...]}}}`) and ai_terms.
  - Dedupe: canonical_of, share_count, canonical_url.
  - pipeline_version.
  - text_cleared_at: when text retention emptied title and body (below).
- **`iai_run`:** one row per run (harvest or relabel), holding status, requests per
  platform, RapidAPI quota, per-query yields and the counts.

**Text retention** (`retention:` in the contract; anooj, 2026-11-24; migration
`20261124T1200_iai_text_retention.sql`). **A row is never deleted; its text is.**
- **Why rows stay:** the page's "Filtered out" counts are counted from dropped rows
  (rule 4), and the filters are not measured yet (rule 8). Deleting on labelling
  would make a wrong drop unrecoverable.
- **Whose text is cleared,** `clear_text_after_days` (30) after the post was first
  stored:
  - every **dropped** row: spam, sign-up ads, hiring, sponsored, and dedupe copies;
  - **kept** rows in a `kept_domains` domain (Personal: people's own debts, diet,
    parenting, relationships), even when also filed under another domain.
- **What clearing does:** each run, after labelling, `store.clear_text` empties title
  and body and stamps `text_cleared_at`. The row, its verdict, labels, flags and
  counts stay, and the page is unchanged.
- **A cleared row is not re-labelled.** Every run re-labels the collection, and empty
  text would be re-judged ("no AI term"), shifting the drop counts. So
  `store.load_items` leaves cleared rows out, and they keep the labels their text
  earned. The cost: a rule changed later does not reach them, and a new copy of a
  cleared post is not folded into it.
- **30 days** covers the first-run review and the §7 hand-check, which read samples.
- **Raw pages are not kept in the shared database** (#656 review; anooj, 2026-11-24).
  A harvested search page carries the full text of every post it returned, and the
  shared raw store (`raw_blob`) keeps pages for good, so clearing `iai_item` alone
  would leave the same words behind. This lane's raw store is **local only**
  (`scripts/run_industry_ai.py` `raw_store`, `remote=None`, whatever
  `RAW_STORE_REMOTE` says): on a GitHub runner the pages go when the run ends.
  Nothing reads them, since every run re-labels from `iai_item`. The cost: no
  re-sieve from the original pages, and `discovery_ref` names a page nobody can fetch.
- **Personal posts lose their words after 30 days,** so a post or guide drafted from
  Personal uses must quote them within that window.
- **The run log's stage counts cover rows with their text only.** Cleared rows are not
  loaded, so those counts shrink as rows age, while the page counts every row.

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
- **Two switches:**
  - `run.enabled` in the contract: `false` refuses a harvest, while `--plan`,
    `--dry-run` and `--relabel` still work;
  - `INDUSTRY_AI_ENABLED`, the repository variable for the scheduled workflow.
- **Which domains run** is set in the contract (`active`). `--domains` narrows within
  the active ones and refuses an inactive one.
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

   **Sample Governance on its own:** "AI governance" is common in vendor marketing.
4. **Tune** the contract, then run `--relabel` (no requests) and re-check.

---

## 8. Known risks

| Risk | Handling |
|---|---|
| "prompt engineering" in Engineering | *Software & AI* only, never *Physical* (#645) |
| "AI governance" vendor marketing in Governance | sampled on its own in §7 |
| busy keywords crowd out quiet ones in a clubbed X query | per-keyword counts from `matched_terms` |
| airline "pilots" read as pilot programmes | the pilot pattern needs a programme context |
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
2. **Broad industry terms:** "agency/agencies", "council/councils", "engineers" and
   "simulation" became `ambiguous_terms` in #644. "booking", "reservations", "tax" and
   "payments" are still plain terms and are candidates too.
3. **Type patterns.**
   - "launched", "introducing" and "meet" over-count `tool_or_product`.
   - The `use_case` phrasings are narrow.
4. **Hacker News items are often a title only,** so they are judged on the headline.
   Hacker News **comments** carry much of the first-hand work: in a 2026-11-12 sample
   of board entries, 16 of 29 met the bar of first-hand plus concrete work plus a
   named model. The comments phase, or the observer arm, should add Hacker News
   comment search.
5. **Retention.** `iai_item.body` stores post text, Reddit's included, in the shared
   database. It is never shown, but the main pipeline's Reddit data-retention
   question applies here too.

**From the #645 review** (the umbrellas' contract, read 2026-11-20; the team's to tune):

6. **Terms that pass the AI test by themselves. Fixed in #646 for Leaders & Founders.**
   - **The problem:** "AI adoption", "AI strategy", "AI transformation" and "AI
     implementation" contain "AI", so a post naming one passed both sieve checks with
     one phrase.
   - **The fix:** they are now `ambiguous_terms`, counted only with a leaders word
     nearby (founder, startup, CEO, CTO, our team, our company, board, leadership), and
     no longer searched on their own.
   - **The recount:** they were also strong by construction in the evidence test, so
     the domain choice was recounted without them (§1).
   - **A test now pins this:** no active domain has an AI term as a domain term.
   - **Still open:** Governance's AI-policy group has the same shape. Fix it before
     Governance is switched on.
7. **Terms that name the AI capability, not the work. Fixed in #646.** Design &
   Creative's "image generation" and "image upscaling" are now `ambiguous_terms`,
   counted only with a design word nearby (designer, client, brand, studio, agency,
   our team), and no longer searched on their own.
8. **Broad phrases in the active five:** "blog posts", "landing pages", "LinkedIn
   posts", "product launches", "small business", "fundraising", "cost cutting",
   "pricing strategy", "product reviews".
9. **The X AI group's bare `agent`: fixed in #646.** It also matched travel,
   real-estate and support agents. The group is now `(AI OR ChatGPT OR Claude OR LLM)`
   in all 93 X queries.
10. **Governance's domain-level terms** (government, public sector, courts and others)
    sit in no group, so its group counts would be incomplete. Move them into its
    groups before Governance is switched on.
11. **Quota.**
    - **X:** since #646 the cap is 110, for the active five's 21 queries × 5 pages
      (105 requests), so a new X query is capped until the cap rises.
    - **Per run:** a weekly run spends up to 110 X and 40 Reddit requests from the
      RapidAPI quota the model fetches share.
    - **The first dry run** (2026-11-20, on #646's contract) used 105 X and 35 Reddit.
      Its counts are on #646.

**From the #646 review** (Personal & Everyday Life, active since #646; the team's to
tune):

12. **"self-learning" is also an AI phrase.** "self-learning algorithm / agents / AI"
    are common in AI research and tool news. A post like that names an AI term too, so
    it would count as Personal. Make it ambiguous with a learner's context (learn,
    course, study, skill, language, myself), or exclude
    `\bself-learning (AI|model|system|agent|algorithm)s?\b` in **Personal's own**
    `exclude_phrases`, not `global_exclude_phrases`: a domain's exclusions only remove
    text before that domain's terms are matched, while the global ones also apply
    before AI terms are found, so there it would remove "AI" from "self-learning AI"
    for every domain (anooj, #648 review).
13. **"mental health" and "health questions" bring the most sensitive posts in the
    collection.** They reach six platforms: "mental health" is Personal's first search
    on Reddit, Hacker News, dev.to, Bluesky and GitHub (`mental health llm`), and both
    keywords are in one of its grouped X queries. They bring people's own accounts of
    using chatbots for therapy, and news about AI and mental-health harms. The page
    shows counts only, but `iai_item.body` stores that text in the shared database, so
    point 5's retention question is most pressing here.

    **Decided for the test run** (anooj, 2026-11-20): both keywords and their queries
    are removed from Personal, and its X groups are rebuilt so each still clubs 5 or
    more keywords (in the observer PR). **Before they come back:** (a) no stored `body`
    for Personal items beyond what `--relabel` needs, or (b) a retention limit for the
    lane.
14. **A failed search must not read as "found nothing".** In the first dry run
    (2026-11-20), GitHub's 9 searches (401, an invalid local token) and 4 of dev.to's
    14 (429, rate limited) showed as `ok` with 0 items, because the runners read no
    failure from the adapters. **Fixed in #648:** `harvest.failure_of` reads each adapter's record
    (`http_errors`, `rate_limited`, `empty_response`), and such a search is marked
    `error` with the reason, keeping any items the pages that answered gave. A real
    zero result (the site answered, nothing matched) stays `ok` (rule 4).

---

## 11. Open points

- **Governance scope: decided** (anooj, #644 review). It covers the public sector's
  use of AI **and** AI policy and governance practice, as two groups since #645.
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

- **Run the migration on the shared database straight after merge, in the order
  agreed on #644** (`python -m collect.cli db migrate`), and announce it.
  - `db migrate` applies **every** pending migration. #640's content-workspace
    migration (`20261119T1200`) was deliberately left unapplied, and it needs
    `python -m judge.content_workspace seed --development-write` straight after.
  - So either both run together with that seed, announced on both PRs, or this one
    waits.
- **Create the lane's summary issue and set the repository variables:**
  - `INDUSTRY_AI_ISSUE`: that issue's number. **Done 2026-11-24: #657**;
  - `INDUSTRY_AI_ENABLED`: **leave unset (off)** until the tuning below is done.
- **Do NOT set `RAW_STORE_REMOTE=postgres` for this lane** (#656). Its raw search
  pages carry every post's full text and would stay in `raw_blob` for good;
  `scripts/run_industry_ai.py` builds its store with `remote=None` whatever the
  environment says. (This line used to say the opposite.)
- **Both agents in one hand-started run:** the workflow's `watch` box adds the
  observer's watch lists (`--watch`) without switching them on for the schedule.
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
