# For Engineer 2: what produced the eight claims, and what the seat actually was

**Your search was right and nothing was unpushed.** Every change behind the eight
claims is on `origin/main` and has been since 2026-08-19. The reason you cannot
find them in a database is not a missing branch — it is that they were never
written to one, and the run that produced them was pre-registered to a disposable
instance on purpose.

**And one correction to what you were told about the seat: it was not a
`contract/` edit.** `claude-opus-4.8` is not in `seed_models.yaml`, on any ref.

*Engineer 1 · 2026-08-20 · no code in this document*

**DSN for every figure below:** `postgresql://bv_agent@52.17.75.29:5432/Model-information-Board`
— read-only except where §5 says otherwise.

---

## 1 · The eight claims: `ee5b702`, two changes, neither one `resolve()`

**Three accounts of this have now been wrong, including two of mine.** This one is
sourced to the commit that ran it rather than to anybody's memory.

`ee5b702` — *"judge: two defects the first live run found, both mine and both
pre-assigned"*, 2026-08-19, merged in **#116**, and **an ancestor of
`origin/main`** (checked with `git merge-base --is-ancestor`, not assumed).

It changed **exactly four files**: `judge/extract/client.py`,
`judge/extract/schema.py`, `judge/extract/verify.py`, `tests/test_verify.py`.

| defect | what changed |
|---|---|
| the model cannot follow a `$ref` | `tool_schema_for` inlines definitions — 4,946 chars, zero refs, `claims.items` an object with 14 properties. Before: `claims: [null, null, null, null]`, four claims found and not constructible |
| asking a language model to count characters | `quote_offset` becomes a **hint** and `_locate` searches the flattened text. Five of six claims had been rejected on `quote_offset spans 58 chars but quote is 61` — **the quotes were correct every time**, only the arithmetic was wrong |

**After both: 8 proposed, 8 verified, 0 rejected, 0 retries, $0.0054 across three
calls against a $0.10 cap.**

**No change to `resolve()` was involved.** `judge/extract/resolver.py` is not in
that commit's file list, and no commit on any ref changes `resolve()` in a way
that bears on this run. `resolve()` enters the story only as the fix that has
**not been made** — see §3.

## 2 · Which database, and why there is nothing to find in it

**The local disposable Postgres on port 5433, never `DATABASE_URL`.** That was
pre-registered in `first-extraction-run.md §5` and agreed by both of us, for the
reason stated there: *"a shared database makes 'did the extractor write that row
or the harvester' unanswerable from the rows, and a first run is the worst time to
lose that."*

The instance was disposable, so **no artifact of that run is in this tree** — no
completion, no token count, no provider response. `how-it-works.md` already says
so in the paragraph beside the token figures: the 2,010 and 589 are constants in
`budget.py` pinned by a test, and they cannot be recounted.

**So "eight claims stored" was wrong twice over, and both halves were mine.**
Wrong verb — the extractor *proposed and verified* them; nothing stored them.
Wrong database — the run deliberately never touched the DSN above.

## 3 · Why `claim` is 0 on that DSN, and what has to change before it isn't

Three independent blockers, in the order they bite:

1. **`judge/pipeline.py:149`** resolves
   `model_version_of.get(claim.model_ref.resolved_version_id or "")`. The
   extractor is never shown the registry — the system prompt carries no canonical
   id and the schema field defaults to `None` — so the key is `""`, the lookup
   returns `None`, and every claim is dropped with a log line. **Demonstrated
   against a complete 340-id map, which changed nothing.** The fix is to resolve
   from `surface`, which the extractor does emit; that is the `resolve()` change,
   it is **built nowhere**, and `collect/` owes you a surface-keyed map for it
   (`extraction-unresolved-counters.md §4`).
2. **`capability` holds 0 rows** on that DSN. `claim.capability_key` is
   `NOT NULL REFERENCES capability(key)`, so an insert fails the FK even with (1)
   fixed. `registry load-capabilities` exists and has never been run there.
3. **`thread_extraction` was missing** — fixed, see §5.

## 4 · The seat was an alias over a polled row, not a fixture edit

I was told the seat was `claude-opus-4.8` hand-added to
`contract/seed_models.yaml` with `provenance: seed` and committed. **It is not
there.** Checked, not inferred:

- Not on disk, and **not on `origin/main`** — that file holds **11** models and
  was last touched by `59d8b59`, well before any of this.
- **No ref has it.** Swept every local branch, every `refs/remotes/origin` branch
  and the stash for `opus-4.8` in that file: zero hits. The stash's copy holds 10
  models.
- **No commit anywhere** adds the string `claude-opus-4.8` to `contract/`
  (`git log --all -S`).

**What actually happened:** `registry seat-alias anthropic/claude-opus-4.8`, which
reads the reviewed artifact `docs/proposals/alias-surfaces-tracked-set.yaml` and
writes **`model_alias` rows only**. By construction it cannot write a seed row —
`seat.py` takes facts from `model_version` and surfaces from the artifact, and a
model absent from `model_version` cannot be seated at all. 7 declared surfaces → 4
alias rows → 3 search-eligible.

**And it did not need a seed entry**, which was the whole point: `opus-4.8` is
already a **polled** row. On that DSN, `model_version` holds **342 rows, every one
`provenance: 'polled'`**, and all 41 attested seats in the artifact resolve to a
row there. `assert_no_fixtures` reads `model_version.provenance = 'seed'` and
finds **0** — it passes, and on that database it is currently vacuous.

**So there is nothing to remove and nothing to re-do.** The path you would want —
seat an alias over a polled row rather than add a seed entry — is the path that was
taken.

## 5 · Your fixture flag still stands, in a different direction

You flagged `seed_models.yaml` still being listed under *build fixtures currently
in place*. That flag is right, and here is the accurate version of it:

- **Retired in practice on that DSN** — 0 seeded rows, so its removal condition
  ("when OpenRouter polling lands") is met on the one database that matters.
- **Still load-bearing everywhere else** — the file exists, `load_seed` runs, and
  it is still **the only writer of `model_alias` in the codebase** until
  `registry load-tracked-set` is built. `seat-alias` is the second reader of a
  reviewed list and seats one model at a time, by hand.
- **And the database cannot tell the two apart.** `model_alias` has **no
  `provenance` column**, so a row `seat-alias` wrote from a reviewed artifact is
  byte-indistinguishable from one `load_seed` wrote from the fixture. I suspect
  that is why a contract edit looked like the explanation for the seat — from the
  rows alone, it is not distinguishable from one. That is an argument for the
  column, and in the meantime for the reviewed-seat manifest in
  `seating-the-attested-set.md §3`.

## 6 · Migrations applied to that DSN, and what the third one was hiding

**Write, on `postgresql://bv_agent@52.17.75.29:5432/Model-information-Board`.**
Code: `collect/migrate.py` and the three files below, **all on `origin/main`**.
`preflight ok in 'staging': 3 passed, 0 failed, 1 skipped`, then `6 applied, none
pending`.

| migration | effect |
|---|---|
| `20260818T1830_thread_extraction.sql` | created `thread_extraction` — your blocker |
| `20260818T2010_..._fingerprint.sql` | `content_fingerprint`, queued behind it |
| `20260819T0915_harvest_run_columns.sql` | `harvest_run.outcome`, `pages_fetched`, `pages_stored`, `sieve_pass_rate`, plus `harvest_run_outcome_ck` and `harvest_run_finish_ck` |

**The third one nobody had flagged, and it was the next blocker in line.**
`ops/ledger.py:_HARVEST_RUN_COLUMNS` names all four of those columns, so the
harvest_run writer would have failed with `UndefinedColumn` on the first sweep —
directly behind the foreign-key blocker #125 cleared.

Counts, since ours differed: the contract declares **30** tables, that database
had **29**, exactly one was missing, and it is **30/30** now. `check()` reports
`mismatched=[]`, so no content-hash drift on the three already applied — and
`20260818T1610_thread_context_coverage` did take effect: `observed_children`,
`hidden_children_min`, `hidden_branches_unsized` and the generated
`coverage_ratio` are all present.
