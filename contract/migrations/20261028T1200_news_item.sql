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
-- news_item, ONE ROW PER ITEM. A row is INSERTED once and never re-inserted
-- (ON CONFLICT DO NOTHING), but it is NOT append-only, and these are every
-- field updated after the insert (#583 review):
--   - a `daily` source's entry: url, title, published_at, summary,
--     llm_keywords, daily_count, raw_ref - as that UTC day's items arrive;
--   - collect/news/preview.py on a story with no feed picture: image_url,
--     image_source, preview_outcome, preview_attempts, preview_checked_at,
--     preview_raw_ref, and the chosen brief (summary, summary_source);
--   - preview.py `rebrief_from_stored_heads`: the chosen brief again.
-- What the feed gave is never overwritten: its brief stays in feed_summary /
-- feed_summary_source, and every response read stays in the raw store.
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
--   feed_summary  the brief as the FEED gave it, set at insert and never
--                 changed; the chosen `summary` sits beside it
--   feed_summary_source  feed | feed_content, as `summary_source` was at insert
--   author        as given; NULL when not given
--   categories    as given; empty when none
--   image_url     the story's picture link (https only); NULL when none was
--                 found - the page then draws a card. The picture itself is
--                 never downloaded
--   image_source  feed | link_preview: where image_url came from (the feed
--                 item, or the article's og:image - collect/news/preview.py,
--                 CLAUDE.md's second scraping exception). NULL with no picture
--   preview_checked_at  when the article's link preview got a FINAL answer
--                 (a picture, none, a robots.txt refusal, a 4xx, or
--                 `max_attempts` reached).
--                 NULL: not asked yet, or a failure that may pass is to be retried
--   preview_outcome  found | none | robots_refused | robots_no_answer |
--                 not_https | not_html | http_error | error - what the last ask
--                 did; NULL: never asked. robots_no_answer (robots.txt timed
--                 out or gave a 5xx) is retried; robots_refused is final.
--                 A failed read is never mistaken for a page with no picture
--   preview_attempts  how many times the article has been asked
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
  feed_summary      text,
  feed_summary_source text,
  author            text,
  categories        text[] NOT NULL DEFAULT '{}',
  image_url         text,
  image_source      text,
  preview_checked_at timestamptz,
  preview_outcome   text,
  preview_attempts  integer NOT NULL DEFAULT 0,
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
  CONSTRAINT news_item_summary_has_source_ck CHECK ((summary IS NULL) = (summary_source IS NULL)),
  CONSTRAINT news_item_feed_summary_source_ck CHECK (feed_summary_source IN ('feed', 'feed_content')),
  CONSTRAINT news_item_feed_summary_has_source_ck
    CHECK ((feed_summary IS NULL) = (feed_summary_source IS NULL)),
  CONSTRAINT news_item_preview_outcome_ck CHECK (preview_outcome IN
    ('found', 'none', 'robots_refused', 'robots_no_answer', 'not_https', 'not_html',
     'http_error', 'error')),
  CONSTRAINT news_item_preview_attempts_ck CHECK (preview_attempts >= 0)
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
