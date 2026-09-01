# Every column in the audit's diagnostic bucket on web-only evidence is a false positive — 4 of 4

**Not a bug report about your frontend.** Twice now the fix for this has been to
change working web code — a `Set` swapped for an array in `2db0625`, and its
explanatory comment reworded so the literal token would not appear. The audit
was wrong both times. This is the audit's defect and the fix belongs in
`scripts/audit_columns.py`.

*Engineer 1 · 2026-09-01*

Figures at commit `4668adb`. Reproduce with `python scripts/measure_web_scan.py`.
Full working: `docs/measurements/column-audit-web-scan-collisions.md`.

---

## 1 · The finding

`UNWRITTEN, read` is the state the audit's own docstring calls **"the DIAGNOSTIC
one: somebody already decided the value matters"**. It is the bucket a person
acts on.

Four columns are in it on web-only evidence. All four are false positives.

| column | what the audit matched | what it actually is |
|---|---|---|
| `watermark.cursor` | `cursor:` | a CSS property in a style object |
| `golden_label.label` | `label:` | a UI config literal, `{label: 'Trivial'}` |
| `audit.verdict` | `verdict:` | JSX prose — *"is not a verdict:"* |
| `author_identity_cluster.evidence` | `evidence:` | a UI config object key |

**4 of 4.** Not a majority, not a known-noisy signal — the entire contents of the
one bucket that is supposed to mean *somebody has already decided this matters*.

Two more phantoms sit outside that bucket, absorbed by declarations permissive
enough to tolerate a spurious read: `role.name` (§4) and `source.platform` (§3).
Six live phantoms in total, from 13 columns whose only read evidence is a web
match.

That is also why only three of these ever reached a commit. Whether a collision
fails CI depends on which state it lands beside — `CONSISTENT_WITH` lets
`unwired` and `read` swallow a false read, and only a strict declaration turns
one red. The rest have not been waiting to happen. They are here, quietly
holding up declarations that have no reader.

## 2 · The mechanism, which is smaller than it looks

Column names are ordinary English. So are JS builtin accessors.

| | count | population |
|---|---:|---|
| schema columns | 319 | `contract/column_states.yaml` |
| single-owner names | 193 | the only ones the web check considers |
| JS builtin prototype names | 949 | enumerated by `scripts/enum_js_builtins.js` on Node v24.13.1 |
| **collide** | **9** | `answer.reason` · `capability.description` · `capability.version` · `dedup_cluster.size` · `document.url` · `model_event.type` · `role.name` · `source.platform` · `task_profile.profile` |

**Nine is a floor.** The population is Node's builtins and Node has no DOM, so
`.value`, `.checked`, `.title` and `.lang` are not even in it. `.size` and
`.lang` were on nobody's list; the next one will not be either.

Nine is the mechanism. **§1 is the finding.**

## 3 · What has already landed, and what it is worth

In `scripts/audit_columns.py` and `tests/test_column_states.py`. Both measured
at **0 real reads dropped, 0 new mismatches** — the baseline is 0 and stays 0.

**The failure now names your file and the token.** It named a backend column and
nothing else, three times, while the cause was a frontend token and you had 25
files and no line number:

```
watermark.cursor: declared 'unwired', discovered 'UNWRITTEN, read'
      the ONLY read evidence is a web-text match:
      web/src/routes/Articles.jsx:239 web:'cursor:'
      If that token is a JS builtin (a Set/Map/Blob .size, an Error .name, a
      CSS property in a style object, a UI config key) then this is a FALSE
      POSITIVE in the audit — fix scripts/audit_columns.py or scope the scan.
      Do NOT edit the column's state, and do NOT reword the web file to dodge
      the token.
```

**A scanner, so comments and string literals stop counting.** Pure Python, no
dependency: CI installs Python only — no `setup-node` — and `web/node_modules`
does not exist in a fresh checkout, so a real JS AST would mean adding a
toolchain for one check. Also `\.[ \t]*name` rather than `\.\s*name`, which
closes a case the measurement turned up: a sentence-ending full stop in a
comment, followed by a real object key on the next line, was reading as a member
access.

**Be clear about what the scanner buys: nothing measurable.** It removes one web
hit — the word *surface* in a docblock — on a column that has a SQL read anyway.
Web-only reads stay 13, phantoms 6, the diagnostic bucket 4. It closes none of
the three instances, because `.size` on a `Set` and `cursor:` in a style object
are code, not comments. It is in because it is free and because keeping CI green
should never again mean rewording a comment.

## 4 · The ask: scope the scan to the files that consume the endpoint

A web file counts as a reader of table `T` only if it imports an `api` export
whose endpoint resolves to `T`.

Derivability was the open question, and the answer is yes — cleanly, because of
the one-module-per-page convention in `judge/pages/`:

| hop | resolved by |
|---|---|
| table ← SQL literals in `judge/pages/*.py`, `judge/store/*.py` | `ast` + the audit's own `TABLE_REF` |
| module ← function-level `from judge.pages.X import Y` in a handler | `ast` |
| path ← that handler's `@app.get(...)` argument | `ast` |
| export ← `export const NAME = ... request('/path')` | regex, `api/index.js` |
| file ← `import { NAME } from '../api'` | regex, per web file |

17 of 31 tables resolve to at least one web file. The 14 that resolve to none
mostly **have no endpoint** — `dedup_cluster`, `watermark`, `golden_label`,
`audit`, `author_identity_cluster`, `source` — which is exactly why a web hit on
their column names was always a phantom.

| | today | scoped |
|---|---:|---:|
| columns whose only read evidence is a web match | 13 | 7 |
| of those, phantom | 6 | 1 |
| **phantoms in the diagnostic bucket** | **4** | **0** |
| real web reads dropped | — | 1 |
| declarations needing reconciliation | — | 2 |

## 5 · The three reconciliations are the fix working, not its cost

Scoping makes two declarations stop matching, three if the object-key
alternative goes too. **That is not damage.** Those declarations are currently
held up by nothing else:

| column | declared | the entire basis of that `read` |
|---|---|---|
| `source.platform` | `read` | `platform: 'arxiv'` — a URL search-param key in `Articles.jsx` |
| `model_version.regions` | `read` | `regions: req.hard.regions` — a request body |
| `task_profile.raw_text` | `read` | `raw_text: task` — a request body |

Not one of the three is a SELECT. **Two of them are the frontend writing a
request body**, which is the opposite of a read of that column. Remove the noise
and three columns stop claiming a reader they never had — which is the audit
finally doing its job, not the fix breaking something.

They want `write_only` with a `why`, or `read_not_by_query` naming the real
reader if one exists. **I have not touched them.** `contract/` gets two eyes, and
the working agreement is that a state moves with its reason written down rather
than being nudged to whatever makes CI green.

## 6 · `role.name` — the case scoping cannot reach

Scoping leaves one phantom, and it is worth more than the eight it removes,
because it shows where this approach ends.

```
web/src/api/index.js:52     this.name = 'ApiError'
```

That is `Error.name`. The audit reads it as a read of `role.name`, the only
column of that name in the schema.

Scoping does not save it. `role` resolves to `Ask.jsx`, `.name` occurs inside
`Ask.jsx` too, and that file is legitimately in scope — **so the collision
happens inside the correctly scoped file.** The scanner does not save it either;
`this.name = 'ApiError'` is code.

This is the instance to argue from. It is why the answer is not a list of
forbidden tokens: `.size` and `.lang` were not on one, and a list only ever
contains the collisions somebody has already been bitten by. The residual wants
the treatment this repo already gives evidence the static audit cannot see —
`read_not_by_query` exists for a read the audit **misses**; the symmetric case is
a read the audit **invents**, and it wants a declared state with a reason for the
same reason. Now that the failure names the file and the token, a reviewer can
tell the two apart in one read instead of grepping 25 files.

## 7 · Sequencing

```
1  message + scanner                landed. 0 mismatches, ruff clean
2  agree the reconciliations in §5   this document — needs your eyes
3  scoping + the reconciliation      one change, so the audit and the contract
                                     move together and CI never sees a state it
                                     cannot explain
4  the object-key alternative        separately. Removes 2 more phantoms for 1
                                     more reconciliation, and is defensible on
                                     its own terms: an object key is a name
                                     being WRITTEN, not a column being read.
                                     Deserves its own argument, not a ride-along
```

**One open question I have not guessed at.** `capability` resolves to zero web
files, because `/capabilities` reads the list from `contract/` YAML rather than
SQL — yet `capability.key` has a real-looking web hit in `PipelinePanel.jsx`.
Under scoping that read disappears. If it is genuine, the chain needs to be
taught that endpoint; if it is not, the column wants `read_not_by_query`. Your
call, it is your panel.

## 8 · About these figures

Two things went wrong in the measuring, and both belong next to the numbers
rather than in a commit message.

**`main` moved twice while I measured.** `db80713` (12:37) declared
`claim.extractor_model` as `read` for the new extractor A/B, and `4668adb`
(12:49) merged #206. An early run of the measurement reported a **fourth**
reconciliation target that does not exist at HEAD: it had read a contract
snapshot that changed underneath it. Everything above is pinned to `4668adb`,
and the pinning is the point — a figure taken against a moving tree has to say
which tree.

**The first baseline I computed was wrong, in the direction that would have
justified more work.** I reimplemented the declared-vs-discovered comparison as a
read/not-read split instead of importing `CONSISTENT_WITH` from the test, which
is more permissive. That reported **six pre-existing mismatches** when the true
baseline is **zero** — CI is green today. Six would have made this look like a
standing mess worth a large change; zero makes it a clean tree with one bad
signal in it. Recorded because a self-serving error found by its author is still
worth writing down, and because the correction is the reason the tables above
import the vocabulary rather than restate it.

**One limit that is not an error.** `tests/test_column_states.py` needs Postgres
on 5433 and I had none locally, so the end-to-end assertion is unverified here.
The mismatch counts come from `discover()` plus the test's own
`CONSISTENT_WITH` — the same comparison the test makes — but CI is what will
confirm it.
