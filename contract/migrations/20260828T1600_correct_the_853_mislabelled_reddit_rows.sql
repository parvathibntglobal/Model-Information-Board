-- The 853 reddit documents mislabelled `no_run_for_source` become `not_recorded`.
--
-- ⚠ NEEDS E2's SIGN-OFF, per the lane rule on contract/. Proposed in
--   docs/proposals/for-engineer-2-the-853-rows-and-withdrawing-the-fourth-value.md
--   No schema change: one UPDATE, and the CHECK is untouched.
--
-- WHAT IS WRONG WITH THEM
--
-- `no_run_for_source` is a POSITIVE claim: this run rendered no query, so a NULL
-- `harvest_run_id` is complete and there is nothing missing. For these rows it is
-- false. E2 confirmed on issue #160 that the per-model fetch's reddit arm inserted
-- them, and that arm issues model-name QUERIES.
--
-- So the rows assert "there was nothing to record" where the truth is "something
-- was not recorded". **A positive claim that nothing is missing is worse than the
-- absent value it was chosen over**, because a reader has nothing to disagree
-- with — rule 6, on the column added to prevent exactly this.
--
-- WHY `not_recorded` AND NOT A NEW VALUE
--
-- The vocabulary already covers it. `contract/tables.sql` defines `not_recorded`
-- as *"a run existed, OR MIGHT HAVE, and nobody wrote it down"* — which is these
-- rows precisely. A fourth value (`unreviewed_writer`) was added on 2026-08-28
-- and withdrawn the same day: it described the CODE that wrote the row rather
-- than what retrieved it, and a fourth value breaks
-- `judge/pages/pipeline_status.py`, which counts exactly three as three
-- `count(*) FILTER` buckets against `count(*)` as the total.
--
-- NULL WAS NEVER AN OPTION. The column is NOT NULL, and making it nullable would
-- defeat its purpose: it exists so a NULL `harvest_run_id` cannot mean two
-- things, and a nullable provenance column reintroduces that ambiguity.
--
-- THIS RESTS ON #160's ACCOUNT, NOT ON A COLUMN
--
-- Nothing records which writer produced a row. That is the gap this column
-- cannot retroactively close, and the correction cannot invent it. What supports
-- the WHERE clause is the shape: 57 roots and 796 comments, all fetched
-- 2026-08-27, all `no_run_for_source`. A listing sweep over 12 subreddits at 7
-- pages would have produced ~2,100 roots, not 57 — the row count matches a query
-- arm and not a listing.
--
-- If the account is wrong this moves 853 rows from one incorrect value to
-- another and loses nothing, because neither carries a run id.
--
-- IDEMPOTENT. The WHERE clause matches only rows still carrying the wrong value,
-- so a re-run updates nothing. Deliberate: `migrate()` applies each file once,
-- and a data migration that cannot be re-run safely is one nobody dares replay
-- from the raw store.

UPDATE document
   SET retrieval_provenance = 'not_recorded'
 WHERE source = 'reddit'
   AND retrieval_provenance = 'no_run_for_source'
   AND fetched_at >= timestamptz '2026-08-27 00:00:00+00'
   AND fetched_at <  timestamptz '2026-08-28 00:00:00+00';
