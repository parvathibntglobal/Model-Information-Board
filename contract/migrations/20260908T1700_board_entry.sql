-- board_entry — what the classifier DISCOVERED, and what the Board page renders.
--
-- WHY A NEW TABLE RATHER THAN `cell`
-- ----------------------------------
-- `cell` is the publication surface for the ratified capability vocabulary, and
-- reaching it means clearing the gate in judge/curate/gate.py: n_eff >= 3.0,
-- two platforms, no single author dominating. That gate is right for a claim
-- that says a model is GOOD or BAD at something — a verdict needs corroboration
-- before it is published.
--
-- The board's three sections are not verdicts. "Somebody discussed RAG on this
-- model" and "the docs say 2M context" are observations, and gating them behind
-- four agreeing voices would leave all three sections empty for months while
-- the evidence sat in the database. So entries land here, ungated, and the
-- page shows how many reports are behind each one rather than hiding it until a
-- threshold is met. Absence stays visible instead of being manufactured.
--
-- WHAT IS STILL ENFORCED, and it is the part that matters
-- ------------------------------------------------------
--   * `quote_verified` is CHECKed true, exactly like `claim`. Rule 1 does not
--     bend for a new table: no row reaches the board without a quote that was
--     matched byte-for-byte against the text the model was shown.
--   * a `metric` row must carry its unit, its figure and its basis. The same
--     rule the pydantic model enforces, restated here, because a metric row
--     missing any of them renders as an empty cell — and on this board a blank
--     already MEANS something, so a spurious one is not a harmless gap.
--   * `basis` keeps `stated` and `reported` apart. 2M advertised and ~200k
--     reported-usable are two facts from two sources; the column exists so
--     nothing downstream can average them into a number nobody measured.
--
-- NO CLOSED VOCABULARY, ON PURPOSE
-- --------------------------------
-- `slug` has no foreign key and no CHECK against a list. The sections are
-- discovered from the evidence — the hand-designed board carries `vision`,
-- `multimodal` and `function-calling`, none of which is in
-- contract/capabilities.yaml, so a constrained slug would drop them.
--
-- The cost of that is DUPLICATES, not gaps: "function-calling" and
-- "tool-calling" arriving from two threads are one section under two names.
-- `ruling` is how that is repaired — `merged` with a `ruling_target` folds one
-- slug into another, the same shape `capability_candidate` already uses and the
-- admin review UI already renders. An LLM proposes a section; a person
-- consolidates. Rule 2 is unchanged by this table.

CREATE TABLE board_entry (
  id                text PRIMARY KEY,   -- content hash of the natural key below

  -- WHICH OF THE THREE, and they are of equal standing. No section is a
  -- fallback for another, and one quote may produce a row in each.
  section           text NOT NULL,      -- best_for | capability | metric
  slug              text NOT NULL,      -- grouping key, normalised in code
  name              text NOT NULL,      -- the heading the board renders
  definition        text NOT NULL,      -- the test a report has to meet

  -- ── metric-only ──────────────────────────────────────────────────────────
  unit              text,               -- "milliseconds", "USD per 1M tokens"
  value_verbatim    text,               -- THE FIGURE AS WRITTEN. Never computed.
  basis             text,               -- stated | reported

  -- ── provenance: every row traces to one verified quote ───────────────────
  model_version_id  text REFERENCES model_version(id),
  document_id       text NOT NULL REFERENCES document(id),
  claim_id          text REFERENCES claim(id),
  quote             text NOT NULL,
  quote_verified    boolean NOT NULL,
  polarity          text NOT NULL,      -- positive | negative | neutral
  proposer_model    text NOT NULL,      -- which model classified it
  pipeline_version  text NOT NULL,
  created_at        timestamptz NOT NULL DEFAULT now(),

  -- ── consolidation, not publication ───────────────────────────────────────
  -- There is no gate here. A ruling only ever REMOVES or REDIRECTS a row that
  -- should not stand on its own; a row with `ruling IS NULL` is shown.
  ruling            text,               -- adopted | declined | merged
  ruling_target     text,               -- the slug a `merged` row folds into
  reviewed_at       timestamptz,

  CONSTRAINT board_entry_section_ck
    CHECK (section IN ('best_for', 'capability', 'metric')),

  CONSTRAINT board_entry_basis_ck
    CHECK (basis IS NULL OR basis IN ('stated', 'reported')),

  CONSTRAINT board_entry_polarity_ck
    CHECK (polarity IN ('positive', 'negative', 'neutral')),

  -- A metric row is the figure, its unit, and where it came from. Any one of
  -- them missing makes the row unrenderable, so it is refused at the boundary.
  CONSTRAINT board_entry_metric_complete_ck CHECK (
    CASE WHEN section = 'metric'
         THEN unit IS NOT NULL AND value_verbatim IS NOT NULL AND basis IS NOT NULL
         ELSE TRUE END
  ),

  -- Rule 1, restated in the schema. NO `IS NULL OR`: an unverified quote has no
  -- business in a table the board reads.
  CONSTRAINT board_entry_quote_verified_ck CHECK (quote_verified = true),

  CONSTRAINT board_entry_ruling_ck
    CHECK (ruling IS NULL OR ruling IN ('adopted', 'declined', 'merged')),
  CONSTRAINT board_entry_reviewed_ck
    CHECK ((ruling IS NULL) = (reviewed_at IS NULL)),
  CONSTRAINT board_entry_merge_target_ck CHECK (
    CASE WHEN ruling = 'merged' THEN ruling_target IS NOT NULL ELSE TRUE END
  ),

  -- IDEMPOTENT RE-RUNS. Re-classifying the same corpus must not double the
  -- report count the page shows, so the natural key is the quote in its
  -- document under this section and slug, at this pipeline version.
  CONSTRAINT board_entry_natural_key
    UNIQUE (document_id, section, slug, quote, pipeline_version)
);

-- The board reads by section then slug on every page load; the model pages read
-- by model. Both are the whole access pattern.
CREATE INDEX board_entry_section_slug_idx ON board_entry (section, slug);
CREATE INDEX board_entry_model_idx        ON board_entry (model_version_id);
