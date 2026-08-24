# The control missed its prediction, and that is what it was for

**Predicted Tier 2 under 1%; measured 5.0%. Predicted Tier 1 at 3–8%; measured
17.8%. Both wrong in the same direction, and the diagnosis is a real defect in
the entity gate: `saba` was matching inside "wa[s a ba]d". Fixed, the controls
land at 1.3% and 9.1% — and the 49.5pp bias figure was not invalidated, it was
understated at 51.7pp.**

*Engineer 1 · 750 control posts, 30 calls · 2026-08-18*

---

## 1 · Against the predictions, as committed

Committed in `docs/proposals/sweep-reshape-and-control.md` before fetching:

| population | predicted | measured | after the fix |
|---|---|---|---|
| Tier 2 non-technical | **< 1%** | **5.0%** ✗ | **1.3%** |
| Tier 1 general technical | **3–8%** | **17.8%** ✗ | **9.1%** |
| the eleven (sample) | 33.7% | 33.7% | 29.8% |

**Both predictions missed, in the same direction.** Tier 2 landed exactly at the
threshold I said would invalidate the bias measurement — *"Tier 2 above 5%
invalidates the 49.5pp figure, not just this measurement"* — and 5.0% is at the
line rather than over it, which is not a distinction worth hiding behind.

So the pre-committed diagnostic ran rather than an after-the-fact explanation.

---

## 2 · The diagnosis, and my named candidates were wrong

I predicted the culprits would be `cursor`, `codex`, `command` and `nova`. None
of them appeared. The surfaces actually matching in control survivors were:

| surface | count | from |
|---|---|---|
| `free` | 45 | `openrouter/free` |
| `auto` | 42 | `openrouter/auto` |
| `saba` | 6 | `mistralai/mistral-saba` |
| `fusion` | 2 | `openrouter/fusion` |

And the mechanism is not surface length. It is **the matching itself**:

```
saba    matched inside   "wa[s a ba]d"      r/movies
fusion  matched inside   "con[fusion]"      r/programming, "DRY vs. SRP"
free    matched inside   "[free]ze"         r/AskReddit
```

`normalize()` strips every non-alphanumeric so `gpt-4.1 mini` and `gpt4.1mini`
are one surface — which is load-bearing and correct — and then `resolve()`
matched the needle as a **plain substring of the space-stripped haystack**. That
crosses word boundaries and reaches inside longer words. On an AI corpus it is
invisible; on a corpus about cooking it is obvious.

**This is why the instrument control earned its place.** Tier 1 alone would have
been read as "the technical control is higher than expected, interesting". Tier
2 at 5% on posts about movies is not interesting, it is broken — and it was the
tier I said bounds almost nothing.

### The fix: a boundary map, not a word-boundary regex

Space-stripping cannot simply be dropped. So `normalize_with_boundaries()`
returns the key plus two masks recording which normalised positions began and
ended a word in the original, and a match is admissible only when it starts at a
word start and ends at a word end.

`claude opus 5` still matches `claudeopus5` — both begin and end on boundaries.
`saba` inside `was a bad` does not, because it begins mid-word.

---

## 3 · A second defect the fix exposed: routers are not models

After the boundary fix the controls still survive at 1.3% and 9.1%, and every
remaining match is `free` or `auto` **as a standalone English word** — a genuine
word-boundary match of a surface that should not exist.

`openrouter/auto`, `openrouter/free`, `openrouter/fusion` are OpenRouter
**routing endpoints**, not models. 17 of the 340 registry ids are routers or
`~vendor/…-latest` pointers.

Excluding them:

| corpus | with routers | without |
|---|---|---|
| unfiltered sample | 29.8% | **19.2%** |
| Tier 1 control | 9.1% | **0.4%** |
| Tier 2 control | 1.3% | **0.0%** |

**Tier 2 goes to exactly zero.** The instrument control passes: the gates can
return a true zero, which nothing had previously demonstrated.

### Ruled 2026-08-18: routes are not models. The 17 are excluded.

The reason is FR-4 rather than tidiness. **A claim about `free` resolves to a
pointer that routes to whatever is cheapest today, so the model that served the
request is unknown — unattributable by construction, not merely unattributed.**
FR-4 exists so a mention resolves to what existed when it was written, and a
pointer has no such thing. That also settles the `~vendor/…-latest` question
left open at rank 64 of the tracked set.

Implemented as `is_route()` in `collect/registry/propose.py` — with what a
canonical id *denotes*, not in triage, because both the tracked set and the
entity gate need the same answer.

**BOTH READINGS, side by side**, because the boundary fix in §2 was measured
against the pre-exclusion numbers and they are what make it legible:

| corpus | before either fix | boundary fix only | **+ routes excluded** |
|---|---|---|---|
| A · model-name-retrieved slice | 83.1% | 81.5% | **78.0%** |
| B · unfiltered sample (26 × 75) | 33.7%\* | 29.8% | **19.9%** |
| C · Tier 1 technical control | 17.8% | 9.1% | **0.4%** |
| D · Tier 2 non-technical control | 5.0% | 1.3% | **0.0%** |
| retrieval bias A → B | 49.5pp | 51.7pp | **58.1pp** |
| topicality bound B → C | — | 20.7pp | **19.5pp** |

\* the 11 × 175 sweep; B is 26 × 75 from §5 onward.

**Tier 2 at exactly 0.0% is the instrument control passing**, and nothing had
previously demonstrated that the gates can return a true zero.

The topicality bound now says something much stronger: **19.5 of B's 19.9
points are topicality.** Almost all of what the AI subreddits produce is the
subject matter, and the pipeline's own discrimination on a technically-literate
population is 0.4%.

**Original text, kept because it was the state at the time:**

**Not fixed here, and deliberately.** *"Do `~vendor/…-latest` routes count as
models?"* was raised as an open contract question in the tracked-set report and
has not been ruled. This is now evidence for that ruling rather than a licence
to make it unilaterally — the boundary bug was an unambiguous defect and this is
a definition. But the measurement is decisive and the recommendation is to
exclude.

Note what it costs: **10.6 points of the sample's survival** was router
surfaces. Those documents say "free" and "auto"; they do not name a model.

---

## 4 · What the bias bound actually is

With the boundary fix, holding the pipeline constant and varying only the
population:

| | survival |
|---|---|
| A · model-name-retrieved slice | 81.5% |
| B · unfiltered, 11 AI subreddits | 29.8% |
| C · Tier 1, general technical | 9.1% |
| D · Tier 2, non-technical | 1.3% |

**Retrieval bias, A → B: 51.7 percentage points.** The original 49.5pp figure
was not invalidated by the control — it was *understated*, because the spurious
matches inflated both sides and inflated B more.

**Topicality bound, B → C: 20.7 points of B's 29.8%.** Your framing carried
forward: this **bounds** rather than subtracts, because populations are not
additive. What it says is that a technically-literate population with no AI
selection survives at 9.1%, so roughly two thirds of what the AI subreddits
produce is the subject matter and about a third is the pipeline letting
technical prose through.

And with the router exclusion the same comparison is 19.2% against 0.4% — under
which reading almost *all* of the sample's survival is topicality. **Which of
those two readings is right depends on the router ruling**, which is now the
single largest open question in this measurement.

---

## 5 · The reshape: 26 × 75

Run at the same 78 calls.

| | 11 × 175 | **26 × 75** |
|---|---|---|
| posts | 1,925 | 1,900 |
| calls | 78 | **78** |
| survival | 29.8% | **29.7%** |
| between-subreddit spread | 15.4–59.4% | 13.3–61.3% |
| design effect | 14.5 | **4.89** |
| effective n | 132 | **388** |
| 95% CI | ±7.3pp | **±4.5pp** |

**±4.5pp, better than the ±5.0pp predicted**, because the design effect falls
faster than the model assumed: `deff = 1 + (n̄−1)·ICC` drops as the per-subreddit
draw shrinks, and 73 posts each rather than 175 nearly trebles the effective n.

Survival is unchanged at 29.7% against 29.8% — fifteen more subreddits moved the
point estimate by 0.1pp while halving the interval, which is what a design-effect
problem looks like when it is fixed.

---

## 6 · What this run changes about earlier figures

Every survival number published before this fix was **inflated by spurious
substring matches**. Corrected:

| figure | as published | corrected |
|---|---|---|
| slice survival | 83.1% | 81.5% |
| unfiltered survival | 33.7% | 29.8% |
| retrieval bias | 49.5pp | **51.7pp** |
| E4 ceiling *(all six gates + floor)* | ~23.8% | to be re-measured |

The 10–15% conclusion is unaffected in direction and slightly strengthened: the
corrected ceiling is lower, so E4 is closer to the target than it looked, and
still does not reach it.

---

## 7 · What would revise this

- **The router ruling.** §3. It moves the sample by 10.6 points and the controls
  to near-zero, and it is the largest open question here.
- **Re-running the E4 ceiling** with both fixes, since §6 leaves it stale.
- **A larger Tier 1.** 450 posts over 6 subreddits gives a wide interval on the
  control itself; the bound in §4 is directionally solid and not precise.
- **Nothing about the method.** The control did exactly what it was designed to
  do, on the first run, by failing its prediction. That is the argument for
  committing predictions before fetching.
