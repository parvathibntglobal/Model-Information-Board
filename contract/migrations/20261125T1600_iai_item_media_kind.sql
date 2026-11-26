-- WHAT MEDIA A POST CARRIES (anooj, 2026-11-25).
--
-- The Industry AI lane reads text only: a caption, a title, a body. A post whose
-- content is a picture or a video was judged on its few words, and "no AI term"
-- in three words of caption was stored as if the video had been read. On
-- 2026-11-25, 277 of the 620 watched posts dropped for "no AI term" had under 80
-- characters of text (watch-found rows with text still held, read-only count).
-- `media_kind` records what the provider says the post carries
-- (collect/industry_ai/media.py), so such a post is counted apart as "not
-- readable" (drop_stage 'unread') rather than filtered out.
--
--   none | image | gallery | video | link   recorded
--   NULL                                    NOT recorded: a platform not read for
--                                           media, or a row stored before this
--                                           column. Never read as 'none' (rule 6).
--
-- Rows stored before it stay NULL until their post is seen again by a run
-- (store.upsert_items fills a NULL, never overwrites a recorded kind).
--
-- WHO RUNS THIS MIGRATION: the person who merges the PR that adds it, on the
-- shared database, straight after merge, with `db check` before and after, and
-- announces it on that PR the same day. Until it has run, a run fails when it
-- stores (the column is missing), so it must run before the next harvest.
--
-- No transaction control here: the runner owns the transaction.

ALTER TABLE iai_item ADD COLUMN IF NOT EXISTS media_kind text;
ALTER TABLE iai_item DROP CONSTRAINT IF EXISTS iai_item_media_kind_ck;
ALTER TABLE iai_item ADD CONSTRAINT iai_item_media_kind_ck
  CHECK (media_kind IS NULL OR media_kind IN ('none', 'image', 'gallery', 'video', 'link'));
