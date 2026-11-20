-- THE INDUSTRY AI AGENT (2026-11-20): data about AI in five industries
-- (finance, healthcare, hospitality, engineering, governance), as a SEPARATE
-- LANE from the model board. Written by scripts/run_industry_ai.py
-- (collect/industry_ai/), read by judge/industry_ai/view.py for the signed-in
-- "AI in industries" page. Nothing in the evidence pipeline reads these
-- tables, and this lane writes nothing else. No language model is involved.
--
-- WHAT A ROW HOLDS: one harvested post or article - its ROOT's title and body
-- only, never comments - with the code rules' verdict and labels. DROPPED
-- ITEMS ARE KEPT TOO, with their stage and reason: they are the page's
-- denominator, and `--relabel` re-applies changed rules to them without a
-- request. The page shows counts only, never this text.
--
-- WHO RUNS THIS MIGRATION: the person who merges the PR that adds it, on the
-- shared database, straight after merge, and announces it the same day.
--
-- No transaction control here: the runner owns the transaction.

CREATE TABLE iai_run (
  id              text PRIMARY KEY,
  started_at      timestamptz NOT NULL,
  finished_at     timestamptz,
  -- harvest | relabel
  mode            text NOT NULL,
  -- running | ok | error
  status          text NOT NULL,
  domains         text[] NOT NULL,
  platforms       text[] NOT NULL,
  -- contract/industry_ai.yaml `pipeline_version` the run labelled with.
  pipeline_version text NOT NULL,
  -- Requests per platform, and RapidAPI quota as read from response headers.
  requests        jsonb NOT NULL DEFAULT '{}',
  quota           jsonb NOT NULL DEFAULT '{}',
  -- One entry per query: key, domain, platform, query, requests, items,
  -- status (ok | capped | error | skipped), detail.
  queries         jsonb NOT NULL DEFAULT '[]',
  -- The counts by stage, domain, type and platform after this run.
  counts          jsonb NOT NULL DEFAULT '{}',
  detail          text,
  CONSTRAINT iai_run_mode_ck CHECK (mode IN ('harvest', 'relabel')),
  CONSTRAINT iai_run_status_ck CHECK (status IN ('running', 'ok', 'error'))
);

CREATE TABLE iai_item (
  -- '<platform>:<external_id>'.
  id               text PRIMARY KEY,
  -- reddit | x | github | hackernews | devto | bluesky | feeds
  platform         text NOT NULL,
  external_id      text NOT NULL,
  url              text NOT NULL,
  title            text NOT NULL DEFAULT '',
  body             text NOT NULL DEFAULT '',
  -- When it was posted. NULL when the platform does not say (rule 6).
  created_at       timestamptz,
  -- The platform's own stable author id; never shown.
  author_id        text,
  -- The platform's declared language, where it declares one.
  lang             text,
  engagement       jsonb NOT NULL DEFAULT '{}',
  -- The article a post links to, when it links to one.
  link             text,
  -- The raw search page this item was read from (content-hash ref).
  discovery_ref    text,
  -- The domains whose queries found it, and the queries.
  domain_hints     text[] NOT NULL DEFAULT '{}',
  query_keys       text[] NOT NULL DEFAULT '{}',
  first_seen_at    timestamptz NOT NULL DEFAULT now(),
  last_seen_at     timestamptz NOT NULL DEFAULT now(),
  first_run_id     text REFERENCES iai_run(id),
  -- THE RULES' ANSWER, rewritten by every harvest and every `--relabel`.
  verdict          text NOT NULL,
  -- window | sieve | dedupe | filter, and why. NULL exactly when kept.
  drop_stage       text,
  drop_reason      text,
  flags            text[] NOT NULL DEFAULT '{}',
  -- Confirmed domains; EMPTY on a kept item means "domain unconfirmed".
  domains          text[] NOT NULL DEFAULT '{}',
  -- Within confirmed domains, the groups whose terms matched: '<domain>/<group>'.
  groups           text[] NOT NULL DEFAULT '{}',
  -- WHICH TERMS MATCHED, per domain: {"<domain>": {"terms": [...],
  -- "groups": {"<group>": [...]}}}. The value a workflow keyword's count is
  -- counted from (one post can count for several) - kept, not recomputed
  -- (#644 review, point 2). Written for every item the sieve passed.
  matched_terms    jsonb NOT NULL DEFAULT '{}',
  -- The AI terms the item named.
  ai_terms         text[] NOT NULL DEFAULT '{}',
  content_type     text,
  matched_pattern  text,
  stage_guess      text,
  canonical_of     text,
  share_count      integer NOT NULL DEFAULT 0,
  canonical_url    text,
  pipeline_version text NOT NULL,
  labelled_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT iai_item_platform_ck
    CHECK (platform IN ('reddit', 'x', 'github', 'hackernews', 'devto', 'bluesky', 'feeds')),
  CONSTRAINT iai_item_verdict_ck CHECK (verdict IN ('kept', 'dropped')),
  CONSTRAINT iai_item_drop_ck CHECK ((verdict = 'dropped') = (drop_reason IS NOT NULL)),
  CONSTRAINT iai_item_type_ck CHECK (content_type IS NULL OR content_type IN
    ('use_case', 'how_to', 'tool_or_product', 'research', 'news', 'discussion')),
  CONSTRAINT iai_item_stage_ck CHECK (stage_guess IS NULL OR stage_guess IN
    ('deployed', 'pilot', 'first_hand'))
);

CREATE INDEX iai_item_verdict_idx ON iai_item (verdict);
CREATE INDEX iai_item_domains_idx ON iai_item USING gin (domains);
CREATE INDEX iai_item_created_idx ON iai_item (created_at);
