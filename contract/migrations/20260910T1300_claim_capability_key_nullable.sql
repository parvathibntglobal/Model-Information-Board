-- claim.capability_key becomes NULLABLE — the closed vocabulary stops gating the open one.
--
-- WHAT THIS UNBLOCKS. The board discovers three open vocabularies from the
-- evidence: best_for, capability, metric. `board_entry` was built for exactly
-- that and its `claim_id` is nullable on purpose, so an entry can stand alone.
-- But `claim.capability_key` was `NOT NULL REFERENCES capability(key)`, and
-- `judge/pipeline.py` writes board rows inside the claim-write loop — so every
-- discovered section was gated behind a closed list of twelve.
--
-- HOW BADLY THE TWELVE FIT. Of the eight capability sections on the demo board
-- the classifier is calibrated against, SIX have no ratified key:
--
--     structured-output      -> format.structured_output    ✓
--     reasoning              -> reasoning.multistep         ✓
--     function-calling       -> none
--     agentic-tool-use       -> none
--     long-context           -> none
--     instruction-following  -> none
--     vision                 -> none
--     multimodal             -> none
--
-- `judge/extract/prompt.py` says this in its own words: a classifier restricted
-- to that list "would have dropped a third of the board, or forced those quotes
-- into the nearest ratified key — which manufactures agreement about something
-- nobody said." The NOT NULL made the forcing mandatory.
--
-- WHAT THIS IS NOT. The twelve are not deleted and the FK is not dropped: a
-- claim that genuinely IS about `format.structured_output` still says so, still
-- references the row, and still prices a cell. What changes is that a claim
-- about `vision` may now record NULL instead of picking a neighbour — and its
-- board entry lands either way.
--
-- The unratified key is not lost. `proposed_capabilities` already carries it to
-- `capability_candidate` for a person to rule on, which is the design: an LLM
-- may propose, it may never decide.
--
-- REVERSIBLE ONLY WHILE NO NULL EXISTS. Re-adding NOT NULL after a NULL has
-- been written would fail, which is the correct behaviour rather than a trap:
-- restoring it means deciding what those claims' keys should have been, and
-- that is a ruling, not a migration.

ALTER TABLE claim ALTER COLUMN capability_key DROP NOT NULL;

COMMENT ON COLUMN claim.capability_key IS
  'A ratified key from contract/capabilities.yaml, or NULL when the behaviour '
  'the writer described matches none of them. NULLABLE since 2026-09-10: the '
  'board''s capability section is DISCOVERED and unbounded, and six of the '
  'eight sections on the reference board have no ratified key at all. NULL here '
  'means "no ratified key fits", never "no capability" — the discovered section '
  'is on board_entry, and the unratified key is on capability_candidate for a '
  'person to rule on. This column feeds the legacy cell score only.';
