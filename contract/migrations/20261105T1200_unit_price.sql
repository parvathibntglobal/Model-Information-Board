-- A price in its own unit, for models not priced per token (2026-11-05, #602
-- items 3 and 4). contract/litellm_prices.yaml says where the rows come from.
--
-- WHY A TABLE AND NOT A COLUMN. `model_version.price_in` / `price_out` and
-- `model_catalog.price_in` / `price_out` are USD PER 1M TOKENS, and every sort,
-- "cheapest" and the advisor read them as that. A video model is priced per
-- second of output, an image input per image. Putting either number in those
-- columns would make it comparable with a token price, which it is not. Here
-- each row names its unit, and nothing that compares token prices reads this
-- table, so a comparison across units cannot happen by accident.
--
-- APPEND-ONLY. Each load adds a snapshot stamped `retrieved_at`; the reader
-- takes the newest snapshot per model and source, and the older ones are the
-- history. Nothing is updated or deleted.
--
-- WHO WRITES: scripts/load_litellm_prices.py (by hand; no schedule).
-- WHO READS: judge/catalog.py, for the Models pages.
--
--   canonical_id  the model, as `model_catalog` lists it
--   unit          second_of_video | image
--   direction     input | output
--   variant       the source's own tier name (720p, 1080p, 4k ...) or
--                 `default`, the source's base figure. LiteLLM does not say
--                 which resolution its base figure is, so neither do we
--   usd           US dollars per one unit
--   source        litellm
--   source_key    the source's own id for the entry, host-prefixed
--                 (`volcengine/doubao-seedance-2-0-260128`) - the host is the
--                 part of the price a reader most needs
--   source_url    the file the figure was read from
--   retrieved_at  when it was read. The page shows it, so a stale price shows

CREATE TABLE unit_price (
  canonical_id  text NOT NULL,
  unit          text NOT NULL,
  direction     text NOT NULL,
  variant       text NOT NULL DEFAULT 'default',
  usd           numeric(14,8) NOT NULL,
  source        text NOT NULL,
  source_key    text NOT NULL,
  source_url    text NOT NULL,
  retrieved_at  timestamptz NOT NULL,
  PRIMARY KEY (canonical_id, unit, direction, variant, source, retrieved_at),
  CONSTRAINT unit_price_unit_ck CHECK (unit IN ('second_of_video', 'image')),
  CONSTRAINT unit_price_direction_ck CHECK (direction IN ('input', 'output')),
  CONSTRAINT unit_price_source_ck CHECK (source IN ('litellm')),
  CONSTRAINT unit_price_usd_ck CHECK (usd >= 0)
);

CREATE INDEX unit_price_latest_idx ON unit_price (canonical_id, source, retrieved_at DESC);
