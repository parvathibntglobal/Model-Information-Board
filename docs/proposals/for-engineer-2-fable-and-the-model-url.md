# For Engineer 2: the eight claims, and which id the URL should carry

**Two things, both yours, both measured. The eight claims were not dropped
because the registry is stale — and not because it cannot carry the model
either. And the model-page URL is a product decision that a query fix alone
does not make.**

*Engineer 1 · 2026-08-20 · against a freshly polled 340-model registry*

---

## 1 · Fable 5 is in the registry. The eight claims failed on something else.

Checked four ways, vendor-agnostic, on a registry polled today:

```
ids containing "fable", any vendor : 1   anthropic/claude-fable-5  2026-06-09  in_window
google/* containing fable          : 0
/models/anthropic/claude-fable-5   : 200, mv_86c0c8bf10aa4a0d
```

So **neither diagnosis is right.** The registry is not stale about Fable 5, and
it is not unable to carry it. It carries it, dated, in window, with a page.

**What actually dropped the eight**, and it is worth having exactly because the
remedy is different again:

```python
# judge/pipeline.py:149
model_version_of.get(claim.model_ref.resolved_version_id or "")
```

The extractor is **never shown the registry**. The system prompt is 2,714
characters, contains no canonical id, and never mentions `resolved_version_id`
or the registry; the schema field defaults to `None`. So the lookup key is a
field the model has no vocabulary to fill. Demonstrated with a **complete**
340-id map:

```
extractor emitted: surface='fable 5'  resolved_version_id=None
pipeline.py:149    model_version_of.get('') -> None
```

Every claim drops regardless of what the registry holds. **Resolve from
`surface`** — which the extractor does emit, *"exactly as the human wrote it"* —
and the eight become eight. `docs/proposals/extraction-unresolved-counters.md` §4
has the shape: the map wants keying by normalised surface, and `collect/` owes
you that because `is_route` and the population live on this side.

## 2 · But the thing you were pointing at is real, and it is bigger than Fable

*"The corpus can name a model the feed cannot resolve — permanent, and a
property of a single-source registry rather than a gap that closes with the next
poll."* That is right, it is measured, and it wants a coverage kind rather than a
poll. It just is not Fable.

From the 2026-08-17 surface extract, 5,546 Reddit documents:

| verdict | surfaces | mentions | what it means |
|---|---|---|---|
| `attested-gap` | 62 | 4,556 | the registry holds it; no derivation reaches the surface |
| `resolved` | 83 | 2,646 | a mechanical variant reaches it |
| `attested-gap-ambiguous` | 49 | 1,530 | several registry models could be meant |
| **`unknown-model`** | **255** | **1,523** | **names nothing the registry carries** |

**1,523 mentions across 255 surfaces naming nothing OpenRouter lists.** Top of
it:

```
claude 3.7  70    qwen 3.5  66    claude 3.5  58    qwen 3.6  58
step 3      50    chatgpt 5 49    step 2      48    qwen 3    41
```

That is your argument with numbers on it, and it is permanent for a single-source
registry: `claude 3.5` and `claude 3.7` are real Anthropic models the feed does
not list under those surfaces, and no poll will change that.

**One caveat before it is quoted.** `unknown-model` mixes two things and only one
is your point: models the feed genuinely lacks, and **detector false positives** —
`step 1`, `step 2`, `step 3` at 48–50 mentions each are almost certainly the word
"step" in prose, not a model. So 1,523 is an upper bound on the phenomenon, not a
measurement of it, and splitting it is a piece of work rather than a reading.

**And Fable is in neither column: no surface in the extract contains "fable" at
all.** Zero mentions in the corpus, and a row in the feed — the opposite
configuration from the one described. If a thread names it eleven times, that
thread is not in the 5,546.

`docs/proposals/coverage-page-scope.md` proposes `undeclared-model` for the
roster-reachability gap. This is a **different** kind again and yours to place:
`mention-unresolvable` already exists in `KNOWN_KINDS` for exactly it, and it is
already recognised-but-unmeasured on the coverage page.

## 3 · Which id the URL should carry

The query fix landed (`judge/app.py`, flagged as cross-lane — revert freely). But
you are right that it is not the whole question, and the whole question is
yours.

**Today both work and only one is readable:**

```
/models/mv_568e0eb3a95b5113          ← the key `cell.model_version_id` holds
/models/anthropic/claude-opus-5      ← what the registry publishes
```

**The canonical id should be the URL, and the `mv_` id should stop appearing in
one.** Four reasons, in the order that decides it:

**It is the only one a human or another system can construct.** `mv_…` is
`stable_id("mv", canonical_id)` — a hash. Nobody types it, no provider publishes
it, and no external reference can produce it without asking us first. A board
whose URLs cannot be constructed from public identifiers cannot be linked to.

**It is what the frontend already builds.** `modelPath()` splits a canonical id
on `/` and re-joins it. The client was written for the readable form before the
route could serve it.

**It is stable across a re-derivation and the hash is not.** `stable_id` is a
function of the canonical id today. If its inputs ever change — a salt, a
version, a second component — every `mv_` URL breaks and every canonical URL
survives. That asymmetry is the whole argument for not exposing derived keys.

**It carries the provider, which is half the meaning.**
`/models/anthropic/claude-opus-5` says who made it. `/models/mv_568e0eb…` says
nothing, and a reader cannot tell two vendors' models apart.

**What that costs, stated rather than waved at.** `cell.model_version_id` is the
`mv_` id and should stay so — it is an internal foreign key and a canonical id in
a join column would be a wider key for no benefit. So the resolution stays where
it is now: canonical in, `mv_` internally. And the `mv_` id should remain
*accepted* rather than removed, because links already exist; it just should not
be what anything new emits.

**One thing to fix that the query did not.** The response now returns both
`model_version_id` (the `mv_` id) and `canonical_id`. If the canonical id becomes
the URL, the page builder should emit `canonical_id` in links and the field name
`model_version_id` becomes misleading — it reads as "the id of this page" and is
the id of the row. Renaming it is a client-visible change and therefore yours.

## 4 · One thing that cannot be worked around from this side

**A re-poll cannot trigger a re-extraction.** `should_skip` reads
`(thread_context_id, pipeline_version, content_fingerprint)` — the thread, the
code, the text. **The registry is not among them**, and it is the only thing that
changed. So a thread extracted when a surface was unresolvable stays skipped
after the surface lands, with a matching fingerprint and nothing to disagree
with.

That is `claims_unresolved` arriving from the other direction, and it is why the
column needs `resolver_population` beside it rather than only a count. Not
reconstructible later either: `write_model_versions` upserts
`ON CONFLICT DO UPDATE`, so the registry keeps no history of its id set.

## 5 · What landed on this side today, for context

- `registry seat-alias <canonical_id>` — the tracked-set artifact had **no
  consumer**; the only writer of `model_alias` was `load_seed` over a build
  fixture. `anthropic/claude-opus-4.8` is now seated: 4 alias rows, 3
  search-eligible, and `opus 4.8` / `opus-4.8` / `OPUS4.8` / `claude 4.8` all
  resolve to it. **`opus 5` and `fable 5` still resolve to nothing** — they are
  not seated, and one is not in the artifact at all.
- `registry load-capabilities` — `claim.capability_key` FKs to a table that held
  0 rows, so no claim was insertable for any model.
- `registry load-sources` — `harvest_run.source_id` FKs to a table that held 0
  rows.
- The poller **never parsed the feed**: the chain passed an httpx `Response` to
  `parse_models`, which read it as neither dict nor list and returned an empty
  result, reporting `OK models=0`. Fixed both sides.
