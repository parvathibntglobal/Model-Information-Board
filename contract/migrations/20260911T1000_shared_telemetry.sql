-- Telemetry stops being per-machine: spend, fetch logs and quota move to the shared database.
--
-- WHAT WAS WRONG. Three pieces of state lived only on the machine that produced
-- them, so no figure on the usage panel was ever a team figure:
--
--   var/spend-ledger.jsonl    every paid model call — each person saw their own
--                             spend and nobody saw the total
--   var/fetch/<run>.jsonl     the per-stage fetch log — a run was only visible
--                             on the machine whose button was clicked
--   var/rapidapi-quota.json   the metered-API reading — one machine's view of a
--                             counter the whole team draws down
--
-- `judge/spend_ledger.py` said so itself: "The durable home for this is
-- Postgres. contract/ is shared, so a table is Engineer 1's to agree to — hence
-- a judge/-owned append-only file, and the table proposed rather than assumed."
-- This is that table, now agreed.
--
-- THE FILES DO NOT GO AWAY, and that is the point rather than a compromise.
-- Every writer writes the FILE FIRST and the database best-effort. The fetch
-- log exists in files precisely so a run that dies BECAUSE THE DATABASE IS
-- UNREACHABLE can still say what happened — which is exactly what let us read
-- the 2026-09-10 log while AWS was down. A telemetry table that can take the
-- run down with it is worse than no table.
--
-- IDS ARE CONTENT-DERIVED, so every merge is an append and a backfill is
-- idempotent. The ledger had NO primary key at all: fields were only
-- {at, stage, model, in, out, usd, unpriced}, and two machines can legitimately
-- emit byte-identical rows. Without an id, re-running a backfill INFLATES THE
-- SPEND TOTAL — the one direction a money figure must never drift.
--
-- MACHINE, NOT PERSON. `machine` records which host ran it, because this app
-- has exactly one account: everyone signs in as the same AUTH_EMAIL. A column
-- called `clicked_by` would be a definite answer to a question nobody can
-- currently answer (rule 6), so it is not called that.

-- ── every paid model call, from any machine ──────────────────────────────
CREATE TABLE IF NOT EXISTS spend_ledger (
  -- sha256 of machine|run|at|stage|model|tokens. Deterministic, so the same
  -- call recorded twice is one row and a re-run of the backfill is a no-op.
  id             text PRIMARY KEY,

  at             timestamptz NOT NULL,
  stage          text NOT NULL,
  model          text NOT NULL,
  input_tokens   integer NOT NULL,
  output_tokens  integer NOT NULL,

  -- numeric, not float: this is money and it gets summed. A double accumulates
  -- error across thousands of rows in the direction nobody audits.
  usd            numeric(16, 10) NOT NULL,

  -- The model has no published rate, so `usd` is 0.0 and the TOKENS are the
  -- only real figure on the row. A total containing one of these is a floor.
  unpriced       boolean NOT NULL DEFAULT false,

  machine        text NOT NULL,
  run_id         text,
  recorded_at    timestamptz NOT NULL DEFAULT now(),

  -- The same closed set rule 2 permits to call a model. A third value here is
  -- a rule-2 violation and should be refused by the database rather than
  -- appear as a new line on a chart nobody questions.
  CONSTRAINT spend_ledger_stage_ck CHECK (stage IN ('extract', 'ask'))
);

-- The two questions asked of this table: "what has today cost" (the shared cap)
-- and "what has this run cost".
CREATE INDEX IF NOT EXISTS spend_ledger_at_idx ON spend_ledger (at DESC);
CREATE INDEX IF NOT EXISTS spend_ledger_run_idx ON spend_ledger (run_id) WHERE run_id IS NOT NULL;

COMMENT ON COLUMN spend_ledger.machine IS
  'Hostname that recorded the call. NOT the person: this app has a single '
  'account, so who clicked is genuinely unknown and is not guessed here.';


-- ── the per-stage fetch log, one row per line ────────────────────────────
CREATE TABLE IF NOT EXISTS fetch_log (
  -- sha256 of run_id|seq|payload, for the same idempotence reason.
  id           text PRIMARY KEY,

  run_id       text NOT NULL,

  -- Position within the run. The log is a SEQUENCE — "E3 started" before "E3
  -- failed" is the whole meaning — and timestamps are second-resolution, so
  -- several lines share one. Ordering by `at` alone scrambles a run.
  seq          integer NOT NULL,

  at           timestamptz,
  machine      text NOT NULL,

  -- The line verbatim. Deliberately not columns-per-field: the writer adds
  -- stage-specific counts freely, and a schema that had to grow a column for
  -- each would be a schema people route around. The queryable bits are lifted
  -- out below.
  payload      jsonb NOT NULL,

  -- Lifted from the payload so a run can be listed without reading every line.
  kind         text,
  model_version_id text,

  recorded_at  timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT fetch_log_run_seq_uq UNIQUE (run_id, seq)
);

CREATE INDEX IF NOT EXISTS fetch_log_run_idx ON fetch_log (run_id, seq);
CREATE INDEX IF NOT EXISTS fetch_log_recent_idx ON fetch_log (recorded_at DESC);

COMMENT ON TABLE fetch_log IS
  'A mirror of var/fetch/<run_id>.jsonl, written best-effort AFTER the file. '
  'The file is the survivor: a run that fails because the database is '
  'unreachable must still be able to report that it did.';


-- ── the metered-API quota, newest READING wins ───────────────────────────
CREATE TABLE IF NOT EXISTS rapidapi_quota (
  -- One row per METER, not per key and not per machine. Measured 2026-09-10:
  -- Reddit and X are separate accounts with separate limits (1,000,000 and
  -- 100,000), so a single row would show one meter's figure under the other's
  -- heading.
  meter           text PRIMARY KEY,

  quota_remaining bigint,
  quota_limit     bigint,

  -- WHEN THE READING WAS TAKEN, which is not when the row was written. Two
  -- machines racing on a decreasing counter can have the later WRITE carry the
  -- older READING; the upsert below compares this, so newest-reading wins.
  read_at         timestamptz NOT NULL,

  read_by         text NOT NULL,
  source_run_id   text,
  machine         text NOT NULL,
  recorded_at     timestamptz NOT NULL DEFAULT now(),

  -- A reading with neither figure is not a reading. Refused here as well as in
  -- collect/usage.py, because "no header" must never become "a quota of zero".
  CONSTRAINT rapidapi_quota_has_a_figure_ck
    CHECK (quota_remaining IS NOT NULL OR quota_limit IS NOT NULL)
);

COMMENT ON COLUMN rapidapi_quota.quota_limit IS
  'The denominator AS THIS READING STATED IT, or NULL when the response '
  'carried none. NEVER inherited from a previous reading: the arms are '
  'separately metered, so an inherited limit may belong to another meter.';
