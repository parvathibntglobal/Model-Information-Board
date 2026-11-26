-- THE TEXT THAT COMES WITH A POST'S MEDIA (anooj, 2026-11-26; #679 step 1).
--
-- Words the provider already sends beside a post that are not the author's own:
--   alt_text          the description an author gave a picture (Bluesky, X)
--   quoted_post       the text of the post this one quotes (X, Bluesky)
--   crosspost_parent  a Reddit crosspost's original title and body
-- They are matched for AI and industry terms with the post's own words
-- (collect/industry_ai/rules.py judged_text), never shown as the author's words, and
-- cleared by retention with the title and body.
--
--   media_text       NULL = none found or not read; '' = cleared by retention
--   media_text_from  the kinds above, NULL when media_text is NULL
--
-- Rows stored before it stay NULL until their post is seen again by a run
-- (store.upsert_items fills a NULL, never on a row retention cleared).
--
-- WHO RUNS THIS MIGRATION: the person who merges the PR that adds it, on the shared
-- database, straight after merge, with `db check` before and after, and announces it
-- on that PR the same day. Until it has run, the Industry AI run refuses before any
-- request (scripts/run_industry_ai.py, store.missing_columns), so it must run before
-- the next harvest.
--
-- No transaction control here: the runner owns the transaction.

ALTER TABLE iai_item ADD COLUMN IF NOT EXISTS media_text text;
ALTER TABLE iai_item ADD COLUMN IF NOT EXISTS media_text_from text[];
ALTER TABLE iai_item DROP CONSTRAINT IF EXISTS iai_item_media_text_from_ck;
ALTER TABLE iai_item ADD CONSTRAINT iai_item_media_text_from_ck
  CHECK (media_text_from IS NULL
         OR media_text_from <@ ARRAY['alt_text', 'quoted_post', 'crosspost_parent']::text[]);
