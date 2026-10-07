-- The shared raw store, in the shared database: one row per raw payload.
--
-- WHY. Raw payloads (the full text of every harvested thread and post) were
-- files on the machine that fetched them; the database holds only their refs.
-- The nightly fetch runs on a fresh GitHub runner, so it could read none of
-- them - the first scheduled run read 0 of 6,087 unread threads. A shared
-- object store was planned (collect/rawstore_remote.py S3Blobs), but it needs an
-- external storage account the team does not have. This table is the store
-- with no new service: every machine and the runner already reach this
-- database. Chosen by Anooj, 2026-10-07.
--
-- SIZE, MEASURED 2026-10-07: one machine's store is 33,842 files, 731 MB, all
-- uncompressed JSON text. zlib at level 6 measured 4.2x on 600 random files, so
-- about 175 MB here, against a 52 MB database. It grows with every fetch.
--
-- WHAT A ROW IS
--   key        the payload's ref, verbatim (`raw/sha256/ab/cd/<hash>`), or the
--              ref plus `.tombstone` for a takedown marker - the same keys the
--              S3 store uses, so either store reads like the folder it mirrors
--   data       zlib-compressed bytes
--   size       the UNCOMPRESSED length, which is what RawStore.stat reports
-- Content addressing makes every write idempotent: a key present means the same
-- bytes, so writers use ON CONFLICT DO NOTHING.
--
-- WHO WRITES: collect/rawstore_remote.py PgBlobs, behind RawStore, when
-- RAW_STORE_REMOTE=postgres; and scripts/sync_raw_store.py, which sends a
-- machine's existing files once.

CREATE TABLE raw_blob (
  key        text PRIMARY KEY,
  data       bytea NOT NULL,
  size       bigint NOT NULL,
  stored_at  timestamptz NOT NULL DEFAULT now()
);
