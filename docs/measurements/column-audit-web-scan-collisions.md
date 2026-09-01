# The column audit's web scan: how many collisions, and is scoping derivable

Measured 2026-09-01 for #203, **at commit `4668adb`**. Method and reproduction
at the bottom; every figure below names the population it came from.

The commit matters more than usual here: `main` moved twice while this was being
measured. `db80713` (12:37) declared `claim.extractor_model` as `read` because
the new extractor A/B harness selects it, and `4668adb` (12:49) merged #206.
An early run of this measurement therefore reported a fourth reconciliation
target that does not exist at HEAD — it was reading a contract snapshot that had
changed underneath it, not an effect of any fix. Recorded because a figure taken
against a moving tree has to say which tree.

## The defect

`scripts/audit_columns.py` credits a schema column with a READ when its name
appears in `web/src/**/*.{js,jsx}` in a shape that looks like a field access.
The name must belong to exactly one table, and the shape must match one of three
alternatives:

| | pattern | reads as |
|---|---|---|
| A1 | `\.\s*name` | a member access — `row.reach` |
| A2 | `["name"]` | a subscript |
| A3 | `name\s*:` | an object key |

Column names are ordinary English, and JS builtin accessors are ordinary
English too. When they collide the audit reports a read of a **backend column**
and names neither the web file nor the token, so the person holding the failure
starts from the wrong end of the repo.

Three instances reached a commit. Each was worked around in the frontend rather
than in the audit — most recently `2db0625`, which replaced a working `Set` with
an array **and reworded a comment** so the literal token `size` would not appear.

## A — collision exposure: nine, not thirty

| | count | population |
|---|---:|---|
| schema columns | 319 | every column declared in `contract/column_states.yaml`, which `tests/test_column_states.py` asserts equals the live schema |
| single-owner column names | **193** | of those 319 — the only ones the web check considers at all |
| JS builtin property names | 949 | own property names on the prototype and statics of every builtin reachable from `globalThis`, plus instance-side names, enumerated by `scripts/enum_js_builtins.js` on Node v24.13.1 |
| **collide** | **9** | 193 ∩ 949 |

The nine:

```
capability.description    dedup_cluster.size     document.url
capability.version        model_event.type       role.name
answer.reason             source.platform        task_profile.profile
```

**This is a floor, not a total.** The population is Node's builtins; Node has no
DOM, so element properties (`.value`, `.checked`, `.title`, `.lang`) are absent
from it even though the scanned code is browser code. `.lang` and `.size` were
on nobody's list either, which is the argument against fixing this with a list
of names.

**Nine pending is not the same as nine failing.** Whether a collision trips CI
depends on which state the column declares: `CONSISTENT_WITH` lets `unwired` and
`read` tolerate a spurious read, and only a strict declaration (`reserved`)
turns one into a red build. That is why three surfaced and the rest did not — the
others are quietly propping up declarations that have no real reader.

## The live false positives: six, and four are in the diagnostic bucket

Running the check over the actual tree (25 web files, 193 single-owner columns)
records 28 web-sourced reads. **13 columns have web evidence as their ONLY read
evidence**, and hand-reading all 13 gives:

| column | matched | why it is a phantom |
|---|---|---|
| `watermark.cursor` | `cursor:` | CSS property in a style object |
| `golden_label.label` | `label:` | UI config literal `{label: 'Trivial'}` |
| `audit.verdict` | `verdict:` | JSX prose, *"is not a verdict:"* |
| `author_identity_cluster.evidence` | `evidence:` | UI config object key |
| `role.name` | `.name` | `this.name = 'ApiError'` — `Error.name` |
| `source.platform` | `platform:` | a URL search-param key |

**All four columns sitting in `UNWRITTEN, read` on web-only evidence are
phantoms — 4 of 4.** That is the state the audit's own docstring calls "the
DIAGNOSTIC one: somebody already decided the value matters". Where the evidence
is web-only, the bucket a person would act on is entirely noise.

## B — is "files that consume this table's endpoint" derivable? Yes, for 17 of 31 tables

The chain, and how each hop resolves:

| hop | from | how |
|---|---|---|
| table | SQL string literals in `judge/pages/*.py`, `judge/store/*.py` | `ast` + the audit's own `TABLE_REF` |
| module | a function-level `from judge.pages.X import Y` inside a handler | `ast` |
| path | that handler's `@app.get(...)` first argument | `ast` |
| export | `export const NAME = (...) => request('/path')` | regex over `web/src/api/index.js` |
| file | `import { NAME } from '../api'` | regex over each web file |

Coverage:

| | count |
|---|---:|
| routes in `judge/app.py` | 21 |
| resolving to a SQL-bearing module | 13 |
| `api/index.js` exports resolving to a path | 20 |
| web files importing named api functions | 9 |
| schema tables | 31 |
| **reachable from ≥1 web file** | **17** |
| not reachable — would fall back to scanning nothing | 14 |

It is derivable, and cleanly, because of the one-module-per-page convention in
`judge/pages/`. The 14 unreachable tables are mostly correct: `dedup_cluster`,
`watermark`, `golden_label`, `audit`, `author_identity_cluster` and `source`
have **no endpoint at all**, which is exactly why a web hit on their column
names is a phantom.

Two honest gaps in the chain:

- `/capabilities` reads the capability list from `contract/` YAML, not SQL, so
  `capability` resolves to zero files while `capability.key` has a real-looking
  web hit. That is the `read_not_by_query` case the audit already documents.
- The chain resolves modules by *import*, not by call graph. A handler that
  reaches a table through a helper it does not import directly is invisible.

## C — what each candidate fix actually removes

Measured against the real `CONSISTENT_WITH` vocabulary imported from the test,
not a restatement of it. **The baseline is zero mismatches: CI is green today.**

> **The first version of this table said six.** I had reimplemented the
> declared-vs-discovered comparison as a read/not-read split instead of importing
> `CONSISTENT_WITH`, which is more permissive. Six pre-existing mismatches would
> have made this a standing mess worth a large change; zero makes it a clean tree
> with one bad signal in it — so **the error was in the direction that would have
> justified more work.** That is why the numbers below import the vocabulary
> rather than restate it, and why this note sits here rather than in a commit
> message.

| variant | web-only reads | phantoms left | diagnostic-state phantoms | real reads dropped | CI mismatches |
|---|---:|---:|---:|---:|---:|
| today | 13 | 6 | 4 | — | 0 |
| **+ lexer, + no newline after the dot** | 13 | 6 | 4 | **0** | **0** |
| + drop A3 `key:` | 10 | 4 | 2 | 1 | 1 |
| + scoping | 7 | 1 | **0** | 1 | 2 |
| + drop A3 and scope | 6 | 1 | **0** | 2 | 3 |

Read the second row carefully, because it is the uncomfortable one. **The lexer
changes nothing that matters.** It removes exactly one web hit — the word
*surface* in a docblock, credited to `model_alias.surface` — and that column has
a real SQL read as well, so removing the web hit changes no state, no bucket and
no count. Web-only reads stay at 13, phantoms at 6, the diagnostic bucket at 4.

That is not an argument against landing it. It costs nothing, it is measurably
harmless (0 real reads dropped, 0 mismatches), and it ends the situation where
keeping CI green meant **rewording a comment**. But the step the plan describes
as removing comments and string literals cannot touch this defect class, because
`.size` on a `Set` and `cursor:` in a style object are code. Anyone expecting
step 2 to close #203's three instances should expect it to close none of them.

**Scoping is the fix**: it clears the diagnostic bucket completely, 4 → 0.

### The reconciliations are the fix working, not its cost

Three columns declare `read` and their **only** evidence is an A3 object-key web
hit:

| column | the whole basis of its `read` declaration |
|---|---|
| `source.platform` | `platform: 'arxiv'`, a URL search-param key in `Articles.jsx` |
| `model_version.regions` | `regions: req.hard.regions`, a request-body field |
| `task_profile.raw_text` | `raw_text: task`, a request-body field |

None of the three is a SELECT, and the last two are the frontend *writing* a
request, not reading a column. So the two-to-three "CI mismatches" a scoping fix
introduces are not damage — they are three declarations that have been resting
on noise, becoming visible. They need `write_only` with a `why`, or
`read_not_by_query` naming the real reader if one exists. That is a
`contract/` change, which is why step 3 is a proposal.

**One phantom survives everything: `role.name`.** `.name` also appears inside
`Ask.jsx`, which is legitimately in `role`'s scope, so the collision happens
*inside* the correctly-scoped file. No scoping and no lexer can reach it. That
residual is the honest limit of this approach, and it is also the reason a
denylist keeps looking attractive and still is not the answer — the next
collision will be a name nobody listed.

## Method, and reproduction

```
node   scripts/enum_js_builtins.js > builtins.json      # the 949, reproducible
python scripts/measure_web_scan.py                      # A, B, C
```

Both are committed. The builtin population is enumerated rather than written
down, so it changes with the Node version and says which version it came from.

- The schema is read from `contract/column_states.yaml` rather than a live
  database, so the measurement runs without `TEST_DATABASE_URL`. The
  column-states test asserts the two agree, so this is the same 319 columns.
- **The real `tests/test_column_states.py` could not be run for this
  measurement**: it needs Postgres on 5433 and none was available locally. The
  mismatch counts above come from `discover()` plus the test's own
  `CONSISTENT_WITH`, which is the same comparison the test makes, but the
  end-to-end assertion is unverified here and should be confirmed in CI.
- Phantom-vs-real is a **hand classification of all 13 web-only columns**, with
  a reason recorded per entry. It is a judgement, not a measurement, and the
  reasons are in the table above so it can be argued with.
- The two errors made while measuring — the six-mismatch baseline and the
  fourth reconciliation target that a moving `main` produced — are recorded
  **beside the figures they affected**, in section C and at the top of this
  document respectively, rather than collected here. A caveat filed under Method
  is a caveat nobody reads next to the number it qualifies.
