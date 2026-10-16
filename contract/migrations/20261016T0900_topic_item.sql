-- THE BLOG'S TOPIC HARVEST (2026-10-16): papers and posts about AI in general,
-- for the blog only. Written by scripts/harvest_topics.py from arXiv's API and
-- the blog feeds contract/sources.yaml already reviews; read by judge/topics.py
-- (trends, emerging terms, what to write next). Never read by the evidence
-- pipeline, and never a board entry.
--
-- WHAT A ROW HOLDS IS WHAT THE PUBLISHER SYNDICATES: a title, the abstract or
-- the feed's own summary, the authors, the date and the link. Never a full
-- article.
--
-- No transaction control here: the runner owns the transaction.

CREATE TABLE topic_item (
  -- 'arxiv:<id>' for a paper; '<feed source id>|<entry id>' for a post.
  id            text PRIMARY KEY,
  -- 'arxiv', or the feed's source id as contract/sources.yaml names it.
  source        text NOT NULL,
  kind          text NOT NULL,
  title         text NOT NULL,
  -- The abstract or the feed summary, as plain text. NULL when the feed gives none.
  summary       text,
  url           text NOT NULL,
  authors       text[] NOT NULL DEFAULT '{}',
  -- When the publisher says it was published. NULL when it does not say.
  published_at  timestamptz,
  -- The blog_topics.yaml keys its title and summary match. Recomputed on every
  -- harvest, so a topic added later re-labels old items.
  topics        text[] NOT NULL DEFAULT '{}',
  harvested_at  timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT topic_item_kind_ck CHECK (kind IN ('paper', 'post'))
);

CREATE INDEX topic_item_published_idx ON topic_item (published_at);
CREATE INDEX topic_item_topics_idx ON topic_item USING gin (topics);
