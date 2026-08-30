# The tier re-key lands, and the best cell on the board still reads 25% of the gate

**Nothing publishes, and this time that is a proof rather than a prediction.**
`n_eff` is a sum of per-voice maxima and every claim's `f_evidence` rises by at
most `0.65 / 0.12 = 5.4167`, so `n_eff_after ≤ 5.4167 × n_eff_before` for every
cell whatever the two booleans turn out to say. The best cell on the board is
`claude-sonnet-5 · reasoning.multistep` at **0.1409**. Its ceiling is **0.7632**
against a gate of **3.0**.

*Engineer 1 · 2026-08-30. Option 2 of the tier proposal, capped at B, on E2's
delegated ruling. The code is landed and tested; the rollup has NOT run, because
staging was unreachable all afternoon.*

---

## 1 · What is not in this document, and why

**The re-weight did not run.** `52.17.75.29:5432` refused to answer for the whole
session — 40 probes over 35 minutes, three of them with a 25-second timeout, zero
connections. So there are no measured per-cell before/after figures here, and the
`n_eff per cell` table E2 asked for is the one thing this cannot supply today.

**And the claims are only in that database.** The 150-thread run's per-claim
output was never written to disk, so it cannot be reconstructed from the
checkout. That is the failure `docs/measurements/` exists to prevent and it has
now cost something concrete: a run that could have been re-priced offline has to
wait for a host. `judge reweight --from-version e5.1` is written, tested against
a real Postgres, and takes about a second when there is something to connect to.

What survives the outage is the part that decides the question, because the
headline result is a **bound**. A bound does not need the rows.

## 2 · The ceiling, and it is not close

```
tier D -> B multiplies f_evidence by     5.4167
gate                                        3.0

best cell    claude-sonnet-5 · reasoning.multistep
             measured 2026-08-28    n_eff 0.1409   voices 7   platforms 2

             ceiling at tier B      0.7632    25.4% of the gate
             ceiling at tier A      1.1742    39.1% of the gate
```

**Tier A would not have published it either.** That is worth stating plainly,
because the rule-8 argument for capping at B invites the reply *"we are leaving
publication on the table to be careful"*, and we are not. The rung we refused
does not reach the bar on this corpus. The cap costs nothing today and buys the
thing rule 8 is for: `has_repro_steps` stays a weight until round 3 measures it.

**What `claude-sonnet-5 · reasoning.multistep` reads at tier B, and what it would
need.** Its per-voice weight is `0.1409 / 7 = 0.0201`:

```
if every one of its 7 voices reaches B    n_eff 0.7632   needs  28 voices
if none of them promote                   n_eff 0.1409   needs 150 voices
it has                                                           7
```

So the honest answer to *"how many voices would it need"* is **28 at the very
best and 150 at worst**, and the true figure is somewhere between and not
measurable from here. Both ends assume every added voice weighs what the seven
already there weigh, which is the only assumption available and is stated rather
than hidden.

**At most 157 of the 197 stored claims can move at all.** 29 are `E` and 11 are
`F`, and neither has rungs.

## 3 · The vendor case, which is the one that could have made the board worse

E2's flag: *"if a vendor announcement filed own-experience gets promoted to tier
B by having numbers in it, the fable-5 cell gets heavier rather than lighter."*

**A correctly-filed announcement cannot get heavier.** `vendor-about-own-product`
maps straight to F with no rungs, so numbers buy it nothing.
`tests/test_reweight_db.py::test_a_vendor_announcement_full_of_numbers_stays_at_F`
asserts it end to end against a real database, and the tier tests parametrise
both booleans over both non-first-hand `speaking` values so the property is *"the
booleans are not read here"* rather than *"they happen not to matter for this
input"*.

### The correction, and E2 asked for it to be recorded as one

The brief said *"E6 was wired last night, so the reject rules run on future
claims and not on the 197 already stored"*, and read the announcement problem as
a gate that exists and had not yet run. **It is not.** E6's five triggers are
`affiliate_link`, `sponsored_disclosure`, `discount_code`,
`syndicated_duplicate` and `predates_model`, and **none of them detects a vendor
announcement.** E6 running on all 197 would have caught zero of them.

So the announcement problem **has no gate and never had one**, on any branch, at
any point in this project. E6 being unwired was never what left it exposed, and
wiring E6 did not close it. That makes the exposure larger than the brief
assumed, not smaller — and it is worth stating in that direction, because the
version where E6 was the guard has a fix (wire it, done) and the true version
does not.

E2 asked for this to sit in the writeup as a correction to the brief rather than
as a footnote, and it belongs there for a reason beyond bookkeeping: the same
sentence would have been believed by whoever read the commit next.

**What stands in for the missing gate is `speaking`** — the extractor's own
label, unmeasured on the same unlabelled golden-set round as `has_repro_steps`.
An announcement it files as `own-experience` is full of numbers by construction
and now promotes.

That cannot be fixed by a gate today, so it is counted: `judge/reweight.py`
reports every promotion whose document is hosted on a provider's own domain,
per model, with the domain named. Rule 8 — a flag, not a filter. The suffix
match is on a dot boundary, so `notanthropic.com` does not match `anthropic.com`;
that control is a test, because the substring version of this mistake is already
in `docs/measurements/control-and-reshape.md`.

**The one instance held locally is filed correctly.** The auto-mode post's *"none
of the 720 attack attempts succeeded against Claude Fable 5, Opus 5, or Sonnet
5"* is `vendor-about-own-product` with `has_numbers: true`. It stays at F.

## 4 · A different population, and it is reported as one

186 claims across three persisted blog extraction runs — **not** the 197 stored
across three platforms, and not a sample of them. Every one is in the checkout
because its run happened to be saved.

```
124  own-experience            repro=False  numbers=False
 47  relayed-from-elsewhere    repro=False  numbers=False
 13  vendor-about-own-product  repro=False  numbers=False
  2  vendor-about-own-product  repro=False  numbers=True

own-experience claims that would promote   0
has_repro_steps true anywhere              0
```

**On this population the re-key is a no-op**, and `has_repro_steps` is False on
all 186. If the stored 197 resemble it, the measured lift will be near zero and
nowhere near the §2 ceiling — which is a reason to run the rollup and read the
number, not a reason to assume it.

## 5 · What I broke, and what I found while breaking it

**`f_specificity` and the tier now price the same two facts.** The old contract
block used that as its argument for not promoting — *"raising the tier on the
same signals would price one fact twice"* — and it is still true. A claim
carrying both signals is worth 5.42× in the tier and 1.95× in `f_specificity`,
**10.6× combined**, of which the 1.95× is the double count. E2's ruling
overrides the conclusion and not the objection. De-duplicating means dropping
`has_numbers` and `has_repro_steps` from `specificity_factor()`, which moves
every stored weight in a second way, so it is a separate ruling and is not taken
here.

**`None` walked straight past the check built to stop exactly this — and E2 is
right that it may matter more than the tier re-key.** `judge/cli.py:_document_facts`
passed a literal `None` for `has_numbers` and `has_conditions`; `compute()`'s
refusal tested `value is UNSUPPLIED`; `specificity_factor` then read the `None`
as falsy. **Every claim in the table was weighted as though both were False**,
whatever the document says, by a guard whose entire purpose was to make that
impossible.

The sentinel exists because `False` had once meant "nobody measured". `None`
means the same thing and had the same effect, and it got in because the guard was
written against the **shape** of the old bug rather than its substance. A
sentinel that catches only the spelling somebody remembered is a guard against a
spelling.

**Fixed 2026-08-30, in three places, and the third is the one that costs
something.**

```
compute()            refuses `None` as well as UNSUPPLIED, on all ten inputs
                     - parametrised over the whole list, because auditing the
                     two that were caught would fix the instance and leave the
                     class
_document_facts()    reads document.has_numbers / has_conditions
release_date         still accepts None, which MEANS "no release date known"
                     and returns f_launch 1.0. The one None that is a value,
                     and the reason the check lists its inputs rather than
                     scanning the signature
```

⚠ **A refusal is a drop, and the columns are NULL on most documents.**
`collect/triage/specificity.py` computes both and nothing writes them —
`contract/column_states.yaml` now carries them as `unwired` with the gap named.
So this repair moves the failure from a silent wrong weight to a **loud dropped
claim**, and the remaining repair is in the other lane: write the columns.

That is rule 8's hazard and it is accepted rather than dodged. What makes it the
right trade is that the absence is loud — `UnsuppliedWeightInput` names the input
and its writer, and `judge/reweight.py` counts refusals per input — whereas the
`None` it replaces was a silent wrong weight on every row. **Rule 8 prefers a
visible wrong weight to an invisible wrong gate; it says nothing in favour of an
invisible wrong weight**, which is what this was.

**How many stored claims change is not guessed here.**
`scripts/measure_document_facts_gap.py` is read-only, runs against the corpus
rather than a sample, and reports the refusals broken out by which column is
NULL, per platform and per model, plus the claims whose `f_specificity` actually
moves. It has not run yet, for the reason in §1. Nobody should learn how many
claims a NULL column drops by running the migration that drops them.

**The two rulings get two pipeline versions, and that is what pays for the
attribution.** `e5.1 → e5.2` is the tier alone, with the document booleans held
at the values e5.1 effectively used — `--document-facts frozen`, passing `False`
explicitly, so the reproduction no longer depends on the bug being present.
`e5.2 → e5.3` is the document facts alone. A single diff carrying both would
measure neither, and `plan()` asserts the separation per claim rather than
claiming it in a comment: it compares each recomputed factor against the stored
one and counts any that moves, `f_recency` excepted because it decays with the
calendar.

**`CellStore` had no `pipeline_version` filter**, which was harmless while the
table held one version and is not harmless after a fork. `count()` keeps one
representative per voice at its **highest** weight, so an unfiltered read would
have handed every voice the better of its two tiers — inflating the *before* side
of the diff, worst on exactly the claims the re-tier moved.

**The column audit was over-attributing SQL reads.** `claim` and `claim_weight`
both have `pipeline_version`; a statement joining them credited the read to both.
`scripts/audit_columns.py` now resolves table aliases, which is the same
correction its web-side check already carried and got the same way — from a false
positive.

**One test was asserting the opposite of its own name.**
`test_a_different_pipeline_version_is_a_different_claim` contrasted against a
hardcoded `"e5.2"`, so bumping `PIPELINE_VERSION` to `e5.2` made the two writes
the same claim. It now derives the contrasting version from the constant.

## 6 · What runs next, in order

```
1  scripts/measure_document_facts_gap.py --pipeline-version e5.1
       read-only. How many claims a NULL column drops, before anything drops one.

2  judge reweight --from-version e5.1 --to-version e5.2 --document-facts frozen
       dry run. THE TIER RULING ALONE. Drift must be empty.
   judge reweight --from-version e5.1 --to-version e5.2 --document-facts frozen                   --apply --driver config-change

3  judge reweight --from-version e5.2 --document-facts read
       dry run. THE DOCUMENT-FACTS RULING ALONE, at e5.3. f_specificity moves
       here by design and is reported as a result rather than as drift.
       Gated on step 1's number.

4  scripts/report_rollup_delta.py                against _before_rollup.json
```

Each dry run prints the tier moves, the withheld promotions, the provider-domain
flags and the per-cell `n_eff` before and after — all inside a transaction that
is rolled back, because pricing cells needs the claims to be IN the table.

**Read the drift line first, and stop if anything but `f_evidence` moved.** In
step 2 that line must read *"only f_evidence moved"*; anything else means the
run is not about the tier ruling and nothing in §2 applies to it. In step 3
`f_specificity` moving is the point, so it is excluded from drift there and
counted separately — the stop condition still holds for the other four factors.
