# Round 3, first reading: the extractor could not give 21 of the 36 answers

**2026-09-22. Labeller: anooj. Transcribed by `scripts/load_round3_labels.py`,
validated by `scripts/check_labelling.py --source` (exit 0, no row drift).**

`fixtures/golden/capability-choice-round3--labelled-by-anooj.jsonl`

⚠ **A FIRST READING, AND TWO CONDITIONS BOUND WHAT IT SUPPORTS.** Both are in
the file's own `_meta.caveats`, not only here. §5.

---

## 0 · Population, and what it is not

36 claims, **33 distinct quotes**, 15 documents — **one site, one author, one
extractor (`google/gemini-2.5-flash`), one draw**, run 2026-08-21. The extractor
is nondeterministic: the same 30 documents have produced 8, 28 and 36 claims on
three runs.

**This is not a misfiling rate for the pipeline.** It is a rate for one
engineer's blog as read by one extractor on one afternoon.

Three rows share one quote (9, 20, 35 — a sentence naming three vendors) and two
share another (1, 8). So `not-a-capability-claim`'s 12 rows are **9 distinct
quotes**, and the 36 are 33.

---

## 1 · The ceiling, before extractor quality enters

The extractor's tool-schema enum offers the **twelve ratified keys and nothing
else**. `no-key-fits` and `not-a-capability-claim` are answers it **cannot
give** — not answers it got wrong.

```
21 of 36 rows  (58%)  gold says one of those two
10 of 36 rows  (28%)  gold picked a ratified key  <- the ONLY rows where agreement is possible
 5 of 36 rows  (14%)  cannot-tell, about the pool
```

**Maximum possible agreement is 10 of 36 = 28%.** Any headline below that
measures the instrument, not the extractor.

---

## 2 · The three-way split

### A · Gold picked a ratified key — **7 of 10 agreed (70%)**

```
OK  row  2  code.generation                     = code.generation
OK  row  4  reasoning.multistep                 = reasoning.multistep
OK  row  5  tool_calling.long_chain_reliability = tool_calling.long_chain_reliability
XX  row  7  code.generation                     ≠ code.editing_diff_fidelity
OK  row 16  code.generation                     = code.generation
OK  row 21  code.generation                     = code.generation
XX  row 24  reasoning.multistep                 ≠ over_refusal
OK  row 28  ops.latency_ttft                    = ops.latency_ttft
XX  row 29  code.generation                     ≠ code.editing_diff_fidelity
OK  row 33  code.generation                     = code.generation
```

**Two of the three disagreements are the same confusion** — `code.generation`
read as `code.editing_diff_fidelity` (rows 7, 29). That pair is deliberately
separate in `capabilities.yaml` ("cheap models routinely write fine code and
cannot produce a clean diff"), and the boundary is exactly what the
`description` the extractor never saw is for.

### B · Answers the extractor structurally could not give — **21 of 36 (58%)**

```
not-a-capability-claim  12 rows  (9 distinct quotes, 7 documents)
no-key-fits              9 rows  (9 distinct quotes, 6 documents)
```

**Every one of the 21 got a ratified key anyway**, because the prompt said to
pick the closest and the schema had no way to decline. What the 12
`not-a-capability-claim` rows were filed as:

```
 4  reasoning.multistep        3  code.generation           1  instruction.adherence
 1  over_refusal               1  summarization.fidelity    1  ops.latency_ttft
 1  tool_calling.long_chain_reliability
```

Row 17 — *"scores 52 on the Artificial Analysis Intelligence Index"* — is
`reasoning.multistep`. Row 26 — *"Qwen supports Multi-Token Prediction, an
architectural…"* — is `ops.latency_ttft`. Neither quote is about a model
behaving.

### C · `cannot-tell` — 5 rows (0, 14, 18, 19, 23)

About the **pool**, not the extractor, and caused by §5's first condition.
Excluded from the accuracy arm.

### Denominators, kept apart

```
7/36 = 19%   what `score_golden.py round3` prints. Conflates all three groups.
7/31 = 23%   over the 31 usable rows (cannot-tell excluded).
7/10 = 70%   over the rows where agreement was POSSIBLE.
```

**None of the three is "the extractor is 19% accurate".** The first is
dominated by a ceiling the extractor cannot reach; the third is the only one
about its judgement, and it rests on ten rows.

---

## 3 · The finding: nine `no-key-fits` are not nine missing keys

**Four of the nine are one missing key, and the extractor put all four in the
same wrong place.**

```
row 15  "none of the 720 attack attempts succeeded …"          -> instruction.adherence
row 25  "… prompt injection and data exfiltration …"           -> instruction.adherence
row 27  "Claude Haiku 4.5 was the easiest to attack."          -> instruction.adherence
row 30  "Auto mode would have blocked 89% of those actions."   -> instruction.adherence
```

Unanimous. Not four scattered guesses — one systematic landing place.

**The corpus agrees, and so did the extractor's own proposal channel.**

`capability_candidate` already holds **`security.prompt_injection_resistance`,
proposed twice, from two independent documents** — and one of the two quotes
**row 15 verbatim**. The extractor identified the gap unprompted, on the same
row, while being forced to file the claim under `instruction.adherence`. All
160 candidates are still `ruling: null`.

Corpus-wide, with denominators:

| | entries | documents | authors | models | platforms |
|---|---|---|---|---|---|
| **resist an attack** | 20 | 10 | 8 | 10 | 3 |
| **perform an attack** | 25 | 11 | 10 | — | — |

The defensive 20 sit under `instruction.adherence` (11), `over_refusal` (7) and
`reasoning.multistep` (2) — the `vision` dispersal shape, three keys and none of
them the right one. At 8 authors across 3 platforms it clears the gate's
diversity bar and has never had a key to accumulate under.

**⚠ TWO KEYS, NOT ONE, AND MERGING THEM WOULD REPEAT THE DEFECT THIS STARTED
FROM.** Resisting an attack and performing one are different capabilities with
different failure modes. The board already carries `cybersecurity` (7 entries)
sitting across both, which is a key wide enough to take anything — the same
shape as `extraction.faithfulness` absorbing facial recognition.

Also for a person, not for code: `prompt-injection-resistance` (4) and
`prompt-injection-robustness` (1) are one thing spelled two ways.
`normalise_slug` must **not** fold them — that is meaning, not punctuation
(rule 10's boundary).

**The other five `no-key-fits` do not cluster**: rows 3, 10, 22, 32, 34 are
five different subjects. Nine is not one finding; four is.

---

## 4 · What this does and does not say about the two shipped steps

**Does not say either helped.** This gold scores the **bare-key `e5.4`
extractor** — the frozen sidecar. No extraction has run under `e5.5`, so the
*after* arm does not exist. The comparison is one gold against two runs, and
only one run has happened.

**Does say the ceiling was real.** 21 of 36 rows needed an answer the schema
could not express, which is precisely what making `legacy_score_key` optional
was for. Whether the extractor now *uses* the empty answer on these rows is the
unrun measurement.

**Is evidence for the `security.*` key**, and that is a
`contract/capabilities.yaml` change — a proposal and two eyes, not an edit.

---

## 5 · The two conditions, and why they are in `_meta`

Recorded in the file itself so a reader of the figure meets them there:

**1 · Labelled without `source_document_text`.** The pool's own question is
*"Read the quote, then the document it came from"*; the render the labeller
worked from carried quote and model only. **Five rows are `cannot-tell` for that
reason** — the option doing its job, not a labeller failing — so the accuracy
arm has **31 usable rows, not 36**.

**2 · Labelled without the twelve keys' `description` and `sounds_like`.** The
pool's rationale states a labeller *"cannot choose between `ops.latency_ttft`
and `over_refusal` from the key names alone"*. **This gold therefore carries
LESS information than the pool intended**, which cuts the usual asymmetry the
other way: normally the labeller is better informed than the extractor and a
disagreement is an upper bound on what definitions could fix. Here both were
working from names alone, so a disagreement in §2A may be the extractor's or may
be the labeller's missing context, and **the 7/10 cannot separate them**.

That condition bears hardest on exactly the rows it would: the two
`code.generation` / `code.editing_diff_fidelity` disagreements are the pair
whose boundary lives in the description neither party saw.

**A second reading is coming** on `round3-for-labelling-with-context.md` — the
same 36 rows with the document text and the definitions. **It is its own record
and not a trend against this one.** Same rows, same options, more information:
a disagreement between the two readings measures what the missing context was
worth, which is a different question from agreement between two people.
