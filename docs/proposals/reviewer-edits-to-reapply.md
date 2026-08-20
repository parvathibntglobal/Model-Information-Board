# Reviewer edits to re-apply after a `--force` regenerate

**Captured 2026-08-20, BEFORE regenerating, because `--force` discards them.
Exactly two entries of hand work. The `(free)` strips come back from the
generator and need no re-application — confirmed in code, not assumed.**

*Engineer 1 · against `docs/proposals/alias-surfaces-tracked-set.yaml` as
reviewed*

---

## Why this file exists rather than a note in a message

`_refuse_to_discard_review` refuses to overwrite the artifact and names the
markers it found, so a regenerate needs `--force`. `--force` then writes a fresh
file from the generator, and everything a reviewer decided is gone — including
the decision that a *generated* value was wrong, which is the only kind of edit
that leaves no trace in the input.

So the re-apply is a paste rather than an archaeology exercise, and this is the
thing to paste.

## What comes back for free, confirmed in the generator

**The six `(free)` drops.** `propose.strip_pricing_annotation` handles both
arrival shapes — the id's own tier suffix (`dots-3-note-preview:free`) and the
feed's display name (`Dots Studio: Dots3-Note Preview (free)`) — against the
closed set `{free, batch, fast, nitro, floor}`. It is applied inside
`mechanical_variants` before any rendering, so no derived form can carry a price
tier.

Deliberately **not** in that set: `extended` and `thinking`. They change what the
model *does* rather than what it costs, so a surface carrying one may be a real
distinction people write. If a seventh annotation appears it arrives as an
unstripped surface a reviewer can see, rather than as a silently deleted name.

**So the `(free)` work is not hand work and must not be re-applied by hand** —
doing so would be indistinguishable from the generator having done it, and the
next regenerate would look like it lost something.

## What does NOT come back: two reseats

Both are the same judgement, and it is one the generator cannot make: **a bare
date matches most loosely, so it must not be the primary surface** — even though
it is the only *attested* form and the generator therefore promotes it.

### 1 · `deepseek/deepseek-v4-flash-0731`

```yaml
  - canonical_id: deepseek/deepseek-v4-flash-0731
    status: attested
    seated_by: launch-window          # inside the launch window AND below the mention floor: attested, but not by enough to seat it
    surface: deepseek v4 flash        # by rule (vendor-drop), unattested — reseated 2026-08-19
    variants:
      - deepseek flash 0731           # attested 3 mentions [slice 3]; DEMOTED — a bare date matches most loosely
      - deepseek-v4-flash             # mechanical, unattested
      - deepseekv4flash               # mechanical, unattested
      - deepseek v4 flash 0731        # mechanical, unattested
      - deepseek-v4-flash-0731        # mechanical, unattested
      - deepseekv4flash0731           # mechanical, unattested
    incomplete: [family_surface]
```

**The generator will emit `deepseek flash 0731` as the primary**, because
`AliasProposal.surface` returns the most-mentioned attested surface and that is
the only attested one (3 mentions, all substitution-slice). The reseat promotes
the by-rule form and demotes the attested one.

### 2 · `deepseek/deepseek-v4-pro-0813`

```yaml
  - canonical_id: deepseek/deepseek-v4-pro-0813
    status: attested
    seated_by: launch-window          # inside the launch window AND below the mention floor: attested, but not by enough to seat it
    surface: deepseek v4 pro        # by rule (vendor-drop), unattested — reseated 2026-08-19
    variants:
      - deepseek 0813                 # attested 1 mentions [sweep 1]; DEMOTED — a bare date matches most loosely
      - deepseek-v4-pro               # mechanical, unattested
      - deepseekv4pro                 # mechanical, unattested
      - deepseek v4 pro 0813          # mechanical, unattested
      - deepseek-v4-pro-0813          # mechanical, unattested
      - deepseekv4pro0813             # mechanical, unattested
    incomplete: [family_surface]
```

Same shape, on a single mention. `deepseek 0813` is **one** attested mention from
the general sweep, and it is a bare vendor word plus a date — the loosest thing
in the file.

## The rule underneath both, worth promoting out of two comments

**An attested surface is not automatically the best primary.** The proposer ranks
by mention count because that is what the corpus can measure, and mention count
does not measure *specificity*. `deepseek 0813` is attested and matches almost
anything deepseek-shaped with a date near it; `deepseek v4 pro` is unattested and
names a tier.

That is the same trade `classify_specificity` already makes — a bare family word
resolves at `family` and never counts as independent corroboration — one level
down, at the surface rather than at the claim. **If the generator learned it,
these two reseats would come back for free too**, and the rule is stateable:
*a surface whose only distinguishing token is a date stamp is not a primary.*
`propose.py` already has `_DATE_STAMP` and uses it to stop the vendor-drop rule
deriving from a snapshot id; the same regex would demote here.

Not taken, because it changes what the generator proposes for all 63 entries and
that is a reviewed output. Recorded as the durable fix rather than a third
hand-edit next time.

## How to re-apply

1. Regenerate with `--force`.
2. Confirm the six `(free)` forms are absent — they should be, from the
   generator. If any is present, `strip_pricing_annotation` regressed and that is
   a code fix, not a hand edit.
3. Paste the two blocks above over the generated `deepseek/deepseek-v4-flash-0731`
   and `deepseek/deepseek-v4-pro-0813` entries.
4. Check `seated_by` on both against the new run. It was `launch-window` on
   2026-08-19 and **may not be after a re-poll** — the launch window slides, and
   both ids carry a date-stamped release. If either now reads `attested`, the
   comment explaining the seat is wrong and the reseat comment stays right.
