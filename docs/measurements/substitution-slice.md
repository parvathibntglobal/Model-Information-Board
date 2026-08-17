# Substitution — re-run properly, and the zero is now measured

**146 queries · 1,678 distinct Reddit documents · 9.5 minutes · nothing passes the sieve.**

> The previous figure, `substitution_kept: 0`, was **unknown, not zero**. The
> probe took `entry.terms.topic[0]` — one topic term per entry. The negative
> entry's first term is `switched back`, which carries no `{alias_b}`, so all
> four model pairs rendered the *same* query and the run measured one query
> four times. The positive entry used 1 of its 6 terms.

*Engineer 1 · Reddit, RapidAPI · 2026-08-17 · 204 requests, quota 999,267 → 999,063*

---

## 1 · The control, first

A zero from a harness nobody has shown can produce a one is indistinguishable
from a broken harness. That is exactly what the first probe produced, so this
run states its control before its result.

A synthetic document, put through the same `sieve_any` call the corpus went
through, at the contract locality window:

```
"We replaced claude opus 5 with claude haiku 4.5 for our ticket summariser
 back in March. Six months on there has been no regression that anyone has
 noticed, and it is still running in production."

    passed  = True
    subject = ('claude haiku 4.5',)
    topic   = ('replaced claude opus 5',)
    signal  = ('no regression', 'still running')
    missing = ()
```

**The harness produces a pass.** The zero below is a measurement.

---

## 2 · The result, at its right size

| | |
|---|---|
| rendered entries (2 stances × 17 ordered pairs) | 34 |
| independence predicts, per-entry basis | **1.82** documents |
| measured, full sieve | **0** documents |

**This does not show that substitution is absent.** At a prediction of 1.82,
observing zero is roughly a **1-in-6 outcome under independence alone**. What
it shows is that the corpus is too thin to distinguish "nobody reports
migrations" from "we retrieved 1,678 documents and got unlucky". Any stronger
reading of the zero is unsupported.

> **Basis note.** The prediction above is per-entry — subject, topic and signal
> from the *same* rendered entry, combined as `1 − ∏ₑ(1 − Pₛ·P_t|e·P_g|e)`. The
> any-entry marginals in §4 are a different basis and multiplying them does not
> reproduce it. Same caveat as the other two slices.

---

## 3 · The funnel — where the constraint actually is

A document counts at a stage if **any** of the 34 rendered entries reaches it.

| stage | documents | share |
|---|---|---|
| retrieved | 1,678 | |
| **+ subject** — a pair member named | 257 | 15.3% |
| **+ topic** — a migration phrase | 69 | 4.1% |
| **+ signal** — in the author's own prose | **0** | **0.0%** |
| passes the sieve | 0 | 0.0% |

**Signal binds. Subject does not. Locality never got the chance to reject
anything.**

Sixty-nine documents name a pair member *and* carry a migration phrase, and
not one of them carries a substitution signal term in the author's own
sentences. The locality window — the thing the last measurement was about —
was never reached, so this run says nothing about whether 1200 is right.

The signal vocabulary is not dead in general. Twelve of the fifteen terms
across the two entries fired somewhere in the corpus:

| term | documents | | term | documents |
|---|---|---|---|---|
| `months later` | 24 | | `complaint from` | 3 |
| `still running` | 8 | | `started failing` | 2 |
| `had to revert` | 6 | | `no regression` | 2 |
| `wasn't worth` | 6 | | `cheaper per` · `regression after` · `saved us` · `no regressions` | 1 each |
| `held up` | 6 | | | |

Three matched nothing at all: `kept it in production`, `nobody noticed`,
`quality dropped`. The other twelve simply never land on a document that also
names both models.

---

## 4 · Retrieval and marginals — the same shape as the other slices

| kind | queries | non-zero | posts | pages stored |
|---|---|---|---|---|
| `alias_b`-rendered | 98 | 15 | 57 | 92 |
| alias-scoped | 44 | 43 | 2,031 | 94 |
| bare | 4 | 4 | 300 | 12 |
| **total** | **146** | **62** | **2,388** | **198** |

84 queries returned zero posts. `data not found` is zero results, not an
error. No HTTP errors, no rate limiting.

Highest-yield directional phrases: `"switched from gemini 2.5 pro"` 19,
`"instead of opus 5"` 9, `"replaced gemini 2.5 flash"` 6,
`"replaced gemini 2.5 pro"` 6.

**Any-entry marginals** (not the basis §2's prediction uses):

| | | |
|---|---|---|
| P(subject — any registry alias) | 0.396 | 664 / 1,678 |
| P(≥2 distinct registry models) | 0.133 | 223 — the pair precondition |
| P(any substitution topic) | 0.379 | 636 |
| P(any substitution signal, prose) | **0.033** | 56 |

Topic terms are carried almost entirely by the four model-free negative
phrases — `went back to` 305, `rolled back` 161, `switched back` 117,
`reverted to` 52 — against `instead of opus 5` 6 and
`replaced gemini 2.5 pro` 3 for the directional ones. 3 of 34 rendered entries
matched no topic term; 0 of 34 matched no signal term.

### How the pairs were chosen

Not the first N from the registry. Ranked on `slot`, **not price**: `price_in`
is NULL for 4 of 11 seed models and rule 6 says a NULL price is not the
cheapest tier, so price cannot rank them.

- **11 downgrades** — frontier|mid → budget|open-weight|just-launched, the
  decision this board exists to inform. Same-vendor first (opus→sonnet→haiku,
  gemini pro→flash, mistral large 2→3, r1→v3, r1→v4-flash), plus three
  cross-vendor moves to the most-discussed budget models.
- **6 peers** — same slot, both directions. opus↔gemini pro, haiku↔gemini
  flash, gemini flash↔gpt-4.1-mini.

All 11 seed models appear in at least one pair. Alias surfaces: variants at
`version`/`snapshot` specificity containing a space, most-qualified first,
cap 2 — family surfaces (`opus`, `haiku`) name a line rather than a tier, and
id spellings (`claude-opus-5`) are config lines rather than sentences.

**Retrieval is per `alias_b`, not per pair.** `replaced {alias_b}` renders from
the origin alone, so 17 pairs cost 14 origin surfaces. The pair is a sieve-time
object. That is what keeps this at 146 queries rather than several hundred.

---

## 5 · The registry is a generation behind the conversation

A substitution query names **two** models, so it is doubly exposed to this.

Model-shaped surfaces — a proxy (vendor word plus version token), not a
reading; whether a surface names a real model is the registry's judgement:

| | |
|---|---|
| total mentions | 3,619 |
| the registry carries | **745 — 20.6%** |
| the registry does not | **2,874 — 79.4%** |
| distinct surfaces carried | 9 |
| distinct surfaces not carried | **227** |
| documents naming a model, none of which is carried | 425 — 25.3% |

On the 636 documents carrying a migration phrase:

| | documents | |
|---|---|---|
| naming ≥2 distinct model surfaces | 133 | 20.9% — reachable by *some* registry |
| naming ≥2 the registry carries | **6** | **0.9%** — reachable by *this* one |

**127 documents state a migration, name both models, and the registry cannot
resolve the pair.** That is a poller finding, not a substitution finding, and
the two must not be reported as one.

| not carried | | carried — all nine |  |
|---|---|---|---|
| `sonnet 4.5` | 393 | `opus 5` | 348 |
| `opus 4.8` | 162 | `gemini 2.5 pro` | 146 |
| `gpt-5` | 161 | `sonnet 5` | 111 |
| `opus 4.5` | 132 | `gemini-2.5-pro` | 35 |
| `opus 4.6` | 120 | `gemini-2.5-flash` | 34 |
| `gemini 3 pro` | 83 | `haiku 4.5` | 31 |
| `sonnet 4` | 76 | `gemini 2.5 flash` | 31 |
| `opus 4.7` | 58 | `gpt-4.1-mini` | 8 |
| `sonnet 4.6` | 57 | `gpt-4.1 mini` | 1 |
| `gemini 3` 54 · `qwen3` 52 · `gpt5` 48 · `opus 4.1` 48 · `gpt-5.5` 43 · `glm-4.6` 41 · `gemini 3 flash` 38 | | **total** | **745** |

Three uncarried surfaces alone — `sonnet 4.5`, `opus 4.8`, `gpt-5` — total 716,
which is within 30 of everything the registry carries put together.

**What would revise this measurement:** the poller replacing
`contract/seed_models.yaml`. Until then the substitution vocabulary cannot be
tested, because the documents that would test it name models the registry has
never heard of.

---

## 6 · What went wrong in this run, and why the result survives it

**44 of the 146 queries did not do the job they were designed for.** The four
model-free negative topic terms were issued alias-scoped — `"switched back"
claude opus 5` — on the assumption that a bare term after a quoted phrase
narrows the result set to that model. It does not.

| | |
|---|---|
| posts containing the appended alias | **7%** of 2,031 |
| overlap with the bare phrase | Jaccard **0.00–0.01**, near-disjoint |
| phrase containment | **degrades**, 43% alone → 32% appended |

It reweights rather than restricts. The scoped queries retrieved a different
1,700-odd documents rather than a narrower slice of the same ones.

**The measurement survives because the sieve arbitrated.** Retrieval only ever
decides what the sieve is shown; every stage of §3's funnel was computed by
`matches` and `sieve_any` over stored text, not by trusting what a query
claimed to have returned. The corpus is wider and less targeted than intended,
which costs recall of the specific pairs and costs nothing in correctness.

Saying so is the difference between a result and a lucky one. It also means
the 15.3% subject rate in §3 is a property of a loosely-retrieved corpus and
should not be compared directly to the sweep's 82.4%.

A **sidecar** was written this time — `pages.jsonl`, 198 rows of
`(ref, query, page, entry, alias_b)` beside the store. Every number in this
document was re-derived from it rather than from the run's own memory, which
is the first time that has been possible. `reddit_slice_store` has no such
sidecar, and recovering which page came from which query there needed write
order plus phrase containment.

---

## 7 · What this does not say

- It does not say substitution is undiscussed. See §2 — the zero is
  indistinguishable from bad luck at this corpus size.
- It does not say the signal vocabulary is wrong. Twelve of fifteen terms fire;
  they never co-occur with a resolvable pair, and §5 explains why.
- It does not say anything about the locality window. Nothing reached the stage
  where locality is evaluated.
- It does not measure blogs, which `contract/queries.yaml` names as
  substitution's likeliest home. This is Reddit only.

Thread assembly stays refused. Nothing here called `assemble_thread`.
