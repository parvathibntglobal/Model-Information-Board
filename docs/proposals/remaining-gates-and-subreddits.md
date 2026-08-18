# The three unbuilt gates, and why 10–15% is not reachable

**Report before building. Each gate's blocker is a decision, not code — and the
arithmetic says all three together cannot close the gap from 33.7% to 10–15%.
They get about a third of the way. The target and the measurement are about
different populations.**

*Engineer 1 · 1,925-post unfiltered sweep · 2026-08-18*

---

## 0 · The finding that governs the rest

Measured, on the unfiltered corpus, adding each stage in turn:

| stage | alive | survival |
|---|---|---|
| retrieved | 1,925 | 100.0% |
| built gates (3 of 6) | 648 | **33.7%** |
| + out-of-window | 479 | **24.9%** |
| + specificity floor | 470 | **24.4%** |
| + language *(ceiling)* | ~466 | ~24.2% |
| + known-bot *(ceiling)* | ~458 | **~23.8%** |
| **target** | | **10–15%** |

**Everything E4 specifies, built and run optimistically, lands at ~23.8%.** The
gap to the top of the target range is ~9 points, and there is nothing left in
the stage to spend on it.

The two unbuilt gates are worth **almost nothing on this population**:

- **language: 4 posts (0.2%)** have under 90% Latin letters; **zero** have under
  50%. These are English-language AI subreddits.
- **known-bot: 8 posts (0.4%)** by six name-matched accounts, and at least three
  of those six are humans with bot-ish names.

Out-of-window is the only one with real weight — 169 of 648 survivors, 8.8
points — and §3 explains why that number is available at all today.

### So either the target is wrong, or it is about a different population

The honest reading is the second. **10–15% was written for "raw documents" from
a broad sweep.** This sweep is 11 AI-focused subreddits — the most
survival-friendly population that exists for this pipeline. The entity gate
dropped 62.6% here; on general programming subreddits it would drop far more,
and on r/all almost everything.

Engineer 2 already corrected the docs so the estimate carries a population
(*"within the sources actually swept"*). This measurement is what that
correction was anticipating: **the figure and the target now need to name the
same population before either can be compared to the other**, and they do not.

**Nobody should tune a gate toward 10–15% on this corpus.** Every point between
23.8% and 15% would have to be bought by making a gate stricter than the
evidence supports, and the evidence is that the documents are there.

---

## 1 · `wrong-language` — a dependency decision, and a threshold

Nothing is installed and nothing is declared. `document.lang` is a nullable
column with no writer, so the schema anticipated this and the code never
arrived.

### Options, and the constraint that eliminates most of them

`pyproject.toml` already documents the hazard that decides this: **CI installs
from scratch every run and a laptop does not**, so anything with a compiled
component or a downloaded model drifts between them silently.

| option | pure Python? | model | notes |
|---|---|---|---|
| `py3langid` | yes (+ numpy) | bundled, ~2 MB | fork of `langid.py`. **`trafilatura`'s own optional extra**, so it is already inside our dependency tree's design |
| `langdetect` | **yes**, no numpy | bundled profiles | port of Google's detector. **Non-deterministic by default** — needs a seed set, or the same document classifies differently between runs |
| `lingua` | yes | bundled, ~90 MB | most accurate, gives real confidence values; the install size is the objection |
| `pycld2` / `cld3` | **no** — C++ | bundled | wheels are the exact CI/laptop drift the pin comment warns about |
| `fasttext` | **no** — C++ | **126 MB download** | a runtime download in a nightly batch is a new failure mode |

**Recommendation: `py3langid`.** Pure Python, deterministic, small, returns a
normalised confidence, and it is the detector `trafilatura` itself reaches for —
so it is one library rather than a second opinion about the same question.

`langdetect`'s non-determinism should disqualify it outright here: NFR-4 makes
every derived row re-runnable, and a gate whose verdict changes between runs on
identical input breaks that at the cheapest possible layer.

### What it does when detection is uncertain — and that is a threshold

Short social-media text is exactly where detectors are least reliable, and this
corpus is mostly short. So the gate needs three outcomes, not two:

```
confident and not in the allow-list   -> DROP
confident and in the allow-list       -> keep
NOT CONFIDENT                         -> keep, and record that it was unresolved
```

**Keep, never drop, on uncertainty.** A false drop destroys evidence silently
and permanently; a false keep costs one extraction. The asymmetry is not close.

Both values are rule-5 thresholds and belong in `contract/`:

```yaml
# contract/harvest.yaml  →  triage:
language:
  allow: [en]
  # Below this the detector's answer is not used at all. Short social text is
  # where detection is least reliable and this corpus is mostly short, so the
  # uncertain bucket is expected to be large — it is not a failure mode.
  min_confidence: 0.90
  # An uncertain document is KEPT. A false drop destroys evidence permanently;
  # a false keep costs one extraction.
  on_uncertain: keep
```

`TriageResult` already distinguishes "gate could not run" from "gate passed", so
`on_uncertain: keep` has somewhere honest to be recorded rather than becoming an
invisible pass.

**Expected yield on this corpus: under 0.5%.** Worth building for correctness on
a broader sweep, not worth building to move the survival number.

---

## 2 · `known-bot` — a list, and a definition

Rule 5 puts it in `contract/`, same class as the subreddit list. Proposed from
what the corpus contains rather than from imagination.

### What the corpus actually holds

Name-pattern matching over 1,925 unfiltered posts flags six accounts, 8 posts:

| account | posts | verdict |
|---|---|---|
| `ClaudeAI-mod-bot` | 3 | **bot** — subreddit moderation |
| `AutoModerator` | 1 | **bot** — Reddit's own, platform-wide |
| `AutoProspectAI` | 1 | **probable bot**, needs a person to look |
| `Automatic-Algae443` | 1 | **human** — Reddit's auto-generated username format |
| `automatedbullshit` | 1 | **human** — a username, not a description |
| `autonoma_2042` | 1 | **human** |

**Three of six name matches are humans**, which is the whole argument against a
pattern and for a list. `Automatic-Algae443` is Reddit's `Adjective-NounNNNN`
default username shape; matching `^auto` catches it and catches every other user
who took a default.

### What qualifies, since "bot" is a judgement

Proposed criteria, all of which a person checks once:

1. **Posts on a schedule or on a trigger, not on a thought.** Moderation
   notices, digests, changelog mirrors.
2. **The account is the mechanism, not the author.** `AutoModerator` is a
   feature of the platform; a person who posts forty times a week is a person.
3. **The content is not a report of use.** This is the one that matters for us —
   a bot mirroring release notes carries no experience, which is what the board
   is for.

**Prolific ≠ bot** is the criterion this list exists to hold. The most prolific
author in the unfiltered corpus posted 26 times and is a human.

```yaml
# contract/sources.yaml  →  known_bots:
#
# HAND-CURATED, like the seeded feeds and the subreddit list. Nominated by name
# pattern over the 2026-08-18 unfiltered sweep, CHOSEN BY A PERSON: 3 of the 6
# name matches were humans, including one on Reddit's default `Adjective-NounNNNN`
# username format. A pattern cannot be the rule.
#
# PROLIFIC IS NOT BOT. The most prolific author in that corpus posted 26 times
# and is a person.
known_bots:
  version: "1.0"
  reviewed_on: 2026-08-__
  platform: reddit
  members:
    - AutoModerator          # Reddit's own, platform-wide
    - ClaudeAI-mod-bot       # subreddit moderation notices
  # Flagged by pattern, NOT added — a person has to look:
  candidates:
    - AutoProspectAI
```

**Expected yield: 0.4% at most.** Build it for `/filtered` to be honest about
what it removed, not to move the number.

---

## 3 · `out-of-window` — buildable now, and it already found a defect

**It is not blocked on the alias review**, and testing that assumption is what
turned up the more interesting thing.

### The defect: `in_window` had never been computed

All 340 registry rows read `in_window = true`. The column is
`NOT NULL DEFAULT true`, and `registry recompute-window` — its **sole writer** —
had never run against staging. So every row was carrying a schema default that
is indistinguishable from a computed answer.

```
policy in_window_months = 18; window starts 2025-02-18
stored   in_window: {True: 340}
computed in_window: {True: 280, False: 60}
```

**60 rows disagreed**, including `openai/gpt-3.5-turbo` (2023-05-28) and
`openai/gpt-4`. FR-1 makes `in_window` the thing the answer path is allowed to
see, so the board would have offered GPT-3.5 Turbo as a current model. Run and
corrected: `60 changed, 280 in window, 60 outside`.

This is rule 6 at the schema layer — a default that reads as a measurement — and
it is the third instance this project has found.

### Should it be built against the seven, or wait?

**Build it now.** The concern — *build against 7 and discover the shape is wrong
at 64* — does not apply here, because the gate does not read `model_alias` at
all. It reads:

```
matched surfaces  ->  SurfacePopulation.owners  ->  model_version.in_window
```

`owners` is derived from the **registry**, not from the alias table: all 340
models, 1,337 surfaces, today. The alias review changes *which surfaces a
reviewer has blessed*; it does not change the shape of the mapping the gate
consumes.

What the alias review *will* change is coverage, and the gate already handles
that correctly — it returns **unavailable** rather than a verdict when a matched
surface has no recorded owner, which happened on 13 of 648 survivors (2.0%). A
declared-only surface such as `deepseek r1` cannot be placed in or out of the
window, and says so instead of guessing.

So the shape is settled and the recall grows. That is the safe direction.

**Measured effect: 169 of 648 survivors (26.1%), 33.7% → 24.9%.** By far the
largest of the three, and the only one worth building for the number rather than
for correctness.

---

## 4 · The subreddit list, widened

At a design effect of 14.5, **only more subreddits buy precision.** The ceiling
per subreddit is `1/ICC ≈ 12.9` effective units no matter how deep the draw, and
11 × 12.9 ≈ 142 — the measured effective n was 132, so depth is already
exhausted.

`ICC = 0.0778`, from `deff = 1 + (n̄−1)·ICC` at n̄ = 175.

| subreddits | 25 posts each | 75 each | 175 each |
|---|---|---|---|
| **11** *(today)* | ±8.6pp | ±7.6pp | **±7.3pp** |
| 20 | ±6.4pp | ±5.7pp | ±5.4pp |
| **26** | — | **±5.0pp** | — |
| 40 | ±4.5pp | ±4.0pp | ±3.9pp |
| 72 | — | ±3.0pp | — |

### The number that decides it

**26 subreddits at 75 posts each: ±5.0pp, in 78 calls — the same budget as the
sweep just run.**

Reshaping 11 × 175 into 26 × 75 costs nothing and takes the interval from ±7.3pp
to ±5.0pp. Going further gets expensive fast: ±4pp needs 41 subreddits (123
calls), ±3pp needs 72 (216 calls).

**Recommendation: widen to ~26 and shorten the draw.** ±5pp is enough to say
whether survival is nearer 20% or nearer 30%, which is the decision the number
feeds. Chasing ±3pp means tripling the call budget to sharpen a figure whose
dominant uncertainty is *which subreddits are on the list*, not sampling error.

### The circularity, unchanged and restated

Every available basis biases high. The honest claim stays:

> **survival within the sources we would harvest** — never survival over Reddit.

Widening makes the interval smaller and does **not** make the figure less
biased; a wider list of AI subreddits is still a list of AI subreddits. The one
thing that would bound the bias is a **non-AI control** — a handful of general
programming subreddits — which measures how much of the survival rate is the
topic rather than the pipeline. That is the more valuable next measurement, and
it is cheap.

```yaml
# contract/sources.yaml  →  sweep_subreddits:
#
# See docs/measurements/unfiltered-sweep.md §3. The subreddit is the unit of
# variation, not the post: survival ran 15.4% (r/singularity) to 59.4%
# (r/LocalLLaMA) across the first eleven, so depth is exhausted at ~13 effective
# units per subreddit and only WIDTH buys precision.
#
# 26 x 75 gives +/-5.0pp in the same 78 calls that 11 x 175 spent for +/-7.3pp.
sweep_subreddits:
  version: "2.0"
  draw: equal
  posts_per_subreddit: 75
  members: [...]            # 11 today + ~15 more, chosen on topic
  control: [...]            # non-AI programming subreddits, to bound the bias
  excluded:
    - id: Anthropic
      reason: >-
        returned `data not found` on page one of the 2026-08-18 sweep while the
        other eleven each returned 175. Not empty — unavailable to
        /getPostsBySubreddit. Recheck before re-adding.
```

---

## 5 · What I would build, in order

1. **`out-of-window`.** Buildable today, shape settled, 8.8 points, and it has
   already paid for itself by exposing the `in_window` default.
2. **The subreddit widening.** Free at the current call budget, and it halves
   the interval on every figure this stage produces.
3. **A non-AI control.** The only cheap thing that bounds the selection bias
   rather than narrowing the interval around it.
4. **`known-bot`.** For `/filtered` to be honest, not for the number.
5. **`wrong-language`.** Last: a new dependency, two contract thresholds, and
   under 0.5% yield on any corpus we have.

And **before any of it: someone has to decide whether 10–15% still means
anything**, because four of these five cannot move the number materially and the
fifth has already been measured.
