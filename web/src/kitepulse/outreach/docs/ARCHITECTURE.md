# Kite Pulse Outreach — Architecture

Written 2026-11-06 from `Outward Marketing Strategy.md` (4 Nov 2026).
**Status: design only. Nothing here is built.**

This is the technical design for the strategy's six agents: what runs where,
what is stored, which steps call a model, which steps are plain code, and what
a person decides. The strategy says *what* and *why*. This document says
*how*.

---

## 1. Scope and the one rule

The system **finds** public threads where people ask about problems Kite Pulse
solves, **shortlists** them, **drafts** a disclosed, helpful reply, and
**shows** that draft to a team member. The team member edits it, approves it
and **posts it by hand from their own account**.

> **No component holds a posting credential.** The system only reads from
> forums. Posting is a person copying text into a browser. This is a property
> of the design, not a setting: if no write token exists, no bug and no
> prompt injection can post.

Not in scope: Kite Pulse's product code, the SEO site build
(`web/src/kitepulse/docs/ARCHITECTURE.md`), and MIB's evidence pipeline.
Outreach shares the app's shell, sign-in, admin and spend ledger with MIB. It
shares **no evidence tables**: it never writes `document`, `claim` or
`thread_context`, and MIB never reads outreach tables.

---

## 2. Constraints this design inherits

| # | Constraint | Source | What it means here |
|---|---|---|---|
| C1 | **A model may propose, never decide.** A new model-calling stage needs a recorded agreement. | `CLAUDE.md` rule 2 | Outreach is a new caller (stage `outreach`). It needs the same agreement the blog generator (#508) got **before the Shortlister or Reply Writer runs**. Phase 1 (section 9) needs no model and can start without it. |
| C2 | Every model call is a `spend_ledger` row at OpenRouter's reported cost. | rule 2, `judge/spend_ledger.py` | Add `STAGE_OUTREACH` to `RECORDED_STAGES`, with its own daily cap, outside `EXTRACTION_DAILY_BUDGET_USD`. |
| C3 | An unmeasured check ships as a weight, not a gate. | rule 8 | The model's relevance label **orders** the review list. It does not remove threads from it (section 5.2). |
| C4 | Official APIs and public feeds only; identifying User-Agent. | Stack decisions | Each source uses its documented API. No scraping, no logged-in browsing, no search-engine scraping. |
| C5 | Config in versioned YAML, not code. | rule 5 | Queries, community allowlist, approved claims, pace limits are YAML files in the outreach package (section 4), **not** in `contract/` (KP config stays out of `contract/`, SEO architecture §3.3). |
| C6 | Migrations live in `contract/migrations/` and get two eyes. | `CLAUDE.md` | The outreach tables (section 6) arrive as one reviewed migration PR whose body says who runs it and when. |
| C7 | Product claims come from MSoT Section 1 only. | SEO architecture §2.3 | The Reply Writer's approved-claims list is built from MSoT Section 1. The MSoT's "Website corrections" become refused phrasings. |
| C8 | Disclosure is mandatory. | Strategy, "ground rule"; FTC / ASCI | A code check refuses any draft without a disclosure line. The reviewer cannot approve it without one either (section 5.4). |

---

## 3. System overview

```
                       config/*.yaml  (queries · communities · claims · pace)
                                 │
   ┌─────────────────────────────┼─────────────────────────────────────────┐
   │  BACKEND (Python, cron)     ▼                                         │
   │                                                                       │
   │  1 FINDER ──────► kp_outreach_thread   (status: found)                │
   │  plain code        one row per thread, deduped on (source, ext_id)    │
   │                         │                                             │
   │                         ▼                                             │
   │  2 SHORTLISTER                                                        │
   │    a. code filters  ── age · open · allowlisted community ·           │
   │                        not already answered by us · pace cap          │
   │    b. model         ── PROPOSES: problem label, relevance (H/M/L),     │
   │       (DeepSeek V4     best article slug, one-line reason             │
   │        Flash)                                                         │
   │    c. code          ── verifies slug exists & is public; orders list  │
   │                         │                    (status: shortlisted)    │
   │                         ▼                                             │
   │  3 REPLY WRITER                                                       │
   │    a. model         ── PROPOSES a draft                               │
   │    b. REPLY CHECK   ── code: disclosure · ≤1 product mention ·        │
   │       (code only)      claims ⊂ approved list · links ⊂ allowed ·     │
   │                        no refused phrasing · length                   │
   │                      fail → retry once, then status: draft_refused    │
   │                         │                    (status: drafted)        │
   └─────────────────────────┼─────────────────────────────────────────────┘
                             ▼
   ┌───────────────────────────────────────────────────────────────────────┐
   │  4 REVIEW SCREEN   Admin → Kite Pulse Outreach                        │
   │    thread · draft · edit box · Approve / Skip                         │
   │    edited text re-runs the REPLY CHECK before Approve is enabled      │
   │                         │                                             │
   │    PERSON copies the reply, posts it from their own account,          │
   │    pastes the posted URL back  ──►  kp_outreach_reply (posted)        │
   └─────────────────────────┼─────────────────────────────────────────────┘
                             ▼
   5 ARTICLE SHARER  (same draft → check → review path, different source)
   6 REPORTER        plain code: re-reads posted replies via the same APIs,
                     reads UTM clicks from site analytics, weekly summary
```

Every arrow into the review screen is a **proposal**. The only transitions to
`approved` and `posted` are made by a signed-in person.

---

## 4. Where the code lives

Everything lives under `web/src/kitepulse/outreach/`, **one folder per
platform**, each run as a script by its path (the way
`web/src/kitepulse/shared/import_sheet.py` is).

```
web/src/kitepulse/outreach/
├── docs/                             strategy, this document
├── hackernews/                       BUILT 2026-11-06 (phase 1 Finder)
│   ├── find.py                       py -3.12 web/src/kitepulse/outreach/hackernews/find.py
│   ├── finder.py                     search → deduplicate → filter
│   ├── client.py                     GET-only calls to Algolia HN Search
│   ├── parse.py                      API hit → Thread
│   ├── thread.py                     the Thread record, statuses, drop reasons
│   ├── filters.py                    the code filters (5.2a)
│   ├── config.py                     loads config/*.yaml, no defaults in code
│   └── config/
│       ├── queries.yaml              search phrases per problem
│       ├── communities.yaml          vendor-reply policy and a link to the rules
│       └── pace.yaml                 max thread age, team accounts
├── reddit/  devto/  github/  discourse/  x/      to build, same shape
│
│   to build in phase 2 and 3, location to settle then (see below):
├── shortlist, writer, checks         model proposal, REPLY CHECK (5.2b–5.4)
├── articles, sharer, reporter        article index, Article Sharer, Reporter
├── llm                               OpenRouter call → spend_ledger stage `outreach`
├── api                               FastAPI router, mounted under /admin/outreach
├── OutreachPanel.jsx, outreach.css   Admin → Kite Pulse Outreach (review screen)
└── claims.yaml, disclosure.yaml      approved product sentences, disclosure lines

var/outreach/                         Finder output today (gitignored)
contract/migrations/<ts>_kp_outreach.sql      the tables (two eyes, C6)
tests/test_kp_outreach_*.py                   checks, filters, no-posting guard
```

**Why not `collect/`.** `collect/adapters/` already search Reddit, HN, dev.to,
GitHub Discussions, Discourse and X, but every adapter's job ends in a
`document` row for MIB's evidence corpus. Outreach must not write there
(section 1). The `hackernews/` folder imports nothing from `collect/` except
`collect.config` for the User-Agent, and a test enforces that (section 10).

**What this layout defers.** When a second platform is built, the parts every
platform shares (`thread.py`, `filters.py`, `config.py`) move to a shared
folder (e.g. `outreach/common/`) rather than being copied. And the phase-2
API router must be importable by `judge/app.py`, which runs from the
repository root; a script folder under `web/src/` is not on that path. Decide
how (a path entry, or moving the backend to the root) when phase 2 starts.

**Hooks outside these folders** (keep to three, as the SEO site did):

| File | Change |
|---|---|
| `judge/app.py` | `app.include_router(outreach_router, prefix="/admin/outreach")` behind the existing admin auth |
| `judge/spend_ledger.py` | `STAGE_OUTREACH = "outreach"`, added to `RECORDED_STAGES` and `STAGE_LABELS` |
| `web/src/routes/Admin.jsx` | "Projects" group: Kite Pulse Outreach |

---

## 5. Components

### 5.1 Finder (plain code)

| | |
|---|---|
| **Runs** | Cron, every 4 hours (`python -m kitepulse_outreach find`) |
| **Input** | `queries.yaml`: each problem has phrases per source, e.g. problem `claude-limits` → `"hit my claude limit"`, `"claude code usage limit"`, `"5 hour limit claude"` |
| **Does** | Calls each source's search API for posts from the last 7 days; normalises to `Thread {source, ext_id, community, url, title, body, author, created_at, is_open, reply_count}`; upserts on `(source, ext_id)` |
| **Output** | `kp_outreach_thread` rows, `status='found'`, `matched_problem`, `matched_phrase` |
| **Model** | None |

Source notes (each is an open item in section 11 until confirmed):

| Source | API | Note |
|---|---|---|
| Reddit | Data API (OAuth, read scope only) | Commercial use needs Reddit's approval. Read-only app; no `submit` scope requested. |
| Hacker News | Algolia HN Search | Free, no key |
| dev.to | Forem API | Free |
| GitHub Discussions | GraphQL API | Token with read-only public scope |
| Developer forums | Discourse `/search.json` | Per forum; listed in `communities.yaml` |
| X | X API v2 search | Paid tier. Leave off until the cost is agreed. |

### 5.2 Shortlister

Three steps, in this order. **The model never sees a thread that code has
already ruled out, and code makes every keep/drop decision.**

**a. Code filters (gates; each one is a rule a person wrote, not a measured
classifier):**

| Filter | Rule | Drop reason stored |
|---|---|---|
| Age | `created_at` within `pace.yaml: max_thread_age_days` (default proposed: 7) | `too_old` |
| Open | Not locked/archived/closed per the API | `closed` |
| Community | `community` is in `communities.yaml` with `vendor_replies: allowed` | `community_not_allowed` |
| Already ours | No `kp_outreach_reply` posted in this thread; no team account (from `pace.yaml: team_accounts`) among its commenters | `already_answered` |
| Pace | The community's weekly cap not reached | `pace_cap` |

Dropped rows stay in the table with the reason (rule 6: an absence we caused
must not read as one we found). The review screen has a "Dropped" tab.

**b. Model proposal (DeepSeek V4 Flash, one call per thread that passed a):**
a tool-call schema with exactly these fields:

```
problem        one of the problem keys in queries.yaml, or "none"
relevance      high | medium | low
article_slug   one slug from the article index, or null
reason         ≤ 30 words: why this article answers this thread
```

The thread text is untrusted input. It goes in a delimited user message; the
model's only output channel is the schema above.

**c. Code verifies and orders:**

- `article_slug` must exist in the article index (5.3). An unknown slug
  becomes `null` and is flagged; it is never "corrected" to a near match
  (rule 12).
- Order within the review list: `high` before `medium` before `low`, then
  newest first. **`low` and `problem: none` are shown, collapsed, not
  dropped** (C3). If after a measured period reviewers skip, say, every `low`
  thread, that measurement is the evidence for turning it into a gate.

### 5.3 Article index (plain code)

The set of pages a reply may link to. Built from `web/src/kitepulse/shared/data/sheet.json`
(the Page Map) and the prototype registry in `web/src/kitepulse/shared/site.js`.

**A page is linkable only when it is live on the public Kite Pulse domain.**
Today every page is an internal preview behind sign-in (SEO architecture
phase 3 not done). So until the public site is live, the index is empty, and
the Shortlister proposes `article_slug: null` — the reply helps without a link.
That is a valid phase-1 and phase-2 state, not a failure.

Each index entry: `slug`, `public_url`, `title`, `problems` (which
`queries.yaml` problem keys it answers), `summary` (from the sheet).

### 5.4 Reply Writer and the REPLY CHECK

**a. Model proposal (DeepSeek V4 Flash).** Input: the thread, the chosen
article's title, URL and summary, the approved claims relevant to the
problem, the community's rules note, and the reviewer's chosen disclosure line.
Output schema: `body` (the reply text, markdown).

**b. REPLY CHECK (`checks.py`, no model).** Every rule is a pure function of
the text and the config. It runs on the model's draft **and again on the
reviewer's edited text**; Approve stays disabled until it passes.

| Check | Rule | Example refusal |
|---|---|---|
| Disclosure | Contains one of the lines in `disclosure.yaml` verbatim | `no_disclosure` |
| One mention | "Kite Pulse" (case-insensitive, any spacing/hyphen) appears ≤ 2 times: once in the disclosure, once at most in the body | `too_many_mentions: 3` |
| Claims | Every sentence that mentions Kite Pulse, other than the disclosure, matches a sentence in `claims.yaml: approved` (exact after whitespace normalisation) | `unapproved_claim: "Kite Pulse tracks cost for every tool"` |
| Refused phrasing | No phrase from `claims.yaml: refused` (from the MSoT's "Website corrections") | `refused_phrase: "Org Overview"` |
| Links | Every URL is either the chosen article's `public_url` (with UTM, 5.6) or a domain in `communities.yaml: allowed_link_domains` for that community; at most one Kite Pulse link | `link_not_allowed` |
| Numbers | Every number in digits appears in the thread text, in an approved claim, or in the article summary | `number_not_in_sources: 40%` |
| Length | Within the community's `max_reply_chars` | `too_long` |
| Answers first | The first Kite Pulse mention is not in the first paragraph | `pitch_first` |

The checks stop the drafts that break the ground rule. They **do not** check
that the answer is correct or helpful. That is the reviewer's job, and the
review screen says so (rule 4: a passed check must not read as a verified
answer).

On failure the writer retries once with the refusal reasons in the prompt; a
second failure stores `status='draft_refused'` with the reasons, visible to the
reviewer, who may still write a reply by hand.

### 5.5 Review screen (Admin → Kite Pulse Outreach)

Tabs: **To review** (drafted, ordered per 5.2c) · **Approved, not posted** ·
**Posted** · **Skipped** · **Dropped** · **Report**.

Each item shows: thread title, community, age, a link to the live thread, the
thread text, the model's `problem`/`relevance`/`reason` labelled *"suggested by
the model"*, the chosen article, the draft in an edit box, live REPLY CHECK
results, and the community's rules note.

Actions and what they record:

| Action | Who | Records |
|---|---|---|
| Approve | Signed-in admin | `approved_by`, `approved_at`, final text, check result. Only enabled when the check passes. |
| Copy | — | Copies the final text. The person posts it themselves. |
| Mark posted | The person who posted | `posted_url` (must be a URL inside the same thread on the same source — code-checked), `posted_by_account`, `posted_at` |
| Skip | Signed-in admin | `skip_reason` from a short list (not relevant, already answered, community wouldn't welcome it, draft not salvageable, other + note). These are the measurement for 5.2c and for the model upgrade decision in the strategy. |

Endpoints (`kitepulse_outreach/api.py`, all behind admin auth):

```
GET  /admin/outreach/items?status=drafted
GET  /admin/outreach/items/{id}
POST /admin/outreach/items/{id}/check      body: {text}   → check result
POST /admin/outreach/items/{id}/approve    body: {text}   → re-checks, then records
POST /admin/outreach/items/{id}/posted     body: {url, account}
POST /admin/outreach/items/{id}/skip       body: {reason, note}
GET  /admin/outreach/report?week=2026-W45
```

There is no endpoint that posts to a forum.

### 5.6 Measuring clicks

Each Kite Pulse link in an approved reply carries UTM parameters:
`?utm_source=<source>&utm_medium=community&utm_campaign=outreach&utm_content=<reply_id>`.
Clicks are read from the public site's analytics. **This depends on the public
site existing and having analytics** (SEO architecture phase 3), so until then
the Reporter shows clicks as *"not measurable yet"*, never as 0 (rule 6).

### 5.7 Article Sharer

Same path as the Reply Writer with a different input: a published article
instead of a thread. Draft types: dev.to / Hashnode / Medium cross-post (with a
canonical link to the original), a "Show HN" draft (only when an entry in
`sharer.yaml: releases` names a real release), and a newsletter pitch. Same
REPLY CHECK with type-specific limits; same review screen, own tab. Starts in
phase 3.

### 5.8 Reporter (plain code)

Weekly, Monday 06:00 UTC. For each `posted` reply it re-reads the reply via
the same source API: still visible or removed, score, replies to it. Plus UTM
clicks (5.6), skip reasons, and the most common `matched_problem` values.
Output: the Report tab and one `kp_outreach_report` row per week.

Every figure on the report states its population, e.g. *"12 replies posted
this week by 2 people, in 5 communities"*, not *"12 replies"* (rule 7). A
removed reply is a reported fact, shown prominently: it is the earliest
signal that a community does not welcome us.

---

## 6. Data model

Proposed tables, one migration in `contract/migrations/`. Prefix `kp_` keeps
them visibly apart from MIB's tables.

```sql
kp_outreach_thread
  id               bigserial PK
  source           text NOT NULL          -- reddit | hackernews | devto | github | discourse | x
  ext_id           text NOT NULL
  community        text NOT NULL          -- r/ClaudeAI, a forum host, a repo
  url              text NOT NULL
  title            text
  body             text                   -- as fetched; never published by us
  author           text
  created_at       timestamptz NOT NULL
  fetched_at       timestamptz NOT NULL
  matched_problem  text NOT NULL
  matched_phrase   text NOT NULL
  status           text NOT NULL          -- found | dropped | shortlisted | drafted |
                                          -- draft_refused | approved | posted | skipped
  drop_reason      text
  UNIQUE (source, ext_id)

kp_outreach_proposal                       -- the model's shortlist output, as proposed
  thread_id        FK → kp_outreach_thread
  problem          text, relevance text, article_slug text NULL, reason text
  slug_verified    boolean NOT NULL
  model            text NOT NULL, pipeline_version text NOT NULL, created_at

kp_outreach_draft                          -- every draft, including refused ones
  id, thread_id (or article_slug for sharer drafts), kind text  -- reply | crosspost | show_hn | pitch
  body             text NOT NULL
  check_passed     boolean NOT NULL
  check_failures   jsonb NOT NULL          -- [] when passed
  model            text NULL               -- NULL when a person wrote it
  pipeline_version text NOT NULL, created_at

kp_outreach_reply                          -- what a person approved and posted
  id, draft_id FK, thread_id FK
  final_body       text NOT NULL
  approved_by      text NOT NULL, approved_at timestamptz NOT NULL
  posted_url       text NULL, posted_by_account text NULL, posted_at timestamptz NULL
  skip_reason      text NULL, skip_note text NULL

kp_outreach_observation                    -- Reporter's re-reads
  reply_id FK, observed_at, visible boolean, score int NULL, reply_count int NULL,
  clicks int NULL                          -- NULL = not measurable, never 0

kp_outreach_report
  week text PK, body jsonb NOT NULL, created_at
```

Every column has a named reader (rule 9): the review screen reads thread,
proposal, draft and reply; the Reporter reads reply and observation; the
proposal's `relevance` and the reply's `skip_reason` together are the
measurement that decides whether `relevance` ever becomes a gate.

Retention: `body` of threads that were dropped or skipped is deleted after 30
days (we keep the URL and the reason). We store other people's posts only as
long as we need them to answer.

---

## 7. Models and cost

| Step | Model | Calls |
|---|---|---|
| Finder, filters, checks, Reporter | none | — |
| Shortlister (5.2b) | DeepSeek V4 Flash via OpenRouter | one per thread that passes the code filters |
| Reply Writer (5.4a) | DeepSeek V4 Flash | one per shortlisted thread, plus at most one retry |
| Article Sharer | DeepSeek V4 Flash | one per draft type per article |

- The model ID lives in `config/models.yaml`, so switching the Reply Writer to
  Claude Haiku 5.5 (the strategy's upgrade path) is a config change, compared
  for a week using the skip reasons.
- Every call goes through `llm.py` → OpenRouter → a `spend_ledger` row with
  stage `outreach` at OpenRouter's reported cost, shown in Admin → API usage.
- **Cap:** `OUTREACH_DAILY_BUDGET_USD`, separate from the extraction cap. When
  reached, the run stops and the screen says *"daily outreach budget reached"*;
  unprocessed threads wait, they are not dropped.

**Cost reference, an estimate, not a measurement of this system:** one forum
thread read by DeepSeek V4 Flash cost about $0.002 for a similar but longer
reading task (3 calls on one thread, measured 2026-08-19,
`docs/measurements/extraction-token-counts.md`). If, say, 50 threads a day
passed the code filters and 5 were drafted, that would be roughly
55–60 calls a day, on the order of $0.10/day. Replace this with the measured
`spend_ledger` total after the first week of phase 2.

---

## 8. Schedule

Cron plus the jobs table (stack decision; no workflow engine).

| Job | When | Needs a model |
|---|---|---|
| `find` | every 4 h | no |
| `shortlist` | after each `find` | yes (phase 2+; phase 1 runs filters only) |
| `draft` | after each `shortlist` | yes |
| `daily-list` | 08:00 IST | no — phase 1's emailed/Slack list of shortlisted threads |
| `report` | Monday 06:00 UTC | no |
| `retention` | daily | no |

---

## 9. Rollout, mapped to components

| Phase | Runs | Model calls | Prerequisites |
|---|---|---|---|
| **1. Find** | Finder, code filters, daily list, minimal review screen (thread + Skip/Mark posted, no draft) | **none** | Migration merged and applied; source API access (Reddit approval); `communities.yaml` written by a person who has read each community's rules |
| **2. Draft** | + Shortlister model step, Reply Writer, REPLY CHECK, full review screen | yes | **Rule-2 agreement for stage `outreach`** recorded in `CLAUDE.md`; `claims.yaml` built from MSoT §1 and reviewed by the product owner; spend stage added |
| **3. Share & report** | + Article Sharer, Reporter with clicks | yes | Public Kite Pulse site live with analytics (SEO phase 3); article index non-empty |

Phase 1 is useful on its own and needs no model, no agreement and no public
site. It also produces the first measurement: which communities and problems
the team actually replies to.

---

## 10. Tests that guard the design

| Test | Guards |
|---|---|
| `test_kp_outreach_cannot_post.py` | AST/grep over `kitepulse_outreach/`: no call to any posting endpoint (Reddit `/api/comment`, `/api/submit`, X `POST /2/tweets`, GitHub `addDiscussionComment`, dev.to `POST /articles`), no write-scope OAuth request |
| `test_kp_outreach_does_not_write_evidence.py` | No import of `collect/` writers; no SQL touching `document`, `claim`, `thread_context` |
| `test_kp_outreach_checks.py` | Each REPLY CHECK rule with a passing and a refused example; the edited-text path re-runs the check |
| `test_kp_outreach_filters.py` | Each code filter; dropped rows keep their reason |
| `test_kp_outreach_spend.py` | Every model call writes a `spend_ledger` row with stage `outreach`; the cap stops the run |
| `test_kp_outreach_unknown_slug.py` | An article slug not in the index becomes `null` and flagged, never a near match |

---

## 11. Decisions needed

| # | Decision | Who | Blocks |
|---|---|---|---|
| 1 | Rule-2 agreement for a new model stage `outreach` (propose-only, person approves, code checks, spend recorded) | Both MIB engineers | Phase 2 |
| 2 | Reddit Data API: apply for commercial read access | Product owner | Reddit in phase 1 |
| 3 | X API: pay for search access, or leave X out | Product owner | X source |
| 4 | Who reviews and posts, from which accounts; list them in `pace.yaml: team_accounts` | Product owner | Phase 1 |
| 5 | The first `communities.yaml`: which communities, each checked against its own self-promotion rules | Reviewer(s) | Phase 1 |
| 6 | The approved-claims list (from MSoT §1) and the disclosure wording | Product owner | Phase 2 |
| 7 | `OUTREACH_DAILY_BUDGET_USD` value | Product owner | Phase 2 |
| 8 | Phase-1 daily list delivery: email, Slack, or the admin screen only | Team | Phase 1 |
| 9 | Proposed migration (section 6) reviewed as a `contract/` change | Both MIB engineers | Phase 1 |

---

## 12. Risks

| Risk | Mitigation |
|---|---|
| A reply gets an account banned or the product named as a spammer | No auto-posting (no write credentials); community allowlist; pace caps; disclosure check; removed replies shown first in the report |
| Prompt injection in a thread steers the draft | Thread text is delimited untrusted input; output is schema-only; REPLY CHECK constrains claims, links and mentions; a person reads every draft |
| A draft states a product fact Kite Pulse does not have | Claims check against MSoT §1 sentences; refused phrasings from the MSoT corrections |
| A draft is wrong about the person's actual question | Not checkable by code; the review screen says so; skip reasons measure it |
| Reviewers rubber-stamp | Approve requires the check to pass on the final text; the report shows approvals per reviewer and edit rate (draft vs final) |
| "No clicks" read as "no interest" before the site exists | Clicks are NULL and shown as *"not measurable yet"* until analytics exist |
| Storing other people's posts longer than needed | 30-day deletion of thread bodies we did not answer |
| Outreach spend hides inside extraction spend | Own ledger stage and own cap |
