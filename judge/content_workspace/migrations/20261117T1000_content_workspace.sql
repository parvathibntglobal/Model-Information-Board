-- Content workspace: platforms, editable notes, drafts and their fit checks.
--
-- Lives in the workspace's OWN database (CONTENT_WORKSPACE_DATABASE_URL),
-- never in the board's: these rows are not evidence and nothing on the board
-- reads them. Applied by `python -m judge.content_workspace setup`, which
-- runs each file in its own transaction and records it in
-- cw_schema_migration. No BEGIN/COMMIT here: the runner owns the transaction.

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
    id           bigserial PRIMARY KEY,
    platform_key text NOT NULL REFERENCES cw_platform (key),
    format       text NOT NULL,
    topic_kind   text,
    title        text,
    body         text NOT NULL DEFAULT '',
    tags         text[] NOT NULL DEFAULT '{}',
    -- The suggestion the draft started from: its evidence and board links.
    suggestion   jsonb,
    -- A person says whether an AI drafted any of it. Only X and LinkedIn
    -- allow that; elsewhere the platform's rules decide what it means.
    ai_assisted  boolean NOT NULL DEFAULT false,
    status       text NOT NULL DEFAULT 'draft'
                 CHECK (status IN ('draft', 'ready', 'posted', 'dropped')),
    posted_url   text,
    posted_at    timestamptz,
    created_at   timestamptz NOT NULL DEFAULT now(),
    created_by   text,
    updated_at   timestamptz NOT NULL DEFAULT now(),
    updated_by   text
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
