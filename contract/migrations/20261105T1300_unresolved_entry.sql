-- Board entries whose model is not in the registry YET, held rather than lost
-- (2026-11-05, #602).
--
-- WHY. A verified claim whose model name resolves to no registry row was
-- dropped at `judge/pipeline.py` and only its surface was kept, in memory, for
-- the run's log. A local fetch for GPT Image 2.5 Sunburst on 2026-11-05 kept 3
-- of 50 verified claims this way: its richest thread was an article comparing
-- GPT-Image 2.5 and 2.6, and the 2.6 claims - a model released the day before,
-- not yet seated - were thrown away after being paid for.
--
-- WHAT THIS IS NOT. It is not a board row and no page reads it as one: the
-- refusal to guess a model stays exactly as it was (a family name, an ambiguous
-- codename, a range and a model nobody seated all land here alike). Each row is
-- the entry the extractor proposed, with its verified quote and the model name
-- AS WRITTEN, so that when the model is seated, `scripts/attribute_unresolved_
-- entries.py` can resolve the name with the same resolver and file it onto the
-- board - with no second model call.
--
-- WHO WRITES: judge/pipeline.py (extraction). scripts/attribute_unresolved_
-- entries.py sets the three `attributed_*` columns, once, when a row is filed.
-- WHO READS: scripts/attribute_unresolved_entries.py; scripts/fetch_model.py
-- reports the count per run.
--
--   id                 hash of (document_id, section, slug, quote, surface,
--                      pipeline_version) - a re-run cannot double a row
--   surface            the model name as the extractor read it from the text
--   document_id        the document the quote is in
--   thread_context_id  the thread it was read in
--   section .. basis   the entry as proposed, as board_entry holds them
--   parent_proposed    the heading the extractor filed it under, if any
--   axis_verbatim, subject_verbatim  carried as board_entry carries them
--   polarity, quote    the claim's polarity and its VERIFIED quote
--   proposer_model     which model proposed it
--   pipeline_version   the pipeline that extracted it
--   attributed_at      when it was filed onto the board; NULL = still held
--   attributed_to      the model_version id the surface resolved to then
--   attributed_entry   the board_entry id it became (NULL when that entry
--                      already existed)

CREATE TABLE unresolved_entry (
  id                 text PRIMARY KEY,
  surface            text NOT NULL,
  document_id        text NOT NULL REFERENCES document(id),
  thread_context_id  text,
  section            text NOT NULL,
  slug               text NOT NULL,
  name               text NOT NULL,
  definition         text NOT NULL,
  unit               text,
  value_verbatim     text,
  basis              text,
  parent_proposed    text,
  axis_verbatim      text,
  subject_verbatim   text,
  polarity           text NOT NULL,
  quote              text NOT NULL,
  proposer_model     text NOT NULL,
  pipeline_version   text NOT NULL,
  created_at         timestamptz NOT NULL DEFAULT now(),
  attributed_at      timestamptz,
  attributed_to      text REFERENCES model_version(id),
  attributed_entry   text,
  CONSTRAINT unresolved_entry_section_ck
    CHECK (section IN ('best_for', 'capability', 'metric')),
  CONSTRAINT unresolved_entry_polarity_ck
    CHECK (polarity IN ('positive', 'negative', 'neutral')),
  CONSTRAINT unresolved_entry_attributed_ck
    CHECK ((attributed_at IS NULL) = (attributed_to IS NULL))
);

CREATE INDEX unresolved_entry_held_idx ON unresolved_entry (surface) WHERE attributed_at IS NULL;
