# Polarity, read by hand: 7 of 23 wrong, and two of them are inversions

**One reader — me — no golden set, no second labelling.** That is the whole
population of stored claims, so the denominator is complete, but the judgement is
one person's and §4 says what would change it. Recorded because the third
extractor failure has had no check of any kind.

*Engineer 1 · 2026-08-24*

---

## 1 · The count

```
claims stored                      23
polarity matches the quote         13   (56.5%)
polarity WRONG                      7   (30.4%)
borderline / defensible either way  3   (13.0%)
```

**And the distribution is the first finding, before any individual verdict:
21 of 23 claims are `positive`.** Two are negative. On a corpus gathered by a
sweep whose negative queries feed the gate and whose whole purpose is surfacing
what engineers complain about, a 91% positive rate is a systemic signal rather
than a set of individual errors.

`severity` is NULL on all 23. `speaking` is NULL on 4.

## 2 · The two inversions — the class that corrupts a page

These say the opposite of the quote, and there is nothing in the pipeline that
would notice.

**`clm_1c6e656d` · `instruction.adherence` · labelled `positive`**

> *"Claude Haiku 4.5 was the easiest to attack."*

Easiest to attack is the worst possible outcome for instruction adherence. This
is a prompt-injection result reported as praise. `speaking` is
`relayed-from-elsewhere`, so it is a third party's finding, correctly flagged —
and then inverted.

**`clm_6bd482dd` · `over_refusal` · labelled `positive`**

> *"Qwen 3.8 27B is excellent, but it defaults to wildly overthinking things"*

The quote has two clauses and the extractor took the polarity of the wrong one.
`excellent` is general praise; the clause bearing on the capability is
*"wildly overthinking"*, which is the complaint. **A `but` inverted the sentence
and the label followed the first half.**

**Why these two matter more than the other five:** a wrong polarity on a real
capability claim renders as praise on a model page built to surface problems.
Rule 4 is about absence reading as approval; this is worse — it is a complaint
reading as approval.

## 3 · Five where polarity is not wrong so much as meaningless

No valenced claim is being made, so `positive` is unsupported rather than
inverted. This is over-production, and it is the same failure as the vendor-copy
one: the extractor emitting a claim where there is none.

| claim | quote | why |
|---|---|---|
| `clm_84fb3dd3` | *"I tasked Codex and GPT-5.6 Sol Ultra with building a prototype"* | states what the author **did**, no outcome |
| `clm_d7c2f7e0` | *"I had Qwen 3.8 27B build for me, running offline on my laptop."* | same shape — an action, not a result |
| `clm_a6a1ec5c` | *"scores 52 on the Artificial Analysis Intelligence Index"* | a bare number. 52 of what, out of what? Positive is unsupported without the scale — **rule 7 inside a quote** |
| `clm_9e35285c` | *"On paper Qwen 3.8 27B has all three of these, so is it up to the task?"* | **a question**, and *"on paper"* explicitly marks it unverified |
| `clm_049c6638` | *"The API has zero authorisations checks on cancelling other people's reservations … I tested this … and it actually went through."* | a security bug in **an API the author was testing**, filed as `code.generation` `positive`. If it is about generated code at all, it is negative |

`clm_049c6638` is the worst of the five: it is not a model-capability claim in any
reading, and the polarity is inverted **in addition** to the subject being wrong.

## 4 · The three I will not call either way

Stated rather than folded into a count, because a borderline counted as an error
inflates the finding and counted as correct hides it.

- **`clm_928cffaf`** *"It churned away for 38 minutes and delivered this answer"* —
  delivered is positive, 38 minutes is a latency complaint. Mixed, and
  `code.generation` picks out the half that succeeded.
- **`clm_f83085fa`** *"just one point behind GLM-5.2 (max) and DeepSeek V4 Pro"* —
  the framing is positive, the fact is a deficit. For the subject model a
  near-tie with the leaders is arguably good news.
- **`clm_3896c2fd`** *"I'm now generating my summaries using GPT-5.6 Luna."* —
  adoption implies satisfaction, but no outcome is stated. Closer to the §3 group
  than to a claim.

## 5 · Does it need a code check? Partly, and not the part that matters most

**The inversions cannot be caught by code, and that is not a gap — it is rule 2.**
Deciding whether *"excellent, but wildly overthinking"* is positive about
`over_refusal` is exactly the judgement `CLAUDE.md` refuses to give code: *"is
this person complaining or joking, about which capability, under what
condition"*. A code check that tried would be the pure-code matcher that hit
`free` inside *"freeze"*.

**So the check for the inversions is a golden set, and it is the one thing this
failure has never had.** Vendor copy got `speaking`. Missed first-hand reports
got a labelling round. Polarity has had neither — no option in any pool asks
whether the polarity matches the quote.

**Three things code CAN check, and none of them is a gate:**

1. **A distributional alert.** 21 of 23 positive is checkable arithmetic. It
   proves nothing about any single claim and it is a strong signal about the set —
   which is precisely what an alert is for, and `ops/alerts.py` already has the
   shape.
2. **A quote ending in `?`** is not a claim. Mechanical, unambiguous, and it
   catches `clm_9e35285c`.
3. **A quote with no first-person or evaluative token** flags the §3 group for
   review. A flag, not a drop — the difference between proposing and deciding.

**What I would do, in order:** add polarity to the next labelling round as a
binary — *does the polarity match the quote, yes or no* — because that is the
question a second reader can answer reliably and a 15-way capability choice is
not. Then the distributional alert, which costs nothing. The two mechanical
checks last, since between them they catch one claim.

## 6 · What would change this reading

**One reader is not a measurement**, and this document is one reader. The
same caveat that discarded round 1's claim-row labels applies: three of four
disagreements there turned out to be about a row nobody had identified as
vendor-authored.

Specifically:

- **If a second reader agrees on the two inversions**, they are real and the
  golden-set question is justified on its own.
- **If a second reader splits on the §3 group**, the finding is that
  *"is this a claim at all"* is the unreliable judgement and polarity is
  downstream of it — which would make `not-a-capability-claim` the thing to fix
  and polarity a symptom.
- **If a second reader disagrees on more than 3 of the 13 I called correct**, my
  read is the instrument problem and none of the above stands.

**And the denominator, stated:** 23 claims from 13 documents of 343, extracted by
one model over one blog corpus plus a small Reddit set. It is the complete
population of stored claims and it is not a sample of anything larger. A 30% error
rate here is a fact about 23 claims, not a rate for the extractor.

---

## 7 · E2's counter-reading, recorded, and the two claims it does not cover

**Ruling from Engineer 2, 2026-08-24: polarity is not a third extractor failure.
There are two — vendor copy read as evidence, and first-hand reports missed — and
`speaking` addresses the first.**

The argument, and it is correct where it applies:

> *"state of the art on nearly all tested benchmarks"* is a positive claim, and
> what is wrong about it is **who said it**.

**I agree, and this document already scored those that way.** `clm_ea8ce84c`
(*"exceptional performance in software engineering"*), `clm_f50792ae` (*"none of
the 720 attack attempts succeeded"*) and `clm_6b9561ea` (*"gives 10%+ better
results on SWE-Bench"*) are all counted in the 13 that MATCH. A vendor asserting
excellence is making a positive claim; the defect is attribution, and `speaking`
is where it belongs. None of the 7 I called wrong is a vendor-copy case.

**Two remain that the argument does not reach, and both are single-clause
sentences by named individuals about their own testing:**

```
clm_1c6e656d  instruction.adherence  positive
              "Claude Haiku 4.5 was the easiest to attack."

clm_6bd482dd  over_refusal           positive
              "Qwen 3.8 27B is excellent, but it defaults to wildly
               overthinking things"
```

Neither is vendor copy. `speaking` on the first is `relayed-from-elsewhere` and
on the second `own-experience`, both plausibly right — so the attribution
machinery is working and the polarity is still the opposite of the sentence.

**Where that leaves the classification, stated as a disagreement rather than
resolved:** the *count* stands at 7 of 23 by my read, because a count is a
measurement and this one is reproducible from the table by anyone who wants to
re-read the quotes. Whether 2 inversions plus 5 not-a-claims constitutes a
**third failure mode** or is a tail of the second is a judgement about
classification, and that judgement is E2's to make — the taxonomy of extractor
failures is hers.

**What both readings agree on:** `speaking` is the fix for the vendor case, and
it has landed. Nothing in this section changes that.

**What would settle the remainder in one step:** the binary question in §5 —
*does the polarity match the quote* — on the next labelling round. Two readers on
23 rows is an afternoon, it needs no new pool, and it replaces this disagreement
with a count neither of us authored. Until then §6 stands: one reader is not a
measurement, and that applies to my 7 as much as to anything else here.
