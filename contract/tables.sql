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

  CONSTRAINT model_version_provenance_ck
    CHECK (provenance IN ('seed', 'polled'))
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
  specificity_score       real,                   -- numbers · error strings · code
                                                  -- · version named. Reused by E3
                                                  -- for child ranking.

  dedup_cluster_id        text,
  is_canonical_in_cluster boolean,

  triage_verdict          text,                   -- kept | dropped
  filter_reasons          text[],
  status                  text NOT NULL DEFAULT 'kept',

  CONSTRAINT document_status_ck
    CHECK (status IN ('kept', 'filtered', 'rejected', 'tombstoned')),
  UNIQUE (source, external_id)
);
CREATE INDEX document_minhash_idx     ON document (minhash);
CREATE INDEX document_simhash_idx     ON document (simhash);
CREATE INDEX document_thread_root_idx ON document (thread_root_id);
CREATE INDEX document_status_idx      ON document (status) WHERE status = 'kept';

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

  polarity              text NOT NULL,   -- positive | negative
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
  extractor_model       text NOT NULL,
  extractor_confidence  real,
  pipeline_version      text NOT NULL,
  created_at            timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT claim_polarity_ck  CHECK (polarity IN ('positive', 'negative')),
  CONSTRAINT claim_relevance_ck CHECK (relevance IN ('central', 'passing')),
  CONSTRAINT claim_severity_ck  CHECK (severity IS NULL
                                       OR severity IN ('mild', 'clear', 'severe')),
  -- FR-13: an unverified claim must never exist
  CONSTRAINT claim_verified_ck  CHECK (quote_verified = true)
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

  pipeline_version text NOT NULL,

  CONSTRAINT harvest_run_truncated_ck
    CHECK (truncated_by IS NULL OR truncated_by IN ('query-budget', 'rate-limit',
                                                    'time-budget', 'extraction-budget',
                                                    'result-ceiling'))
);
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
