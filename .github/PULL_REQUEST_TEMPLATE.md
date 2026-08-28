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
      **what population was its error rate measured on, and did the filter
      choose that population?** If it hasn't been measured against a population
      it did not choose, it ships as a weight/flag/recorded field, not a gate.
      (Argument: `docs/weight-before-drop.md`.)
- [ ] **Contract change?** `contract/` is the agreement — flagged and reviewed
      by the other person, never taken solo.
- [ ] **Numbers carry their denominator and where it came from** (rules 6, 7).
- [ ] **A caused absence is not a found one** (rule 4): anything dropped is
      recorded and shown (`/filtered`), not silently removed.
- [ ] **Staging writes coordinated** if this touches the shared DB: append-only,
      no global rebuild, migrations applied once/in-order/announced same day.

## Measurements

<!-- If this PR is backed by a measurement, put the number and its population
here, not only in a linked doc — measurements travel the day they're taken. -->
