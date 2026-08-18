-- `job_run.outcome` takes the chain's vocabulary, not a second one.
--
-- 20260818T1400 wrote CHECK (outcome IN ('ok','refused','failed')) before
-- anybody looked at `collect/ops/chain.py`, which has used
--
--     OK = "ok"   ERROR = "error"   REFUSED = "refused"
--
-- since it was written. A writer bridging the two would have had to translate
-- `error` to `failed` on the way in and back on the way out — two vocabularies
-- for one concept, which is the drift this project keeps finding in prose and
-- would here have been in code.
--
-- The schema moves rather than the code: the chain's constants are the older
-- and more used of the two, and `error` is the more accurate word. A stage that
-- raised is not a stage that failed a check.
--
-- ALSO THE FIRST MIGRATION HERE THAT IS NOT A `CREATE TABLE`. 20260818T1400
-- proved the path works on an object that did not exist; this one alters an
-- object that does, which is the case the equivalence test could not reach
-- before either of them.

ALTER TABLE job_run DROP CONSTRAINT job_run_outcome_ck;

ALTER TABLE job_run ADD CONSTRAINT job_run_outcome_ck
  CHECK (outcome IS NULL OR outcome IN ('ok', 'refused', 'error'));
