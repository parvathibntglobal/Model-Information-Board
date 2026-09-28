# The disjoint contexts, the store gap, and a baseline that changed its mind twice

**The disjointness is by design and documented. The store gap is a store/DB
mismatch, not corruption — the local store is not the store the remote rows were
written against, and the payload rebuilt to a byte-exact hash match. And the
zero-claim run was an artefact of reading the wrong thread: against the corpus
staging actually used, the extractor produces four claims and every one of them
is relayed vendor copy.**

*Engineer 1 · 2026-08-21 · runs in `disjoint-thread-contexts.txt` and
`raw-store-audit.txt`*

---

## 1 · Why the child sets are disjoint — four hypotheses, one answer

| | verdict |
|---|---|
| **H2** the two runs saw different comments from the API | **ruled out.** All 11 selected ids across both artefacts are in the payload, with real scores. |
| **H3** the selector is nondeterministic | **ruled out.** Five runs of `rank_children`'s arithmetic are identical; ties break on `external_id` (`thread.py:224`). |
| **H1** `specificity_score` moved | **not needed** — see §2, something else moves it. |
| **H4** they are not the same kind of artefact | **this is the answer.** |

`fixtures/threads/build.py` says so at the top of its own docstring:

> **Not E3.** `collect/assemble/` is Engineer 1's and is authoritative. This is
> fixture tooling that produces the same SHAPE so `judge/` can meet it before the
> real assembler exists.
>
> child selection is by score alone, where E3 ranks by
> `specificity_score x log(1 + engagement)`

And `CHILD_COUNT = 6` against E3's `MAX_CHILDREN = 5`, because:

> the selection is forced to include specific shapes rather than whatever ranked
> highest — a deleted body, two emoji documents, a run of full blocks, and an
> HTML entity.

So the fixture's children were **chosen to exercise the offset map** — `[removed]`,
emoji, block characters, `&gt;` — and were never ranked. The disjointness is the
design. It is also five children against **six**, not five each.

**The defect was mine**: I ran extraction against judge-side test tooling and
compared the result to an assembler output. Corrected below.

---

## 2 · But the worry was right, by a different route

Today's code reproduces the database's five **exactly, in order**, when handed the
registry alias list. Change one argument and it does not:

```
aliases = registry population (1247)     top5 = oqoc844 oqocu7n oqorjbe oqozyx5 oqoehi3
                                         matches the database: 5/5

aliases = ()   the adapter default       top5 = oqoc844 oqodw1j oqocfjv oqorjbe oqocu7n
                                         matches the database: 3/5
```

`collect/adapters/reddit.py:681` passes `version_aliases=()`. Every one of the
database's five gains **+0.15 from `names_version`** and drops two places without
it:

```
oqoc844   aliases=()  spec=0.45 [has_numbers, has_code]
          registry    spec=0.60 [has_numbers, has_code, names_version]
oqocu7n   aliases=()  spec=0.20 [has_code]
          registry    spec=0.35 [has_code, names_version]
```

So **which five comments a thread is built from depends on whether the caller
remembered to pass the alias list.** Not on a weight — on an argument default.
That is the shape of the worry, one layer over from where it was expected: the
weights did not have to move, because the *input to a weighted component* moves
the ranking on its own.

### And the selector prefers relayed content, which matters for §4

The five it picks score on `has_numbers`, `has_code` and `names_version`. Read
them:

```
oqoc844  270  "Edit: This is from blog: * On ..."          relaying the blog
oqocu7n  241  "for anyone asking about what happens ..."   relaying
oqorjbe   92  "Fable 5 on med is cheaper than Opus 4.8 ... SWE-Bench"  relaying the model card
oqozyx5   49  "Because it requires massive compute ..."    speculation
oqoehi3   83  "It already costs 2x Opus 4.8 (says claude.ai)"  relaying pricing
```

**Numbers, links and version names are what a relay carries.** First-hand
experience — *"it feels slower"*, *"Fable uses up more tokens than a old Porsche
gas"* — has none of those signals. So `specificity_score` systematically selects
the documents the extractor then mis-reads as reports. The two failures in §4 are
not independent; the first stage feeds the second.

---

## 3 · The store gap: a mismatch, not corruption

**63 of 124 refs the database points at are unresolvable. 149 blobs on disk are
referenced by nothing. Zero tombstone markers exist.**

That pattern is not decay. `ENVIRONMENT=staging`,
`DATABASE_URL=postgresql://…@203.0.113.5:5432/…`, `RAW_STORE_PATH=./raw_store` —
**the database is remote and the store is local.** Which is precisely the second
meaning of MISSING that `RawStoreReader` names in its own docstring:

> Takes the store rather than a path, so a caller cannot point this at a
> different store than the one the rows were written against — which is one of
> the two things a `MISSING` outcome means, and the one worth making unreachable
> rather than reportable.

Taking the store object cannot help when the only store available locally is the
wrong one. **I retract the "LOSS" verdicts my first audit printed and the
"unrecoverable" claim I made before it** — those payloads are presumably intact
on the server, and I had no evidence they were not.

### Proof, and the rebuild

The store is content-addressed, so a byte-exact reconstruction must produce the
same ref. Rebuilding `thread_context_eacc17c8af367044`'s flattened text from the
raw payload:

```
selector picks   t1_oqoc844 t1_oqocu7n t1_oqorjbe t1_oqozyx5 t1_oqoehi3
db children      t1_oqoc844 t1_oqocu7n t1_oqorjbe t1_oqozyx5 t1_oqoehi3
SAME FIVE, SAME ORDER: True

root text as `title\nselftext`    3549 chars   hash: no match
root text as `title\n\nselftext`  3550 chars   hash: *** MATCH ***
```

`flattened/sha256/1227b5b3…` restored at its own ref, re-reads `found`, 3550
chars, members identical. **Nothing in the database was touched** — the blob was
missing, not the row, and `write_thread_context` is `ON CONFLICT DO NOTHING`
precisely so an `offset_map` that stored quotes resolve against is never replaced
in place.

One incidental find: `RedditPost.text` joins title and selftext with a **single**
newline (`reddit.py:245`), and the stored document used **two**. Two constructions
of the same string, and only a hash comparison distinguishes them.

### Is missing-with-no-tombstone distinguishable from never-written?

**Tombstoned vs missing: yes.** A tombstone is a marker file carrying
`tombstoned_at`, a reason from `("takedown-request", "upstream-deleted")`, and the
content hash. Deliberate, dated, attributed.

**Missing vs never-written: no, and not from the store alone.** A
content-addressed store has no write log — `put` is idempotent by construction —
so "written and gone" and "computed and never put" leave byte-identical evidence:
an absent file under a path nothing created.

What partially distinguishes them is the row that points at the ref:

- something downstream was derived from the payload → it existed and was read;
- nothing was → **indistinguishable**, and that is 61 of the 63 here.

And a **third state the vocabulary has no member for**: `thread_context` holds one
row whose `flattened_text_ref` is `flattened/inline-see-json`, a sentinel in a
column typed as a location. `parse_ref` rejects it before touching the
filesystem, so the reader raises `ValueError` rather than returning an outcome —
neither FOUND, MISSING, TOMBSTONED nor CORRUPT. Worth a fifth member or a
constraint on the column.

---

## 4 · The baseline, which changed its mind twice

| run | corpus | result |
|---|---|---|
| first | `fixtures/threads/thread-1u1b22l.json` (judge test tooling) | **0 claims** |
| second | `thread_context_eacc17c8af367044` (what staging used) | **4 claims, 0 rejected** |

**The zero-claim run was an artefact of the wrong corpus**, and its stated reason
was about a thread the pipeline never reads. So I withdraw the framing I gave it:
the extractor did not miss `oqocfjv` from the staging corpus, because `oqocfjv` is
not in the staging corpus at all. It is a fixture child, forced in for its emoji.

The real baseline is worse in a more useful way. Four claims, and **every one is
relayed vendor copy**:

```
C0  "So when Fable's classifiers detect a request related to cybersecurity…"   root, announcement
C1  "more than 95% of sessions involve no fallback at all…"                    root, announcement
C2  "We'll keep refining the safeguards to reduce false positives."            root, announcement
C3  "gives 10%+ better results on SWE-Bench"                                   oqorjbe, relaying the model card
```

Three of the four match staging exactly; `C1` replaces staging's *"exceptional
performance in software engineering"*. So run-to-run variance on the same corpus
is **3 of 4 stable, one substitution** — both substituted quotes are from the same
announcement, so the variance is in which sentence of the vendor copy it picks.

**Four for four relayed, zero first-hand, out of a thread whose five selected
comments are all relays.** The two failures the brief names are both present and
they compound: §2's selector prefers documents carrying numbers and links, which
is what a relay looks like, and then the prompt cannot tell a relay from a report.
A fix aimed only at the second leaves the first choosing its inputs.

### The golden set

`fixtures/golden/extraction-reading-baseline--unlabelled.jsonl` — 14 rows, every
`label: null`, nothing labelled by me.

| section | n | unit | what it captures |
|---|---:|---|---|
| **A-on-staging** | 4 | claim | the claims in `claim` today, already counted into a `cell` |
| **B-documents** | 6 | document | one per member, with how many claims were proposed for it — so a **miss** is labellable |
| **C-fresh-run-same-corpus** | 4 | claim | this run, same corpus as A |

Options: `first-hand-observation`, `relayed-vendor-claim`, `over-read`, and
`nothing-here` for section B. Section B exists because the second failure is an
absence, and an absence is only labellable with the text beside it — four of the
six documents had no claim proposed and that may be right or may be the miss.

`fixtures/golden/extraction-baseline-seven--unlabelled.jsonl` is the wrong-corpus
run, kept because its `no_claim_reason` is evidence about the prompt on a thread
of jokes and pricing, and because deleting a run I already reported would hide
the correction.

---

## 5 · There is no NULLS LAST, and the selector defect is upstream of it

Checked before changing anything, because three premises have not held this week.

**`NULLS` appears nowhere in the repository.** No `NULLS LAST`, no `NULLS FIRST`,
and no SQL `ORDER BY specificity_score` at all. `rank_children`
(`collect/assemble/thread.py:207`) calls `score_document(comment.body, ...)` in
Python, per comment, at assembly time. **The column is never read for selection.**

**`document.specificity_score` is NULL on all 64 rows — not 189 of 196.** Zero
scored, not seven:

```
document.specificity_score IS NULL   64 of 64
distinct values                      [None]
scored by source                     blog 0/31   reddit 0/6   github 0/27
```

**And it is a writer gap, not a backfill.** `collect/ops/chain.py:434` lists it,
by name, as what the unimplemented stage starves:

> `Stage("triage", …, starves="document.status and document.specificity_score,
> which no writer sets today — so triage survival has neither a numerator nor a
> denominator")`

Nothing has ever written the column. So the honest finding is not about ordering:
**the column and the selector are two independent computations of the same
quantity, and only the selector runs.** If anything ever ordered by the column it
would order by NULL — the reason that is not a live defect is that nothing does,
which is a property of today's callers rather than of the design.

**`selection_method` already records what happened.** Both reddit contexts carry
`specificity_x_log_engagement@observed`; the other 58 carry `whole_document` (31)
and `issue_body_only` (27), which is correct for single-document blog and GitHub
contexts. The `@observed` suffix is already the treatment being asked for, and
`collect/adapters/reddit.py` says why it never takes the schema default.

### The real defect: the export script's aliases matched nothing

`scripts/export_thread_contexts.py:version_aliases()` returned `r.normalized` —
`registry.aliases.normalize` output, which strips every non-alphanumeric:
`anthropicclaudeopus5`. But `names_version` normalises the **text** with
`sieve.normalize`, which lowercases and collapses whitespace and **keeps spaces,
dots and hyphens**:

```
sieve.normalize(text) = 'fable 5 on med is cheaper than opus 4.8 on xhigh and gives 10%+ …'
```

An alias in the first normal form cannot appear in the second. Measured over this
thread's 195 comment bodies:

| alias set | matches |
|---|---:|
| `r.normalized` — what the function returned | **0 of 195** |
| the same rows' raw `surface` (seed holds 10 models) | 0 of 195 |
| `build_population` surfaces (1247) | **27 of 195** |

**So the script's own control was two copies of the same arm.** It compared `()`
against "the full registry surface set" and recorded *"the aliases are still
inlined in provenance … but they are not the cause"* — because both arms matched
nothing and scored identically. That is why it concluded the staging row was
irreproducible and blamed an unbumped `PIPELINE_VERSION`.

Corrected:

```
matching  0 of 195   oqoc844 oqodw1j oqocfjv oqorjbe oqocu7n   2.5210 1.2459 1.1437 1.1331 1.0978
matching 27 of 195   oqoc844 oqocu7n oqorjbe oqozyx5 oqoehi3   3.3613 1.9211 1.8130 1.5648 1.5508
staging row          oqoc844 oqocu7n oqorjbe oqozyx5 oqoehi3
```

**The staging row is reproducible.** So the unbumped `PIPELINE_VERSION` is a
separate and real hazard — `stable_id` depends on root and version, not content,
so a scoring change would silently reuse an id — but it is not what happened
here.

`version_aliases()` now derives from `model_version` through `build_population`,
returns matchable surfaces, and the export picks staging's five exactly.
`alias_match_count` was added and the provenance records it, because **35 aliases
matching 0 documents recorded identically to 1247 matching 27**. A list is not a
scoring input until something matches it, and presence is what passed.

---

## 6 · Which five the corrected selector picks, and where `oqocfjv` lands

| | five selected | `oqocfjv` rank | selected |
|---|---|---:|---|
| aliases matching 0/195 | oqoc844 oqodw1j **oqocfjv** oqorjbe oqocu7n | **3** of 195 | yes |
| aliases matching 27/195 | oqoc844 oqocu7n oqorjbe oqozyx5 oqoehi3 | **8** of 195 | **no** |

**Fixing the selector removes the only first-hand capability observation in the
thread.**

Its own score does not move: `0.25 [has_numbers]` under both. `oqocfjv` says
*"(Fable uses up more tokens than a old Porsche gas)"* — bare `Fable`, no version
token — so `names_version` gives it nothing while each of its competitors gains
`+0.15` and overtakes it. It falls out on other documents improving, not on
anything about it getting worse.

This is the §2 bias measured from the other side, and it is now a property rather
than an accident: `specificity_score` rewards `has_numbers`, `has_code` and
`names_version`, which are what a **relay of a model card** carries. First-hand
experience carries none of them. So the more correctly the selector runs, the
less likely it reaches the one document in this thread that is a first-hand
report — and §4 already showed the four claims it does produce are four for four
relayed vendor copy.

That is not an argument for leaving the selector broken. It is an argument that
`specificity_score`'s five components measure *artifact density*, and the board
needs first-hand experience, and nobody has checked that those are the same
thing. `contract/harvest.yaml` already says the weights are
*"PROVISIONAL · INTRA-CHANNEL ONLY · NEVER CALIBRATED"*. This is the first
measurement of what they select.

**No rebuild was needed.** Staging already holds the corrected five, and its
flattened payload was restored byte-exact in §3. The artefact producing the wrong
five was the export script, and that is what changed.

---

## Corrections to earlier rounds

- **"The four claims are gone"** — they are not. `claim` holds 4, `cell` holds 2.
- **"The staging input is unrecoverable"** — wrong. Rebuilt to a byte-exact hash
  match and restored.
- **"LOSS"** on 2 of 63 refs in my first audit — withdrawn. Remote DB, local
  store; I had no evidence of loss.
- **"The extractor missed `oqocfjv` and said the document contains no capability
  claims"** — true of the fixture, and the fixture is not a corpus the pipeline
  reads. Against the real corpus it proposes four.
- **"the selection is a function of a number nobody has measured"** — right, and
  it is not a weight. It is the alias list, and §5 sharpens my own §2: the
  adapter's `version_aliases=()` default is one route, and the live one was an
  alias list in the wrong normal form that matched 0 of 195 documents while
  looking like 35 inputs.
- **"NULLS LAST and selection_method need fixing before a rebuild"** — neither
  exists to fix. `NULLS` appears nowhere in the repository, nothing orders by
  `specificity_score`, and `selection_method` already carries `@observed`. The
  column is NULL on 64 of 64 rows, and that is a writer gap `chain.py` already
  names. §5.
- **"189 of 196 rows have no score"** — it is 64 of 64. No row in `document` has
  ever carried a `specificity_score`.

Cost across four extraction calls: **$0.0032**.
