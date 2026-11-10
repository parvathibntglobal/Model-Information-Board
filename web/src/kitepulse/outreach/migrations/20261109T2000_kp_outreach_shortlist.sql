-- Kite Pulse outreach, phase 2: the Shortlister's output (ARCHITECTURE.md 5.2).
--
-- One row per thread per prompt version: what code decided before the model
-- (set_aside), or what the model proposed and code checked (proposed), or a
-- model answer code refused (invalid). The thread's own status is NOT changed:
-- a shortlisted thread is still 'found' and still in To review, so Skip and
-- Mark posted work exactly as before. This table only ORDERS that list.
--
-- outcome
--   set_aside  code did not send it: words_far_apart | hiring_thread | too_old.
--              No model call, no spend row.
--   proposed   the model answered and every field passed code's checks.
--   invalid    the model answered and a field failed; invalid_why says which.
--              The answer is kept as given, never corrected (rule 12).
--
-- A call that failed before any answer (network, provider error) writes NO
-- row: the thread is simply not shortlisted yet, and the next run tries again.
--
-- READERS (CLAUDE.md rule 9), 2026-11-09:
--   outcome, set_aside_reason, problem, relevance, reason, invalid_why
--       kp_review.listing: the order of To review and the badge on each thread
--   article_slug, slug_verified
--       kp_review.listing returns them; the screen shows a slug when there is
--       one. Always NULL / false until the article index exists (5.3).
--   model, prompt_version
--       shortlist.py: a thread is shortlisted again when the prompt changes;
--       kp_review.listing shows the model's name beside its suggestion.
--   spend_id   DECLARED UNREAD: links a row to the call that paid for it, for a
--              cost-per-useful-thread figure the Reporter will compute.
--   input_chars  DECLARED UNREAD: whether a cut post changed the answer.

CREATE TABLE kp_outreach_shortlist (
  id               bigserial   PRIMARY KEY,
  thread_id        bigint      NOT NULL REFERENCES kp_outreach_thread(id),
  at               timestamptz NOT NULL DEFAULT now(),
  prompt_version   text        NOT NULL,
  outcome          text        NOT NULL,
  set_aside_reason text,
  model            text,
  spend_id         bigint      REFERENCES kp_outreach_spend(id),
  input_chars      integer,
  problem          text,
  relevance        text,
  article_slug     text,
  slug_verified    boolean,
  reason           text,
  invalid_why      text,

  CONSTRAINT kp_outreach_shortlist_once_uq UNIQUE (thread_id, prompt_version),
  CONSTRAINT kp_outreach_shortlist_outcome_ck
    CHECK (outcome IN ('set_aside', 'proposed', 'invalid')),
  CONSTRAINT kp_outreach_shortlist_set_aside_ck
    CHECK ((outcome = 'set_aside') = (set_aside_reason IS NOT NULL)),
  CONSTRAINT kp_outreach_shortlist_set_aside_reason_ck
    CHECK (set_aside_reason IN ('words_far_apart', 'hiring_thread', 'too_old')),
  -- a set-aside thread was never sent, so it has no model and no answer
  CONSTRAINT kp_outreach_shortlist_no_model_when_set_aside_ck
    CHECK (outcome <> 'set_aside' OR (model IS NULL AND spend_id IS NULL
           AND problem IS NULL AND relevance IS NULL AND reason IS NULL)),
  CONSTRAINT kp_outreach_shortlist_model_when_sent_ck
    CHECK (outcome = 'set_aside' OR model IS NOT NULL),
  CONSTRAINT kp_outreach_shortlist_proposed_ck
    CHECK (outcome <> 'proposed' OR (problem IS NOT NULL AND relevance IS NOT NULL
           AND reason IS NOT NULL AND slug_verified IS NOT NULL)),
  CONSTRAINT kp_outreach_shortlist_invalid_ck
    CHECK ((outcome = 'invalid') = (invalid_why IS NOT NULL)),
  CONSTRAINT kp_outreach_shortlist_relevance_ck
    CHECK (outcome <> 'proposed' OR relevance IN ('high', 'medium', 'low'))
);

CREATE INDEX kp_outreach_shortlist_thread_ix ON kp_outreach_shortlist (thread_id, at DESC);
