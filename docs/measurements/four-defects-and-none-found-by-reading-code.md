# Four defects in one day, and not one was found by reading code

**A statement about where to look, not about today.** Every one was found by a
number disagreeing with another number that was already on the screen, or by a
test changing its answer. Reviewing the code would have found none of them,
because in each case the code was correct in isolation and wrong in company.

*Engineer 1 · 2026-08-31.*

---

## The four

```
  1  a count exceeding the distinct things it counted
     new 1,881  beside  unique 1,410  beside  stored 1,145
     `new_to_corpus` incremented per FETCH, so a document retrieved by two
     surfaces counted twice. Two figures in one printed row cannot both be
     document counts if one is larger than the other's universe.

  2  a refusal-test flipping to DID NOT RAISE
     test_a_heterogeneous_tuple_refuses_rather_than_guessing
     A clean merge put two implementations of one rewrite in one call chain -
     `widen_tuples(inline(schema))` - and the permissive one ran first, so the
     strict one had nothing left to inspect.

  3  a figure surviving its own denominator moving
     $4.70 held while the population went 1,519 -> 1,549 -> 2,835 unread.
     Three restatements, and the third moved it to $8.29. A number that does
     not move when its denominator does is either robust or not measuring the
     denominator, and only re-deriving tells you which.

  4  a number contradicting another in the same row
     _before_rollup.json: e5.1, 197 claims. The table: e5.1, 211 claims.
     Three staleness refusals passed it, because all three were built to catch
     a baseline from a DIFFERENT pipeline_version and this one was from the
     same.
```

## What they have in common, and it is not carelessness

**Each is correct locally.** `new_to_corpus += 1` is a correct line. `inline`'s
`prefixItems` rewrite is correct and its comment is accurate. The $4.70 fit was
computed properly from 195 measurements. The three baseline refusals each catch
a real case.

**Each is wrong only in relation to something else** - another counter in the
same report, another function in the same chain, an earlier run of the same
figure, a table the file claims to describe. That relation is invisible from
inside the file, which is why reading the file finds nothing.

## Where to look, then

Not "read more carefully". The four say something narrower:

**Put figures that must agree in the same output.** Defect 1 was caught because
`new`, `unique` and `stored` printed on one line. Had they been in three
sections nobody would have compared them. The report format was the detector.

**Assert refusals, not just results.** Defect 2's test does nothing on the happy
path - it exists solely to prove a `raise` still happens. That is the test most
likely to be deleted as redundant and the only one that caught a merge git
called clean. Three merges have now hidden a defect this way: the
`DocumentFacts` fields, the Protocol body, and `prefixItems`.

**Re-derive rather than carry.** Defect 3 was found by re-running the same
projection against a moved population, which is cheap because every script
prints its own denominator. Carrying the number forward would have been free
and wrong.

**A guard's population is narrower than the thing it guards.** Defect 4's three
refusals were complete for the case they were written for. So was
`tests/test_script_output_is_encodable.py`, which walked `print()` arguments and
missed a message that was RETURNED and printed by its caller - found by eye, in
output that test exists to make impossible. When a guard fires, ask what it
cannot see rather than only whether it fired.

## The uncomfortable half

Three of the four were mine, introduced the same day I found them. Defect 4 was
not mine and I nearly compounded it: I called two column-state mismatches
"pre-existing" twice before running the one command that showed main was green
on that test and the readers were ours.

**So the honest version of the observation is not "measurement finds what review
misses".** It is that measurement finds what its author could not see, including
when its author is the reviewer, and that the specific mechanism is redundancy
between numbers rather than attention paid to any one of them.
