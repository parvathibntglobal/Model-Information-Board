# For Engineer 2 — `unreported` is two states and the page says one

**A finding, not a change. `judge/pages/` is untouched.**

> ⚠ **THE 301 FIGURE ON THIS PAGE IS WRONG, AND SO IS THE CONCLUSION DRAWN FROM
> IT. CORRECTED 2026-08-21.**
>
> I measured resolution with my own query — `SELECT mv.id, ma.surface FROM
> model_version mv LEFT JOIN model_alias ma …` — so the 301 models with no
> `model_alias` row contributed **no surface** and could not resolve. That is a
> property of my query, not of the system.
>
> **The production path never touches `model_alias`:**
>
> ```python
> # collect/surface_resolver.py  RegistrySurfaceResolver.from_connection
> rows = conn.execute("SELECT canonical_id, display_name FROM model_version")
> population = build_population([(r[0], r[1]) for r in rows])
> ```
>
> `build_population` derives surfaces mechanically from the canonical id and the
> display name, for **every** model. So **all 342 are resolvable**; `model_alias`
> holds *curated* surfaces for the seated tracked set and is not the resolution
> input.
>
> **This is the 55-to-77 ruling working exactly as written** — the sweep covers a
> few, the registry resolves everything — rather than contradicting it. I had it
> as a coverage gap and it is not one.
>
> Measured consequence, on the 176 saved blog claims:
>
> | | my query | production |
> |---|---:|---:|
> | surfaces in the population | 1,342 | 1,224 |
> | claims resolving | 9 | **25** |
>
> And the models I called synthetic are real registry rows: `qwen/qwen3.8-27b`
> (11 claims), `openai/gpt-5.6-sol`, `openai/gpt-5.6-luna`,
> `openai/gpt-5.6-sol-pro`, `google/gemini-3.7-flash`,
> `anthropic/claude-sonnet-4.5`.
> `docs/measurements/the-population-i-starved.md`


`unreported` renders identically for *a capability nobody discussed* and *a model
nothing has ever been read about*. **337 of 342 models are the second kind**, so
almost the whole board reads as silence when it is absence of looking.

---

## The distinction is already structural, which is why this is copy

Nothing needs a column, a query or a schema change. The page already knows:

```python
# judge/pages/model.py
@property
def unreported(self) -> bool:
    return not self.slices        # a capability with no cell
```

A capability with no cell and a model with no cells at all reach that property by
different paths, and your summary sentence already computes the difference:

```
/models/anthropic/claude-sonnet-5    "1 of 12 tracked capabilities have any
                                      reports at all. 4 of the 11 unreported
                                      fail silently…"
/models/anthropic/claude-sonnet-4.5  "0 of 12 tracked capabilities have any
                                      reports at all. 4 of the 12 unreported…"
```

**`0 of 12` versus `1 of 12` is the whole signal, and it is already there.** So
this is not a design gap — it is that the signal lives in one sentence above a
body of twelve identically-labelled rows, in a different register, on the page a
customer scans rather than reads.

Measured on the served pages, these two differ in the data and are identical in
the `state` field:

```
claude-sonnet-5    ops.latency_ttft   unreported   11 siblings, 1 has a cell
claude-sonnet-4.5  ops.latency_ttft   unreported   no cell anywhere, no document
                                                   ever extracted for this model
```

## Why it is a rule-4 question rather than a display preference

Rule 4 says absence of evidence must never read as evidence of capability, and
the page honours that: *"Nobody has publicly discussed this"* is distinct from
*"engineers report problems"*, and `needs_positive_consensus` marks the silent
failures. That part works.

**What the rule does not currently name is a second confusion one level in:
absence of evidence versus absence of looking.** A reader who sees twelve
`unreported` rows on `claude-sonnet-4.5` has no way to know we have never read a
document about it — and that is a stronger caveat than the one they are being
given, because it says nothing about the model at all.

## Suggested shape, and it is yours to pick

A fourth state, or a qualified label, decided by the `0 of N` you already compute:

```
unreported    "Nobody has publicly discussed this"      N > 0
unexamined    "No document we have read mentions this   N == 0
               model"
```

Both strings live in `judge/curate/phrases.py`; the state lives in
`judge/pages/model.py`'s `state` expression. Both are yours, and I have changed
neither.

## One thing offered from `collect/`, not built

If a stronger sentence is wanted than *"nothing read"*, I can supply **a
per-model count of documents mentioning the model at all** — resolvable from the
surface population against stored documents, no schema change, no model call.
That would let the copy say *"12 documents mention this model and none discussed
latency"*, which separates a swept-and-quiet model from an unswept one.

Say the word and it is a read; I have not built it, because the copy decision
comes first and might not need it.

## Context you may want, because it changes the size of the problem

`model_alias` holds **105 rows across 41 of 342 models**, so 301 models can never
resolve a claim however correctly a writer names them. Those 301 will render as
`unreported` forever, and *"unseated"* is a third thing again — arguably a
coverage-page concern rather than a model-page one.
`docs/measurements/alias-coverage-and-the-prefix-defect.md` has the numbers and
the recommendation (seat on demand, and state the ruling as it actually is).

Not blocking anything. But if a fourth state is being added, the existence of a
possible fifth is worth knowing before the vocabulary is fixed.
