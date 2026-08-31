# `has_repro_steps` is False on every claim because the extractor is never asked for it

**Not "the corpus has no repro steps". The question was never put.** The field
is absent from the system prompt, and the tool schema hands the model a bare
boolean with a default and no description:

```
judge/extract/prompt.py     no occurrence of "repro" anywhere in the file

ExtractedClaim.model_json_schema()["properties"]["has_repro_steps"]
                            {"default": false,
                             "title": "Has Repro Steps",
                             "type": "boolean"}

judge/extract/schema.py:220 has_repro_steps: bool = False
                            # no Field(), no description, not in `required`
```

Every other field the tier or the weight reads carries a description — `quote`
gets 90 words, `is_sarcastic` gets two sentences, `severity` gets a warning
about averaging. This one gets its own name, restated in title case.

*Engineer 1 · 2026-08-31. Measured on the 199 claims stored at `e5.1`: 0 True.*

---

## 1 · Why this matters more than it did last week

Until 2026-08-30 the field fed only `f_specificity`, where a wrong value is a
mis-ranking. Since the tier re-key it is **half the ladder**:

```
contract/harvest.yaml evidence_tier_rules

  own-experience:
    repro_steps_and_numbers:  B     0.65
    one_of_the_two:           C     0.35
    neither:                  D     0.12
```

`signals` counts True values across `(has_repro_steps, has_numbers)`. With one
of the two structurally False:

- **B is unreachable.** It needs both, and one can never be True.
- **C is reachable by the numbers rung alone**, and that rung is additionally
  vetoed by `document.has_numbers`.

So the ruling that was made to lift claims off D is running on one leg. That was
already known — the ruling caps at B on purpose, and `docs/proposals/for-
engineer-2-tier-a-is-unreachable-by-construction.md` argued C and B into
existence. What was not known is that the rung the ruling opened first is the
one the extractor was never asked to fill.

## 2 · The distinction that makes this worth fixing rather than deleting

`has_numbers` has **exactly the same schema defect** — no description, default
False, not required — and it comes back True on 20 of 199. So the model does
fill an undescribed boolean when the name alone carries the question.

That is the whole finding. `has_numbers` is self-evident from four words of
title case. `has_repro_steps` is a judgement — does "I ran it twice with the
same prompt and got different output" carry repro steps? — and the model
declines to make it, silently, by taking the default.

**Which means the 0-of-199 is not evidence about the corpus and must not be
quoted as any.** Rule 7: the figure answers "how often does an unasked optional
boolean take its default", and it has been read as "how many engineers publish
repro steps". Those have different denominators and only one of them was
measured.

## 3 · What I am proposing, and what I am not

**Proposed: give the field a description and name it in the prompt.** Two edits,
both in `judge/`, neither of which changes what a model may decide — the model
still proposes, code still checks. Yours to make or refuse; I have not touched
either file.

A description in the same register as the others, e.g.:

> Did the writer give enough for someone else to reproduce what they saw — a
> prompt, a config, a command, a sequence of steps, a repository link, or a
> stated number of runs? A description of an outcome is not repro steps. Leave
> it false rather than reaching: a false positive here promotes the claim a
> whole tier.

And one line in `SYSTEM_PROMPT`'s "WHAT YOU RECORD" block, because
`Do not fill a field to be helpful` currently reads to the model as an argument
for the default on a field it was never introduced to.

**Not proposed: promoting anything to A.** The 2026-08-30 cap stands and this
does not touch it. If anything it strengthens the cap's own argument — the
boolean's error rate is unmeasured, and a boolean nobody asked for does not even
have an error rate yet, it has a default.

**Not proposed: a code-side falsifier.** `contract/harvest.yaml` already refuses
`document.has_code` for this and gives the right reason. A repro is not a code
fence.

## 3.5 · Does this need a re-extraction? Yes for the existing 199, and it is $0.43

**The question you should have before ruling, answered with a measurement rather
than the estimate.**

`has_repro_steps` is a column on `claim`, written by the extractor. Adding a
description changes what the model EMITS, so:

```
  new claims          get the described field from the first call. No backfill.
  the existing 199    keep `false` forever unless the thread is read again.
                      `judge reweight` cannot help: it RE-PRICES stored fields
                      and cannot invent a boolean the model was never asked for.
                      A reweight over these 199 would faithfully re-price 199
                      falses.
```

So the existing corpus needs a re-extraction to benefit, and here is what that
costs — **measured from the token counts of the very extractions that produced
those claims, n = 93, not the n = 3 estimate:**

```
  thread_contexts behind the 199 claims        93
  input tokens                            487,060
  output tokens                           115,393
  cost at contract/seed_models.yaml pricing  $0.4346      $0.00467 per thread
```

Two things in that number are worth having beside it:

- **It is a measured token count times a SEEDED price**, not a billed amount.
  `price_in=0.30 / price_out=2.50` per 1M is Gemini 2.5 Flash from
  `contract/seed_models.yaml`, itself a build fixture.
- **$0.00467 per thread is 56% above the corpus mean of $0.00299** (all 207
  extractions, $0.6186). Threads that yield claims are longer than threads that
  do not, so the claim-bearing 93 are the expensive end. Do not read $0.00467 as
  a per-thread rate for anything else.

**And there is a fork cost that is not dollars.** A re-extraction at a new
`pipeline_version` forks `claim` — `PIPELINE_VERSION` is hashed into
`claim_id_for` and `judge/store/cells.py` filters on the column, so the board
reads one version or the other, not both. Whether the 199 move or a second
version stands beside them is your ruling, not a consequence of the price.

## 4 · What this changes downstream, stated before it is done

If the field starts coming back True at any rate above zero, **every claim it
fires on moves D → C, and any claim also carrying a vetted `has_numbers` moves
to B.** That is a re-price of stored rows, so it wants a `pipeline_version` bump
and a `judge reweight` fork rather than an in-place edit — the same shape as the
tier re-key.

It also makes the known double-count worse in exactly the direction
`contract/harvest.yaml` already records: `has_repro_steps` is worth 0.4 in
`specificity_factor()` and now prices a tier as well. That objection is not new
and this does not settle it; it just becomes visible for the first time, because
until now the field was False everywhere and the double count on it was zero.

## 5 · The measurement I would want before believing the result

Round 3 of the golden set is unlabelled, and it is what would give this boolean
an error rate. Until then a True here is a proposal, priced as a weight, which
is where rule 8 puts it. **What I would ask for first is the smaller thing:**
re-extract a slice with the description added and report how many claims flip.
If it stays 0, the corpus answer is real and this document is wrong about
everything except the schema.

---

### Appendix — how to reproduce the schema claim

```
python -c "from judge.extract.schema import ExtractedClaim; \
  print(ExtractedClaim.model_json_schema()['properties']['has_repro_steps'])"

grep -ci repro judge/extract/prompt.py     # 0
```
