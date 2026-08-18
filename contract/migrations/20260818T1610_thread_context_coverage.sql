-- #54: the four `thread_context` coverage columns. Ruled 2026-08-18.
--
-- Unblocks E3. `assemble_thread` refuses today because a selection that cannot
-- state what it saw would write "the top 5 children" when it means "the top 5
-- of the 4% we happened to fetch".
--
-- THE THIRD MIGRATION, AND THE FIRST WITH A GENERATED COLUMN. 20260818T1400
-- created a table that did not exist; 20260818T1520 altered a constraint;
-- this adds columns including one Postgres computes. Nothing else in the
-- schema uses GENERATED ALWAYS, so the equivalence test carries a shape it
-- has never compared - see tests/test_migrations.py.
--
-- Full reasoning per column is in contract/tables.sql. This is the delta.

ALTER TABLE thread_context ADD COLUMN observed_children       int;
ALTER TABLE thread_context ADD COLUMN hidden_children_min     int;
ALTER TABLE thread_context ADD COLUMN hidden_branches_unsized int;

-- An UPPER BOUND on coverage: hidden_children_min is a floor, so the
-- denominator is understated. GENERATED so it cannot drift from its inputs -
-- the fifth instance of a derived value stored beside what it derives from.
-- CASE with no ELSE, so an empty tree is NULL rather than 1.0.
ALTER TABLE thread_context ADD COLUMN coverage_ratio real GENERATED ALWAYS AS (
  CASE WHEN COALESCE(observed_children, 0) + COALESCE(hidden_children_min, 0) > 0
       THEN observed_children::real / (observed_children + hidden_children_min)
  END
) STORED;
