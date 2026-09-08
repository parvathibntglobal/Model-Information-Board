# Five new platform sources, and the `contract/` lines they need

**Proposal, 2026-09-07. Nothing in `contract/` has been changed.**

The adapters are built and have run: arXiv, dev.to, Hacker News and Hugging
Face all fetched, stored and wrote `document` rows end to end against a
disposable local database. X is built to the credential and refuses there.

What they cannot do is run against anything shared, because five things are
missing from `contract/` and every one of them is a decision rather than an
implementation:

```
contract/sources.yaml        5 terms_rulings + 5 source rows
contract/column_states.yaml  document.lang: reserved -> write_only
```

The paste-ready YAML is in **`docs/proposals/new-platform-sources.draft.yaml`**,
marked `reviewed_by: UNRATIFIED-DRAFT` in every ruling. This document is what
each block is asking you to agree to.

---

## 1 · Why this is a proposal and not a commit

Three reasons, in descending order of how much they should worry you.

**The robots finding is a question I cannot answer alone.** Measured
2026-09-07 (`docs/measurements/new-platform-robots-2026-09-07.json`):

| host we actually call | robots.txt | the path we use |
|---|---|---|
| `export.arxiv.org` | 200, `Disallow: /` | **disallowed** |
| `dev.to` | 200, no matching rule | allowed |
| `hn.algolia.com` | **404** — no rules at all | the 404 caveat applies |
| `huggingface.co` | 200, `Allow: /` | allowed |
| `twitter241.p.rapidapi.com` | 200, `Disallow: /` | **disallowed** |

Also read, for hosts we do *not* call on these routes: `arxiv.org/abs` (200,
allowed, `Crawl-delay: 15`), `news.ycombinator.com` (200, `Crawl-delay: 30`),
`api.x.com` (200, `Disallow: /` — X's own API, which the X adapter does not
use).

Two of the five hosts disallow crawling themselves. **This is not new for this
project** — it is already true of both hosts we harvest Reddit through:

```
oauth.reddit.com/robots.txt              200, Disallow: /
reddit34.p.rapidapi.com/robots.txt       200, Disallow: /
api.github.com/robots.txt                404, no rules
```

and the existing rulings resolve it the same way: robots.txt is the
crawler-exclusion protocol, an API is a documented programmatic interface, and
`github-api-terms` says so out loud by quoting GitHub's own *"scraping does not
refer to the collection of information through our API"*. Four of the five
draft rulings therefore turn on `access_path: [api]`, matching `github`; the
fifth turns on `access_path: [rapidapi-reseller]`, matching `reddit`, because
that is what it is.

**That is a precedent, not a proof, and it is the single thing in the draft
most worth disagreeing with.** If the answer is that robots governs a
documented API path, arXiv is out — and X is in the same position Reddit is
already in, which is a bigger question than this proposal.

**No terms document has been read, for any of the five.** Each ruling records
which documents need reading and states the deferral in the same words
`blog-class-a-self-hosted` uses for the nine feeds: *"NO TERMS PAGE HAS BEEN
READ."* That is the honest state and it is written into the ruling rather than
left as an absence somebody later reads as a clearance.

**`base_trust` is a weight, and all five values are guesses.** They come with
the argument rather than instead of it, and the argument is the part to
disagree with — the reasoning is in the draft file's PLATFORM ROWS header. The
proposed values: `hackernews 0.85`, `huggingface 0.80`, `devto 0.75`,
`arxiv 0.70`, `x 0.60`.

---

## 2 · What each adapter is, in one line each

The document unit is the decision that decides what the corpus can answer, so
it leads.

| Source | Document unit | Discovery | `text_ref` names |
|---|---|---|---|
| `arxiv` | one paper's **abstract entry, versioned** (`2609.03450v1`) | Atom `search_query` | a single-entry `id_list` feed — a second request, to avoid hashing bytes we assembled |
| `devto` | the **article** | `/api/articles/search?q=` | `/api/articles/{id}` — a search hit carries no body |
| `hackernews` | the **comment inside a subject thread** | Algolia `tags=comment` | `/items/{objectID}` — plus the story, written as the thread root |
| `huggingface` | the **comment inside a discussion** | repo search → per-repo discussions | the discussion payload for the root; the re-serialised event for a comment |
| `x` | the **post** | a RapidAPI provider's search, `type=Top`/`Latest` | the re-serialised post object — the route is metered and shares Reddit's subscription |

Two rulings inside those that are worth your attention:

**Hacker News is the comment, not the story.** The measurement is already in
this repository: `scripts/fetch_hackernews_articles.py` recorded a thread that
was *a bare GitHub link at 678 points whose evidence — a quoted price, the
pricing URL, an expiry date, a routing claim — was entirely in its comments.* A
story-only harvest builds a corpus of links people submitted and calls it a
corpus of what engineers report. Story rows are written as **subject anchors**
and counted separately from comments in every report, because nothing sieved
them and the query never returned them.

**Two of the five re-serialise the per-document payload, and three do not.**
The ruling wants `content_hash` to be the hash of the bytes the platform gave
us. Hugging Face publishes no per-comment endpoint, so the bytes for one
comment do not exist as a response; X goes through a metered gateway whose
allowance is shared with Reddit and unverified, so a second request per post
doubles a budget nobody can size. Both use `json.dumps(record,
sort_keys=True)`, which is exactly what `github.fetch_comments` already does
and for the same reason. arXiv spends the second request instead. **The
difference is per-platform and deliberate**, and each module says which it does
and why, so a reader comparing two of them sees a decision rather than two
people who never spoke.

---

## 3 · The test run

`py -3 scripts/smoke_new_adapters.py --query "Fable 5.1" --max 2`, against the
disposable local Postgres. Full output:
`docs/measurements/new-adapter-smoke-2026-09-07.json`.

```
platform       reqs  cands  surf  stored  ins  refs  prose  outcome
arxiv             2      1     1       1    1     1      1  ok
devto             3     30    12       2    2     2      2  ok
hackernews        5     50    49       4    4     4      4  ok
huggingface       1      0     0       0    0     0      0  ok
x                 0      0     0       0    0     0      0  refused
```

`surf` is how many candidates contain the surface as an exact substring —
carried beside `cands` because retrieval on two of these platforms is looser
than a mention (Algolia prefix-matches every token; dev.to's search matches body
text), so a candidate count quoted as a mention count would be rule 7 exactly.

Four `harvest_run` rows opened and closed with `outcome = 'ok'`; all 7 documents
carry `retrieval_provenance = 'run_recorded'` with the id on the row; 7 of 7
`text_ref`s resolve and 0 hash mismatches.

**The gate was not bypassed.** Every harvester was built through
`harvester_for_source()`, so `assert_terms_reviewed` ran with the draft rulings
and this run's live observations — and it did its job: X was **refused**, with

> `x: ruling x-via-rapidapi-scraper requires scraper_provider to be one of ['twitter241']; observed None.`

⚠ **And note which refusal that is.** `RAPIDAPI_KEY` is already set in this
machine's `.env` — it is the Reddit key, shared — so `XCredentialMissing` is
*not* what stops X here. What stops it is `SCRAPER_PROVIDER` being unset, plus
the ruling being an unratified draft. The credential stop is real for a fresh
checkout and is not the operative one on a machine that already harvests
Reddit, and saying otherwise would overstate the guard.

The corollary is worth stating plainly: **set `SCRAPER_PROVIDER=twitter241` in
`.env` and this draft ruling would let an X sweep run**, because the gate checks
structure and cannot know a ruling is unread. That is precisely why the draft
lives in `docs/proposals/` and not in `contract/`.

**Hugging Face returned nothing, and it is the platform, not the adapter.** The
Hub has no full-text search over discussions, so discovery is repo-scoped:
`Fable 5.1` matched 0 repos, which is a *structural* absence — Anthropic
publishes no weights there. A control run against `DeepSeek-R1` matched 20
repos, walked 2, listed 100 discussions and stored 8 documents with 8 of 8
`text_ref`s resolving
(`docs/measurements/new-adapter-smoke-hf-control-2026-09-07.json`). The adapter
works; the model has no surface on that platform.

**The control run also found a defect in my own adapter**, which is the reason
it was worth running: one comment event carried `data.latest.raw` empty with
`hidden` false, was written `status='kept'`, and then refused at
`huggingface_prose` — a row that looks like evidence and has none. Fixed:
`no_comment_text` is now a shared `filter_reasons` string across Hacker News
and Hugging Face, one constant, so two platforms reaching the same condition
cannot spell it two ways.

---

## 4 · What you are being asked to agree to

### 4.1 `contract/sources.yaml` — five rulings and five source rows

Copy from `docs/proposals/new-platform-sources.draft.yaml`. Each ruling names
the terms documents to read; replace `reviewed_by: UNRATIFIED-DRAFT` when they
have been. The four questions I could not answer:

1. **Does robots.txt govern a documented API path?** §1. Decides arXiv and X.
2. **On Hacker News, whose terms govern — Y Combinator's or Algolia's?** The
   index is operated by Algolia on HN's behalf, so there are two parties. This
   is the Medium-shaped question `sources.yaml` already answers for blogs (*the
   platform is the party speaking, not the publisher*) and it has not been
   answered here.
3. **Is a 404 robots.txt on `hn.algolia.com` acceptable?** The file's own 404
   CAVEAT says absence of a crawl policy is not consent.
4. **Is a reseller route acceptable for X, on the same basis Reddit's is?**
   The route IS a reseller — `SCRAPER_PROVIDER=twitter241` on RapidAPI, the
   provider this project's own X sweep already used — so it inherits the exact
   condition `reddit-via-rapidapi` records as unresolved: *credentials issued
   by the platform, OAuth identity unmasked; a reseller route does not satisfy
   this regardless of use.* The draft records it the same way rather than
   clearing it, and it should be escalated **with** Reddit's rather than
   separately: it is one question about one gateway. Note also that
   `RAPIDAPI_KEY` is shared, so an X sweep spends the Reddit quota.

### 4.2 The X route, and the two variables it reads

Corrected 2026-09-07 after review: the first version of this adapter was built
against **X's own API v2 with a bearer token**, which was wrong. It is now a
RapidAPI scraper provider, the same shape and the same gateway as Reddit:

```
SCRAPER_PROVIDER=twitter241     ->  X-RapidAPI-Host: twitter241.p.rapidapi.com
RAPIDAPI_KEY=…                  ->  X-RapidAPI-Key
```

`collect/adapters/x.py:host_for` derives the host from the provider name and is
the only place a host is made, so moving to a different RapidAPI provider is an
environment change rather than a code change. It refuses rather than defaulting
when the variable is unset — an unconfigured process must not quietly call one
particular vendor — and refuses a full host pasted into the provider slot,
because `RAPIDAPI_HOST` already suffered one bad paste in this project.

**A provider swap is not free, and the ruling is where that is caught.**
`observe_x_use()` reports `scraper_provider` on every run and the draft ruling
pins `[twitter241]`, so swapping providers **refuses at the gate**. That is
deliberate: a different provider fronts a different response envelope, and the
failure mode without the pin is parsing nothing and reporting the platform as
quiet — rule 4, one stage earlier.

`XCredentialMissing` names **`RAPIDAPI_KEY`** explicitly, plus
`SCRAPER_PROVIDER`, and says the credential is the same one the Reddit path
uses. A generic "credential missing" would send somebody to open an X developer
account, which is the wrong file and the wrong afternoon.

### 4.3 `contract/column_states.yaml` — one line

```yaml
    lang: {state: write_only, reviewed: true, why: "…"}   # was: reserved
```

`document.lang` is NULL on 6,502 of 6,502 rows, which is why
`triage.gates.wrong_language` reports UNAVAILABLE for the whole corpus. **Two
of the five new platforms declare a language per document** — dev.to's
`language` and X's `lang` — and that is the platform's own field, not an
inference, so rule 8 makes it a recorded field.

The adapters parse and carry it (`DevtoHit.language`, `XPost.lang`,
`DocumentDraft.lang`) and `WriteReport.lang_declared_by_platform` counts what
would land: 2 of 2 dev.to documents in the smoke run. **The writer does not
store it**, because adding it moved the discovered state to `write_only` and
`tests/test_column_states.py` failed by name — the guard working, not an
obstacle. Enabling it is that YAML line plus adding `lang` to `_INSERT` and to
`as_row`, and the two belong in one PR.

It does not make the gate runnable — no detector is installed — but the input
cannot be back-filled later without re-reading every payload.

---

## 5 · What is deliberately not proposed

- **No change to the three existing document writers.** Folding them into
  `collect/adapters/documents.py` would refactor the only paths that have ever
  written a real corpus, for a benefit that arrives on the next column. The
  duplication is now 3-plus-1 rather than 8, and it is visible from the new
  module's docstring.
- **No triage change.** Assessed separately in
  `docs/triage-assessment-2026-09-07.md`, recommendations only. The one that
  touches these platforms — the entity gate resolving **11 of 511** Hacker News
  thread comments — is a ruling about whether triage is per-document or
  per-thread, and it is yours.
- **No `source` rows on the shared database.** `scripts/smoke_new_adapters.py`
  refuses any host that is not localhost, read from the open connection rather
  than from the DSN. A seeded `source` row is what the terms gate consults to
  decide whether we may fetch, so an unratified one on a shared database would
  read as a decision to every later run — item 20's shape exactly.
- **`scripts/fetch_model.py`'s Reddit arm still stores prose as the payload**
  (`store.put(post.sieve_text)` at line ~284), which is the artifact-choice
  defect `docs/engineer-1/ruling-what-content-hash-identifies.md` was written
  to close. Noticed while reading for the new adapters, not fixed here: it is a
  live script with its own callers, and repairing it means deciding what to do
  with the rows it has already written.
