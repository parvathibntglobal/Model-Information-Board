-- Fresh AI news for Admin -> News. 2026-10-28. contract/news_sources.yaml.
--
-- Headlines with a link, from the feeds that file lists. Nothing in the
-- evidence pipeline reads these tables and no model call writes them: a news
-- item is never a claim, a quote or a board entry.
--
-- WHO WRITES: collect/news/harvest.py:harvest, from
-- `python -m collect.cli news harvest` (every 6 hours once switched on,
-- .github/workflows/news-harvest.yml).
-- WHO READS: judge/news.py:news_view, for GET /admin/news.
--
-- news_item, ONE ROW PER ITEM, APPEND-ONLY - except a `daily` source's entry,
-- which is one row per source and UTC day and is updated as that day's items
-- arrive (contract/news_sources.yaml `daily`).
--   id            stable id: the link for an ordinary item, source + day for a
--                 daily entry
--   source_key    contract/news_sources.yaml `key`
--   url           the item's own link; a daily entry links its newest item
--   title         as the source gives it; a daily entry's is composed
--                 ("15 builds on 2026-10-28: b11937 - b11951")
--   published_at  the source's own date. NULL when it gives none - never the
--                 time we saw it (rule 6); the page says "date not given"
--   summary       the source's summary, HTML removed, cut to
--                 `summary_max_chars`. NULL when it gives none
--   author        as given; NULL when not given
--   categories    as given; empty when none
--   llm_keywords  the contract's `llm_keywords` this item matched; empty when
--                 none. A badge, never a default filter (rule 8)
--   daily_count   a daily entry: how many items it stands for. NULL otherwise
--   raw_ref       raw store ref of the response the item was read from
--   first_seen_at when we first stored it
--   updated_at    when it last changed (a daily entry gaining an item)
--   pipeline_version  the code that wrote it
--
-- news_fetch, ONE ROW PER SOURCE PER RUN: what each read did, so the page can
-- say a source is quiet, refused or failing rather than show nothing.
--   run_id        one harvest run
--   source_key    contract/news_sources.yaml `key`
--   fetched_at    when it was read
--   outcome       ok | robots_refused | http_error | error
--   http_status   NULL when no response came back
--   detail        why, for anything but ok; NULL for ok
--   items_seen    items in the response; NULL when it could not be read
--   items_new     rows this read added; NULL when it could not be read

CREATE TABLE news_item (
  id                text PRIMARY KEY,
  source_key        text NOT NULL,
  url               text NOT NULL,
  title             text NOT NULL,
  published_at      timestamptz,
  summary           text,
  author            text,
  categories        text[] NOT NULL DEFAULT '{}',
  llm_keywords      text[] NOT NULL DEFAULT '{}',
  daily_count       integer,
  raw_ref           text NOT NULL,
  first_seen_at     timestamptz NOT NULL,
  updated_at        timestamptz NOT NULL,
  pipeline_version  text NOT NULL,
  CONSTRAINT news_item_daily_count_ck CHECK (daily_count IS NULL OR daily_count > 0)
);
CREATE INDEX news_item_published_idx ON news_item (published_at DESC);
CREATE INDEX news_item_seen_idx ON news_item (first_seen_at DESC);

CREATE TABLE news_fetch (
  run_id            text NOT NULL,
  source_key        text NOT NULL,
  fetched_at        timestamptz NOT NULL,
  outcome           text NOT NULL,
  http_status       integer,
  detail            text,
  items_seen        integer,
  items_new         integer,
  PRIMARY KEY (run_id, source_key),
  CONSTRAINT news_fetch_outcome_ck
    CHECK (outcome IN ('ok', 'robots_refused', 'http_error', 'error')),
  CONSTRAINT news_fetch_detail_ck CHECK ((outcome = 'ok') = (detail IS NULL))
);
CREATE INDEX news_fetch_source_idx ON news_fetch (source_key, fetched_at DESC);
