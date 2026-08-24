# Nine feeds swept. Eight of them barely name a model

**The corpus went from 31 blog documents to 120 across 7 hosts, and the
capability question it was meant to settle cannot be settled — because the eight
new feeds do not discuss named models often enough to produce a distribution.**

```
                            docs  names a model  resolves to one  triage kept
simonwillison.net             44        15             10             16
vickiboykis.com               20         3              3              4
jxnl.co                       20         1              1              2
hamel.dev                     12         1              1              1
engineering.grab.com          10         1              0              1
slack.engineering              8         1              0              1
engineering.atspotify.com      5         1              0              1
TOTAL                        119        23             15             26
```

**Willison is 15 of the 23 model-naming documents (65%) while being 37% of the
corpus.** The other six writers contribute 8 model-naming documents between them.
So the concentration got better by document count and barely moved by *evidence*.

*Engineer 1 · 2026-08-21 · 9 feeds, ~230 HTTP requests, no model calls, $0.00*

---

## 1 · Cost, stated first — and the 304 saving does not exist yet

```
robots.txt          9 requests, cached one hour per host
feeds               9 conditional GETs
articles          105 GETs (class-A rulings permit article fetches)
                  ~123 per run, at ~1/sec politeness
money               $0.00 — no model calls, no metered API
```

**The conditional-GET saving is designed, tested, and not wired.**
`BlogFetcher` defaults to `InMemoryValidatorStore`, and
`collect/adapters/blog/validators.py` says so in its own docstring: *"Nothing
here writes to the database."* The durable home — `watermark.etag` and
`watermark.last_modified` — is a **contract change that has not been agreed**.

So an unchanged feed is *not* one 304 across runs. It is a full re-fetch, every
time, and this sweep proved it: Willison's feed had been swept before and
returned all 30 entries rather than a 304. **Every future blog sweep costs the
full ~123 requests until those two columns land.**

That is the cheapest outstanding item in this lane and it is blocked on a
contract change, not on work. Proposed, not taken.

---

## 2 · What landed

```
feeds                9      refused 0      all robots.txt checked and allowed
articles           105
documents           89 new  (105 - 16 already present)
thread_contexts     89 new
corpus:  blog 120   reddit 196   github 27   = 343 documents
```

Per host, after the run: Willison 44, vickiboykis 21, jxnl 20, hamel 12, grab 10,
slack 8, spotify 5.

**Two feeds produced nothing at all**: `netflixtechblog.com` and
`medium.com/airbnb-engineering`, both under the `blog-class-b-medium` ruling, 0
articles each. Reported rather than treated as a failure — a Medium-hosted feed
under a different ruling behaving differently is the ruling working — but *why*
is unexamined, and 2 of 9 feeds contributing zero is worth knowing before anyone
counts nine feeds as nine sources.

### Two defects the sweep exposed, both the same shape

**`feed=` was never passed to the writer, so 89 documents landed with 0
authors.** `write_blog_run(conn, run, store=store)` — and the writer's own
docstring says the default *"keeps the old behaviour — `author_id` NULL, honestly
unknown"*. Honest, and not what a sweep wants. Fixed at the call site, and
`write_blog_run` now also attaches an author to a document that already exists
(guarded by `author_id IS NULL`), the same fix already applied to
`reddit_write` and `github.write_documents`.

```
blog author rows   1 -> 14
attributed         simonwillison 44/44 · jxnl 20/20 · grab 10/10 · spotify 5/5
correctly NULL     vickiboykis 0/20   (byline_source: none)
unwired            hamel 0/12, slack 0/8  (byline_source: entry — several
                   authors per feed and no per-document mapping exists)
```

So **4 blog voices carry documents**, and 10 more author rows exist that nothing
points at. Blog is 4 voices for 120 documents, which is the honest count and the
reason blog can never be the platform that clears `N_EFF_MINIMUM` alone.

**And the same missing argument made the template-block rules inert.**
`template_block_for(feed.get("id") if feed is not None else None)` — with
`feed=None` the rule cannot resolve, so run 1 flattened every article *without*
stripping. Measured after: **54 of 119 thread_contexts contain a template
block.** Run 2 fired the rules correctly (29 stripped for Willison, 10 for Grab)
and wrote nothing, because the contexts were already present.

> **This is the third instance this week of a capability that exists and nothing
> calls.** `document.author_id` had a writer and no caller; `collect/triage/`
> computes verdicts nothing persists; here a writer took an argument no caller
> passed, and one omission cost both the authors and the stripping. The tell is
> the same each time: the default is *honest* — NULL, inert — so nothing fails,
> and the gap reads as a considered absence.

---

## 3 · The capability question: it cannot be re-read, and that is the answer

The test was: *if `code.generation` is a fact about Willison rather than about
blogs, eight more feeds will say so.*

**The eight feeds cannot say either way, because they do not name models.** 8 of
75 non-Willison documents name any model; **5 of 75 resolve to exactly one.** The
three corporate engineering blogs — Grab, Slack, Spotify — contribute 1
model-naming document each and **0 that resolve to a single model.**

So a paid extraction run over the 89 new documents (~$0.19 at the measured
per-document rate) would read 75 documents that mention no model to produce at
most a handful of claims. That is not a distribution and it would not test
anything. **Not run**, and the reason is a free measurement rather than a budget
call.

### What that itself says about the medium

It is a finding, and a more useful one than the split would have been:

> **"Engineering blog" is not one channel.** A practitioner's link blog —
> Willison, Boykis — names specific models constantly, because naming the model
> is the point of the post. A company engineering blog names architecture and
> almost never a model version, because the post is about the system. They share
> a retrieval mechanism (RSS) and a terms class, and they are different
> populations for our purposes.

`contract/sources.yaml` classifies these feeds by *terms* (class-A self-hosted,
class-B Medium), which is the right axis for permission and the wrong axis for
yield. Nothing in the contract distinguishes *"names models"* from *"names
systems"*, and after this sweep that distinction predicts document yield better
than anything recorded.

**And the correction to the figure that framed the question**: `code.generation`
is **9 of 36 blog claims — 25%**, not 79%. It is the largest single key and it is
not a majority. I cannot source 79% from any run.

---

## 4 · The zero-overlap premise: the cheap test ran and did not move it

Eight more feeds were the only move that could produce a platform overlap without
a new Reddit sweep. It did not, and now it is measured rather than argued:

```
non-Willison documents resolving to exactly one model      5 of 75
of those, on a model Reddit also discusses (fable-5)       0
```

So the premise finding stands and is stronger, with one correction carried
forward from last turn that matters here: **the overlap was never absent at the
capability level.** Blogs carry 9 capabilities, Reddit's 2 are both among them.
The intersection is `{code.generation, over_refusal}`, not empty.

What is empty is the overlap of **models**, and nine feeds did not change it:
blogs discuss GPT-5.6, Qwen 3.8, Claude Haiku 4.5; the Reddit thread discusses
Fable 5. `PLATFORM_MINIMUM = 2` needs one cell — one model, one capability, one
bucket — on two platforms, and the corpus has never produced one.

**A ninth feed will not fix that and neither will a tenth.** What would: a Reddit
sweep aimed at the models the blogs actually discuss, which is a query change
rather than a corpus change. That is the next cheap test and it is not this one.

---

## 5 · Inheritance: ruled twice, recorded as closed

Taken. `docs/measurements/inherited-subjects-and-family-claims.md` now opens with
**RULED TWICE, NOT DEFERRED**, and states the shape rather than only the outcome:

```
ruling 1   the second condition fires on 60% of candidates; what survives is
           announcement threads.                        A QUALITY objection.
reopened   the recoverable population is much larger than 21 — true, measured
           at 104 comments and 86 voices, a 6.1x n_eff multiplier.
ruling 2   the FIRST condition fails (population 0 on the thread we hold), 72%
           of what it recovers carries no specificity signal, and 6.1x lands at
           1.247 against a threshold of 3.0.
           A CORRECTNESS objection, a PURPOSE objection, an ARITHMETIC one.
```

With the pattern stated where the next reader will meet it: **a rule getting more
attractive under measurement is not evidence for it.** The reopening was right
and the answer went the other way.

---

## What changed

| file | change |
|---|---|
| `scripts/harvest_blogs.py` | passes `feed=` to the writer — the one omission that cost 89 documents their authors and their template stripping |
| `collect/adapters/blog/write.py` | attaches an author to an already-present document, guarded by `author_id IS NULL`; `authors_attached_to_existing` on the report |
| `docs/measurements/inherited-subjects-and-family-claims.md` | RULED TWICE header |

Database: **343 documents** (blog 120, reddit 196, github 27), **166 author rows**
(reddit 152, blog 14).

**Open, and named rather than fixed:** 54 contexts carry a template block and a
re-flatten cannot land on the current path; 2 of 9 feeds yield nothing and nobody
has looked at why; `entry`-byline feeds have authors and no per-document mapping;
and the conditional-GET columns are still an unagreed contract change.
