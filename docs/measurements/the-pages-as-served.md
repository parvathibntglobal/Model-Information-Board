# The pages as served, and the 31 drops have four different reasons

**The pages work. Quotes render, permalinks resolve, every phrase is bound to a
claim id, and the summaries are rule-4 correct.**

**And the mis-attribution is visible on screen.** The `openai/gpt-5` page carries
the quote *"I'm now generating my summaries using GPT-5.6 Luna."* A reader sees a
quote naming one model on the page of another.

*Engineer 1 · 2026-08-21 · no writes, no model calls*

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


---

## 1 · What the endpoint actually serves

Fetched over HTTP through the ASGI app, not read from `ModelPageReader`.

```
GET /models/anthropic/claude-sonnet-5                             200
  summary   "1 of 12 tracked capabilities have any reports at all. 4 of the 11
             unreported fail silently, where an absence of complaints is not
             evidence of safety."
  states    insufficient 1 · unreported 11
  quotes    1 attached      unbound_phrases  []
  instruction.adherence  insufficient
     headline  "1 person has reported on this, which is not yet enough to
                publish a finding."
     phrase    "One person mentioned following instructions — not yet corroborated"
     quotes    ['clm_f50792aee7d3698aeab80906']

GET /models/openai/gpt-5                                          200
  summary   "2 of 12 tracked capabilities have any reports at all. 3 of the 10
             unreported fail silently…"
  states    insufficient 2 · unreported 10
  quotes    5 attached      unbound_phrases  []

GET /models/anthropic/claude-sonnet-4.5                            200
  states    unreported 12       quotes 0
```

**Quotes carry text, a resolving permalink, platform and timestamp:**

```json
{"text": "It churned away for 38 minutes and delivered this answer plus the
          files you see in this folder.",
 "permalink": "https://simonwillison.net/2026/Aug/9/sqlite-text-history-prototype/",
 "platform": "blog", "claimed_at": "2026-08-09 22:05:00+00:00"}
```

`unbound_phrases` is `[]` on every page — every rendered phrase has claim ids
behind it, which is the check that exists so a sentence cannot appear without
evidence.

### Two corrections to what to look at

**`anthropic/claude-sonnet-4.5` has no cells.** It is in the registry with three
aliases and renders **12 unreported, 0 quotes**. The model that gained a cell is
`claude-sonnet-5`, with **one** capability at insufficient. **No model on the
board has five capabilities at insufficient** — the maximum is two
(`claude-fable-5`, `openai/gpt-5`).

**And a measurement error of mine, caught here:** my first pass at this counted
`slices` in the JSON response and reported "12 unreported" for every page,
including the two with cells. The response key is `conditions`, not `slices` —
the reader's field name, not the API's. **The endpoint was right and my probe was
wrong**, which is the same shape as reading a figure against the wrong
population: the probe returned a clean, plausible, uniform answer.

### The mis-attribution, on the page

```
page      /models/openai/gpt-5
quote     "I'm now generating my summaries using GPT-5.6 Luna."
```

This is the substring defect (`gpt-5` inside `gpt-5.6`) reaching a reader. Not a
false *published* claim — the cell is `insufficient` and the phrase says "not yet
corroborated" — but a quote about GPT-5.6 is displayed as evidence about GPT-5,
with a working permalink to prove it. **Three of `gpt-5`'s five attached quotes
name GPT-5.6.**

**DONE, 2026-08-21.** The six mis-attributed claims were deleted, along with the
three cells they orphaned — a cell whose claims are gone is not rebuilt by
`rebuild_all`, because `keys_with_claims()` reads `claim`, so it would have been
left rendering `insufficient` with `quote_ids` pointing at deleted rows. That is
the worse render, and it is why the cells went too.

```
claims 12 -> 6    cells 7 -> 4    models with a cell 5 -> 3
/models/openai/gpt-5             12 unreported, 0 quotes
/models/anthropic/claude-sonnet-5 12 unreported, 0 quotes
unbound_phrases [] and 0 orphan phrases on every page
```

---

## 2 · The 31 drops, and they need four different answers

Measured on the 36 saved Willison claims by resolving each surface against
staging's population (342 models, 1385 surfaces, `c511fceb6b7fb3df`):

```
resolved -> stored        5
NOTHING  -> dropped      31
```

> ⚠ **CORRECTED.** This first read `29 NOTHING + 2 AMBIGUOUS`. The two
> "ambiguous" were an artefact of my probe, which unioned owners across every hit
> `entity.resolve` returned. `RegistrySurfaceResolver` takes the LONGEST match
> and only then refuses on `len(owners) != 1`, so `Opus 4.6` resolves correctly
> and nothing here was ambiguous. The resolver is better than the probe implied;
> the real defect is a longest match that is still a proper prefix of the
> surface's own version. `alias-coverage-and-the-prefix-defect.md` §2.

**31 dropped, not 16, and 36 extracted, not 28.** The stored figure of 8 comes
from the live run, which was a different draw.

| reason | claims | what it needs | is polling the fix? |
|---|---:|---|---|
| **a model that does not exist upstream** — `Qwen 3.8 27B` ×11, `Muse Glimmer` | **12** | nothing. These are fixture-world names; OpenRouter never listed them and never will | **No** |
| **a bare family word** — `Codex` ×3, `Claude` ×2, `Qwen` ×2 | **7** | the family-word ruling, and a family-shaped destination before it | **No** |
| **not a model at all** — `Anthropic` ×2, `OpenAI`, `Claude Code` ×2 | **5** | nothing. A vendor and a product are not models | **No** |
| remainder, long tail of one-offs | 7 | mixed | — |

**None of them is a polling gap**, so *"the extractor failed"* is right to
reject and *"the registry is behind"* is not the replacement.

### The three models named in the question resolve three different ways

```
openai/gpt-4.1        PRESENT, 2 aliases -> resolves CLEANLY to
                      openai/gpt-4.1 by longest match. Would be stored.
google/gemini-2.5-pro PRESENT, 2 aliases -> resolves CLEANLY. Would be stored.
anthropic/claude-3.7-sonnet  ABSENT from the registry -> and it does NOT drop.
                      It resolves to `anthropic/claude-3-haiku`, because
                      `claude 3` matches inside `claude 3.7 sonnet`.
                      SILENTLY WRONG, stored.
```

So of the three: **two resolve fine** and one is **worse than a drop** — a claim
about Claude 3.7 Sonnet filed against Claude 3 Haiku, because the longest alias
we hold (`claude 3`) is a proper prefix of the surface's own version.

### The one thing polling *would* fix, and it is real

```
model_version rows                 342
model_alias rows                   105
models with at least one alias      41
models with NO alias              301
```

**301 of 342 models contribute no surface to the population and can therefore
never be resolved**, however correctly a writer names them. The poller populated
`model_version` and barely populated `model_alias`.

That is the genuine polling gap, it is the largest single structural limit on
resolution, and it is invisible in every figure quoted so far — because the
models people happened to write about are mostly among the 41. **It is
`collect/`'s and it is mine.**

---

## 3 · `unreported`: your reading is right, and the copy is Engineer 2's

Taking your reading. The distinction **is** already structural:

```python
# judge/pages/model.py
@property
def unreported(self) -> bool:
    return not self.slices          # a capability with no cell
```

and a model with no cells at all takes a different path — `ModelPageReader`
returns 12 capabilities with no slices, and the summary sentence is computed from
counts rather than from cells. So nothing needs a new column or a new query to
tell the two apart: **the page already knows.** What it does not do is *say*
which.

Confirmed on the served pages — these two differ in the data and read the same in
the state field:

```
claude-sonnet-5     ops.latency_ttft   unreported   11 siblings, 1 has a cell
claude-sonnet-4.5   ops.latency_ttft   unreported   no cell on any capability,
                                                    no document ever extracted
```

**Whose it is: Engineer 2's, and it is a copy change.** The three states, the
headline, the summary sentence and the per-capability phrase all live in
`judge/pages/model.py` and `judge/curate/phrases.py`. Both are hers. Nothing in
`collect/` renders a word of it.

And the summary sentence is already 80% of the fix, which is the argument for it
being copy rather than design:

```
sonnet-5    "1 of 12 tracked capabilities have any reports at all."
sonnet-4.5  "0 of 12 tracked capabilities have any reports at all."
```

**`0 of 12` is the signal, and it is in the summary but not in the state.** A
reader scanning capability rows sees twelve identical `unreported` labels; the
distinguishing fact is one sentence above, in a different register, and is easy
to miss on a page whose body is a list.

**Going to her as a finding, not a change**, with a suggested shape rather than
an edit: a fourth state or a qualified label — *"no reports"* versus *"nothing
read about this model"* — decided by `0 of N` in the summary she already
computes. I have not touched `judge/pages/`.

The one thing I can add from this lane, and it is optional: **a per-model count
of documents mentioning the model at all**, resolvable from the population
against stored documents with no schema change. It would let the copy say *"12
documents mention this model and none discussed latency"* rather than only
*"nothing read"*. Offered, not built.

---

## What changed

Nothing. Reads and HTTP fetches only.

**Open before the presentation:** the six mis-attributed claims are still in the
database and three of them are visible as quotes on `/models/openai/gpt-5`.
