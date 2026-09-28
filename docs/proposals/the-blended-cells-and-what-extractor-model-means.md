# Three cells blend two extractors. What to do about it is a decision

**Filtering drops ten verified claims to fix a labelling problem. Recording keeps
them and names it. There is a third option nobody costed: the entire blend is
**two threads**, and re-reading them costs **$0.004**.**

*anooj · 2026-09-18 · PROPOSED. The `EXTRACTOR_MODEL` refusal and the registry
check ship alongside this because they stop the mechanism; this file is about the
instance, and the instance is somebody's call, not mine.*

---

## 1 · What is on the board

```
claim.extractor_model, by pipeline_version
  e5.1   google/gemini-2.5-flash       211
  e5.4   deepseek/deepseek-v4-flash    975
  e5.4   google/gemini-2.5-flash        10
```

985 claims carry one version label and come from two extractors. `CellStore`
filters on `pipeline_version` alone — `extractor_model` appears nowhere in its
`WHERE` — so:

```
3 of 211 distinct e5.4 cell keys aggregate claims from both
  mv_4247e801b57d22e3  code.generation        deepseek=4  gemini=4
  mv_4247e801b57d22e3  instruction.adherence  deepseek=3  gemini=1
  mv_0691ed45b103d0df  instruction.adherence  deepseek=1  gemini=1
```

Those three cells' `n_eff` is a blend of two models' recall and nothing says so.

**The e5.1 rows are not part of this.** They are entirely Gemini, entirely
separate under `claim_id_for`'s version hash, and a version fork is exactly the
mechanism that keeps them apart. The problem is confined to e5.4.

---

## 2 · The option that was not on the table

**The ten claims come from two threads.**

```
thread_context_ada128ab6651409e   5 claims
thread_context_ab6426efec81fc53   5 claims
```

Measured cost per extract call, from `spend_ledger`: 1,546 deepseek calls for
$3.4280517600, or **$0.00222 each**. Re-reading two threads is **$0.004**, plus
at most one schema retry each.

So the blend can be removed by **producing** evidence rather than discarding it,
for less than half a cent. That reframes everything below: this is not a choice
between losing data and living with a caveat.

**What it costs that is not money.** `ExtractionLedger.should_skip` will skip
both threads — id present, version matches, fingerprint matches — so a forced
re-read needs the two `thread_extraction` rows and their ten `claim` rows
deleted first. That is a targeted, auditable delete on the shared staging
database, and it is a coordinated write under `CLAUDE.md`'s convention: announce
it, do it in one transaction, and record the ids removed. Ten rows is small
enough to paste into the announcement.

---

## 3 · The two options as posed, and what each costs

### A · Filter `CellStore` on `extractor_model`

**Cost: ten verified claims stop counting, three cells move, and nothing on the
page says why.**

Three rules argue against it, and they are the project's own:

- **Rule 1 says these claims are not suspect.** Quote verification is
  model-agnostic and runs identically whatever produced the proposal.
  `scripts/ab_extractors.py` states the consequence in its own docstring: *"a
  weaker model yields FEWER verified claims, never wrong ones."* So the extractor
  affects **recall**, not correctness. A Gemini claim with a verified quote is
  exactly as true as a DeepSeek one. Filtering discards evidence to fix a label.
- **Rule 4.** Three cells getting quieter with nothing rendering the reason is an
  absence we caused reading as one we found.
- **Rule 8, and this is the one that settles it.** A filter is a gate. Its error
  rate — does extractor identity actually change what a claim says? — **has not
  been measured**. The instrument exists (`ab_extractors.py`, `test_extractor_swap.py`,
  both of which write nothing) and has not been run to a recorded conclusion on
  these threads. A gate before that measurement is the thing rule 8 refuses, and
  its false positives would be invisible: dropped claims, quieter cells, no trace.

### B · Record the blend and name it

**Cost: a surface, and a reader who has to interpret it.**

The record already exists — `claim.extractor_model` is populated and correct.
What is missing is that **nothing reads it**. Rule 9's shape, on a column that
was added precisely to answer this question.

The minimal honest version is a counted caveat, not a score: a cell whose claims
span more than one extractor says so, with the counts, the same way `n_eff`
carries its constituent voices. No new number, no weighting change, no gate.

---

## 4 · Recommendation

**C now, B as the durable answer, and not A.**

**C** removes the instance for $0.004 by re-reading two threads. It is the only
option that ends with more evidence than it started with.

**B** is what stops the next one being invisible. C works only because somebody
went looking; nothing surfaced these three cells, and nothing would have. A
counted caveat is cheap and is the thing that would have raised a hand.

**A** is wrong on rule 8 today and might become right later — but only after
`ab_extractors.py` has been run on a real population and has produced a measured
disagreement rate. If that measurement showed two extractors genuinely disagree
about what a thread says, this whole file would need rewriting, and the
measurement is the thing that would justify it. It is a day's work and it has
not been done.

---

## 5 · What `extractor_model` currently means, and it is not what the comment says

Relevant because it bounds how much any of the above is worth.

`judge/store/claims.py` describes the column as:

> "The model that ACTUALLY ran, **from the completion, not from the
> environment.**"

**That is not true of the code.** `judge/pipeline.py:560` sets
`self._extractor_model` once, from its constructor argument, which came from the
environment. `Completion.model` carries what the provider reported and **nothing
reads it** — rule 9, on the value that would make the docstring true.

So the column records *what we asked for*, not *what ran*. With the refusal
shipping alongside this, "what we asked for" is at least always explicit and
never a guess — which narrows the gap to "did OpenRouter serve the model we
named". It does not close it.

**Not proposed here**, because wiring `Completion.model` through changes what a
provenance column means mid-corpus, and that is a third decision rather than a
tidy-up. Named so it is not rediscovered.

---

## 6 · We are on 0423 deliberately, not incidentally

`EXTRACTOR_MODEL=deepseek/deepseek-v4-flash`. OpenRouter resolves that to
**"DeepSeek V4 Flash 0423"**, published 2026-04-24. The undated slug is pinned,
not floating: a dated `deepseek/deepseek-v4-flash-0731` and a route
`~deepseek/deepseek-v4-flash-latest` both exist separately, and `-latest` would
be redundant if the bare slug moved.

**So the vendor cannot change our extractor underneath us.** What can is a person
editing one machine's `.env`, which is what happened.

**0731 is five months newer and we are staying on 0423.** What moving would cost:

```
a version bump      e5.4 -> e5.5. `claim_id_for` hashes pipeline_version, so a
                    bump FORKS the claim table - which is the correct behaviour
                    and is the whole reason a bump is the right vehicle for an
                    extractor change.
a re-extraction     531 thread_extraction rows at e5.4 today, at the measured
                    $0.00222 per call = ~$1.18, plus retries. The whole-corpus
                    figure in CLAUDE.md is $1.84 for 887 threads, consistent.
a rebuild           cells recomputed at the new version, and a `judge reweight`
                    diff to see what moved.
```

Under two dollars in money. The real cost is the fork: every figure on the board
would be re-derived, and the before/after comparison is the work, not the spend.

**Recorded here so that staying on 0423 is a decision with a date on it rather
than a variable nobody has looked at since April.** The re-review trigger is not
a date — it is evidence that 0423 is missing claims a newer snapshot finds, and
`ab_extractors.py` is the instrument that would show it.
