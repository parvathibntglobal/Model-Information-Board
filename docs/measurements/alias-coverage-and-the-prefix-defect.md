# 301 models cannot resolve, and 22 of the 41 that can are mis-attributable

**Two structural limits, both in `collect/`, both mine.**

```
model_version rows                342
model_alias rows                  105
models with >=1 alias              41      12%
models with NO alias              301      88%   can never resolve

prefix pairs where a shorter alias is a proper prefix of a longer one
belonging to a DIFFERENT model                     42
model_versions exposed                             22   of 342 - but 22 of the
                                                        41 that resolve at all
```

**More than half the resolvable registry is exposed to the prefix defect**, and
the 88% that cannot resolve at all has been invisible because every model people
happened to write about was among the 41.

*Engineer 1 · 2026-08-21 · reads only*

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

## 1 · What closing the alias gap takes

**It is a review problem wearing a generation problem's clothes, and the
generator already exists.**

`collect/registry/propose.py` has `mechanical_variants` and `rule_variants` — the
machinery that turns a canonical id into spellings a human might write. That is
not the missing part. The 105 rows on 41 models are what it produced for a
**tracked set** somebody reviewed; the other 301 models have never been through
it.

So the three candidate answers, and it is the third:

| | |
|---|---|
| **a run of the proposer over the other 301** | necessary and not sufficient. Running it is minutes. It produces candidate surfaces, and a candidate surface is not an alias — `assert_terms_reviewed` and the seated-set discipline exist because an unreviewed surface that over-matches is worse than a missing one. This week has two instances of that costing real attribution errors |
| **a review problem** | closest, and it is the honest bottleneck. 301 models x ~3 candidate spellings is ~900 surfaces for a human to accept or reject, and the accept/reject decision is exactly what stops `opus 4` being seated as a match for `opus 4.8` |
| **a decision about which models are worth seating** | **the actual answer.** See below |

### And it contradicts the earlier ruling, which is the finding

The recorded ruling was: **the sweep covers 55–77 models while the registry
resolves everything.** That is the split that makes a narrow sweep safe — we only
*search* for a few, but any model anyone *mentions* still attributes correctly.

**301 unresolvable models means the second half is false.** The registry does not
resolve everything; it resolves 41. So a narrow sweep is currently paired with a
narrow resolver, and the safety argument for the sweep's narrowness does not
hold.

Two ways to make it true again, and they are different products:

- **seat all 342.** ~900 candidate surfaces to review, and the review is where
  the prefix defect gets caught or admitted. Restores the ruling as written.
- **state the ruling as it actually is** — *"the registry resolves the seated
  set, and a claim about an unseated model is dropped and counted"*. Cheaper,
  honest, and it makes the coverage page's job bigger: 301 models would need to
  render as *unseated* rather than as *unreported*, which is the same display
  problem as §5 of `the-pages-as-served.md` one level up.

**My recommendation: state the ruling as it is, seat on demand.** Seating 900
surfaces to serve a corpus that named 41 models is work aimed at a population we
have no evidence anyone writes about. Seating a model the moment a claim is
dropped for it — the drop is already counted — spends review only where there is
demand, and the drop count is the queue.

**This is `collect/`'s and it is mine.** The proposer, the population and the
seated set are all in this lane.

---

## 2 · The prefix defect: not ambiguity, and the resolver is better than I said

### Correcting myself first

I reported that `Opus 4.6` and `GPT-4.1` resolve ambiguously to two models. **That
was my probe, not the resolver.** My static test unioned owners across *every*
hit `entity.resolve` returned. `RegistrySurfaceResolver` does the right thing:

```
takes the LONGEST match (entity.resolve sorts longest-first)
then refuses if that key has more than one owner   -> `if len(owners) != 1`
```

So genuine ambiguity IS caught and counted. `Opus 4.6` resolves correctly to
`claude-opus-4.6`. My earlier "AMBIGUOUS -> dropped 2" figure was an artefact of
my probe and the drop taxonomy in `the-pages-as-served.md` §2 should read **31
dropped, all `NOTHING`** rather than 29 + 2.

### The real defect, which is worse than ambiguity

```
surface   "GPT-5.6 Sol Ultra"
aliases held for it   none - there is no gpt-5.6 in the registry
longest match         `gpt-5`         ONE owner -> resolves CONFIDENTLY
result                openai/gpt-5
```

**The longest match can still be a proper prefix of the surface's own version.**
That is not ambiguity — there is exactly one owner and the resolver is behaving
as designed. It fires silently, with full confidence, and produces a claim about
a different model.

`claude-3.7-sonnet` is the same shape and it is the sharpest instance because the
model is absent entirely:

```
"Claude 3.7 Sonnet"  ->  longest match `claude 3`  ->  anthropic/claude-3-haiku
```

A claim about Claude 3.7 Sonnet is filed against **Claude 3 Haiku** — a different
family member, different capabilities, different price tier. It does not drop. It
publishes, eventually.

### How many stored claims could be affected

```
stored claims now                        6
  affected                               0   (the six mis-attributed ones were
                                              deleted; see below)
model_versions exposed to the pattern   22   of the 41 that resolve
prefix pairs                            42   e.g. `claudeopus4` is a prefix of
                                             opus-4.1 / 4.5 / 4.6 / 4.7 / 4.8
```

**Zero right now, and that is a fact about a 6-row table rather than about the
defect.** Every Anthropic version line is exposed: `claude-opus-4` is a prefix of
five later Opus versions, `claude-sonnet-4` of two later Sonnets. Any corpus
naming `Opus 4.8` while the registry seats `opus-4` and not `opus-4.8` files it
against `opus-4`.

### Would anything catch it

**No, and each existing guard misses it for a different reason:**

| guard | why it misses |
|---|---|
| quote verification | the quote is verbatim. Rule 1 is about fidelity, not about attribution |
| `len(owners) != 1` | there is exactly one owner. The check is correct and the input is wrong |
| `subject_was_inherited` | catches a quote naming *no* model. `"GPT-5.6 Luna"` names one |
| the gate | `insufficient` renders honestly either way, and a mis-attributed claim corroborates a real one once a second arrives |
| the golden set | round 3 asks about the **capability**, not the subject. Nothing labels attribution |

**The check that would catch it, and it is one condition:** after taking the
longest match, look at the character immediately after the matched span in the
normalised surface. If it is a digit, the surface names a **more specific version
than any alias we hold** — refuse and count it, rather than resolving to the
shorter one.

```
"gpt56solultra"      match `gpt5`   next char `6`   -> REFUSE
"claude37sonnet"     match `claude3` next char `7`  -> REFUSE
"claudeopus46"       match `claudeopus46`  nothing after -> resolve
"claudehaiku45"      match `claudehaiku45` nothing after -> resolve
```

That is a `collect/surface_resolver.py` change, mine, and **not made before the
presentation** — a resolver change is the wrong thing to land the day before a
demo, and the six bad rows are already out. Queued as the item after it.

**And it interacts with §1**: refusing here converts a silent mis-attribution
into a counted drop, which raises the drop count and makes the seat-on-demand
queue longer and more honest. The two changes want to land together.
