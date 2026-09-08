# The five new platforms meet the gates

**2026-09-08.** A small real corpus on all five new platforms, triaged. First
time these adapters' documents have faced E4.

**192 documents, 121 kept = 63.0%**, and that figure is an upper bound for
reasons §2 states. Corpus on the **disposable local instance only** — three of
the five rulings are unratified drafts, so `smoke_new_adapters.py` refuses any
non-localhost host and nothing here touched shared staging.

Population fingerprint `b5744297e9210497`, identical to staging's, so the
numbers are comparable to `docs/triage-first-run-2026-09-08.md`.

Runs: `docs/measurements/corpus-harvest-{control,fable,astra}-2026-09-08.json`,
`triage-new-platform-corpus-2026-09-08.json`, `hn-subject-join-2026-09-08.json`.

---

## 0 · Two things about the models, before any figure

Both matter for reading everything below, and I found them before harvesting
rather than after.

**`GPT Astra 6` resolves to nothing, and the name is wrong.** There is no
`astra` surface anywhere in the 1,247-surface population and no `model_version`
row. Worse, the real name appears to be **`GPT-6 Astra`** — an HN story in the
corpus is titled *"GPT-6 Astra soundly defeats Fable 5.1 on recognizing
handwritten…"*, and another simply *"GPT-6 Astra"* with 2,063 comments. `GPT-6
Astra` does not resolve either. So the Astra arm retrieved **0 documents
containing its own query phrase on every platform** (`surf 0` across the board)
and every document it did retrieve was dropped by the entity gate. It exercised
the gates for free and told us nothing about the model — which is what a
control is for, in reverse.

**`Fable 5.1` resolves, to the wrong model.** It matches the surface `fable 5`,
which is owned by `anthropic/claude-fable-5`. There is no `fable 5.1` surface.
So every Fable 5.1 document in this corpus **would be filed against Fable 5**,
silently. The corpus contains a story titled *"Claude Fable 5.1 and Claude
Mythos 5.1"* — two models, neither registered — and `claude mythos 5.1`
resolves to nothing at all.

**This is the registry, not the adapters.** It is also the single biggest
suppressor of the subject-join result in §3, and it is the actionable item out
of this whole exercise.

The control, `claude opus 5`, resolves to 7 surfaces owned by
`anthropic/claude-opus-5` — so a low count on the other two reads as a fact
about the registry, which is exactly why it was there.

## 1 · The corpus, and the distribution per source

Harvested through `harvester_for_source()` for three queries at `--max 17`.

| source | docs | triaged | kept | dropped | survival | never gated |
|---|---|---|---|---|---|---|
| arxiv | 18 | 18 | 17 | 1 | **94.4%** | 0 |
| devto | 40 | 40 | 36 | 4 | **90.0%** | 0 |
| hackernews | 77 | 77 | 38 | 39 | **49.4%** | 0 |
| huggingface | 7 | 7 | 1 | 6 | **14.3%** | 0 |
| x | 50 | 50 | 29 | 21 | **58.0%** | 0 |
| **total** | **192** | **192** | **121** | **71** | **63.0%** | **0** |

**Zero ungated documents**, which is the one clean thing here: every payload was
readable and every one produced prose. Contrast the stored corpus, where 1,492
of 6,502 could not be gated at all.

Drops by gate, over 192:

| gate | dropped | share |
|---|---|---|
| `no-resolvable-entity` | 64 | 33.3% |
| `too-short-no-artifact` | 31 | 16.1% |
| `pure-link-post` | 20 | 10.4% |

**Hugging Face's 14.3% is 1 of 7 and should not be read as a rate.** The
adapter is repo-scoped with no full-text discussion search, so discovery found
3 repos and 4 comments across three queries. n=7 is a sample of the platform's
*shape*, not of its content.

**arXiv's 94.4% is high for a structural reason, not a good one.** An abstract
is long, carries numbers, and names the model in the title — so it passes the
length and entity gates by construction. It is also third-party measurement
rather than own-experience, which is why its `base_trust` is the lowest of the
five. High survival here is not high value.

## 2 · Which gates ran on nothing

| gate | ran on | dropped | could not run | nothing to run on |
|---|---|---|---|---|
| `wrong-language` | **0** / 192 | 0 | **192** | 0 |
| `pure-link-post` | 28 / 192 | 20 | 0 | **164** |
| `too-short-no-artifact` | 192 / 192 | 31 | 0 | 0 |
| `no-resolvable-entity` | 192 / 192 | 64 | 0 | 0 |
| `out-of-window` | 127 / 192 | 0 | 0 | 65 |
| `known-bot` | **0** / 192 | 0 | **174** | 18 |

**Two gates ran on nothing at all, so 63.0% is an upper bound.**
`wrong-language` on all 192 (no detector, and `lang` is NULL on every row here —
none of these five declares a language except dev.to and X, and neither
populated it in this harvest). `known-bot` on all 192, which §4 breaks down.

`out-of-window` dropped **0 of 127** — every resolved model in this corpus is
in the release window. That is a fact about a corpus harvested today, not about
the gate.

## 3 · Does the HN thread-subject join fire? Yes — and on one thread

**It fires, mechanically and decisively.** Repeating the 2026-09-07 experiment
with the same method — every nested comment of the stored stories, entity gate
run twice — over **7,561 comments across 28 threads**, no new requests:

| | resolves | share |
|---|---|---|
| entity gate, **own text only** | 475 / 7,561 | **6.3%** |
| entity gate, **with the thread root** | 1,640 / 7,561 | **21.7%** |
| of which inherited | 1,165 | 15.4% |
| full triage kept, own only | 437 / 7,561 | 5.8% |
| full triage kept, with root | 1,330 / 7,561 | **17.6%** |

So against the 2.2% baseline: this corpus's own-text baseline is 6.3%, and the
join takes it to 21.7% — **3.4× its own baseline, and a 3.0× lift in documents
actually kept.** The ruling is no longer untested.

### And the figure is about one thread

> **1,164 of the 1,165 inherited comments come from a single thread** —
> `49525378`, *"Claude Fable 5.1 and Claude Mythos 5.1"*, 1,377 comments. **Two
> threads of 28 contribute any inheritance at all.**

On that one thread the join is total: 213 of 1,377 comments resolve on their
own, and all 1,377 resolve once the title is supplied. That is the mechanism
working exactly as designed — an announcement thread whose subject is in the
title and whose evidence is in the replies.

**It is also precisely the population the original inheritance refusal was
measured on**: *"the 21 survivors were all in two announcement threads."* Here
it is one. So this result confirms the mechanism and confirms the concern, and
reporting "6.3% → 21.7%" without the denominator would be rule 7's exact
failure.

### Why the other 26 threads contribute nothing

**Only 4 of 28 story titles name a tracked model.** The two largest AI threads
in the corpus name models the registry does not have:

| story | comments | root resolves? |
|---|---|---|
| `GPT-6 Astra` | 2,063 | **no** — not in the registry |
| `Claude Fable 5.1 and Claude Mythos 5.1` | 1,377 | yes (as Fable **5**) |
| `Gemini 3.8 Flash and 3.8 Flash Cyber` | 664 | **no** |
| `Ask HN: Why were OpenAI, Claude, and Grok simultaneously…` | 698 | no — vendors, not models |

**The join's yield is gated by the registry, not by the join.** If `GPT-6 Astra`
were registered, that one thread would add roughly 1,955 more inherited
comments and the corpus-wide figure would roughly double again. The
`no-resolvable-entity` gate dropping 33.3% of this corpus is substantially the
registry being three model-generations behind the conversation.

### One document faced the gate alone and is counted

`root_unresolvable: 1` — one HN comment's `thread_root_id` names a story that
was not stored. Named rather than silently treated as "no subject line", which
is why that counter exists.

## 4 · `pure-link-post` and `known-bot`, per source

### `pure-link-post` returns NOT_APPLICABLE, and does not default either way

Measured per source, on every document:

| source | NOT_APPLICABLE | ran → True (drop) | ran → False (keep) |
|---|---|---|---|
| arxiv | **18 / 18** | 0 | 0 |
| devto | **40 / 40** | 0 | 0 |
| huggingface | **7 / 7** | 0 | 0 |
| x | **50 / 50** | 0 | 0 |
| hackernews | 49 (the comments) | 20 | 8 |

**Confirmed: arXiv, dev.to and Hugging Face are NOT_APPLICABLE on every
document**, never `False` and never `True`. None of the three has a self/link
distinction, so `is_self_post` is NULL and the gate declines. X is the same, and
was not asked about but behaves identically.

Hacker News is the only platform that answers, and it answers three ways: 20
link posts with no commentary **dropped**, 8 self posts kept, and its 49
comments NOT_APPLICABLE — permanently, because the distinction is about how a
*submission* carries content and a comment is neither.

### `known-bot` returns UNAVAILABLE for four of the five, and arXiv is different

| source | outcome | why |
|---|---|---|
| devto | **UNAVAILABLE** 40/40 | source not declared in `contract/bots.yaml` |
| hackernews | **UNAVAILABLE** 77/77 | source not declared |
| huggingface | **UNAVAILABLE** 7/7 | source not declared |
| x | **UNAVAILABLE** 50/50 | source not declared |
| arxiv | **NOT_APPLICABLE** 18/18 | **no author id exists at all** |

The list declares `github` alone (26 gated, 7 counted), so UNAVAILABLE here
means *this platform has not been curated*, not *the list is missing*. The count
shrinks platform by platform as each is read, which is what the per-source
design is for.

**arXiv is the exception and it is permanent.** 0 of 18 arXiv documents carry an
author id — `arxiv.py:author_external_id` returns None by design, because arXiv
publishes no stable author identifier and a paper has many authors. So the gate
returns NOT_APPLICABLE before it ever asks whether the source is declared.
**Curating a bot list for arXiv would be pointless: there is nothing to key it
on.**

### What each would need

Measured author coverage in this corpus:

| source | docs with an author id | example | id space | what it needs |
|---|---|---|---|---|
| hackernews | 77 / 77 | `0xC0ncord` | `hackernews_username` ✓ declared | **a curated block only** |
| huggingface | 7 / 7 | `65fd9db32cbe7ad397c44b28` | `huggingface_author_id` ✓ declared | **a curated block only** |
| x | 50 / 50 | `111982853` | `x_rest_id` ✓ declared | **a curated block only** |
| devto | 40 / 40 | `1250743` | **no `devto_user_id` in `ID_SPACES`** | **a code change first**, then a block |
| arxiv | **0 / 18** | — | none possible | **nothing helps** |

So three of the five need only a `contract/` block. dev.to needs a new member
in `collect/triage/bots.py:ID_SPACES` before a block can even be written — that
list is closed on purpose, because a typo in an id space is a list that matches
nothing and is indistinguishable from a platform with no bots.

## 5 · Two defects the harvest found

Neither was findable by review, and both are the same shape: code written to an
assumed payload, with fixtures built to the same assumption.

**`x_post_prose` read a key the payload does not have.** It looked for a
top-level `text`; the twitter241 payload is a GraphQL `Tweet` whose text is at
`legacy.full_text`. It raised `NotAPayload` on **50 of 50** X documents — the
entire platform produced no prose. `collect/adapters/x.py:_post_of` had been
reading `legacy` correctly the whole time: two readers of one payload, one
right, and only the wrong one on the path that turns bytes into text.

Fixed, and the order matters: **21 of 50 payloads carry a `note_tweet` block**,
where `legacy.full_text` is truncated — 190 characters against the note's 250 on
the first one checked. Reading `full_text` first would cut a long post's
evidence off mid-sentence and a quote of the missing half would fail rule 1's
substring check while the reader can plainly see it. 50 of 50 now yield text.
Regression tests use the real shapes.

**`TriageStoreRun.describe()` crashed the report it was writing.** It built a
line beginning with `⚠`, the script printed it, and Windows' cp1252 console
raised `UnicodeEncodeError` — **after** the per-source table and gate breakdown
had scrolled past, so the useful half was produced and thrown away.
`tests/test_script_output_is_encodable.py` exists for exactly this and scopes
itself to `scripts/` on the stated grounds that `collect/` never prints the
character. A string *returned* from `collect/` and *printed* by a script is the
gap that left; there is now a test that calls the report builders and asserts
what the console will do.

## 6 · What this does not establish

- **Nothing was written to shared staging.** Local disposable instance only,
  and the harvest script enforces that by reading the open connection's host.
- **`triage_verdict` was not written even locally** — the run is a dry run.
- **Three of five rulings are still unratified drafts** (dev.to, Hacker News,
  Hugging Face). This corpus was gathered with the real gate consulted against
  visibly-unratified rulings, which is the arrangement
  `smoke_new_adapters.py` was built for; it is not a clearance.
- **n is small and deliberately so.** 192 documents is enough to exercise six
  gates and not enough to calibrate any of them. The one figure here with a
  real denominator behind it is the subject-join measurement, at 7,561
  comments — and that one is about one thread.

---

*Harvested and triaged 2026-09-08 against
`postgresql://localhost:5433` (disposable). Registry copied from staging so the
population fingerprint matches: 342 `model_version` rows, 1,247 surfaces,
`b5744297e9210497`.*
