-- kp_outreach_spend: every paid model call outreach makes, one row per call.
--
-- Decided 2026-11-09 (ARCHITECTURE.md decision #10): outreach records its spend
-- in ITS OWN database, not in MIB's spend_ledger. The daily cap
-- (OUTREACH_DAILY_BUDGET_USD) is checked against this table before each call.
-- Cost: this spend does not appear in MIB's Admin -> API usage.
--
-- Readers (rule 9), by column:
--   at, usd                      common/spend.py today() - the daily cap
--   step, model, input_tokens,
--   output_tokens, usd, machine  common/spend.py by_day() - spend_report.py
--   thread_id                    DECLARED UNREAD: intended reader is the review
--                                screen, showing what a thread's draft cost. Not
--                                rendered until the draft view exists.
--
-- usd is what OpenRouter REPORTED for the call. NULL means it reported no
-- cost: never 0, because an unpriced call is not a free one (rule 6). A day
-- holding one is a floor, and today() says so.

CREATE TABLE kp_outreach_spend (
  id               bigserial PRIMARY KEY,
  at               timestamptz NOT NULL DEFAULT now(),
  step             text NOT NULL,
  model            text NOT NULL,
  thread_id        bigint REFERENCES kp_outreach_thread (id),
  input_tokens     integer,
  output_tokens    integer,
  usd              numeric(12, 8),
  machine          text NOT NULL,
  CONSTRAINT kp_outreach_spend_step_ck CHECK (step IN ('shortlist', 'draft')),
  CONSTRAINT kp_outreach_spend_usd_ck CHECK (usd IS NULL OR usd >= 0),
  CONSTRAINT kp_outreach_spend_tokens_ck
    CHECK ((input_tokens IS NULL OR input_tokens >= 0)
       AND (output_tokens IS NULL OR output_tokens >= 0))
);

CREATE INDEX kp_outreach_spend_at_idx ON kp_outreach_spend (at);
