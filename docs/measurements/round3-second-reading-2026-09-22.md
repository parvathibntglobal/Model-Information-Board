# Round 3, second reading: what the missing context was worth

**2026-09-22. Labeller: anooj.** Transcribed by `scripts/load_round3_labels.py`,
validated by `scripts/check_labelling.py --source` (exit 0, no row drift).

`fixtures/golden/capability-choice-round3--second-reading-by-anooj.jsonl`
— written with `--out`, so
`capability-choice-round3--labelled-by-anooj.jsonl` (the first reading) is
untouched.

⚠ **NOT A TREND AND NOT A SECOND LABELLER.** Same 36 rows, same 15 options, one
labeller. What changed is the information: this reading had
`source_document_text` **and** the twelve keys' `description` and `sounds_like`,
both of which the first reading lacked. A disagreement between the two measures
**the context**, not the reader and not the extractor.

Labelled from `docs/measurements/round3-for-labelling-with-context.md` as of
commit `043a18b`. That file's layout has since been changed — §5.

---

## 1 · What moved

**Nine rows of 36 changed.**

```
row  0  cannot-tell                        -> not-a-capability-claim
row  2  code.generation                    -> no-key-fits
row  3  no-key-fits                        -> code.generation
row  5  tool_calling.long_chain_reliability -> tool_calling.schema_accuracy
row  6  not-a-capability-claim             -> code.generation
row  7  code.generation                    -> not-a-capability-claim
row 14  cannot-tell                        -> no-key-fits
row 18  cannot-tell                        -> code.generation
row 22  no-key-fits                        -> reasoning.multistep
```

```
first :  ratified 10   impossible 21   cannot-tell 5
second:  ratified 12   impossible 22   cannot-tell 2
```

**`cannot-tell` resolved on 3 of 5** — rows 0, 14, 18. Rows 19 and 23 remain,
for different reasons (§4).

---

## 2 · The ceiling moved and the agreement did not

Only a row whose gold is a **ratified key** can ever agree with the extractor,
whose tool-schema enum offers the twelve and nothing else.

```
first : ceiling 10/36 = 28%    agreed 7/10 = 70%
second: ceiling 12/36 = 33%    agreed 7/12 = 58%
```

**The agreed count is 7 in both readings.** The context added two rows on which
agreement was *possible* — 6 and 18 — and the extractor is wrong on both. So the
rate fell from 70% to 58% while nothing about the extractor changed and no
previously-agreeing row flipped.

**That is why the rate is the wrong headline.** 70% and 58% are the same seven
rows against two different denominators, and the denominator moved because the
labeller could see more. Report the ceiling and the count; the ratio is a
property of how much context the gold had.

---

## 3 · Direction — and it is not one-way

```
 3  impossible  -> ratified      rows 3, 6, 22
 2  cannot-tell -> impossible    rows 0, 14
 2  ratified    -> impossible    rows 2, 7
 1  cannot-tell -> ratified      row 18
 1  ratified    -> ratified      row 5
```

**Four rows became "the claim should not exist" with context** — 0, 2, 7, 14 —
and rows 0 and 7 are the clean instances of it: more information made the
labeller *readier* to say the claim should not exist, not less.

**But four moved the other way**, out of `impossible` or `cannot-tell` and into
a ratified key. Net movement into `impossible` is **+1** (21 → 22).

So the honest summary is **resolution, not drift**. Context did not push the
labelling systematically toward "no claim"; it let a hedged or wrong answer
become a definite one in whichever direction the document pointed. Worth stating
because "more context made me readier to reject claims" is true of rows 0 and 7
and would be a mis-description of the nine.

**Two changes name their own cause:**

- **Row 22** moved to `reasoning.multistep` because the key's `sounds_like`
  lists **"confidently wrong" verbatim**, and the quote is *"Neither of you has
  any idea whether any of it is true…"*. The first reading had no `sounds_like`
  to see. This is the definitions half of the context doing work on its own,
  independent of the document.
- **Row 2** is §6.

---

## 4 · The two remaining `cannot-tell`, and one is a labeller error

**Row 23 — a property of the quote.** It names four capabilities and cannot be
reduced to one. No caveat is owed to the pool or the tooling; the option is
doing its job.

**Row 19 — labeller error, and it was first attributed to the artifact.**

The reason offered was that the document render truncated before the sentence
appeared, "a render defect rather than a pool defect". **Checked, and it is
neither:**

```
pool      all 36 quotes appear in their own stored source_document_text
          row 19's document is 12,508 characters, ending on a complete sentence
render    row 19's section is 203 lines: <details> at 6, fence pair at 8 and
          197, </details> at 199 — the quoted sentence at line 91, well inside
file      the quote is present in every one of the 36 rendered sections
```

The labeller read the file in batches, stopped short of line 91, and attributed
their own truncation to the artifact. **Recorded as labeller error** in
`_meta.caveats`.

⚠ **AND THE LAYOUT IS STILL A REAL DEFECT, WHICH IS THE PART TO ACT ON.** The
file did not truncate, but a 203-line fenced block nested inside a `<details>`
is the shape that makes a long document look finished before it is. The error
was the labeller's; the invitation was mine. §5.

---

## 5 · The layout is fixed for a third reading

`round3-for-labelling-with-context.md` regenerated:

- **no `<details>`** — nothing collapses
- **no fences** — four-space indentation instead, which renders as a code block
  in every viewer, cannot mis-nest against backticks inside a document, and
  still shows the text in a viewer that ignores it
- **an explicit end marker per row**:
  `[end of document — 188 lines, 12508 characters]`
- a header line telling the reader some documents run to several hundred lines

Verified: 0 `<details>`, 0 unindented triple-backtick lines, 36 end markers, and
all 36 quotes present in their own section.

**The old layout is preserved in git at `043a18b`**, which is what the second
reading was labelled from. The regeneration is for a third reading and does not
alter this record.

---

## 6 · Row 2 changes the security proposal

```
row 2   code.generation  ->  no-key-fits
```

> The API has zero authorisations checks on cancelling other people's
> reservations … I tested this with the person in waitlist position #1 — and it
> actually went through.
>
> — OpenClaw (running Opus 4.6), **hacking an Australian gym-booking website**

Quote alone it is a bug report about a booking API and the first reading filed
it `code.generation`. With the document the speaker is **the model**, performing
the attack — and the labeller says no ratified key names it.

**So the offensive cluster now has a labelled `no-key-fits` row**, which it did
not have when `docs/proposals/two-security-keys-not-one.md` and PR #396 were
written. That PR asks *one PR or two*, on the grounds that the defensive key had
golden-set evidence and the offensive key had corpus evidence only. **That
asymmetry is smaller than stated.**

It does not collapse entirely, and the difference is worth keeping:

```
defensive   4 labelled rows (15, 25, 27, 30), all mis-filed to one key,
            plus two independent capability_candidate proposals, one quoting
            row 15 verbatim
offensive   1 labelled row (2), and NO claim from that document is stored in
            the database at all — so it is not among the offensive cluster's
            25 board entries either
```

One row against four, and a row whose claim the pipeline has never persisted.
Recorded on PR #396 rather than settled here: it is evidence for the offensive
key, not a decision about how to ship it.

---

## 7 · Artefacts

```
fixtures/golden/capability-choice-round3--second-reading-by-anooj.jsonl
round3-second-reading-labels.txt                 the answers as handed back
docs/measurements/round3-readings-compared.py    every figure in §1-§3
```

The first reading's record is `round3-first-reading-2026-09-22.md`. Neither
supersedes the other: one is the gold as it stood without context, one with.
