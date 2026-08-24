# The resolver refuses a surface more specific than anything seated

**Fixed, tested, and it catches five of the six. The sixth is a different defect
and the guard does not touch it.**

```
collect/surface_resolver.py   containment path only:
  after the longest match, if the next character in the normalised surface is a
  DIGIT, the surface names a version past everything we hold -> REFUSE and count

  gpt56solultra     match gpt5           next `6`  -> refused
  claude37sonnet    match claude3        next `7`  -> refused
  claudeopus48xhigh match claudeopus48   next `x`  -> resolves, as before
  claudehaiku45     EXACT match                    -> resolves, as before
```

Counted in `ResolutionReport.more_specific_than_seated`, not dropped: a refusal
and a no-match are different findings. **8 new tests; suite 1,987.**

*Engineer 1 · 2026-08-21 · no model calls, no writes*

> ⚠ **THE 301 FIGURE ON THIS PAGE IS WRONG, AND SO IS THE CONCLUSION DRAWN FROM
> IT. CORRECTED 2026-08-21.**
>
> I measured resolution with my own query — `SELECT mv.id, ma.surface FROM
> model_version mv LEFT JOIN model_alias ma …` — so the 301 models with no
> `model_alias` row contributed **no surface** and could not resolve. That is a
> property of my query, not of the system.
>
> **The production path never touches `model_alias`:**
>
> ```python
> # collect/surface_resolver.py  RegistrySurfaceResolver.from_connection
> rows = conn.execute("SELECT canonical_id, display_name FROM model_version")
> population = build_population([(r[0], r[1]) for r in rows])
> ```
>
> `build_population` derives surfaces mechanically from the canonical id and the
> display name, for **every** model. So **all 342 are resolvable**; `model_alias`
> holds *curated* surfaces for the seated tracked set and is not the resolution
> input.
>
> **This is the 55-to-77 ruling working exactly as written** — the sweep covers a
> few, the registry resolves everything — rather than contradicting it. I had it
> as a coverage gap and it is not one.
>
> Measured consequence, on the 176 saved blog claims:
>
> | | my query | production |
> |---|---:|---:|
> | surfaces in the population | 1,342 | 1,224 |
> | claims resolving | 9 | **25** |
>
> And the models I called synthetic are real registry rows: `qwen/qwen3.8-27b`
> (11 claims), `openai/gpt-5.6-sol`, `openai/gpt-5.6-luna`,
> `openai/gpt-5.6-sol-pro`, `google/gemini-3.7-flash`,
> `anthropic/claude-sonnet-4.5`.
> `docs/measurements/the-population-i-starved.md`


---

## 1 · Longest-match-first changes nothing, because it was already there

The premise was that candidates might be unordered. They are not:

```python
# entity.resolve
return tuple(sorted(hits, key=lambda s: (-len(normalize(s)), s)))   # longest first
# RegistrySurfaceResolver
key = normalize(hits[0]) if hits else None                          # takes it
```

**So the population that ordering saves is already saved.** Measured over all
176 saved blog claims: **5** have a shorter hit whose owner differs from the
longest hit's. All 5 resolve to the longest today and always have.

The answer to *"it may be larger than eight"* is **it is 5, and it was never
broken.** The defect was never about ordering — it was about the longest
available match still being a proper prefix of the surface's own version, which
no amount of ordering fixes because the better candidate does not exist.

---

## 2 · Before and after, all eight blog claims

```
surface                                    before                      after
Claude Haiku 4.5                           anthropic/claude-haiku-4.5  UNCHANGED
Opus 4.6                                   anthropic/claude-opus-4.6   UNCHANGED
GPT-5.6 Sol Ultra                          openai/gpt-5                REFUSED
Codex Desktop running GPT-5.6 Sol Ultra    openai/gpt-5                REFUSED
GPT-5.6 Sol Pro                            openai/gpt-5                REFUSED
GPT-5.6 Luna                               openai/gpt-5                REFUSED
GPT-5.6                                    openai/gpt-5                REFUSED
Claude Fable 5, Opus 5, or Sonnet 5        anthropic/claude-sonnet-5   UNCHANGED ⚠
```

Across all 176 saved blog claims: **5 resolutions change**, all refusals, and one
more surface joins them that had gone unnoticed — **`GPT-4-32k`**, which was
resolving to `openai/gpt-4` in the eight-feeds run and was counted there as a
success.

### The guard reproduces the deletion, which validates both

The six claims deleted last turn were the five GPT-5.6 ones and the multi-model
one. **The guard would have refused exactly five of those six and kept exactly
the two that were kept.** The fix and the deletion agree on 7 of 8 rows, which is
the closest thing to a check either could have.

> **On "fix rather than delete": the deletion had already run**, last turn, on
> instruction. So the choice was not available for those six. What the fix buys
> now is that re-extracting them cannot recreate the error — which is the state
> "fix rather than delete" was aiming at, reached in the other order.

---

## 3 · The sixth is a different defect, and it is still live

```
"Claude Fable 5, Opus 5, or Sonnet 5"  ->  anthropic/claude-sonnet-5
```

**Not a prefix problem.** The longest match has exactly one owner and no digit
follows it. The surface names **three models** and resolves to one, silently,
because a surface is assumed to name a single subject.

That is a distinct check and it is not in this change: **a surface matching
several different models' aliases at non-overlapping positions should refuse.**
`resolve()` already returns every hit, so the signal is there — as it was for the
prefix case. Queued, not landed, and stated because "one defect" was the framing
and there are two.

The claim it produced is already deleted, so nothing live is affected today.

---

## 4 · `claude-3.7-sonnet` — your correction is right about the cause

**It belongs with the 301, not with the substring defect.** If
`anthropic/claude-3.7-sonnet` were seated with an alias, longest-match would
resolve it correctly and no guard would be needed. The cause is the alias gap.

**And the guard does touch the symptom, which is worth separating:**

```
before   "Claude 3.7 Sonnet" -> anthropic/claude-3-haiku   silent, confident, wrong
after    "Claude 3.7 Sonnet" -> REFUSED, counted           correct failure
correct  "Claude 3.7 Sonnet" -> anthropic/claude-3.7-sonnet  needs seating
```

So three statements, all true, and only the middle one is this change:

- the **cause** is that no `claude-3.7` surface exists → it is an alias-coverage
  problem and belongs in §5;
- the **symptom** was a wrong attribution to a different family member, and the
  guard converts it to a counted drop;
- **resolving it correctly** needs the model seated, which the guard cannot do.

I had it filed as a separate substring defect. It is not: it is the alias gap
producing a wrong answer *through* the prefix path. One cause, two symptoms —
and the guard is a safety net under the gap rather than a fix for it.

---

## 5 · Alias coverage, restated because it is still open

```
model_version rows                342
model_alias rows                  105
models with >=1 alias              41      12%
models with NO alias              301      88%   can never resolve
```

**What closing it takes:** the generator already exists —
`collect/registry/propose.py`'s `mechanical_variants` and `rule_variants`. The
105 rows are what it produced for a tracked set somebody reviewed. Running it
over the other 301 is minutes and produces ~900 candidate surfaces; **the
bottleneck is the review**, because accept/reject is exactly the decision that
stops `opus 4` being seated as a match for `opus 4.8`. So: not a run, not really
a review problem either — **a decision about which models are worth seating.**

**And it does contradict the ruling.** The ruling was *"the sweep covers 55–77
while the registry resolves everything"* — the split that makes a narrow sweep
safe, because anything anyone *mentions* still attributes correctly. The registry
resolves **41**, so the second half is false and the safety argument does not
hold as written.

Two ways to make it true again:

| | |
|---|---|
| **seat all 342** | ~900 surfaces to review. Restores the ruling verbatim. Aimed at a population we have no evidence anyone writes about |
| **state the ruling as it is** | *"the registry resolves the seated set; a claim about an unseated model is refused and counted"*. Cheaper and honest, and it makes 301 models a **coverage-page** fact rather than 301 pages of apparent silence |

**Recommendation: the second, and seat on demand.** The refusal counts are
already the queue — `unmatched` plus `more_specific_than_seated` name exactly the
models a corpus asked for and we could not answer. Reviewing on that signal
spends effort where there is demand, and this change makes the signal sharper by
moving five silent wrong answers into it.

Both halves are `collect/`'s and both are mine.
