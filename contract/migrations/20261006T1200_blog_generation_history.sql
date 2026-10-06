-- Blog generation history and post review. ADD-ONLY: two new tables, nothing
-- existing is altered or touched.
--
-- WHY NOW. Admin -> Blogs starts `generate_sample_blogs.py --plan 3` (the
-- button moved there from the Blogs page, 2026-10-06), and a run spends real
-- money. Until this, what a run did lived only in two files on the machine that
-- ran it (`_blog_synthesis/_ui_status.json`, `_ui_run.log`), overwritten by the
-- next run. A run is now a row: what it was asked for, what it wrote, what it
-- cost as the provider reported it, its tokens, and its whole log.
--
-- SCOPE: POSTS THE BUTTON WRITES FROM NOW ON. The drafts already on disk are
-- left exactly as they are; they belong to no run, so they are not reviewable
-- here. A post becomes reviewable by appearing in a run's `posts_written`.
--
-- THE DRAFTS STAY FILES. `judge/blog_posts.py` still reads them from
-- BLOG_POSTS_DIR; these tables record what happened TO them (which run wrote
-- them, and what was decided), not the posts themselves. A `blog_post` table for
-- the content is a separate decision and is not made here.
--
-- REVIEW IS APPEND-ONLY. A decision is a new row, never an update: the latest
-- row for a slug is its state, and "move back to drafts" is a `reopened` row,
-- so every decision ever made stays on record (rule: rulings are undoable).
--
-- No `decided_by`: the backend authenticates the deployment, not the person,
-- so any name stored there would be unverified. Recorded when identity is.

CREATE TABLE blog_generation_run (
  id               text PRIMARY KEY,
  started_at       timestamptz NOT NULL,
  finished_at      timestamptz,
  state            text NOT NULL,          -- starting | running | done | partial | failed | stalled
  requested_count  integer NOT NULL,
  model            text,                   -- the generation model the run reported
  cost_usd         numeric(12,6),          -- provider-reported; NULL = not reported, never 0
  tokens_in        bigint,                 -- summed from the run's per-post log lines
  tokens_out       bigint,
  posts_written    text[] NOT NULL DEFAULT '{}',   -- slugs of drafts this run created
  posts_failed     text[] NOT NULL DEFAULT '{}',   -- planned post keys that failed
  message          text,
  log              text                    -- the run's console log, keys masked
);

CREATE TABLE blog_post_review (
  id          text PRIMARY KEY,
  slug        text NOT NULL,
  run_id      text NOT NULL REFERENCES blog_generation_run(id),
  decision    text NOT NULL CHECK (decision IN ('approved', 'rejected', 'reopened')),
  reason      text,
  decided_at  timestamptz NOT NULL
);

CREATE INDEX blog_post_review_slug_at ON blog_post_review (slug, decided_at DESC);
