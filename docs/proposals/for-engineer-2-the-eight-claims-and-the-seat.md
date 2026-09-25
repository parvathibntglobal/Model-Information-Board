# For Engineer 2: what produced the eight claims, and what the seat actually was

**Your search was right and nothing was unpushed.** Every change behind the eight
claims is on `origin/main` and has been since 2026-08-19. The reason you cannot
find them in a database is not a missing branch — it is that they were never
written to one, and the run that produced them was pre-registered to a disposable
instance on purpose.

**And one correction to what you were told about the seat: it was not a
`contract/` edit.** `claude-opus-4.8` is not in `seed_models.yaml`, on any ref.

*Engineer 1 · 2026-08-20 · no code in this document*

**DSN for every figure below:** `postgresql://example_user@203.0.113.5:5432/Model-information-Board`
— read-only except where §5 says otherwise.

---

## 0 · You have been told three different things. This is the fourth, and every line of it carries the command that checks it

Three accounts of one run have now reached you, at least two of them from me. The
answer to that is not a fourth confident paragraph — it is a table you can run.

| statement | how to check it | result |
|---|---|---|
| nothing was unpushed | `git merge-base --is-ancestor ee5b702 origin/main` | passes; merged by `d35d25b` (#116) |
| the code behind it is unchanged since | `git log ee5b702..origin/main -- judge/extract/{verify,schema,client}.py` | empty |
| `find_model` never existed | `git grep -n find_model $(git rev-list --all)` on `judge/`+`collect/` | no definition, ever |
| `SeedModel.name` never existed | `collect/registry/models.py:167` | fields are `canonical_id`, `provider`, `family`, `display_name`, `slot`, under `extra="forbid"` |
| `resolve()` was already on main | `4f960ac` (`collect/triage/entity.py`), `792000a` (`judge/extract/resolver.py`) | both ancestors of `origin/main` |
| no seed entry exists for `opus-4.8` | `git grep -lEi "opus[-. _]?4[-. _]?8" <every ref> -- contract/*` | zero hits, any spelling |
| nor is one uncommitted | `git status --porcelain -- contract/seed_models.yaml` | clean |
| `opus-4.8` is a **polled** row, both databases | `SELECT provenance FROM model_version WHERE canonical_id ILIKE '%opus-4.8%'` | `polled` on staging **and** on `localhost:5433` |
| the alias rows exist | `SELECT count(*) FROM model_alias` on `localhost:5433/modelboard_test` | **4** |
| the eight claims are in **no** database | `SELECT count(*) FROM claim` | **0** on staging, **0** on `localhost:5433` |

**The last two lines together are the finding.** The four alias rows are still
present, and `tests/conftest.py` runs `DROP SCHEMA public CASCADE` before every
test — so their survival proves **no drop has happened since the seat**. Any claim
inserted after the seat would therefore still be there too. `claim` is 0. **The
claims were never inserted, not inserted-and-lost.**

### So "the claims came from data arriving" does not hold either, and this is why

`judge/` **never reads `model_alias`** — not one file in the lane mentions the
table. And `pipeline.py:150` keys on `claim.model_ref.resolved_version_id`, which
**nothing in production code ever sets**: the only writers of that field in the
whole tree are test fixtures, all of them assigning
`"google/gemini-2.5-flash"` by hand.

So an alias row could not have made those claims resolve, and removing one could
not have unmade it. A `model_version` row plus an alias is exactly the state that
exists right now on `localhost:5433` — 340 polled rows, 4 alias rows — and `claim`
is 0 in it. **The eight claims were extractor output that the pipeline dropped**,
and the only thing that changes it is the unbuilt `resolve()`-from-`surface` fix
in §3.

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

### Verified mechanically, not remembered

```
commit ee5b702   on origin/main   judge: two defects the first live run found
path  judge/extract/verify.py    on origin/main (last ee5b702)
path  judge/extract/schema.py    on origin/main (last ee5b702)
```

`git merge-base --is-ancestor ee5b702 origin/main` passes, and `d35d25b` (#116)
is the merge that brought it in. **And nothing has touched those files since:**
`git log ee5b702..origin/main -- verify.py schema.py client.py` is empty, so the
code at that commit and the code on `origin/main` today are the same code.

**One thing that cannot be confirmed, and it should be said rather than glossed:**
that the working tree at run time was byte-identical to the commit. The run
preceded the commit that records it, and its artifacts are absent by design (§2),
so the evidence is the commit's own message. `how-it-works.md` already carries
that caveat beside the token figures — *"checked, not confirmed"* — and it applies
here too. What is mechanically established is narrower and still enough: the
fixes are on origin, they are unchanged since, and nothing about them was ever
unpushed.

### `find_model` and `SeedModel.name` never existed

Both were named as fixes behind this run. Neither is a thing:

- **`find_model`** — no function of that name in `judge/` or `collect/`, on any
  ref. `model-page-id-resolution.md §1` already said so; the real defect was that
  `/models/{id}` returned 200 for an unknown id, fixed in `2322482`.
- **`SeedModel.name`** — `SeedModel` has `canonical_id`, `provider`, `family`,
  `display_name` and `slot`, with `extra="forbid"`. There is no `name` field, so
  `.name` on it could only ever have raised — and no commit on any ref changes
  such an expression.

Naming a fix after a symbol that does not exist is what let three accounts of one
run disagree. Hence the two names being retired explicitly rather than quietly
dropped.

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

### What reverting a seed edit would and would not do

Worth stating even though there is nothing to revert, because the two possible
states have different consequences and only one of them survives a revert:

- **The alias rows would stand.** They are database rows; `seed_models.yaml` is an
  input file. Nothing in the codebase deletes an alias row on a file edit —
  `_sync_alias` is append-only and the single write it ever issues against an
  existing row is closing `valid_until`. The same principle is already explicit one
  table over: `load_capabilities` refuses to derive `active` from absence, because
  *"a key that vanishes from the YAML"* must not retire a capability from a file
  edit.
- **What a revert removes is the ability to re-create them**, not the rows. And
  here it removes nothing at all: those four rows came from `seat-alias` reading
  the artifact, not from `load_seed` reading the seed file.
- **And the claims' resolvability was never downstream of either**, per §0 — so
  neither state changes it.

Observed rather than reasoned: `localhost:5433/modelboard_test` right now holds 4
alias rows for `opus-4.8`, 340 polled `model_version` rows, `opus-4.8` among them
as `polled`, and 0 claims.

## 5 · Your fixture flag still stands, in a different direction

You flagged `seed_models.yaml` still being listed under *build fixtures currently
in place*. **That flag is right, and what it names is documentation drift rather
than a live violation.** Not "the violation is on a branch, not on main" — there
is no such branch either:

```
every local branch, every origin branch, the stash, in any spelling
  git grep -lEi "opus[-. _]?4[-. _]?8" <ref> -- contract/*     →  zero hits
git log --all -S"claude-opus-4.8" -- contract/                 →  no commits
```

Three unmerged branches touch `contract/` at all, and all three are
`contract/sources.yaml` for the blog terms deferral. So nothing anywhere seats a
model by editing the shared contract, and nothing is queued to.

Here is the accurate version of the drift:

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

**Write, on `postgresql://example_user@203.0.113.5:5432/Model-information-Board`.**
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

## 7 · What changes going forward, and it is your fix as much as mine

**You raised the reporting gap, and it is the one defect here that produced all the
others.** Three accounts of one run disagreed not because anybody was careless
about the run, but because two facts that decide every such report were carried in
someone's head:

1. **Which database did this touch?**
2. **Is the code that touched it on origin?**

Both were answered from memory for a fortnight. Both went wrong in the same
report — one said *"committed on main"* while the shell sat on an unmerged branch,
in a report whose own subject was that shape. A check that depends on remembering
is a check that holds until somebody is busy.

So they are a command now (`scripts/write_report.py`):

```
python -m scripts.write_report --path collect/migrate.py --commit ee5b702

WRITE REPORT
  DSN            postgresql://example_user@203.0.113.5:5432/Model-information-Board
  ENVIRONMENT    staging
  branch         for-e2-eight-claims-and-the-seat  HEAD 76dbf81
  HEAD on origin/main?  NO   (ahead 2, behind 0)
  path  collect/migrate.py    on origin/main (last a3deeba)
  commit ee5b702              on origin/main
  commit 4c56ee2              DOES NOT EXIST IN THIS REPOSITORY
```

**The convention, for both lanes: every report that names a write carries that
header.** Not "I believe this is on main" — the ancestor check, the DSN with the
password stripped, and the branch the shell was actually on.

Four things it refuses to guess, each one a way a report has already gone wrong
here: it compares by **ancestor relation, not branch name**; it reports a path by
whether its **last commit** is published rather than whether the file exists on
the ref; it says **DOES NOT EXIST** for a sha that isn't an object, which is how
`4c56ee2` was caught; and it **refuses with exit 2** rather than answering if the
comparison ref is missing, because a stale origin turns a NO into a YES.

It prints nothing out of `.env` but the DSN with the password removed. Host, port,
database and user identify which database a write landed in and a report omitting
them is unauditable; the password identifies nothing and belongs in no report.
