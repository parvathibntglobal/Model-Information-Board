-- READERS' DISCUSSION POSTS, HELD FOR REVIEW (2026-10-20).
--
-- The Discussions page lets a reader share their own experience with an AI
-- model. Every post is stored `pending` and is shown only once a person
-- approves it in Admin -> Discussions (judge/discussions.py) - the same
-- draft-then-approve shape as the blog and the quiz bank.
--
-- NEVER EVIDENCE. Nothing reads this table into `claim`, `board_entry` or any
-- count: a reader's post is shown beside the reports, not added to them.
--
-- REPLIES ARE ROWS TOO. A reply carries `parent_id` (the post it answers) and
-- no title, and is held for review like a post. Deleting a post deletes its
-- replies (ON DELETE CASCADE).
--
-- NO EMAIL, NO ADDRESS, NO ACCOUNT. The display name is free text, required in
-- code (judge/discussions.py).
-- The rate limit is in memory (judge/gate.py), so no IP is stored.
--
-- No transaction control here: the runner owns the transaction.

CREATE TABLE discussion_post (
  -- dp_ + random hex. A post is not deduplicated by its text: two readers can
  -- write the same sentence.
  id            text PRIMARY KEY,
  -- One of contract/discussions.yaml `topics[].slug`, checked in code.
  topic         text NOT NULL,
  -- The post this answers; NULL for a post that opens a discussion. A reply
  -- takes its parent's topic.
  parent_id     text REFERENCES discussion_post (id) ON DELETE CASCADE,
  -- A post's title; NULL exactly for a reply (CHECK below).
  title         text,
  body          text NOT NULL,
  -- The display name as the reader typed it, required in code
  -- (judge/discussions.py). The column stays nullable.
  author_name   text,
  -- Optional: the model the post is about, as a canonical id
  -- (`anthropic/claude-opus-5`). Not checked against the registry - a reader
  -- may write about a model we do not list.
  model_id      text,
  state         text NOT NULL DEFAULT 'pending',
  created_at    timestamptz NOT NULL DEFAULT now(),
  reviewed_at   timestamptz,
  review_note   text,
  CONSTRAINT discussion_post_state_ck CHECK (state IN ('pending', 'approved', 'rejected')),
  -- A decision has a time; a pending post has none.
  CONSTRAINT discussion_post_reviewed_ck CHECK ((state = 'pending') = (reviewed_at IS NULL)),
  -- A post has a title and no parent; a reply has a parent and no title.
  CONSTRAINT discussion_post_reply_ck CHECK ((parent_id IS NULL) = (title IS NOT NULL))
);

CREATE INDEX discussion_post_state_idx ON discussion_post (state, created_at DESC);
CREATE INDEX discussion_post_parent_idx ON discussion_post (parent_id);
