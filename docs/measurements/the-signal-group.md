# The signal group: 102 of 207 terms have never fired, and one term is a third of all hits

**Measured offline against the 32,723 candidates in `_sweep_store`** — the stored
search responses from both sweep runs. No network, no re-retrieval, and the
matcher is `sieve._pattern_for`, the same object the sieve uses.

*Engineer 1 · 2026-08-24*

---

## 1 · Which terms fire

```
distinct signal terms in contract/queries.yaml   207
  fired at least once                            105
  NEVER fired                                    102   (49.3%)
candidates matching >=1 signal term            5,317 of 32,723  (16.25%)
```

**Yes, it is the same handful every time.**

```
truncat                2574   34.2% of all firings
hallucinated            479    6.4%
infinite loop           391    5.2%
gets stuck              299    4.0%
no regression           242    3.2%
timed out               188    2.5%
times out               186    2.5%
no timeout              179    2.4%
good enough             175    2.3%
unparseable             162    2.2%

top 3  = 45.8% of firings
top 5  = 53.0%
top 10 = 64.8%
```

**One term — `truncat` — is over a third of the entire signal group's output.**

## 2 · The 1.3% and the 16.25% are different questions, and both are right

The sweep reported `signal 302/23,160 (1.3%)`. This document reports 16.25%.
**Neither is wrong and they must not be quoted interchangeably** (rule 7):

| question | figure |
|---|---|
| does **any** of the 207 terms appear anywhere in the candidate | **16.25%** |
| does **this request's own entry's ~8 terms** appear — what the sieve actually asks | **0.39% median across entries** |
| the sweep's observed per-request rate, weighted over 459 requests | **1.3%** |

Entries carry a **median of 8 signal terms** (min 6, max 13), so a single request
is asking a far narrower question than the vocabulary as a whole. The 1.3% is the
weighted middle of the per-entry spread, and that spread is the finding:

```
code.editing_diff_fidelity:negative        9.05%
tool_calling.long_chain_reliability:neg    2.73%
substitution:positive                      2.40%
...
context.effective_window:positive          0.07%
code.generation:positive                   0.03%
extraction.faithfulness:negative           0.00%
format.structured_output:positive          0.00%
tool_calling.schema_accuracy:positive      0.00%
```

**Three entries are at exactly 0.00% across 4,000 candidates.** And
`context.effective_window:positive` — the entry I committed hardest on — is at
0.07%, which is why its one stored document came from the *negative* stance.

**Positive stances are systematically worse.** Four of the worst five are
positive; the best is negative. Complaints are terse and quotable; praise is
essay prose. That asymmetry matters because the four silent-failure capabilities
depend on positive evidence — `contract/harvest.yaml` is explicit that for a
silent failure *"nobody complained" is not evidence, because you would not find
out.*

## 3 · It is not the exclusion set, which was the obvious suspect

Measured, because a GitHub issue is largely fenced code and I expected this to be
the answer:

```
signal term present in title+body            17.61%
... still present after ALL exclusions       14.97%
lost to fenced code / blockquotes / logs      15.0% of those that had one

surviving prose as a fraction of the document:
  median 78.5%   mean 73.2%   p10 39.0%
documents >=90% excluded content:  2.6%
```

**The exclusion set costs 15%, not 90%.** The median GitHub issue is 78.5% prose.
So the two false positives that motivated the exclusions — `accurate` inside a
Google marketing blockquote, `accurately` inside a Python prompt string — were
bought at a price this measurement says is small. **The exclusions are not the
constraint and should not be relaxed.**

## 4 · What fires versus what never fires, and the shape is unmistakable

**Fires** — terse, mechanical, the language of a bug title:

```
truncat · hallucinated · infinite loop · gets stuck · timed out · times out
unparseable · invalid json · invalid argument · code fence
```

**Never fires** — 102 terms, and the sample reads as prose:

```
forgets the middle · applied cleanly · compiled first try · compiled cleanly
didn't invent · faithful to the source · declined a perfectly · full window without
drifted from the format · always picked the right · arguments were correct
correctly returned null · finished all · followed the chain · degraded under load
consistent latency · added preamble · breaks the diff · fell off past
```

`forgets the middle` is in the never-fired list. So is `consistent latency`,
which `sieve.py` already flags as unreachable for a different reason — the
`y`→`ies` stem gap.

**These are two different registers.** An engineer writing an essay says *"it
loses recall past about 80k"*. The same engineer opening an issue titles it
*"context truncated at 128k"*. The vocabulary was written in the first register
and is being asked to retrieve the second.

## 5 · What the terms would need to be for GitHub

Not a proposal to `contract/queries.yaml` — that file is shared and this is a
ruling. `docs/proposals/for-engineer-2-per-platform-signal-terms.md` carries the
argument. The shape, in one line: **an issue reports a symptom with a number, not
an impression with an adverb.**

```
essay register (current)        issue register (what fires, or would)
loses recall                    truncates at · returns empty · drops after N tokens
forgets the middle              ignores the system prompt · context window exceeded
falls apart                     crashes on · stack overflow · exits 1
applied cleanly                 patch applied · diff applied without conflict
didn't invent                   no such field · unknown key · KeyError
```

The four that already fire — `truncat`, `timed out`, `invalid json`,
`unparseable` — are all in the right-hand register already, which is the evidence
that the register is what matters rather than the capability.

## 6 · The baseline: do not complete it yet, and run the nights anyway

**33 models unreached. At the measured 459 requests per 35-minute night against a
900-request cap, and ~64 requests per model, that is 2,144 planned requests
total — roughly 3 more nights**, now that the resume ordering sends the 6 stamped
models to the back of the queue.

**Not as a baseline.** A baseline's only value is being comparable to a later
sweep, and the signal terms are embedded in the rendered queries — change them
and the retrieved candidate set changes, so a later sweep is a different
instrument. **A baseline measured with a vocabulary that is about to change is a
baseline nobody can compare against**, and completing it now would produce
exactly that.

**But run the nights as a measurement**, and the distinction is not a
technicality:

- The per-entry rates in §2 rest on 4,000 candidates and three entries read
  0.00%. **0 of 4,000 and 0 of 30,000 are different findings** — the first is
  consistent with a rate of 1-in-5,000, the second is not. The vocabulary
  decision needs the second.
- 102 never-fired terms is a claim about *this* corpus, which is 7 models and
  overwhelmingly `anthropic/*`. A term that never fires on Claude issues may fire
  on `llama` or `qwen` ones, and the unreached 33 are where that gets tested.
- A measurement run's value does not depend on comparability, so nothing is
  wasted if the vocabulary then changes.

**So: run the remaining nights, label the output a measurement, and do not call
it a baseline.** The baseline is the run that comes *after* the vocabulary ruling,
and it will be worth more for having a settled instrument behind it.

**What I would not do:** finish the sweep, call it the baseline, and then change
the vocabulary — which is the default if nobody decides. That produces a
before-and-after where the instrument moved between the two, and this project has
already retired one figure for exactly that reason.

---

## 7 · Locality is not the explanation, and this is settled by the code path

The proposal was that *"one candidate in six carries a signal term and the
locality window rejects most of them."* **It cannot, and no measurement is needed
to rule it out — `sieve()` says so.**

```python
signal_hits = tuple(t for t in terms.signal if matches(t, prose))
...
if not missing and window is not None and not _within_window(terms, text, window):
    missing.append("locality")
```

`signal_hits` is computed independently and returned as `verdict.signal`. The
window's only effect is to append `"locality"` to `missing`. And `sweep_github`
counts the group flags directly:

```python
for group in ("subject", "topic", "signal"):
    if getattr(verdict, group):
        report.group_hits[group] += 1
```

**So the 1.3% is measured BEFORE the window is consulted.** The window operates
on the subset that already has all three groups — it can only reduce `passed`,
never `signal`. Widening it from 1,200 characters cannot raise a 1.3% group rate.

The docstring is explicit that this separation is deliberate: *"'topic and signal
are too far apart' is a different statement from 'one of them is absent', and
collapsing them would lose the distinction `missing` exists to carry."*

**What the 16.25% versus 1.3% gap actually is**, restated because it has now been
attributed to two wrong causes (the exclusion set, measured at 15%; and
locality, ruled out here):

> **A request asks its own entry's ~8 terms, not the vocabulary's 207.** Median
> 8, min 6, max 13. The per-entry rate is 0.39% median, the best entry is 9.05%,
> and three entries are 0.00%. The 1.3% is the weighted middle of that spread.

**So the two fixes are not comparable in size, and the numbers say which:**

| fix | what it could move | ceiling |
|---|---|---|
| **widen the vocabulary** — more terms per entry, in the register the platform uses | the per-entry rate, 0.39% median | up to the 16.25% the full vocabulary already reaches |
| widen the locality window | `passed`, among candidates already at 1.3% | at most 1.3%, and only the fraction the window currently rejects |

**Vocabulary is the larger fix by an order of magnitude**, and locality is not a
competing candidate — it is downstream of the group that is failing.

## 8 · A correction to my own document-size figure

`sieve.py`'s own docstring carries a measurement I did not have when I wrote
`the-unwind.md` §7:

> *"Blog articles have a median of 8,191 characters against GitHub's 2,228."*

**GitHub's median document is 2,228 characters.** My n=1 of 65,502 was a tail
sample, not a typical one — and the 2.2k figure in the sieve cost model, which I
described as *"measured, but on Reddit thread contexts"*, turns out to be right
for GitHub too and for a reason I had not found.

So the sieve cost model should use ~2.2k, the full-sweep sieve cost is the
**9.4-minute** figure rather than 206.7, and §7's *"it lands nearer 48k"* is
wrong. n=1 licensed less than I claimed, and the check I did not run was grep for
an existing measurement before treating a fresh one as the first.
