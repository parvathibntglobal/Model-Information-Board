-- Blog posts in the shared database: drafts pending, approved posts shown,
-- rejected posts kept but never shown. Builds on 20261006T1200, which
-- recorded runs and review decisions but left the posts themselves as files.
--
-- WHY. A draft as a file lives on the machine that generated it. The team
-- reviews on the hosted platform, which has none of those files, and the
-- hosted Blogs page could only show what a deployed commit carried - so a post
-- reached readers through git, and a review decision could name a post the
-- deciding machine did not have. One row per post, read by every machine,
-- removes both (agreed by anooj, 2026-10-06).
--
-- THE STATES
--   pending    stored, awaiting review; never on the public Blogs page
--   approved   on the public Blogs page
--   rejected   never on the Blogs page, CONTENT KEPT. Decided by anooj,
--              2026-10-06 (a first draft deleted it): a rejected post and its
--              reason are what a later change can feed back to the generator
--              so it avoids similar posts. Its `plan_key` already stops the
--              planner writing the same (format, subject) again and paying for
--              it twice. It can be moved back to drafts like an approved one.
--
-- WHO WRITES
--   judge/blog_store.py   store_drafts (a finished run's drafts, or a
--                         machine's draft files stored from Admin -> Blogs),
--                         decide (approve / reject / move back)
-- Inserts are ON CONFLICT (slug) DO NOTHING: storing never overwrites a post
-- that is already stored, whatever its state.
--
-- `blog_post_review.run_id` BECOMES NULLABLE: a post stored from files was
-- written by no recorded run, and its decisions must still be recordable.
-- Existing rows all carry a run id; nothing about them changes.

CREATE TABLE blog_post (
  slug          text PRIMARY KEY,
  state         text NOT NULL CHECK (state IN ('pending', 'approved', 'rejected')),
  doc           jsonb NOT NULL, -- the post as views.js vPost renders it, in every state
  plan_key      text,           -- the planner's (format, subject) key
  run_id        text REFERENCES blog_generation_run(id),  -- NULL: stored from files
  generated_at  timestamptz,    -- the post's provenance.generated_at; NULL when absent
  stored_at     timestamptz NOT NULL
);

CREATE INDEX blog_post_state ON blog_post (state);

ALTER TABLE blog_post_review ALTER COLUMN run_id DROP NOT NULL;
