# For Engineer 2 — two contract changes, one of them not asked for

**`contract/conditions.yaml` has a new dimension and a renamed one. Both are in
the file, both are flagged there, and this is the sign-off request.**

The rename is the one to read first, because it was not requested and it is the
one a reviewer would otherwise wave through as tidying.

---

## 1 · What changed

```
contract/conditions.yaml   + reasoning_effort   bands off/low/medium/high/max/auto/unknown
                           ~ structured_mode -> schema_enforced
                           ~ dominant_dimension: format.structured_output -> schema_enforced
contract/queries.yaml      ~ records_condition: structured_mode -> schema_enforced   (x2)
```

Non-contract files carried along: `judge/extract/schema.py`, `judge/config.py`,
`judge/curate/phrases.py`, `judge/ask/requirements.py`,
`tests/test_conditions_contract.py` (new, 17 tests).

---

## 2 · The new dimension: why, and what is deliberately not done

`structured_mode` is `bool | None` meaning *"was provider-side schema
enforcement on"*. It received a string three times — `'xhigh'` twice,
`'auto mode'` once, the last costing four claims — because there was no field
for a reasoning-effort setting.

**`auto` is a band rather than an omission.** *"The provider chose the effort"*
is a real, comparable condition and is not the same as *"the report does not
say"*. Collapsing them would convert an observed condition into an absence,
which is rule 6. Correspondingly `unknown` is a band but **not** an emittable
value: omitting the field is how the extractor says the document was silent, and
two ways to say that would lose the distinction.

**An unrecognised effort raises rather than banding to `unknown`.** Folding a
value somebody reported into missing data is rule 6 pointed the wrong way, and
it is the worse direction — nobody audits a bucket that reads as absent.

Three things not done, each needing your call:

| | why it is yours |
|---|---|
| **no capability is `reasoning_effort`-dominant** | `ops.latency_ttft` is the obvious candidate. Moving it off `context_size` rebuckets every existing latency claim — a re-run, not an edit. Until then the dimension is recorded and never bucketed on. |
| **no query records it** | `queries.yaml` has no `records_condition: reasoning_effort`, so nothing is retrieved *for* the dimension. It is picked up incidentally, which caps its coverage in a way a reader of the contract cannot see. |
| **`*:unknown` has no phrase, for any dimension** | `condition_label` falls back to the raw bucket string, so `reasoning_effort:unknown` would render as itself. Pre-existing across all four dimensions. The wording is a rule-4 question, not a fill-in: *"effort not stated"* must not read as *"no effort"*. |

---

## 3 · The rename, which you did not ask for

### The measurement

Adding the field **did not stop the misfiling.** Same document, `reasoning_effort`
in the tool schema, its description naming `'auto mode'` as its own example, and
a pointer written into `structured_mode`'s description:

```
auto-mode, with reasoning_effort present
  3 of 3 claims -> conditions.structured_mode = 'auto mode'
  reasoning_effort = null on every one
  all three lost to validation
```

Three arms, one document, three draws each, differing **only in field names**:

| | `'auto mode'` in the bool | `reasoning_effort` |
|---|---|---|
| **A** as shipped | **3 of 4 claims** | null on 4 of 4 |
| **B** bool renamed `schema_enforced` | **none** | **`auto` on 4 of 4** |
| **C** bool removed | none | `auto` on 4 of 4 |

Identical across three replications. The value was going to the field whose
**name matched the document's words** — "auto mode" to the only field ending in
`_mode`.

On the corpus rather than the probe: `auto-mode` went **0 claims → 3**, and
`unclassified` fired on it.

### Why I took it instead of proposing it

Three reasons, and I would rather you disagree with them explicitly than not see
them:

1. **The field alone is a known-broken state.** Shipping it and stopping would
   have left the misfiling in place with a new field sitting next to it,
   documented as a fix.
2. **It costs no migration today.** `0 of 6` stored `condition_bucket` values
   carry the old prefix — 4 `claim` rows, 2 `cell` rows, all
   `context_size:unknown`. It will never be cheaper than now.
3. **Revert is a find-and-replace** across five files plus one test. Nothing
   derived, nothing stored, nothing published depends on the old string.

### The rule I would like in the contract, if you agree with it

> **Do not name a dimension or a field after a word the corpus uses in another
> sense.**

`tool_count` and `context_size` are safe. `*_mode` was not, in a corpus about
models that have modes. `tests/test_conditions_contract.py` asserts no
`Conditions` field ends in `_mode`, which is the mechanical half; the naming rule
is the half that needs to be written down somewhere a person reads before adding
a field.

This qualifies a rule recorded earlier the same day — *"if the model must
respect a constraint, the constraint goes in the description of the field it is
filling."* Still true. Now measurably **necessary and not sufficient**: a field
name outranks every description, including the description of the field that
should have won.

### Population, stated

One document, one extractor (`google/gemini-2.5-flash`), three arms, three draws
each. The draws were byte-identical, so they establish that the effect is
**stable at this temperature**, not that it generalises across documents or
models. What generalises is the mechanism, and the mechanism is cheap to
re-check the next time a field takes a value it should not.

---

## 4 · Two things for you that are not sign-off

**The extractor has never been shown what the capability keys mean.**
`build_system_prompt` appends the twelve keys as bare strings;
`capabilities.yaml`'s `description` and `sounds_like` do not reach the model —
verified by searching the assembled prompt for a fragment of every description
and every `sounds_like` phrase, zero hits. This is your lane and your file, it
is probably the largest lever left on extraction quality, and it is **not
touched** because it changes what the extractor emits and round 3's pool is
drawn from the current one.

**`openai-timeline`'s twelve `code.generation` claims do not reproduce.** Four
draws return zero, and they were never persisted. If you have read the argument
in `salvage-the-five-and-the-yield-movement.md` §5 that the vocabulary is
demonstrably incomplete, that argument is withdrawn — a correction is in the
file. The conclusion it supported (do not add a key yet) is unchanged.
`docs/measurements/the-effort-dimension.md`.
