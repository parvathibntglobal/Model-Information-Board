-- Record whether a board entry's model was SEARCHED FOR or merely MENTIONED.
--
-- WHY THIS IS A COLUMN AND NOT AN INFERENCE. The distinction already existed in
-- the data, by accident: `board_entry.model_version_id` held the canonical id
-- (`anthropic/claude-fable-5-1`) for the model a run was FOR, because
-- `fetch_model.py` passes the CLI argument straight through - and the internal
-- key (`mv_4247e801b…`) for a model resolved out of the text through
-- `model_alias`. Two writers, two shapes, one column. Measured 2026-09-11 on a
-- single run: 11 canonical against 35 internal.
--
-- That accident was the only carrier of the distinction, and it was never
-- reliable - it depended on two code paths continuing to disagree. It stopped
-- being visible the same day, when the read path was fixed to resolve both
-- shapes to one display name so the board would stop rendering `mv_4247e801…`
-- where a model name belongs. The fix was right and it erased the signal, so
-- the signal has to be recorded on purpose.
--
-- WHY IT MATTERS FOR THE COUNTS. A run for one model produces claims about
-- every model the threads compared it against - 2 of 40 were about the model
-- searched for on 2026-09-11. Those comparisons are KEPT, ruled by both
-- engineers: a claim that Fable is cheaper than DeepSeek is evidence about
-- both. But a section's counts then mix a model searched exhaustively with one
-- mentioned once in passing, and nothing on the page says which. That is rule
-- 7 - a figure whose population is unstated - and this column is the
-- population.
--
-- NULL IS A REAL STATE AND IS NOT BACKFILLED. Rows written before this column
-- existed genuinely do not record it, and guessing from the id shape would
-- bake the accident in as though it had been a decision (rule 6). They stay
-- NULL and read as "not recorded", which is true.

ALTER TABLE board_entry ADD COLUMN IF NOT EXISTS model_scope text;

ALTER TABLE board_entry DROP CONSTRAINT IF EXISTS board_entry_model_scope_ck;
ALTER TABLE board_entry ADD CONSTRAINT board_entry_model_scope_ck
  CHECK (model_scope IS NULL OR model_scope IN ('searched', 'mentioned'));

COMMENT ON COLUMN board_entry.model_scope IS
  'searched = this entry''s model is the one the run was for; mentioned = the '
  'model was named inside a thread retrieved for a different model. NULL = the '
  'run predates this column and did not record it, which is not the same as '
  'either value. Read it as the POPULATION behind a section''s counts: a '
  'section built from mentions has not been searched for and its count is not '
  'comparable with one that has.';
