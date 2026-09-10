# A value produced and never consumed

**Three defects in one week shared a shape, and it is not a shape any test can
see.** A stage computes a value, hands it onward, and nothing downstream reads
it. Every stage passes. The suite is green. The value costs money or
information, silently, for as long as nobody asks the one question that finds
it: **what reads this, and where?**

This is the argument for rule 9. It is written down because the three instances
were each fixed on their own, as three unrelated bugs, and the fourth will be
too unless the shape is named.

---

## 1 · The instances

### `comparison_target` — extracted, paid for, dropped

`judge/extract/schema.py:416` defines it:

```python
comparison_target: str | None = Field(
    default=None, description="set when the quote compares two models"
)
```

It is part of `ExtractedClaim`, `ExtractedClaim` is flattened into the forced
tool schema by `judge/extract/client.py:257`, and that schema is sent on
**every extraction call**. So the field name and its description are paid for
on input tokens, and any value the model returns is paid for on output tokens,
once per thread, nightly.

`comparison_target` appears **nowhere else under `judge/`**. There is no
persister. `claim.comparison_target_id` exists in `contract/tables.sql` and is
declared `state: reserved` in `contract/column_states.yaml:210`.

So: a language model is asked a question every night, answers it, is paid for
the answer, and code throws it away before it reaches the column reserved for
it. **This is the expensive one**, and it is the one that had no marker at all.

### `unattributed_reading` — published, never rendered

`judge/app.py` publishes it so that a quota reading written before `read_on`
existed is not lost under per-arm keying. It was added *specifically* to avoid
discarding evidence.

`web/src/components/UsagePanel.jsx` never referenced it. The API told the truth
and the page said "No reading yet" over a real 998,660-of-1,000,000 header
reading. Fixed in the PR that accompanies this document.

Note the sequence: **the fix for one instance of this shape created another.**
That is why a rule beats three fixes.

### `specificity_score` — written, declared, and honest

`contract/column_states.yaml:399`:

> `state: write_only` — *written by collect/triage/store.py since 2026-08-31.
> STILL WRITE-ONLY, and deliberately: E3's child ranking is the intended reader
> and is blocked on comment fetching … NO `known_gap` ON PURPOSE: that key
> makes the discovered-state check skip the column, and this one should start
> failing the day something reads it.*

**This is what the rule asks for.** The value is unconsumed, and that is
recorded, with the intended reader named and the reason it cannot read yet. A
reviewer meets no surprise, and the declaration is wired so it breaks when the
situation changes.

### `quota_exhausted` — computed, dropped, named

`collect/ops/ledger.py:_PROPOSED_NOT_IN_SCHEMA` drops it by name, with the
reason, and with PR #161 named as the fix. Its own comment says why the set
exists at all:

> *A permissive `{k: v for k, v in fields.items() if k in COLUMNS}` is how the
> first four would have vanished without anyone deciding.*

Also correct. The value is discarded and the discard is a decision somebody can
read.

---

## 2 · The discipline already exists — for columns only

`contract/column_states.yaml` declares a state for all **340** columns:

| state | count | meaning |
|---|---:|---|
| `read` | 186 | something reads it, and the audit knows what |
| `write_only` | 95 | **written and not read**, declared |
| `reserved` | 45 | exists in the schema, nothing writes it yet |
| `unwired` | 7 | written by code no caller reaches |
| `defaulted` | 3 | the database writes it, we never do |
| `read_not_by_query` | 3 | read, but not through a query |
| `generated` | 1 | computed by the database |

**150 of 340 columns are declared as not-currently-read, and that is a
strength.** The audit is why `specificity_score` is a documented state rather
than a discovery. It also means "produced and never consumed" is *already*
measured for the schema — nobody needs convincing that the shape is real.

**And it stops at the schema boundary.** All four states above describe
*columns*. Three of the four instances in §1 are not columns:

| what it is | covered by the column audit? |
|---|---|
| a field in an LLM tool schema | **no** |
| a field in an API JSON payload | **no** |
| an adapter field dropped before the DB | **no** |
| a database column | yes |

`comparison_target` is invisible to `column_states.yaml` precisely *because* it
never reaches a column. The most expensive instance is the one furthest outside
the only place we look.

---

## 3 · Why no test can catch it

The same reason rules 7 and 8 are reviewer questions.

A test can assert that a value is produced. A test can assert that a consumer,
**given** the value, behaves correctly. Neither can assert that a consumer
*exists*, because the absence of a reader is not a behaviour — it is a
silence, and a test that passes over a silence looks identical to one that
passes over a correct answer.

Nor is a grep sufficient, though it helps. `comparison_target` greps to two
hits, both in the file that defines it. But `unattributed_reading` greps to one
hit in Python and one in JSX *after* the fix, and to one hit before — and
distinguishing "one definition, one use" from "one definition, no use" needs
the reader to know which file is which lane. What finds it reliably is the
question, asked of anything new:

> **What reads this, and where — file and line?**

If the answer is "nothing yet", the follow-up is not "delete it". It is
**"then declare that, with the intended reader and why it cannot read yet"** —
which is exactly what `specificity_score` and `quota_exhausted` already do.

## 4 · Deletion is the wrong default

Three of the four instances should NOT be deleted:

- `specificity_score` has a real intended reader, blocked on other work.
- `quota_exhausted` has a real intended fix, in a named PR.
- `comparison_target` is a field we *want*; the defect is the missing
  persister, not the field. Deleting it would discard a capability the
  extractor already provides and we already pay for.

Only `unattributed_reading` needed the consumer written, and that is because it
was one commit old.

So the rule is about **declaration**, not pruning. A value with no reader is
not necessarily waste; a value with no reader **and no statement about it** is
always a defect, because the next person cannot tell those two apart.

## 5 · The cost is of two kinds, and one of them is money

Worth separating, because they are argued differently:

**Information.** An unread value is a measurement we took and cannot use.
`specificity_score` is 3,054 rows of computed signal that no ranking consumes.
That is recoverable at any time — the data is there.

**Money.** `comparison_target` is tokens spent on every extraction call, in and
out, for an answer that is discarded before it is stored. The whole corpus
extracts for $1.84 at $0.00208 a thread
(`docs/measurements/extraction-token-counts.md`), so the absolute figure here is
small — and it is a **rate**, not a one-off: it recurs on every re-run of every
thread, forever, and it is invisible on any invoice because it is a fraction of
a call nobody itemises.

**The money case is the one that argues for a rule rather than a checklist**,
because information can be recovered later and spend cannot.

---

*Instances verified 2026-09-10 against `main` at `f470ad3`. The
`comparison_target` claim was checked by generating the tool schema and
searching it, not by reading the field definition —
`ExtractedClaim.model_json_schema()` contains `comparison_target`, which is what
makes it a paid field rather than a dead one.*
