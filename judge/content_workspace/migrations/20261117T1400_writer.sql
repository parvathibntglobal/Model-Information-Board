-- Content workspace phase 2: the AI writer for platforms that allow one
-- (cw_platform.ai_writer_allowed: X and LinkedIn). One row per model call.
-- The model PROPOSES text; code checks it; a person chooses whether to use it
-- and edits it. Spend lives here, not in the board's spend_ledger.

CREATE TABLE cw_writer_run (
    id            bigserial PRIMARY KEY,
    draft_id      bigint NOT NULL REFERENCES cw_draft (id),
    platform_key  text NOT NULL REFERENCES cw_platform (key),
    format        text NOT NULL,
    instructions  text,
    model_asked   text NOT NULL,
    model_served  text,
    input_tokens  integer,
    output_tokens integer,
    -- As OpenRouter reported it. NULL = not reported, never zero (rule 6).
    cost_usd      numeric(16, 10),
    -- proposed: passed the code checks. refused: failed them (reasons says
    -- which). failed: no usable answer (an error, a substituted model).
    state         text NOT NULL CHECK (state IN ('proposed', 'refused', 'failed')),
    reasons       jsonb NOT NULL DEFAULT '[]'::jsonb,
    proposal      jsonb,
    fit           jsonb,
    prompt_sha    text NOT NULL,
    requested_by  text,
    created_at    timestamptz NOT NULL DEFAULT now(),
    used_at       timestamptz,
    used_by       text,
    -- The draft's title and text before this proposal replaced them.
    replaced      jsonb
);

CREATE INDEX cw_writer_run_draft_idx ON cw_writer_run (draft_id, created_at DESC);
CREATE INDEX cw_writer_run_day_idx ON cw_writer_run (created_at);
