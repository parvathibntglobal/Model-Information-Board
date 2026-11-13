-- Keep WHO IS SPEAKING on the board row: own-experience, vendor-about-own-product,
-- or relayed-from-elsewhere. The extractor already answers this on every call
-- and the answer is thrown away.
--
-- THE DEFECT (rule 9: a paid value with no reader and no declaration).
-- `model_ref.speaking` is REQUIRED on every extracted claim
-- (judge/extract/schema.py, ModelRef.speaking), so every extraction call pays
-- output tokens for it. It was stored on `claim.speaking` only, and claim rows
-- are written only when LEGACY_CELLS is on (judge/legacy.py). No workflow sets
-- it, so since the board took over, the answer is computed, paid for and
-- discarded at write time. `board_entry` has no column for it. Measured
-- 2026-11-12 on the shared database: the newest `claim` row is from
-- 2026-10-01 (1,777 rows, 2026-08-20 to 2026-10-01), and 19,242 of the 22,004
-- `board_entry` rows were written after it. None of those can say whether the
-- person writing did the thing they describe.
--
-- WHY IT MATTERS. "Did the person writing do the thing they describe?" is the
-- first question a reader asks of a report, and for every row written since
-- 2026-10-01 the board cannot answer it without re-reading the quote. With the
-- column, first-hand reports can be counted rather than sampled.
--
-- WHAT THIS DOES NOT DO.
--   - No backfill and no DEFAULT. Every existing row gets NULL, which means
--     "not recorded" (the row predates the column). A default would assert a
--     speaker nobody observed: rule 6.
--   - No re-extraction. The answer exists only for rows written after this
--     lands.
--   - Not a gate. Like claim.speaking (harvest.yaml `not_a_storage_gate`),
--     it never decides whether a row is stored or shown (rule 8: the
--     extractor's accuracy on this field is unmeasured).
--
-- BOTH TABLES. `unresolved_entry` holds entries whose model is not seated yet,
-- and scripts/attribute_unresolved_entries.py files them onto board_entry with
-- no second model call. Without the column there, a held entry would lose its
-- speaker on the way to the board and arrive as NULL, a missing value we
-- caused rather than one we found.
--
-- The CHECK has no `IS NULL OR`: a CHECK fails only on FALSE, so `IN (...)`
-- already admits NULL, and contract/tables.sql must render the constraint
-- identically (the equivalence test compares pg_get_constraintdef text).
--
-- No BEGIN/COMMIT: the migration runner owns the transaction.

ALTER TABLE board_entry
  ADD COLUMN speaking text
  CHECK (speaking IN (
    'own-experience',
    'vendor-about-own-product',
    'relayed-from-elsewhere'
  ));

COMMENT ON COLUMN board_entry.speaking IS
  'Whose report this is, from the extractor''s model_ref.speaking: '
  'own-experience | vendor-about-own-product | relayed-from-elsewhere. '
  'NULL means not recorded (the row predates the column). Never gates '
  'storage or display.';

ALTER TABLE unresolved_entry
  ADD COLUMN speaking text
  CHECK (speaking IN (
    'own-experience',
    'vendor-about-own-product',
    'relayed-from-elsewhere'
  ));

COMMENT ON COLUMN unresolved_entry.speaking IS
  'model_ref.speaking for a held entry, carried onto board_entry.speaking '
  'when the model is seated. NULL means not recorded.';
