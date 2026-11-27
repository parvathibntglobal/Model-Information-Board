-- TEXT IN A "NOT READABLE" POST'S FIRST PICTURE, SHADOW MODE (anooj, 2026-11-26;
-- #679 step 3; CLAUDE.md's fourth fetch exception, #683).
--
--   ocr_text        every word Tesseract read, space separated. NULL = not read;
--                   '' = cleared after retention.clear_text_after_days, whatever the
--                   post's label (store.clear_picture_text).
--   ocr_confidence  each word's confidence (0-100), in the same order, so
--                   ocr.min_confidence can be set from the shadow week's hand-check
--                   without fetching a picture again.
--   ocr_status      ok | no_text | failed | too_large | over_cap | refused (robots.txt);
--                   NULL = not tried (rule 6).
--
-- The text decides no label (contract ocr.affects_labels: false); it sets the flags
-- picture_text_would_pass / picture_text_only_ai. Nothing is read until the contract's
-- ocr.enabled is set true by its own PR.
--
-- WHO RUNS THIS MIGRATION: the person who merges the PR that adds it, on the shared
-- database, straight after merge, with `db check` before and after, and announces it
-- on that PR the same day. Until it has run, the Industry AI run refuses before any
-- request (scripts/run_industry_ai.py, store.missing_columns checks these columns).
--
-- No transaction control here: the runner owns the transaction.

ALTER TABLE iai_item ADD COLUMN IF NOT EXISTS ocr_text text;
ALTER TABLE iai_item ADD COLUMN IF NOT EXISTS ocr_confidence smallint[];
ALTER TABLE iai_item ADD COLUMN IF NOT EXISTS ocr_status text;
ALTER TABLE iai_item DROP CONSTRAINT IF EXISTS iai_item_ocr_status_ck;
ALTER TABLE iai_item ADD CONSTRAINT iai_item_ocr_status_ck
  CHECK (ocr_status IS NULL
         OR ocr_status IN ('ok', 'no_text', 'failed', 'too_large', 'over_cap', 'refused'));
