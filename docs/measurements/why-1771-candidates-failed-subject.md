# Why 1,771 of 2,500 candidates failed subject verification — and one of them was our fault twice

**48.8% surface wrong, 45.7% correct refusal, 5.4% nothing matched.** The failures
were retained, so this needed no re-run. And chasing the two zero-candidate
surfaces found a defect that had been documented as a measurement for two weeks.

*Engineer 1 · 2026-08-28 · `model_only_sweep.jsonl`, 2,500 candidates, full text
recovered for all 1,771 failures from the stored search pages*

---

## 0 · The failures were retained

`model_only_sweep.jsonl` records every candidate with its title, its three group
verdicts, its surface and its permalink — and the search-page payloads are in
`raw_store/raw`, so the full title-plus-selftext was recoverable for **1,771 of
1,771**. No re-run, no sampling.

That was luck rather than design: the sweep wrote the JSONL because the three
group numbers were the point, and the pages are stored because the adapter stores
before it sieves. Either decision going the other way would have cost a re-run.

## 1 · The split

```
                        candidates   share of 1,771   recoverable by
A  surface wrong               865           48.8%    SEATING
B  loose index match           810           45.7%    nothing — correct refusal
C  nothing matched              96            5.4%    fetching comment trees
```

**Method.** For each failure, the full text was matched against every form
`propose.py` derives for that model (`mechanical_variants` + `rule_variants`). A
hit means the model IS named and our surface was the wrong spelling — bucket A.
No hit, but a family word (`opus`, `qwen`, `gemini`, …) or the bare version
numeral present — bucket B. Neither — bucket C.

## 2 · Bucket A: 865, and the titles make the judgement obvious

Queried `Claude Fable 5`; the text says `fable 5`:

```
Fable 5 is a mess for coders / system engineers.
    reddit.com/r/Anthropic/comments/1vlt8yb/
Game dev with Fable 5 is actually crazy
Why aren't businesses using Fable 5?
Fable 5 in x20 is a joke
    reddit.com/r/claude/comments/1v4aeyg/
Almost Nobody Is Using Anthropic's Fable 5
Anyone actually seeing a real difference between Opus 5 and Fable 5 in day to day use?
```

Those are capability reports. Every one was lost because the surface carried the
family prefix and the writer did not.

**Bucket A by model — this is what seating buys:**

```
anthropic/claude-opus-4.8       199
anthropic/claude-haiku-4.5      132
qwen/qwen3.8-27b                119
anthropic/claude-opus-4.6       116
anthropic/claude-sonnet-4.6      99
anthropic/claude-fable-5         96
openai/gpt-5.6-luna              58
anthropic/claude-sonnet-5        35
openai/gpt-5.6-sol-pro           11
                                ---
                                865
google/gemini-3.7-flash            0   <- its surface was already right
```

**Note what is not here.** Five of the nine are models that ARE seated. `opus 4.8`
scored 84.6% and still lost 199 candidates, because the other surfaces seated for
it (`claude-opus-4.8`, `claude 4.8`) matched nothing and the run needed a form
none of the three covered. So this is not only about the six unseated models — it
is about which forms are seated for any of them.

## 3 · Bucket B: 810 correct refusals, and the ceiling they imply

```
Game over. 22GB local models run in Pi now outperform Claude Code Opus 5 High
    queried 'Claude Fable 5'; text contains opus, sonnet, claude, qwen, fable
KIMI K3 Beats Claude Fable and GPT 5.6 sol in arena.ai!!!
    queried 'Claude Fable 5'; contains claude, gpt, fable, sol, 5
Claude Opus 5 BENCHMARKS!
    queried 'Claude Fable 5'; contains opus, claude, 5
Fable + 5.6 is absolute peak
    queried 'Claude Fable 5'; contains claude, fable, luna, sol, 5
```

Reddit matched these on a family word or a loose numeral. **The sieve refusing them
is correct** — the first is about Opus 5, and filing it against Fable 5 would put
a quote on the wrong model's page, which is the GPT-5.6 defect that `judge/`
already has a check for. Family words are excluded for exactly this reason.

**So 810 of 2,500 — 32.4% — is the floor this query shape cannot recover**, and it
is the cost of a bare-alias query on an index with no phrase operator.

## 4 · Bucket C: 96, and they are probably in the replies

```
Access has been extended!
Anthropic guardrails does it again
Anthropic saw this number and sent me this hat
The creators of SWE-Bench just dropped a really simple new benchmark
```

No model name, no family word, no version numeral — in the **title or the
selftext**. Most are image posts (`i.redd.it`) with an empty body, so Reddit
matched on something the sieve never saw: comments, or the linked image's
context. That is the unit mismatch, it is 5.4%, and it is recoverable by fetching
comment trees rather than by changing surfaces.

## 5 · What each cause is worth

**Seating is the largest lever in this run, and 247-of-729 understated it by 3.5x.**

```
                                    candidates   -> stored  -> triage  -> reports
bucket A recovered by seating              865        865       443        315
this run actually produced                 729        699       358        255
```

Applying this run's own rates — 51.2% triage survival, 71.2% capability-report
rate — bucket A is worth roughly **315 additional capability reports against the
255 this run found.** That is a **projection with a stated chain, not a
measurement**: it assumes recovered candidates behave like the ones that passed,
and there is a reason to think they behave slightly better, since they are posts
that name the model in the reader's own words rather than in the vendor's.

**The honest ceiling for this query shape is 1,594 of 2,500** — the 729 that
verified plus the 865 that should have. Bucket B's 810 is the part no surface work
touches.

## 6 · The two zero-candidate surfaces, and the defect behind them

`sonnet 5` and `GPT-5.6 Sol` returned zero candidates. The adapter recorded
`exhausted = True`, which its own docstring justified as measured behaviour:

> *"The API answers a query with no matches by returning `success: false` and
> `data: "data not found"` with HTTP 200. A nonsense query returns it; 25
> back-to-back calls produced none."*

**Re-probed the same day:**

```
query          in the sweep      on re-probe        5 consecutive retries
'sonnet 5'     0 candidates      25 posts           —
'GPT-5.6 Sol'  0 candidates      25 posts           —
'opus 4.8'     175 candidates    "data not found"   25 posts, 5 of 5
```

**A query that returned 175 candidates an hour earlier returned `data not
found`, then recovered on every one of five retries.** So the response is a
**transient gateway decline**, the body is byte-identical to a genuine zero, and
it is **not distinguishable by inspection**.

The 25 back-to-back calls in the original measurement were real. The conclusion
did not follow from them: they showed that a *nonsense* query returns it
consistently, not that a *real* query never does.

**So the answer to "is it distinguishable" is no — and the old reading was wrong
in the unsafe direction.** `run.exhausted = True` plus a `break` converted one
blip into "this surface has no more results", which is a statement about the
corpus. Two of seventeen surfaces reported zero for models that demonstrably have
discussion, and a third stopped at page 2 of 7.

**This is the collision this project keeps finding, produced by the comment that
claimed to have avoided it.** A surface that silently returns nothing looked
exactly like a model nobody discusses.

### What changed

`collect/adapters/reddit.py`, both `search` and `list_subreddit`:

```
retry twice before believing an empty response   measured: 1 retry sufficed 5/5
empty_response                                   a page we could not read
empty_retries                                    what the retries cost
exhausted                                        now ONLY the platform running out
```

Two attempts rather than one because the measurement needed one and this fires on
responses that may genuinely be empty — an unbounded retry would spend the
monthly quota proving a query has no matches.

**And the retry stores its own page.** The caller still holds the empty response,
so storing that would file a `discovery_ref` containing no posts beside posts from
a different response — not corruption, since the store is content-addressed, but a
provenance ref that a re-sieve would read as "this query found nothing."

`tests/test_reddit_fetch.py` asserted `exhausted is True` here. It now asserts
`exhausted is False`, `empty_response == 1` and `empty_retries == 2`, with the
falsified belief recorded in the docstring rather than deleted.

## 7 · What this means for the numbers already published

**`model-only-harvest-end-to-end.md` is affected in one direction: it undercounts.**

- 2,500 candidates is short by whatever the three truncated surfaces would have
  returned. Two got 1 page of 7 and one got 2 of 7 — **so up to 18 pages, ~450
  candidates, were never fetched.**
- Every rate in that document has 2,500 as its denominator and is therefore a
  rate over a corpus with an unmeasured hole. The *direction* is knowable: more
  candidates would have arrived, so the per-request yield is a floor.
- The listing sweep has the same exposure — 1,950 candidates of 2,100 offered,
  and 150 short is exactly 6 pages.

Neither figure is retracted. Both are floors, and the reason is now recorded
rather than latent.
