-- `unpolled`: a real model OpenRouter does not list, hand-entered so the board
-- can link it. #382, agreed by both engineers 2026-09-21.
--
-- THE DEFECT THIS CLOSES IS A VOCABULARY GAP, NOT A BAD ROW. `provenance`
-- allowed `seed | polled` and the world has three states:
--
--     polled     OpenRouter carries it. 344 rows.
--     seed       a BUILD FIXTURE that polling replaces, and
--                `assert_no_fixtures` refuses it outside development.
--     unpolled   a real model hand-entered because no poll will ever carry it,
--                or has not carried it yet. Nothing about it is a fixture.
--
-- With no value for the third, four real models were labelled with the word
-- that means fixture. `assert_no_fixtures` then refused them correctly by its
-- own definition and wrongly by intent, and three contract files accumulated
-- (`seed_models.yaml`, `unpolled_models.yaml`, `awaiting_poll_models.yaml`)
-- each added to dodge a load refusal rather than to mean something different.
--
-- ⚠ THE FOUR ROWS ARE NOT FIXTURES AND CARRY REAL EVIDENCE. Measured against
-- this database 2026-09-23, which is why this migration converts rather than
-- deletes:
--
--     google/gemini-3.8-flash    60 claims   7 cells   87 board entries
--     elevenlabs/eleven-v3        5 claims   4 cells    5 board entries
--     recraft/recraft-v4.1-pro    0          0          0
--     qwen/qwen3.5-omni-flash     0          0          0
--                                --                    --
--                                65         11         92
--
-- Every one of the 65 traces to a harvested document with a real quote,
-- extracted by ordinary fetch runs (devto 49, hackernews 12, reddit 4).
-- Deleting the rows to satisfy a column's vocabulary would destroy evidence to
-- fix a label.
--
-- WHY `unpolled` AND NOT A SECOND BOOLEAN. Two columns encoding one fact is
-- how `provenance` came to carry two meanings in the first place; a boolean
-- buys safety by repeating the mistake one layer out. Refused 2026-09-21.
--
-- ⚠ AND WHY ONE VALUE COVERS BOTH CONTRACT FILES, WHICH IS THE ONE JUDGEMENT
--   CALL IN THIS FILE AND IS WORTH DISAGREEING WITH IF YOU DO.
--
--   `unpolled_models.yaml` holds models the poll will NEVER bring - Recraft,
--   ElevenLabs, Qwen's Omni speech line - because OpenRouter lists no
--   standalone image or speech vendor. `awaiting_poll_models.yaml` holds
--   Gemini 3.8 Flash, which the poll WILL bring the day it ships. Those files
--   argue at length that they are different claims about the world, and they
--   are right.
--
--   They are NOT different claims about this column. `provenance` answers
--   "where did this row come from", and for both the answer is "a person put
--   it here because the poll had not". The never/eventually distinction is a
--   prediction about the future, it already lives in the two files' own prose,
--   and #382 explicitly refused adding encodings to dodge refusals - "a fourth
--   file is worse than a migration", and a fourth VALUE is the same trade.
--
--   What actually depends on the distinction is the downgrade guard, and that
--   is handled in code rather than here: `_refuse_provenance_downgrade` now
--   permits `unpolled -> polled` (the poll catching up to Gemini 3.8 Flash,
--   which is the correct outcome - at that point the poll owns the row) and
--   still refuses `polled -> unpolled` and `polled -> seed`.
--
-- WHAT THIS DOES NOT TOUCH. `assert_no_fixtures` is UNCHANGED, and that is the
-- point rather than an omission: it already queries `provenance = 'seed'`
-- exactly. Converting the four rows makes the guard stricter in intent and
-- unchanged in code - it goes back to meaning what it always meant, and
-- `seed_models.yaml`'s eleven build fixtures are still refused outside
-- development.
--
-- REVERSIBILITY. `UPDATE model_version SET provenance='seed' WHERE provenance
-- ='unpolled'` then restore the old CHECK. No row is deleted and no column is
-- dropped, so this migration loses nothing on the way back.

ALTER TABLE model_version
  DROP CONSTRAINT model_version_provenance_ck;

ALTER TABLE model_version
  ADD CONSTRAINT model_version_provenance_ck
  CHECK (provenance IN ('seed', 'polled', 'unpolled'));

-- KEYED ON canonical_id FROM THE TWO CONTRACT FILES, NOT ON `provenance =
-- 'seed'`. A blanket update would also convert any genuine `seed_models.yaml`
-- fixture that happens to be present on the database this runs against - a
-- local or freshly-seeded one holds eleven - and silently relabel eleven
-- fixtures as real models. That is the exact missing-becomes-definite
-- conversion this migration exists to undo, pointed the other way.
--
-- Listed literally rather than read from the YAML because a migration cannot
-- import the repository, and because the four names are the thing being
-- asserted: if a fifth is seated later it must be loaded as `unpolled`
-- directly, not swept up by a migration nobody re-reads.
UPDATE model_version
   SET provenance = 'unpolled',
       updated_at = now()
 WHERE provenance = 'seed'
   AND canonical_id IN (
         'recraft/recraft-v4.1-pro',     -- unpolled_models.yaml, 2026-09-15
         'elevenlabs/eleven-v3',         -- unpolled_models.yaml, 2026-09-15
         'qwen/qwen3.5-omni-flash',      -- unpolled_models.yaml, 2026-09-15
         'google/gemini-3.8-flash'       -- awaiting_poll_models.yaml, 2026-09-17
       );

-- POST-CONDITION, so a run that converted nothing fails loudly rather than
-- reporting success. On the shared staging database this must leave zero
-- `seed` rows; on a database that also holds `seed_models.yaml`'s eleven
-- fixtures it leaves those eleven, which is correct - so the assertion is
-- about the FOUR, not about the total.
DO $$
DECLARE remaining int;
BEGIN
  SELECT count(*) INTO remaining
    FROM model_version
   WHERE provenance = 'seed'
     AND canonical_id IN ('recraft/recraft-v4.1-pro', 'elevenlabs/eleven-v3',
                          'qwen/qwen3.5-omni-flash', 'google/gemini-3.8-flash');
  IF remaining > 0 THEN
    RAISE EXCEPTION
      'unpolled conversion incomplete: % of the four still carry provenance=seed',
      remaining;
  END IF;
END $$;
