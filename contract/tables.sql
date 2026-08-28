-- ============================================================================
--  Model Information Board — schema
--
--  contract/ IS SHARED. Changes go through a PR so the other engineer sees them.
--
--  The lane boundary runs between `thread_context` and `claim`:
--      collect/  fills  document, thread_context, author, model_version, model_alias
--      judge/    fills  claim, claim_weight, cell, label
--  Nothing flows back.
-- ============================================================================


-- ============================================================================
--  REGISTRY — ground truth. Seeded now (10 models), polled from week 5.
--  A social post can TRIGGER a re-check here. It can never WRITE here.
-- ============================================================================

CREATE TABLE model_version (
  id                          text PRIMARY KEY,
  canonical_id                text NOT NULL UNIQUE,   -- e.g. google/gemini-2.5-flash
  provider                    text NOT NULL,
  family                      text,                   -- for same-family disambiguation
  display_name                text,

  release_date                date,
  deprecation_date            date,
  retirement_date             date,
  lifecycle                   text,                   -- preview | ga | deprecated | retired

  advertised_context          int,
  max_output_tokens           int,

  -- The RELIABLE knowledge cutoff, not the training-data cutoff, where a
  -- provider publishes both. They differ: Claude Haiku 4.5 is Feb 2025
  -- reliable and Jul 2025 training. The answer path uses this to reason about
  -- what a model knows, and overstating that costs a wrong recommendation.
  knowledge_cutoff            date,

  -- USD per 1M tokens. NULL when a `price_tier` row exists for this model:
  -- see the warning above that table. These are NOT the lowest tier.
  price_in                    numeric(12,6),
  price_out                   numeric(12,6),
  price_cached_read           numeric(12,6),
  batch_discount              numeric(4,3),

  supports_tools              boolean DEFAULT false,
  supports_structured_output  boolean DEFAULT false,
  supports_vision             boolean DEFAULT false,
  supports_caching            boolean DEFAULT false,
  supports_batch              boolean DEFAULT false,
  regions                     text[],

  -- FR-2: every field traceable to where it came from and when
  sources                     jsonb NOT NULL,         -- {field: {url, retrieved_at}}

  possibly_changed            boolean NOT NULL DEFAULT false,
  provenance                  text NOT NULL,          -- seed | polled
  in_window                   boolean NOT NULL DEFAULT true,

  first_seen_at               timestamptz NOT NULL DEFAULT now(),
  updated_at                  timestamptz NOT NULL DEFAULT now(),

  -- WHEN THIS MODEL WAS LAST SWEPT FOR EVIDENCE. Not when the row was written.
  --
  -- `updated_at` says when the FACTS changed; this says when we last went
  -- looking for what engineers said. They come apart the moment a rotation
  -- exists, and a rotation is forced: 900 daily requests / 81.45 per model is
  -- 11 models a night against a feed carrying 340.
  --
  -- NULLABLE, AND NULL MEANS NEVER SWEPT. Not "swept long ago" and not
  -- "swept now" — a model polled into the registry has had its facts read and
  -- its evidence not looked for, and those are different states (rule 6).
  --
  -- IT EXISTS BEFORE THE ROTATION DOES, ON PURPOSE. A rotation without it is
  -- rule 4 with a date on it: a model whose evidence is five days old renders
  -- identically to one swept last night, and the gate reads both as current.
  -- Nothing records the difference unless this column does.
  --
  -- It does not make every rotation safe. At 340 models a full pass takes 31
  -- days against a 30-day half-life on ops.latency_ttft, so the sweep would
  -- lose to the decay curve and a timestamp only lets you SEE that. Which
  -- models to track is a scoping decision — issue #33.
  last_swept_at               timestamptz,

  CONSTRAINT model_version_provenance_ck
    CHECK (provenance IN ('seed', 'polled'))
);

-- ============================================================================
--  THE MIGRATION LEDGER — collect/migrate.py
--
--  Which forward-only migrations have been applied to THIS database, and the
--  content hash each was applied at. Here rather than created only on demand,
--  because a freshly-applied schema and a migrated one must be identical - and
--  `tests/test_migrations.py` compares them object by object, so a table
--  present in one and not the other is the first thing it catches.
--
--  `content_hash` is what makes an edited migration detectable. An edit after
--  application means two databases already disagree, and `migrate()` refuses
--  the whole run rather than compounding it.
--
--  Not a schema table. A ledger of what happened to the schema.
-- ============================================================================

CREATE TABLE schema_migration (
  filename     text PRIMARY KEY,
  content_hash text NOT NULL,
  applied_at   timestamptz NOT NULL DEFAULT now()
);


-- FR-4: APPEND ONLY. Never DELETE, never UPDATE. Old aliases must keep
-- resolving old quotes, and `latest` in March is not `latest` in June.
CREATE TABLE model_alias (
  id                text PRIMARY KEY,
  surface           text NOT NULL,        -- as written by a human
  normalized        text NOT NULL,        -- lowercased, punctuation stripped
  variants          text[] NOT NULL,      -- search expansions; no fuzzy operator
                                          -- exists in the GitHub or Reddit APIs
  provider_hint     text,
  model_version_id  text REFERENCES model_version(id),
  family            text,
  specificity       text NOT NULL,        -- snapshot | version | family
  valid_from        date,
  valid_until       date,                 -- NULL = still current
  confidence        real NOT NULL DEFAULT 1.0,
  created_at        timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT model_alias_specificity_ck
    CHECK (specificity IN ('snapshot', 'version', 'family'))
);
CREATE INDEX model_alias_normalized_idx ON model_alias (normalized);

CREATE TABLE model_event (
  id                text PRIMARY KEY,
  model_version_id  text NOT NULL REFERENCES model_version(id),
  type              text NOT NULL,   -- new-model | new-snapshot | alias-moved
                                     -- price-change | deprecation-announced
  occurred_at       timestamptz,
  detected_at       timestamptz NOT NULL DEFAULT now(),
  payload           jsonb,
  source_url        text
);

-- ============================================================================
--  TIERED PRICING (item 18). Some providers charge by input length: Gemini
--  2.5 Pro is $1.25/$10.00 at or below 200k input tokens and $2.50/$15.00
--  above it. A single numeric cannot hold that.
--
--  model_version.price_in / price_out are NULL when a row exists here. They are
--  NOT the lowest tier. A lowest-tier fallback would let any caller that forgets
--  to read this table price a model at half its real rate on long-context work,
--  which is a false qualification and reads as plausible on the page.
--
--  With NULL, forgetting fails loudly: a candidate with no cost renders as
--  unpriced rather than as cheap. An unpriced frontier model is a visible gap
--  somebody fixes; a frontier model at half its real price is a wrong
--  recommendation nobody catches.
-- ============================================================================

CREATE TABLE price_tier (
  model_version_id  text NOT NULL REFERENCES model_version(id),
  dimension         text NOT NULL,   -- input_tokens | output_tokens
  min_tokens        int NOT NULL DEFAULT 0,
  max_tokens        int,             -- NULL = no upper bound
  price             numeric(12,6) NOT NULL,
  price_cached_read numeric(12,6),

  -- FR-2 applies here as much as to model_version. Note that FR-2's wording
  -- says "every populated field on any `model_version` row", so a tier row is
  -- outside the requirement as written. `check_source_coverage` walks these
  -- rows anyway: the alternative is provenance with a second place to hide.
  sources           jsonb NOT NULL,

  PRIMARY KEY (model_version_id, dimension, min_tokens),
  CONSTRAINT price_tier_dimension_ck CHECK (dimension IN ('input_tokens','output_tokens'))
);

CREATE TABLE pricing_history (
  model_version_id  text NOT NULL REFERENCES model_version(id),
  price_in          numeric(12,6),
  price_out         numeric(12,6),
  price_cached_read numeric(12,6),
  observed_at       timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (model_version_id, observed_at)
);


-- ============================================================================
--  THE INTERFACE — collect/ fills these, judge/ reads them.
--  Agree any change to these two tables together, in a PR.
-- ============================================================================

CREATE TABLE author (
  id                   text PRIMARY KEY,
  source               text NOT NULL,          -- github | blog | reddit
  external_id          text NOT NULL,
  handle_hash          text,                   -- hashed: we don't need the handle
  account_created_at   timestamptz,
  karma                int,
  technical_history_score real,

  -- FR-17: one engineer on two platforms is ONE voice, not two.
  -- Unresolved stays separate, so counts are an upper bound.
  identity_cluster_id  text,

  first_seen_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source, external_id)
);

CREATE TABLE author_identity_cluster (
  id                 text PRIMARY KEY,
  member_author_ids  text[] NOT NULL,
  evidence           text NOT NULL,   -- matching-handle | linked-profile | shared-repo-link
  merged_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE document (
  id                      text PRIMARY KEY,
  source                  text NOT NULL,          -- github | blog | reddit
  external_id             text NOT NULL,
  url                     text NOT NULL,
  author_id               text REFERENCES author(id),

  thread_root_id          text,                   -- self for a root post
  parent_id               text,

  created_at              timestamptz,            -- when the human posted it
  fetched_at              timestamptz NOT NULL DEFAULT now(),
  lang                    text,

  -- `text_ref` LOCATES the payload; `content_hash` IDENTIFIES it. They are
  -- separate columns because NFR-6 requires the hash to outlive the bytes:
  -- "tombstone a document; its quotes vanish next run, only the content hash
  -- remains" only parses if the two are separable. Storage can therefore move
  -- (filesystem now, an object store later) without rewriting identity.
  --
  --   text_ref      "raw/sha256/ab/cd/abcd...ef"   see collect/rawstore.py
  --   content_hash  "abcd...ef"
  --
  -- Full text is retained privately for verification and reprocessing. It is
  -- never republished: published content is quote + attribution + link.
  text_ref                text NOT NULL,
  content_hash            text NOT NULL,

  -- length-aware near-duplicate detection: simhash is unstable below ~200 tokens
  minhash                 bytea,                  -- short documents
  simhash                 bigint,                 -- long-form

  engagement              jsonb,                  -- {score, comments, upvote_ratio}

  -- SPECIFICITY. Five counted components and the composite they combine into.
  -- Written per document at ingest by collect/triage/specificity.py, BEFORE E3
  -- ranks — child selection happens inside E3, so a score computed in E4 would
  -- arrive a stage too late. E4's floor is the second reader, not the producer.
  --
  -- The COMPONENTS are stored, not just the composite, because the floor is a
  -- five-way OR over them: from the composite alone a row cannot say why it was
  -- kept or dropped, and the evidence drill-down has nothing countable to show.
  --
  -- NULL MEANS NOT SCORED, AND IS NOT false. Every row written before this
  -- existed carries NULL in all six. The floor returns UNKNOWN for those rather
  -- than DROPPED, and E3 must not coalesce the composite to 0 — that would sort
  -- unscored documents last while making them look scored (rule 6).
  --
  -- NOT judge/vet/weight.py's f_specificity: that is per CLAIM, over four
  -- booleans of which two the extractor emits, on a 0.3-1.0 range. These must
  -- never be merged and never compared.
  --
  -- document.has_numbers is readable from judge/ as a FALSIFIER for the
  -- extractor's self-reported claim.has_numbers. It falsifies and cannot
  -- confirm: false here makes a claim asserting true a fabrication; true here
  -- says nothing about whether the quote contains a number.
  -- THE FIVE COMPONENTS. Computed per document at ingest by
  -- collect/triage/specificity.py, from the text alone. No model participates.
  --
  -- ⚠ judge/: `names_version` AND `has_conditions` ARE THE SOURCE FOR
  --   `weight.compute()`'s `version_named=` and `has_conditions=` ARGUMENTS.
  --
  --   Those two are required parameters of `judge/vet/weight.py:compute` and
  --   `ExtractedClaim` carries neither — it has `has_repro_steps` and
  --   `has_numbers` only. So whoever calls `compute()` first has to supply them
  --   from somewhere, and these columns are that somewhere: derived by code
  --   from the same text, which is what "derive them rather than add extractor
  --   fields" meant. judge/ reads `document`; nothing needs to change in the
  --   extractor schema, and nothing needs to change here.
  --
  --   `has_numbers` is the pair that already exists on both sides, and
  --   collect/triage/specificity.py records what that is good for: a document
  --   whose `has_numbers` is False FALSIFIES a claim asserting `has_numbers:
  --   true`, because there are no numbers for the quote to contain. It cannot
  --   confirm — True says nothing about whether THAT quote carried one.
  has_numbers             boolean,
  has_error_strings       boolean,
  has_code                boolean,
  has_conditions          boolean,
  names_version           boolean,
  -- ⚠ COMPARABLE WITHIN A SOURCE, NEVER ACROSS SOURCES.
  --
  -- The weighted composite. Weights live in contract/harvest.yaml and are
  -- PROVISIONAL — nothing has calibrated them. E3 ranks on
  -- specificity_score x log(1 + engagement), which is intra-thread and
  -- therefore intra-source, which is the only comparison this column supports.
  --
  -- #24 closed on the reason: has_error_strings and names_version are 0.45 of
  -- the weight and on the measured corpus both are largely a proxy for MEDIUM
  -- (42.0%/3.6% and 48.3%/6.3%, github/blogs). Sorting two sources by this
  -- column sorts by which source they came from, wearing the clothes of
  -- sorting by evidence quality. Measured means: github 0.527, blogs 0.286.
  --
  -- The five component columns above carry no such restriction: the floor is a
  -- five-way OR over them and never reads the weights, so component-level
  -- comparisons and every gate built on them hold across sources and under any
  -- weighting. If you need to compare documents from different platforms, use
  -- the components, not this.
  specificity_score       real,

  dedup_cluster_id        text,
  is_canonical_in_cluster boolean,

  triage_verdict          text,                   -- kept | dropped
  filter_reasons          text[],
  status                  text NOT NULL DEFAULT 'kept',

  -- ── RETRIEVAL PROVENANCE ──────────────────────────────────────────────
  --
  -- ⚠ ADDED BY E1 2026-08-24 AND NEEDS E2's SIGN-OFF, per the lane rule on
  --   contract/. Two columns, and the second is the reason the first is worth
  --   having.
  --
  -- WHAT WAS ASKED. `harvest_run_id` names the query that retrieved this
  -- document — which alias, which capability entry, which page. It is the join
  -- that separates "this page is empty because we never asked" from "we asked
  -- and got nothing", and without it neither is answerable: 343 documents are
  -- stored and not one of them can name what retrieved it.
  --
  -- FK ADDED BY ALTER BELOW, not inline, because `harvest_run` is created after
  -- `document` in this file.
  harvest_run_id          text,
  --
  -- WHY A SECOND COLUMN, AND IT IS NOT BOOKKEEPING. A nullable FK cannot say
  -- WHY it is null, and the two reasons are opposite findings:
  --
  --   no_run_for_source  the source issues no per-query run. Blog documents
  --                      come from a feed fetch and reddit from a listing;
  --                      neither renders a query, and `harvest_run` holds 153
  --                      rows of which all 153 are github. So NULL here is
  --                      CORRECT and complete — there is no run to point at.
  --   not_recorded       a run existed, or might have, and nobody wrote it
  --                      down. Every row predating these columns is this.
  --   run_recorded       `harvest_run_id` is set.
  --
  -- Collapsing those into one NULL is rule 6 exactly, and it is the mistake
  -- this project has now made four times — an absent value read as a definite
  -- one. A coverage page that cannot tell them apart reports "no provenance"
  -- for a blog document whose provenance is complete, and "provenance absent"
  -- for a github document nobody instrumented, which have opposite repairs.
  --
  -- DEFAULT IS THE HONEST STATE FOR AN UNINSTRUMENTED WRITER. A new writer
  -- that forgets to set this gets `not_recorded` rather than a claim, so the
  -- failure mode is under-claiming. Blog and reddit writers set
  -- `no_run_for_source` explicitly; that is a statement about the source, and
  -- it should require somebody to type it.
  --
  -- NOT PERMANENT FOR BLOGS. `collect/adapters/blog/validators.py` already
  -- names `feed_url` as the natural `watermark.query_key`, so a blog feed fetch
  -- could become a `harvest_run` row and move those documents to
  -- `run_recorded`. This column is what makes that migration visible instead of
  -- silently reinterpreting existing NULLs.
  retrieval_provenance    text NOT NULL DEFAULT 'not_recorded',

  CONSTRAINT document_status_ck
    CHECK (status IN ('kept', 'filtered', 'rejected', 'tombstoned')),
  -- `unreviewed_writer` (added 2026-08-28) is a document written by code that
  -- is not on `main`, by a run that opened no `harvest_run`. It is NOT
  -- `not_recorded`: that value means a run existed and no id was passed, which
  -- is a plumbing gap, and collapsing the two makes an unreviewed writer's rows
  -- indistinguishable from it (rule 6). See the migration for the 853 rows that
  -- were mislabelled `no_run_for_source` - a positive claim that nothing was
  -- missing - and why that is worse than an absent value.
  CONSTRAINT document_retrieval_provenance_ck
    CHECK (retrieval_provenance IN ('run_recorded', 'no_run_for_source', 'not_recorded',
                                    'unreviewed_writer')),
  -- THE TWO COLUMNS CANNOT DISAGREE. `run_recorded` with no id would be a
  -- provenance claim with nothing behind it, and an id under any other state
  -- would be provenance the page refuses to show. Either is worse than both
  -- being absent.
  CONSTRAINT document_retrieval_provenance_agrees_ck
    CHECK ((retrieval_provenance = 'run_recorded') = (harvest_run_id IS NOT NULL)),
  UNIQUE (source, external_id)
);
CREATE INDEX document_minhash_idx     ON document (minhash);
CREATE INDEX document_simhash_idx     ON document (simhash);
CREATE INDEX document_thread_root_idx ON document (thread_root_id);
CREATE INDEX document_status_idx      ON document (status) WHERE status = 'kept';
-- The join `harvest_run_id` exists for: "which documents did this query produce".
-- Present in the migration and MISSED HERE, which `test_the_chain_and_the_file
-- _agree_on_indexes` caught — the second time a migration/DDL divergence has been
-- found by that equivalence rather than by anything behavioural.
CREATE INDEX document_harvest_run_idx ON document (harvest_run_id);

CREATE TABLE dedup_cluster (
  id                    text PRIMARY KEY,
  canonical_document_id text NOT NULL REFERENCES document(id),
  size                  int NOT NULL,
  reach                 int,            -- amplifications contribute to REACH,
                                        -- never to WEIGHT
  first_seen_at         timestamptz NOT NULL DEFAULT now()
);

-- FR-14, FR-15. The single most important table in the interface.
--
-- flattened_text is the exact byte string sent to the extractor.
-- offset_map is how a quote gets back to the comment a human actually wrote.
--
-- THE MAP CANNOT BE RECONSTRUCTED LATER. It is ~10 lines while already walking
-- the thread tree, and impossible afterwards. Anything extracted without it
-- must be re-run.
CREATE TABLE thread_context (
  id                  text PRIMARY KEY,
  thread_root_id      text NOT NULL,
  member_document_ids text[] NOT NULL,   -- root + the 3–5 selected children

  -- Same convention as document.text_ref: a location, not a hash. Uses the
  -- `flattened/` namespace of the same store, which is a regenerable cache —
  -- raw/ is irreplaceable, flattened/ can be dropped and rebuilt.
  flattened_text_ref  text NOT NULL,

  -- SEGMENTS, NOT WHOLE COMMENTS.
  --
  -- [{"flat": [412, 587], "doc": "gh_8842_c3", "raw": [88, 263]}, ...]
  --
  -- Normalisation rewrites text in place: an emoji becomes
  -- `[upside_down_face]`, one character becoming eighteen. So flattened and
  -- raw offsets DRIFT APART inside a single comment, and one offset delta per
  -- comment silently resolves to the wrong text — or past the end of the
  -- document — the moment a quote spans a substitution.
  --
  -- E3 therefore emits:
  --   * one segment per contiguous run where flat and raw are identical
  --     (flat length == raw length; offsets shift linearly)
  --   * one segment per substitution
  --     (flat length != raw length; the span is taken whole, because there
  --      is no meaningful position inside a rewrite)
  --
  -- Consumer: judge/extract/verify.py, step 2. Covered by
  -- tests/test_verify.py::TestDisplay.
  offset_map          jsonb NOT NULL,

  -- ── COVERAGE (#54, ruled 2026-08-18) ──────────────────────────────────
  --
  -- What the selection SAW, so a `thread_context` row cannot claim to
  -- describe a thread it read 4% of. One getPostComments call returned 200 of
  -- 4,833 comments, and Reddit orders SIBLINGS rather than the tree, so the
  -- last-seen score bounds nothing unseen.
  --
  -- ALL FOUR NULLABLE. A row written before coverage existed has not been
  -- measured at 0% — it has not been measured (rule 6).

  -- Comments actually fetched and stored for this thread.
  observed_children        int,

  -- sum(reported counts) + count(unsized markers). What truncation ADMITTED
  -- TO, never the remainder: of 252 `more` markers on the measured thread,
  -- 126 report a hidden count and 126 report none.
  hidden_children_min      int,

  -- Markers reporting no count at all. KEPT SEPARATE, and the argument for it
  -- was inverted during review and the inversion was right: it measured 0 on
  -- fourteen threads and 126 on the fifteenth, which is exactly what makes it
  -- worth recording. A field that is 0 almost always and large occasionally is
  -- how you tell which kind of thread you are holding, and the unexplained
  -- 126/252 split cannot be investigated without it. You cannot investigate
  -- what you do not record.
  hidden_branches_unsized  int,

  -- ⚠ AN UPPER BOUND ON COVERAGE, NEVER A MEASUREMENT OF IT.
  --
  -- `hidden_children_min` is a FLOOR, so the denominator is understated and
  -- this ratio is correspondingly overstated. A thread reading 0.04 was seen
  -- at AT MOST 4%, and the true figure is lower by however much truncation did
  -- not admit to.
  --
  -- That matters to whoever reads this column from a query rather than from
  -- the coverage page, which is why it is here and not only in the page code:
  -- a bound presented as a measurement is rule 7's failure with the unsafe
  -- lean, and this one leans towards flattering our own coverage.
  --
  -- GENERATED, NOT STORED BESIDE ITS INPUTS. The fifth instance of one drift:
  -- a derived value written next to what it derives from means somebody
  -- corrects `hidden_children_min` in a backfill, does not recompute the
  -- ratio, and the row disagrees with itself silently — in the direction that
  -- flatters coverage. The database recomputes it or it does not exist.
  --
  -- The CASE has NO ELSE on purpose: an empty tree yields NULL rather than
  -- 1.0, so 0/0 cannot become full coverage. NULL here is "not measurable",
  -- which is the truth for a thread with nothing observed and nothing hidden.
  coverage_ratio           real GENERATED ALWAYS AS (
                             CASE WHEN COALESCE(observed_children, 0)
                                     + COALESCE(hidden_children_min, 0) > 0
                                  THEN observed_children::real
                                       / (observed_children + hidden_children_min)
                             END
                           ) STORED,

  child_count         int NOT NULL,
  -- children ranked by specificity_score × log(1 + engagement), NOT engagement
  -- alone: the top-voted replies are jokes; the two-line correction that
  -- matters sits at +2
  selection_method    text NOT NULL DEFAULT 'specificity_x_log_engagement',

  assembled_at        timestamptz NOT NULL DEFAULT now(),
  pipeline_version    text NOT NULL
);
CREATE INDEX thread_context_root_idx ON thread_context (thread_root_id);


-- ============================================================================
--  CLAIMS — judge/ fills these.
-- ============================================================================

CREATE TABLE capability (
  key            text PRIMARY KEY,
  failure_mode   text NOT NULL,   -- silent | loud. Drives how much evidence
                                  -- the answer path demands.
  description    text,
  version        text NOT NULL,
  active         boolean NOT NULL DEFAULT true,

  CONSTRAINT capability_failure_mode_ck CHECK (failure_mode IN ('silent', 'loud'))
);

CREATE TABLE claim (
  id                    text PRIMARY KEY,
  document_id           text NOT NULL REFERENCES document(id),
  thread_context_id     text NOT NULL REFERENCES thread_context(id),
  source_comment_id     text NOT NULL,   -- WHICH comment inside the flattened text
  author_id             text REFERENCES author(id),

  model_version_id      text NOT NULL REFERENCES model_version(id),
  family                text,
  specificity           text NOT NULL,   -- snapshot | version | family
  resolution_confidence real,

  capability_key        text NOT NULL REFERENCES capability(key),
  taxonomy_version      text NOT NULL,
  condition_bucket      text NOT NULL,   -- e.g. tools:6-15
  conditions            jsonb,
  pain_points           text[],

  polarity              text NOT NULL,   -- positive | negative | neutral
                                         -- neutral = a voice, never a sentiment:
                                         -- counts toward discussion and weight,
                                         -- toward neither positive nor negative.
  severity              text,            -- mild | clear | severe
                                         -- PHRASE SELECTION ONLY. Never averaged.
  comparison_target_id  text,            -- set when the quote compares two models

  -- FR-12. The anti-fabrication guarantee.
  quote                 text NOT NULL,   -- the RAW span, as written, for display
  quote_flat_offset     int4range NOT NULL,  -- into flattened_text  → verified step 1
  quote_raw_offset      int4range NOT NULL,  -- into the source doc  → resolved step 2
  quote_verified        boolean NOT NULL,

  relevance             text NOT NULL,   -- central | passing
  has_repro_steps       boolean,
  has_numbers           boolean,
  is_sarcastic          boolean,         -- true → the claim is DISCARDED and logged

  evidence_tier         text NOT NULL,   -- A B C D E F

  -- WHOSE claim this is, not whether it is true. Supplies `evidence_tier` via
  -- `contract/harvest.yaml:evidence_tier_by_speaking`, and weights only - it is
  -- NOT a storage gate, so a vendor's own words are stored and discounted
  -- rather than refused.
  --
  -- NULLABLE, and that is deliberate: the four rows written before the column
  -- existed have no answer, and back-filling would need the surface population
  -- each was resolved against. A guess there is rule 6 on a provenance field.
  speaking              text,            -- own-experience | vendor-about-own-product
                                         -- | relayed-from-elsewhere
  extractor_model       text NOT NULL,
  extractor_confidence  real,
  pipeline_version      text NOT NULL,
  created_at            timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT claim_polarity_ck  CHECK (polarity IN ('positive', 'negative', 'neutral')),
  CONSTRAINT claim_relevance_ck CHECK (relevance IN ('central', 'passing')),
  CONSTRAINT claim_severity_ck  CHECK (severity IS NULL
                                       OR severity IN ('mild', 'clear', 'severe')),
  -- FR-13: an unverified claim must never exist
  CONSTRAINT claim_verified_ck  CHECK (quote_verified = true),
  -- Added by 20260821T1600_claim_speaking.sql, and this file did not describe it
  -- for two days. The migration ran against staging and was verified THERE, so
  -- every check I made passed and the equivalence test in CI - which compares a
  -- migrated database against this file - was the only thing that could see the
  -- gap. Checking the artifact is not checking the contract.
  -- NO `IS NULL OR`, deliberately, and it is not a semantic choice: a CHECK
  -- fails only on FALSE, so `speaking IN (...)` already admits NULL. The
  -- equivalence test compares `pg_get_constraintdef` TEXTUALLY, so this has to
  -- render identically to what the migration produced or the two disagree about
  -- a constraint that behaves the same.
  CONSTRAINT claim_speaking_check CHECK (speaking IN (
                                    'own-experience',
                                    'vendor-about-own-product',
                                    'relayed-from-elsewhere'))
);

-- the aggregation hot path
CREATE INDEX claim_cell_idx
  ON claim (model_version_id, capability_key, condition_bucket, created_at);

CREATE TABLE claim_weight (
  claim_id         text PRIMARY KEY REFERENCES claim(id) ON DELETE CASCADE,
  w_final          real NOT NULL,

  -- FR-19: itemised, because "why does this page say that?" must be answerable
  -- with a table
  f_evidence       real NOT NULL,   -- tier: A 1.00 · B 0.65 · C 0.35 · D 0.12 · E 0.04 · F 0.02
  f_platform       real NOT NULL,   -- github 0.95 · blog 0.90 · reddit 0.85
  f_specificity    real NOT NULL,   -- version named · numbers · conditions · repro
  f_relevance      real NOT NULL,   -- central 1.0 · passing 0.4
  f_recency        real NOT NULL,   -- exp(-ln2 · age_days / half_life)
  f_launch         real NOT NULL,   -- FR-20: FROZEN at extraction, NEVER recomputed
  f_fuzziness      real NOT NULL,   -- snapshot 1.0 · version 0.6 · family 0.3

  computed_at      timestamptz NOT NULL DEFAULT now(),
  pipeline_version text NOT NULL
);


-- ============================================================================
--  EXTRACTION LEDGER — that a thread was READ, separately from what it said.
--  judge/ fills this. Proposed by E2, ruled 2026-08-18.
-- ============================================================================

-- WHY THIS IS NOT DERIVABLE FROM `claim`.
--
-- A nightly batch must not re-extract a thread it has already read: at
-- $0.00164 a thread, re-paying for the whole corpus every night is 96% of the
-- monthly bill buying rows that already exist, since claim_id hashes the
-- pipeline version and the writes come out identical.
--
-- The obvious skip is "threads that already have claims at this
-- pipeline_version", and it is WRONG in the direction that costs most:
--
--     A THREAD THAT YIELDED ZERO CLAIMS IS NOT AN UNEXTRACTED THREAD.
--
-- It looks unextracted forever and is re-paid for every night — and those are
-- precisely the threads that cost the most and return the least. Rule 6,
-- landing on the single signal the whole saving depends on. `claim` cannot
-- express "read it, found nothing", because that row does not exist.
CREATE TABLE thread_extraction (
  thread_context_id text NOT NULL REFERENCES thread_context(id),

  -- Part of the key, not an attribute. A re-extraction under a changed prompt
  -- is new work on old text and must NOT be skipped — the same reason
  -- claim_id hashes it.
  pipeline_version  text NOT NULL,

  extracted_at      timestamptz NOT NULL DEFAULT now(),

  -- ⚠ NOT NULL, AND 0 IS A RESULT RATHER THAN AN ABSENCE.
  --
  -- This column is the entire point of the table. `0` says "we read this and
  -- there was nothing in it", which is a finding; the ABSENCE OF A ROW says
  -- "nobody has read this", which is a job. Same distinction as
  -- `phrase_present` NULL versus 0, on a table where it decides what gets
  -- billed.
  claims_written    int NOT NULL,

  -- What the call actually reported, NULL where the provider did not say.
  -- Never 0 for "unknown" (rule 6): a completion reporting no usage silently
  -- disables the spend cap, and `judge/extract/budget.py` counts those
  -- separately for exactly that reason. This is also where E1's token
  -- measurement lands without a second mechanism — the estimate in
  -- ESTIMATED_INPUT_TOKENS assumes 4 chars per token and is wrong by whatever
  -- the real tokenizer says.
  input_tokens      int,
  output_tokens     int,

  -- Retries are recorded because they are paid for. A thread that needed two
  -- calls cost twice and looks identical afterwards.
  schema_retries    int NOT NULL DEFAULT 0,

  -- ⚠ WHAT WAS READ, because the id does not say.
  --
  -- `thread_context.id` is stable_id("thread_context", root_id, version) and
  -- IGNORES CONTENT, so a thread re-assembled with different children keeps
  -- the same id. E1 found this: `specificity.py` changed, the scorer picked
  -- different children, and PIPELINE_VERSION did not move.
  --
  -- Without this column the skip is wrong in the expensive direction: the
  -- ledger says "already extracted at this version", the id and version both
  -- match, and the thread we would skip is not the thread we read. Evidence
  -- silently never extracted, which is worse than paying twice.
  --
  -- sha256 of `flattened_text` - the exact bytes the extractor was given.
  content_fingerprint text,

  PRIMARY KEY (thread_context_id, pipeline_version)
);

-- The skip lookup: every thread already read at one pipeline version.
CREATE INDEX thread_extraction_version_idx
  ON thread_extraction (pipeline_version);

-- ============================================================================
--  CELLS — what the board is allowed to say. judge/ fills these.
-- ============================================================================

CREATE TABLE cell (
  model_version_id   text NOT NULL REFERENCES model_version(id),
  capability_key     text NOT NULL REFERENCES capability(key),
  condition_bucket   text NOT NULL,

  n_eff              real NOT NULL,   -- Σ w. w_max = 0.95, so n_eff ≥ 3.0
                                      -- already implies ≥4 claims
  independent_voices int NOT NULL,    -- distinct PEOPLE, after identity clustering
  platform_count     int NOT NULL,
  max_author_share   real NOT NULL,
  positive           int NOT NULL,
  negative           int NOT NULL,

  status             text NOT NULL,   -- published | insufficient | contested
  provenance         text NOT NULL,   -- harvested | hand_curated

  consensus_phrase   text,            -- TEMPLATE-ASSEMBLED from counts.
                                      -- Never model-written. Never a score.
  conditional_note   text,            -- "fine under 5 tools, breaks above 10"
  quote_ids          text[],

  freshest_at        timestamptz,
  median_age         interval,
  computed_at        timestamptz NOT NULL DEFAULT now(),
  pipeline_version   text NOT NULL,

  PRIMARY KEY (model_version_id, capability_key, condition_bucket),
  CONSTRAINT cell_status_ck     CHECK (status IN ('published','insufficient','contested')),
  CONSTRAINT cell_provenance_ck CHECK (provenance IN ('harvested','hand_curated'))
);

-- what the answer path reads. It never touches the pipeline (NFR-2).
CREATE VIEW cell_current AS
  SELECT * FROM cell WHERE status IN ('published', 'contested');

-- FR-31: match against the REPORTED limit, never the advertised one
CREATE TABLE reported_context (
  model_version_id text PRIMARY KEY REFERENCES model_version(id),
  advertised       int,
  reported_low     int,
  reported_high    int,
  quote_ids        text[],

  -- FR-31 reads `reported_low` as a HARD FILTER, so a hand-seeded value
  -- silently excludes models from every long-context recommendation.
  --
  -- Every other number on this board argues its case in front of the reader
  -- and can be disagreed with. This one removes candidates before the reader
  -- sees them: a wrong `cell` shows up as a phrase somebody can read, a wrong
  -- `reported_low` shows up as an absence, and nobody audits a model that was
  -- never in the list. Same guard as cell.provenance, for a stronger reason.
  --
  -- assert_no_fixtures() refuses to start outside development while any row
  -- here is hand_seeded. In development, where hand-seeded rows legitimately
  -- exist, judge/ names the exclusion and says the threshold is hand-seeded.
  provenance       text NOT NULL DEFAULT 'harvested',

  computed_at      timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT reported_context_provenance_ck
    CHECK (provenance IN ('harvested', 'hand_seeded'))
);

CREATE TABLE label (
  id                  text PRIMARY KEY,
  model_version_id    text NOT NULL REFERENCES model_version(id),
  kind                text NOT NULL,   -- praised-for | criticised-for | contested
                                       -- undiscussed | just-launched
                                       -- possibly-changed | deprecating
  capability_key      text REFERENCES capability(key),
  state               text NOT NULL,   -- pending | provisional | established
                                       -- weakening | withdrawn
  -- FR-26: "click the label, see the words" is a property of the data
  earned_by_quote_ids text[] NOT NULL,
  first_seen_at       timestamptz NOT NULL DEFAULT now(),
  last_confirmed_at   timestamptz
);

-- FR-27: a board that changes its answers without explaining why
-- doesn't get trusted twice
CREATE TABLE label_change (
  id          text PRIMARY KEY,
  label_id    text NOT NULL REFERENCES label(id),
  direction   text NOT NULL,   -- gained | lost
  driver      text NOT NULL,   -- new-evidence | price-change
                               -- version-change | config-change
  quote_ids   text[],
  occurred_at timestamptz NOT NULL DEFAULT now()
);


-- ============================================================================
--  ANSWER PATH — judge/ fills these.
-- ============================================================================

CREATE TABLE task_profile (
  id                 text PRIMARY KEY,
  raw_text           text NOT NULL,
  profile            jsonb NOT NULL,
  complexity_tier    int,
  error_cost         text,   -- experimental | internal | customer-facing | irreversible

  -- THE VOLUME INVARIANT: the user always states REQUESTS.
  -- Role volume is always derived. Q6 multiplies by runs_per_request
  -- exactly once; nothing else may.
  requests_per_month bigint,

  inferred_fields    text[],  -- FR-30: shown to the user as editable
  created_at         timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE role (
  id                text PRIMARY KEY,
  task_profile_id   text NOT NULL REFERENCES task_profile(id),
  name              text NOT NULL,
  capability_needs  jsonb NOT NULL,
  runs_per_request  int NOT NULL DEFAULT 1,   -- where the money is
  failure_mode      text,                     -- silent | loud
  error_cost        text,
  dependents        text[]
);

CREATE TABLE answer (
  id          text PRIMARY KEY,
  role_id     text NOT NULL REFERENCES role(id),
  candidates  jsonb NOT NULL,   -- [{model_version_id, band, cost_per_task,
                                --   margins, weakest, risks, quote_ids}]
  abstained   boolean NOT NULL DEFAULT false,
  reason      text,
  assumptions text[],
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- the only measure that can tell us we were wrong
CREATE TABLE outcome (
  answer_id        text PRIMARY KEY REFERENCES answer(id),
  adopted          boolean NOT NULL,
  model_version_id text REFERENCES model_version(id),
  success          boolean,
  retries          int,
  latency_ms       int,
  cost_usd         numeric(12,6),
  failure_kind     text,
  what_happened    text,
  reported_at      timestamptz NOT NULL DEFAULT now()
);


-- ============================================================================
--  QC
-- ============================================================================

CREATE TABLE golden_label (
  document_id text NOT NULL,
  label_type  text NOT NULL,   -- extraction | entity_resolution | filter
  label       jsonb NOT NULL,
  labeler     text NOT NULL,
  labeled_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (document_id, label_type, labeler)
);

CREATE TABLE audit (
  id         text PRIMARY KEY,
  claim_id   text NOT NULL REFERENCES claim(id),
  auditor    text NOT NULL,
  verdict    text NOT NULL,   -- correct | wrong | unclear
  notes      text,
  audited_at timestamptz NOT NULL DEFAULT now()
);

-- Every feed is a source row. The initial nine are seeded from
-- `contract/sources.yaml` so the list is reviewable and diffable; feeds
-- discovered from links in already-harvested content are inserted here
-- directly and never written back to the contract file.
CREATE TABLE source (
  id           text PRIMARY KEY,
  platform     text NOT NULL,
  endpoint     text,
  base_trust   real NOT NULL,   -- github 0.95 · blog 0.90 · reddit 0.85
  tos_notes    text NOT NULL,   -- NFR-5: reviewed and recorded per source

  -- Item 20's shape, applied to sources. Without this, a feed that arrived by
  -- link is indistinguishable from one somebody vetted, and silently inherits
  -- a class ruling nobody made about it — a value that reads as reviewed,
  -- gating whether we are allowed to fetch at all.
  provenance   text NOT NULL,   -- seed | discovered

  -- NFR-5, the machine-readable half. `tos_notes` is the prose a human reads;
  -- these are what `assert_terms_reviewed()` gates on. A row with no ruling is
  -- refused, and a ruling whose evidence has gone stale is refused too — a
  -- ruling asserted forever against a site that changed in October is the
  -- unreviewed placeholder again, wearing a date.
  --
  -- NULLABLE, and that is rule 6 rather than laxity. `reddit` genuinely has
  -- no ruling: access is deferred, nobody has read the terms, and the row has
  -- to exist anyway because `watermark.source_id` references it. NOT NULL
  -- here would force one of two lies — a sentinel ruling id, which is the
  -- placeholder this design removed wearing a better name, or a fabricated
  -- date. NULL says "not reviewed", the reader can act on it, and
  -- `assert_terms_reviewed()` refuses to fetch it. An unreviewed source is
  -- visible as unreviewed instead of missing.
  terms_ruling      text,       -- an id from sources.yaml:terms_rulings
  terms_checked_on  date,       -- when this row's evidence was measured

  -- The mechanical observations the ruling is applied to: robots status and
  -- HTTP code, which paths are permitted, paywall, feed type.
  terms_evidence    jsonb,

  health_status text,
  last_yield   int,             -- FR-10: a drop means broken markup,
                                -- not a quiet internet

  CONSTRAINT source_provenance_ck CHECK (provenance IN ('seed', 'discovered')),

  -- The honest gap above is available to the hand-curated seed only. A feed
  -- that arrived by a link in harvested content must carry a ruling made
  -- about *its* host: without this, a discovered row inserts ruling-less and
  -- is indistinguishable at the gate from one somebody deferred on purpose.
  -- Item 20 again — the value that cannot be told apart from a considered one.
  CONSTRAINT source_discovered_needs_ruling_ck
    CHECK (provenance = 'seed' OR terms_ruling IS NOT NULL)
);

-- Deliberately NOT swept by assert_no_fixtures(). `source.provenance = 'seed'`
-- is a curation decision that stays, unlike `model_version.provenance = 'seed'`
-- which is a build fixture standing in for the week-5 poller.

-- FR-9: resume exactly where consumption paused
CREATE TABLE watermark (
  source_id       text NOT NULL REFERENCES source(id),
  query_key       text NOT NULL,
  last_run_at     timestamptz,
  cursor          text,

  -- FR-9's acceptance is "resumes with no gap and no REFETCH". A cursor alone
  -- cannot say whether a query paused mid-pagination or reached the end of
  -- its results, and on resume the first must be continued while the second
  -- must not.
  exhausted       boolean NOT NULL DEFAULT false,

  PRIMARY KEY (source_id, query_key)
);


-- ============================================================================
--  HARVEST RUNS — one row per source, per query, per run. collect/ fills it.
--
--  Serves three requirements that would otherwise each need their own place:
--    FR-9   whether a query finished or paused mid-pagination
--    FR-10  yield HISTORY, so a drop is visible as a drop. `source.last_yield`
--           holds one number with nothing to compare it against, and
--           collect/CLAUDE.md requires a 14-day burn-in before the related
--           alert arms for exactly that reason.
--    FR-11  truncation by a budget cap, named rather than silent
-- ============================================================================

CREATE TABLE harvest_run (
  id               text PRIMARY KEY,
  source_id        text NOT NULL REFERENCES source(id),
  query_key        text NOT NULL,   -- matches watermark.query_key

  started_at       timestamptz NOT NULL DEFAULT now(),
  finished_at      timestamptz,

  items_fetched    int NOT NULL DEFAULT 0,
  items_kept       int NOT NULL DEFAULT 0,   -- FR-10: the yield figure
  http_errors      int NOT NULL DEFAULT 0,

  -- NULL while running; false when paused mid-pagination; true when the query
  -- reached the end of its results and must not be resumed.
  exhausted        boolean,

  -- FR-11. NULL when the harvest ran to completion. Naming the cap that cut
  -- it short is what stops silent truncation reading as "we looked
  -- everywhere" when we did not. Closed set on purpose: FR-11's acceptance is
  -- a check, and a check over arbitrary strings is not one.
  --
  -- TWO KINDS, AND THE COVERAGE PAGE MUST RENDER THEM DIFFERENTLY:
  --
  --   CAPS WE CHOSE           query-budget · time-budget · extraction-budget
  --     "we decided not to look further"
  --
  --   THE PLATFORM STOPPING US   rate-limit · result-ceiling
  --     "we were not allowed to look further"
  --
  -- Those are opposite statements about the same missing data. One is a
  -- decision somebody can revisit by raising a budget; the other is a wall
  -- that raising a budget will not move, and the only remedies are narrower
  -- queries or a different access path.
  --
  -- `result-ceiling` covers any platform limit on how many results a query
  -- can ever yield, regardless of pagination: GitHub Search returns at most
  -- 1,000 results per query (100 per page) and at most 4,000 repositories
  -- for a repository search. Same class, same consequence.
  --
  -- NOT in this set: a query whose syntax the platform silently discarded.
  -- That query returned everything it matched, so it was not cut short. It
  -- was the wrong query, which is a different failure and needs a different
  -- signal.
  truncated_by     text,

  -- WHAT HAPPENED, and it is NOT a kind of truncation. `truncated_by` says a
  -- sweep stopped early; a refused sweep never started, so filing it there
  -- would make that column mean "cut short" and "never begun" at once.
  --
  --   ok        it ran
  --   refused   we declined to try - the terms gate said no
  --   error     we tried and something broke
  --
  -- The last two need different responses: a ruling gap and a network failure
  -- are not the same fault, and collapsing them files a compliance state as a
  -- defect.
  --
  -- NULL is still-running-or-killed, matching `job_run.outcome` exactly, and
  -- the vocabulary is job_run's for the same reason: that table spent a whole
  -- migration replacing `failed` with `error` so one concept has one word.
  --
  -- ⚠ ANY DURATION FIGURE OVER THIS TABLE MUST FILTER `outcome = 'ok'`.
  -- A refused run has finished_at ≈ started_at, because the gate check is all
  -- that happened between them. Averaging those in with real sweeps is not a
  -- small bias: BOTH harvest commands refuse until the terms rulings land, so
  -- the first population of this table is entirely refusals and the mean
  -- duration of a sweep would be the mean duration of a gate check.
  outcome          text,

  -- Issue #5. Pages requested against pages written to `raw/`, which differ the
  -- moment `max_pages` rises above one - and the difference is exactly what
  -- makes "recoverable by re-sieving" true or false for a run. A re-sieve that
  -- can say "this run stored page 1 of 4" is a re-sieve nobody over-trusts.
  --
  -- NULL means NOT RECORDED, never zero. A run that stored no pages is 0; a row
  -- written before these columns existed is unknown, and the two must not read
  -- alike (rule 6).
  pages_fetched    int,
  pages_stored     int,

  -- The sieve's own yield for this run, which the GitHub harvester already
  -- computes and rounds to three places. Carried here so FR-10's figure has a
  -- denominator that travels with it rather than being recomputed downstream.
  sieve_pass_rate  real,

  pipeline_version text NOT NULL,

  CONSTRAINT harvest_run_truncated_ck
    CHECK (truncated_by IS NULL OR truncated_by IN ('query-budget', 'rate-limit',
                                                    'time-budget', 'extraction-budget',
                                                    'result-ceiling')),

  CONSTRAINT harvest_run_outcome_ck
    CHECK (outcome IS NULL OR outcome IN ('ok', 'refused', 'error')),

  -- THE FAILED-CLOSE CASE IS WHY THIS EXISTS, and the argument is Engineer 2's.
  -- Without it, an update that sets `finished_at` and forgets `outcome` succeeds
  -- and leaves a row reading "finished, verdict unknown" - which is
  -- indistinguishable from a schema that never recorded verdicts at all. With
  -- it, that update is REJECTED and the row stays both-NULL, which is job_run's
  -- own "did not finish" and is TRUE.
  --
  -- So the constraint makes a half-written row accurate rather than missing.
  -- That is the better argument: the cost is not that a refused sweep gets a
  -- finished_at, it is that a partial write cannot lie.
  CONSTRAINT harvest_run_finish_ck
    CHECK ((finished_at IS NULL) = (outcome IS NULL))
);

-- `document.harvest_run_id`'s foreign key, declared here because `document` is
-- created ~680 lines above `harvest_run` and an inline REFERENCES would fail on
-- a fresh schema. See the RETRIEVAL PROVENANCE block on `document`.
--
-- NO ON DELETE CASCADE, deliberately. A document outlives the query that found
-- it: deleting a harvest_run must never delete evidence. ON DELETE SET NULL is
-- also wrong, because it would silently move a row from `run_recorded` to a
-- state its own CHECK forbids — so a harvest_run with documents cannot be
-- deleted at all, which is the correct answer for an append-only ledger.
ALTER TABLE document
  ADD CONSTRAINT document_harvest_run_fk
  FOREIGN KEY (harvest_run_id) REFERENCES harvest_run(id);
CREATE INDEX harvest_run_source_query_idx
  ON harvest_run (source_id, query_key, started_at DESC);
CREATE INDEX harvest_run_truncated_idx ON harvest_run (truncated_by)
  WHERE truncated_by IS NOT NULL;


-- ============================================================================
--  COVERAGE — what the board does not know.
--  collect/ fills this. judge/ reads it for the coverage page.
--
--  Gaps that live only in CLI output become permanent the first time somebody
--  scripts the load. FR-11's principle generalises past budget caps: a gap
--  nobody can see reads as "we looked everywhere" when we did not.
-- ============================================================================

CREATE TABLE coverage_gap (
  id               text PRIMARY KEY,
  kind             text NOT NULL,
  subject          text NOT NULL,   -- canonical_id. Deliberately NOT a foreign
                                    -- key: a gap can concern a model that is
                                    -- not in the registry, which is itself one
                                    -- of the things worth reporting.
  detail           text NOT NULL,
  observed_at      timestamptz NOT NULL DEFAULT now(),
  pipeline_version text NOT NULL,   -- every derived row carries one, so a
                                    -- reporting change is re-runnable

  -- An unconstrained `kind` is how a fifth gap type gets added later without
  -- the coverage page knowing it exists. Adding one is then a deliberate
  -- contract change with a review attached.
  CONSTRAINT coverage_gap_kind_ck CHECK (kind IN (
    'unsourced-field',
    'missing-spelling',
    'out-of-window',
    'unknown-release-date'
  )),

  -- A nightly re-run must not multiply the same gap.
  CONSTRAINT coverage_gap_unique UNIQUE (kind, subject, detail, pipeline_version)
);
CREATE INDEX coverage_gap_kind_idx ON coverage_gap (kind);


-- ============================================================================
--  THE RUN LEDGER — collect/ops/chain.py
--
--  Every stage of every nightly run. WRITTEN BEFORE THE WORK, updated after.
--
--  WHY A TABLE AND NOT THE JSONL ARTIFACT IT WAS FIRST PROPOSED AS. Three
--  defects reduced to one question a file on the machine cannot answer:
--
--      in_window at its schema default on 340 rows   has recompute_window run?
--      one last_swept_at from an ad-hoc mark_swept   has anything ever swept?
--      three writers greping as wired                has this caller ever run?
--
--  Each cost a manual investigation. `assert_no_phantom_sweeps` is cheap only
--  because it can join `last_swept_at` against `harvest_run` — a CONTRADICTION
--  is checkable and an ABSENCE is not. This table generalises that from one
--  column to every stage, in the database the rows are about.
-- ============================================================================

CREATE TABLE job_run (
  id            text PRIMARY KEY,
  stage         text NOT NULL,
  started_at    timestamptz NOT NULL DEFAULT now(),

  -- ⚠ NULL MEANS DID NOT FINISH. IT DOES NOT MEAN FAILED.
  --
  -- A killed process cannot write its own failure, so the absence has to carry
  -- that meaning: "started 03:00, never finished" is a fact, and a row written
  -- only on success leaves nothing at all, which reads as a night with no work.
  --
  -- Same treatment as `harvest_run.truncated_by` and for the same reason:
  -- ANYTHING READING THIS MUST NOT COLLAPSE THE TWO. `finished_at IS NULL` with
  -- `outcome IS NULL` is still-running-or-killed; `outcome = 'failed'` is a
  -- stage that ran and reported failure. A dashboard showing both as red loses
  -- the distinction between a crash and a refusal, which are opposite repairs.
  finished_at   timestamptz,

  -- NULL while running. Closed set, because a check over arbitrary strings is
  -- not a check.
  --   ok       the stage did its work
  --   refused  the stage declined deliberately — a gate, a missing input, a
  --            precondition. NOT an error, and it must not render as one.
  --   error    the stage tried and raised
  --
  -- These are `collect/ops/chain.py`'s OK / REFUSED / ERROR verbatim. The
  -- first version of this CHECK said 'failed' instead of 'error' and would
  -- have needed a writer translating between the two — one concept, two
  -- vocabularies, drifting from the day it was written. Corrected by
  -- 20260818T1520.
  outcome       text,

  -- NULL WHERE UNKNOWN, NEVER 0 (rule 6). A stage that refused counted nothing;
  -- 0 would assert it counted and found none, which is the distinction this
  -- project has now had to make four times.
  items_in      int,
  items_out     int,

  -- The refusal text, or the stage's own report. Free-form on purpose: the
  -- closed set above is what gets queried, this is what gets read.
  detail        jsonb,

  pipeline_version text NOT NULL,

  CONSTRAINT job_run_outcome_ck
    CHECK (outcome IS NULL OR outcome IN ('ok', 'refused', 'error')),

  -- An outcome without a finish is a row that claims to have concluded and did
  -- not record when. The reverse is legitimate and common: finished_at set with
  -- outcome NULL cannot happen either, so both directions are refused.
  CONSTRAINT job_run_finish_ck
    CHECK ((finished_at IS NULL) = (outcome IS NULL))
);

-- The two questions asked of this table: "when did stage X last run" and
-- "what is still running".
CREATE INDEX job_run_stage_idx ON job_run (stage, started_at DESC);
CREATE INDEX job_run_unfinished_idx ON job_run (started_at) WHERE finished_at IS NULL;
