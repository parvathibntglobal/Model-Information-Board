-- OpenRouter's whole model list, every output type, for the Models pages.
-- 2026-10-14.
--
-- WHY A TABLE OF ITS OWN. `model_version` is the registry the evidence pipeline
-- reads - what is `in_window` is what the nightly chain plans searches for -
-- and the poller fills it from the feed's default, text-only listing (462 of
-- 667 models on 2026-10-14). The Models pages also list image, video, speech,
-- audio, transcription and decision models; putting those into `model_version`
-- would make them evidence targets by accident. Nothing in the evidence
-- pipeline reads this table. See collect/registry/catalog.py.
--
-- WHO WRITES: collect/registry/catalog.py:write_catalog, from
-- `python -m collect.cli registry poll-catalog` and the chain's `poll-catalog`
-- stage. WHO READS: judge/catalog.py:catalog_view, for GET /model-catalog.
--
-- WHAT THE COLUMNS MEAN
--   canonical_id       OpenRouter's id as listed (`elevenlabs/eleven-v3`); a
--                      leading `~` is its "latest" alias and is kept as listed
--   provider           the id's vendor segment, `~` stripped
--   listed_at          OpenRouter's `created`: when it LISTED the model, which
--                      is not a vendor's release date
--   output_modalities  OpenRouter's own types: text, image, video, speech,
--                      audio, transcription, decisions, embeddings, rerank
--   price_in/out       USD per 1M tokens where the feed prices per token;
--                      NULL means "not priced per token", never free (rule 6)
--   pricing            the feed's pricing object as published (per image, per
--                      second, per character ...)
--   last_seen_at       the latest poll that listed it; a model that leaves the
--                      feed keeps its row with an older stamp

CREATE TABLE model_catalog (
  canonical_id       text PRIMARY KEY,
  provider           text NOT NULL,
  name               text NOT NULL,
  description        text,
  listed_at          timestamptz,
  input_modalities   text[] NOT NULL,
  output_modalities  text[] NOT NULL,
  context_length     int,
  price_in           numeric(12,6),
  price_out          numeric(12,6),
  pricing            jsonb NOT NULL,
  first_seen_at      timestamptz NOT NULL DEFAULT now(),
  last_seen_at       timestamptz NOT NULL
);

CREATE INDEX model_catalog_seen_idx ON model_catalog (last_seen_at);
