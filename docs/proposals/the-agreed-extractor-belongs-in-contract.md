# The check that would have caught machine-C

**Validating `EXTRACTOR_MODEL` against the registry does not help: the registry
contains gemini. The check that helps compares it against a CHOSEN extractor,
and rule 5 already decides where a chosen value lives.**

*anooj · 2026-09-18 · PROPOSED, NOT TAKEN. `contract/` is the agreement and gets
two eyes. Written after restoring the default, because the refusal-on-unset that
shipped in #362 answered a failure that had not happened.*

---

## 1 · What actually happened, and what each check sees

```
2026-09-18 06:39Z   thread_context_ada128ab...  5 claims  extractor_model=gemini
2026-09-18 06:41Z   machine-C             4 extract calls, gemini
2026-09-18 06:42Z   thread_context_ab6426ef...  5 claims  extractor_model=gemini
```

A machine with `EXTRACTOR_MODEL` **explicitly set** to gemini wrote claims at
`pipeline_version=e5.4` beside deepseek's.

| check | would it have fired? |
|---|---|
| refuse on unset (#362, now reverted) | **no** — the variable was set |
| registry validation (#362, kept) | **no** — `google/gemini-2.5-flash` is a polled model, correctly |
| route refusal (#362, kept) | **no** — gemini is a model, not a route |
| **compare against an agreed extractor** | **yes** |

The first three are all defensible and none of them was aimed at this. That is
the lesson worth keeping: a guard added after an incident should be checked
against the incident, and the refusal-on-unset was not.

## 2 · Where the agreed value lives: `contract/`, and rule 5 says so

> **Rule 5. Config in versioned YAML, not code.** Thresholds, weights,
> half-lives, the capability list, alias variants and filter rules all live in
> `contract/`.

The extractor is not a threshold, and it is more load-bearing than one. It
decides what the board can know, it is written to a provenance column on every
claim, and changing it forks comparability. If a locality window earns a place
in `contract/harvest.yaml`, this does.

**And the second reason is the one that matters more.** `contract/` gets two
eyes — *"a contract change is proposed and reviewed, never taken solo."* That is
exactly the right cost for changing the extractor, and exactly the property a
`.env` line does not have. Today the agreed model is a Python constant one
person can edit and a per-machine variable nobody reviews.

Proposed shape, in `contract/harvest.yaml` beside `sieve` and `specificity`:

```yaml
extraction:
  #: THE AGREED EXTRACTOR. Changing this is a provenance change: every claim
  #: written afterwards records it in `claim.extractor_model`, and claims from
  #: two extractors under one pipeline_version are not comparable (three cells
  #: on 2026-09-18 aggregated both).
  agreed_model: deepseek/deepseek-v4-flash
  agreed_on: 2026-09-18
  agreed_by: <names>
  #: WHY THIS SNAPSHOT. OpenRouter resolves the undated slug to 0423, pinned -
  #: `-0731` and `~-latest` exist separately. Moving to 0731 costs a
  #: PIPELINE_VERSION bump and a re-extraction of ~531 threads (~$1.18); the
  #: fork is the cost, not the money.
  rationale_ref: docs/proposals/the-blended-cells-and-what-extractor-model-means.md
```

## 3 · A gate, not a flag — and rule 8 permits it here

Rule 8 refuses a gate whose error rate has not been measured. **This check has
no error rate to measure**: it is string equality against a declared value, with
no judgement and nothing to misclassify. Same footing as #362's registry check,
which gates for the same reason.

The usual objection to a gate is that it blocks legitimate work and therefore
gets stepped around. **Checked, and it does not.** Both A/B tools take the model
as an argument and never read the environment:

```
scripts/ab_extractors.py       --models google/gemini-2.5-flash deepseek/...
scripts/test_extractor_swap.py --candidate deepseek/deepseek-v4-flash
```

and both write nothing to any database. So a refusal on `EXTRACTOR_MODEL`
mismatch leaves every sanctioned experiment working and stops only the thing
nobody intended: a *write* path running a model the team did not agree on.

**The escape hatch is a contract change**, which is two eyes and a dated record —
the right price for a provenance change, and not a keystroke.

Where it fires: the same place #362's registry check does, in
`judge/cli.py:_assert_model_is_registered`'s neighbourhood, before the first
call and before any spend. `scripts/fetch_model.py` needs it too and does not
currently pass that door — **that is #328, and this check inherits its gap**. A
guard on `judge/cli.py` alone would refuse the careful path and permit the one
that evades it, which is #328's inversion repeated. Fixing #328 is a
precondition for this being worth much.

## 4 · The detection side already exists and nothing runs it

`claim.extractor_model` is populated and correct. Finding claims written by an
extractor that was never agreed is one query:

```sql
SELECT pipeline_version, extractor_model, count(*)
FROM claim GROUP BY 1, 2 ORDER BY 1;
```

which returns 211 gemini at e5.1, and at e5.4 **984 deepseek and 10 gemini**.
That deepseek count was 975 four hours earlier in this same session, so the
table is moving while nobody is watching it - which is the argument for the
detector rather than a detail about it.

**Nothing anywhere runs it, and nothing surfaces the result.** A nightly check
that counts extractors per `pipeline_version` and says so when there is more
than one is cheaper than the gate, catches what the gate misses, and — unlike a
gate — works retrospectively on rows already written.

**Recommendation: build the detector first.** It is a counter rather than a
refusal, so rule 8 is satisfied trivially, it needs no contract change, and it
would have surfaced the blend within a day without anybody going looking.

## 5 · What this would still not catch

Three, and they should be written down rather than discovered.

- **A machine on a stale checkout.** The agreed value would be read from the
  local `contract/`, so a machine that has not pulled compares against an old
  agreement and passes. Same shape as the migration gap in root `CLAUDE.md`:
  the file ships on merge and the state does not. The detector in §4 catches
  this and the gate does not.
- **The provider serving something else.** `Completion.model` carries what
  OpenRouter actually ran and nothing reads it, so every check here validates
  what we *asked for*. Named in
  `docs/proposals/the-blended-cells-and-what-extractor-model-means.md` §5 and
  deliberately unaddressed — wiring it changes what a provenance column means
  mid-corpus.
- **Anything already on the board.** The gate is prospective. The 221 gemini
  claims are not affected by it, and the two-thread repair is still blocked on
  the payloads being absent from this machine.
