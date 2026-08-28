# Model-name against capability retrieval on GitHub: ~3x on precision, and the cause is signal rather than topic

**Two findings, and they point at different repairs. The headline number is a
retrieval figure; the mechanism underneath it is a vocabulary figure, and only
one of them is an argument for changing how we retrieve.**

*Engineer 1 · 2026-08-28 · no fetches, no model calls. Capability figures read
from `harvest_run`; model-name figures reported by E2's run and NOT verifiable
in this database — every one is labelled where it appears*

---

## 0 · Provenance of every number here, because two sources are mixed

| figure | source | verifiable here |
|---|---|---|
| capability requests, candidates, kept | `harvest_run`, 1,019 rows | **yes** |
| model-name candidates, kept | E2's run output | **no** — no `harvest_run` row exists for it |
| model-name topic / signal hits | E2's run output | **no** |
| qualifiers in use | `contract/queries.yaml` + 591 distinct `query_key`s | **yes** |

`harvest_run` holds no row after 2026-08-24 and none with `source_id` other than
`github`, so the model-name arm left no trace in the shared database. Its figures
are carried here as reported, and marked. They should not be re-quoted without
this line.

---

## 1 · The precision comparison, corrected

```
CAPABILITY QUERIES          (harvest_run, measured)
  requests                        1,019
  candidates                     44,848
  kept                              181
  pooled kept / candidates        0.404%
  mean of per-run rates (n=895)   0.359%      <- weights a 2-candidate run
                                                 like a 200-candidate one
  380 of 1,019 runs fetched 0 candidates

MODEL-NAME ARM              (reported, not verifiable here)
  candidates                      2,239
  kept                                3
  kept / candidates               0.134%

RATIO      pooled  3.0x      mean  2.7x
```

**About 3x worse on precision, not 23x.** An earlier reading of 3.4% for the
capability arm is an order of magnitude high: no slice of `harvest_run` produces
it. The closest value in the table is `avg(sieve_pass_rate) = 0.003585`, which is
**0.36%**. Checked every grouping — by night, pooled and mean, and the full
distribution: 850 of 895 runs sit in [0, 0.02] and six exceed 0.067.

**Quote the pooled figure.** The mean of per-run ratios is the same
mean-of-ratios error the extraction cost model already made once across corpora
with a 240x median spread. For "what fraction of candidates survive the sieve",
the pooled ratio is the quantity.

The baseline is not stable either, which bounds how much any single comparison
can carry:

```
2026-08-20   153 requests    2,887 candidates      6 kept   pooled 0.208%
2026-08-24   866 requests   41,961 candidates    175 kept   pooled 0.417%
```

Two runs of the same instrument, four days apart, 2.0x apart on precision.

## 2 · The cause is the signal group, not the topic token

Reported from the model-name arm: **63 topic hits, 3 signal hits** on 2,239
candidates. Signal fires at **0.13%**.

That is not a retrieval finding. It is the per-entry signal thinness already
measured independently and pre-registered:

```
per-entry signal rate, median      GitHub 0.39%   blogs 0.42%
terms that fire on neither platform          101 of 207
one stem (`truncat`)                         34.2% of all GitHub firings
```

`docs/measurements/prediction-signal-on-prose.md`, `the-signal-group.md`.

**So removing the topic token was not what cost the yield.** Topic still hit 63
times. The sieve requires subject AND topic AND signal, and signal is what failed
— which it also does under capability queries, at a rate the same order of
magnitude. **The 3x is a signal-vocabulary result wearing a retrieval result's
clothes.**

The two findings argue for different repairs and should not be quoted as one:

| finding | what it prices | what it argues for |
|---|---|---|
| 3x precision | the cost of dropping the capability token | a retrieval decision |
| signal at 0.13% | the vocabulary, on both query shapes | widening or replacing the 101 dead terms |

Acting on the first alone buys a 3x precision improvement on a corpus the second
finding says is thin either way.

## 3 · The third option: structural qualifiers — real, and NOT already in use

It was framed as a binary — capability token or bare alias — and there is a third
axis. **Correcting the claim that four of twelve queries already use it:**

```
contract/queries.yaml         26 entries, each carrying exactly
                              subject / topic / signal / stance / records_condition
                              NO qualifier field exists in the schema

harvest_run                   591 distinct query_key values
  carrying `type:`            591   (hardcoded in render_search, every query)
  carrying `is:issue`           0
  carrying `state:open`         0
  carrying `label:`             0
  carrying `repo:` or `org:`    0
```

**No structural qualifier beyond `type:issue` has ever been issued.** The
mechanism exists and is unused: `render_search` takes `item_type` (default
`"issue"`) and `plan_searches` takes a `scope` tuple, surfaced as a repeatable
`--scope` flag that no recorded sweep passed.

So the third option is **available and unexercised**, not established. Pitching
it as already-working would claim evidence that does not exist. What supports it
is one adjacent measurement: `org:` qualifiers compose correctly and union
exactly — `org:langchain-ai` 475 + `org:run-llama` 56, both together 531
(`collect/adapters/queries/github.py`). Qualifiers are honoured where the boolean
operators are not.

**Why it matters for the circularity argument:** a structural qualifier narrows
without naming a capability, so a capability nobody wrote a query for is still
reachable. That is the objection the reframe was proposed to answer, and it
survives here — which is the whole reason this is a third option rather than a
variant of the first.

### 3.1 · The qualifiers are not equivalent, and one of them is nearly the objection

**`label:bug` selects for complaints, which is a stance and not a capability.**
It is nearer the circularity objection than `is:issue` is, and it carries a
second cost the others do not:

> A corpus filtered to `label:bug` makes positive evidence structurally
> unreachable. `harvest.yaml` is explicit that for the four **silent-failure**
> capabilities *"nobody complained" is not evidence, because you would not find
> out* — and those already read 0.00-0.07% on positive stances. Filtering to bug
> labels would take the positive half from thin to absent, and rule 4 says the
> resulting silence must not render as approval.

Ranked by how much stance they smuggle in:

```
type:issue      none            already applied to every query
is:issue        none            structural; separates issues from PRs
state:open      weak            selects unresolved, correlates with unfixed
label:bug       STRONG          selects complaints. A stance filter wearing a
                                structural name
```

**Recommendation: test `is:issue` and `state:open`; hold `label:bug` behind an
explicit ruling**, because adopting it silently would re-import the selection
effect the reframe exists to remove.

## 4 · What this settles and what it does not

**Settles:** the price of dropping the capability token is ~3x on precision, on
the same platform with the same sieve. That number was previously an argument;
it is now a measurement with a stated denominator.

**Does not settle — the circularity argument is untouched.** A capability nobody
wrote a query for has empty cells forever under capability retrieval, however
good its precision. Precision and coverage are different axes and this measures
one.

**Whether 3x is affordable depends on triage absorbing it**, and triage is
currently unwired: `chain.py` carries `Stage("triage", run=None, ...)` and
`triage_verdict` is NULL on every row. So the affordability question has no
answer today, and it is E2's lane. **This document prices the option; it does not
recommend taking it.**

## 5 · The cheapest next measurement

Two probe requests, before anything is built:

```
  claude-opus-5 type:issue                      baseline
  claude-opus-5 type:issue is:issue state:open  structural narrowing
```

Report candidates and sieve pass for each. If structural qualifiers narrow
without touching the signal group, the third option is priced for a request
apiece; if they do not, the binary was real after all and this document is the
record of having checked.
