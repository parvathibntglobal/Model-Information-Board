-- Official developer sources and a video index, for the Guides (phase A).
-- 2026-10-30, PROPOSED. contract/official_sources.yaml.
--
-- The providers' own cookbooks, their Python SDKs' releases and changelogs,
-- OpenAI's API spec, and PyVideo's index of recorded talks - all read through
-- the GitHub REST API. NOTHING HERE IS EVIDENCE: no claim, quote or board entry
-- is made from these rows, and no model call reads or writes them.
--
-- WHO WRITES: collect/official/harvest.py:harvest, from
-- `python -m collect.cli official harvest` (by hand; no schedule yet).
-- WHO READS: nothing yet. The intended reader is phase B's writing packs, which
-- turn these into developer guides; contract/column_states.yaml says so per
-- column (rule 9). The harvest itself reads path, blob_sha, unlisted_at,
-- pyvideo_id and raw_ref back to decide what to fetch.
--
-- official_doc, ONE ROW PER FILE: a cookbook notebook or markdown file, an
-- SDK's changelog, or the API spec. Inserted once, then UPDATED IN PLACE when
-- the file's blob sha changes (the previous bytes stay in the raw store under
-- their own hash), and marked when a listing no longer has it.
--   id            stable id: repository key + path
--   repo_key      contract/official_sources.yaml `repos[].key`
--   provider      openai | anthropic | google | mistral
--   doc_kind      cookbook | changelog | spec
--   path          the file's path in the repository
--   format        the file's extension, lowercase (ipynb, md, yaml); `none`
--                 when it has none
--   blob_sha      git's sha of the file as last fetched. A listing with the
--                 same sha is not fetched again
--   size_bytes    the fetched file's size
--   licence       the repository's SPDX licence, as the contract names it and
--                 GitHub confirmed on the run that fetched the file
--   html_url      the file on github.com - the attribution link
--   title         the file's first level-one heading, or its file name when it
--                 has none (title_source says which; rule 6)
--   title_source  h1 | file_name
--   raw_ref       raw store ref of the file's bytes
--   text_ref      the text a writing pack reads: the flattened notebook
--                 (markdown cells as text, code cells fenced, outputs dropped;
--                 raw store `flattened/`) for ipynb, the file itself for md.
--                 NULL for a spec, which is not prose, and for a notebook that
--                 could not be read as one (its raw bytes are still kept)
--   first_seen_at when it was first stored
--   changed_at    when its stored bytes last changed (= first_seen_at until then)
--   unlisted_at   set when a complete listing no longer has the file in scope
--                 (deleted upstream, or excluded since); NULL while listed.
--                 Never deleted: what was read stays readable
--   pipeline_version  the code that wrote it
--
-- official_release, ONE ROW PER SDK RELEASE, from the releases API. Read on
-- every run and rewritten only when GitHub's record of it changed.
--   id            stable id: repository key + tag
--   repo_key, provider  as above
--   tag           the release's tag
--   name          its title; NULL when it has none (the tag stands alone)
--   published_at  GitHub's publish date; NULL when it gives none - never the
--                 time we read it (rule 6)
--   html_url      the release page
--   prerelease    as GitHub marks it
--   raw_ref       raw store ref of the release record as GitHub gave it (one
--                 object from the releases API, JSON with sorted keys); the
--                 notes are its `body`, which may be empty
--   first_seen_at, changed_at, pipeline_version  as above
--
-- video_ref, ONE ROW PER TALK in PyVideo's index (pyvideo/data, CC0), for
-- events whose folder name carries a year at or after `min_event_year`. A
-- talk PyVideo's NO_PUBLISH.json lists is never stored, and one stored before
-- it was listed is deleted (its stored bytes tombstoned). Nothing is fetched
-- from YouTube or Vimeo; links are stored as PyVideo gives them.
--   id            stable id: the record's path
--   path          `<event>/videos/<slug>.json`
--   blob_sha      as official_doc
--   event         the event's folder name ("pycon-us-2024")
--   event_year    the year in that name
--   pyvideo_id    the record's own `id`; NULL when it gives none (most recent
--                 records do not). NO_PUBLISH.json lists these ids
--   title         as given
--   recorded      the date it was recorded; NULL when not given
--   speakers      as given; empty when none
--   description   as given (reStructuredText or plain text); NULL when none
--   video_urls    every video link the record gives, in its order; empty when
--                 it gives none
--   video_hosts   youtube | vimeo | other for each link, same order, derived
--                 from the link's domain (contract `video_hosts`)
--   thumbnail_url as given; NULL when not given. Never fetched
--   duration_seconds  as given; NULL when not given
--   language      ISO 639-3 code as given; NULL when not given
--   copyright_text  the video's own licence as given ("CC BY"); NULL when not
--   llm_terms     the contract's `llm_terms` found in title or description.
--                 A WEIGHT for later ranking, never a gate: a talk with none is
--                 stored like any other (rule 8)
--   raw_ref       raw store ref of the record
--   first_seen_at, changed_at, unlisted_at, pipeline_version  as official_doc
--
-- official_fetch, ONE ROW PER SOURCE PER RUN: what each read did, and every
-- file it did not fetch, by reason. A count that does not apply to the source
-- (releases for a cookbook, talks for a repository) is NULL, never 0.
--   run_id        one harvest run
--   source_key    contract `repos[].key` or `pyvideo.key`
--   fetched_at    when the source's read began
--   outcome       ok | partial | licence_mismatch | rate_limited | http_error |
--                 error. partial: something was deferred, too large, failed,
--                 or a listing or the releases were cut short - detail says what
--   http_status   the status that stopped the read; NULL otherwise
--   detail        every reason the outcome is not ok; NULL for ok
--   files_listed  files the listing had in scope (after the globs, or the
--                 event year for PyVideo)
--   files_unchanged  in scope with the same sha as stored: not fetched
--   files_fetched    fetched this run
--   files_new        stored for the first time
--   files_changed    stored before, now with different bytes
--   files_deferred   left for a later run by max_blob_fetches_per_run, or by
--                    the run stopping
--   files_too_large  larger than max_blob_bytes: not fetched
--   files_failed     fetched or parsed and refused (a wrong sha, a record that
--                    is not a talk)
--   files_unlisted   stored, and no longer in a complete listing
--   talks_no_year           PyVideo only: talks in events whose name has no year
--   talks_before_min_year   PyVideo only: talks in events before min_event_year
--   talks_withheld          PyVideo only: fetched, on NO_PUBLISH.json, not stored
--   talks_withdrawn         PyVideo only: stored before, now on NO_PUBLISH.json,
--                           deleted
--   releases_seen    SDKs only: releases read (drafts are never listed to us)
--   releases_new     SDKs only: stored for the first time
--   releases_changed SDKs only: GitHub's record of it changed
--   api_calls        requests this source's read made
--   rate_remaining   GitHub's x-ratelimit-remaining after it; NULL when no
--                    response carried one

CREATE TABLE official_doc (
  id                text PRIMARY KEY,
  repo_key          text NOT NULL,
  provider          text NOT NULL,
  doc_kind          text NOT NULL,
  path              text NOT NULL,
  format            text NOT NULL,
  blob_sha          text NOT NULL,
  size_bytes        integer NOT NULL,
  licence           text NOT NULL,
  html_url          text NOT NULL,
  title             text NOT NULL,
  title_source      text NOT NULL,
  raw_ref           text NOT NULL,
  text_ref          text,
  first_seen_at     timestamptz NOT NULL,
  changed_at        timestamptz NOT NULL,
  unlisted_at       timestamptz,
  pipeline_version  text NOT NULL,
  CONSTRAINT official_doc_path_uq UNIQUE (repo_key, path),
  CONSTRAINT official_doc_kind_ck CHECK (doc_kind IN ('cookbook', 'changelog', 'spec')),
  CONSTRAINT official_doc_provider_ck
    CHECK (provider IN ('openai', 'anthropic', 'google', 'mistral')),
  CONSTRAINT official_doc_title_source_ck CHECK (title_source IN ('h1', 'file_name')),
  CONSTRAINT official_doc_size_ck CHECK (size_bytes >= 0),
  CONSTRAINT official_doc_spec_has_no_text_ck CHECK (doc_kind <> 'spec' OR text_ref IS NULL)
);
CREATE INDEX official_doc_repo_idx ON official_doc (repo_key, doc_kind);

CREATE TABLE official_release (
  id                text PRIMARY KEY,
  repo_key          text NOT NULL,
  provider          text NOT NULL,
  tag               text NOT NULL,
  name              text,
  published_at      timestamptz,
  html_url          text NOT NULL,
  prerelease        boolean NOT NULL,
  raw_ref           text NOT NULL,
  first_seen_at     timestamptz NOT NULL,
  changed_at        timestamptz NOT NULL,
  pipeline_version  text NOT NULL,
  CONSTRAINT official_release_tag_uq UNIQUE (repo_key, tag),
  CONSTRAINT official_release_provider_ck
    CHECK (provider IN ('openai', 'anthropic', 'google', 'mistral'))
);
CREATE INDEX official_release_published_idx ON official_release (repo_key, published_at DESC);

CREATE TABLE video_ref (
  id                text PRIMARY KEY,
  path              text NOT NULL UNIQUE,
  blob_sha          text NOT NULL,
  event             text NOT NULL,
  event_year        integer NOT NULL,
  pyvideo_id        bigint,
  title             text NOT NULL,
  recorded          date,
  speakers          text[] NOT NULL DEFAULT '{}',
  description       text,
  video_urls        text[] NOT NULL DEFAULT '{}',
  video_hosts       text[] NOT NULL DEFAULT '{}',
  thumbnail_url     text,
  duration_seconds  integer,
  language          text,
  copyright_text    text,
  llm_terms         text[] NOT NULL DEFAULT '{}',
  raw_ref           text NOT NULL,
  first_seen_at     timestamptz NOT NULL,
  changed_at        timestamptz NOT NULL,
  unlisted_at       timestamptz,
  pipeline_version  text NOT NULL,
  CONSTRAINT video_ref_hosts_match_urls_ck
    CHECK (cardinality(video_urls) = cardinality(video_hosts)),
  CONSTRAINT video_ref_duration_ck CHECK (duration_seconds IS NULL OR duration_seconds >= 0)
);
CREATE INDEX video_ref_event_idx ON video_ref (event_year DESC, event);

CREATE TABLE official_fetch (
  run_id                 text NOT NULL,
  source_key             text NOT NULL,
  fetched_at             timestamptz NOT NULL,
  outcome                text NOT NULL,
  http_status            integer,
  detail                 text,
  files_listed           integer NOT NULL,
  files_unchanged        integer NOT NULL,
  files_fetched          integer NOT NULL,
  files_new              integer NOT NULL,
  files_changed          integer NOT NULL,
  files_deferred         integer NOT NULL,
  files_too_large        integer NOT NULL,
  files_failed           integer NOT NULL,
  files_unlisted         integer NOT NULL,
  talks_no_year          integer,
  talks_before_min_year  integer,
  talks_withheld         integer,
  talks_withdrawn        integer,
  releases_seen          integer,
  releases_new           integer,
  releases_changed       integer,
  api_calls              integer NOT NULL,
  rate_remaining         integer,
  PRIMARY KEY (run_id, source_key),
  CONSTRAINT official_fetch_outcome_ck CHECK (outcome IN
    ('ok', 'partial', 'licence_mismatch', 'rate_limited', 'http_error', 'error')),
  CONSTRAINT official_fetch_detail_ck CHECK ((outcome = 'ok') = (detail IS NULL))
);
CREATE INDEX official_fetch_source_idx ON official_fetch (source_key, fetched_at DESC);
