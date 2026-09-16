-- WHOSE COUNTER, not whose machine.
--
-- `rapidapi_quota` is keyed on `meter` and carries `machine`, and the usage
-- panel led with the machine - so a quota drawn down by anybody signed in to
-- the hosted board rendered as though a laptop owned it. Parvathi: "this
-- project is hosted on railway then why api usage for reddit and x is shown
-- with local machine names ... anybody logged in can do the fetch run so rely
-- on api key usage and not machines".
--
-- The row identity was already right - one row per METER is what the table's
-- own comment insists on. What was missing is WHICH SUBSCRIPTION the meter
-- belongs to. Every reading merges into one row by recency, and nothing could
-- check they were readings of the same account:
--
--   * the board is hosted, so a run starts from any browser;
--   * `x.py:key_for` falls back X_RAPIDAPI_KEY then RAPIDAPI_KEY, so two hosts
--     with different env read DIFFERENT accounts on the same arm;
--   * the fresher of two unrelated counters simply wins, and the number moves
--     for no visible reason.
--
-- ⚠ A FINGERPRINT, NEVER THE KEY. `sha256(key)[:12]`, computed in
--   `collect/usage.py:key_fingerprint`. One-way, so it is safe in a shared
--   table and on a page, and it is comparable, which is the whole point.
--   `x.py:key_for` already established the shape by returning the VARIABLE NAME
--   rather than the value.
--
-- NULLABLE, AND NULL MEANS "NOT RECORDED". Every row written before today has
-- no fingerprint, and that must not read as "a different subscription" - which
-- is why the reader treats an absent fingerprint as unknown rather than as a
-- mismatch (rule 6).

ALTER TABLE rapidapi_quota ADD COLUMN IF NOT EXISTS key_fingerprint text;

COMMENT ON COLUMN rapidapi_quota.key_fingerprint IS
  'sha256(api key)[:12] - WHICH SUBSCRIPTION this counter belongs to. Never '
  'the key itself. NULL means the reading predates this column or was taken '
  'with no credential, which is "not recorded" and never "a different account".';
