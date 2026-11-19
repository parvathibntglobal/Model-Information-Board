-- Content workspace: saved "check by hand" ticks, and media files per draft.

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

-- A media file made for a draft (a carousel PDF, a card or chart image),
-- made outside the page (in Claude Code, with the media skills) and stored
-- here so the page can show and download it. Internal: like everything in
-- the workspace, served only to a signed-in person.
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
    -- How it was made, e.g. "claude-code: dataviz + theme-factory (MIB theme)".
    made_with    text NOT NULL CHECK (btrim(made_with) <> ''),
    -- The draft's content when the file was made (store.content_sha), so a
    -- file made before the text changed shows as out of date.
    content_sha  text NOT NULL,
    note         text,
    created_at   timestamptz NOT NULL DEFAULT now(),
    created_by   text
);

CREATE INDEX cw_media_draft_idx ON cw_media (draft_id, created_at DESC);
