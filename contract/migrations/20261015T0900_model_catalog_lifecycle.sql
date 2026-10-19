-- When a catalogue model stops being served, and what it knows up to. 2026-10-15.
--
-- WHY. A model's page shows its lifecycle, retirement first. OpenRouter's feed
-- publishes `expiration_date` (20 of 667 entries on 2026-10-14) and
-- `knowledge_cutoff` (172 of 667); the catalogue poller read neither. Added as
-- a migration of its own rather than an edit of 20261014T1300, because that
-- file is on a pushed branch and may already be applied elsewhere.
--
-- WHAT A VALUE MEANS
--   expiration_date   the date OpenRouter says it stops serving the model;
--                     NULL means none announced - never "it will not retire"
--   knowledge_cutoff  the date the feed gives for the model's training data;
--                     NULL means not stated (rule 6)
--
-- WHO WRITES: collect/registry/catalog.py:write_catalog. WHO READS:
-- judge/catalog.py:catalog_model, for the Lifecycle part of a model's page.

ALTER TABLE model_catalog ADD COLUMN expiration_date date;
ALTER TABLE model_catalog ADD COLUMN knowledge_cutoff date;
