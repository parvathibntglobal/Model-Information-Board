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
