-- The one header that dates the window, kept instead of discarded.
--
-- WHAT WAS WRONG. Both adapters already PARSE `x-ratelimit-requests-reset` -
-- `collect/adapters/reddit.py` and `collect/adapters/x.py` both map it onto a
-- `quota_reset_seconds` field on their run object. `record_rapidapi_quota` took
-- `remaining` and `limit` and nothing else, so the value died with the process
-- on every metered call. It reached one X log line and no store.
--
-- Rule 9: a produced value has a named consumer or a declared reason it has
-- none. This one had neither. It was extracted, carried across a function
-- boundary, and dropped at the edge of persistence.
--
-- WHAT IT BUYS, AND IT IS A QUESTION THREE WEEKS OF HARVESTING COULD NOT
-- ANSWER. `docs/measurements/reddit-rate-and-quota.md` is explicit that one
-- reading cannot give the window LENGTH:
--
--   "23.893 days remaining is consistent with a 28-day window that began
--    2026-08-14 and with a 30-day window that began 2026-08-12."
--
-- The BOUNDARY is already dated. Two readings 23 days apart - 2026-08-18
-- (2,064,366s) and 2026-09-10 (102,225s) - both point at a reset of
-- 2026-09-11 09:45 UTC. That window has since rolled. So the next reading with
-- this column populated names the NEXT boundary, and boundary-to-boundary is
-- the period. One metered call we were going to make anyway.
--
-- This matters because the panel currently says "monthly" and nothing has
-- measured that. A sweep costed as a monthly share is costed against a period
-- nobody has established (rule 7).
--
-- SECONDS AS READ, NEVER A COMPUTED DATE. `tests/test_reddit_fetch.py` already
-- pins this on the adapter side - "seconds, not a computed date" - for the
-- reason this column inherits: a date has to be computed against a clock, and
-- the reading's worth comes from being the provider's own number. The
-- subtraction is the reader's to do, beside `read_at`, which is stored.
--
-- bigint, not integer. 2,064,366 fits in an int4 comfortably, but this is a
-- provider's opaque counter and a wider type costs nothing to choose now and a
-- migration to change later.
--
-- NULLABLE, AND NULL MEANS "NOT RECORDED". Every row written before today has
-- no reset value, and a response can legitimately carry -remaining without
-- -reset. Absent stays absent (rule 6); it is never a window of zero.

ALTER TABLE rapidapi_quota ADD COLUMN IF NOT EXISTS quota_reset_seconds bigint;

COMMENT ON COLUMN rapidapi_quota.quota_reset_seconds IS
  'x-ratelimit-requests-reset as read: SECONDS REMAINING until this meter''s '
  'window resets, never a computed date. Add it to read_at to get the boundary. '
  'NULL means the reading predates this column or carried no -reset header, '
  'which is "not recorded" and never "resets now".';
