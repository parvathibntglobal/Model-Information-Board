# Measurements

Five reports live here and there was no convention for writing the sixth. This
is it.

Everything below exists because **three figures in one fortnight turned out to
be measuring the instrument rather than the world**, and each was load-bearing
in an argument before anyone checked. `CLAUDE.md` rule 7 is the rule; this is
the method.

---

## Vary the query, not the world

**A number retrieved by a query is a property of the query as much as of the
world.** To find out which, change the query in a way that should not change the
answer, and see whether it does.

That is the whole technique, and it is cheap. Every one of the three failures
had a control available that took two API calls, and nobody ran it until
afterwards.

Four forms it takes, all of them from real incidents:

**Reverse the words inside the quotes.** `"claude sonnet 5"` returns 540 and
`"sonnet claude 5"` returns 545. If word order does not change the answer, the
quotes are not binding a phrase — they are requiring tokens and ranking the
result. Everything downstream that assumed adjacency was wrong.

**Substitute a token that should behave identically.** `"claude sonnet 5"`
returns 123 at `org:openai` and `"claude sonnet 7"` returns 96. A version
numeral that nothing uses should return nothing; both return plenty, because the
numeral is being matched against the issue number. The count was never about the
model.

**Enumerate exhaustively where the set is small enough that ranking cannot bias
it.** `"gemini flash" "dropped a detail"` returns 8. All eight fetched, checked
by plain substring: **seven contain the phrase nowhere.** Any conclusion drawn
from page one of a large result set is a conclusion about relevance ranking.

**Add a token that must fail.** `"gemini flash" zzzqqx` returns 0, which
establishes that tokens are required at all. Without that control, "the words
are required but their order is not" is half a claim.

**And sort the same query two ways.** `"as an AI"` returns 49,848 under every
sort. The first 30 by relevance contain the phrase 30 times; the first 30 by
date contain it once. Same set, different window. This is the one that survives
a careful person eyeballing page one, which is why it needed its own finding
rather than a footnote.

---

## What a figure must carry

Not the principle — the format. A figure without these is not yet evidence:

| | |
|---|---|
| **the count** | `52.7%`, `636`, `18 of 10,255` |
| **the population** | what was counted, in units somebody can picture |
| **how it was gathered** | the query, the scope, the date |
| **what it cannot support** | where the number stops being evidence |

So not `52.7% subject match` but:

```
52.7% subject match
  of 636 candidates retrieved for gemini-2.5-flash using that model's own variants
  GitHub Search, framework sweep, 2026-08-13
  circular as a measure of how often models are named — the corpus was
  selected by the thing being counted. Supports the shape, not the rate.
```

**This applies to counts, not only percentages.** What the three failures shared
was an unstated population, not a form. `227 uncarried surfaces` needs its
denominator exactly as much as `52.7%` does, and `0 mentions` needs to say
whether the detector could have seen one — a zero from an instrument that cannot
observe the thing is not a measurement of zero.

**`None` and `0` are different findings.** `phrase_present = None` for
not-measured, never `0`, because `0` asserts that no candidate carried the
phrase and that is a result. Same for `last_swept_at`: NULL means never swept,
not swept long ago.

---

## The three incidents, as worked examples

They are examples rather than the point. Someone should be able to apply the
method above without reading any of this.

**`"context window"` present in 96% of 248 posts.** Read as evidence that Reddit
binds quoted phrases. It was measuring collocation frequency — a common English
pair comes back because relevance ranking returns it anyway. The variant probe
settled it: 19 enumerated looser forms, 0 hits on three families. There is no
phrase operator; it degrades to OR over tokens, and `"rolled back"` returns
posts containing `back` without `rolled`.

**`"went back to"` present in 100%.** The same mistake, and the 100% made it
look stronger. It is the one substitution term with nowhere to insert a word,
which is the single class where adjacency holds regardless of the index.

**`52.7%` subject match on GitHub.** Quoted as evidence for GitHub's role and
written into `docs/logic-and-workflow.md` §6 as a justification. The corpus had
been retrieved for one model using that model's own variants, so the figure
measures the retrieval. The shape survived — GitHub names models in configs
rather than describing them in prose — and the rate did not.

**One non-example worth keeping.** `82% of hand-written surfaces never observed`
was measured, quotable, and withdrawn before anyone used it: it compared one
platform's prose against a surface list built partly for another platform's
configs. Withdrawing a figure that has not yet done any damage is cheaper than
every entry above.

---

## Report conventions

- **State the negative results.** The union approach to GitHub's discarded
  operators was measured at 3.4x worse unscoped and 124 hours against 134
  scoped. Recording that stopped it being re-derived.
- **Strike rather than delete a retracted claim.** The counts usually stand
  while the interpretation does not, and how the correction arrived is part of
  what the next reader needs.
- **Name the instrument's limits beside its output.** A detector needing a
  vendor word plus a digit cannot see `deepseek r1`, so that zero is a detector
  limit rather than evidence — and in a table the two look identical.
- **Say which platform.** All 5,546 documents in the alias extract are Reddit.
  Id spellings unattested there are plausibly exactly what GitHub config lines
  use, which is an argument for keeping mechanical variants rather than pruning
  to what is attested.
