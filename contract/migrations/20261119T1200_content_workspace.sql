-- The content workspace (Admin -> Content workspace, /admin/content), moved into
-- the board's database (anooj, 2026-11-19). Platforms, editable notes and their
-- edit history, drafts, fit-check runs, AI-writer runs, results, hand-check
-- ticks and media files.
--
-- These rows are NOT evidence: nothing on the board's pages or pipeline reads a
-- cw_* table, and no cw_* table references a board table. Signed-in only.
--
-- The final shape of the five files that built the workspace's own database
-- from 2026-11-17 (content_workspace, writer, first_comment, results,
-- ticks_and_media), minus that database's own ledger, which the board's
-- schema_migration replaces. No BEGIN/COMMIT: the runner owns the transaction
-- (collect/migrate.py).

CREATE TABLE cw_platform (
    key               text PRIMARY KEY,
    name              text NOT NULL,
    sort_order        integer NOT NULL,
    formats           text[] NOT NULL,
    topic_kinds       text[] NOT NULL,
    video_creation    boolean NOT NULL,
    ai_writer_allowed boolean NOT NULL,
    researched        boolean NOT NULL,
    seeded_at         timestamptz NOT NULL DEFAULT now()
);

-- One philosophy point, research finding, rule or recommendation.
-- platform_key NULL: applies to every platform.
CREATE TABLE cw_note (
    id           bigserial PRIMARY KEY,
    platform_key text REFERENCES cw_platform (key),
    section      text NOT NULL
                 CHECK (section IN ('philosophy', 'research', 'rule', 'recommendation')),
    seed_key     text UNIQUE,
    topic        text,
    source       text NOT NULL,
    source_type  text,
    body         text NOT NULL CHECK (btrim(body) <> ''),
    -- Rules only: which coded check tests it, how a miss is shown, its
    -- parameters (limits) and the formats it applies to (NULL = all).
    check_id     text,
    severity     text CHECK (severity IN ('fail', 'warn', 'manual')),
    params       jsonb NOT NULL DEFAULT '{}'::jsonb,
    formats      text[],
    sort_order   integer NOT NULL DEFAULT 0,
    archived     boolean NOT NULL DEFAULT false,
    created_at   timestamptz NOT NULL DEFAULT now(),
    created_by   text,
    updated_at   timestamptz NOT NULL DEFAULT now(),
    updated_by   text,
    CONSTRAINT cw_note_rule_fields_ck CHECK (
        (section = 'rule' AND check_id IS NOT NULL AND severity IS NOT NULL)
        OR (section <> 'rule' AND check_id IS NULL AND severity IS NULL)
    )
);

CREATE INDEX cw_note_platform_idx ON cw_note (platform_key, section);

-- Every edit keeps what the note said before it.
CREATE TABLE cw_note_edit (
    id        bigserial PRIMARY KEY,
    note_id   bigint NOT NULL REFERENCES cw_note (id),
    before    jsonb NOT NULL,
    after     jsonb NOT NULL,
    edited_at timestamptz NOT NULL DEFAULT now(),
    edited_by text
);

CREATE TABLE cw_draft (
    id            bigserial PRIMARY KEY,
    platform_key  text NOT NULL REFERENCES cw_platform (key),
    format        text NOT NULL,
    topic_kind    text,
    title         text,
    body          text NOT NULL DEFAULT '',
    tags          text[] NOT NULL DEFAULT '{}',
    -- The suggestion the draft started from: its evidence and board links.
    suggestion    jsonb,
    -- A person says whether an AI drafted any of it. Only X and LinkedIn
    -- allow that; elsewhere the platform's rules decide what it means.
    ai_assisted   boolean NOT NULL DEFAULT false,
    status        text NOT NULL DEFAULT 'draft'
                  CHECK (status IN ('draft', 'ready', 'posted', 'dropped')),
    posted_url    text,
    posted_at     timestamptz,
    created_at    timestamptz NOT NULL DEFAULT now(),
    created_by    text,
    updated_at    timestamptz NOT NULL DEFAULT now(),
    updated_by    text,
    -- The first comment (LinkedIn) or reply (X) that goes with a post: where
    -- the link to the model page lives when the platform's rules keep links
    -- out of the post itself. Checked with the post for links, handles, quotes.
    first_comment text
);

CREATE INDEX cw_draft_platform_idx ON cw_draft (platform_key, status);

-- One run of the platform fit check over one version of a draft.
CREATE TABLE cw_check_run (
    id          bigserial PRIMARY KEY,
    draft_id    bigint NOT NULL REFERENCES cw_draft (id),
    ran_at      timestamptz NOT NULL DEFAULT now(),
    ran_by      text,
    content_sha text NOT NULL,
    results     jsonb NOT NULL,
    counts      jsonb NOT NULL
);

CREATE INDEX cw_check_run_draft_idx ON cw_check_run (draft_id, ran_at DESC);

-- The AI writer for platforms that allow one (cw_platform.ai_writer_allowed:
-- X and LinkedIn). One row per model call. The model PROPOSES text; code
-- checks it; a person chooses whether to use it and edits it. Spend lives
-- here, not in spend_ledger (CLAUDE.md rule 2, the writer's entry).
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

-- What a posted draft did, as the platform's own analytics showed it. One row
-- per observation: a later reading is a new row, so the log keeps how a number
-- moved. A metric nobody recorded has no row and reads as "not recorded",
-- never as zero.
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

-- A person's tick (or untick) of a hand-checked rule on a draft. Append-only:
-- the latest row per (draft, rule) is the state. `content_sha` is what the
-- draft said when it was ticked, so a tick made before an edit shows as such
-- instead of silently vouching for text nobody re-read.
CREATE TABLE cw_tick (
    id          bigserial PRIMARY KEY,
    draft_id    bigint NOT NULL REFERENCES cw_draft (id),
    note_id     bigint NOT NULL REFERENCES cw_note (id),
    ticked      boolean NOT NULL,
    content_sha text NOT NULL,
    at          timestamptz NOT NULL DEFAULT now(),
    by_whom     text
);

CREATE INDEX cw_tick_draft_idx ON cw_tick (draft_id, note_id, at DESC);

-- A media file made for a draft (a carousel PDF, a card or chart image), made
-- outside the page and stored here so the page can show and download it.
-- Internal: like everything in the workspace, served only to a signed-in person.
CREATE TABLE cw_media (
    id           bigserial PRIMARY KEY,
    draft_id     bigint NOT NULL REFERENCES cw_draft (id),
    kind         text NOT NULL CHECK (kind IN ('carousel_pdf', 'card_png', 'chart_png',
                                                'cover_png', 'other')),
    filename     text NOT NULL,
    content_type text NOT NULL CHECK (content_type IN ('application/pdf', 'image/png')),
    data         bytea NOT NULL,
    size_bytes   integer NOT NULL,
    width        integer,
    height       integer,
    pages        integer,
    -- How it was made, e.g. "claude-code: field report generator".
    made_with    text NOT NULL CHECK (btrim(made_with) <> ''),
    -- The draft's content when the file was made (store.content_sha), so a
    -- file made before the text changed shows as out of date.
    content_sha  text NOT NULL,
    note         text,
    created_at   timestamptz NOT NULL DEFAULT now(),
    created_by   text
);

CREATE INDEX cw_media_draft_idx ON cw_media (draft_id, created_at DESC);
