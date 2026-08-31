# Twice in two days, a state changed without its reason — and the guard asked for it that way

**This is not two people forgetting. The failure message names the state and does
not name the reason, so the minimal edit that makes the test green is exactly the
edit that loses the information the file exists to hold.** I wrote that message.

*Engineer 1 · 2026-08-28*

---

## 1 · Both incidents

```
2026-08-27  thread_context.assembled_at   write_only -> read
            flipped in the #166 conflict resolution, reviewed: false, no why.
            The reader was scripts/fetch_model.py:295, ORDER BY assembled_at DESC,
            landed by #163.

2026-08-28  harvest_run.id                write_only -> read
            flipped on the #182 branch, reviewed: false, no why.
            The readers were ops/sweep_reddit.py and scripts/model_only_sweep.py
            carrying opened.id onto documents, and document.harvest_run_id is a
            foreign key to it.
```

Both times the state was **correct**. Both times the reason was recoverable in
about two minutes by grepping. And both times it was not recorded, in the file
whose entire premise is that the state is *declared* rather than *discovered*.

## 2 · Why it is a design fault and not a discipline one

Here is the assertion I wrote:

```python
assert not mismatched, (
    f"{len(mismatched)} column(s) are not in the state they declare, and "
    f"none names a `known_gap`:\n  " + "\n  ".join(mismatched[:20])
)
```

It reports `declared 'write_only', discovered 'read'`. **The smallest change that
turns that red into green is to edit one word.** No part of the message asks why,
so a person doing the obviously-correct thing produces a snapshot with the reason
missing — and the test then passes, which confirms they were done.

Both incidents were somebody resolving a test failure competently. The guard got
what it asked for.

**And it is the same class as the thing the guard was built to catch.** A column
whose state nobody declared reads as a considered state; a state changed without
its reason reads as a declaration. The file was designed against the first and is
generating the second.

## 3 · What I propose

**Two parts, and the first is free.**

### 3.1 · The failure message asks for the reason

```python
assert not mismatched, (
    f"{len(mismatched)} column(s) are not in the state they declare:\n  "
    + "\n  ".join(mismatched[:20])
    + "\n\nIf the discovered state is now correct, DO NOT ONLY EDIT THE STATE. "
      "Set `reviewed: true` and add a `why` naming the reader or writer that "
      "changed — a state edited without its reason is a snapshot wearing a "
      "declaration's clothes, which is what this file exists to prevent. "
      "If the declaration is the intent and the code has not caught up, add "
      "`known_gap` instead."
)
```

Costs nothing, ships with the next commit, and addresses the actual mechanism.
**I would do this whether or not §3.2 is accepted.**

### 3.2 · The test requires it, by comparing against the committed file

A state change is invisible to a test that only sees the current file, so the test
has to read the previous version:

```
test_a_changed_state_carries_its_reason
  1. read contract/column_states.yaml from the merge base (git show)
  2. for every column whose `state` differs from that version:
       require reviewed: true AND a non-empty why
  3. a NEW column is exempt — it has no previous state, and the initial
     declaration is already governed by the entry-exists test
```

**Three things I do not like about it, stated because they are the reasons you
might refuse.**

It needs git in the test process. CI has the checkout, but a test that shells out
to git fails differently on a shallow clone or a detached HEAD, and a guard whose
failure mode is "could not determine the baseline" is one people learn to skip.
The mitigation is that it must **skip and say so** rather than pass — the same
rule `triage.gates` already applies: a check that cannot run has not passed.

It makes the manifest harder to regenerate. `scripts/audit_columns.py` output
currently regenerates snapshot entries wholesale; under this rule a regeneration
that moves any state needs a `why` per moved entry, which is correct and is also
friction on exactly the workflow that keeps the file current.

And it can be satisfied with a bad `why`. Nothing stops `why: state changed`.
That is true of every `why` in the file, including the twenty-five I wrote, and
the answer is review rather than machinery.

## 4 · What I am not proposing

**Not blocking on `reviewed: true` for snapshots.** 281 of 306 entries are
snapshots nobody has ruled on, and requiring a decision before a column can exist
would make declaring a prerequisite for adding — which I refused when I built the
file and still refuse.

The rule is narrow on purpose: **an entry that CHANGES needs a reason. An entry
that appears needs only to exist.**

## 5 · The honest scoring of this

Twice in two days is a pattern, and it is a two-day-old file, so the base rate is
one per day of existence. That is not enough to know whether the message fix alone
solves it — and §3.1 is cheap enough that it does not need to be.

**What would tell us:** ship §3.1, and if a third state changes without a reason
after that, §3.2 is justified by evidence rather than by argument. Until then
§3.2 is a mechanism proposed on two instances, which is the same standard I held
the signal-vocabulary work to and should hold this to.
