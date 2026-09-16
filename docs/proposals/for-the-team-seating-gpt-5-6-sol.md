# Seating `openai/gpt-5.6-sol` — and the six-model family behind it

**Status: proposed. Nothing seated, nothing written to staging.**
A fetch was attempted, cost nothing, and produced nothing. This is why, what the
corpus actually holds, and the one judgement call left for a reviewer.

## What happened

A full fetch of `mv_0510680735d3c79a` (OpenAI: GPT-5.6 Sol) at an extraction cap
of 50, `ENVIRONMENT=development`, terminated in 7 seconds:

```
E1 Registry  ok       OpenAI: GPT-5.6 Sol — 0 search-eligible name variant(s)
E2 Harvest   skipped  no search variants for this model — nothing to search for
end          ok       nothing to harvest
```

`scripts/fetch_model.py:2233` returns before E5 exists when `_variants_for`
comes back empty. So: 0 threads committed, 0 claims, 0 board entries, 0 cells,
0 stopped at the ceiling, and **no three-way selection split, because selection
never ran**. The board row is unchanged, diffed against a snapshot taken before
the run rather than recalled — 2 cells, 5 board entries, both sides identical.

`_variants_for` reads `model_alias` and falls back to `seed_models.yaml` only
for seeds. **All six members of the 5.6 family carry zero alias rows** —
`luna`, `luna-pro`, `sol`, `sol-pro`, `terra`, `terra-pro` — and none is a seed.
The family postdates `alias-surfaces-tracked-set.yaml`, whose 12 OpenAI entries
stop at `gpt-5.5`.

## This is not a thin model

**119 documents name GPT-5.6 Sol specifically**, carrying 189 mentions.
Population: 8,848 documents scanned, being those with a `text_ref` whose payload
is readable on this machine, out of 12,779 with a `text_ref` — 3,931 payloads
are not on this machine. Matching is normalised substring, the same transform
the resolver uses, with `-pro` excluded by lookahead (see below). It is a
retrieval count over the stored corpus; it is not a naming rate, and it is not
attribution.

By `document.source`, following the `deepseek-v4-pro` entry's convention:

```
gpt-5.6-sol (not -pro)   189 mentions, 119 documents   reddit 172, blog 9, github 5, hackernews 2, devto 1
gpt-5.6-sol-pro           39 mentions,  23 documents   reddit 38, blog 1
bare "5.6 sol", no gpt    29 mentions,  21 documents   reddit 26, github 2, blog 1
```

The literal spellings people wrote, which are what become search queries
(175 mentions, 113 documents — lower than the normalised 189/119 because
normalisation folds forms the word-boundary regex misses; both figures are
given rather than the flattering one):

```
  81  gpt 5.6 sol          11  gpt5.6sol
  59  gpt-5.6 sol           6  gpt-56-sol
  14  gpt-5.6-sol           4  other spacings
```

That clears the header's `mention_floor: 20` by a wide margin. For scale against
the two most recent seats: `gpt-5.5` was seated on 228 mentions,
`deepseek v4 pro` on 33 documents.

Separately, a scan of unread threads only — the pool a fetch would draw from —
found **172 of 3,908 readable unread `thread_context` rows** naming the model
(4,276 unread total; 368 not readable here). So the evidence is not only stored,
it is unread and reachable.

## The collision I flagged does not exist — measured, not reasoned

**This section previously said the opposite and was wrong.** It claimed
resolution is normalised-substring, so seating Sol alone would resolve every
Sol-Pro mention to Sol. That was not checked before it was written. It has now
been checked against the live population and the premise is false.

`RegistrySurfaceResolver.__call__` is **exact normalised match FIRST**, and only
falls back to containment when the exact lookup misses. `from_connection` builds
its population from `model_version` — canonical_id and display_name — and **not
from `model_alias`**. So both models are already distinct keys, each with
exactly one owner, today, with zero alias rows seated:

```
gpt56sol      -> ('openai/gpt-5.6-sol',)
gpt56solpro   -> ('openai/gpt-5.6-sol-pro',)
```

Resolved against the live registry, all correct:

```
'GPT-5.6 Sol'      -> openai/gpt-5.6-sol       'GPT-5.6 Sol Pro'  -> openai/gpt-5.6-sol-pro
'gpt-5.6-sol'      -> openai/gpt-5.6-sol       'gpt 5.6 sol pro'  -> openai/gpt-5.6-sol-pro
'gpt 5.6'          -> None (refused)           'GPT-5.6 Terra'    -> openai/gpt-5.6-terra
```

`ambiguous: {}`. Nothing collides.

**So attribution never depended on alias seating at all**, which is also why
this model already holds 5 board entries and 2 cells with no aliases. Seating
buys two other things and only those: search queries for the harvest arms, and
the E5 ordering weight in `threads_naming_the_model`. That second one *is*
substring-matched — which is where my wrong premise came from, by reading the
selection path and describing the attribution path — but it is an ordering
weight over a pool, not a gate and not an attribution (rule 8).

**Consequence for the three options:** option 1 is not merely alive, it is
unnecessary. There is no correctness hazard to resolve, so seating Sol alone,
Sol with Sol-Pro, or all six is now a question of harvest coverage and nothing
else. A third of the decision is gone.

### One real finding, not a blocker

```
'GPT-5.6 Sol Ultra' -> openai/gpt-5.6-sol
```

The digit-guard that refuses `gpt 5.6` (next char `6`) does not fire here: the
char after `gpt56sol` is `u`. The comment at `surface_resolver.py:240` uses
`GPT-5.6 Sol Ultra` as its worked example of a refusal, but that reasoning was
written when the longest match was `gpt5`; now that `gpt56sol` is in the
population the match is longer and the guard misses. **No `gpt-5.6-sol-ultra`
exists in the registry**, so this is hypothetical today and costs nothing — but
it is a live edge the guard was believed to cover, and seating more of the
family does not change it either way. Worth its own look, not worth blocking on.

### The blocking slot is left in place, and its reason is withdrawn

I have NOT removed `sol_pro_disambiguation` from the entry's `incomplete` list,
because seating is E1/E2's call and this document only reports. But the question
it was blocking on is answered: there is nothing to disambiguate. Deleting that
token is now a one-line change with no open decision behind it.

## What is NOT proposed here

The bare `5.6 sol` form (21 documents) is **left out of the variants**. It is
attested, and it is one token away from every other 5.6 model; including it
buys 21 documents and risks the ambiguity the family surfaces already have.
Recorded so the omission is arguable rather than invisible.

## Payload gap — moved out

This proposal previously carried a paragraph about unreadable payloads. It did
not belong in a seating proposal and is now **issue #321**, alongside the prior
art it should have cited (#303, same machine, one day earlier; #316, a different
cause).

It matters here only as a caveat on the counts above: they are drawn from the
8,848 documents readable on this machine of 12,779, so **every figure in this
document is a floor.**

## The entry

Appended to `docs/proposals/alias-surfaces-tracked-set.yaml`, hand-added the way
`deepseek/deepseek-v4-pro` was on 2026-09-14, and generated rather than
reviewed — the counts are measured, the surface choice is not yet anyone's
judgement.

To seat after review: settle the item above, delete `sol_pro_disambiguation`
from the `incomplete` list, then run the seat and announce the staging write.
