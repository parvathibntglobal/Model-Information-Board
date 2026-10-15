-- THE QUIZ'S QUESTION BANK, AND ITS SPEND STAGE (2026-10-15).
--
-- General questions about how language models work - the kind in Google's ML
-- Crash Course LLM quiz - DRAFTED by a model and APPROVED by a person, the
-- same shape as the blog: an LLM may propose, it may never decide. The daily
-- quiz draws only from `state = 'approved'`.
--
-- ⚠ A FOURTH CALLER UNDER RULE 2. The blog generator was agreed as the third
--   on 2026-10-06; this drafter is the same pattern (draft, then a person
--   approves) and needs the same agreement. Its spend is its own stage,
--   'quiz', recorded outside the daily extraction cap like 'blog', so it is
--   never mislabelled as extraction.
--
-- No transaction control here: the runner owns the transaction.

CREATE TABLE quiz_question (
  -- qq_ + sha256 of the normalised question text, so a re-draft of the same
  -- question is one row, not two.
  id              text PRIMARY KEY,
  topic           text NOT NULL,
  difficulty      text NOT NULL,
  question        text NOT NULL,
  -- Exactly four answer texts, in the order drafted. The page shuffles.
  options         jsonb NOT NULL,
  answer_index    integer NOT NULL,
  explanation     text NOT NULL,
  state           text NOT NULL DEFAULT 'pending',
  proposer_model  text NOT NULL,
  run_id          text NOT NULL,
  generated_at    timestamptz NOT NULL DEFAULT now(),
  reviewed_at     timestamptz,
  review_note     text,
  CONSTRAINT quiz_question_state_ck CHECK (state IN ('pending', 'approved', 'rejected')),
  CONSTRAINT quiz_question_difficulty_ck CHECK (difficulty IN ('easy', 'medium', 'hard')),
  CONSTRAINT quiz_question_options_ck
    CHECK (jsonb_typeof(options) = 'array' AND jsonb_array_length(options) = 4),
  CONSTRAINT quiz_question_answer_ck CHECK (answer_index BETWEEN 0 AND 3),
  -- A decision has a time; a pending question has none.
  CONSTRAINT quiz_question_reviewed_ck CHECK ((state = 'pending') = (reviewed_at IS NULL))
);

CREATE INDEX quiz_question_state_idx ON quiz_question (state);

ALTER TABLE spend_ledger DROP CONSTRAINT spend_ledger_stage_ck;
ALTER TABLE spend_ledger
  ADD CONSTRAINT spend_ledger_stage_ck CHECK (stage IN ('extract', 'ask', 'blog', 'quiz'));
