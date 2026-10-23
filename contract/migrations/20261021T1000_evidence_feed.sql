-- THE EVIDENCE FEED (2026-10-21, PROPOSED on branch feat/evidence-feed).
--
-- The drill-down from a count to the reports it counted: each report in our
-- own words, its source beside it, and a one-page summary per model. Settings
-- in contract/evidence_feed.yaml; publication terms in contract/publication.yaml
-- `evidence_feed`; the code in judge/feed/.
--
-- ⚠ THE FOURTH RECORDED CALLER UNDER RULE 2 (CLAUDE.md), and the first
--   whose output reaches a page
--   without a person reading each item: a paraphrase is stored once code has
--   checked its shape. The summary keeps the blog's and the quiz's guard - a
--   person approves it. This needs the rule-2 amendment in
--   docs/proposals/evidence-feed.md before it reaches main. Spend is its own
--   stage, 'feed', outside the daily extraction cap.
--
-- No transaction control here: the runner owns the transaction.

-- ONE PARAPHRASE PER REPORT, per prompt version. A report is one document
-- about one model - the unit the board counts as "reports".
CREATE TABLE feed_paraphrase (
  document_id       text NOT NULL REFERENCES document (id),
  -- The registry id the board groups on (board_entry.model_version_id can hold
  -- either id shape; this is the resolved one).
  model_version_id  text NOT NULL REFERENCES model_version (id),
  prompt_version    text NOT NULL,
  -- sha256 of the excerpts this was written from. When a report gains or
  -- loses an entry the digest changes and the paraphrase is re-drafted, so a
  -- stored paraphrase never describes a different set of quotes from the one
  -- the counts are made of.
  excerpts_digest   text NOT NULL,
  text              text NOT NULL,
  -- The model OpenRouter SERVED, not the one asked for.
  proposer_model    text NOT NULL,
  run_id            text NOT NULL,
  generated_at      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (document_id, model_version_id, prompt_version)
);

CREATE INDEX feed_paraphrase_model_idx ON feed_paraphrase (model_version_id);

-- HOW A REDDIT OR X DOCUMENT IS CITED: the platform's official embed, or the
-- reason there is none. One row per document, whichever models it is about.
-- A Reddit link post's `document.url` is the LINKED content, not the thread,
-- so the post address comes from the raw payload (scripts/build_evidence_feed.py).
CREATE TABLE feed_embed (
  document_id  text PRIMARY KEY REFERENCES document (id),
  platform     text NOT NULL,
  outcome      text NOT NULL,
  -- The ID-ONLY address (judge/feed/items.py canonical_embed_url):
  -- reddit.com/comments/<post>/[_/<comment>/] or x.com/i/status/<id>. No
  -- subreddit, no title slug, no handle; the payload carries only the ids.
  -- (Reddit's oEmbed title, author and community were stored here until the
  -- #558 second review, 2026-10-23: nothing read them, and the embed shows
  -- them itself. Dropped before this migration first ran on a shared DB.)
  url          text,
  resolved_at  timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT feed_embed_platform_ck CHECK (platform IN ('reddit', 'x')),
  CONSTRAINT feed_embed_outcome_ck
    CHECK (outcome IN ('embeddable', 'no_post_address', 'unavailable')),
  -- An address exactly when there is something to embed.
  CONSTRAINT feed_embed_url_ck CHECK ((outcome = 'embeddable') = (url IS NOT NULL))
);

-- ONE PAGE PER MODEL, DRAFTED BY A MODEL, APPROVED BY A PERSON. The page shows
-- the newest approved row; a new approval supersedes the last.
CREATE TABLE feed_summary (
  -- fs_ + random hex.
  id                 text PRIMARY KEY,
  model_version_id   text NOT NULL REFERENCES model_version (id),
  prompt_version     text NOT NULL,
  -- [{"text": ..., "cites": [document_id, ...]}], every paragraph citing at
  -- least one report it was written from (checked in code).
  paragraphs         jsonb NOT NULL,
  -- What the soft checks found, for the reviewer: [{"check": ..., "detail": ...}].
  flags              jsonb NOT NULL DEFAULT '[]'::jsonb,
  -- The denominator travels with the summary (rule 7): written from the newest
  -- `reports_used` of `reports_available` paraphrased reports.
  reports_used       integer NOT NULL,
  reports_available  integer NOT NULL,
  -- When the newest report it was written from was POSTED, so the page can say
  -- how many reports arrived since.
  newest_report_at   timestamptz,
  state              text NOT NULL DEFAULT 'pending',
  proposer_model     text NOT NULL,
  run_id             text NOT NULL,
  generated_at       timestamptz NOT NULL DEFAULT now(),
  reviewed_at        timestamptz,
  review_note        text,
  CONSTRAINT feed_summary_state_ck
    CHECK (state IN ('pending', 'approved', 'rejected', 'superseded')),
  -- A decision has a time; a pending draft has none.
  CONSTRAINT feed_summary_reviewed_ck CHECK ((state = 'pending') = (reviewed_at IS NULL)),
  CONSTRAINT feed_summary_paragraphs_ck
    CHECK (jsonb_typeof(paragraphs) = 'array' AND jsonb_array_length(paragraphs) > 0),
  CONSTRAINT feed_summary_reports_ck CHECK (0 < reports_used AND reports_used <= reports_available)
);

CREATE INDEX feed_summary_model_state_idx ON feed_summary (model_version_id, state, generated_at DESC);

ALTER TABLE spend_ledger DROP CONSTRAINT spend_ledger_stage_ck;
ALTER TABLE spend_ledger
  ADD CONSTRAINT spend_ledger_stage_ck CHECK (stage IN ('extract', 'ask', 'blog', 'quiz', 'feed'));
