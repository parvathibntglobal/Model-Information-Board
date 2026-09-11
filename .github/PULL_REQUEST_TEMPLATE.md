<!--
The checklist is the moment-it-matters enforcement for the rules a helpful
refactor quietly violates (CLAUDE.md). Delete lines that don't apply; keep the
ones that do and answer them. An unchecked box is a fine answer if you say why.
-->

## What this changes

<!-- One or two sentences. What broke, or what this enables. -->

## Rule check

- [ ] **Rule 8 — an unmeasured check ships as a weight, not a gate.**
      If this PR adds or changes a filter/gate/drop:
      **what population was its error rate measured on, and did the filter, or
      anything upstream of it, choose that population?** ("No, I used the whole
      corpus" is not an answer when the corpus is an earlier filter's output.)
      If it hasn't been measured against a population it did not choose, it
      ships as a weight/flag/recorded field, not a gate.
      (Argument: `docs/weight-before-drop.md`.)
- [ ] **Contract change?** `contract/` is the agreement — flagged and reviewed
      by the other person, never taken solo.
- [ ] **Numbers carry their denominator and where it came from** (rules 6, 7).
- [ ] **A caused absence is not a found one** (rule 4): anything dropped is
      recorded and shown (`/filtered`), not silently removed.
- [ ] **Staging writes coordinated** if this touches the shared DB: append-only,
      no global rebuild, migrations applied once/in-order/announced same day.

## Migration in this PR?

<!-- Delete this whole section if `contract/migrations/` is untouched. -->

- [ ] The body says **who runs `db migrate`, and when**.
- [ ] That person is **whoever merges this PR**, immediately after merge.
- [ ] It is **announced the same day**, as a comment on this PR, with the
      `db check` output before and after.

> ⚠ **A MIGRATION DOES NOT APPLY ON MERGE.** Merging ships the FILE. A
> person runs the runner. The writer that depends on the new column ships
> as CODE and takes effect the moment somebody pulls — so between the merge
> and the migrate, every other machine has a writer for a schema it does
> not have.
>
> Do not write *"applies on merge"*, *"lands with this"*, or *"the ledger
> is clean so it will apply"*. All three read as **no action required**.
>
> The third of those was written in #260 and cost a run: the writer merged
> at 11:16Z and reached the other machine on a pull; the migration reached
> it as a file nobody had run; E5 died on `column "model_scope" of relation
> "board_entry" does not exist` and spent three extract calls doing it.
> Applied at 13:13Z, two hours later.

## Measurements

<!-- If this PR is backed by a measurement, put the number and its population
here, not only in a linked doc — measurements travel the day they're taken. -->
