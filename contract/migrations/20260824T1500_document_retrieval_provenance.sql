-- document.harvest_run_id + document.retrieval_provenance — what retrieved this.
--
-- ⚠ ADDED BY E1 2026-08-24 AND NEEDS E2's SIGN-OFF, per the lane rule on
--   contract/. Two columns and one foreign key on `document`. No existing row
--   changes meaning: all 343 land on `not_recorded`, which is what they are.
--
-- WHY NOW RATHER THAN AFTER THE SWEEP.
--
-- Backfill is already impossible for the corpus we hold. 343 documents are
-- stored and nothing records what retrieved them; `harvest_run` holds 153 rows
-- but a document returned by six queries cannot be attributed to one of them
-- after the fact. A GitHub sweep was about to run and would have produced a
-- SECOND corpus with the same hole, which is the argument for landing this
-- first: the cost is thirty minutes of sweep, and the alternative is
-- permanently unattributable provenance for everything retrieved twice.
--
-- WHAT THE COLUMN HOLDS FOR EACH ADAPTER, stated rather than left to a default.
--
--   github   `run_recorded`, with the harvest_run id. This is the only adapter
--            that renders a query per alias per capability entry, and the only
--            source in `harvest_run` — all 153 rows are source_id='github'.
--            `collect/ops/sweep.py` already opens the run BEFORE the fetch, so
--            the id is in scope at the write. One call site.
--
--   reddit   `no_run_for_source`. A subreddit listing is not a rendered query
--            and writes no harvest_run row. NULL here is complete, not missing.
--
--   blog     `no_run_for_source`. A feed fetch renders no query either.
--            NOT permanent: collect/adapters/blog/validators.py already names
--            `feed_url` as the natural `watermark.query_key`, so a feed fetch
--            could become a harvest_run row later and move these rows to
--            `run_recorded`. The discriminator is what makes that a visible
--            migration rather than a silent reinterpretation of old NULLs.
--
-- SO THE ANSWER TO "does the write cover all three adapters" IS: the column
-- covers all three and only ONE of them can carry an id. The other two carry a
-- statement about why they cannot, which is the part that needed a column.
--
-- WHY `not_recorded` IS THE DEFAULT AND NOT `no_run_for_source`.
--
-- The default is what an uninstrumented writer produces, so it must be the
-- claim that asserts least. `no_run_for_source` is a statement ABOUT A SOURCE
-- and somebody should have to type it; `not_recorded` says only "nobody wrote
-- this down", which is true of any writer that has not been updated. A default
-- of `no_run_for_source` would let a github writer that forgot to pass the id
-- render as "github has no runs", which is false and unfalsifiable from the row.
--
-- Rule 6, and the fourth time: a NULL that means "no run exists" and a NULL
-- that means "nobody recorded one" have opposite repairs, and a page that shows
-- both as blank reports a considered answer where there is none.

ALTER TABLE document
  ADD COLUMN IF NOT EXISTS harvest_run_id text;

ALTER TABLE document
  ADD COLUMN IF NOT EXISTS retrieval_provenance text NOT NULL DEFAULT 'not_recorded';

-- The vocabulary. Three states, mutually exclusive, none of them a synonym for
-- another.
ALTER TABLE document
  DROP CONSTRAINT IF EXISTS document_retrieval_provenance_ck;
ALTER TABLE document
  ADD CONSTRAINT document_retrieval_provenance_ck
  CHECK (retrieval_provenance IN ('run_recorded', 'no_run_for_source', 'not_recorded'));

-- The two columns cannot disagree. `run_recorded` with no id is a provenance
-- claim with nothing behind it; an id under any other state is provenance the
-- page refuses to show. Either is worse than both being absent.
ALTER TABLE document
  DROP CONSTRAINT IF EXISTS document_retrieval_provenance_agrees_ck;
ALTER TABLE document
  ADD CONSTRAINT document_retrieval_provenance_agrees_ck
  CHECK ((retrieval_provenance = 'run_recorded') = (harvest_run_id IS NOT NULL));

-- NO ON DELETE CASCADE and no SET NULL. A document outlives the query that
-- found it, and SET NULL would move a row into a state its own CHECK forbids.
-- So a harvest_run with documents cannot be deleted, which is correct for an
-- append-only ledger.
ALTER TABLE document
  DROP CONSTRAINT IF EXISTS document_harvest_run_fk;
ALTER TABLE document
  ADD CONSTRAINT document_harvest_run_fk
  FOREIGN KEY (harvest_run_id) REFERENCES harvest_run(id);

CREATE INDEX IF NOT EXISTS document_harvest_run_idx ON document (harvest_run_id);
