-- document.retrieval_provenance gains a fourth value: 'unreviewed_writer'.
--
-- ⚠ ADDED BY E1 2026-08-28 AND NEEDS E2's SIGN-OFF, per the lane rule on
--   contract/. Proposed first in
--   docs/proposals/for-engineer-2-a-fourth-retrieval-provenance-value.md
--   (PR #159); this is that proposal landing.
--
-- THE STATE THAT HAD NO VALUE
--
-- A document written by code that is not on `main`, by a run that opened no
-- `harvest_run` row. Three values existed and each already meant something
-- else:
--
--   run_recorded        a run exists and its id is on the row
--   no_run_for_source   this source renders no query, so a NULL harvest_run_id
--                       is COMPLETE rather than missing
--   not_recorded        A RUN EXISTED AND NO ID WAS PASSED - a plumbing gap
--
-- Filing an unreviewed writer's rows under `not_recorded` makes them
-- indistinguishable from the 28 GitHub rows whose run was simply never
-- recorded. That is rule 6: a missing value becoming a definite one, with
-- nothing on the page to disagree with. It is rule 7's half too, because any
-- denominator drawn over `document` then silently contains rows whose
-- population nobody can state.
--
-- WHY THIS IS URGENT RATHER THAN TIDY, AND IT IS NOT ABOUT THE 17
--
-- The per-model fetch will keep producing these rows, and 853 already exist
-- MISLABELLED IN THE OPPOSITE DIRECTION - see the UPDATE below. That is worse
-- than an absent value: `no_run_for_source` is a positive claim that nothing is
-- missing.
--
-- `document_retrieval_provenance_agrees_ck` NEEDS NO CHANGE. It reads
-- (retrieval_provenance = 'run_recorded') = (harvest_run_id IS NOT NULL), and a
-- fourth value on a row with a NULL id satisfies it exactly as written. Stated
-- because a second constraint on the same column is what a migration like this
-- usually breaks.
--
-- ON THE NAME. `unreviewed_writer` states the fact - the code path that wrote
-- the row is not on `main` - rather than a judgement about the data. It stays
-- true whether the branch is later merged or deleted, and it does not imply the
-- documents are wrong. `orphan`, `untrusted` and `bad_provenance` were
-- considered and rejected for asserting more than is known: the rows may be
-- perfectly good documents.

ALTER TABLE document DROP CONSTRAINT document_retrieval_provenance_ck;

ALTER TABLE document ADD CONSTRAINT document_retrieval_provenance_ck
  CHECK (retrieval_provenance IN
         ('run_recorded', 'no_run_for_source', 'not_recorded', 'unreviewed_writer'));


-- THE 853 ROWS THAT ARE MISLABELLED, AND WHY THIS IS A CORRECTION NOT A GUESS
--
-- Every reddit document fetched 2026-08-27 carries `no_run_for_source`, because
-- `collect/adapters/reddit_write.py` TYPED THAT STRING INTO ITS INSERT - the
-- same statement, for every caller, whatever the caller did. The comment there
-- justified it for a SUBREDDIT LISTING, which renders no query and so is
-- genuinely complete.
--
-- These rows did not come from a listing. E2 confirmed 2026-08-28 (#160) that
-- the per-model fetch's Reddit arm inserted them, and that arm issues
-- MODEL-NAME QUERIES. So a query was rendered, no run was opened, and the
-- column asserts the opposite: "there was nothing to record" where the truth is
-- "something was not recorded".
--
-- The shape of the evidence, which is why the WHERE clause is this narrow:
--   57 roots + 796 comments, all fetched_at 2026-08-27, all no_run_for_source.
--   A listing sweep over 12 subreddits x 7 pages would have produced ~2,100
--   roots, not 57. The row count matches a query arm and not a listing.
--
-- THIS UPDATE RESTS ON E2's ACCOUNT, NOT ON A COLUMN. There is no field that
-- records which writer produced a row - that is the whole gap this value exists
-- to close, and it cannot retroactively close itself. If the account is wrong,
-- this reclassifies 853 rows from one wrong value to another; it does not make
-- anything less recoverable, because neither value carries a run id.
UPDATE document
   SET retrieval_provenance = 'unreviewed_writer'
 WHERE source = 'reddit'
   AND retrieval_provenance = 'no_run_for_source'
   AND fetched_at >= timestamptz '2026-08-27 00:00:00+00'
   AND fetched_at <  timestamptz '2026-08-28 00:00:00+00';
