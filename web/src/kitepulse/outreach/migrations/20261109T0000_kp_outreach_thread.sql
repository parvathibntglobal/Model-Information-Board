-- Kite Pulse outreach, phase 1: one row per thread a Finder matched.
--
-- Lives in the OUTREACH database (KP_OUTREACH_DATABASE_URL), never in MIB's,
-- so it is applied by web/src/kitepulse/outreach/setup_db.py, not by
-- collect.migrate, and it is not a contract/ change.
--
-- The columns are common/thread.py's Thread record, one for one, so a Finder's
-- JSONL line becomes a row without a reshape. ARCHITECTURE.md section 6 drew a
-- single matched_problem/matched_phrase; a thread found by two phrases matches
-- both, so they are arrays here, as they are in the record.
--
-- READERS (CLAUDE.md rule 9). Declared, not yet built, on 2026-11-09:
--   writer  the four Finders (hackernews, discourse, devto, github find.py),
--           which today write var/outreach/*.jsonl only
--   reader  the phase-1 review screen (ARCHITECTURE.md 5.5), not built
-- Until the writer lands this table is empty, and empty means "no Finder has
-- written here", never "no threads were found".

CREATE TABLE kp_outreach_thread (
  id               bigserial   PRIMARY KEY,
  source           text        NOT NULL,   -- hackernews | discourse | devto | github
  ext_id           text        NOT NULL,   -- the source's own id
  kind             text        NOT NULL,   -- story | comment | topic | article | discussion
  community        text        NOT NULL,   -- a forum host, dev.to, a GitHub repo
  url              text        NOT NULL,
  root_id          text,                   -- the story or topic a comment belongs to
  title            text,
  body             text,                   -- as fetched, plain text; never published by us
  author           text,                   -- NULL: a deleted account, not "anonymous"
  created_at       timestamptz NOT NULL,   -- when the author posted it
  fetched_at       timestamptz NOT NULL,   -- when a Finder first read it
  matched_problems text[]      NOT NULL,
  matched_phrases  text[]      NOT NULL,
  status           text        NOT NULL,
  drop_reason      text,
  flags            text[]      NOT NULL DEFAULT '{}',

  CONSTRAINT kp_outreach_thread_source_ext_uq UNIQUE (source, ext_id),
  CONSTRAINT kp_outreach_thread_matched_ck
    CHECK (cardinality(matched_problems) >= 1 AND cardinality(matched_phrases) >= 1),
  CONSTRAINT kp_outreach_thread_status_ck
    CHECK (status IN ('found', 'dropped', 'shortlisted', 'drafted', 'draft_refused',
                      'approved', 'posted', 'skipped')),
  -- A dropped thread always says why, and only a dropped thread has a reason
  -- (CLAUDE.md rule 6: an absence we caused never reads as one we found).
  CONSTRAINT kp_outreach_thread_drop_reason_ck
    CHECK ((status = 'dropped') = (drop_reason IS NOT NULL))
);

CREATE INDEX kp_outreach_thread_status_created_ix
  ON kp_outreach_thread (status, created_at DESC);
