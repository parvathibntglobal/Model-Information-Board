-- The evidence feed's upkeep agent (2026-10-27, PROPOSED): a nightly
-- paraphrase run and a weekly summary REVISION, both on a schedule.
-- docs/proposals/evidence-feed-agent.md.
--
-- NOTHING IS SCHEDULED UNTIL A REFUSAL IS REMEMBERED (Parvathi, #558): a
-- paraphrase or a summary the checks refused was never stored, so every run
-- paid to ask for it again. Run by hand that was bounded; on a schedule it is
-- unbounded repeat spend on the same refusals. These tables are that memory.
--
-- WHO WRITES: judge/feed/paraphrase.py (feed_paraphrase_refusal) and
-- judge/feed/summary.py (feed_summary_attempt, feed_summary.parent_id and
-- .changes), from scripts/build_evidence_feed.py, by hand or from
-- .github/workflows/evidence-feed.yml.
-- WHO READS: paraphrase.pending() and summary.models_due() /
-- summary.revisions_due(), to skip what was refused and has not changed since;
-- summary.listing() for Admin; summary.current() for the public tab.

-- A PARAPHRASE THE CHECKS REFUSED, for the excerpts it was asked from. It is
-- asked for again only when the report's excerpts change (a new digest) or the
-- prompt version does - never just because another night came round.
CREATE TABLE feed_paraphrase_refusal (
  document_id       text NOT NULL REFERENCES document (id),
  model_version_id  text NOT NULL REFERENCES model_version (id),
  prompt_version    text NOT NULL,
  excerpts_digest   text NOT NULL,
  -- The last attempt's reason, e.g. "copies 9 consecutive words".
  reason            text NOT NULL,
  run_id            text NOT NULL,
  refused_at        timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (document_id, model_version_id, prompt_version)
);

-- EVERY SUMMARY ATTEMPT AND ITS OUTCOME: a stored draft or revision (which is
-- also a feed_summary row), a draft the checks refused, or a revision that
-- found nothing worth changing. `newest_report_at` is the newest report the
-- attempt considered, so a model is not asked again until a newer one arrives;
-- `attempted_at` is what the weekly cadence counts from.
CREATE TABLE feed_summary_attempt (
  id                  bigserial PRIMARY KEY,
  model_version_id    text NOT NULL REFERENCES model_version (id),
  kind                text NOT NULL,
  outcome             text NOT NULL,
  -- The approved summary a revision started from; NULL for a first draft.
  parent_id           text REFERENCES feed_summary (id),
  -- The row it stored; NULL unless the outcome is `stored`.
  summary_id          text REFERENCES feed_summary (id),
  newest_report_at    timestamptz,
  -- How many reports the attempt was given (rule 7): for a revision, only the
  -- ones newer than its parent.
  reports_considered  integer NOT NULL,
  -- Why it was refused, or why nothing changed.
  detail              text,
  prompt_version      text NOT NULL,
  run_id              text NOT NULL,
  attempted_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT feed_summary_attempt_kind_ck CHECK (kind IN ('draft', 'revision')),
  CONSTRAINT feed_summary_attempt_outcome_ck CHECK (outcome IN ('stored', 'refused', 'no_change')),
  CONSTRAINT feed_summary_attempt_stored_ck CHECK ((outcome = 'stored') = (summary_id IS NOT NULL)),
  CONSTRAINT feed_summary_attempt_parent_ck CHECK ((kind = 'revision') = (parent_id IS NOT NULL)),
  CONSTRAINT feed_summary_attempt_reports_ck CHECK (reports_considered >= 0)
);

CREATE INDEX feed_summary_attempt_model_idx ON feed_summary_attempt (model_version_id, attempted_at DESC);

-- A REVISION IS A SUMMARY WITH A PARENT. It is stored `pending` like a draft
-- and approved by a person like a draft; `changes` lists each edited point -
-- what it was, what it is now, the reports it adds and why - for Admin to
-- show side by side. A first draft has neither.
ALTER TABLE feed_summary ADD COLUMN parent_id text REFERENCES feed_summary (id);
ALTER TABLE feed_summary ADD COLUMN changes jsonb;
ALTER TABLE feed_summary ADD CONSTRAINT feed_summary_revision_ck
  CHECK ((parent_id IS NULL) = (changes IS NULL));
