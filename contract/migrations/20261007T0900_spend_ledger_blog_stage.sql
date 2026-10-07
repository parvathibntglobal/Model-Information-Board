-- The spend ledger accepts the blog generator's calls: stage 'blog'.
--
-- WHY. Rule 2 names the blog generator (`generate_sample_blogs.py`) as a third
-- model caller (CLAUDE.md, agreed 2026-10-06), and its GPT-6 Luna spend was
-- visible only per Admin-started run (`blog_generation_run`) - a run started
-- from a terminal was not recorded anywhere. Every blog model call now writes a
-- ledger row, so Admin -> API usage can show it by month beside extraction.
--
-- OUTSIDE THE DAILY CAP. `EXTRACTION_DAILY_BUDGET_USD` covers 'extract' and
-- 'ask' only (judge/spend_ledger.py STAGES); a blog run must never spend the
-- extraction budget. That is enforced in code, where the cap is computed - this
-- file only widens the set of stages the table accepts.
--
-- A blog row's usd is what OpenRouter REPORTED for the call. A call with no
-- reported cost is `unpriced` with usd 0, as for any model without a rate.
--
-- Nothing existing changes: every row already holds 'extract' or 'ask'.

ALTER TABLE spend_ledger DROP CONSTRAINT spend_ledger_stage_ck;

ALTER TABLE spend_ledger
  ADD CONSTRAINT spend_ledger_stage_ck CHECK (stage IN ('extract', 'ask', 'blog'));
