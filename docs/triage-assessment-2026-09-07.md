# Triage as it stands, and what it would do to five new platforms

**Assessment of `collect/triage/`, 2026-09-07.** It was read-only when written;
**two of its recommendations have since been built** and this document has been
updated rather than left to go stale — a claim about wiring goes stale silently,
which is the one thing `CLAUDE.md` says to re-check rather than re-read.

    R1  the bot list DETECTOR and plumbing   BUILT. The list is a contract/
                                             change and is proposed, not taken.
    R2  `is_self_post` for Hacker News       BUILT.
    R3, R4, R5                               unchanged, and R4 is now a decision
                                             put to the team in
                                             docs/proposals/for-the-team-three-
                                             blocking-decisions-2026-09-07.md

Everything measured below was measured before those two changes and none of it
is invalidated by them: no gate has started writing verdicts.

Measurements this rests on, all persisted:

```
docs/measurements/gate-shape-new-platforms-2026-09-07.json     length distributions
docs/measurements/entity-gate-on-hn-threads-2026-09-07.json    the decisive one
docs/measurements/new-adapter-smoke-2026-09-07.json            what the new writers wrote
```

---

## 0 · The headline, before the gate-by-gate detail

**No gate has ever written a verdict.** `triage_verdict` is NULL on **6,502 of
6,502** `document` rows on the shared database, and `filter_reasons` is set only
by `github.write_comments`' bot rule — never by a triage gate. The `triage`
stage in `collect/ops/chain.py` is `run=None`. The gates are called from
`tests/` and from `scripts/labelling_pools.py`, and from nowhere that writes.

So every figure below is about **what the gates would do**, not what they have
done. `ops/alerts.py:triage_survival` already says this in the one place a
reader would look for a number:

> *"no triage gate sets document.status, so survival has no numerator and no
> denominator"*

That is the correct state to be in — rule 8 makes the whole stage a decision
about promotion rather than a wiring job — but it means the phrase "triage
survival" currently describes an intention.

---

## 1 · Which gates run, and which do not

`collect/triage/gates.py` implements six. `triage()` runs all six on every
document with no short-circuit, so the table is about what each one *answers*,
not about what is reached.

| Gate | State today | Why |
|---|---|---|
| `wrong-language` | **UNAVAILABLE, whole corpus** | No allow-list is passed by any caller, and `allowed is None` is checked first, so this reports UNAVAILABLE rather than per-document NOT_APPLICABLE. No detector is installed and `pyproject.toml` declares none. `document.lang` is NULL on 6,502 of 6,502 rows. |
| `known-bot` | **UNAVAILABLE, whole corpus — now PER SOURCE** | Rule 5 puts a filter rule in `contract/`, and there is no bot list in any file there. Since 2026-09-07 the gate loads one through `collect/triage/bots.py` and matches on the **stable account id**, so an absent file is UNAVAILABLE everywhere and a *declared* file leaves only the platforms nobody has curated UNAVAILABLE — the count now falls platform by platform instead of all at once. `contract/bots.yaml` still does not exist. |
| `pure-link-post` | **NOT_APPLICABLE off Reddit and Hacker News** | Needs `Document.is_self_post`. Reddit set it, and Hacker News now does too (`is_self_post_of`, added 2026-09-07): a story with a `url` and no `text` is a link post, a story with `text` is a self post, a comment is neither. Blogs, GitHub issues and arXiv entries have no such notion, and guessing `False` would drop them all. |
| `out-of-window` | Runs, and **NOT_APPLICABLE in three common cases** | No surface matched; no matched surface has a known owner (a declared-only surface carries none); an owned surface resolves to several models whose window flags disagree. |
| `too-short-no-artifact` | **Runs** | Pure text. |
| `no-resolvable-entity` | **Runs** | Needs the surface population, which every caller must build; the verdict is only meaningful beside `population.fingerprint`. |

### The two that could not run are still the same two

The 82.8% survival in `gates.py`'s docstring (1,074 of 1,297) is an upper bound
for two reasons, and **both still hold**:

1. `wrong-language` and `known-bot` remain UNAVAILABLE. Nothing has changed:
   no language detector has been added, and `contract/` still has no bot list.
2. Every post in that corpus was retrieved by a query containing a model name,
   so it is pre-filtered for exactly what the entity gate tests. The figure
   ranks the gates against each other and calibrates nothing.

`TriageRun.describe()` already prints both caveats and separates them
correctly — `never_ran` (a build defect that shrinks when fixed) from
`not_applicable` (a property of the document, permanent). That split is the
right design and it is about to be tested hard: see §3.

---

## 2 · Is any gate platform-shaped when it should not be — or the reverse?

Both, and the second is the more expensive.

### `too-short-no-artifact` is Reddit-calibrated and it does NOT empty the new platforms

This was the worry, so it was measured rather than reasoned.
`MIN_TOKENS = 15`, with the conjunction (*under the floor AND carrying no
artifact*). Each row below is a different population retrieved a different way;
they are **not comparable to each other** as platform properties and none is
comparable to the Reddit corpus.

| Population | n | min | median | max | under floor | has artifact | gate would drop |
|---|---|---|---|---|---|---|---|
| HN comment bodies, `tags=comment` query `Fable 5.1` | 50 | 11 | 63 | 857 | 6.0% | 42.0% | **6.0%** |
| dev.to search blurbs (what the pre-fetch sieve reads) | 30 | 22 | 33 | 53 | 0.0% | 30.0% | 0.0% |
| dev.to fetched `body_markdown` (what the gates see) | 2 | 545 | 772 | 1000 | 0.0% | 50.0% | 0.0% |
| arXiv title+abstract, `abs:"large language model"` | 50 | 99 | 201 | 262 | 0.0% | 50.0% | 0.0% |
| Hugging Face discussion comments | — | | | | | | not measured; n too small |

Reddit's own figure was **1 of 1,297 = 0.08%**. So the floor is ~75× more
active on Hacker News comments and inert on the other three. It does not empty
anything. **The finding is the opposite of the worry: on these platforms the
length gate is nearly a no-op, and the reason is format** — an arXiv abstract
is structurally 100–260 tokens and a dev.to article is structurally long.

One thing the table does say clearly: **the dev.to blurb and the dev.to body
are different documents.** The pre-fetch sieve sees a 33-token median and the
gates see a 772-token median. That is why `devto.py` runs the terms twice and
reports the two separately (`sieve_run` over blurbs, `sieve_stored` over
bodies); quoting the first as if it were the second would be rule 7 exactly.

### `pure-link-post` was NOT_APPLICABLE on Hacker News, where it IS derivable — FIXED

This was the reverse fault. HN has link posts — a story with a `url` and no
`text` is precisely one, and the standalone article sweep found the case that
matters: **a bare GitHub link at 678 points whose evidence was entirely in its
comments.** The gate reads `Document.is_self_post`, nothing set it for HN, so
the gate declared NOT_APPLICABLE — which `NotRun` documents as *permanent, a
property of the document*. It was neither: it was a field nobody mapped.

**Mapped 2026-09-07** (`hackernews.is_self_post_of`, and the properties on
`HnStory` / `HnComment`). Three answers, and the third is the one worth
spelling out: a comment is `None`, identified by its own `type` rather than by
the absence of a `url` — a link post also has no `text`, so an absence test
would call every comment a link post and hand the gate a verdict on a record
the rule is not about. A story with neither a `url` nor `text` also stays
`None`: `False` there would call it a link post with no link.

Same for arXiv in the other direction: an arXiv entry genuinely has no
link-post notion, so NOT_APPLICABLE there is honest and permanent.

The consequence of leaving it: `not_applicable` grows by one per new-platform
document, which is exactly the drift `NotRun`'s docstring predicted, and the
count stops distinguishing "no such concept" from "nobody mapped it".

### `no-resolvable-entity` is keyword-corpus-shaped, and on Hacker News that is fatal

**This is the finding worth acting on.**

The gate was ranked on a corpus retrieved by model-name queries — every
document names a model by construction. The new adapters change the retrieval
shape: Hacker News's unit is *the comment inside a subject thread*, and a reply
inside a thread about a model does not repeat the model's name, it says "it".

Measured over every comment of the two subject threads the smoke run stored
(511 comments, read from stored payloads, no new requests, resolved against the
real 342-model registry population plus the declared seed surfaces):

```
thread 49587217  "Research acceleration: The view inside OpenAI"
                 135 comments · entity gate resolves    4  =  3.0%
thread 49588080  "An Alien Mind"
                 376 comments · entity gate resolves    7  =  1.9%
                 ---------------------------------------------------
                 511 comments · entity gate resolves   11  =  2.2%
```

**The entity gate drops 97.8% of a Hacker News thread.** And the length gate
would drop a further 23 and 56 (17% and 15%) — several times the 6.0% it drops
on the keyword-retrieved population from the same platform.

Two honest caveats on that 2.2%, both of which matter:

- **These two threads are general AI threads, not model-release threads.** They
  are the threads a `Fable 5.1` comment search led to, which is exactly the
  population a subject-thread sweep would pull anchors for — but a thread
  titled *"Claude Opus 5 released"* would resolve far higher. n=2 threads.
- The gate is not wrong about those comments. They genuinely name no model we
  hold. What is wrong is applying a per-document entity test to a platform
  where **aboutness lives on the thread**, which is why `hackernews.py` records
  `thread_root_id` on every comment and refuses to fold the story title into
  `sieve_text`: a 200-comment thread whose title names the model would
  otherwise pass every comment in it, and `candidates` would silently become
  "comments in threads about X".

The same logic reaches Reddit, and the Reddit phase-one pass had already found
it from the other direction: **3 of its 7 surviving items were only phase one
when their comments were read together.**

---

## 3 · What each gate would do to the four new platforms

Reasoned from each gate's own logic and the document shapes, with the measured
figures above where they exist.

| | arXiv (abstract) | dev.to (article) | Hacker News (comment) | Hugging Face (discussion comment) |
|---|---|---|---|---|
| `wrong-language` | UNAVAILABLE | UNAVAILABLE — **and dev.to declares `language` per article** (2 of 2 in the smoke run) | UNAVAILABLE | UNAVAILABLE |
| `pure-link-post` | NOT_APPLICABLE, correctly and permanently | NOT_APPLICABLE, correctly | **NOT_APPLICABLE and should not be** — derivable from a story's `url`/`text` | NOT_APPLICABLE, correctly |
| `too-short-no-artifact` | inert (0% of 50) | inert on bodies (0% of 2); 0% on blurbs | **6% on keyword hits, 15–17% inside a thread** | likely the most active of the five — HF comments include one-line `+1`s and upload notices; the control run's 4 comments included *"Update README.md"* and one with no text at all |
| `no-resolvable-entity` | passes almost always — an abstract names the models it benchmarks | passes on keyword-retrieved articles; a general AI post that mentions the model once in 12,000 characters also passes, so this gate does little work here | **drops 97.8% of a thread** (11 of 511 measured) | repo-scoped discovery means the repo name usually IS the model, but the comment often names nothing — same shape as HN, one level down |
| `out-of-window` | NOT_APPLICABLE wherever an abstract names several models with disagreeing flags — common, since an abstract benchmarks a table of them | applies where one model resolves | NOT_APPLICABLE for the 97.8% with no match; applies to the rest | as HN |
| `known-bot` | UNAVAILABLE — and arXiv has no author identity at all, so the gate could never run here even with a list | UNAVAILABLE | UNAVAILABLE. HN usernames are stable, so a list would work | UNAVAILABLE — **and HF declares `author.type` as `user`/`org` with no bot value**, so nothing on the platform answers the question |

Two platform-specific notes that no gate currently expresses:

- **arXiv is the wrong evidentiary class, and no gate says so.** An abstract is
  a third-party benchmark of somebody else's model, not `own-experience`, and
  `judge/vet/weight.py` tiers on exactly that. Every arXiv document also has
  **no attributable author** — arXiv publishes no stable author id, and a paper
  has many authors — so `documents_without_author` was 1 of 1 in the smoke run,
  by design. arXiv can corroborate the *platform* half of the publication gate
  and never the *voice* half. That is a weighting question, not a gate, and it
  is recorded here because this is where somebody will look.
- **A Hugging Face zero is structural, not silence.** The Hub has no full-text
  search over discussions, so discovery is repo-scoped: a model with no HF repo
  has no discussion surface at all. Measured — `Fable 5.1` matched **0 repos**
  and produced 0 documents, while the `DeepSeek-R1` control matched 20 repos,
  walked 2, listed 100 discussions and stored 8 documents. Rule 4 lives or dies
  on that distinction being visible, so the adapter reports both numbers and
  its `counts()` says the sentence out loud.

---

## 4 · The three specific things

### 4.1 `KNOWN_BOT` reports UNAVAILABLE, and the gap is measurable

Confirmed: **no bot list exists in `contract/`.** `grep -i bot contract/*.yaml`
returns comments about `filter_reasons` and nothing declaring accounts.

The independent measurement, over `_github_comments.json` — **2,016 GitHub
comments, 1,099 distinct accounts**, which is the comment export and *not* the
6,502-document corpus:

```
[bot]-suffixed accounts                26  →  200 comments  ( 9.9%)
'bot' in the login, NO [bot] suffix     7  →   42 comments  ( 2.1%)
```

The seven, and the busiest is the number in the brief:

| login | comments |
|---|---|
| `tenstorrent-github-bot` | **33** |
| `Issues-translate-bot` | 4 |
| `raycastbot` | 1 |
| `QAbot-zh` | 1 |
| `doyouacceptcrypto-bot` | 1 |
| `FacultativeObligatoryBotContract` | 1 |
| `happier-bot` | 1 |

⚠ **CORRECTED 2026-09-07, AND THE CORRECTION CHANGES THE ARGUMENT.** When this
was written the export carried `author_handle` and no `user.type`, so only the
login side was verified. `GET /users/{login}` has since been read for all 33
accounts carrying `bot` in the login
(`docs/measurements/bot-account-ids-2026-09-07.json`):

```
[bot]-suffixed accounts                          26  ->  all declare type: Bot
'bot' in the login, no [bot] suffix               7  ->  all declare type: User
accounts where user.type and the suffix DISAGREE  0
```

The brief's claim is confirmed exactly: **7 accounts, all `type: User`,
busiest at 33 comments.**

**And zero disagreements inverts what I said about the heuristic.** I framed
the `[bot]` suffix as an unreliable proxy for `user.type`. On this population
the two agree perfectly — what they do is **miss the same seven accounts
identically**, because GitHub declares `type: Bot` only for registered GitHub
Apps and a human account running a script is a `User`. There is no third
signal. So a curated list is not the cheaper option, it is the only one, and
that is a stronger argument than the one I made.

Why 33 matters: the busiest human accounts in the same export are
`cdomotor-g` (33) and `SchlenkR` (30). So `tenstorrent-github-bot` is not a
rounding error, it is **joint-busiest voice in the corpus** — and on a board
where `N_EFF_MINIMUM = 3.0` weighted independent voices decides publication, a
third voice that is a CI account is the failure the voice count exists to
prevent.

And `FacultativeObligatoryBotContract` is the reason the list must be a list.
That is almost certainly a person with a joke name. A regex over logins would
filter them and would filter `releasebot` the helpful maintainer; that is the
string-heuristic trap `github.py:is_bot` already refuses, measured against a
denominator of **two accounts** (`github-actions[bot]` and `linear[bot]`), which
is far too small to license the heuristic. The list belongs in `contract/` as
reviewed account ids, per rule 5.

### 4.2 `score-documents` is wired, and nothing runs the chain

Both halves confirmed.

- `Stage("score-documents", run=_score_documents_stage, needs=("preflight",))`
  is real and does the work.
- **Nothing schedules the chain.** `.github/workflows/ci.yml` is
  `on: push: branches: [main]` plus `on: pull_request` — no `schedule:` block.
  No cron file, no scheduled task, no service. The only caller is
  `collect/cli.py:254`, i.e. a person typing it.

Current state on the shared database:

```
                total   has_numbers NULL   has_conditions NULL
github          3,382                 9                    9
reddit          2,999             1,234                1,234
blog              121                 0                    0
                -----   ----------------
total           6,502             1,243  (19.1%)
```

So the sweep has been run by hand at least once and 5,259 rows carry values.
The user's framing is right in direction: **every new write lands NULL and
stays NULL until somebody runs it again.** The seven documents the smoke run
wrote are 7 of 7 NULL on all six columns.

The Reddit 1,234 is worth naming separately rather than pooling: `score_
unscored` leaves a row NULL and *counts it* when the payload is not in the
local raw store, and `ScoreRun.unreadable_by_source` exists for exactly that.
Those rows are most likely unreadable-on-this-host rather than unscored — a
different repair (run it where the store is) from "nobody ran the stage".

### 4.3 Will the new adapters populate the document-facts columns? No — by design

`collect/adapters/documents.py` does not write `has_numbers`,
`has_error_strings`, `has_code`, `has_conditions`, `names_version` or
`specificity_score`, and neither do the three existing writers. That is
`collect/triage/store.py`'s ruling, not an omission:

> *ONE REGISTRY READ, NOT FOUR. `score_document` takes `version_aliases`
> because the registry read belongs once per run… Four adapters each building
> that population is four chances for them to diverge, and a `names_version`
> computed against a different surface set is not comparable to one that was
> not.*

Five more writers would make that nine. So the new adapters land NULL like
everything before them, and the consequence travels with them:
`judge/`'s numbers rung is withheld and `f_specificity` prices both
`has_numbers` and `has_conditions` as absent while they are NULL — which
`_score_documents_stage`'s own `starves=` text already states.

**The one adapter-side change worth making is not those six columns.** It is
`document.lang`, which the adapters can fill and the writer deliberately does
not: `column_states.yaml` declares it `reserved`, and
`tests/test_column_states.py` failed by name when the write was added. The
value is parsed and carried (`DevtoHit.language`, `XPost.lang` — X's route is a
RapidAPI provider and its posts carry `lang` in the tweet object —
`DocumentDraft.lang`) and counted in the write report: 2 of 2 dev.to documents
in the smoke run carry one. Un-reserving the column is a contract line,
proposed rather than taken.

---

## 5 · Recommendations

Ordered by value per unit of risk. **None of these has been applied.**

### Do

**R1 · Write the bot list into `contract/`, as reviewed account ids, and keep
the gate a gate.** — **DETECTOR BUILT 2026-09-07, LIST PROPOSED.**

`collect/triage/bots.py` loads it, `known_bot` matches on the **stable account
id** rather than the login, `collect/cli.py triage bots` prints its state with
no database, and `tests/test_bot_list.py` covers the refusals. Three states are
kept apart by construction: no file (UNAVAILABLE everywhere), a file that
declares nothing for a platform (UNAVAILABLE there, and the count falls as each
is curated), and `accounts: []` (False — somebody looked).

**The list itself is a `contract/` change and is proposed, not taken:**
`docs/proposals/for-engineer-2-the-bot-list.md` carries all 33 resolved
`user.id`s, my reading on each of the seven, and the one I would leave off.

Still true: this is the only one of the six gates whose error rate needs no new
measurement to promote — a list of specific accounts has no false-positive
class beyond "somebody put a human on the list", which review catches.

**R2 · Map `is_self_post` for Hacker News.** — **DONE 2026-09-07.** See §2.

**R3 · Run `score-documents` where the raw store is, and record the run.** It
is idempotent by construction and needs no scheduling decision. 1,243 rows are
waiting; the 7 new ones join them. If the chain is going to stay hand-run, that
is a decision worth writing down beside `default_stages()`, because the
docstring reads as though something fires nightly.

### Decide, don't build yet

**R4 · The entity gate needs a thread-level answer before Hacker News is
swept.** — **PUT TO THE TEAM 2026-09-07**, as the lead item in
`docs/proposals/for-the-team-three-blocking-decisions-2026-09-07.md`, and framed
there as a **reading-rule versus resolution-rule** question rather than as
inheritance. That distinction matters: thread-subject *inheritance* is already
ruled out on measured grounds, and it is a resolution rule about what a claim
may be filed against. What text constitutes an HN comment is a reading rule,
the class ruling 7's locality window belongs to — and GitHub already reads a
comment inside its issue's thread (`issue_with_comments`).

2.2% of 511 comments resolve. Three options, and this is a ruling rather than a
fix:

- *Inherit aboutness from the thread root.* Cheapest, and it converts
  `candidates` from "comments mentioning X" to "comments in threads about X" —
  two different populations, and the second cannot support a claim on its own.
  If taken, the inheritance must be **recorded on the row** so `judge/` can
  tell which kind it has.
- *Gate at the thread and not at the document.* Keep the whole thread when its
  root resolves, and let E3's specificity ranking pick children. Closest to
  what the platform actually is, and it makes the unit of triage the thread.
- *Leave it, and accept that HN yields ~2%.* Defensible, and it means the
  platform contributes the comments that name a model explicitly and nothing
  else — which on the measured evidence is not where the evidence is.

My recommendation is the second, and it is not a small change: it moves triage
from per-document to per-thread for one platform, which needs a verdict shape
that can say so.

**R5 · Un-reserve `document.lang` (contract line) and enable the write.** Two
lines in one PR, listed in the proposal. It does not make `wrong-language`
runnable — no detector — but it makes the input exist for the two platforms
that declare it, and that half cannot be back-filled later without re-reading
every payload.

### Leave alone

- **`too-short-no-artifact` and `MIN_TOKENS = 15`.** Measured inert on three of
  four new platforms and 6% on the fourth. There is no evidence for changing
  the floor, and `has_artifact` reusing the four specificity components rather
  than a private regex is the right construction — the note in its docstring
  about `\bError\b` failing to match inside `TypeError` is the reason.
- **`wrong-language`.** Installing a detector is a dependency decision, and the
  gate correctly reports UNAVAILABLE meanwhile. Adding a `lang == "en"` check
  against a NULL column would silently pass every document, which is worse than
  no gate.
- **`out-of-window`'s three NOT_APPLICABLE cases.** All three are places where
  a definite answer would be invented, and the arXiv shape (an abstract
  benchmarking a table of models with disagreeing window flags) is a new
  instance of the third case rather than a reason to weaken it.
- **The `triage` stage staying `run=None`.** Wiring it now would write verdicts
  from four gates while two are UNAVAILABLE, and `document.status` is what
  `/filtered` and every survival figure read. Rule 8's direction is one-way:
  the missing bot list is a decision, not code, and it should land before the
  stage that acts on its absence.

  **Unchanged by the detector.** Building the loader removed the *code* half of
  one of the two blockers and none of the decision half — `contract/bots.yaml`
  still does not exist, so `known_bot` still reports UNAVAILABLE for every
  document and every survival figure is still an upper bound. What changed is
  that the day the list lands, nothing else has to be written.
