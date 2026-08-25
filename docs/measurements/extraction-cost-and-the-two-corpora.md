# Extracting everything stored: $0.93, and GitHub is 76% of it on 13.5% of the units

**Cost first, per corpus, with the medians beside the rates so nobody can average
them again — including me.**

*Engineer 1 · 2026-08-24*

---

## 1 · The corpora, kept apart

```
corpus       n      chars      median   chars/token   input tokens
blog       120   1,075,511      6,007      5.83           184,478
github      53   1,770,343     22,813      2.87           616,844
reddit     190      32,809         94      5.83             5,627
                                                        ---------
                                                          806,950
```

**Which ratio each corpus gets, and why:**

- **blog and reddit -> 5.83.** Prose. The ratio was measured on Reddit and
  link-blog prose and these are that corpus.
- **github -> 2.87.** An issue body is largely code, stack traces, logs and
  config dumps, and the 2.87 figure was measured on exactly that kind of text.
  Using 5.83 here would understate GitHub's token count by 2.03x.

**The medians are the reason the corpora must not be pooled.** 6,007 against
22,813 against **94** is a 240x spread between the largest and smallest median.
Any figure averaged across them is a figure about whichever corpus has the most
rows, which is Reddit — and Reddit is 4% of the characters.

I made this exact error one document ago, pooling 119 blog documents at median
6,054 with 196 Reddit comments at median 95 and reporting the average as "prose".
The medians are printed here so the next reader cannot repeat it without seeing
them.

## 2 · The cost

```
input   806,950 tokens  ->  $0.2421   at $0.30/M
output  273,700 tokens  ->  $0.6843   at $2.50/M   <- ESTIMATE, see below
                            -------
TOTAL                       $0.9263

EXTRACTION_DAILY_BUDGET_USD = $1.00
```

**One full pass over everything stored fits inside one day's budget, with 7%
headroom.**

**The output half is an estimate and it is 74% of the cost.** 700 tokens per unit
x 391 units, and that per-unit figure is not measured on this corpus. The
corroboration is independent and close: the repository's own measured extraction
cost is **$0.00208 per thread**, which over 391 units is **$0.81** against my
$0.93. Two routes within 15% of each other is worth more than either alone, and
neither is precise enough to plan a budget to two decimal places.

**The input half is not an estimate** — it is a character count times a measured
ratio.

## 3 · GitHub is 76% of the cost on 13.5% of the units

```
                units      input tokens
github        53 (13.5%)   616,844 (76.4%)
blog         120 (30.7%)   184,478 (22.9%)
reddit       190 (48.6%)     5,627 ( 0.7%)
```

Two multipliers compound: GitHub documents are 3.8x longer than blog documents by
median, and they tokenise at 2.03x the rate. **So the cheapest corpus by document
count is the most expensive by a wide margin**, and any future decision to
restrict extraction should be taken on tokens rather than on documents.

**Reddit is essentially free to extract** — 190 units for 0.7% of the tokens —
which is a point in favour of extracting it even though §the-signal-group
measured its signal rate at 0.51%. Cheap and low-yield is a different decision
from expensive and low-yield.

## 4 · What is not readable, named rather than skipped

```
missing    27   the pre-sweep github documents, whose payloads were written by
                the 2026-08-20 harness run to a store this machine does not have
malformed   1
```

**The 53 readable GitHub documents are the ones this session's sweep stored**,
which is also why they carry `harvest_run_id` and the older 27 do not. So the
extraction population and the provenance population are the same set, by
accident rather than design, and that will stop being true the moment the 27 are
recovered.

## 5 · A third figure for GitHub document size, and they measure different things

This is the third number this week for "how big is a GitHub document", and the
first two were mine:

| figure | what it actually measures |
|---|---|
| **2,228** — `sieve.py` docstring | the **sieve text**: title + body from the *search response*, on an older corpus |
| **65,502** — my n=1 confirming fetch | one **fetched issue payload**, a tail sample |
| **22,813** — this measurement, n=53 | the median **stored payload**, which is the fetched issue including its JSON envelope |

**They are not in conflict; they are three different objects.** A search result
carries a truncated body, a fetched issue carries the full body plus metadata.
My correction two documents ago — *"the 2.2k figure is right for GitHub too"* —
**was itself over-corrected**: 2,228 is right for what the sieve reads and wrong
for what the extractor reads, and the extractor is what this cost model is about.

So: **the sieve cost model should keep 2,228** (it sieves search results) and
**the extraction cost model uses 22,813** (it reads stored payloads). One number
each, and neither travels to the other.

## 6 · The blog sweep, run and saturated

```
feeds                 9
articles            105
already_present     104
documents             1   <- new
author_rows          14
```

**The blog feeds are exhausted at the current feed list.** 105 articles offered,
104 already held. One new document from `engineering.grab.com`, whose template
block (`Join us`) was stripped on all 10 of its pages.

Two feeds returned **0 articles** — `netflixtechblog.com` and
`medium.com/airbnb-engineering` — and three are marked *"unverified: no page has
been examined"* for template stripping. Both are coverage facts rather than
failures, and neither is silent.

**There is no Reddit sweep to run.** `ops` exposes only `sweep-github`;
`write_reddit_thread.py` takes one thread and `unfiltered_sweep.py` writes to a
directory for calibration rather than to the database. The Reddit corpus is the
190 comments already held, and adding to it needs a path that does not exist yet.
Not built here, because a sweep invented in passing is how the last four defects
got in.
