# What symbols blog articles actually contain

**Both candidate rules are wrong. `So` does not generalise off the Reddit
fixture, and "sentiment versus value" is not what the corpus contains either.
The dominant class is box-drawing characters inside fenced code blocks — where
substitution destroys a directory tree — and it comes from 2 documents out of
106, which makes it a severity finding and not a frequency one. No rule is
proposed here.**

*Engineer 1 · 9 feeds, live · 2026-08-18 · `_blog_so_sweep/`*

> The `So` rule was read off one Reddit fixture where `So` meant emoji plus `█`.
> My own counter-examples — `°`, `©`, `®`, `™` — occurred **zero** times in
> 519,997 characters. The constructed census was right that the rule is wrong
> and wrong about how.

---

## 0 · Two populations, and which figure came from which

Stated first because the two differ by a factor of two and mixing them is
rule 7's failure.

| population | what it is | n |
|---|---|---|
| **A — the sweep** | articles measured under the per-feed cap of 8, `_blog_so_sweep/manifest.json` | **53 articles, 519,997 chars** |
| **B — the re-extraction** | every article the fetch path stored in `raw/`, re-extracted with no network calls | **106 articles** |

Population B is larger because `harvest_feed` fetches every entry in a feed
while the sweep only *measured* the first 8 per feed. B is used for anything
about fence membership and concentration; A for anything with a character
denominator. Each figure below says which.

Nine feeds attempted, **nine passed the terms gate**, robots.txt re-read per
host on this run. Two returned no articles and it is not a failure:
`netflixtechblog.com` and `medium.com/airbnb-engineering` are
`blog-class-b-medium`, whose ruling sets `fetch_articles: False`, so the feed
body is the permitted retrieval. Recorded rather than retried.

## 1 · The entity ruling, confirmed on real articles

```
entities_surviving_trafilatura: {}     (population A)
```

**Zero of the five reached the flattener** across 53 articles. §4's ruling was
made from a constructed probe; this is the frequency measurement behind it, and
it agrees. `BLOG_RULES.decode_entities = False` is now in
`collect/assemble/flatten.py` with the reasoning in the code.

The reason the pass is *off* rather than merely *unused* is the third decode,
and it is not reachable by anything a fixture built from this corpus contains —
same shape as `&amp;gt;` on the Reddit side, and tested synthetically for the
same reason.

## 2 · Every `So` character that actually appeared

Population A: 190 occurrences, **365 per million characters**, in **14 of 53
articles (26%)**. Population B: 236 occurrences in 28 of 106 (26% — the same
share, which is the one number that replicates across both).

| codepoint | ch | n (B) | docs | flat cost | name |
|---|---|---|---|---|---|
| U+2500 | ─ | 68 | 2 | +30 | BOX DRAWINGS LIGHT HORIZONTAL |
| U+21A9 | ↩ | 30 | 10 | +26 | LEFTWARDS ARROW WITH HOOK |
| U+2502 | │ | 27 | 2 | +28 | BOX DRAWINGS LIGHT VERTICAL |
| U+251C | ├ | 26 | 2 | +38 | BOX DRAWINGS LIGHT VERTICAL AND RIGHT |
| U+25B6 | ▶ | 13 | — | +30 | BLACK RIGHT-POINTING TRIANGLE |
| U+2514 | └ | 8 | 2 | +32 | BOX DRAWINGS LIGHT UP AND RIGHT |
| U+1F449 / U+1F448 | 👉 👈 | 6 / 6 | — | +38 | POINTING BACKHAND INDEX |
| U+2318 | ⌘ | 6 | 1 | +23 | PLACE OF INTEREST SIGN |
| U+2726 | ✦ | 6 | — | +24 | BLACK FOUR POINTED STAR |
| U+1F4BC | 💼 | 5 | 5 | +10 | BRIEFCASE |
| ~25 others | | 1–3 each | | | mostly single-occurrence emoji |
| U+2713 / U+2705 | ✓ ✅ | 1 / 1 | 1 | +11 / +23 | CHECK MARK / WHITE HEAVY CHECK MARK |

**Zero occurrences, all population B:** `°` `©` `®` `™` `█` `⚠` `⭐`.

`°` was my worked example for "content, not decoration" and it is not in the
corpus. `█` is the character the original rule was justified by and it is not
here either. The check mark in a table — the case I argued mattered because
`include_tables=True` — is **2 occurrences in 1 document**.

## 3 · The discriminator is context, not the character

Population B, classified by whether the character sits inside a ``` fenced
block (readable off trafilatura's own output, since `include_formatting=True`):

```
inside a code fence    133   (56%)
in prose               103   (44%)
```

| Unicode block | in fence | in prose | total |
|---|---|---|---|
| Box/Block Drawing | **129** | **0** | 129 |
| Emoji, pictographic | 4 | 43 | 47 |
| Arrows | 0 | 30 | 30 |
| Dingbats | 0 | 8 | 8 |
| Misc Technical | 0 | 6 | 6 |
| other | 0 | 16 | 16 |

The separation is near-total: box drawing is **129 in fences and 0 in prose**,
and everything pictographic is the other way round. That is a cleaner split than
any property of the characters themselves, and the flattener has no notion of a
code fence.

### What it costs when it happens

One article: **16,637 chars → +3,654, a 22% inflation from 117 substitutions.**
Its content is a directory tree:

```
/
├── app/
│   ├── server.py              # FastAPI app factory
│   │   ├── simple_react_agent.py
```

Flattened under the current global rule that becomes
`[box_drawings_light_vertical_and_right][box_drawings_light_horizontal]...`.
The tree is not degraded, it is destroyed — and it is exactly the kind of
specific, quotable technical content triage ranks highest.

## 4 · Why this does not become a rule today

**129 of the 236 occurrences come from 2 documents, and 117 from one.**

| class | n | documents | max in one doc |
|---|---|---|---|
| box/block drawing | 129 | **2** | **117** |
| emoji pictographic | 47 | 10 | 21 |
| arrow | 30 | 10 | 7 |
| other symbol | 24 | 9 | 14 |
| misc technical | 6 | 1 | 6 |

So "56% of occurrences are inside code fences" is very nearly *one article*.
The count is real and it answers a question nobody asked: it measures how many
box-drawing characters that one author used, not how often blog articles contain
ASCII-art trees. **The document frequency is the honest figure — 2 of 106 — and
the severity is the finding.**

That is enough to say the current rule is wrong. It is not enough to say what
the right one is, and narrowing a rule from 2 documents is the same move as
narrowing it from 1 Reddit fixture.

## 5 · What the corpus says about the hypothesis on the table

The proposal was that the split is "characters that carry sentiment" versus
"characters that carry a value", and that this is not a Unicode category. **The
second half is confirmed and the first half is not what is here.** Three classes,
not two:

| class | n (B) | example | substituting it |
|---|---|---|---|
| **structure** | 129 | `├──` in a directory tree | destroys the content |
| **chrome** | 43 | `↩` footnote backlinks, `▶` disclosure markers | should never have been extracted |
| **decoration** | 43 | 💼 🎓 🎉 in headers and prose | the rule's original justification, and fine |
| **value** | 8 | `⌘` a keyboard shortcut, `✓` a table cell | destroys the content |

`↩` is the second-most-common character in the corpus and belongs to none of the
proposed categories: it is a footnote back-link the renderer emitted, in 10
documents. Substituting it is harmless because it should not be in the text at
all — that is a boilerplate-extraction question, not a flattening one, and it
would be a mistake to fix it in the flattener where it will look solved.

Sentiment-versus-value would keep 💼 and drop `⌘`, which is backwards for `⌘`
and right for 💼. It does nothing about structure, which is the expensive class.

## 6 · What would settle it

- **More documents containing code fences.** Two is not a corpus. The next
  sweep should over-sample articles with fenced blocks rather than take the
  first 8 per feed, and the count to watch is *documents*, not occurrences.
- **A fence-aware flattener, measured before it is written.** The split in §3 is
  the strongest signal here and it is a structural property, so it can be
  computed exactly rather than inferred from a character list.
- **Nothing about `°`, `©` or `™`.** They are absent. Any rule justified by them
  would be justified by my constructed probe, which is what this document exists
  to correct.

## 7 · What did change

Three rulings landed with this run, none of them the `So` rule:

- `BLOG_RULES.decode_entities = False` — §1, and rule 1 cannot catch the defect
  it prevents, so the reasoning is in `flatten.py` rather than only here.
- `WHOLE_DOCUMENT = "whole_document"` for a one-member thread's
  `selection_method` — nothing was ranked.
- `BLOG_COVERAGE_HIDDEN_CHILDREN_MIN = None` — `include_comments=False` means we
  withheld, so 0 would be rule 6 leaning towards flattering our own coverage.

`So` stays global and known-wrong. That is the deliberate outcome.

## 8 - For Engineer 2

**A NULL `coverage_ratio` now carries two meanings and only its inputs separate
them.** Flagged rather than solved, because it is the display side.

    inputs (0, NULL, 0)        no children exist       a blog article
    inputs (NULL, NULL, NULL)  never measured          a pre-#54 row

Both generate NULL. A consumer selecting `coverage_ratio` alone cannot tell
"this article has no comment section" from "nobody has measured this thread",
and rule 4 says those must not render alike - absence of evidence reading as
evidence. `observed_children` is the column that disambiguates: 0 is a
measurement, NULL is not.

Same class as the `insufficient` status that prompted this whole change:
`cell.status` records `insufficient` and the gate's reason is not persisted at
all, so `platform_count = 1` has to be inferred by whoever reads the row. One
platform looking like "the extractor found nothing" is what made the blog path
urgent; this is the same shape one table over.

## 9 - What produced this corpus, and what says so

Added 2026-08-19, when `pipeline` was folded into `extraction_version`
(`collect/adapters/blog/options.py`). It changes what identifies an extraction,
so it changes what this corpus can claim about itself.

**Nothing recorded the identifier.** Not a column - `thread_context` has no
`extraction_version` and never has - and not this measurement either. The
manifest records

    "extraction_options": "collect.adapters.blog.options.DEFAULT_EXTRACTION"

which is a **reference to a symbol, not a value**. The symbol still resolves; it
resolves to something else. Its fingerprint was `190b1753cf1b` on 2026-08-18 and
is `ef2e678b64d9` today, and a reader following the reference gets the current
answer to a question about a past run with nothing saying they differ. A stored
reference to mutable config is the configuration-identifier failure in its
purest form: it looks like provenance and it is a pointer.

**What actually exists, counted rather than recalled:**

| | |
|---|---|
| article payloads in `raw_store/raw/` | **106** (+ 9 feed payloads) |
| articles this census measured (population A) | 53 |
| blog `document` rows | **0** |
| blog `thread_context` rows | **0** |
| claims resolving against any of it | **0** |

So the corpus is raw bytes and a measurement. `write_blog_run` has never run
against it, and the paid stage has never touched it.

### The three options, none of them picked here

**Re-extract.** Every payload in `raw/` is immutable and content-addressed, so
re-extraction needs no network and cannot drift. It costs CPU and nothing else
*today*, because there are no `document` rows to reconcile and no claims whose
offsets would move. That is a property of this week, not of the corpus: the
first blog document that gets extracted against closes it.

**Mark.** Write the identifier the corpus was produced under - `pipeline-1`,
options `190b1753cf1b` - onto the artefacts that describe it. Cheap, and it is
an assertion about a run nobody observed. It is right if the code path is
unchanged since 2026-08-18, and no stored value proves that; it would be
recording a belief in the slot where a measurement goes, which is the move
`docs/measurements/README.md` exists to argue against.

**Accept and record.** Leave the corpus as it is and state that its extraction
configuration is unidentified. Free, honest, and it makes the corpus unusable as
a baseline for any before-and-after comparison across a pipeline change - which
is most of what a stored corpus is for.

The choice turns on whether these 106 payloads are a *measurement input* (then
re-extract, while it is free) or a *historical record* (then accept and record,
because marking invents the provenance it appears to preserve). That is a call
about what the corpus is for, and it is not one to make inside a census.
