# Every column in the audit's diagnostic bucket on web-only evidence is a false positive — 4 of 4

**Not a bug report about your frontend.** Twice now the fix for this has been to
change working web code — a `Set` swapped for an array in `2db0625`, and its
explanatory comment reworded so the literal token would not appear. The audit
was wrong both times. This is the audit's defect and the fix belongs in
`scripts/audit_columns.py`.

*Engineer 1 · 2026-09-01*

Figures at commit `4668adb`. Reproduce with `python scripts/measure_web_scan.py`.
Full working: `docs/measurements/column-audit-web-scan-collisions.md`.

**Status:** §3 landed as #207. **Scoping (§4–5) is landed in this PR**, with the
two contract reconciliations, after you validated all seven on #203. The
diagnostic bucket is now empty: 4 → 0.

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
enough to tolerate a spurious read: `role.name` (§6.1) and `source.platform` (§5).
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

## 3 · What landed in #207, and what it was worth

Merged as **#207**. Both measured at **0 real reads dropped, 0 new mismatches** —
the baseline is 0 and stays 0.

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

| | before | after (this PR) |
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

**Done, with one caveat.** Scoping needs only two of the three —
`task_profile.raw_text` stays satisfied because `raw_text:` sits in `Ask.jsx`,
which *is* in `task_profile`'s scope; it only breaks if the object-key
alternative goes (step 4). So `model_version.regions` and `source.platform` are
now `write_only`, `reviewed: true`, each with a `why` naming what the apparent
reader actually was. Mismatches after reconciliation: **0**.

> **⚠ One of the two is not yet validated by you, and I would rather flag it than
> count it.** Your #203 reply lists the three reconciliations as
> `capability.key`, `model_version.regions` and `task_profile.raw_text` — but §5
> above had named **`source.platform`** where you named `capability.key`. So
> `regions` is confirmed by you, `capability.key` is answered (a React list key,
> and it turns out to have a SQL read as well, so scoping changes nothing for
> it), and **`source.platform` has only my eyes on it.** Its entry in
> `contract/column_states.yaml` carries that warning inline. If you disagree with
> it, it is a one-line revert and nothing else in the change depends on it.

## 6 · Two residuals, and neither fix reaches both

The two most useful cases in this whole investigation are the ones a single fix
leaves behind. They fail in opposite directions, and **only scoping removes both**
— which is a stronger argument for scoping-first than either instance alone.

### 6.1 · `role.name` — the case SCOPING cannot reach

```
web/src/api/index.js:52     this.name = 'ApiError'
```

That is `Error.name`, read as `role.name`, the only column of that name.

Scoping does not save it. `role` resolves to `Ask.jsx`, `.name` occurs inside
`Ask.jsx` too, and that file is legitimately in scope — **so the collision
happens inside the correctly scoped file.** (After scoping the recorded hit moves
to `Ask.jsx:57`; it does not disappear.) The scanner does not save it either:
`this.name = 'ApiError'` is code.

**An object-type check would.** It asks what the receiver *is* rather than where
the file sits, and `this` in `this.name` is an `Error`. That is the lever in §7.

### 6.2 · `audit.verdict` — the case an AST cannot reach

```
web/src/routes/Models.jsx:359   …is not a verdict: not "good", not "bad"…
```

**English prose.** A sentence with a colon in it, matching the `col:` object-key
alternative. No accessor, no object — *there is no receiver here at all.*

So the object-type check has nothing to inspect and does not resolve this one.
An AST would parse it as JSX text, which is only a fix if the check is taught to
exclude `JSXText` nodes — and the scanner already cannot help, because JSX
children are not string literals and stay marked as code.

**Scoping removes it cleanly**, and for the simplest possible reason: `audit` has
no web endpoint, so no web file is a reader of it. Confirmed by E2 on #203, who
called it the starkest of the four.

### 6.3 · Which is why the answer is not a list of tokens

`.size` and `.lang` were on nobody's list, and a list only ever contains the
collisions somebody has already been bitten by. The residual wants the treatment
this repo already gives evidence the static audit cannot see: `read_not_by_query`
exists for a read the audit **misses**, and the symmetric case is a read the
audit **invents**. Now that the failure names the file and the token, a reviewer
can tell the two apart in one read instead of grepping 25 files.

## 6A · None of the seven wants a code change

Worth stating plainly, because every fix so far has been a rename.

| | what the audit matched | what it is |
|---|---|---|
| `watermark.cursor` | `cursor:` | a CSS property in an inline `style={{}}` |
| `golden_label.label` | `label:` | a difficulty-label UI string |
| `audit.verdict` | `verdict:` | a sentence with a colon |
| `author_identity_cluster.evidence` | `evidence:` | a filter-config key |
| `capability.key` | `.key` | a React list key on a bucket |
| `model_version.regions` | `regions:` | an outgoing request body field |
| `task_profile.raw_text` | `raw_text:` | an outgoing request body field |

**A CSS cursor, a UI label, a sentence with a colon and a config key are all
things the frontend is right to have.** All seven reconcile to *"not read from
the web"* — E2's phrase, validated against the running panels on #203, with line
numbers for each.

Twice the fix was to change working web code: `2db0625` swapped a `Set` for an
array **and reworded its comment** so the token would not appear. That is the
audit asking the frontend to contort around database names, and it is the actual
defect being closed here. No web file changes in this PR.

## 7 · Sequencing

```
1  message + scanner                LANDED, #207. 0 mismatches, ruff clean
2  agree the reconciliations in §5   DONE. You validated all seven on #203;
                                     source.platform is the one exception, §5
3  scoping + the reconciliation      LANDED HERE, one change, so the audit and
                                     the contract move together and CI never
                                     sees a state it cannot explain
4  the object-key alternative        separately. Removes 2 more phantoms for 1
                                     more reconciliation, and is defensible on
                                     its own terms: an object key is a name
                                     being WRITTEN, not a column being read.
                                     Deserves its own argument, not a ride-along
5  a real AST + object-type check    NOT NOW. The named lever for §6, agreed
                                     with E2 as the move if role.name bites
```

**The lever for §6.1, named rather than left to be rediscovered.** Nine
collisions measured against Node's builtins is a **floor rather than a count** —
Node has no DOM, so `.value`, `.checked`, `.title` and `.lang` are outside the
population that produced the figure. **An object-type check is the only thing
that reaches a collision inside a correctly-scoped file**, because it asks what
the receiver *is* rather than where the file sits: a real JS AST, and enough type
or flow inference to know that the `active` in `active.size` is a `Set` and the
`this` in `this.name` is an `Error`.

**It is a lever for §6.1 only, not a backstop.** `audit.verdict` (§6.2) is prose
with a colon — no accessor, no object, no receiver to inspect — so the type check
has nothing to work on there. Scoping is the only one of the three that removes
both residuals, which is why it goes first and why this stays step 5.

Not worth a JS toolchain in CI for one case today — one phantom survives scoping,
and buying it costs a `setup-node` step and a parser dependency for a check that
runs beside a Python audit. E2 and I agree that is the move if `role.name` starts
biting, or if the floor in §2 turns out to be well under the real number. Written
down so the next person reaches for it deliberately instead of arriving at it
again from a red build.

**The open question from §7 is answered, benignly.** `capability` does resolve to
zero web files, because `/capabilities` reads its list from `contract/` YAML
rather than SQL. You identified the hit as `key={b.key}`, a React list key on a
bucket — not a read. And `capability.key` turns out to have a SQL read as well,
so losing the web hit changes its state not at all and it needed no
reconciliation. The chain's YAML blind spot is real and stays documented in
`web_scope()`; it cost nothing here.

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
