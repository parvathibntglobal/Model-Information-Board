# Surface resolver coverage: 320 of 342 models resolve, 0 to the wrong one

**Measured read-only against the shared registry** (`203.0.113.5`, 342
`model_version` rows), building `RegistrySurfaceResolver.from_connection` and
asking it to resolve each model. No writes, no network beyond the DB, and the
resolver is the exact object the extraction pipeline now uses.

*2026-08-25. Validates the fix in `fix/wire-surface-resolver`: does wiring the
resolver actually let extraction attribute claims, and how often does it get the
model wrong?*

---

## 1 · The population, in four numbers

```
model_version rows                          342
distinct surfaces the resolver holds      1,224   (mechanical variants + curated aliases)
normalised keys (surfaces fold to these)    397
ambiguous keys (>1 owner -> None)             1
```

**Ambiguity is one surface, not 49.** The 49 owned-by-several figure was the
substitution corpus, a different population. In the seated registry as it stands,
396 of 397 normalised keys have a single owner and resolve cleanly; one is shared
and correctly returns None (rule 6 — a surface owned by several models resolves to
none, never to whichever sorted first).

## 2 · Coverage: 320 of 342 resolve by their natural name

For each model, the local part of its `canonical_id` — `gpt-4.1` from
`openai/gpt-4.1` — was resolved and checked against its own id:

```
correct (resolves to its own model)      320   93.6%
resolves to None                          22
resolves to the WRONG model                0
```

**Zero wrong-model resolutions among the 324 real (non-router) models.** That is
the result that matters most: a claim about model X is never silently filed
against model Y. The `gpt-5` inside `GPT-5.6` containment bug the resolver's own
docstring records is not present in this population.

## 3 · What the 22 misses are, and only 4 are real gaps

```
routing pointers, correctly unresolved      18   ~*-latest and openrouter/auto family
model name shorter than a surface can be      2   openai/o1, openai/o3
snapshot / obscure local part                 2   cohere/command-r-08-2024, tencent/hy3
```

- **18 are routing pointers** — `~anthropic/claude-opus-latest`,
  `openrouter/auto`, `openrouter/free` and the like. These are not models; they
  are pointers to whichever model routes. Resolving them to a specific id would
  be wrong, so None is the correct answer, and this is the resolver behaving as
  designed rather than a coverage gap.

- **2 are genuinely unreachable and worth a follow-up: `o1` and `o3`.** Their
  bare names are two characters, below `MIN_SURFACE_CHARS`, so they are excluded
  from the surface population. A claim naming only "o1" resolves to None and is
  skipped. Narrow — a claim naming "openai o1" or "o1-preview" still resolves —
  but it is a real hole for two real models, and it is a threshold decision
  (`collect/triage/entity.py`) rather than missing data.

- **2 are snapshot-suffixed or obscure** (`command-r-08-2024`, `hy3`); the family
  surface resolves, the full snapshot local part does not.

So of 342 models, **320 resolve, 18 correctly do not (routers), and 4 are real
narrow gaps** — two of which (`o1`, `o3`) are worth raising against
`MIN_SURFACE_CHARS`.

## 4 · Every model the current corpus discusses resolves

The surfaces that appear in the 23 claims and 16 cells now on staging, resolved
individually:

```
claude opus 4.8   -> mv_a2b4f7fc3fa679c2      gpt-4            -> mv_f245a4d18572e409
opus 4.6          -> mv_15f79ec75cbf492e      gpt 5            -> mv_3ada7776822f837f
sonnet 4          -> mv_0d39d592ec7da47b      gemini 2.5 flash -> mv_cd62f9d5ea30935d
haiku 4.5         -> mv_9122fecaae125a57      fable 5          -> mv_86c0c8bf10aa4a0d
```

Eight distinct surfaces, eight distinct models, all correct — including
`fable 5`, which was unresolvable earlier in the build and has since been seated.

## 5 · What this means for the extraction run

The surface-resolver fix will attribute the overwhelming majority of claims
correctly, and it will not mis-attribute any to the wrong model. So the answer to
"is extraction worth running once the raw store is reachable" is **yes** — the
resolution half is sound, and low yield from here on is a corpus problem (what
engineers wrote) rather than a resolution problem.

The one narrow, actionable gap is `MIN_SURFACE_CHARS` excluding two-character
model names (`o1`, `o3`). Raising it is not free — it is the guard that stops
`code`→`model` and `key`→`keyword` — so it is a threshold change to weigh, not an
obvious win. Flagged, not ruled.

**Denominators, so nothing here is requoted loose (rule 7):** 342 is the seated
registry, 324 of those are real models and 18 are routers; 93.6% is 320 of 342 by
natural name; the 1 ambiguous surface and 0 wrong-model are over the 397
normalised keys and the 324 real models respectively.
