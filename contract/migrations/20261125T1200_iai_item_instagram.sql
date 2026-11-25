-- INSTAGRAM AS AN INDUSTRY AI PLATFORM (anooj, 2026-11-25).
--
-- The observer reads named Instagram accounts (contract/industry_ai.yaml
-- `watch.instagram`, collect/adapters/instagram.py), so `iai_item` must accept
-- `platform = 'instagram'`. The only platform list in the Industry AI tables is
-- this CHECK: `iai_run.platforms` is an unconstrained array. Widened, never
-- narrowed: every existing row already satisfies the new list.
--
-- WHO RUNS THIS MIGRATION: the person who merges the PR that adds it, on the
-- shared database, straight after merge, with `db check` before and after, and
-- announces it on that PR the same day. Until it has run, a run that harvests
-- Instagram fails on the CHECK when it stores, so the observer stays off
-- (`watch.enabled: false`) until it has.
--
-- No transaction control here: the runner owns the transaction.

ALTER TABLE iai_item DROP CONSTRAINT IF EXISTS iai_item_platform_ck;
ALTER TABLE iai_item ADD CONSTRAINT iai_item_platform_ck
  CHECK (platform IN ('reddit', 'x', 'github', 'hackernews', 'devto', 'bluesky', 'feeds',
                      'instagram'));
