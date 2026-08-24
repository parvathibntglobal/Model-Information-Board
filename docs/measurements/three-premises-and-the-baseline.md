# Three premises, none of which held — and the near-miss was mine

**Written 2026-08-24.** Three findings arrived with numbers attached and an
instruction to act on them. All three were checked before acting; none holds.
One of the three was my own error from the previous report, and it is the one
that would actually have cost something.

*Engineer 1*

---

## 1 · The sleep fix: there is nothing to fix, in either shape

Asked which shape I took — the sieve loop not holding the limiter, or the limiter
distinguishing a fetch from a local call. **Neither, because the limiter is
already only ever called immediately before a network request, in both
adapters.**

```python
# collect/adapters/github.py
def _get(self, url, *, params=None, search: bool):
    (self._search if search else self._rest).wait(url)
    return self._client.get(url, params=params)          # next line

# collect/adapters/blog/fetch.py:354
self._limiter.wait(current, min_interval=self._robots.min_interval(current))
try:
    response = self._client.get(current, ...)            # next line
```

Those are the only two `wait()` call sites in the repository. The sieve loop —
`for hit in hits: request.sieve(hit.sieve_text)` — reaches neither.

**The general fix is the better design and I would have taken it**, at similar
cost, if there were a local call site to distinguish. There is not: the
distinction is already structural rather than conditional, which is the stronger
form of it. A `is_local` flag on `wait()` would be a parameter that is always
False.

**The 95% sleep is real and it is the rate limit.** `SEARCH_INTERVAL` is 2.222s,
from GitHub's documented 30 searches/minute at 0.9 headroom. 4,944 requests
cannot be issued faster than that. The lever is fewer requests, not less
sleeping — which is what §4 is about.

## 2 · The proposer: the prose forms are withheld on purpose, and correctly

The claim: *"24 of 25 have attested prose forms already in
`observed-surfaces.json`, and the artifact emits mechanical variants instead."*

`fixtures/openrouter/observed-surfaces.json` is real — 449 rows, 147 models — and
the proposer already reads it, through a `--surfaces` flag that
`docs/measurements/tracked-set.md:318` documents as the way the live artifact was
generated. So the file is not an unused measurement.

**Measured against the 20 unseated attested models:**

```
with a prose form in the file : 10 of 20
without                       : 10 of 20
```

Not 24 of 25. And the split that matters is not have/have-not — it is the
**verdict** on the forms they have:

| model | prose form | mentions | verdict |
|---|---|---|---|
| `anthropic/claude-fable-5` | `claude 5` | 11 | **attested-gap-ambiguous** |
| `openai/gpt-5.6-sol` | `gpt 5.6` | 207 | **attested-gap-ambiguous** |
| `openai/gpt-5.6-luna` | `gpt 5.6` | 207 | **attested-gap-ambiguous** |
| `qwen/qwen3.6-27b` | `qwen3.6` | 113 | **attested-gap-ambiguous** |
| `google/gemini-3.6-flash` | `gemini 3.6 flash` | 13 | resolved |
| `openai/gpt-5-pro` | `gpt 5 pro` | 4 | resolved |

**Only 2 of the 10 are unambiguous.** The rest name more than one model:

```
'gpt 5.6'   -> 6 models   gpt-5.6-{luna,luna-pro,sol,sol-pro,terra,terra-pro}
'qwen3.6'   -> 5 models
'claude 5'  -> 3 models   fable-5, opus-5, sonnet-5
'gemini 3.5'-> 2 models
```

**`claude 5` is the case worth naming.** Seating it as `claude-fable-5`'s primary
would collide with `anthropic/claude-opus-5`, which is *already seated* — every
`claude 5` mention would attribute to whichever seat resolved first. That is the
`gpt-5.6`-quote-on-the-`gpt-5`-page defect, which this repo has already written
up once.

So the proposer is not emitting id forms *instead of* available prose forms. It
is declining to emit prose forms that do not identify a model, which is exactly
what the `attested-gap-ambiguous` verdict is named for. **49 of 449 rows carry
that verdict and they hold 1,530 of 10,255 mentions — 15% of all attested
mentions sit on surfaces that name more than one model.** Emitting them would
raise coverage and corrupt attribution, and rule 6's display side is that a wrong
cell renders as a phrase somebody can argue with.

**It is not the loader, not the rule, and not the proposer.** It is that most of
what people write does not name one model — which is the same finding as
§the-fifty-seats, arriving from a different direction.

## 3 · The re-seat: 40 of 40 already, and "4 to 29" cannot be verified as asked

Asked to verify against `model_alias` **with `search_eligible` set**.
`search_eligible` is not a column on `model_alias` — the columns are `id`,
`surface`, `normalized`, `variants`, `provider_hint`, `model_version_id`,
`family`, `specificity`, `valid_from`, `valid_until`, `confidence`,
`created_at`. `collect/ops/sweep.py` states the reason: eligibility *"is
expressed as a non-empty `variants` array"*.

Verified the way the sweep itself does it, `seated_variants(conn)`:

```
seated models              40
  plan >0 requests         40
  plan  0 requests          0
daily requests, 5 repos  3,216
of the 40, seed models      5
```

**It was 40 before this session and it is 40 now.** There is no 4, and no 29 to
reach. Nothing was re-seated because regeneration adds no entries — see below.

## 4 · What the near-miss actually was, and it was mine

The instruction was to record that *"the baseline nearly went out over 4 models,
and the reason was a proposer emitting id forms while the prose forms sat
measured in a file."* **That is not what happened, and the real version is worse
because it was not caught by a guard — it was caught by re-running my own work.**

In the previous report I claimed regenerating the artifact would **revoke 30 of
the 41 live review fingerprints**, with 23 returning `INCOMPLETE`. On that basis
I said seating was blocked and recommended a separate additive artifact.

Re-run through the documented CLI, with `--surfaces`:

```
py -3 -m collect.cli registry propose-aliases \
    --surfaces fixtures/openrouter/observed-surfaces.json \
    --mention-floor 20 --launch-window-days 30

59 tracked of 342.  41 by mentions, 19 by launch window.
unchanged : 41 of 41
MOVED     : 0
```

**41 of 41 unchanged. Zero moved. Regeneration is safe and always was.**

My "30 moved" came from calling `propose(models, observed)` in Python with
`observed` built from a live corpus scan through `build_population` — **derived
surfaces**, not the measured prose forms in the file the CLI reads. I fed the
proposer the wrong input and reported its output as a property of the proposer.

**This is the second denominator error in two reports.** The first was assuming
100 items per query when the recorded sweep says 18.9, which turned a 3.2-hour
sweep into a 21-hour one and put a sieve optimisation at the top of a priority
list where it belongs third. Both had the same shape: **a figure produced from an
input I chose and did not state.** The measured value was right; the population I
drew it from was mine and invisible.

Rule 7 is written for figures that reach an argument. Both of these reached one.
The check that catches them needs no suspicion — *what input produced this, and
was it the one the system uses?* — and in both cases the answer was one command
away.

**What it would have cost:** the 30-of-41 claim recommended building a parallel
artifact and manifest to avoid a revocation that does not occur. That is real
work, on a file whose whole purpose is being the single audited record, and the
duplication would have been permanent.

## 5 · What was built

The two things at the top of my own order, both preconditions
`contract/harvest.yaml` named on 2026-08-14 and neither of which existed.

**`last_swept_at` is now written.** `mark_swept()` stamps a model when its whole
plan has been issued, and **only** then — a model the budget stopped short of
keeps NULL, because the column answers "when was this last covered" and a
half-covered model has no honest answer to give (rule 6). A failed stamp is
logged and does not roll back retrieval that already committed.

**The sweep resumes instead of restarting.** `seated_variants` was
`ORDER BY mv.canonical_id`; it is now
`ORDER BY MIN(mv.last_swept_at) ASC NULLS FIRST, mv.canonical_id`. Verified
against the live registry: stamping the two alphabetically-first models moves
them to the back of the order, so night two starts where night one stopped.

This is what makes a 40-model baseline reachable at all. Alphabetically, 3,216
daily requests against a 900 cap covered the first ~11 models **and the same 11
every night** — `z-ai/*` was not late, it was unreachable. The 2026-08-20 record
is that defect already having happened: its three swept models were its three
alphabetically-earliest seats.

`SweepReport.marked_swept` is reported separately from seats swept, because they
differ when a stamp fails and only one is what a fortnight comparison joins on.

**Tests:** `run_sweep` had none. The order is pinned as SQL rather than
behaviour, because with every timestamp NULL the two orderings are behaviourally
identical and a revert would pass every other test in the suite.

## 6 · The baseline, and the pre-registration it inherits

**The baseline is 40 models**, and with the resume order it is reachable across
nights rather than being one alphabetical prefix. Three nights at the 900-request
cap covers it; each model carries its own `last_swept_at`, so the fortnight
comparison joins on a per-model date rather than on a single sweep timestamp.

**This changes one line of the pre-registration in
`two-arm-sweep-preregistration.md` §7 and no others.** That document said a
result where *"neither sweep completes its population"* must be reported
inconclusive, because the comparison would be between two alphabetical prefixes.
**That failure mode is now removed at the source** — coverage is no longer
determined by name — so a sweep that does not complete in one night is a partial
population with dates attached rather than a biased sample.

Everything else stands unchanged: the thresholds, the decision table, the
`>= 3 stored quote-verified claims` bar, and the confound that blog and Reddit
sweeps grow the corpus independently so **sweep 2 must attribute each new claim
to the source that retrieved its document.**

**Still open, unchanged and still third:** the document-size question. 192.5
minutes at Reddit-sized documents against 389.8 at 48k, and all 27 GitHub
payloads resolve `missing` from this machine, so it needs a run where the store
lives. It decides whether the sieve union is worth 5% or 53%, and nothing else
depends on it.
