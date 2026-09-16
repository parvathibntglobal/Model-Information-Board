-- Quota gets a history. The latest row stays exactly as it is.
--
-- WHAT WAS WRONG. `rapidapi_quota` is keyed `meter text PRIMARY KEY` and its
-- writer is an upsert, so every reading REPLACES its predecessor. Two rows have
-- ever existed - one per meter - and nothing anywhere retains a past reading.
-- The panel can therefore show "150 requests spent" and cannot answer "what did
-- we spend this month" or "how fast are we consuming", because each reading
-- destroys the evidence for both.
--
-- ⚠ THIS DOES NOT REPLACE THAT TABLE, AND THE REASON IS LOAD-BEARING.
--   `rapidapi_quota`'s value is the merge condition
--   `where excluded.read_at > rapidapi_quota.read_at`: two machines racing a
--   DECREASING counter will have the later WRITE carry the older READING, and
--   that clause is what stops the shared number walking backwards. Deriving
--   "latest" from this table with ORDER BY read_at DESC LIMIT 1 would get the
--   same answer while moving the guarantee out of SQL and into every reader.
--   #330 then added `subscriptions_differ` on top of that same comparison.
--
--   They also have OPPOSITE failure modes. The latest row must never grow;
--   a history must never lose a row. One `do update`, one `do nothing`. Both
--   behaviours in one relation means every reader must filter, and a reader
--   that forgets renders a month of readings under a heading meaning "now".
--
-- EVERY READING, NOT ONLY CHANGES. A suppressed row cannot be recovered and a
-- duplicate can be collapsed by whoever reads it. "The counter did not move
-- across 40 calls" is the consumption signal, not noise to filter at write time.
--
-- ── WHY `observed_at` EXISTS, WHICH IS A DEVIATION FROM spend_ledger ────────
--
-- `spend_ledger` hashes its caller-supplied `at`. `collect/usage.py:_now()` is
-- SECOND resolution ("%Y-%m-%dT%H:%M:%SZ"), so under that scheme two calls in
-- the same second carrying the same figures produce the same id and the second
-- one is silently dropped by `on conflict do nothing`.
--
-- That is not a rare edge. It is EXACTLY the case this table exists to record:
-- the counter not moving between two calls. The one row we would lose is the
-- one carrying the signal.
--
-- So `read_at` stays what the arm read (second resolution, identical to
-- `rapidapi_quota.read_at`, so the two tables agree and can be compared), and
-- `observed_at` records when THIS call recorded it, at microsecond precision.
-- The id hashes `observed_at`, so two real calls are two rows and a replay of
-- one already-built record is one row.
--
-- Raising `_now()` to microseconds would have done the same job and was not
-- taken: it feeds `rapidapi_quota.read_at` and the file, both on the merge path
-- #330 has just changed, and a wider blast radius to save a column is a bad
-- trade for a table whose whole purpose is to not lose rows.

CREATE TABLE IF NOT EXISTS rapidapi_quota_reading (
  -- sha256 of meter|machine|run|observed_at|remaining|limit|reset|fingerprint.
  -- Deterministic, so a replay is a no-op. MACHINE AND RUN ARE IN THE HASH for
  -- spend_ledger's reason: two hosts can read the same counter in the same
  -- instant and those are two real observations of a shared subscription.
  id                  text PRIMARY KEY,

  -- Which meter. NOT a foreign key to rapidapi_quota: that table holds only the
  -- latest row per meter and may be pruned or rebuilt, and a history that can be
  -- deleted by tidying the thing it is the history OF is not a history.
  meter               text NOT NULL,

  quota_remaining     bigint,
  quota_limit         bigint,

  -- Seconds remaining until this meter's window resets, as read. Carried from
  -- the first row so the series can date window BOUNDARIES without a backfill -
  -- a backfill could not supply it anyway, since the header was never stored.
  quota_reset_seconds bigint,

  -- WHAT THE ARM READ. Second resolution, same value as rapidapi_quota.read_at.
  read_at             timestamptz NOT NULL,

  -- WHEN THIS CALL RECORDED IT. Microseconds. See the header: this is what makes
  -- two same-second readings two rows.
  observed_at         timestamptz NOT NULL,

  read_by             text NOT NULL,
  source_run_id       text,
  machine             text NOT NULL,

  -- WHICH SUBSCRIPTION. Without it a series spanning a key change reads as one
  -- counter that jumped, which is a wrong finding rather than a missing one.
  -- NULL is "not recorded" and never "a different account" (rule 6), same
  -- reading as 20260916T0930's column.
  key_fingerprint     text,

  recorded_at         timestamptz NOT NULL DEFAULT now(),

  -- Same refusal as the latest-row table and as collect/usage.py: a reading with
  -- neither figure is not a reading, and "no header" must never become "zero".
  CONSTRAINT rapidapi_quota_reading_has_a_figure_ck
    CHECK (quota_remaining IS NOT NULL OR quota_limit IS NOT NULL)
);

-- The series is always read per meter and in time order. Both questions this
-- table exists for - consumption rate, and where a window boundary falls - are
-- that scan.
CREATE INDEX IF NOT EXISTS rapidapi_quota_reading_meter_read_at_idx
  ON rapidapi_quota_reading (meter, read_at);

COMMENT ON TABLE rapidapi_quota_reading IS
  'Append-only history of RapidAPI quota header readings, one row per metered '
  'call. rapidapi_quota holds the latest row per meter and keeps its '
  'newest-reading-wins merge; this never updates and never deletes.';

COMMENT ON COLUMN rapidapi_quota_reading.observed_at IS
  'When this call recorded the reading, microsecond precision. Distinct from '
  'read_at, which is second resolution: two calls in one second that read the '
  'same figures must be two rows, because an unmoved counter is the signal.';
