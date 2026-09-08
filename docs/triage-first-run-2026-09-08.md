# Triage's first run against the database

**2026-09-08.** E4's six gates have never touched the corpus. `Stage('triage')`
carried `run=None`, `document.triage_verdict` was NULL on all 6,502 rows, and
every survival figure this project has quoted — including the **82.8%** in
`collect/triage/gates.py`'s own docstring — came from a script building
`Document`s by hand off a JSONL export. This is the first figure that is about
the corpus.

Runs: `docs/measurements/triage-first-run-2026-09-08.json` and
`docs/measurements/triage-github-subject-counterfactual-2026-09-08.json`.
Reproduce with `scripts/triage_stored_corpus.py`. Population fingerprint
`b5744297e9210497` — 342 polled `model_version` rows plus the seed's declared
surfaces.

**Nothing was written.** The run is a dry run; see §5.

---

## 1 · The distribution, per source

**Denominator is TRIAGED, never ELIGIBLE**, and the gap is 1,492 rows — not a
rounding difference. A document whose payload this host cannot read was never
gated, and putting it in a survival denominator reports our coverage as the
corpus's quality (rule 7).

| source | eligible | triaged | kept | dropped | survival | never gated |
|---|---|---|---|---|---|---|
| github | 3,382 | 3,373 | 1,447 | 1,926 | **42.9%** | 9 |
| reddit | 2,999 | 1,517 | 1,362 | 155 | **89.8%** | 1,482 |
| blog | 121 | 120 | 51 | 69 | **42.5%** | 1 |
| **total** | **6,502** | **5,010** | **2,860** | **2,150** | **57.1%** | **1,492** |

Drops by gate, over the 5,010 triaged:

| gate | dropped | share of triaged |
|---|---|---|
| `no-resolvable-entity` | 1,578 | 31.5% |
| `too-short-no-artifact` | 618 | 12.3% |
| `out-of-window` | 346 | 6.9% |

**57.1% is an UPPER BOUND and is not comparable to the 10–15% estimate.** Two
gates could not run at all, so every document they would have dropped is
counted as kept. **Since measured: by at least 4.8 points.** The bot list would
drop 149 of the 2,860 kept (54.1%) and an `is_self_post` column would drop 92
(55.2%); both together, **52.3%**. Neither needs new data. A language gate can
only lower it further and its size is unmeasurable until a detector exists -
`docs/the-three-dead-gates-2026-09-08.md` has the costs and the reasoning. And the estimate's population is *documents retrieved from the
sources we sweep*; this corpus was retrieved by queries containing model names,
so it is pre-filtered for exactly what the entity gate tests. The two numbers
answer different questions.

**Reddit's 89.8% is the figure to distrust most**, and not because it is high.
1,482 of its 2,999 rows were never gated - 1,234 payloads absent from this
host's raw store, 248 present and not prose - and the loss is not random:
**every absent payload belongs to a `not_recorded` row and none to a
`run_recorded` one**, 1,234 of 1,492 against 0 of 1,507. So the `not_recorded`
half contributes **10 documents of 1,517** to that denominator, and 89.8% is to
three figures the survival of the `run_recorded` population alone - which was
retrieved by queries containing model names, i.e. pre-filtered for the gate that
drops 31.5% of everything else. Doubly selected, and written up separately as a
data finding: `docs/for-the-team-reddit-payloads-absent-2026-09-08.md`.

## 2 · Which gates could not run — plainly

| gate | ran on | dropped | could not run | nothing to run on |
|---|---|---|---|---|
| `wrong-language` | **0** / 5,010 | 0 | **5,010** | 0 |
| `pure-link-post` | **0** / 5,010 | 0 | 0 | **5,010** |
| `too-short-no-artifact` | 5,010 / 5,010 | 618 | 0 | 0 |
| `no-resolvable-entity` | 5,010 / 5,010 | 1,578 | 0 | 0 |
| `out-of-window` | 3,411 / 5,010 | 346 | 0 | 1,599 |
| `known-bot` | **0** / 5,010 | 0 | **5,010** | 0 |

**Three of six gates ran on nothing at all**, and the three have different
remedies, which is why they are not one line:

- **`wrong-language` — UNAVAILABLE, 5,010.** No detector is installed and none
  is declared in `pyproject.toml`; adding one is a dependency decision.
  `document.lang` is written as of 2026-09-08 for platforms that declare one,
  but it is NULL on all 6,502 stored rows — so **even with a detector this gate
  has no input on the existing corpus**, and the input cannot be back-filled
  without re-reading every payload.
- **`known-bot` — UNAVAILABLE, 5,010.** The detector was built 2026-09-07;
  `contract/bots.yaml` does not exist. It reports UNAVAILABLE *per source*, so
  this count shrinks platform by platform as each is curated rather than
  all-or-nothing. Proposed in
  `docs/proposals/for-engineer-2-the-bot-list.md` — measured there: 7 GitHub
  accounts carry `bot` in the login with no `[bot]` suffix, the busiest at 33
  comments.
- **`pure-link-post` — NOT_APPLICABLE, 5,010.** Permanent, and a different
  thing: `is_self_post` and the poster's own commentary are **not columns on
  `document`**, so no stored row can answer this. Nothing to build in triage;
  it needs a column or it stays unanswerable. On the 1,297-post hand-built
  corpus this gate was the *largest* single dropper at 144 — so its absence
  here is not a small hole.

`out-of-window`'s 1,599 NOT_APPLICABLE is the honest kind: no matched surface
has a known owner, or the owners disagree on the window flag. A property of the
document, not of the build.

## 3 · The HN subject join — reachable, no new storage

**The root is reachable from the comment row. The adapter stores nothing new.**
`document.thread_root_id` already points at the root's own `document` row, and
that row already carries a `text_ref`, so the subject text is:

```
thread_root_id → document.text_ref → raw store → the platform's prose function
```

Cost, measured: **one extra raw-store read per distinct thread root, not per
document**, plus one `LEFT JOIN` on the primary key. `_root_text` caches per
root within a run, so reads are the distinct count.

| source | children | root id set | root row resolves | dangling | distinct roots | reads per child |
|---|---|---|---|---|---|---|
| github | 2,016 | 2,016 | **2,016** | 0 | 584 | 1 : 3.45 |
| reddit | 1,420 | 1,420 | **0 then 1,420** | **1,420 then 0** | 24 | — |
| blog | 0 | 0 | 0 | 0 | 0 | — |
| hackernews | **0 documents stored** | | | | | |

### Two things that fell out of measuring it

**A defect, REPAIRED 2026-09-08: Reddit's `thread_root_id` resolved to
nothing, 1,420 of 1,420.**
Two writers use two conventions for one column:

```
reddit_write.py    thread_root_id = 't3_1v6a104'          bare fullname
documents.py       thread_root_id = 'reddit:t3_1v6a104'   <source>:<id>
```

Re-joined with the prefix added, all 1,420 resolve — and `parent_id` is the
same, so 2,840 stored references. **The rows were there; the references were
not.**

Repaired in `contract/migrations/20260908T1100_reddit_thread_link_prefix.sql`,
applied to staging 2026-09-08: Reddit now resolves 1,420 of 1,420, GitHub
untouched at 2,016 of 2,016, and the forward path fixed in
`reddit_write.py:_document_ref` so the next sweep cannot reintroduce it.

It is still why `root_unresolvable` is a counter with a name rather
than a silent NULL — a join that read a dangling id as *"this document has no
subject line"* would report an absence we caused as one we found, on the
platform where the count is largest.

**And there is no HN corpus to prove the join against.** Staging holds github,
reddit and blog and **not one `hackernews` row** — the 2026-09-07 smoke run
wrote to the disposable local instance, which has since been reset. So the join
is exercised in `tests/test_triage_stored.py` against a real database, on rows
that file inserts: 15 tests covering inheritance, the control with the join
disabled, an unresolvable root, an unreadable root, a root that is its own
document, the per-thread cache, and scope.

One of those tests exists because a fixture found something. A **link
submission's anchor row is eleven tokens and is dropped on length — and its
children still inherit its subject.** The join reads the root's *text*, never
its *verdict*, and that has to stay true: the highest-signal HN thread in the
measured corpus was a bare GitHub link at 678 points whose evidence was entirely
in its comments. A subject gate that refused to inherit from a dropped root
would discard exactly that thread.

## 4 · The counterfactual: GitHub is in the same position

The ruling scoped thread-level subject to Hacker News. **GitHub's 2,016
comments have the same shape** — a comment's payload is its `body`, and the
issue title lives in the parent row — and now there is a number rather than an
argument:

| GitHub, 3,373 triaged | kept | survival | `no-resolvable-entity` drops | inherited |
|---|---|---|---|---|
| ruling as scoped (HN only) | 1,447 | 42.9% | 1,511 | 0 |
| widened to GitHub | **2,497** | **74.0%** | **123** | 1,388 |

**+1,050 documents kept; `no-resolvable-entity` falls by 1,388.** Reproduce with
`--subject-sources hackernews,github`, which refuses to combine with `--write`:
a counterfactual's verdicts are not the ruling's, and nothing on the row would
say which run wrote it.

**The ruling was not widened.** `SUBJECT_FROM_THREAD_ROOT` is
`frozenset({"hackernews"})` and a test pins it, so widening fails a test rather
than passing silently. This is the input to that decision, not the decision —
and the argument against widening is unchanged and worth restating: 1,388
documents would reach the extractor with a subject from outside their own text,
every one of them labelled `QUOTE_NAMES_NOTHING`, and the weighting call on that
label is Engineer 2's.

## 5 · What was written: nothing, and what the write would do

The run is a **dry run**. `DATABASE_URL` is the shared staging database and
CLAUDE.md's convention is that a write session is announced first. One command,
when you want it:

```
.venv\Scripts\python.exe scripts/triage_stored_corpus.py --write
```

**It writes `triage_verdict` and `filter_reasons`, and deliberately not
`document.status`.** Rule 8 is the whole reason, and it is not caution:

- `status` is the **gate action**. `judge/` filters on `status = 'kept'` (there
  is an index for exactly that predicate) and `judge/pages/filtered.py` renders
  the rest.
- Two of six gates cannot run. Writing `status = 'filtered'` on 2,150 rows on
  the strength of four gates would drop them out of `judge/`'s view, and **a
  false positive would be invisible** — an absence we caused reading as one we
  found, rule 4 one stage earlier.
- `triage_verdict = 'dropped'` records the same judgement where somebody can
  count it, argue with it, and **measure its error rate against the labelling
  pool**. Promotion to `status` is one-way and goes on that evidence.

So `document.status` still has no writer. The chain's `starves` text says that
rather than reading as wired.

## 6 · What this run makes possible, and one thing it does not fix

`triage_verdict` now has a numerator and a denominator, so **alert 2's 14-night
burn-in can start counting** — there was no baseline to compute σ against
before, because nothing had ever produced a first night.

It does not fix the 1,492 never-gated rows. 1,244 payloads are **missing from
this raw store with no tombstone**, which `collect/rawstore.py` logs as an NFR-4
concern in its own words: *"rebuild-from-raw is no longer guaranteed. This is
corruption or a bug, not a takedown."* That is a separate finding, it is loudest
on Reddit, and this run is the first thing to have counted it per source.

---

### Files

| | |
|---|---|
| `collect/triage/run.py` | **new** — E4 over the stored corpus; the join, the prose dispatch, the counters |
| `collect/triage/store.py` | `registry_population` extracted so one construction serves both callers |
| `collect/ops/chain.py` | `Stage("triage", run=_triage_stage)` — no longer `run=None` |
| `contract/column_states.yaml` | `triage_verdict` `unwired` → `read`; `document.lang` `write_only` → `read` |
| `scripts/triage_stored_corpus.py` | **new** — the run, the report, the counterfactual flag |
| `tests/test_triage_stored.py` | **new** — 15 DB-backed tests on the join |

Two contract entries moved, and the discovered-state guard is what moved them
rather than a decision I made:

- **`triage_verdict`: `unwired` → `read`.** Its `known_gap` said *"E2's lane —
  triage is unwired"*, which was true and was the dangerous half: a `known_gap`
  **exempts an entry from the mismatch check**, so the column could gain its
  first writer and nothing would notice. That is exactly what happened to
  `filter_reasons` one column earlier, for the same reason. The gap is removed
  rather than reworded. `document.status` stays unwritten, and its `starves`
  text now says that is deliberate rather than pending.
- **`document.lang`: `write_only` → `read`.** Un-reserved as `write_only` in the
  morning and read by the triage runner's `SELECT` hours later — the guard
  caught the second change on the same day as the first. **Read is not acted
  on:** the value reaches `wrong_language`, which ran on 0 of 5,010 documents.
  It is `read` by the audit's definition (a SELECT in this repository), not by
  consequence, and the entry says so.

One bug found by the first run and fixed: `extract_article_text` takes **bytes**
and the other seven extractors take **str**, so handing it `get_text()` refused
all 120 readable blog documents through `_require_bytes`. They landed in
`not_prose` — a real count with a cause that was ours, not the corpus's. The
extractor table now carries a `wants_bytes` flag rather than sniffing at the
call site.
