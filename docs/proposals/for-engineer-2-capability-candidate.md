# `capability_candidate`: where a proposed capability key should live

**Proposed, not taken. No table was created and nothing was written to an
existing one.** The classification pass produced proposed capability keys and
there is no table that means that, so its output is a file and this document.

*Engineer 1 · 2026-08-28*

---

## 1 · Why nothing was written

The pass asks a model to propose a capability key where none of the twelve fits.
Three existing tables could have absorbed the output and each would have meant
something false:

```
capability          the CONTRACT's twelve keys, loaded from
                    contract/capabilities.yaml, and the table `claim` has a
                    foreign key to. Writing a proposal here makes it a key a
                    claim can be filed against - the vocabulary decision taken
                    by an insert.

claim               requires model_version_id, quote_verified = true, and a
                    capability_key that FKs to the above. A classification
                    verdict is not a claim: no polarity, no condition bucket,
                    no evidence tier.

coverage_gap        "what we could not cover". A capability nobody has a key
                    for is arguably that, but the table's `kind` vocabulary is
                    about unsourced models and out-of-window versions, and
                    widening it to hold a vocabulary proposal would make its
                    own counts unreadable.
```

**The third is the one worth naming.** `coverage_gap` is the closest fit and it
is the most dangerous, because the row would insert cleanly and quietly change
what a coverage figure counts.

## 2 · The shape

```sql
-- A capability key a model PROPOSED and nobody has ruled on. NOT a capability.
--
-- `capability` holds the twelve keys the contract defines and `claim` FKs to it.
-- This table deliberately has no relationship to either: a proposal that a claim
-- could be filed against is a vocabulary decision taken by an INSERT, and the
-- capability list is contract/capabilities.yaml's to change.
CREATE TABLE capability_candidate (
  id                text PRIMARY KEY,

  -- The proposed key, in the dotted style of the real ones. NOT UNIQUE:
  -- the same name proposed from two documents is two pieces of evidence, and
  -- collapsing them would lose the count that decides whether it is a real
  -- capability or one person's phrasing. See `occurrences` below.
  proposed_key      text NOT NULL,
  definition        text NOT NULL,

  -- WHERE IT CAME FROM. A proposal with no document behind it is an opinion.
  document_id       text NOT NULL REFERENCES document(id),
  quote             text NOT NULL,

  -- Rule 1's shape, even though this is not a claim. The quote is checked by
  -- exact substring match against the text the model was shown, and a proposal
  -- whose quote does not verify is stored with `false` rather than discarded -
  -- a fabricated span is the most interesting thing this table can hold.
  quote_verified    boolean NOT NULL,

  -- Which model produced the proposal, and under which prompt. A temporary
  -- prompt's output must not be indistinguishable from the extractor's.
  proposer_model    text NOT NULL,
  prompt_label      text NOT NULL,

  pipeline_version  text NOT NULL,
  created_at        timestamptz NOT NULL DEFAULT now(),

  -- A person's ruling, and NULL means nobody has looked. Not "rejected".
  reviewed_at       timestamptz,
  ruling            text,
  CONSTRAINT capability_candidate_ruling_ck
    CHECK (ruling IS NULL OR ruling IN ('adopted', 'declined', 'merged')),
  -- The two must not disagree: a ruling with no date is a claim about a review
  -- that may not have happened.
  CONSTRAINT capability_candidate_reviewed_ck
    CHECK ((ruling IS NULL) = (reviewed_at IS NULL))
);
CREATE INDEX capability_candidate_key_idx ON capability_candidate (proposed_key);
```

## 3 · The one design decision that matters

**`proposed_key` is not UNIQUE, and that is the point.**

A proposal backed by one quote and a proposal backed by nine are different
things, and the count is what separates a real capability from one person's
phrasing. Deduplicating on the name would store the first and discard the
evidence that the other eight exist — and the evidence is the whole reason to
have the table.

So the unit is **one row per (proposal, document)**, and "how many documents
proposed this key" is a `GROUP BY` rather than a column. A count that has to be
maintained is a count that goes stale; a count derived from rows cannot.

## 4 · What it does NOT hold

**No score, no confidence, no ranking.** Rule 3: every figure that reaches a page
is counted or measured. "How many documents proposed this" is a count.
"How likely is this to be a real capability" is a synthesised number and has no
place here.

**No `model_version_id`.** A proposed capability is about the vocabulary, not
about a model. The document is the provenance; which model the document discussed
is recoverable through it and is not this table's business.

## 5 · Until it exists

The classification output is a JSONL file plus the write-up, and every proposal
in it carries its document, its permalink and its quote. That is enough to rule
on the vocabulary without a table — **and it is not enough to accumulate**, which
is the argument for the table rather than for the file.

If you would rather not add a table for a temporary prompt's output, the
honest alternative is to keep it a file and say so where the numbers are quoted.
What must not happen is the proposals going into `capability`.
