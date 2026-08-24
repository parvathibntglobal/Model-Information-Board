-- `harvest_run` gains a verdict, issue #5's two page counts, and the sieve's
-- yield - plus the constraint that makes a half-written row accurate.
--
-- ORDER MATTERS IN ONE PLACE. `harvest_run_finish_ck` is added AFTER the
-- outcome column exists and BEFORE anything writes, because the constraint's
-- whole point is to reject an update that sets finished_at without a verdict:
-- `collect/ops/ledger.py:close_harvest_run` sets both in one statement, and it
-- had to change in the same commit or every close would be refused.
--
-- FREE TO ADD VALIDATED, AND THAT IS A FACT ABOUT TODAY: harvest_run holds 0
-- rows, because its writer landed this week and has never run. On a table with
-- closed rows the finish constraint would need NOT VALID and a repair pass, and
-- this comment exists so nobody reads "validated" as a property of the change.

ALTER TABLE harvest_run ADD COLUMN outcome         text;
ALTER TABLE harvest_run ADD COLUMN pages_fetched   int;
ALTER TABLE harvest_run ADD COLUMN pages_stored    int;
ALTER TABLE harvest_run ADD COLUMN sieve_pass_rate real;

ALTER TABLE harvest_run ADD CONSTRAINT harvest_run_outcome_ck
  CHECK (outcome IS NULL OR outcome IN ('ok', 'refused', 'error'));

ALTER TABLE harvest_run ADD CONSTRAINT harvest_run_finish_ck
  CHECK ((finished_at IS NULL) = (outcome IS NULL));
