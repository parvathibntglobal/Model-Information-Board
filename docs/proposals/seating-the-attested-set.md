# Loading the 41 attested seats — what it takes, before any of it is built

**A spec, not an implementation. The instruction is to load the 41 attested
seats, hold the launch-window entries until Engineer 2 rules, and to do it
without making the review optional. The last of those is the whole difficulty:
the artifact has no field that records that a human read an entry.**

*Engineer 1 · 2026-08-20 · nothing built · one `contract/` addition, flagged in §6*

---

## 1 · The population, with three corrections to it

The 41 are `seated_by: attested` — and they are clean on the first guard: **0 of
the 41 carry a blocking `INCOMPLETE` slot** (all 63 carry `family_surface`, which
is permanently incomplete by design and does not block).

**The sweep goes 12 → 47, not 12 → 53.** Six of the 41 already have alias rows:
`anthropic/claude-opus-4.8`, already seated by hand, plus five models that are
also in `contract/seed_models.yaml` — `claude-opus-5`, `claude-sonnet-5`,
`gemini-2.5-flash`, `gemini-2.5-pro`, `gpt-4.1-mini`. Net new to the sweep is
**35**. The `+41` arithmetic assumes the 41 and the 12 are disjoint, and they
overlap by 6.

**The 12 carries a population of its own.** It is the development board, where
`load_seed` has run. `assert_no_fixtures` refuses `model_version.provenance =
'seed'` outside `development`, so on a database where the seed loader has never
run the searchable set is 1 (`opus-4.8`) and loading the 41 gives 41. Which
number is right depends on which database the first sweep runs against — worth
settling before the figure is quoted anywhere.

**41 + 17 is 58, and the artifact holds 63.** There is a third group of **5**,
and it is the interesting one:

| group | count | `status` | `seated_by` | what it is |
|---|---|---|---|---|
| load these | **41** | attested | attested | observed surfaces, cleared the mention floor |
| **unassigned** | **5** | attested | launch-window | observed surfaces, *below* the floor |
| hold these | **17** | mechanical-only | launch-window | no observed surface at all — the guesses |

**And `launch-window` does not mean "nobody has discussed it."** The seating
check's own docstring records that the first version of its condition was wrong on
exactly that belief and fired on 5 correct entries: `cli.py` sets `launch-window`
whenever `BY_MENTIONS` is absent, and `BY_MENTIONS` requires `mentions >= floor`,
so a model with 13 mentions against a floor of 20 is attested, seated by the
window, and seated exactly as the policy intends.

So the rationale for holding — *guesses about what people will write for models
nobody has discussed* — describes the **17**, which is the count that docstring
also names. The 5 are attested below the floor, and **they include both deepseek
reseats**: the only entries in the file carrying hand-written surfaces, and the
ones a rule of "load the attested-seated" leaves out. E2's outstanding review
covers all **22** launch-window seats, so "hold the 22" is the executable
exclusion, and it coincides with loading the 41.

## 2 · The property that has no field, which is why this is not a small command

`seat-alias` gets its review guarantee from **a person typing a canonical id**.
Its docstring says so and argues against exactly what is being asked for here:
*"a bulk loader would defeat that, and lowering the artifact's guard to admit one
would defeat it for all 63 entries at once."*

That argument is answerable, but not by selecting on `seated_by: attested`.
**`status`, `seated_by` and `incomplete` are all written by `to_yaml`** — they are
the generator's measurements, not a reviewer's marks. A loader keyed on them
admits every future entry the generator labels attested, with no human in the
path. That is the review becoming optional, arriving as a selection rule rather
than as a decision.

**Nothing in the artifact records that a human read an entry.** The only
human-authored content in the file is the two reseats, and they are invisible to a
parser — they look exactly like generated lines. So the review that happened
cannot currently be cited by any code.

## 3 · Shape: a reviewed manifest, fingerprinted per entry

```yaml
# contract/reviewed_seats.yaml
artifact:     docs/proposals/alias-surfaces-tracked-set.yaml
reviewed_at:  2026-08-20
reviewed_by:  engineer-1
population:   41            # rule 7 — the count is part of the claim
finding: >
  Judgement group came back empty. In all 41 the seated primary is the
  most-mentioned observed form.
seats:
  anthropic/claude-opus-4.8: "sha256:…"   # of THAT entry's surface + variants
  …
```

The loader loads exactly the ids in `seats:` and refuses on fingerprint drift, on
a count that disagrees with `population`, and on a manifest id absent from the
artifact. An artifact entry absent from the manifest is simply not loaded — that
is not an error, it is the 22.

**Why a manifest and not a per-entry `reviewed:` line.** The review happened as
one set-level event, so recording it as one is honest. More practically, a
per-entry date cannot detect a later edit — it would keep asserting a review of
content that has since changed. A per-entry fingerprint detects it, and
invalidates only the entry that moved rather than all 41.

**This is stricter than what we have, not looser.** Typing an id pins nothing
about content: the entry can change between the review and the seat, and
`seat-alias` cannot tell. A fingerprint revokes the review the moment the surfaces
change.

**And the honest limit:** a command could generate this manifest without anyone
reviewing anything. The guarantee was never *"a human read it"* — it cannot be.
It is *"a human took a deliberate act naming this exact content, and any later
change to that content revokes it."*

## 4 · Its own command, sharing `seat()`

**Not folded into `load-seed`.** That command reads a build fixture and writes
`model_version` rows with `provenance = 'seed'` that the preflight refuses outside
`development`. A single command writing both fixture rows and production rows
cannot be gated by environment — which is the shape `source` already had, where
the loader that *creates* the fixture was the one command with no gate.

**Not a flag on `seat-alias`.** Its "one model at a time is the design" argument
stays true of it, and a flag that turns one verb into 41 models hides the
population inside an option.

**`registry seat-reviewed --manifest <path>`**, calling the same `seat()` per id
so the per-entry refusals cannot drift. **Two phases:** validate all 41 — read
each entry, build its rows, run every guard — and only then write. A refusal names
every problem at once and nothing lands, which is the same argument that gave
`harvest_run` and `job_run` two phases each. It opens a transaction, so it calls
`_gate`, and the AST test over `cli.py` enforces that whether or not anyone
remembers.

## 5 · The guards, and the two that do not exist yet

| guard | state |
|---|---|
| blocking `INCOMPLETE` slot | **inherited** from `seat()`. Also assert it at selection, so the *count* refuses rather than one entry failing mid-run |
| model absent from `model_version` | **inherited** |
| collision with a live alias for a different model | **inherited, and insufficient** — see below |
| the provisional check | **exists only as a test** — see below |
| unknown `seated_by` / `status` value | **new.** Refuse, never load. The seating test already refuses a third ground; a loader must not treat an unrecognised one as admissible (rule 6) |
| manifest population vs resolved ids | **new** (rule 7) |

**The provisional check is `tests/test_tracked_set_seating.py`, and it reads the
file rather than the database.** Its condition is `seated_by == 'launch-window'
AND total mentions >= floor` — an entry that qualifies by count and was not
credited for it. The loader needs that condition in library code, and then the
test should call the same implementation, for the reason `unfinished()` exists as
one function: two derivations of one question drift, and this one has already been
wrong once in a way that fired on five correct entries.

For the 41 it is **vacuous by construction** — they are all `attested`. That is
precisely why it should be built now: the loader will be pointed at launch-window
entries the day E2 rules, and a guard added at that point is a guard that was
absent when it first mattered.

**Cross-entry collisions are genuinely new work.** `check_no_collisions(rows)`
runs inside `seat()`, over one entry's rows. Forty-one entries can collide with
*each other* — two models claiming one normalised surface — and nothing checks
that today, because nothing has ever seated two models in one operation. The batch
must collision-check the union before writing anything.

## 6 · What it costs elsewhere

**`contract/` gains a file** if the manifest lands there, and that wants flagging.
It is an addition rather than a change to an existing interface, so it costs E2 a
read and no rework, and it sits beside `seed_models.yaml`, which is the same kind
of object — a curated list a loader reads. The alternative is a `collect/`-local
home, which leaves `contract/` still at the cost of alias inputs living in two
places.

**`model_alias` still has no `provenance`.** Already raised in `seat.py` and worth
repeating here: after this run, reviewed rows are indistinguishable in the
database from rows `load_seed` wrote. The manifest becomes the only record of
which is which — an argument for versioning it, and a second argument for the
column.

**The six already-searchable models will merge rather than be replaced.**
`_sync_alias` closes a live row only when the same `normalized` and the same
`model_version_id` resolve to a different row id, and inserts otherwise — so a
seed surface the artifact does not reproduce stays live, and a colliding one is
superseded by the artifact's version. Nothing is deleted. Worth verifying on the
first run rather than asserting here.

**Volume:** 180 primary + variant surfaces across the 41, against the one measured
conversion we have — `opus-4.8`, 7 declared surfaces → 4 alias rows →
3 search-eligible after normalised dedup.

## 7 · What this deliberately does not decide

The **22** launch-window seats are E2's, unchanged.

The **5** need a decision that is not *"they are guesses"*, because they are not:
they are attested below the floor. Either load them with the 41 and let the
provisional check keep watching them, or hold them with the 17 and record the
reason in one line — but the reason cannot be the one that applies to the 17, and
two of the five are the only hand-reviewed entries in the file.

---

# Part two: the three questions that had to be settled before building

## 8 · The family surface, settled by measurement rather than by judgement

**Measured across the 41 before asking anyone.** The rule was: if most have one it
is a per-entry decision, if none do it is a design question about the artifact.
**None do, and it is worse than unfilled — for most of them it is unfillable.**

| | of the 41 |
|---|---|
| `family_surface` filled | **0** |
| carrying any digit-free surface, which is what `classify_specificity` needs to return `family` | **0** |
| `model_version.family` populated on the registry row | **0** |
| sharing a candidate family word with another of the 41 | **37** |

The shared words: `opus` 7, `gpt` 7, `glm` 6, `sonnet` 4, `mini` 4, `flash` 3,
and `haiku` / `instruct` / `grok` 2 each. **Only 4 of the 41 have a family word
that names one model within the batch.**

**Two mechanical corrections, because they change what the question is.**
`alias_rows` does not *require* a family surface — `family` comes from
`model.family` on every row and `specificity` is computed from the surface string,
so an unfilled family surface costs a *row*, not a refusal. And for 37 of the 41 a
bare family word cannot be written at all: one normalised surface pointing at two
live models is what `check_no_collisions` refuses, and §5 rule 4 drops an
ambiguous mention rather than guessing. `seat.py` already gives the reason — *"a
bare `opus` is attested constantly and attributable to no single model."*

**So the consequence stands and the framing changes.** Seating these 41 does mean
the sweep never retrieves a bare `sonnet` — true, and worth knowing. But that is
not a per-entry omission to be filled in; it is a property of seating more than
one model per family, which the artifact does by design. The choice is not
*"fill 41 family surfaces"*; it is *"is a family alias worth having for the 4
models where it is even assignable"*.

**The third finding is separate and belongs to `collect/`:**
`model_version.family` is NULL on all 342 registry rows. The feed does not carry
it and the poller does not derive it, so the `family` **column** on every alias
row these seats produce is NULL too — and nothing anywhere can group by family
today. Same shape as `lifecycle`, and mine to fix or to rule on.

## 9 · Undo, or additive-only: additive, and the reason is that an undo would have to lie

The question arrives with the writer rather than after it, so: **no undo, and not
because it is hard.**

`model_alias` is append-only under FR-4, and `_sync_alias` already shows the only
write the design permits against an existing row — closing `valid_until`. So an
"undo" cannot be a DELETE without breaking FR-4's time-aware resolution and
NFR-4's rebuild. **It could only be a window close, and a window close is not a
retraction — it is a claim about the world.** `mistral large` meaning
`mistral-large-2411` until 2025-03-30 and `mistral-large-3` after is exactly what
that column is for. Closing a window to undo a mistaken load would assert that a
surface *stopped meaning* a model on the day we noticed our error, and a March
post would then resolve differently than it should. The undo would put a lie in
the table to tidy up a mistake.

**So the hazard is handled before the write, not after it.** That is what §11's
plan-and-refuse is for, and it is why the guards in §5 are strict rather than
advisory: in an append-only table, *prevention is the only reversal available*.

**A development-only `--rollback-run <id>` is refused on the same reasoning that
refused `--force` here.** The code that closes windows for a rollback is the code
that will run against staging one day. The rollback that exists already is the
disposable instance: `DROP SCHEMA public CASCADE` and re-run, which is what the
dev board does per test.

**One real gap this leaves, and it should be named rather than absorbed.** A row
that is *wrong* — an alias pointing at the wrong model — has no path out. It is
not superseded and it did not stop being true; it was never true. Expressing that
needs a column (`retracted_at`, or `provenance` plus a correction reason) so a
correction is distinguishable from a change in the world. Until it exists **the
loader must not write a row it cannot stand behind**, which is the whole argument
for the manifest. Proposed, not taken: it is `contract/`.

## 10 · The loader cannot land alone — `model_alias` has no reader

**Checked before designing further, and it changes the sequencing.** The only
`SELECT` against `model_alias` in the entire codebase is inside `_sync_alias`
itself, reading the table to decide whether it is superseding. **Nothing reads
those rows to plan a sweep, and nothing reads them to resolve a mention.**

And the GitHub sweep that exists does not want them:
`scripts/harvest_github.py:151` builds its query strings with
`alias_rows(model)` over `next(m for m in seed_models() ...)` — **computed in
memory from `contract/seed_models.yaml`**. So it can only ever sweep one of the 11
seed models, and loading 41 models into `model_alias` would change nothing it does.

**So `load-tracked-set` on its own would be the sixth producer with no consumer on
this project, and the biggest one yet** — 41 models, 180 surfaces, invisible to
every path that could use them. The reader is not a follow-up; it is the half that
makes the loader worth running:

```
load-tracked-set   writes model_alias from the reviewed manifest
        ↓
query planning     reads model_alias where it currently reads seed_models()
        ↓
sweep-github       the chain stage that is still `run=None`
```

Recommended order, and it inverts what I would have built first: **the reader
before the loader.** Point query planning at `model_alias` while the table still
holds only the 11 seed models' rows plus `opus-4.8` — a change whose blast radius
is 12 models and which is verifiable against a sweep we have already run — and
only then load 41 more into a path that is known to read them.

## 11 · What replaces `--force`

Inheriting it would give a loader a flag that means *"I did not read the plan"*.
The generator's `--force` guards **review in a file**; a loader's hazard is
**rows in a table**, and the two want different instruments.

- **A plan, printed by default.** Per entry: `insert` / `unchanged` / `replace`,
  every refusal, and the union collision check across all 41. The loader is
  idempotent, so re-running after reading the plan costs nothing.
- **Refuse on supersede, not on existence.** An insert is additive and safe; a
  `replace` closes a window another run opened. Default refuse, name the rows,
  `--allow-supersede` to proceed. That guards FR-4's one permitted write rather
  than guarding a file.
- **No `--force`.** With the two above in place it could only ever mean "skip
  them", and per §9 there is nothing it could undo afterwards.

## 12 · Superseding §8: the question was one level too low, and the loader ships without

§8 asked whether a family alias is worth having for the 4 models where it is
assignable. **That is not the question, because `family` itself is NULL on all 342
registry rows** — `openrouter.py:166` lists it in `UNAVAILABLE` beside `lifecycle`,
the only writer takes it from a `SeedModel`, and the only source of one is
`seed_models.yaml`. There is nothing for a family surface to be derived *from*.

Reframed and put to Engineer 2 in `for-engineer-2-family-derived-or-curated.md`:
**should `family` be derived from the canonical id, or stay a curation decision?**
With the measurement that decides it — no derivation rule reproduces our own 11
curated values (best is 8 of 11), because those 11 use three granularities chosen
per vendor: `claude` across tiers, `mistral-large` as a product line, `gpt-4.1` as
a version line.

**And the loader ships without family surfaces.** Not a compromise —
`model_alias` is append-only (§9), so a family row added later is an `INSERT`
beside the existing rows rather than a rewrite of them. Seating 41 models with
their version and snapshot surfaces is 41 models more than today; the missing
family alias is a **coverage** loss, not a **correctness** one, and nothing
published becomes wrong for want of it.

So the family answer gates the *column*, and it does not gate the sweep.
