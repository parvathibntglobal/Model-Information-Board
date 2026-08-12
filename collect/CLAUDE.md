# collect/ — Engineer 1

**Get clean, deduplicated, flattened documents into the store.**

This lane never calls a language model. Not once. If a task here seems to need
one, it belongs in `judge/` or it doesn't belong.

## What this lane owns

| Stage | Directory | Job |
|---|---|---|
| E1 registry | `registry/` | Know every model that exists, and the facts about it |
| E2 harvest | `adapters/` | Search three platforms for what engineers wrote |
| E3 assemble | `assemble/` | Deduplicate, normalise, flatten threads, emit `offset_map` |
| E4 triage | `triage/` | Drop junk with cheap deterministic checks |
| E9 ops | `ops/` | The five alerts, coverage data, the nightly chain |

## Where this lane ends

You fill `document`, `thread_context`, `author`, `model_version` and
`model_alias`. `judge/` reads them. **Nothing flows back.**

Never import from `judge/`. Never write to `claim`, `cell` or `label`.

## The three rules that matter most here

**1 — `offset_map` cannot be built later.**
It is roughly ten lines while you are already walking the thread tree, and
impossible to reconstruct afterwards. Every quote extracted without it has to
be re-run. It must exist before `judge/` runs its first extraction.

**2 — Rank thread children by specificity, not popularity.**

```
score = specificity_score × log(1 + engagement)
```

The top-voted replies are agreement and jokes. The two-line correction —
*"you had `tool_choice` misconfigured"* — sits at +2 and is the one that
carries the condition. Ranking by engagement alone drops exactly the comment
flattening exists to capture.

**3 — Over-clustering is worse than under-clustering.**
Merging two genuinely independent reports destroys corroboration, which is the
only thing separating *"someone said this"* from *"this is probably true"*.
Keep the thresholds conservative.

## Platform notes

| | Access | Limit | Watch for |
|---|---|---|---|
| GitHub | PAT, five minutes to set up | 30 search req/min | The highest-signal source: repro steps, error strings, real schemas |
| Blogs | RSS + sitemaps, no auth | be polite, ~1 req/sec | **The only positive-evidence channel.** Do this one early |
| Reddit | Script app, ~15 min | 60 req/min | Their terms prohibit scraping — use the API |

**No scraping. No paywall circumvention.** `robots.txt` respected, identifying
User-Agent with a contact URL. A source whose terms forbid this use is dropped,
not worked around.

## Length-aware deduplication

Simhash is built for long documents; below roughly 200 tokens its signature is
unstable, and most Reddit comments are short.

- **MinHash + LSH** over character shingles → short documents
- **simhash** → long-form

Exclude blockquoted spans from the signature, so commentary *about* a post
isn't merged into it.

## Emoji are preserved, not stripped

🔥 → `[fire]`, 🙃 → `[upside_down_face]`. An innocuous sentence followed by
`[upside_down_face]` is frustration or sarcasm, and **sarcasm read as a claim
is the single most common extraction error on Reddit.** Code fences, error
strings, diffs and numbers-with-units are preserved verbatim — they are the
specificity signal triage depends on.

## Query budget

```
10 models × 5 alias variants × 12 capabilities = 600 queries per platform
```

About 20 minutes at GitHub's rate. **While developing an adapter, run against
one model and three capabilities.** Widen only when it works.

## Numbers to track from day one

- **Triage survival, expected ~10–15%.** An estimate to calibrate, not a
  specification. A shift beyond 2σ means a platform changed or a filter broke —
  but that alert needs a **14-day burn-in** before it arms, because on day one
  there is no baseline to compute σ against. Log and eyeball until then.
- **Per-adapter yield.** A sudden drop means the site changed its markup, not
  that the internet went quiet. Cheapest possible detector for a silently
  broken parser.
