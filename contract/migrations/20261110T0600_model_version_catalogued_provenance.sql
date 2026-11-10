-- ============================================================================
-- `catalogued`: a registry row seated from OpenRouter's CATALOGUE (#616, agreed by
-- both engineers 2026-11-09, proposal merged 2026-11-10).
--
-- THE GAP. `provenance` allowed `seed | polled | unpolled`, and a fourth kind of
-- row now exists:
--
--     polled      OpenRouter's main model list carries it; the poll writes it.
--     seed        a BUILD FIXTURE that polling replaces.
--     unpolled    a real model a PERSON hand-entered (contract/unpolled_models.yaml,
--                 contract/agent_models.yaml).
--     catalogued  a real model in OpenRouter's catalogue that the poll never brings
--                 (every media model, among others), seated by CODE so its claims
--                 are filed rather than held. Neither a poll result nor a hand entry,
--                 so neither existing word fits - and reusing a word is the mistake
--                 CLAUDE.md records for `seed` (its fixtures section).
--
-- Measured on the shared database 2026-11-09: 501 of 766 catalogue models had no
-- registry row; 408 were in scope; the alias rules would seat 392
-- (docs/measurements/catalogue-registry-rows-2026-11-09.out.json).
-- That 392 counted `:batch` listings and `~...-latest` pointers as models. The
-- writer sets both aside; its read-only plan on 2026-11-10 found 504 candidates
-- and 262 to seat (text 100, image 52, speech 30, transcription 30, video 26,
-- decisions 24), 242 set aside with reasons, 98 of them `:batch` listings and 25
-- latest pointers.
--
-- WRITTEN BY collect/ops/catalogue_seat.py ONLY, which inserts with
-- ON CONFLICT DO NOTHING and never touches an existing row. The poll's upsert sets
-- `provenance = 'polled'` on conflict, so a catalogued row the poll later brings is
-- upgraded. `auto_track` requires `polled`, so a catalogued row never starts a daily
-- fetch. `assert_no_fixtures` queries `seed` exactly and is unchanged.
--
-- NO BEGIN / COMMIT: the runner owns the transaction (collect/migrate.py).
-- WHO RUNS IT: the merger of the PR that carries this file, straight after merge,
-- announced on #616, before the first `seat_catalogue_models.py --apply`.
-- ============================================================================

ALTER TABLE model_version
  DROP CONSTRAINT model_version_provenance_ck;

ALTER TABLE model_version
  ADD CONSTRAINT model_version_provenance_ck
  CHECK (provenance IN ('seed', 'polled', 'unpolled', 'catalogued'));
