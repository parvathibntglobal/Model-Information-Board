-- claim.polarity — admit 'neutral' as a third value.
--
-- ⚠ CONTRACT CHANGE, per the lane rule on contract/. Widens a CHECK on `claim`;
--   no column added, no row rewritten.
--
-- WHY. Polarity was positive|negative only, so the extractor was forced to call
-- every claim praise or criticism. Neutral factual observations — "the window
-- is 200k", "it uses X tokenizer" — have no sentiment, and forcing them one way
-- pushed them into `positive`, inflating apparent praise (21 positive to 2
-- negative on the live board, two of the positives self-contradictory: marked
-- positive while listing a `pain_point`). `neutral` is the honest third state.
--
-- WHAT IT MEANS DOWNSTREAM. A neutral claim is a VOICE, never a SENTIMENT: it
-- counts toward `independent_voices`, `platform_count` and `n_eff`, and toward
-- NEITHER `cell.positive` nor `cell.negative` — `judge/curate/gate.py:count`
-- tallies those by exact string, so it already ignores neutral. A cell whose
-- voices are all neutral clears the weight gate but has no direction to publish,
-- and `classify` returns INSUFFICIENT rather than CONTESTED for it — no
-- disagreement, just no sentiment.
--
-- BACKWARD COMPATIBLE. Widening a CHECK never invalidates an existing row: every
-- stored claim is 'positive' or 'negative' and stays valid. DROP then ADD so the
-- constraint definition matches `contract/tables.sql` byte for byte under
-- `pg_get_constraintdef` — the equivalence test in tests/test_migrations.py
-- compares the two, and a differently-worded CHECK would read as drift.

ALTER TABLE claim DROP CONSTRAINT claim_polarity_ck;

ALTER TABLE claim ADD CONSTRAINT claim_polarity_ck
  CHECK (polarity IN ('positive', 'negative', 'neutral'));
