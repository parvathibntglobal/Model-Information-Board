-- THE BENCHMARKS PAGE'S TABLES (2026-10-22). BENCHMARK_PIPELINE_WORKFLOW.md section 14.
--
-- A signed-in page of published benchmark results for the tracked text models,
-- scraped from public leaderboard pages and the data files their sites offer
-- (collect/benchmarks/). No key, no paid service, no language model.
--
-- SEPARATE FROM THE BOARD. Every table is prefixed `bench_`, nothing here is
-- evidence, and nothing reads these tables into `claim`, `cell`, `board_entry`
-- or any count. The seed models are NOT stored here: a row points at the
-- registry id in contract/tracked_models.yaml.
--
-- RAW VALUES ONLY (Parvathi, 2026-10-22). The page shows `raw_text`: the value
-- exactly as the source printed it ("88.0", "0.9577", "#3"), with its source,
-- link and date. `value` holds the same figure in one unit (percent, rating,
-- rank) and is used only by the checks - range, cross-source agreement, change
-- over time - which cannot compare 0.95 with 95. It is never displayed. No
-- derived rank or percentile is stored.
--
-- Phase 1. Overrides, suppressions, the audit log and per-run cell versions
-- (doc 14) come with the admin edit operations in phase 2.
--
-- No transaction control here: the runner owns the transaction.

-- One execution of the pipeline: its trigger, status, report and log.
CREATE TABLE bench_run (
  id            bigserial PRIMARY KEY,
  -- Set by the page's Run button so it can find the run it started.
  request_id    text,
  trigger       text NOT NULL,
  scope         text NOT NULL,
  dry_run       boolean NOT NULL DEFAULT false,
  status        text NOT NULL DEFAULT 'running',
  started_at    timestamptz NOT NULL DEFAULT now(),
  finished_at   timestamptz,
  -- Per-source results, totals and alerts (doc 14 "per-source run report", 20.5).
  report        jsonb,
  -- The run's whole terminal output at verbose level (doc 23.1 rule 7), so a
  -- run can be read on the page after the log file is gone.
  log_text      text,
  CONSTRAINT bench_run_status_ck CHECK (status IN ('running', 'ok', 'partial', 'error', 'dry_run')),
  CONSTRAINT bench_run_finished_ck CHECK ((status = 'running') = (finished_at IS NULL))
);
CREATE INDEX bench_run_started_idx ON bench_run (started_at DESC);
CREATE INDEX bench_run_request_idx ON bench_run (request_id);

-- One line of the table: a seed model's base row, or a setting row under it
-- ("GPT 6 Astra (max)") created the first time a source publishes that setting.
CREATE TABLE bench_row (
  -- "<registry id>" for the base row, "<registry id>:<setting>" for a setting row.
  row_id             text PRIMARY KEY,
  host_model_id      text NOT NULL,
  setting            text,
  -- A dated release of the model, as the source wrote the date ("(12/25)",
  -- "0813", "2025-12-11"): its own row, never filled from the model's row.
  dated              text,
  display_label      text NOT NULL,
  auto_created       boolean NOT NULL DEFAULT false,
  first_seen_source  text,
  first_seen_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX bench_row_model_idx ON bench_row (host_model_id);

-- The saved copy of each fetched page or file, gzip-compressed, so a source
-- can be re-parsed without fetching it again (doc 4, use_snapshot).
CREATE TABLE bench_snapshot (
  id            bigserial PRIMARY KEY,
  run_id        bigint NOT NULL REFERENCES bench_run (id) ON DELETE CASCADE,
  source_key    text NOT NULL,
  method        text NOT NULL,
  url           text NOT NULL,
  final_url     text,
  http_status   integer,
  content_hash  text NOT NULL,
  size_bytes    integer NOT NULL,
  body_gz       bytea NOT NULL,
  fetched_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX bench_snapshot_source_idx ON bench_snapshot (source_key, fetched_at DESC);

-- One source's value for one cell. Several sources can hold one; merge picks
-- which is published. Kept while the source lists it; `stale` once it stops.
CREATE TABLE bench_observation (
  source_key          text NOT NULL,
  row_id              text NOT NULL REFERENCES bench_row (row_id),
  benchmark_key       text NOT NULL,
  metric              text NOT NULL,
  value               double precision NOT NULL,
  rank_high           integer,
  tied                boolean NOT NULL DEFAULT false,
  rank_out_of         integer,
  rank_board          text,
  -- The test setup ("mini-SWE-agent", "Claude Code"); NULL = none stated.
  variant             text,
  raw_text            text NOT NULL,
  raw_model_name      text NOT NULL,
  url                 text NOT NULL,
  -- The source's own date for the value (a run date, an entry date), as given.
  source_date         text,
  setting_not_stated  boolean NOT NULL DEFAULT false,
  priority            integer NOT NULL,
  run_id              bigint NOT NULL REFERENCES bench_run (id),
  collected_at        timestamptz NOT NULL,
  stale               boolean NOT NULL DEFAULT false,
  PRIMARY KEY (source_key, row_id, benchmark_key, metric),
  CONSTRAINT bench_observation_metric_ck CHECK (metric IN ('score', 'rank', 'rating'))
);

-- The published table: one value per (row, benchmark, metric), with where it came from.
CREATE TABLE bench_cell (
  row_id              text NOT NULL REFERENCES bench_row (row_id),
  benchmark_key       text NOT NULL,
  metric              text NOT NULL,
  value               double precision NOT NULL,
  rank_high           integer,
  tied                boolean NOT NULL DEFAULT false,
  rank_out_of         integer,
  rank_board          text,
  variant             text,
  benchmark_version   text,
  source_key          text NOT NULL,
  url                 text NOT NULL,
  raw_text            text NOT NULL,
  raw_model_name      text NOT NULL,
  source_date         text,
  setting_not_stated  boolean NOT NULL DEFAULT false,
  collected_at        timestamptz NOT NULL,
  needs_review        boolean NOT NULL DEFAULT false,
  run_id              bigint NOT NULL REFERENCES bench_run (id),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (row_id, benchmark_key, metric),
  CONSTRAINT bench_cell_metric_ck CHECK (metric IN ('score', 'rank', 'rating'))
);

-- The changelog: every cell added, changed or removed, by run. Never pruned.
CREATE TABLE bench_change (
  id               bigserial PRIMARY KEY,
  run_id           bigint NOT NULL REFERENCES bench_run (id),
  changed_at       timestamptz NOT NULL DEFAULT now(),
  row_id           text NOT NULL,
  benchmark_key    text,
  metric           text,
  -- added | updated | removed | source_changed | variant_added
  change_type      text NOT NULL,
  old_value        double precision,
  new_value        double precision,
  -- The values as the sources printed them ("88.0", "0.9577", "#3"): what the
  -- page shows. old_value/new_value are the same values in one unit, for the checks.
  old_raw          text,
  new_raw          text,
  old_source       text,
  new_source       text,
  rank_out_of_old  integer,
  rank_out_of_new  integer,
  -- better | worse | same, worked out from the column's direction (ranks: lower is better).
  direction        text,
  reason           text NOT NULL,
  actor            text NOT NULL,
  note             text,
  needs_review     boolean NOT NULL DEFAULT false,
  CONSTRAINT bench_change_type_ck CHECK (change_type IN
    ('added', 'updated', 'removed', 'source_changed', 'variant_added'))
);
CREATE INDEX bench_change_run_idx ON bench_change (run_id);
CREATE INDEX bench_change_at_idx ON bench_change (changed_at DESC);

-- A flagged problem waiting for a person (doc 20.3).
CREATE TABLE bench_review_item (
  id             bigserial PRIMARY KEY,
  run_id         bigint NOT NULL REFERENCES bench_run (id),
  -- The check that raised it: disagreement, large_jump, ambiguous_duplicate, unknown_setting, ...
  check_code     text NOT NULL,
  severity       text NOT NULL DEFAULT 'flag',
  source_key     text,
  row_id         text,
  benchmark_key  text,
  metric         text,
  message        text NOT NULL,
  status         text NOT NULL DEFAULT 'open',
  created_at     timestamptz NOT NULL DEFAULT now(),
  -- resolved: a later run that read the same source no longer raised it
  -- (the name now matches, the duplicate is decided, ...). Set by the run.
  CONSTRAINT bench_review_status_ck CHECK (status IN ('open', 'accepted', 'overridden', 'rejected', 'resolved'))
);
CREATE INDEX bench_review_status_idx ON bench_review_item (status, created_at DESC);

-- Names a source lists that match no tracked model (doc 6, B6). The list
-- a person reads to add an alias. No "closest model" is stored: a similar
-- name is a different model (2026-10-22).
CREATE TABLE bench_unmatched (
  source_key        text NOT NULL,
  raw_name          text NOT NULL,
  -- unmatched | similar_to_registry | unknown_setting | setting_not_allowed
  reason            text NOT NULL,
  -- The name without a setting or date at its end ("GPT-5.2 (xhigh)" -> "GPT-5.2"),
  -- and the same normalised: what a decision in bench_name_decision is keyed on.
  base_name         text,
  base_key          text,
  -- reason similar_to_registry: the registry/tracked models this name is very
  -- close to (same numbers, only filler words differ). Shown for a person to
  -- confirm with Same model as; never matched automatically.
  similar_to        text[],
  seen_count        integer NOT NULL DEFAULT 1,
  first_seen        timestamptz NOT NULL DEFAULT now(),
  last_seen         timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (source_key, raw_name)
);

-- What a person decided about a name in the Unmatched list (Benchmarks page ->
-- Unmatched names). The next run, or a re-parse of the saved pages, applies it:
--   alias    the name is the same model as `target_model_id`, written differently
--   new_row  the name is a model of its own: it gets a row below the tracked ones
--   ignore   leave it out of the Unmatched list
-- Stored here, not in YAML, so a decision needs no code change (2026-10-23).
CREATE TABLE bench_name_decision (
  -- The name normalised the way matching compares names (bench_unmatched.base_key).
  name_key          text PRIMARY KEY,
  name              text NOT NULL,
  action            text NOT NULL,
  target_model_id   text,
  actor             text NOT NULL,
  created_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT bench_name_decision_action_ck CHECK (action IN ('alias', 'new_row', 'ignore')),
  CONSTRAINT bench_name_decision_target_ck CHECK ((action = 'alias') = (target_model_id IS NOT NULL))
);
