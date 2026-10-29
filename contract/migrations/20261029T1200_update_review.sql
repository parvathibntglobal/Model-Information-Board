-- The Updates page's Manage section (2026-10-29, PROPOSED, Parvathi).
-- contract/updates.yaml, judge/updates.py.
--
-- AN UPDATE IS NEVER STORED. Its facts are rebuilt from the registry, the price
-- history and the benchmarks changelog on every read, and it is published as
-- soon as it is built. What a person decides about it is stored here, by the
-- update's `key` - a key that names its facts, so a new fact is a new update
-- and an old decision never lands on words it was not made about.
--
-- WHO WRITES: judge/updates.py review() and undo(), from POST /updates/review
-- and /updates/undo (any signed-in person).
-- WHO READS: judge/updates.py listing(), for every section of the page; the
-- home page's news strip will read the published words (home_*) once wired.

-- ONE ROW PER UPDATE a person has touched. No row: shown, not reviewed yet.
CREATE TABLE update_review (
  update_key   text PRIMARY KEY,
  kind         text NOT NULL,
  -- pending: shown, not reviewed (a style or an edit, nothing more)
  -- approved: shown, checked by a person
  -- declined: hidden from News headlines
  status       text NOT NULL,
  -- A style id from contract/updates.yaml; NULL means the default.
  style        text,
  -- A person's own words; NULL means the style's. Either may be set alone.
  headline     text,
  detail       text,
  reviewed_by  text NOT NULL,
  reviewed_at  timestamptz NOT NULL DEFAULT now(),
  -- ON THE HOME PAGE (to be wired): the words as they were when a person
  -- published the update, kept fixed so a later template change or edit
  -- never changes a published headline. All four NULL: not published.
  home_headline      text,
  home_detail        text,
  home_published_by  text,
  home_published_at  timestamptz,
  CONSTRAINT update_review_home_ck CHECK (
    (home_published_at IS NULL) = (home_headline IS NULL)
    AND (home_published_at IS NULL) = (home_published_by IS NULL)),
  CONSTRAINT update_review_status_ck CHECK (status IN ('pending', 'approved', 'declined')),
  CONSTRAINT update_review_kind_ck CHECK (
    kind IN ('launch', 'price_cut', 'price_rise', 'price_change', 'retiring', 'benchmark',
      'roundup'))
);

-- EVERY CHANGE, so one can be undone and the page can say who did what.
-- `before` is the update_review row as it was (NULL: there was none). Undo puts
-- `before` back and marks the change undone; the next undo takes the change
-- before that.
CREATE TABLE update_review_log (
  id           bigserial PRIMARY KEY,
  update_key   text NOT NULL,
  action       text NOT NULL,
  before       jsonb,
  after        jsonb,
  acted_by     text NOT NULL,
  acted_at     timestamptz NOT NULL DEFAULT now(),
  undone_by    text,
  undone_at    timestamptz,
  CONSTRAINT update_review_log_action_ck CHECK (
    action IN ('approve', 'decline', 'restore', 'style', 'edit', 'publish', 'unpublish')),
  CONSTRAINT update_review_log_undone_ck CHECK ((undone_by IS NULL) = (undone_at IS NULL))
);
CREATE INDEX update_review_log_key_idx ON update_review_log (update_key, id DESC);

-- The home page's read (to be wired): published updates, newest first.
CREATE INDEX update_review_home_idx ON update_review (home_published_at DESC)
  WHERE home_published_at IS NOT NULL;
