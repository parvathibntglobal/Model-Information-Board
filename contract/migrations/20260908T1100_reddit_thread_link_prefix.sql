-- Reddit's 2,840 dangling thread links get the `reddit:` prefix their targets carry.
--
-- ⚠ NEEDS E2's SIGN-OFF, per the lane rule on contract/. No schema change: two
--   UPDATEs over one source's rows, no constraint touched, no column added.
--
-- WHAT IS WRONG WITH THEM
--
-- `document.id` for a Reddit row is `reddit:<fullname>` — `collect/adapters/
-- reddit.py:reddit_document_id`, which exists precisely so the convention lives
-- in one named place. `reddit_write.document_row` applied it to `id` and NOT to
-- `thread_root_id` or `parent_id`, which were written as the bare fullname:
--
--     document.id              'reddit:t3_1v6a104'
--     document.thread_root_id  't3_1v6a104'          <- names no row
--     document.parent_id       't1_ozoym09'          <- names no row
--
-- Measured on staging 2026-09-08, before this migration:
--
--     reddit rows                                     2999
--       posts (parent_id IS NULL)                     1579
--       comments with thread_root_id set              1420   ALL BARE
--       comments with parent_id set                   1420   ALL BARE
--     references that resolve to a stored row            0
--     references that resolve once prefixed           2840   ALL OF THEM
--     distinct bare thread_root_id values               24
--
-- So it is not a partial break or a sampling problem. **Every linkage this
-- writer has ever produced points at nothing, and prefixing every one of them
-- resolves with zero left over.** The rows are all there; the references are not.
--
-- WHY IT SAT UNNOTICED, WHICH IS THE PART WORTH RECORDING
--
-- `thread_root_id` carries NO FOREIGN KEY, deliberately. `hackernews.drafts`
-- states the reason: a comment must be storable before its story is fetched, so
-- a dangling root is a COVERAGE fact rather than a lost document. That decision
-- is right, and it is also exactly what let a systematic break survive — a
-- constraint would have rejected the first row ever written.
--
-- Nothing joined on these columns until `collect/triage/run.py` did, on
-- 2026-09-08, to give the subject gate a thread root. It found all 1,420 on the
-- first run. A column with no reader and no constraint is a column whose
-- contents nobody has checked, and this is the second time that shape has cost
-- this project real data: `document.lang` was NULL on 6,502 rows for the same
-- reason, and the specificity components on 3,054.
--
-- WHY A PREFIX AND NOT STRIPPING THE OTHER SIDE
--
-- The alternative — drop `reddit:` from `document.id` — was rejected and it is
-- not close. `document.id` is referenced by `claim.document_id`,
-- `thread_context`, the raw-store audit and `judge/`'s reads; `thread_root_id`
-- and `parent_id` are referenced by nothing, because nothing could join on them.
-- One direction rewrites two unreferenced columns on one source's rows; the
-- other rewrites a primary key that four readers depend on, to make a broken
-- column right. **Move the side nobody is holding.**
--
-- The other alternative — teach the join to add the prefix — was rejected for
-- the reason this project has recorded under "two names for one thing": a reader
-- that compensates for a writer leaves the next reader to discover the same
-- thing, and there is now more than one reader.
--
-- IDEMPOTENT, AND THE WHERE CLAUSE IS THE WHOLE GUARD
--
-- `NOT LIKE 'reddit:%'` means a second run matches nothing. That is not
-- tidiness: a repair that double-prefixes turns 1,420 dangling references into
-- 1,420 `reddit:reddit:t3_…` references, and the second state is harder to
-- recognise than the first because it no longer looks like a convention
-- mismatch. 0 rows carry the prefix today, so this run is the whole population.
--
-- SCOPED TO `source = 'reddit'` AND THAT IS NOT DEFENSIVE. GitHub's linkage is
-- internally consistent and MUST NOT BE TOUCHED: its ids come from
-- `stable_id("doc", ...)` and carry no `<source>:` prefix at all, so 2,016 of
-- 2,016 GitHub children already resolve. A migration written against "any
-- unprefixed thread_root_id" would break the one platform that works.
--
-- THE FORWARD PATH IS FIXED IN THE SAME CHANGE.
-- `collect/adapters/reddit_write.py:_document_ref` now routes both columns
-- through `reddit_document_id`. Without that, the next sweep re-breaks what
-- this repairs — which is how a backfill ends up being run three times with
-- nobody able to say why it keeps being needed.
--
-- ⚠  NO `BEGIN`/`COMMIT` IN THIS FILE, AND THE FIRST DRAFT HAD BOTH.
--    `collect/migrate.py:migrate` wraps each file in `conn.transaction()` and
--    inserts the ledger row inside that same transaction, deliberately, "so a
--    failure leaves neither the change nor the claim that it was made".
--    `collect.db.connect` leaves autocommit OFF, so a transaction is already
--    open and `conn.transaction()` opens a SAVEPOINT — and a `COMMIT` inside
--    the file commits the OUTER transaction, then the savepoint release fails
--    with `InvalidSavepointSpecification`.
--
--    THAT IS NOT A COSMETIC DIFFERENCE. Run against staging with the BEGIN/
--    COMMIT in place, this file COMMITTED ALL 2,840 UPDATES AND THEN FAILED
--    BEFORE THE LEDGER ROW - the exact half-state the runner's one-transaction
--    design exists to prevent: the change made, and no record that it was.
--
--    AND THE RECOVERY TOOK TWO ATTEMPTS, WHICH IS WORTH RECORDING BECAUSE THE
--    FIRST ONE LOOKED LIKE IT WORKED. Removing the statements and calling
--    `migrate(conn)` from a script reported both files applied and stored
--    NEITHER: `migrate()` does not commit - `collect/cli.py:db migrate` calls
--    `conn.commit()` after it, deliberately, so the caller owns the
--    transaction - and a script that closed the connection instead rolled the
--    whole thing back. The ledger row was READ BACK SUCCESSFULLY inside that
--    same connection before it vanished, which is why the first check passed.
--
--    So: apply migrations with `python -m collect.cli db migrate`, which is the
--    sanctioned path and the one that gates and commits. Verify in a FRESH
--    connection, never in the one that did the work.
--
--    `collect/triage/store.py:_flush` records the same savepoint trap from the
--    other direction — a writer that reported rows written and stored none.
--    Same cause, opposite symptom, and this is the second time it has been
--    paid for. Eleven of the eleven migrations before this one carry no
--    transaction control; that was the convention and it is not decoration.

-- The root link. 1,420 rows expected.
UPDATE document
   SET thread_root_id = 'reddit:' || thread_root_id
 WHERE source = 'reddit'
   AND thread_root_id IS NOT NULL
   AND thread_root_id NOT LIKE 'reddit:%';

-- The parent link. 1,420 rows expected. Separate statement rather than one
-- UPDATE with two SET clauses, because the two columns are independently
-- nullable: a comment always has both, but a row with one and not the other is
-- a state the schema permits, and a combined WHERE would have to pick which
-- column's nullability governed the row.
UPDATE document
   SET parent_id = 'reddit:' || parent_id
 WHERE source = 'reddit'
   AND parent_id IS NOT NULL
   AND parent_id NOT LIKE 'reddit:%';

-- ── THE ASSERTION, INSIDE THE TRANSACTION ────────────────────────────────
--
-- Every reddit link must now name a stored row. This is the check the missing
-- foreign key would have been, run once at the moment it can be: if any
-- reference still dangles, the prefix was not the whole story and the repair
-- should not commit on the strength of a count that looked right.
--
-- It rolls back rather than warning, because a half-repaired linkage is the
-- state this migration exists to end.
DO $$
DECLARE
  dangling_roots   integer;
  dangling_parents integer;
BEGIN
  SELECT count(*) INTO dangling_roots
    FROM document d LEFT JOIN document r ON r.id = d.thread_root_id
   WHERE d.source = 'reddit' AND d.thread_root_id IS NOT NULL AND r.id IS NULL;

  SELECT count(*) INTO dangling_parents
    FROM document d LEFT JOIN document p ON p.id = d.parent_id
   WHERE d.source = 'reddit' AND d.parent_id IS NOT NULL AND p.id IS NULL;

  IF dangling_roots > 0 OR dangling_parents > 0 THEN
    RAISE EXCEPTION
      'reddit thread links still dangle after the prefix repair: % root(s), % parent(s). '
      'The prefix was not the whole defect - do not commit on a count that looked right.',
      dangling_roots, dangling_parents;
  END IF;
END $$;
