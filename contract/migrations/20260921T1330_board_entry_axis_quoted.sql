-- Record whether a metric row's AXIS was quoted, and keep the words it was
-- quoted from. #368, decided 2026-09-18 and unbuilt until now.
--
-- THE DEFECT, IN ONE ROW THAT IS ON THE BOARD RIGHT NOW. The Spotify
-- engineering post produced three board entries for `google/gemini-2.5-flash`,
-- and not one of their quotes names Gemini:
--
--     capability/reasoning   "The worker model found surface-level patterns
--                             but missed a subtle thread-safety bug in my
--                             testing. Claude spotted it in seconds"
--     capability/long-context "the corpus goes to the worker model and never
--                             enters Claude's context"
--     best_for/code-generation "For tests, config scaffolding, type stubs"
--
-- The subject is "the worker model", resolved to Gemini from somewhere else in
-- the document. It may even be right. But a NEGATIVE capability claim is
-- attributed to a model its own quote does not name, and nothing on the row or
-- the page says the attribution was inferred. That is what these columns are
-- for, and it is live rather than hypothetical.
--
-- WHAT THIS DOES NOT DO: it does not re-rule or delete anything. The 2026-09-18
-- ruling refused both. Re-extraction is unmeasured spend on a population whose
-- defect rate nobody has characterised - rule 8 one layer out. Leaving them is
-- rule 4 at the figure level, a row whose axis was never checked rendering
-- exactly like one that was. Marking is what this board does everywhere else.
--
-- ⚠ THREE STATES, AND `NULL` IS NOT `false`. Agreed by both engineers.
--
--     NULL   no check ran. The row predates the check.
--     true   `axis_verbatim` was copied AND found in the quote.
--     false  checked, and the slug is NOT backed by the quote. Two ways in:
--              - the quote named no benchmark at all (the common case)
--              - it named one that is not in the quote (fabricated, discarded)
--
--    `false` covers both deliberately. The page's question is "is this slug
--    backed by its quote", and for that they are the same answer. The two are
--    already told apart where the difference is actionable:
--    `judge/store/board_entries.py` counts `axis_absent` and
--    `axis_unsupported` separately per run. A fourth state would put a
--    distinction in the schema that the schema has no reader for.
--
-- ⚠ AND THE BOUNDARY IS A TIMESTAMP, WHICH IS A WEAKNESS WORTH NAMING.
--    Nothing on a row records whether its slug came from a verified axis, so
--    "predates the check" can only be `created_at < 2026-09-21T10:29:16Z` -
--    the moment #385 merged and `axis_slug()` started running.
--    `pipeline_version` cannot discriminate: it is `e5.4` on all 520 rows,
--    before and after. The exact instant is written here rather than "before
--    #385" because a reader in a month cannot recover that from an issue.
--
-- NO BACKFILL, AND NO DEFAULT. Every existing row gets NULL by omission, which
-- is the state they are entitled to. A DEFAULT false would assert that 520
-- rows were checked and failed, which is exactly the missing-becomes-definite
-- conversion rule 6 forbids.
--
-- ⚠ THE READER IS WHERE THIS CAN STILL GO WRONG, and it is not in this file.
--    A page that filters `WHERE axis_quoted = true` drops every NULL row
--    silently and shows a fraction of the board with nothing saying so - rule
--    4, an absence we caused. Three states must be RENDERED, never filtered
--    on. `swe-bench` is the case that proves it: 3 of its 39 quotes say
--    SWE-bench and 28 name no benchmark at all, so that page should look
--    almost entirely unquoted, because it is.
--
-- Population at the time of writing: 520 metric rows, of which those created
-- before the timestamp above are the ones this leaves NULL. The count is
-- deliberately not asserted as a number here - it moved from 440 to 496 to 520
-- across three readings in one day, and a figure in a migration is stale the
-- moment the next run commits.

ALTER TABLE board_entry ADD COLUMN IF NOT EXISTS axis_verbatim text;
ALTER TABLE board_entry ADD COLUMN IF NOT EXISTS subject_verbatim text;
ALTER TABLE board_entry ADD COLUMN IF NOT EXISTS axis_quoted boolean;

COMMENT ON COLUMN board_entry.axis_verbatim IS
  'The benchmark or axis name COPIED from the quote, character for character, '
  'or NULL when the quote named none. Carried on the extraction schema since '
  '#385 and thrown away at write time until this column existed - it set the '
  'slug and was discarded, so a stored row could not be asked what its slug '
  'was derived from (rule 9).';

COMMENT ON COLUMN board_entry.subject_verbatim IS
  'The model name COPIED from the quote, or NULL when the quote named none. '
  'The Spotify/Gemini rows are why: three entries attributing a capability to '
  'a model whose quote says only "the worker model". NULL here and a '
  'non-NULL model_version_id together mean the attribution was inferred from '
  'the document rather than read from the quote.';

COMMENT ON COLUMN board_entry.axis_quoted IS
  'NULL = no check ran, this row predates it (created_at < '
  '2026-09-21T10:29:16Z, when #385 merged). true = axis_verbatim was copied '
  'and found in the quote. false = checked and the slug is not backed by the '
  'quote, either because the quote named no benchmark or because it named one '
  'that is not there. NULL is NOT false: one is an unasked question and the '
  'other is an answer. Render all three; never filter on true.';
