# Two inheritance questions, and the extractor is already answering one of them

**Thread-subject inheritance is not a proposal. It is already happening,
undeclared, in 3 of the 4 claims we have stored.** The extractor is handed the
whole flattened thread and the prompt says nothing about the root, so it has been
attributing comments to a subject named elsewhere and recording
`specificity=version` with nothing saying the subject was inherited.

And the family-specificity question has a different answer than "invisible":
`family` is a permitted value, the gate does not refuse it, and ~12 family claims
would publish a cell.

*Engineer 1 · 2026-08-21 · population `b5744297e9210497` · run in
`thread-subject-inheritance.txt`*

Both questions land mostly in `judge/`. This is measurement and a proposal;
nothing in `judge/` was edited. `docs/proposals/for-engineer-2-inherited-subjects-and-family-claims.md`
is the ask.

---

## RULED TWICE, NOT DEFERRED — 2026-08-21, and again 2026-08-21

**This was ruled against, reopened on new evidence, and ruled against again on
different evidence. It is CLOSED, not pending.** Recorded this way because the
two rulings do not stack — the second measurement made the rule look BETTER on
the axis it was reopened for, and made the case against it stronger on three
axes nobody had measured. A reader who finds only the first ruling will reopen
it for exactly the reason it was already reopened once.

```
ruling 1   the rule's second condition fires on 60% of candidates, and what
           survives is announcement threads.          A QUALITY objection.
reopened   the recoverable population is far larger than the 21 measured —
           true, and measured at 104 with 86 voices, a 6.1x n_eff multiplier.
ruling 2   it fails the FIRST condition (population 0 on the one thread we
           hold), 72% of what it recovers carries no specificity signal at
           all, and 6.1x still lands at 1.247 against a threshold of 3.0.
           A CORRECTNESS objection, a PURPOSE objection, and an ARITHMETIC one.
```

**The pattern worth carrying: a rule getting more attractive under measurement
is not evidence for it.** The reopening was correct and the answer went the
other way, which is what a measurement is for.

## RULING 1 — 2026-08-21

> ⚠ **A SECOND, INDEPENDENT REASON, MEASURED 2026-08-21 AFTER THE RULING.**
> The ruling below rests on condition 2 — 32 of 53 candidates name a second
> model — which is a QUALITY objection: the rule recovers vendor prose. That
> invites the reply *"then filter for non-vendor threads"*.
>
> **Condition 1 fails too, and that is a CORRECTNESS objection.** On the one
> thread we hold in full (`t3_1u1b22l`, 195 comments), of the 177 dropped for
> naming no model, **177 of 177 satisfy condition 2** — and the population the
> rule would reach is still **0**, because the root does not resolve to exactly
> one model:
>
> - the root announces `Claude Fable 5` (9 mentions) and `Claude Mythos 5` (6).
>   **Neither is in the registry**, so neither resolves;
> - the only model that resolves is `Claude Opus 4.8`, at **one** offset, in the
>   sentence saying which requests get handed off to it;
> - and that single mention resolves to **two** model_versions —
>   `anthropic/claude-opus-4.8` and `anthropic/claude-opus-4` — because
>   `opus 4` is a boundary-valid substring of `opus 4.8`.
>
> So inheritance here would attribute **139 authors' opinions about Fable 5 to
> Opus 4.8**: the wrong model, at scale, from a sentence about refusals.
> `docs/measurements/the-rollup-refused-and-why.md` §4.
>
> **A THIRD REASON, AND A FOURTH, measured 2026-08-21.** Reopened on the
> observation that the recoverable population is far larger than 21, which
> is true — and it does not survive being measured either:
>
> - **104 of 177** are dropped on the entity gate ALONE and so are
>   genuinely recoverable; the other 73 also fail `too-short-no-artifact`
>   and inheritance does not save them. 86 distinct authors.
> - **72% of those 104 carry none of** `has_numbers`, `has_code`,
>   `has_error_strings`, `has_conditions`. Median body 90 characters, 0
>   error strings across all 177. It recovers reaction, not observation -
>   thinner than the vendor prose this ruling was made about.
> - **and it does not reach the gate**: n_eff 0.206 -> 1.247, a 6.1x
>   multiplication that is still short of `N_EFF_MINIMUM = 3.0` by 2.4x.
>
> So the rule fails at its first condition, at its second, at what it is
> for, and at the arithmetic. `docs/measurements/the-overlap-is-models-not-capabilities.md` §3.

**Decided by both engineers on the measurement below. Recorded because the next
person will have the same idea, and it is a good idea that does not survive its
own second condition.**

The rule was: a comment that resolves to nothing inherits its thread root's
subject, if the root resolves to exactly one model and the comment names no other
model.

**The second condition is what settles it.** Anooj's count: of 53 candidates,
**32 name a second model** — so the condition fires on 60% of them — and the
**21 that survive are all in two announcement threads**. That is the same
population that produced the four vendor-copy claims already on staging. The rule
would recover, almost exclusively, more copies of the thing we already have too
much of: vendor announcement prose and the reaction to it.

Two counts, two rules, and they are reported separately rather than merged. Mine
was over the one raw comment payload we hold, counting a comment as eligible when
`resolve()` over its body returns nothing at all: **168 of 195 (86.2%)** eligible,
**96 reaching extraction**. Anooj's 53/32/21 uses a rule I could not reconstruct —
53 is not a denominator I reach from the threads we hold. **The two agree on the
conclusion and disagree on the population**, and per rule 7 that is worth leaving
visible rather than picking the number that reads better. If the rule behind 53
matters later, it needs stating.

Either way the direction is the same and the conclusion does not depend on which
is right:

- the conditions are **necessary and nowhere near sufficient** — at 86.2% mine
  selects almost the whole thread;
- what survives is **announcement threads**, where the subject is the vendor's and
  the comments are about price and strategy;
- what reaches a paid call includes *"They probably used the Odyssey"* and *"Too
  bad they didn't use Chimaera"* — jokes about invented models, becoming claims
  about Fable 5;
- **80 distinct authors** in one thread would become 80 independent voices from a
  single act of naming, against `WIDELY_PRAISED_VOICES = 5`.

**And it is already happening anyway**, undeclared, in 3 of the 4 stored claims —
see Part 2. So the work was never "enable inheritance". It is "declare it and
bound the thread", and that survives this ruling unchanged.

**What stays true and worth keeping:** the two conditions are correct as
*necessary* conditions, and `thread_context.offset_map` does carry what a
pipeline-level join would need. Nothing here says the idea is unsound. It says the
population is announcement threads and the filter is not a filter.

---

## Part 1 — Family-specificity claims

### What recording them would take

Three things, and the first is not what I expected.

**1. The mapping does not exist in the database.** `model_alias` holds 105 rows
over 41 model versions: **82 `snapshot`, 23 `version`, 0 `family`.** Bare `opus`,
`sonnet` and `haiku` are absent entirely, and the `family` column is NULL on
every row.

That is not a filter. `alias_rows()` over the current seed file would produce 48
rows — 22 snapshot, 13 version, **13 family** — including exactly what the ruling
in `entity.py` cites:

```
opus   -> mv_568e0eb3a95b5113  (anthropic/claude-opus-5)    search_eligible=True
sonnet -> mv_2cd37409a483435a  (anthropic/claude-sonnet-5)  search_eligible=True
haiku  -> mv_dd2f481c145743d5  (anthropic/claude-haiku-4-5) search_eligible=True
```

`load.py` inserts them with no specificity filter. They are absent because
**every `model_version` row is `provenance='polled'`** — `registry load-seed` has
never been run against this database. Which is `assert_no_fixtures()` passing,
correctly, and it means the family mapping currently lives only in the YAML.

So the poller does not produce family aliases and the seed file may not be
loaded outside development. **A family claim has no owner to resolve to today,
by two independent mechanisms.** That is the first thing recording them would
have to fix, and it is a registry question rather than a claims question.

**2. `build_population` would need to carry them as a labelled part.** It reads
`model_version` and derives; family surfaces are excluded by `_admissible` and
would have to come back as a *third* contribution alongside `MECHANICAL`,
`VENDOR_DROP` and `DECLARED` — separately labelled, so a verdict says which half
matched. Not a predicate change: the population object grows a part.

**3. A claim would need to say the subject was reached at family specificity.**
This one already exists: `Specificity = Literal["snapshot", "version", "family"]`
in `judge/extract/schema.py`, and `claim.specificity` is a stored column. Nothing
to add.

### What it would put on a model page

Not the quote. This is the part worth being precise about, because the question
assumed otherwise.

`judge/curate/phrases.py` builds `"One person mentioned {what} — not yet
corroborated"` with `quote_ids` attached for any sub-threshold cell. But
`judge/pages/model.py:headline` joins `consensus_phrase` **only for slices where
`s.publishes`**, and for an insufficient capability it returns a count instead:

```
"1 person has reported on this, which is not yet enough to publish a finding."
```

So the page states that somebody looked and does not say what they said. Against
the alternative — `"Nobody has reported on this."`, or for a silent-failure
capability the longer form warning that absence of complaints is not reassurance
— it is **strictly more informative and renders distinctly**. That is rule 4
satisfied, not strained.

`oqocfjv` would therefore not appear as *"one person said Fable uses more
tokens"*. It would appear as *"1 person has reported on this"* under
`ops.output_verbosity`, with the quote reachable through `quote_ids` and not
rendered in the headline. A reader learns that the capability has been touched
and cannot yet see by whom or how — which is a smaller claim than the worry, and
a real improvement on silence.

### Is the gate's refusal to count them enough on its own? No — because it is not a refusal

This is the correction that changes the decision. `gate.py:count` does not read
specificity at all; a family claim is one `independent_voices` like any other.
Specificity enters only through `n_eff`, via `FUZZINESS_WEIGHT["family"] = 0.3`.

**And a second correction, to my own sentence above.** "Specificity enters only
through `n_eff`" is true of `claim.specificity` and hides the sharper problem:
`compute()` takes `specificity` *and* `version_named`, and prices overlapping
facts twice at two granularities. `f_fuzziness` reads `claim.specificity`;
`f_specificity` reads `version_named`, which is `document.names_version`. Section
3 below, and it is the finding to act on.

The arithmetic:

| | |
|---|---|
| `w_final` | `f_evidence × f_platform × f_specificity × f_relevance × f_recency × f_launch` |
| best single family claim, Reddit | `1.0 × 0.85 × 0.3 × 1 × 1 × 1` = **0.255** |
| best single family claim, GitHub | `1.0 × 0.95 × 0.3` = **0.285** |
| `N_EFF_MINIMUM` | **3.0** |
| family claims needed to publish | **12 on Reddit, 11 on GitHub** |

Plus `PLATFORM_MINIMUM = 2`, so they would have to span two platforms.

**So 0.3 does not forbid corroboration. It raises the bar from roughly four
claims to roughly twelve.** Twelve people writing "Opus is slow" with no version
would publish a cell against **Claude Opus 5** — because that is what the seed
file maps bare `opus` to, and it is the same misattribution the `entity.py`
ruling refuses at the resolution step. The weight makes it need three times as
many people; it does not make it right.

`gate.py`'s own docstring says a `voices >= 3` condition would be "dead text"
because `n_eff >= 3.0` already implies four or more claims. That reasoning holds
for snapshot claims and inverts for family ones: at 0.3, twelve voices are needed
for the same `n_eff`, so the voice count and the weighted count stop tracking
each other in exactly the regime where the phrase vocabulary uses voice counts
(`WIDELY_PRAISED_VOICES = 5`). A cell could read **"Widely praised"** off twelve
family claims whose subject nobody stated.

### What I would decide

**Record them, mark them, and cap what they can reach.** Specifically:

1. Family claims may be **stored and displayed** at the insufficient state. The
   page text is already right and already distinct, and the alternative is
   deleting the only first-hand capability observation we have.
2. They may **not lift a cell to published**, and the 0.3 weight does not achieve
   that. It needs a stated rule — a family claim cannot be the marginal claim, or
   family claims do not count toward the voice thresholds the phrase vocabulary
   reads.
3. That rule belongs in `contract/`, not in code, and it is E2's to write.

What I would **not** do is treat 0.3 as the decision. It is a discount that was
never chosen for this purpose — `contract/harvest.yaml` says outright that the
specificity weights are "PROVISIONAL · INTRA-CHANNEL ONLY · NEVER CALIBRATED".
Leaning a publication rule on an uncalibrated weight is how a threshold becomes
a policy nobody agreed to.

---

## Part 2 — Thread-subject inheritance

### Are both conditions checkable where resolution runs? One is; the other is not

`judge/pipeline.py:196`:

```python
model_version_id = model_version_of.get(claim.model_ref.resolved_version_id or "")
if model_version_id is None and resolve_surface is not None:
    model_version_id = resolve_surface(claim.model_ref.surface)
```

The Protocol is `__call__(self, surface: str) -> str | None`. **The resolver sees
one string.**

| condition | checkable? |
|---|---|
| the root resolves to exactly one model | **Yes, in `Pipeline.run`** — `thread` is in scope, and `thread.flattened_text` contains the root. Not inside the resolver. |
| the comment names no other model | **No.** At that point there is no comment — there is a claim with offsets into `flattened_text`. |

The second is *recoverable*: `thread_context.offset_map` maps flattened offsets
back to member documents, so the comment a quote came from can be found. But that
makes inheritance a pipeline-level join over `(thread, offset_map, claim)`, not a
resolver argument — a restructure of the same shape as the family-word one, and
for the same reason: the decision needs context the function was designed not to
have.

### But the premise is wrong, and that is the finding

**`wrap_untrusted(flattened_text)` gives the extractor the whole flattened
thread.** Root and children, one string. `judge/extract/prompt.py` never mentions
the root, the thread, or a subject — it asks for *"a MODEL, named specifically
enough to identify"* and leaves the rest open.

So the extractor has been free to inherit all along, and it does. All four stored
claims, checked against the surface population:

| comment | specificity | surfaces inside the quote |
|---|---|---|
| 1 | `version` | **none** — *"exceptional performance in software engineering"* |
| 1 | `version` | `claude opus 4.8`, … |
| 1 | `version` | **none** — *"We'll keep refining the safeguards to reduce false positives."* |
| 5 | `version` | **none** — *"gives 10%+ better results on SWE-Bench"* |

**Three of four quotes name no model.** The subject came from elsewhere in the
flattened thread, every row records `specificity=version`, and nothing anywhere
says the subject was inherited rather than stated.

That reframes the whole question. This is not "should we build inheritance". It
is **"inheritance is on, undeclared, and we cannot tell which claims used it"** —
which is rule 6's shape at the claim level: a value that was absent from the
quote became definite in the row, with no marker.

### What widening it would recover, measured

**The assembled population is 2 threads.** Of 60 `thread_context` rows, 58 have
`child_count = 0` — blogs and GitHub, single documents. Two have five children
each.

I could not read those 10 comments. The raw store reported **four refs missing
with no tombstone** — *"NFR-4 rebuild-from-raw is no longer guaranteed"* — and
eight of the 70 member ids are absent from `document` altogether. So the
assembled arm returns **void, not zero**, and I am not reporting 0 eligible from
it. That store gap is a separate defect and it wants its own look.

The observed arm, over the one raw comment payload we hold:

| | |
|---|---:|
| root: *"Introducing Claude Fable 5"* → | **1 model** (`anthropic/claude-fable-5`) |
| comments with a body | 195 |
| resolve to a model themselves (unchanged) | 27 |
| **would inherit under the two conditions** | **168 (86.2%)** |
| dropped by a non-entity gate (`too-short-no-artifact`) | 72 |
| **reaching a paid extraction call** | **96 (49.2% of the thread)** |

**86.2% eligibility is not reassurance, it is the result.** The two conditions
are necessary and nowhere near sufficient — *"names no other model"* is satisfied
by every comment about pricing, the IPO, or nothing at all. What would reach
extraction:

```
oqodw1j  score=145  'Using it in any capacity will cost like $5000/mo'
oqppqg4  score=6    "OR they want to look extra profitable for the IPO..."
oqokyvp  score=18   'They probably used the Odyssey (next next version)...'
oqom4s8  score=34   "Too bad they didn't use Chimaera. That's the most powerful model..."
oqp1g34  score=8    'i know math, i saw their comment about capacity...'
```

The last two are jokes about invented models. Under the rule they become claims
about Claude Fable 5.

### What it costs at the gate, and this is the number that decides it

| | |
|---|---:|
| distinct authors in the thread | 152 over 195 comments |
| distinct authors among the eligible | 134 over 168 |
| **distinct authors among triage survivors** | **80 over 96** |
| `WIDELY_PRAISED_VOICES` | **5** |
| `GENERALLY_PRAISED_VOICES` | 3 |

`gate.count` takes one representative per `voice_id`, so the same person
commenting twice is already absorbed — 26 of 152 authors comment more than once
and that is handled. **What is not absorbed is 80 different people inheriting one
subject from one root.** That is 80 independent voices produced by a single act of
naming, by the vendor, in a launch announcement.

`max_author_share` does not help: the authors *are* different people. The cap was
built for one loud account and this is not one account.

So the answer to "if `n_eff` counts them identically, a thread's structure
inflates its voice count" is yes, and by a factor of 80 in the one thread we can
measure. A launch thread is the worst case and also the most common case — it is
where people gather to say "it's much faster".

### Is the schema ready to say "inherited"? Nearly, and not where you'd think

`Specificity = Literal["snapshot", "version", "family"]` has room for a fourth
value, but **inheritance is orthogonal to specificity**, not another level of it:
an inherited subject can be perfectly snapshot-specific (*"Introducing Claude
Fable 5"* → `anthropic/claude-fable-5`) while the claim's own text names nothing.
Folding it into `specificity` would collide two facts into one column, which is
the `report.ambiguous` mistake from last week at a different altitude.

A separate boolean — `subject_inherited`, with the `thread_context_id` and the
root document already on the claim row — says the orthogonal thing orthogonally.

### What I would decide

**Do not build the code rule. Declare what is already happening, then bound the
thread.**

1. **Say it in the prompt.** The extractor may attribute a comment to a subject
   named in the thread root; it must mark such a claim. Today it does the first
   half and cannot do the second.
2. **`subject_inherited: bool` on the claim**, not a fourth specificity.
3. **Bound the thread at the gate**, the way `max_author_share` bounds an author:
   a `max_thread_share` counter, so one thread cannot supply a cell's voices. This
   is the fix that matters, and it is needed **whether or not** inheritance is
   ever formalised — because the extractor is already producing inherited claims
   and 80 of them could come from one announcement.
4. **Do not widen thread assembly** until 3 exists. The selector currently keeps
   2.7% of observed children, and that accident is the only thing bounding this.

The two conditions in the brief are worth keeping as *necessary* conditions. They
are just not the filter — at 86.2% they select almost the whole thread, and the
work of distinguishing "it's much faster" from "Too bad they didn't use Chimaera"
is the extractor's, under a prompt that currently says nothing about it.

---

## Corrections to earlier rounds

- **`propose.py`'s "never counts as independent corroboration" was already
  corrected** for overstating the code. This memo adds the arithmetic: ~12 family
  claims reach `N_EFF_MINIMUM`, so the 0.3 weight is a 3× higher bar and not a
  refusal.
- **"today it resolves to nothing because resolution reads each comment alone"**
  is half right. Resolution does read one surface alone. But *extraction* reads
  the whole flattened thread, and that is where inheritance is already entering.
- The assembled-threads arm of this measurement is **void, not zero** — four raw
  refs missing with no tombstone. Reported rather than counted.
