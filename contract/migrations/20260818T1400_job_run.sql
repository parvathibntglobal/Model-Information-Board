-- Adds `job_run`, the nightly chain's run ledger.
--
-- THE FIRST MIGRATION IN THIS DIRECTORY. Until it, `discover()` returned an
-- empty tuple and `tests/test_migrations.py` compared `tables.sql` against
-- `baseline.sql` alone - a chain of length zero, which is two copies of the
-- same DDL agreeing. The equivalence test has never executed a migration
-- statement before this file.
--
-- The full reasoning for every column lives in `contract/tables.sql`. This
-- file is the delta and deliberately carries no second copy of it: two
-- descriptions of one design drift, which is the defect the equivalence test
-- exists to catch.

CREATE TABLE job_run (
  id            text PRIMARY KEY,
  stage         text NOT NULL,
  started_at    timestamptz NOT NULL DEFAULT now(),

  -- ⚠ NULL MEANS DID NOT FINISH. IT DOES NOT MEAN FAILED.
  --
  -- A killed process cannot write its own failure, so the absence has to carry
  -- that meaning: "started 03:00, never finished" is a fact, and a row written
  -- only on success leaves nothing at all, which reads as a night with no work.
  --
  -- Same treatment as `harvest_run.truncated_by` and for the same reason:
  -- ANYTHING READING THIS MUST NOT COLLAPSE THE TWO. `finished_at IS NULL` with
  -- `outcome IS NULL` is still-running-or-killed; `outcome = 'failed'` is a
  -- stage that ran and reported failure. A dashboard showing both as red loses
  -- the distinction between a crash and a refusal, which are opposite repairs.
  finished_at   timestamptz,

  -- NULL while running. Closed set, because a check over arbitrary strings is
  -- not a check.
  --   ok       the stage did its work
  --   refused  the stage declined deliberately — a gate, a missing input, a
  --            precondition. NOT an error, and it must not render as one.
  --   failed   the stage tried and could not
  outcome       text,

  -- NULL WHERE UNKNOWN, NEVER 0 (rule 6). A stage that refused counted nothing;
  -- 0 would assert it counted and found none, which is the distinction this
  -- project has now had to make four times.
  items_in      int,
  items_out     int,

  -- The refusal text, or the stage's own report. Free-form on purpose: the
  -- closed set above is what gets queried, this is what gets read.
  detail        jsonb,

  pipeline_version text NOT NULL,

  CONSTRAINT job_run_outcome_ck
    CHECK (outcome IS NULL OR outcome IN ('ok', 'refused', 'failed')),

  -- An outcome without a finish is a row that claims to have concluded and did
  -- not record when. The reverse is legitimate and common: finished_at set with
  -- outcome NULL cannot happen either, so both directions are refused.
  CONSTRAINT job_run_finish_ck
    CHECK ((finished_at IS NULL) = (outcome IS NULL))
);

-- The two questions asked of this table: "when did stage X last run" and
-- "what is still running".
CREATE INDEX job_run_stage_idx ON job_run (stage, started_at DESC);
CREATE INDEX job_run_unfinished_idx ON job_run (started_at) WHERE finished_at IS NULL;
