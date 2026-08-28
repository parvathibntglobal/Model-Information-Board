-- capability_candidate — where a model-PROPOSED capability key lands.
--
-- Reviewed by E1 (design in for-engineer-2-capability-candidate.md); this adds
-- the four refinements agreed in review:
--   1. content-hash `id` + UNIQUE natural key + ON CONFLICT DO NOTHING at write,
--      so re-running the classifier is idempotent and cannot inflate the count
--      the table exists to produce.
--   2. the count is a floor (free-text keys fragment across phrasings) — noted
--      on the table and wherever the number is shown; clustering rides with the
--      8★ derivation.
--   3. `ruling_target` — what an adopted/merged candidate became, so the trail
--      does not end on the adopted row.
--   4. `quote` is the RAW span (verification step 3), what an admin rules on.
--
-- Deliberately unrelated to `capability` and `claim`: a proposal a claim could
-- be filed against is a vocabulary decision taken by an INSERT, and the
-- capability list is contract/capabilities.yaml's to change (rule 5). Adoption
-- is a PR against that file, never a flag flipped here.
--
-- Urgency: the classification pass had nowhere durable to land its proposals
-- (it writes a JSONL file, which cannot accumulate across runs). This table is
-- the accumulation store. Nothing writes it yet — the classifier's DB write is
-- the next wire-up — so every column is `reserved` in column_states.yaml until
-- that lands.

CREATE TABLE IF NOT EXISTS capability_candidate (
  id                text PRIMARY KEY,

  proposed_key      text NOT NULL,
  definition        text NOT NULL,

  document_id       text NOT NULL REFERENCES document(id),

  quote             text NOT NULL,
  quote_verified    boolean NOT NULL,

  proposer_model    text NOT NULL,
  prompt_label      text NOT NULL,
  pipeline_version  text NOT NULL,
  created_at        timestamptz NOT NULL DEFAULT now(),

  reviewed_at       timestamptz,
  ruling            text,
  ruling_target     text
);

ALTER TABLE capability_candidate
  DROP CONSTRAINT IF EXISTS capability_candidate_ruling_ck;
ALTER TABLE capability_candidate
  ADD CONSTRAINT capability_candidate_ruling_ck
  CHECK (ruling IS NULL OR ruling IN ('adopted', 'declined', 'merged'));

-- A ruling and its date travel together.
ALTER TABLE capability_candidate
  DROP CONSTRAINT IF EXISTS capability_candidate_reviewed_ck;
ALTER TABLE capability_candidate
  ADD CONSTRAINT capability_candidate_reviewed_ck
  CHECK ((ruling IS NULL) = (reviewed_at IS NULL));

-- A target exists exactly when the candidate became something.
ALTER TABLE capability_candidate
  DROP CONSTRAINT IF EXISTS capability_candidate_target_ck;
ALTER TABLE capability_candidate
  ADD CONSTRAINT capability_candidate_target_ck
  CHECK (
    CASE WHEN ruling IN ('adopted', 'merged') THEN ruling_target IS NOT NULL
         ELSE ruling_target IS NULL END
  );

-- Idempotency: one row per (document, key, prompt, version).
ALTER TABLE capability_candidate
  DROP CONSTRAINT IF EXISTS capability_candidate_natural_key;
ALTER TABLE capability_candidate
  ADD CONSTRAINT capability_candidate_natural_key
  UNIQUE (document_id, proposed_key, prompt_label, pipeline_version);

CREATE INDEX IF NOT EXISTS capability_candidate_key_idx
  ON capability_candidate (proposed_key);
