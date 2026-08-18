# Which models get swept

**The mention curve flattens after rank 40, and the count falls out of that
rather than out of the budget: 64 models, against a staleness bound that
affords 77. The feed is fresh — `qwen/qwen3.8-27b` is in the registry — but its
cadence is unmeasured, because there has only ever been one poll.**

*Engineer 1 · 340-model registry (staging) · 5,546 Reddit documents · no fetch · 2026-08-18*

> 340 models, 7 with hand-written aliases, 333 invisible to every sweep. `ops/`
> refuses eight stages and the alerts have no baseline, and none of it moves
> until harvest produces documents for more than seven models. This is the
> scoping decision `model_version.last_swept_at` was added ahead of — #33.

---

## 0 · How to read a zero in this document

Carried from `alias-surfaces.md` §0, because it decides how half the table below
reads:

| written | means |
|---|---|
| a number | measured, and the count came back that |
| **unmeasured** | the corpus contains no observation of this model. There is no zero |

**18 of the 64 tracked models are `unmeasured`.** They are not models measured at
zero mentions. Nothing in this document licenses pruning one.

---

## 1 · The freshness check, first, because it changes what the rest is

The premise, taken as given rather than verified here: Simon Willison posted
about Qwen 3.8 27B on 16 August, two days after release. If the registry does
not carry it, the gap is not only alias surfaces, and a selection rule built on
a lagging list is built on sand.

One query against staging:

```
qwen/qwen3.8-27b   Qwen: Qwen3.8 27B   release_date 2026-08-14   provenance polled
```

**It is there**, dated exactly two days before the post, which corroborates the
premise from a second direction. Alongside it sit 24 more rows with a release
date inside 30 days, including `google/gemini-3.7-flash` at 2026-08-13 and
`bytedance-seed/seed-2.0-code` at 2026-08-12. The whole gap is surfaces, and
this work closes it.

### What the check does not establish, and it is the part worth knowing

Two things, and neither is a defect — the poller landed yesterday.

**The population of one.** This checked one externally-attested release against
the registry and found it. That is a sample of one, chosen because somebody
happened to post about it. The 25 recent rows are the registry describing
itself, not a coverage rate: I have no independent list of what was released in
the last 30 days, so **no completeness figure is claimed here.** `25 of 25`
would be circular in exactly the way `52.7%` was.

**The single poll.** All 340 rows carry `first_seen_at = 2026-08-17`.

| | |
|---|---|
| distinct `first_seen_at` dates in the registry | **1** |
| polls from which a cadence could be measured | **1** |
| external releases checked against the registry | **1**, and it was present |

So the apparent "3-day lag" on `qwen3.8-27b` is the distance from its release to
*the one poll that has ever run*, and it would read identically if the poller
never ran again. Presence is confirmed; **freshness over time is unmeasured**,
and stays so until there are two polls to compare. "The feed has it" and "the
feed keeps up" are different claims, and only the first is supported here.

---

## 2 · Ranked by mentions, not by release date

Recency and discussion are different measurements, and the feed makes the
difference concrete: **11 of the 340 ids are `~vendor/…-latest` routing
pointers**, whose `release_date` is when the pointer moved rather than when
anything launched. Alongside them sit regional variants and fine-tunes nobody
has written a sentence about.

A date-sorted top 50 would seat several of those and drop
`anthropic/claude-sonnet-4.5` — 426 mentions, sixteen months old, still
discussed constantly.

So the ranking is by attributable mentions. **What that count is drawn from:**

```
7,202 attributable mentions over 145 surfaces
  of 10,255 mentions over 449 surfaces, extracted from 5,546 Reddit
  documents, 2026-08-17 (docs/measurements/alias-surfaces.md)
  attributable = the `resolved` and `attested-gap` verdicts, which name
  exactly one registry model each

  EXCLUDED, and each exclusion makes every count a LOWER BOUND:
    attested-gap-ambiguous   49 surfaces, 1,530 mentions, 2–25 candidate
                             models each. Assigning them would invent the
                             attribution the extract refuses.
    unknown-model           255 surfaces, 1,523 mentions naming nothing the
                             registry carries. A poller finding.

  Reddit prose only. A GitHub issue names a model in a config line, where the
  id spelling is the likely form and this corpus finds id spellings
  unattested. So this ranks how often a model is discussed IN REDDIT PROSE,
  not how often it is named.
```

---

## 3 · The count, and it is not the budget's

Her ruling was that the staleness bound sets the number, and 7 days buys 77. I
said 50 earlier; that was a round number. Here is the distribution.

| rank band | mentions added | share of 7,202 | fewest in band |
|---|---|---|---|
| 1–10 | 4,840 | 67.2% | 212 |
| 11–20 | 1,336 | 18.6% | 85 |
| 21–30 | 571 | 7.9% | 34 |
| 31–40 | 268 | 3.7% | **21** |
| 41–50 | 117 | 1.6% | 6 |
| 51–72 | 70 | 1.0% | 1 |

**It flattens exactly where you guessed.** Ranks 1–40 carry 97.4% of
attributable mentions. Ranks 41–72 — thirty-two models, 44% of everything the
corpus has ever discussed — carry 2.6% between them, and the last ten carry
three mentions or fewer.

**The discussed population is 72.** That is the ceiling on ranking by mentions:
beyond 72, there is nothing to rank, only models the corpus has never observed.
A target of 77 therefore cannot be filled by this measurement even in principle
— it would have to be topped up by a rule, which is what §4 is.

A floor of **20 mentions** sits in the flat part rather than on a cliff, and it
is the last floor before the marginal model is worth under 0.1% of the corpus:

| floor | seated by mentions | + launch window alone | **total** | mention coverage |
|---|---|---|---|---|
| 1 | 72 | 18 | 90 | 100.0% |
| 5 | 54 | 20 | 74 | 99.3% |
| 10 | 45 | 22 | 67 | 98.5% |
| **20** | **41** | **23** | **64** | **97.7%** |
| 30 | 32 | 24 | 56 | 94.5% |
| 50 | 26 | 24 | 50 | 91.4% |

**64 models, and the budget is not binding.** 64 < 77, so the staleness bound
and the data agree rather than competing, and the number can be argued from the
corpus. Reporting, not deciding: 10 and 20 are both defensible, and the
difference between them is four models carrying 0.8% of the mentions.

**What this cannot support.** It is a ranking of *Reddit discussion*, so it
will under-rank models discussed mainly in GitHub issues — where §2's caveat
says the naming convention is different and this detector is blind to it. It is
not a ranking of importance, quality, or use.

---

## 4 · The launch-window rule, and what it drags in

A new model has no discussion history, and the launch window is exactly when
people post. Engineer 2 already agreed the shape: a model in its launch window
is swept nightly rather than rotated.

At 30 days that is **25 models, 23 of which the mention floor would not seat** —
18 of those `unmeasured` outright. `qwen/qwen3.8-27b` enters here, at rank 60,
which is the whole reason §1 was worth checking first.

| window | tracked total | seated by the window alone |
|---|---|---|
| 7d | 51 | 10 |
| 14d | 54 | 13 |
| 21d | 58 | 17 |
| **30d** | **64** | **23** |
| 45d | 80 | 39 |
| 60d | 84 | 43 |

45 days is where the budget starts binding (80 > 77). 30 leaves headroom.

### One thing the rule admits that it probably should not

`~deepseek/deepseek-v4-flash-latest` is seated at rank 64 by a `release_date` of
2026-08-01 — **the date a routing pointer moved, not a launch.** There are 11
such ids in the registry and this window catches one of them.

Not fixed here, because "is a `~`-prefixed route a model for sweeping purposes"
is a contract question rather than a threshold, and it belongs with the same
decision as the rest of §5. Flagged rather than filtered: a silent exclusion is
the failure mode, not the inclusion.

The selector also refuses a related case outright — a model whose `release_date`
is *ahead of* today is not in its launch window, because an age of −43 days is
trivially "within 30" if only the upper bound is checked, and a mis-parsed date
would otherwise seat a model that does not exist and keep it seated. No registry
row is future-dated today; `Selection.future_dated` lists them rather than
dropping them if one ever is.

---

## 5 · Where the selection rule should live — a proposal, not a change

Rule 5 puts thresholds and filter rules in versioned YAML. This is the same
class as the feed list and the subreddit list: two numbers that change what gets
collected, and that must produce a version diff rather than a code deploy.

**`contract/registry.yaml` has not been touched.** `TrackedSetPolicy` takes both
values as required arguments with **no defaults** — deliberately unlike
`RegistryPolicy`, which carries proposed values as code defaults. That pattern is
documented in `policy.py` as a hazard tolerated so the lane could be developed
before the contract file existed; here there is no signed-off value for a default
to shadow, so a caller must supply both and nothing can pick up a threshold
nobody agreed to.

Proposed block, for the same PR that rules on the routing-entry question:

```yaml
# ----------------------------------------------------------------------------
#  #33 — the tracked set. Which models the nightly sweep looks for evidence on.
#
#  340 models at 81.45 requests each against ~900 nightly is 11 models a night:
#  a full pass takes 31 days against a 30-day half-life. The sweep loses to the
#  decay curve, so the set has to be smaller than the registry.
#
#  ⚠  CHANGING EITHER VALUE CHANGES WHAT IS COLLECTED, NOT ONLY WHAT IS SHOWN.
#     A model dropped from the set stops accruing evidence that night. Its
#     existing claims stand and its `last_swept_at` stops advancing, which is
#     the state the coverage surface must render distinctly (rule 4).
# ----------------------------------------------------------------------------

tracked_set:

  # Attested mentions at or above which a model is swept.
  #
  # 20 puts 41 models in and covers 97.7% of the 7,202 attributable mentions in
  # the 2026-08-17 Reddit extract. Ranks 41-72 carry 2.6% between them, so this
  # sits in the flat part of the curve rather than on a cliff.
  #
  # Counted from `resolved` and `attested-gap` surfaces only. A model's count is
  # a LOWER BOUND: 1,530 ambiguous mentions are excluded rather than assigned.
  mention_floor: 20

  # Days since release inside which a model is swept regardless of mentions.
  #
  # A new model has no discussion history, and the launch window is when people
  # post. 30 adds 23 models the floor would not seat, 18 of them unmeasured.
  # 45 would take the set to 80, past the 77 the staleness bound affords.
  launch_window_days: 30
```

Two open questions that belong to whoever signs this off, not to me:

1. **Do `~vendor/…-latest` routes count as models here?** §4. Eleven ids, one
   currently seated.
2. **Does the floor move when a GitHub or blog extract lands?** The ranking is
   Reddit-only, and §2 says that is the most likely way it misleads.

---

## 6 · Surface counts: 5.5 does not hold, and it is not close

Her question was whether 5.5 surfaces per model survives contact with the
tracked set. It does not — and the tracked set is no better than the corpus at
large, which is the useful part of the answer.

Over the **46 tracked models the corpus has observed** (the other 18 are
`unmeasured` and are omitted, not counted as zero):

| distinct attested surfaces | models |
|---|---|
| 1 | 6 |
| 2 | **27** |
| 3 | 11 |
| 4 | 2 |

**median 2 · mean 2.20 · min 1 · max 4**

Against `alias-surfaces.md` §2's median 2, mean 2.01 over all 72 discussed
models: **selecting the most-discussed models barely moves the surface count.**
Mean rises 2.01 → 2.20 and the median does not move at all. Being discussed a
thousand times does not get a model discussed under more names — `opus 5` at
1,445 mentions carries two surfaces, the same as the median.

So the review is much smaller than either of us costed. The whole artifact is:

| | |
|---|---|
| entries | 64 |
| variant lines to read | 217 |
| entries with an attested primary | 46 |
| entries where every form is derived | 18 |
| entries with an `INCOMPLETE` slot | **64** |

**217 lines, not the ~350 a 5.5-surface assumption predicts for 64 models.**

---

## 7 · What the artifact is, and what it is not

`docs/proposals/alias-surfaces-tracked-set.yaml`, from:

```
py -3 -m collect.cli registry propose-aliases \
    --surfaces fixtures/openrouter/observed-surfaces.json \
    --mention-floor 20 --launch-window-days 30 \
    --out docs/proposals/alias-surfaces-tracked-set.yaml
```

Three categories kept apart, per entry:

| | |
|---|---|
| **attested** | observed in the corpus, with mention counts. Recall. |
| **by rule** | the vendor word dropped and rendered three ways. Derived from a rule the corpus measured — 12 models, all 12 corroborated by attestation. |
| **mechanical** | spacing, hyphenation, concatenation of the id and the feed's name. Coverage. |

**Every one of the 64 entries carries an `INCOMPLETE` slot**, so the file cannot
be loaded unreviewed — `family_surface` on all 64, plus `attested_surfaces` on
the 18 nobody has been observed writing. Each entry also records `seated_by`,
because it changes what a reviewer can do with the row: under a
`launch-window` entry there is no attested surface to confirm, so every form
below it is a derivation and the reviewer is supplying judgement rather than
checking it.

**The typing is hers** — she called the family surface the same class as the
query vocabulary, and it is. **The candidates are mine, and they come from the
corpus rather than from imagination**: 46 of the 64 primaries are the
most-mentioned form people were actually observed writing, which is the specific
thing the eleven hand-curated models did not have available and got wrong twice
(`claude opus 5` and `claude sonnet 5`, both at 0 against attested alternatives).

So the deliverable is **a ranked, labelled list she works through — not a
finished alias file.** Nothing here decides anything.

---

## 8 · What would revise it

- **A second poll.** §1's cadence question becomes answerable and not before.
- **A GitHub and blog surface extract.** Same selector, different corpus. The
  prediction is that id spellings rank very differently, and it is testable.
- **The routing-entry ruling.** §4. It moves one model today and more as the
  `~…-latest` pointers move.
- **Documents for more than seven models.** The whole reason for the exercise:
  once harvest runs against 64 models, `last_swept_at` starts carrying real
  values and the rotation this set exists to feed can be measured rather than
  argued.
