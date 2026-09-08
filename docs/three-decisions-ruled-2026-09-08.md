# Three decisions, ruled — and one thing the ruling does not do

**2026-09-08, anooj.** Answers to
`docs/proposals/for-the-team-three-blocking-decisions-2026-09-07.md`, all three
implemented, plus arXiv and X ratified into `contract/sources.yaml`.

Read §4 before acting on §1–3. It is the part that says what is *not* true.

---

## 1 · arXiv and X proceed, on the same footing as Reddit

Both are now in `contract/sources.yaml` — `arxiv-api-terms` and
`x-via-rapidapi-scraper`, `reviewed_by: anooj`,
`basis: internal-development-only`, 90-day expiry. Both source rows are seeded
(`arxiv` 0.70, `x` 0.60). The five blocks that were in
`docs/proposals/new-platform-sources.draft.yaml` are now three: **the two
ratified rulings were MOVED, not copied.** Two files declaring one ruling id
makes the gate's answer depend on which file a caller loaded, and
`scripts/smoke_new_adapters.py` now refuses an id found in both.

**The robots reading did not change and the ruling does not resolve it.**

```
export.arxiv.org/api/query     200, Disallow: /     THE HOST WE CALL
arxiv.org/abs/…                200, allowed, Crawl-delay: 15
twitter241.p.rapidapi.com      200, Disallow: /     THE HOST WE CALL
reddit34.p.rapidapi.com        200, Disallow: /     harvested today
```

`docs/measurements/new-platform-robots-2026-09-07.json`, unchanged, and it stays
the evidence. `arxiv-api-terms` records
`robots_api_host_disallows: [true]` as recorded evidence rather than dropping
the inconvenient half of its own measurement.

**What the position rests on is the condition, not a reading of robots.** While
nothing is published externally, arXiv and X proceed. The moment anything is,
both rulings stop applying and the terms documents have to be read first — three
of them on X's reseller route, two on arXiv's.

X inherits Reddit's precedent because it is the same case rather than an
analogous one: one gateway, one `RAPIDAPI_KEY`, one billed subscription, the
same `Disallow: /`, and `reddit-via-rapidapi`'s live precondition is the access
path rather than robots. It inherits the four unresolved conditions with it —
reseller credentials, author display against `handle_hash`, deletion against
NFR-4's immutable store, and an unread allowance — and it is escalated **with**
Reddit's rather than separately, as one question about one gateway.

**Neither ruling claims a terms document has been read.** Both record
`terms_document_read: [false]`. Ratified is not read.

### The publication trigger, defined

`reddit-via-rapidapi` has said *"RE-REVIEW REQUIRED BEFORE: any external
publication"* since 2026-08-18 and never said what publication meant. An
untriggered trigger and an undefined one look identical from inside the
repository. It is now defined once, in `contract/sources.yaml`, and all three
rulings point at it:

> **A quote from a platform, shown with a link, to somebody outside the team.**

Not a launch. **One reader who is not one of us is enough** — a demo to a
prospective user, a screenshot in a deck, a link to a deployed build, a shared
PDF of a board page. A launch is an event we would schedule and therefore
remember; every instance of this trigger that has nearly happened would have
been one person's afternoon decision, which is the class of thing a recorded
condition has to cover.

### Where the board stands against it — and the "demo" framing is half wrong

Not tripped. **But the reason is the audience, not the data**, and the proposal's
framing needs correcting on this one point.

The only page carrying an `illustrative` badge is Landing's throughput panel
(`web/src/routes/Landing.jsx` — 10,000 / 1,200 / 1,700 / 96), which is invented
and labelled. **The Articles pages are not illustrative.**
`web/src/data/articles.js` imports ten static platform files for DeepSeek V4
Pro carrying real verbatim quotes, real handles and real permalinks:

| file | records | fields |
|---|---|---|
| `deepseek-v4-pro-x.json` | 149 posts | `handle`, `profile_url`, `status_url`, `quote` |
| `deepseek-v4-pro-reddit.json` | 150 posts | `author`, `url`, `excerpt` |
| `deepseek-v4-pro-hn.json` | 34 posts | `author`, `url`, `quote` |
| `deepseek-v4-pro-devto.json` | 53 posts | `author`, `url`, `excerpt` |
| `deepseek-v4-pro-arxiv.json` | 43 articles | `authors`, `abs_url` |

So the demo already holds quote + attribution + link at real scale, for exactly
the two platforms whose rulings turn on this condition. What keeps the trigger
untripped is that **nothing is served to anybody outside the team** — not that
the quotes are stand-ins. The distinction matters because *"it is only a demo"*
is how this gets tripped: the sentence is true about the audience and false
about the content, and the audience is the half that changes with one URL.

**The sign-in does not narrow this**, because the route guard is client-side
and the ten JSON files are imported into the bundle — so a deployed build is
published under this definition whether or not anyone logs in.

That is a **frontend deployment decision, not a pipeline finding**, so it does
not sit here: it went to the frontend owner as
[issue #225](https://github.com/parvathibntglobal/Model-Information-Board/issues/225),
with the options, and is written up in
`docs/for-the-frontend-owner-the-bundle-is-the-access-boundary.md`. Recorded in
this document only because the ruling's trigger turns on it.

---

## 2 · Thread-level subject for Hacker News — subject gate only

**Yes, and scoped.** The unit of triage is the thread *for the subject gate*,
on platforms whose subject line is a separate record — Hacker News alone today,
Hugging Face discussions next on the same argument.

`Document.thread_subject_text` carries the root's text.
`TriageResult.subject_was_inherited` is set on every inherited document and
`TriageRun.subject_inherited` counts them, so a survival figure can never pool
two reading units silently — `describe()` says the population is mixed when it
is.

Three constraints make it a reading rule rather than the refused resolution
rule, and all three are enforced in `triage()` rather than remembered:

1. **the document's own text is resolved first and wins.** A comment that names
   a model itself is not an inherited document, however clearly its root also
   names one.
2. **the root is consulted only where the document resolved nothing.** A
   fallback, not an expansion of the match set.
3. **`out_of_window` gets the document's own matches and never the union.** An
   inherited subject may KEEP a document and may never DROP one. A comment
   placed outside a release window on a model named only in a title three
   replies up is an invented definite answer (rule 6), and it would be
   invisible, because the document would be gone.

Subject inheritance as a **resolution** rule stays refused
(`docs/proposals/for-engineer-2-inherited-subjects-and-family-claims.md`).
`judge/pipeline.py:subject_was_inherited` answers that question separately, in
code, and `quote_subject_verdict` returns `QUOTE_NAMES_NOTHING` for exactly this
case — so the weighting decision on it is unchanged and still Engineer 2's.

**`thread_root_id` is therefore load-bearing, not decorative.**

**Supplied as of 2026-09-08, and this paragraph said the opposite for one
afternoon.** It read *"the gate accepts the root text; nothing supplies it yet"*
— true when written and inert as a ruling, which is a note rather than a
control. `collect/triage/run.py` now does the join and
`collect/ops/chain.py` carries `Stage("triage", run=_triage_stage)`.

The root needed **no new storage**: `document.thread_root_id` already points at
the root's own row and that row already carries a `text_ref`, so the subject is
`thread_root_id → text_ref → raw store → the platform's prose function`. Cost is
one raw-store read **per distinct thread root**, cached per run — 584 reads
behind GitHub's 2,016 children, 1:3.45.

Two things measuring it turned up: **all 1,420 stored Reddit children have a
`thread_root_id` that resolves to nothing** (two writers, two conventions for one
column), and **there is no HN corpus on staging at all**, so the join is proven
by 15 database-backed tests rather than by a sweep. Both in
`docs/triage-first-run-2026-09-08.md` §3, along with the measured counterfactual
for widening the ruling to GitHub — 42.9% → 74.0%, which is the input to that
decision and not the decision.

---

## 3 · `document.lang` is un-reserved

`write_only`, `reviewed: true`, with the `why` on the entry.
`collect/adapters/documents.py` names the column in `_INSERT` and the key in
`as_row` — both moved together, because `scripts/audit_columns.py` credits a
dict key in a module that INSERTs as write evidence, and only one of the two
moving is the mismatch `tests/test_column_states.py` caught the first time.

It does **not** make the language gate runnable: no detector is installed, no
allow-list is configured, and `wrong_language` still reports UNAVAILABLE. The
value is a *recorded field* — the platform's own declaration (dev.to's
`language`, X's `lang`), never an inference — which is what rule 8 permits for a
check whose error rate nobody has measured.

Done now rather than after the next sweep because the input cannot be
back-filled without re-reading every stored payload. The 6,502 existing rows
keep their NULLs, and a platform that declares no language still gets none. The
declared value is stored as sent: `qme`, `zxx` and `pt-BR` are the platform's
answers, not ours to normalise.

---

## 4 · What nothing enforces — and the honest answer is *no*

The ruling asked for this explicitly, and it is the part worth reading twice.

**What is enforced**, on all three internal-only rulings:

`use_basis` is re-read on every run. `observe_reddit_use`, `observe_arxiv_use`
and `observe_x_use` all return `internal-development-only` unless
`ENVIRONMENT=production`, in which case `assert_terms_reviewed` refuses the
source and the harvest stops. That is real and it fires — and the three now
share one observation (`collect/adapters/basis.py`) rather than three copies
that drift, because a basis read as internal by two adapters and not the third
would refuse one platform and pass two on the same deployment, reading as a
platform problem.

**What is not enforced:**

> ⚠ **Nothing in the pipeline would notice if the publication condition were
> breached.** There is no check anywhere that observes whether a quote has been
> shown with a link to somebody outside the team. Not a gate, not a weight, not
> a counter. If a build were deployed tomorrow with those 149 X quotes and 150
> Reddit quotes in the bundle, every terms assertion in this repository would
> still pass.

Three reasons, structural rather than missing work:

1. **The gate is on the fetch path; publication is on the serve path.**
   `assert_terms_reviewed` has one `harvester_for_source` caller per adapter
   plus the callers CLAUDE.md's Conventions list — every one a fetch.
   `judge/app.py`, `judge/gate.py` and the web bundle consult no ruling and
   reference none. A breach stops the *next harvest* at worst, and never the
   page.
2. **`use_basis` observes `ENVIRONMENT`, which is a different fact.**
   `observe_reddit_use` said so in its own docstring before any of this: a
   proxy that catches a production deployment inheriting a development-only
   ruling, and does not catch a staging instance that has acquired external
   users. Publication is a property of *who is looking*. No environment
   variable knows that.
3. **The Articles data is static and already built.** Those ten JSON files are
   imported into the bundle. Nothing re-derives them at serve time, so there is
   no moment at which code could be asked to check a ruling.

**So the control is a person, and this document says so rather than implying a
guard.** The condition is honoured by whoever is about to show the board to
somebody; what the repository contributes is that they can find out what the
condition is *before* they do it. Anyone who wants an actual guard should read
this as the argument for building one — the cheapest candidate is a serve-path
check that refuses to render a quote whose source row's ruling rests on
`internal-development-only`. **It does not exist and is not scheduled.**

---

## What changed, by file

| | |
|---|---|
| `contract/sources.yaml` | two rulings, two source rows, the publication definition, the ENFORCEMENT block |
| `contract/column_states.yaml` | `document.lang` reserved → `write_only`, reviewed |
| `collect/adapters/basis.py` | **new** — the shared `use_basis` observation |
| `collect/adapters/{reddit,arxiv,x}.py` | all three observe the basis through it |
| `collect/adapters/documents.py` | `lang` in `_INSERT` and `as_row` |
| `collect/triage/gates.py` | `thread_subject_text`, `inherited_surfaces`, `subject_was_inherited`, `TriageRun.subject_inherited` |
| `collect/adapters/hackernews.py` | `thread_root_id` recorded as load-bearing, and the missing join named |
| `collect/config.py` | `scraper_provider` — the ruling pins it |
| `.env.example` | **a real defect fixed**: a second `RAPIDAPI_KEY=your_rapidapi_key_here` sat below the first, and dotenv keeps the last assignment — a filled-in key was being overwritten by the placeholder, arriving as a gateway 401 that looks like the platform refusing us |
| `docs/proposals/new-platform-sources.draft.yaml` | arXiv and X removed (moved, not copied); three left |
| `scripts/smoke_new_adapters.py` | merges contract/ over the draft, refuses an id in both, reports provenance per platform |
| `tests/test_arxiv_and_x_terms_gate.py` | **new** — 26 tests on the two rulings, including that the enforcement disclaimer is present |
| `tests/test_triage_gates.py` | 10 tests on the inheritance boundaries |

**Suite: 2,948 passed, 1 pre-existing failure**
(`test_export_source.py::test_the_handoff_export_loads_with_typed_spans` — reads
the gitignored `_handoff/`, which holds 12 thread files against the test's
expected 2; it imports only `judge/extract/`, untouched here).

Eight tests had to be updated, and every one of them was a guard asserting the
old state rather than a test that broke — the platform set, three row counts,
`document.lang`'s absence from the INSERT, and one that is worth naming
separately: `test_the_observation_reports_production_as_not_internal` patched
`collect.adapters.reddit.settings`, which stopped reaching the read when the
observation moved to `collect/adapters/basis.py`. **The failure was one-sided.**
The staging case still passed, because an unpatched read in a development
checkout returns the same answer; only the production case failed. A test that
patches the wrong module and still passes is the shape this repository keeps
finding, so the docstring now says where the patch has to land and why.

**Nothing was written to the shared staging database.** `registry load-sources`
would now insert two new `source` rows there, and that is a coordinated write —
it has not been run, and nobody has seeded `arxiv` or `x` on staging.
