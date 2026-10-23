# Proposal: the evidence feed, and the rule-2 amendment it needs

**Proposed 2026-10-21 by anooj, branch `feat/evidence-feed`. Not for `main` until
the two amendments below are reviewed.** `contract/` gets two eyes, and this
changes rule 2 itself.

## What it is

Every model page shows counts: "20 voices" on All models, "3 negative" on
Compare, bars on Most reported. A reader cannot check any of them. The feed is
the drill-down from a number to the reports it counted:

- **Live feed** — every report behind the count, newest first, each with when
  it was posted ("1d ago", exact time on hover), its tags and reaction, **our
  paraphrase** of what the author said, and its source below it: an official
  embed for Reddit and X, a link for everything else. Never a quote.
- **Summary** — one page per model, written from the paraphrases, citing the
  reports each paragraph rests on, with no counts. Drafted by a model,
  **approved by a person** in Admin before anyone sees it.

Entry points: the counts themselves become links, pre-filtered so the list *is*
what the number counted, plus "Evidence feed" in the Models menu.

| From | Opens |
|---|---|
| All models card, "N voices · M reports" | `/evidence/<model>` |
| Model page, a job/capability row and its split | `?section=&slug=` (`&polarity=`) |
| Compare, entries/posts line and each polarity chip | `/evidence/<model>` (`?polarity=`) |
| Most reported, a model's report count and bar segments | `?section=&slug=&polarity=` |

## The guarantee: the feed is the count's population

A feed that lists different reports from the ones counted is not evidence for
the number. `judge/feed/items.py` rebuilds each population with the board's own
rules (non-declined entries, either id shape, `spelling_key` on
`COALESCE(ruling_target, slug)`, `metric_withholding` on section pages, the
board's report-polarity split where one report can be both). The test that
holds it compares against `board_sections` itself, not a copy of its rules:
`tests/test_evidence_feed.py::test_a_section_page_and_the_feed_agree`.

The header carries both units the site uses — reports (everywhere) and entries
(Compare's head-to-head) — so a reader arriving from either finds their number.

## Amendment 1: rule 2

Rule 2 names two stages that may call a model (extract, ask) and records a
third, the blog generator (2026-10-06, #508), as the same shape: **a model
drafts, a person approves, nothing reaches a page unread**. The quiz drafter
(2026-10-15, spend stage `quiz`) is that shape too but is **not recorded in
rule 2** - corrected here from "fifth caller" after review on #558; recording it
is its own change. The summary keeps that shape. **The paraphrases do not**,
and that is the decision:

> 4,122 reports exist today (shared DB, 2026-10-21) and about 500 arrive a
> week. Nobody can approve them one by one. So a paraphrase is stored once
> **code** has checked its shape, and published without a person reading it.

Proposed text, added to rule 2 in `CLAUDE.md` in this PR and marked PROPOSED
there, so the amendment and the code land in the same merge:

> **A fourth recorded caller, PROPOSED 2026-10-23 (#558): the evidence feed,
> `judge/feed/` - the first whose text reaches a page without a person reading
> each item.** A paraphrase restates one report. It is stored only after code
> checks, and the code checks exactly this (`judge/feed/checks.py`):
> - **copying:** no run of consecutive words longer than `max_copied_words`
>   shared with the source; a word is letters or digits in any script, and in
>   Chinese, Japanese or Korean each character is one word;
> - **numbers:** every number in digits appears exactly in the source ("4" does
>   not match "4.1"); a number from the model's name only right after the word
>   it follows in the name ("GLM 5", not "costs 5"); the words two..ninety,
>   hundred, thousand, million, billion, dozen and percent appear in the source
>   as words or digits (a multiplier after "per" or after a sourced number is a
>   unit, "per million tokens");
> - **identity:** no URL, no bare domain other than the vendor's own in the
>   model's name (`huggingface.co` is refused, `Z.ai` for a Z.ai model is not),
>   no `@`, `u/` or `r/` handle, no "reddit", "subreddit", "redditor",
>   "twitter", "tweet" or "x.com";
> - **length:** non-empty and within `max_chars`.
>
> **Not checked, so nobody assumes it is:** "one", "half", "twice" and other
> number words outside that list; a shortened decimal when the short form is
> also in the source ("4.1" written "4" next to a "GLM 4"); a bare "X"; a
> community named without `r/`; a domain on a top-level name not in the list;
> and faithfulness - a number that is in the source but attached to the wrong
> thing passes. The source sits one click from every item for that reason, and
> the polarity shown is the extractor's, never the paraphraser's. The summary
> keeps the guard of the blog generator: a person approves it. Nothing the
> feed's model writes counts, weights, orders, filters or labels anything.

What tightening these cost, measured 2026-10-23 over the 4,102 paraphrases
stored on the local copy (a population the earlier checks had already passed,
so it says what the NEW rules refuse, not how good the old ones were): **34
would now be refused** - 27 number words (mostly the model counting things
itself: "seven metrics", "four categories"), 5 version numbers written without
the model's name, 2 bare domains. A first draft that also refused number words
after "per" and a word-before rule for shortened decimals refused 181, most of
them "per million tokens" and "79" for "79.0", and was cut back.
`docs/measurements/feed-checks-tightened-2026-10-23.*`.

What the trial found about faithfulness: a paraphrase paired "121 tokens per
second prefill" from one excerpt with a checkpoint from another. Every number
was in the source; the pairing was wrong. The source link is the reader's check.

## Amendment 2: `contract/publication.yaml` `evidence_feed`

The board withholds Reddit, X and arXiv entirely (no quote, link, handle or
platform name), while totals count them. **1,595 of 2,725 documents behind
board entries (58.5%) are Reddit, X or arXiv** (shared DB, 2026-10-21), so a feed
that skipped them would back up about half of each number. The feed therefore
follows the *derived-post* terms, not the board's: paraphrase every report,
cite Reddit and X **only** by official embed (loaded when the reader asks),
link every other source, attach arXiv's acknowledgement. No verbatim quote from
any source. The board itself is unchanged.

**An embed travels as ids, never as a URL** (#558 second review, 2026-10-23).
A Reddit permalink names the subreddit and carries the post title's words in its
slug; an X URL carries the handle. So `feed_embed` stores the id-only address
(`reddit.com/comments/<post>/`, `x.com/i/status/<id>`), the API sends only the
ids, and the browser builds the embed's link from them. The platform's own
script then shows the title, author and community in the reader's browser.
Only a 403 or 404 from Reddit's oEmbed is stored as "unavailable"; a rate limit,
a server error or a dropped connection leaves the post pending, to be asked again.

**The feed overrides the board's "no per-platform count"** for the feed only:
items name their platform and can be narrowed to one polarity, so a reader can
count one platform's items. `contract/publication.yaml` `evidence_feed` says so.

**Spend has no dollar ceiling**, only `--limit` and `--model` on a manual run,
at the measured cost: $0.0202 for 237 reports on two models, 218 of them
paraphrased after one retry (the trial below). Summaries are drafted for seated
models only.

## What the trial measured

A real run on a local copy of two models' evidence (DeepSeek V4 Flash and
Grok 4.7, copied read-only from the shared DB into a throwaway local database;
**nothing was written to shared staging**). Model: `deepseek/deepseek-v4-flash`.

| | |
|---|---|
| Reports paraphrased | **218 of 237** stored (92.0%) after one retry each; 19 refused twice and listed without text — 17 for copying more than 6 consecutive words, 2 for length. (That trial ran at 2 attempts; the contract now says 4.) |
| Paraphrase cost | **$0.0202** for those 237 reports, 26 calls — so the 4,122-report corpus is about **$0.35** once |
| Summaries | both stored after prompt fixes (below); 402 and 566 words; 0 and 8 flags |
| Embeds | 152 of 161 Reddit/X documents embeddable; 9 Reddit link posts had no post address because their raw payloads are not on the machine that ran it |
| API, anonymous | `/feed` 200, `/feed/summary` 200 (approved only; a pending draft returns `awaiting_review` and no text), `/feed/summaries` 401 |

That paraphrase run had reasoning on (the trial found and fixed it afterwards),
so it is an upper bound on cost.

What the first drafts got wrong, each caught by a check and each fixed in the
prompt or settings rather than by loosening a check:

1. **Reasoning ate the budget.** DeepSeek V4 Flash thinks by default; a
   137-report summary spent all 3,200 output tokens reasoning and never called
   the tool. Fixed with `reasoning_effort: none` (the extractor's setting).
2. **Too long.** Asked for at most 450 words it wrote 516 and 530. Limit raised
   to a page (600), prompt asks for 70% of it.
3. **Invented and misattached numbers.** Refused by the number check (a "56"
   no cited report carried). The prompt now asks for no measured figures; a
   figure that survives is *flagged* for the reviewer, not refused (rule 8).
4. **A hallucinated citation** (R82 of 81). The prompt now states the id range.
5. **Quantity words** — "widely", "consistently", "several", "majority" — are
   consensus claims a model may not make (rule 3). Flagged for the reviewer.

## Decisions for the reviewer

1. **The copy limit.** 6 consecutive words lets "smarter than Terra or Sonnet
   and costs about half the price" through for a Reddit post. Tighter means
   more reports listed without text. Possibly a lower limit for embed-only
   sources only.
2. **Who approves summaries,** and how often they are redrafted (today: when a
   newer report than the last draft's has been paraphrased).
3. **When the build runs.** After extraction, nightly:
   `python scripts/build_evidence_feed.py --embeds --paraphrase --summaries --apply`
   with `RAW_STORE_PATH` pointing at the shared store.
4. **The migration** (`20261021T1000_evidence_feed.sql`): applied by whoever
   merges, immediately after merge, announced the same day — not before.

## Files

- `contract/evidence_feed.yaml`, `contract/publication.yaml` (`evidence_feed`),
  `contract/migrations/20261021T1000_evidence_feed.sql`, `contract/tables.sql`,
  `contract/column_states.yaml`
- `judge/feed/` — `items.py` (read path), `paraphrase.py`, `summary.py`,
  `checks.py`, `llm.py`; endpoints in `judge/app.py`; public reads in `judge/gate.py`
- `scripts/build_evidence_feed.py` — embeds, paraphrases, summary drafts
- `web/src/routes/Evidence.jsx`, `web/src/evidence/parts.jsx`,
  `web/src/components/FeedSummaryPanel.jsx`, entry points in Catalog, model
  page, Compare, Reports, Nav, Footer
- `tests/test_evidence_feed.py`
