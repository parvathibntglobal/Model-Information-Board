-- The measured GGUF files behind the local VRAM tool ("Can I run it?").
-- 2026-10-23. docs/proposals/can-i-run-it.md.
--
-- One row per model and quantization: the exact files contract/local_models.yaml
-- lists, their summed size as the Hugging Face Hub API reports it, and the
-- attention fields read from the GGUF file's own header. Nothing in the evidence
-- pipeline reads this table, and no model call writes it.
--
-- WHO WRITES: collect/local_models/poll.py:write_rows, from
-- `python -m collect.cli registry poll-local-models` and the chain's
-- `poll-local-models` stage (weekly, .github/workflows/local-models-poll.yml).
-- WHO READS: judge/local_models.py:local_models_view, for GET /local-models.
--
-- WHAT THE COLUMNS MEAN
--   model_id       the entry's id in contract/local_models.yaml
--   quant          Q4_K_M | Q8_0 (contract/local_inference.yaml `quants`)
--   gguf_repo      the repo the files were measured in
--   files          the files listed for this quant, in order; split files part by part
--   bytes          their summed size. NULL when any listed file is missing from
--                  the repo - never a partial sum (rule 6)
--   missing_files  the listed files the repo did not have; empty when none
--   header         the GGUF header's kept fields (collect/local_models/gguf.py),
--                  architecture prefix removed. NULL when the header was not read
--   header_note    why the header is unread; NULL when it was read
--   repo_sha       the repo commit the sizes were read at; the header is read
--                  from the same commit
--   raw_ref        raw store ref of the Hub API response the sizes came from
--   measured_at    when this row was measured
--   pipeline_version  the code that measured it

CREATE TABLE local_model_file (
  model_id          text NOT NULL,
  quant             text NOT NULL,
  gguf_repo         text NOT NULL,
  files             text[] NOT NULL,
  bytes             bigint,
  missing_files     text[] NOT NULL DEFAULT '{}',
  header            jsonb,
  header_note       text,
  repo_sha          text,
  raw_ref           text,
  measured_at       timestamptz NOT NULL,
  pipeline_version  text NOT NULL,
  PRIMARY KEY (model_id, quant),
  CONSTRAINT local_model_file_bytes_ck CHECK (bytes IS NULL OR bytes > 0),
  CONSTRAINT local_model_file_size_or_missing_ck
    CHECK ((bytes IS NULL) = (cardinality(missing_files) > 0)),
  CONSTRAINT local_model_file_header_or_note_ck CHECK ((header IS NULL) = (header_note IS NOT NULL))
);
