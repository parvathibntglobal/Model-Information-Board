-- Fresh AI news for the News page (/news, signed in). 2026-10-28.
-- contract/news_sources.yaml.
--
-- Headlines with a link, from the feeds that file lists. Nothing in the
-- evidence pipeline reads these tables and no model call writes them: a news
-- item is never a claim, a quote or a board entry.
--
-- WHO WRITES: collect/news/harvest.py:harvest, from
-- `python -m collect.cli news harvest` (every 6 hours once switched on,
-- .github/workflows/news-harvest.yml).
-- WHO READS: judge/news.py:news_view, for GET /news.
--
-- news_item, ONE ROW PER ITEM, APPEND-ONLY - except a `daily` source's entry,
-- which is one row per source and UTC day and is updated as that day's items
-- arrive (contract/news_sources.yaml `daily`).
--   id            stable id: the link for an ordinary item, source + day for a
--                 daily entry
--   source_key    contract/news_sources.yaml `key`
--   url           the item's own link; a daily entry links its newest item
--   title         as the source gives it; a daily entry's is composed
--                 ("llama.cpp: 18 releases on 2026-10-27 (b11913 - b11938)")
--   published_at  the source's own date. NULL when it gives none - never the
--                 time we saw it (rule 6); the page says "date not given"
--   slug          the story's address, /news/<slug>: the headline's key words
--                 (harvest.py `slug_base`), set once and never changed; unique
--   summary       the brief: the source's own words cut by code to whole
--                 sentences up to `summary_max_words` (harvest.py
--                 `choose_brief`). NULL when the source gives nothing usable
--   summary_source  feed | feed_content | page_description: which of the
--                 source's own texts the brief was cut from - the feed's
--                 summary, the article content the feed carries, or the
--                 page's own description tag. NULL with no brief
--   author        as given; NULL when not given
--   categories    as given; empty when none
--   image_url     the story's picture link (https only); NULL when none was
--                 found - the page then draws a card. The picture itself is
--                 never downloaded
--   image_source  feed | link_preview: where image_url came from (the feed
--                 item, or the article's og:image - collect/news/preview.py,
--                 CLAUDE.md's second scraping exception). NULL with no picture
--   preview_checked_at  when the article was asked for its link-preview
--                 picture; set once, found or not, so no page is asked twice.
--                 NULL: not asked (it had a feed picture, or it is a release)
--   preview_raw_ref  raw store ref of the <head> that was read; NULL if none
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
  slug              text NOT NULL UNIQUE,
  source_key        text NOT NULL,
  url               text NOT NULL,
  title             text NOT NULL,
  published_at      timestamptz,
  summary           text,
  summary_source    text,
  author            text,
  categories        text[] NOT NULL DEFAULT '{}',
  image_url         text,
  image_source      text,
  preview_checked_at timestamptz,
  preview_raw_ref   text,
  llm_keywords      text[] NOT NULL DEFAULT '{}',
  daily_count       integer,
  raw_ref           text NOT NULL,
  first_seen_at     timestamptz NOT NULL,
  updated_at        timestamptz NOT NULL,
  pipeline_version  text NOT NULL,
  CONSTRAINT news_item_daily_count_ck CHECK (daily_count IS NULL OR daily_count > 0),
  CONSTRAINT news_item_image_https_ck CHECK (image_url IS NULL OR image_url LIKE 'https://%'),
  CONSTRAINT news_item_image_source_ck CHECK (image_source IN ('feed', 'link_preview')),
  CONSTRAINT news_item_image_has_source_ck CHECK ((image_url IS NULL) = (image_source IS NULL)),
  CONSTRAINT news_item_summary_source_ck
    CHECK (summary_source IN ('feed', 'feed_content', 'page_description')),
  CONSTRAINT news_item_summary_has_source_ck CHECK ((summary IS NULL) = (summary_source IS NULL))
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
