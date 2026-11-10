-- Kite Pulse outreach, phase 1 review: what a person decided about a thread.
--
-- Admin -> Kite Pulse -> Outreach shows threads with status 'found'. A person
-- either SKIPS one, with a reason, or answers it on the forum from their own
-- account and MARKS IT POSTED with the URL of their reply. "Back to review"
-- returns it to 'found' and clears these columns (it undoes a misclick; the
-- earlier decision is not kept).
--
-- On the thread row rather than in a separate table: phase 1 has one decision
-- per thread and no drafts. Phase 2's drafts get their own table
-- (ARCHITECTURE.md section 6, kp_outreach_draft / kp_outreach_reply).
--
-- READERS (CLAUDE.md rule 9), all built with this migration on 2026-11-09:
--   writer  web/src/kitepulse/outreach/kp_review.py (skip, mark_posted, reopen)
--   reader  kp_review.listing -> /admin/outreach/threads -> OutreachPanel.jsx
-- decided_by is NULL when the request carried no signed-in identity (a local
-- backend with no sign-in configured): "not known", never "nobody".

ALTER TABLE kp_outreach_thread
  ADD COLUMN decided_at        timestamptz,
  ADD COLUMN decided_by        text,
  ADD COLUMN skip_reason       text,
  ADD COLUMN skip_note         text,
  ADD COLUMN posted_url        text,
  ADD COLUMN posted_by_account text;

ALTER TABLE kp_outreach_thread
  -- A decided thread says when; an undecided one carries no decision fields.
  ADD CONSTRAINT kp_outreach_thread_decided_ck
    CHECK ((status IN ('skipped', 'posted')) = (decided_at IS NOT NULL)),
  ADD CONSTRAINT kp_outreach_thread_decided_by_ck
    CHECK (decided_by IS NULL OR decided_at IS NOT NULL),
  -- Skipped always says why, and only a skipped thread has a skip reason.
  ADD CONSTRAINT kp_outreach_thread_skip_ck
    CHECK ((status = 'skipped') = (skip_reason IS NOT NULL)),
  ADD CONSTRAINT kp_outreach_thread_skip_reason_ck
    CHECK (skip_reason IN ('not_relevant', 'already_answered', 'community_unwelcoming',
                           'other')),
  ADD CONSTRAINT kp_outreach_thread_skip_note_ck
    CHECK ((skip_reason IS DISTINCT FROM 'other' OR skip_note IS NOT NULL)
           AND (skip_note IS NULL OR status = 'skipped')),
  -- Posted always names the reply and the account it was posted from.
  ADD CONSTRAINT kp_outreach_thread_posted_ck
    CHECK ((status = 'posted') = (posted_url IS NOT NULL)
       AND (status = 'posted') = (posted_by_account IS NOT NULL));
