-- The extraction ledger. Proposed by E2, approved by E1, 2026-08-18.
--
-- Records that a thread was READ, separately from what it said. Full reasoning
-- per column is in contract/tables.sql; this is the delta.
--
-- The fourth migration, and the first written from judge/. 20260818T1400
-- created a table, 20260818T1520 altered a constraint, 20260818T1610 added
-- columns including a generated one.

CREATE TABLE thread_extraction (
  thread_context_id text NOT NULL REFERENCES thread_context(id),
  pipeline_version  text NOT NULL,
  extracted_at      timestamptz NOT NULL DEFAULT now(),

  -- 0 is a RESULT ("read it, found nothing"), the absence of a row is a JOB
  -- ("nobody has read this"). Collapsing the two is what makes a nightly batch
  -- re-pay for exactly the threads that cost most and return least.
  claims_written    int NOT NULL,

  input_tokens      int,
  output_tokens     int,
  schema_retries    int NOT NULL DEFAULT 0,

  PRIMARY KEY (thread_context_id, pipeline_version)
);

CREATE INDEX thread_extraction_version_idx
  ON thread_extraction (pipeline_version);
