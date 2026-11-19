-- Content workspace phase 3: what a posted draft did, as the platform's own
-- analytics showed it. One row per observation: a later reading is a new row,
-- so the log keeps how a number moved. A metric nobody recorded has no row
-- and reads as "not recorded", never as zero.

CREATE TABLE cw_result (
    id          bigserial PRIMARY KEY,
    draft_id    bigint NOT NULL REFERENCES cw_draft (id),
    metric      text NOT NULL,
    value       bigint NOT NULL CHECK (value >= 0),
    -- When the platform showed this number (it keeps changing after posting).
    observed_at timestamptz NOT NULL,
    -- Where the person read it ("LinkedIn post analytics", "YouTube Studio").
    source      text NOT NULL CHECK (btrim(source) <> ''),
    note        text,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    recorded_by text
);

CREATE INDEX cw_result_draft_idx ON cw_result (draft_id, metric, observed_at DESC);
