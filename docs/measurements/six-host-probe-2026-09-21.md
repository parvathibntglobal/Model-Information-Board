# Six hosts probed: robots, feeds, and the two deciding numbers

**Run:** 2026-09-21. `scripts/_six_host_probe.py`, artifacts in `_six_host_probe/`
(per-host `report.json`, `robots.txt`, `feed.xml`, and the ten article HTMLs each).
Read-only against the registry; no write, no model call, no spend.

**Hosts:** `minimaxir.com`, `fast.ai`, `matt-rickard.com`, `thorstenball.com`,
`maggieappleton.com`, `swyx.io`. The four already refused — LLM Stats, BenchLM,
LMSYS, the vendor research blogs — were not probed.

**This rules on nothing.** Seating a feed is a `contract/` change and gets two
eyes. This is the evidence that argument would be made from.

---

## The denominators, stated first

Every figure below is drawn from one of three populations, and they are not the
same one:

| Population | Size | How it was gathered |
|---|---|---|
| conventional feed paths | **9 per host** | a fixed list, probed in full — not a search that stops on success |
| feed entries | 10, 20, 10, 20, 142, 432 | whatever the host's feed declares |
| **articles measured** | **10 per host** | the first ten on-host entry links robots permitted |

So "9/10 name a tracked model" is *nine of the ten most recent on-host posts*,
and it is **not** a rate for the blog, whose archive runs to 432 entries on one
of these hosts. Ten is a sample the host chose the order of.

---

## 1. Robots, and the classification the probe made

All six permit. Nothing had to be skipped for robots, on any path, on any host:
**zero robots-refused article paths across 60 articles.**

| Host | robots | status | serves as | platform, by probe |
|---|---|---|---|---|
| minimaxir.com | 200 | rules | minimaxir.com | **Hugo** (`generator` meta), Cloudflare |
| fast.ai | 200 | rules | **www.fast.ai** | **Quarto 1.9.38** (`generator` meta), Cloudflare |
| matt-rickard.com | 200 | rules | **mattrickard.com** | Astro (370 `astro` refs in article HTML), Cloudflare |
| thorstenball.com | **404** | **no-rules** | thorstenball.com | Netlify; no generator, no framework marker |
| maggieappleton.com | 200 | rules | maggieappleton.com | Astro (9,385 refs), Vercel |
| swyx.io | 200 | rules | swyx.io | no generator; Cloudflare; **not a hosted platform** — see below |

**Two of the six do not serve the host you asked for.** `matt-rickard.com`
308-redirects to `mattrickard.com`, and `fast.ai` 301s to `www.fast.ai`. Both
targets serve their own `robots.txt`, which is the one the probe obeyed and the
one that governs the articles. This matters beyond pedantry: a `sources.yaml`
row naming `matt-rickard.com` would name a host that serves nothing, and the
host-match in `_blog_corpus_census.py:feed_of` joins on the **article** URL's
hostname, so the census would file every one of its documents as
`(unseated: mattrickard.com)`.

**`thorstenball.com/robots.txt` is a 404**, which under
`collect/adapters/blog/robots.py` is a definite value — the server answered, and
the answer is that there are no crawl rules — and not a missing one. It is also
the case the class A ruling's 404 caveat is about: where robots is silent, the
class A reading carries the whole weight. Among the seated nine only
`engineering.grab.com` is in this position; this would be the second.

**`swyx.io` is the only host of the six that says anything about AI**, and it
says yes:

```
User-agent: *
Content-signal: search=yes, ai-input=yes
Allow: /
```

That is a Content Signals declaration, and it is the publisher speaking about AI
use inside the crawl policy. It is *evidence toward* the class A reading and
**not** a terms review — the ruling records that no terms page has been read for
any feed, and this does not change that. Recorded verbatim in the report rather
than summarised, because "the publisher permits AI input" is a sentence somebody
will later want the source of.

### swyx.io is not Substack

It was worth checking and it is refuted. Five independent things say so:

- every article's `<link rel="canonical">` points at **swyx.io** (10 of 10);
- **no** Substack script or iframe on any of the ten — the only four iframes are
  `srcdoc`, self-contained, no external origin at all;
- `substackcdn.com` appears on **1 of 10 pages**, as one hotlinked `<img>`;
- of 134 `substack` occurrences across the ten, **132 are in a single post**,
  `/lead`, which is a post *about* Substack, and the rest are in-text links;
- the feed is served from swyx.io with **432 on-host entries**.

`latent.space` appears as an outbound link on 5 of 10 pages. It is his Substack
and it is a different host — outside any ruling that would authorise swyx.io, on
exactly the reasoning that stopped the `sebastianraschka.com` feed from being
followed to `magazine.sebastianraschka.com`.

**The probe's own near-miss is worth recording.** The first pass classified from
the homepage alone, and swyx.io's homepage carries **no platform marker of any
kind** — the label came back `cloudflare`, from a response header. A hosted
platform behind a custom domain shows itself on the *article*, not on a
hand-built homepage. The probe now classifies over the ten article pages too,
and counts markers **per page**, because 134 hits over a concatenation and 132
hits in one post are the same total and opposite findings.

I can confirm the swyx guess was wrong and cannot say which three of six the
hand pass got wrong, because swyx was the only hand classification I was given.

---

## 2. The feed check: nine conventional paths

Every host has a feed, so **none of the six is excluded on this test**. But the
path is different on five of six, which is the argument for probing rather than
guessing one:

| Host | hits among the nine | feed used | type | entries |
|---|---|---|---|---|
| minimaxir.com | `/index.xml` | `https://minimaxir.com/index.xml` | rss20 | 10 |
| fast.ai | `/index.xml` | `https://www.fast.ai/index.xml` | rss20 | 20 |
| matt-rickard.com | `/rss` | `https://mattrickard.com/rss` | rss20 | 10 |
| thorstenball.com | `/atom.xml` | `https://thorstenball.com/atom.xml` | atom10 | 20 |
| maggieappleton.com | `/rss.xml` | `https://maggieappleton.com/rss.xml` | rss20 | 142 |
| swyx.io | `/feed`, `/feed/`, `/rss`, `/rss.xml` | `https://swyx.io/rss.xml` | rss20 | 432 |

No feed was malformed. Four of the six also declare their feed in the homepage
`<link rel=alternate>`; `minimaxir.com` and `matt-rickard.com` declare nothing
and were found only by the path list.

**A 200 is not a feed.** The check is "parses, and has at least one entry" —
several hosts serve a 404 page at 200, and a discovery rule keyed on status code
would have reported feeds that do not exist.

---

## 3. Ten entries each

| Host | on-host | median body | median feed summary | template block | article `author` meta |
|---|---|---|---|---|---|
| minimaxir.com | 10/10 | **11,127** | 60 | clean | 0/10 |
| fast.ai | 10/10 | 9,980 | 55 | clean | **10/10** |
| matt-rickard.com | 10/10 | **1,895** | 160 | clean | 0/10 |
| thorstenball.com | 10/10 | 4,257 | 4,268 | clean | 0/10 |
| maggieappleton.com | 10/10 | 6,377 | 99 | clean | 6/10 |
| swyx.io | 10/10 | 5,780 | 134 | clean | 0/10 |

**On-host ratio is 1.0 on all six** — no feed syndicates its entry links
elsewhere, so the `sebastianraschka.com` problem does not arise here.

**No template block on any host at the 80% threshold.** Every article fetched
returned 200; no paywall wall, no login wall. Two short bodies, both on swyx.io
(253 and 327 chars) — reported as evidence, not as a paywall verdict, which is
the rule 8 shape that caught the `eugeneyan.com` meta-refresh stub.

**`thorstenball.com` is the only full-text feed here** — median summary 4,268
against median body 4,257. The other five publish summaries at 55–160
characters, which is the Lil'Log/Eugene Yan shape and the reason section 4 is
measured where it is.

---

## 4. The two deciding numbers

Measured with `RegistrySurfaceFinder` and `RegistrySurfaceResolver` over 348
`model_version` rows — the same population `_blog_corpus_census.py` uses, so
these numbers mean there what they mean here. Over **article text**, with the
feed-only figure beside it:

| Host | names a tracked model | resolves to exactly one | feed-only would say |
|---|---|---|---|
| **minimaxir.com** | **9/10** | 0/10 | **0/10** |
| maggieappleton.com | 2/10 | 0/10 | 0/10 |
| fast.ai | 1/10 | 0/10 | 0/10 |
| swyx.io | 1/10 | 1/10 | 0/10 |
| matt-rickard.com | 0/10 | 0/10 | 0/10 |
| thorstenball.com | 0/10 | 0/10 | 0/10 |

**Measuring the feed would have returned 13 of 13 naming events as zero.** The
warning was right, and it was not close: the five summary feeds yield 0/10 on a
host whose articles yield 9/10.

### The `resolves to exactly one` column is measuring something else

It reads as a near-total failure and it is not one. On `minimaxir.com` the zero
is produced by posts naming **18, 12, 9, 7, 7, 7, 6, 2 and 2 models** —
`/2026/07/jacobian-conjecture/` alone resolves 18 distinct models. The metric is
not failing to resolve; it is reporting that these are comparison posts.

So the two columns disagree about the same host in opposite directions, and
**the pair is the finding, not either one**. `minimaxir.com` is by a distance
the richest of the six in model mentions and would score last on a
single-model-per-document gate. Which of those two is the seating criterion is a
question for the ruling, not for this probe — flagging it because a table
sorted on the second column puts the best source at the bottom.

`swyx.io`'s 1/10 is a single post resolving `google/gemini-2.5-flash`.

---

## 5. ⚠ Bylines: four of six produce no voice

This is the flag. `voice_id` collapses an unbylined blog entry to
`anonymous:blog` **platform-wide**, so an unbylined host contributes text and no
voices, and two of the three feeds just seated already do this.

| Host | entry-level byline | distinct | verdict |
|---|---|---|---|
| **fast.ai** | **20/20** | **7 distinct authors** | the only multi-voice host of the six |
| matt-rickard.com | 10/10 | 1 (`matt@mattrickard.com (Matt Rickard)`) | one voice |
| thorstenball.com | **0/20** | — | feed-level `author` only: `Thorsten Ball (me@thorstenball.com)` |
| **minimaxir.com** | **0/10** | — | **no byline anywhere** — no feed author, no article `author` meta |
| **maggieappleton.com** | **0/142** | — | no feed author; `author` meta on 6/10 articles |
| **swyx.io** | **0/432** | — | no feed author, no article `author` meta |

**Three of the six carry no entry-level byline and no feed-level author:**
`minimaxir.com`, `maggieappleton.com`, `swyx.io`. Seating all three adds up to
584 declared entries that resolve to one shared `anonymous:blog` voice — and it
does so **to the same bucket the already-seated unbylined feeds land in**, so
their text merges rather than just being uncounted.

`thorstenball.com` is the case worth naming separately: the author is present
but at **feed level**, which an entry-level reader does not see. That is a
one-line fix in an adapter, not an absent fact — but it is absent today, and a
reader who checks only `entry.author` would record it as anonymous.

`fast.ai` is the outlier in the useful direction: 20 of 20 entries bylined, 7
distinct authors including Jeremy Howard, Rachel Thomas and Hamel Husain, and
`author` meta on 10 of 10 articles. It is also 1/10 on naming a tracked model.
**The host with the most voices has nearly no model mentions, and the host with
the most model mentions has no voices at all** — on these ten each, which is the
sample and not the archive.

---

## What this does not establish

- **No terms page was read for any of the six.** Same position as the seated
  nine. `swyx.io`'s `Content-signal` is a crawl-policy line, not a terms review.
- **Ten articles per host, newest-first as the feed ordered them.** Not a random
  draw, not the archive. `maggieappleton.com` has 142 entries and `swyx.io` 432;
  a ten-post sample from the top of either is a recency sample.
- **The platform classifier's error rate is unmeasured**, so it is a recorded
  field with its evidence attached and never a gate — rule 8. Its one known
  near-miss is in section 1, and it was found by checking a label the probe was
  confident about.
- **Nothing here says any of these should be seated.** Adding a feed outside the
  nine assessed requires re-review under the class A ruling's own terms.

---

# Corrections, 2026-09-21 (same day, during the seating pass)

Four things above are wrong or incomplete. They are corrected here rather than
edited in place, because two of them were load-bearing in the seating argument
and the reasoning that produced them is worth keeping visible.

### 1 · `thorstenball.com` is not a "recoverable case" — it works today

Section 5 says its feed-level author is a thing "an entry-level reader does not
see" and calls it "an adapter line, not an absent fact". **Wrong about this
pipeline.** `collect/assemble/authors.py:from_blog` rules four cases and
`feed_declared` is one of them: it writes one author row and
`document.author_id` is set. It is the shape `simonwillison.net` has used since
the nine were seated. thorstenball.com yields **one real voice**, with no work
required.

### 2 · `www.fast.ai` does not buy seven voices — it buys none, today

The worse error, and it runs the other way. Section 5 presents fast.ai's seven
distinct authors as the counterweight to the 584 unbylined entries. But
`byline_source: entry` with **more than one** distinct byline takes the
`authors_per_entry_unwired` branch in `collect/adapters/blog/write.py`: the
author rows are written and **`document.author_id` is left NULL**. That is open
issue #373 — 19 orphaned author rows and 31 unattributed documents already.

So until #373 closes, fast.ai's documents land in `anonymous:blog` beside the
three unbylined feeds, and the trade stated in section 5 is not the trade.
**Of the nine feeds seated today, exactly two produce a voice**: `mattrickard.com`
(one distinct entry byline → the single-row branch) and `thorstenball.com`
(`feed_declared`).

Both errors came from reading the feeds and not reading the consumer. The probe
measured what the *publisher* emits, which is real, and section 5 asserted what
the *pipeline* would do with it, which was not measured. Rule 9's question —
what reads this, and where — applied to bylines rather than to columns.

### 3 · swyx.io has a terms document, and it permits this

Not checked by the probe at all; found during the seating pass by searching the
robots-advertised sitemap. `https://swyx.io/digital-garden-tos`, "Digital Garden
Terms of Service". Read in full (7,845 chars) and searched for crawl, scrape,
automated, robot, index, store, dataset and training clauses: **there are none.**
What it does say is *"You're welcome to quote, with attribution and a link back
here"*, which is the model this project publishes under, and *"I don't waive
copyright for commercial purposes"*, which bites on monetization.

It describes itself as "not-legally-binding", so it is the author's stated intent
rather than a licence. It is still the strongest consent any feed in the contract
has, and swyx.io is the **first and only row with `terms_document_read: true`**.

The other five were searched in three places — robots-advertised sitemap, front
page markup, and eight conventional paths — and found nothing.
`maggieappleton.com/colophon` returns 200 and **is not a terms document**: it was
read, and it is a build-and-typography colophon with no licence, no copyright
grant and nothing about automated retrieval.

⚠ **The terms-page matcher has a high false-positive rate and it is not a gate.**
It flagged `fast.ai/posts/2020-03-31-tech-policy-govt.html`,
`mattrickard.com/bizarre-open-source-licenses` and
`maggieappleton.com/transcopyright-dreams` — all article slugs containing
"policy" or "licence". One true positive in six hosts. Usable to *find candidates
a person then reads*, never to conclude anything by itself.

### 4 · The same-host guard, checked across full feeds rather than ten entries

Section 3 reports on-host ratio 1.0 for all six, over **ten entries each**. That
is not the same claim as a clean feed, which is exactly why
`sebastianraschka.com` was a problem — it syndicated beyond its first page.

Re-checked 2026-09-21 across the **full window of all eighteen seated feeds**:

```
18 feeds, 1,042 entry links, 0 off-host.
```

The guard has not become relevant, on any feed, at full depth.

### And one thing the write-up got right for a reason worth keeping

`resolves to exactly one` being the wrong ranking criterion was flagged in
section 4 as "the pair is the finding, not either one", before anything had been
measured. Issue #375 then measured it: multi-model documents are productive
43-47% of the time against 18% for single-model, and 58% of ten-plus-model
documents produce claims about two or more models. The ruling now ranks on
naming. `minimaxir.com` at 9/10 is the strongest of the six.
