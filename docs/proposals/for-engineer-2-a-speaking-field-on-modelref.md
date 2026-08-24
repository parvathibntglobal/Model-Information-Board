# Three token-efficiency reports, three mechanisms, one class of evidence

**Three first-person reports of a model's token spend are off the board for three
different reasons, at three different stages. All three are the same shape:
first person, own use, no citation — the one class of evidence this project
exists to publish.**

```
qwen-38-27b            the extractor proposed 12 claims and ALL 12 were
                       discarded, because 2 of the 12 quotes exceeded
                       MAX_QUOTE_CHARS = 200. Schema validation is
                       all-or-nothing per document.

deepseek-v4-pro-0813   the extractor read it, judged the observation
                       unmappable to the capability vocabulary, and left
                       `unclassified` EMPTY - the escape hatch the prompt
                       provides for exactly this went unused.

oqocfjv                never reaches extraction in the corpus staging
                       holds; and bare `Fable` is a family word, so it
                       would resolve to no model if it did.
```

Verification, capability mapping, entity resolution. **Three independent
mechanisms converging on the same class of evidence** — which is worth more than
either failure below, because no single fix touches more than one of them.

And the pre-registration named **verbosity / overthinking** as one of only two
capabilities this corpus could support. It appeared in neither run. A prediction
failing quietly belongs next to the ones that held: §1 (one voice), §2 (template
quotes), §4 (unsupported keys) all held; §3's yield band and §3's document
identification and this one did not.

*Engineer 1 · 2026-08-21 · evidence in `round2-two-labellings.md`,
`blog-extraction-run.md`, and a 2-call targeted re-run (6,068 in / 1,374 out)*

---

## 0 · What the three actually say

**`qwen-38-27b`** — 12,508 characters, the longest document in the corpus:

> *"I've been running the model on two different machines: my 128GB M5 Max
> MacBook Pro, and an NVIDIA DGX Spark."*
> *"#### The default of extra high results in spectacular over-thinking"*

**`deepseek-v4-pro-0813`** — 1,015 characters, one of the four the
pre-registration named as first-hand:

> *"Interestingly I got very different looking pelicans for the three different
> reasoning levels of low, medium, and high. I've not noticed this kind of
> difference from any other model."*

**`oqocfjv`** — a Reddit comment, on a paid plan rather than own hardware:

> *"Our usage isn't getting reset? So I went ham for nothing earlier today …
> (Fable uses up more tokens than a old Porsche gas)"*

No citations, no bylines, no vendor. Two on the author's own machines, one on his
own usage. **There is no provenance ambiguity in any of them**, which is the
point of putting them at the top of a proposal about a provenance field.

### The three mechanisms, measured rather than inferred

A targeted re-run of the two blog documents, capturing what the first run did not
record:

```
qwen-38-27b
  proposed 0   verified 0   UNCLASSIFIED []
  no_claim_reason: 'extractor returned nothing parseable against the schema'
  underlying: 2 validation errors - claims.10.quote and claims.11.quote,
              'String should have at most 200 characters'

deepseek-v4-pro-0813
  proposed 0   verified 0   UNCLASSIFIED []
  no_claim_reason: 'The document mentions a model and some observations, but no
   clear claims about its capabilities that fit the defined vocabulary. The
   observations about "different looking pelicans for the three different
   reasoning levels" are too vague to map to a specific capability.'
```

**`qwen-38-27b` is the sharpest and it is not a judgement failure at all.** The
extractor proposed **at least 12 claims** — the errors name `claims.10` and
`claims.11` — and every one was thrown away because two quotes were long. This is
the same failure as `introducing-muse-glimmer`, which I reported as *"1 of 30 lost
to a length ceiling"*. It is **2 of 30**, and the second is the longest document
in the corpus with twelve proposed claims in it.

**`deepseek-v4-pro-0813` is a vocabulary failure with a broken escape hatch.**
The prompt says: *"Do not stretch a quote to fit a capability. A quote that fits
none of them goes in `unclassified` — that list accumulating is how we learn the
vocabulary is short."* The extractor decided the observation fitted no capability
and **left `unclassified` empty**. So the channel built to reveal a missing key
did not fire, and a missing key is exactly what is there to reveal:

```
the 12 keys handed to the extractor include exactly one ops key:
    ops.latency_ttft        time to first token
nothing for token spend, output length, or reasoning-effort cost
```

**There is no capability key for verbosity.** So even had it mapped, there was
nowhere to file it — and the mechanism that would have told us is unused.

---

## 1 · Two failures, and now three mechanisms. One fix covers one of them

```
FAILURE 1  relayed text stored as a report
           -> a `speaking` field addresses this

FAILURE 2  first-hand reports not reaching the board
           -> it does not, and the three mechanisms above are all
              distinct from provenance and from each other
```

Tightening the prompt toward *"is this the author's own experience"* — the
direction failure 1 pushes — is the direction that already dropped one of these.
**Keeping them separate is the point of leading with them.**

What failure 2 needs, none of it proposed here and none of it a prompt change:

1. **Per-claim validation instead of per-document.** Twelve claims should not die
   for two long quotes. Whether that is a partial accept, a repair loop, or a
   quote-length guard in the prompt is a design question — but 2 of 30 documents
   lost their entire yield to it, and one of those had twelve claims.
2. **A verbosity or token-spend capability key**, or a ruling that the board does
   not hold that capability. Three of the three reports above are about it.
3. **`unclassified` needs to be reached.** It is the designed signal for (2) and
   it is empty on the one document that should have filled it.

---

## 2 · The proposal: a required `speaking` enum on `ModelRef`

```python
Speaking = Literal[
    "own-experience",
    "vendor-about-own-model",
    "relayed-from-elsewhere",
]


class ModelRef(BaseModel):
    surface: str = Field(description="exactly as the human wrote it")
    resolved_version_id: str | None = None
    specificity: Specificity
    resolution_confidence: float = Field(ge=0.0, le=1.0)
    speaking: Speaking = Field(
        description=(
            "WHOSE claim this is, not whether it is true. "
            "own-experience: the writer is reporting what happened when THEY "
            "used the model - their run, their session, their bug. "
            "vendor-about-own-model: the writer is the vendor, or speaking for "
            "it, describing their own model - an announcement, a model card, a "
            "release post. "
            "relayed-from-elsewhere: the writer is repeating a claim somebody "
            "else made - a benchmark, a model card, another post. A citation is "
            "the tell. "
            "A verbatim quote from an announcement is relayed or vendor, never "
            "own-experience, however exactly it is quoted."
        )
    )
```

**Required, not nullable — agreed, and the reason is worth stating in the field's
own terms.** A claim without a `speaking` value is a claim nobody can audit for
provenance, which is the state the four claims on staging are in now: three of
them quote a vendor announcement and nothing in the row says so. A nullable field
would reproduce `resolved_version_id` — a schema field with a `None` default that
nothing ever wrote, while the pipeline logged "resolves to no tracked model" for
months and dropped every claim.

`vendor-about-own-model`, not `-own-product`: round 2's document rows split on
Modular quoted about **Mojo**, a programming language. The option said *product*,
the question said *a claim about a model*, and one labeller took each.

### Weighting only, never storage — agreed, and it constrains what comes next

Gating storage means a claim the model mislabels vanishes with no record, and the
field has never run, so its accuracy is unmeasured **on exactly the decision it
would be making**. Weight it down, keep it, revisit when the golden set can say
how often it is right.

Two consequences worth naming now:

- **This is `f_evidence` territory and `f_evidence` has no supplier.**
  `DEFAULT_EVIDENCE_TIER = "D"` (0.12) is hardcoded at both call sites, and tier
  F — *"vendor marketing — capability FACTS only, never quality"* — is 0.02, a 6×
  difference. A `speaking` value of `vendor-about-own-model` is the signal that
  should select F. So the first honest use of the field is to give `evidence_tier`
  a source, not to add a seventh factor.
- **Keeping the claim means it still counts as a voice.** `gate.count` reads no
  specificity and would read no `speaking` either, so a down-weighted
  vendor claim is still one `independent_voices`. Weighting alone does not stop
  three announcement sentences reading as three people. That is the same gap the
  family-specificity arithmetic showed and it needs the counting rule either way.

---

## 3 · Where the vocabulary came from

Not drafted for the schema. Each term is the residue of a disagreement two people
had over real rows:

| term | why it exists |
|---|---|
| `own-experience` | round 1's `first-hand-observation`, renamed to say **whose** hand. The old wording — *"the writer is reporting something they observed themselves"* — is literally true of a vendor announcement and meant the opposite of its purpose. |
| `vendor-about-own-model` | round 1 had **no name for this**. Three of its six disagreements were quotes from a root post by `ClaudeOfficial` announcing their own model, with no row saying so. |
| `relayed-from-elsewhere` | round 1's `relayed-vendor-claim`, renamed because a commenter repeating a model-card number is not a vendor and the old name forced them into one category. |

Derivation in `extraction-baseline-two-labellings.md` §5.

---

## 4 · The evidence, and one half is not corroborated

Round 2 claim rows, `who_is_speaking`:

| corpus | rows | anooj | yathu answered | agreed |
|---|---:|---|---:|---:|
| reddit-thread | 4 | **4 of 4 `vendor-about-own-product`** | **0** | **—** |
| blog | 8 | **8 of 8 `own-experience`** | 5 | **4 of 5** |

**`own-experience` is corroborated. `vendor-about-own-model` is not.** Zero
overlap on the four rows that carry it — one person, four rows, one announcement
thread. Three blog claim rows also have one labeller, and the fifth blog
disagreement is row 13, the Florian Herrengt attribution conflict, which is a
pool defect rather than a vocabulary one.

*A correction to how I quoted this earlier:* "8 of 8 by both" is wrong. It is 8 of
8 by anooj and 4 of 5 where both answered. Conclusion unchanged, strength not.

Beside it, the failure the field addresses is measured and not in doubt: the
pre-change extractor produced **4 claims from the Reddit thread, all 4 vendor
announcement text**, and **8 from the blog corpus, all 8 the author's own runs**.

Yathu's rows are being chased separately, so this proposal waits on them rather
than blocking on them.

---

## 5 · Why the schema and not the prompt — a general finding

**The model reads the field it is filling.** A forced tool call puts every field
description in context at the moment the value is chosen, attached to the thing
being decided. Prose in a system prompt is in context too, and attached to
nothing.

```
tool schema handed to the model     4,946 characters, 18 descriptions
system prompt (with vocabulary)     2,714 characters, 17 non-blank lines
                                    -> the schema is 1.8x the prompt
```

*Corrections to the figures as quoted:* 18 descriptions in the generated tool
schema (14 explicit `Field(description=…)`, the rest model docstrings) against 17
non-blank lines — not 15 against 12. And 199,000 characters is not from this
corpus: the blog corpus is **55,761 characters** across 30 documents, median
1,109, largest 12,508. The 48,945 input tokens is 30 calls each carrying the
prompt again.

The direction survives both, and the evidence that prose loses is in this
pipeline's history — **now three times, and none about `speaking`:**

- *"Choose the SHORTEST span that carries the claim"* is in the prompt. Two of
  thirty documents lost their entire yield to `MAX_QUOTE_CHARS`, one of them
  twelve claims. The prose asked; only the constraint acted, and it acted by
  discarding.
- *"A quote that fits none of them goes in `unclassified`"* is in the prompt.
  `unclassified` is empty on the one document whose stated reason was that
  nothing fitted.
- The prompt says nothing about the thread root, and the extractor has been
  inheriting the subject anyway — 3 of 4 stored claims quote text naming no
  model, all recorded `specificity=version`, with no field able to say so.

**A distinction the pipeline needs to audit belongs in the schema, because the
schema is the only place the model is required to answer and the only place the
answer is stored. Prose can ask; only a field can be checked.** Worth agreeing
independently of this enum.

---

## 6 · The pattern behind `DEFAULT_EVIDENCE_TIER`, stated as a pattern

Not a fourth instance. **`compute()` takes 12 required inputs and 5 of them are
supplied by nothing that runs.**

| input | what supplies it today | what the default decides |
|---|---|---|
| `evidence_tier` | `DEFAULT_EVIDENCE_TIER = "D"`, a literal at both call sites | every claim is bare first-hand opinion, 0.12. Vendor marketing should be F, 0.02 — a **6× over-weight** on the announcement text we know is being stored |
| `has_numbers` | `DocumentFacts` default `False` | no claim ever gets the numbers signal. Rule 2 forbids deriving it from the claim, so this one genuinely needs the table |
| `has_conditions` | `DocumentFacts` default `False` | same, and the column is **False on all 7 populated rows and NULL on 57** — deliberately left, because an absent condition is not a stated absence |
| `platform` | `DocumentFacts`, required field | a caller must pass it, so this one fails loudly rather than silently |
| `claim_date` | `DocumentFacts`, required field | same |

**`DocumentFacts` has exactly one constructor in the repository and it is
`tests/test_pipeline_db.py:190`.** There is no production caller: `run_all` takes
`facts` as a parameter and the nightly job that would build it from the
`document` table does not exist.

So the pattern, stated once:

> **The weighting path reads inputs that nothing writes, and the defaults decide.**
> Three of the five fail silently — a literal `"D"` and two `False`s — and a
> silent default in a weighting factor is indistinguishable from a measurement.
> `f_specificity` held **one value, 0.580, across every row `claim_weight` has
> ever contained**, and that was three dead inputs looking like a working factor.

The same shape outside `compute()`:

- **`author_id`** — written by `collect/adapters/blog/write.py` only. 30 of 31
  blog rows, **0 of 6 reddit, 0 of 27 github**. `gate.count` dedups voices off it,
  so the four Reddit claims collapse to `independent_voices = 1` in a thread with
  152 commenters.
- **`document.specificity_score`** — **NULL on all 64 rows**, no writer at all
  (`chain.py:434` names the unimplemented `triage` stage as starving it), while
  the thread selector recomputes the same quantity in Python. Two computations of
  one number, one of which runs.

**Five weighting inputs, one counting input, one column with no writer.** The fix
is not seven fixes. It is a rule: **a weighting or counting input may not have a
silent default.** Either something writes it, or `compute()` refuses to run
without it and the absence is visible — which is rule 6 applied to the machinery
rather than to the data.

That is the finding I would want signed off before `speaking` is added, because
`speaking` would be the eighth input to this path and the argument for making it
required rather than nullable is exactly this pattern.

---

## 7 · What I would need before building it

1. **Rows 0–3 of Yathu's round 2 file** — the only inter-rater evidence
   `vendor-about-own-model` can have from this pool. Being chased separately.
2. **Sign-off on `vendor-about-own-model`** as the name, and on whether a vendor
   writing about a non-model product is out of scope rather than a `speaking`
   value.
3. **Agreement that `speaking` gives `evidence_tier` a source** rather than
   adding a factor — since weighting-only is the ruling and `f_evidence` is the
   factor that already means this.

Nothing is written into `judge/`. `speaking` appears nowhere in
`judge/extract/schema.py`.
