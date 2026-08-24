# What the never-calibrated weights actually select

**`specificity_score` rewards numbers, links and version names — artifact
density. The four claims already stored are four for four relayed vendor copy.
So the selector selects for what the extractor then over-reads, and the two
failures compound rather than sitting side by side.**

The sharpest single number: `oqocfjv`, the only first-hand capability observation
in its thread, **falls from rank 3 to rank 8 of 195** when the selector is
*fixed* — not on anything about it changing, but on five competitors each gaining
`+0.15` for a version token it does not carry.

*Engineer 1 · 2026-08-21 · this is a finding about the weights and it needs both
lanes. It is not something to fix here.*

---

## 1 · The weights, and what they have never had

`contract/harvest.yaml`, in its own words:

> ⚠ **PROVISIONAL · INTRA-CHANNEL ONLY · NEVER CALIBRATED**
>
> A weight in a contract file with no caveat reads as a decision somebody made.
> Nobody made these. They are five judgement calls […]
>
> **THE COMPOSITE MAY NOT COMPARE ACROSS CHANNELS. EVER.**

And on why nothing has been measured:

> There is no corpus labelled for specificity to fit them against.

The five components, from `collect/triage/specificity.py`:

```
has_error_strings   highest — a machine-emitted failure is the one signal a
                    human cannot produce by having an opinion
has_numbers         "the difference between 'it was slow' and 'p95 was 4.2s'"
has_code            a repro, a config, or a traceback someone pasted
names_version       necessary for attribution and cheap to satisfy
has_conditions      lowest, and the weakest detector of the five
```

Every one of those is a **property of the artifact**, not of the writer's
relationship to what they are describing. That is the whole finding, and it was
not visible until something was measured against a real thread.

---

## 2 · What they select, measured

One thread — `t3_1u1b22l`, 195 comments, coverage 0.238. The five the selector
picks, with what earned them their score:

| id | score | components | what it is |
|---|---:|---|---|
| `oqoc844` | 3.3613 | has_numbers, has_code, names_version | *"Edit: This is from blog: * On …"* — **relaying the blog** |
| `oqocu7n` | 1.9211 | has_code, names_version | *"for anyone asking about what happens after june 22 / this is …"* — **relaying** |
| `oqorjbe` | 1.8130 | has_numbers, names_version | *"Fable 5 on med is cheaper than Opus 4.8 on xhigh and gives 10%+ better results on SWE-Bench"* — **relaying the model card** |
| `oqozyx5` | 1.5648 | has_numbers, names_version | *"Because it requires massive compute…"* — speculation |
| `oqoehi3` | 1.5508 | has_code, names_version | *"It already costs 2x Opus 4.8 (says claude.ai)"* — **relaying pricing** |

**Four of five are relays.** And they are relays *because* of what scores: a
model-card number, a link to the announcement, a version string. Someone
repeating a benchmark carries numbers and a version and a URL. Someone reporting
their own experience carries an adjective.

### The extractor then reads them as reports

Same thread, same corpus, pre-change prompt:

```
C0  "So when Fable's classifiers detect a request related to cybersecurity…"   root, announcement
C1  "more than 95% of sessions involve no fallback at all…"                    root, announcement
C2  "We'll keep refining the safeguards to reduce false positives."            root, announcement
C3  "gives 10%+ better results on SWE-Bench"                                   oqorjbe, model card
```

**Four for four relayed vendor copy. Zero first-hand observations.** Three of the
four match what is already stored in `claim` and counted into a `cell`.

So the two failures are one mechanism seen twice:

```
selection   scores artifact density  ->  prefers relays
extraction  cannot tell relay from report  ->  stores them as reports
```

A fix to either alone leaves the other choosing or reading its inputs. That is
what makes this a finding about the weights rather than about the prompt.

---

## 3 · `oqocfjv`, and why fixing the selector loses it

`scripts/export_thread_contexts.py` was passing an alias list in the wrong normal
form — `anthropicclaudeopus5` against text normalised as
`'fable 5 on med is cheaper than opus 4.8'` — so `names_version` matched **0 of
195** comment bodies. Fixed to registry-derived surfaces, it matches **27 of 195**.

| | five selected | `oqocfjv` |
|---|---|---|
| `names_version` dead (0/195) | oqoc844 oqodw1j **oqocfjv** oqorjbe oqocu7n | rank **3** of 195, selected |
| `names_version` working (27/195) | oqoc844 oqocu7n oqorjbe oqozyx5 oqoehi3 | rank **8** of 195, **not selected** |

`oqocfjv` is *"Our usage isn't getting reset? … (Fable uses up more tokens than a
old Porsche gas)"* — **the only first-hand capability observation in the thread**,
and the only one anywhere in the seven documents.

Its own score does not move: `0.25 [has_numbers]` under both. It says bare
`Fable` with no version token, so the component that was repaired gives it
nothing, while five competitors gain `+0.15` each and step over it.

**It is lost to the selector improving.** That is the measurement, and it is not
an argument for leaving the selector broken.

---

## 4 · What this is and is not evidence for

**It is one thread.** 195 comments, one root, one platform, one launch
announcement. `coverage_ratio` 0.238 — the 195 are what the API returned of 818
observed, and `hidden_children_min` is 623. A launch thread is also the worst
case for relay density: the vendor copy is right there to quote.

So the figures above are: **4 of 5 selected comments are relays, and 4 of 4
extracted claims are relayed vendor copy, in one Reddit launch thread of 195
comments at 23.8% coverage.** Not a rate about Reddit, and not a rate about the
weights in general.

What it *is* enough for is the structural claim, which does not need n: the five
components measure artifact density, artifact density is what a relay carries,
and nothing in the pipeline distinguishes a relay from a report. That holds
whatever the next thread looks like.

**And it is the first time the weights have been measured against anything.**
`harvest.yaml` says there is no corpus labelled for specificity to fit them
against. There is now one thread's worth of evidence about what they select,
which is a different and smaller thing than a calibration — but it is the first
number of any kind.

---

## 5 · For both lanes

This needs `collect/` and `judge/` together and is not being fixed here.

**The question is not what the weights should be.** It is whether *artifact
density* is the quantity the board wants to rank on. The board publishes what
engineers report about capabilities; the selector ranks how many artifacts a
comment contains; those are not the same thing and were never checked against
each other.

Three things that follow, none of them a weight change:

1. **A sixth component, or a separate axis, for first-hand-ness.** `judge/` is
   already going to need `relayed` vs `first-hand` in the extraction prompt and
   possibly on the claim. If that distinction exists claim-side, `collect/` could
   rank on it — but only after something can label it, which is what the baseline
   set is for.
2. **`names_version` is doing attribution work inside a quality score.** It is
   the component that cost `oqocfjv` its place, and `f_specificity` in
   `judge/vet/weight.py` has the same problem from the other end — see
   `docs/measurements/inherited-subjects-and-family-claims.md` §3. Two factors
   pricing "did they name a version" in two places, neither calibrated.
3. **`specificity_score` is NULL on all 64 `document` rows.** Nothing writes it;
   `collect/ops/chain.py:434` names the unimplemented `triage` stage as starving
   it. So the column and the selector are two independent computations of the same
   quantity and only the selector runs. Whatever is decided above has to land in
   one place, not two.

**Do not act on this before the baseline is labelled.** The whole point of
§2 is that the selector and the extractor fail toward the same bias, and the only
way to tell a fix from a re-tuning is a set that says which readings were correct.
`fixtures/golden/extraction-reading-baseline--unlabelled.jsonl` is that set.
