# 150 threads, 197 claims, three platforms, and nothing published

**The board tripled and still publishes nothing.** 51 claims to 197, 28 cells to
94, 16 models gaining a first cell. `PUBLISHED: 0`, and the reason is not the one
I predicted.

*Engineer 1 · 2026-08-28. Stopped by a $0.59 cap after 149 calls, not by a
failure and not by an empty corpus.*

---

## 1 · What ran

```
threads read          150 of 1,655         batches committed 3
proposed              488 = 450 verified + 28 rejected + 10 unclassified
unsalvaged             67 (proposed and unbuildable)
stored                103
spend             $0.5909 of $0.59 over 149 calls
unread              1,505
```

The cap tripped mid-batch-4 and that batch rolled back. **A resumed run skips the
150 already in `thread_extraction` and pays only for the rest** - verified on
this run, whose first batch re-read 50 already-extracted threads in 0.0 minutes
for $0.0000.

## 2 · Claims, and GitHub arrives

```
                 now      was
reddit           160       31
blog              20       20
github            17        0     <- the first github claims this project has had
total            197       51
```

**The 17 github claims exist because of the JSON repair.** Those 71 contexts held
`{"url":"https://api.github.com/repos/...` this morning; every quote from them
would have verified against a field value and reported clean.

Coverage widened past the eleven models the sweep targeted. 12 models gained
their first claims, including `kimi-k2.5/2.6/2.7-code`, `glm-5.2`, `grok-4.5` and
`mimo-v2.5-pro` - none of them swept for.

## 3 · Resolution: 103 of 450, and falling

```
batch 2   244 verified   72 stored   29.5%
batch 3   206 verified   31 stored   15.0%
overall   450 verified  103 stored   22.9%
```

**347 verified claims did not reach the table and I cannot tell you why.** Not for
want of looking: every other exit in the storing loop is a `log.warning` and every
one reports zero - E6 rejection (which never runs at all), missing document facts,
`QUOTE_NAMES_ANOTHER` (which counts and does not drop). An unmapped evidence tier
*raises*, so it would have crashed rather than dropped.

The only silent exit is model resolution, and it is a `log.info` that the default
level does not emit. `judge/cli.py` says so itself: *"Neither is recorded anywhere
but this output."*

**The mechanism is established; the measurement is not.** Every family-level
surface resolves to `None` - `claude`, `gpt`, `gemini`, `opus`, `sonnet`,
`haiku`, `claude code`, `chatgpt` - while `gpt-5` resolves. Stored claims skew
41 `version` to 6 `family`. That is consistent and it is inference: I never
observed the surfaces that were dropped, because they exist only in a suppressed
line.

**And dropping them is probably correct.** A claim about "Claude" cannot be
attributed to `claude-opus-4.8` without inventing specificity - rule 6 working.
What is broken is the *recording*, and `pipeline.py` names the hazard in its own
comment:

> *"silently is how 'nobody discusses this model' and 'we could not resolve the
> name' become the same absence."*

The code says that and then logs at INFO with nothing persisted. It is now the
largest single loss in the pipeline.

## 4 · The gate: my prediction was right and my reason was wrong

I predicted a populated board, not a publishing one, because `PLATFORM_MINIMUM = 2`
would be unmet on an all-Reddit corpus.

```
PUBLISHED     0
CONTESTED     0
INSUFFICIENT 94

94  fail not_enough_weight
85  fail single_author_dominates
82  fail one_platform_only
```

**12 cells now have two platforms**, up from 1. So the platform rule is no longer
what binds. **Weight is, on all 94 without exception.** The best cell in the
corpus:

```
claude-sonnet-5   reasoning.multistep   n_eff = 0.1409   voices = 7   platforms = 2
```

Seven independent voices across two platforms, and `n_eff` is 0.14 against a
threshold of 3.0. `docs/measurements/what-separates-a-populated-board-from-a-publishing-one.md`
predicted exactly this and here it is with a name on it: **seven voices of tier-D
evidence weigh less than half of one tier-A claim.** Volume does not move this
gate. Tier does.

## 5 · What the schema costs, measured

```
unsalvaged                        67 claims
salvage on failing envelopes      dominant causes, in order:
  conditions.context_size         '1M' against an integer field
  quote                           over 200 characters
  conditions.schema_enforced      'q8_0' against a boolean
```

67 claims proposed and unbuildable is 13.7% of everything proposed. The
`context_size: '1M'` case is a one-line fix in E2's schema and it fires
constantly - engineers write context windows as `1M`, `128k`, `200k`, and the
field wants an int.

## 6 · The caveat that belongs in front of every number above

**Capability keys on all 197 claims were assigned by a prompt that lists twelve
names without definitions, and that accuracy is unmeasured.** Round 3 of the
golden set exists to measure it and is unlabelled.

The claims, quotes, permalinks, platform counts and resolution figures are solid.
**The capability distribution is not a finding.** Nobody should read a
per-capability breakdown of these 197 as evidence about what engineers discuss,
and this document deliberately does not print one.

## 7 · What a resume costs

At batch 3's rate, roughly **$6** for the remaining 1,505 threads, or about **$2**
for another third. Per-thread cost is **not stationary** - batch 1 of the earlier
run was $0.0971 per 50 threads and batch 3 was $0.2015, because the ordering mixes
short reddit posts with long github issues. Three of my projections today were
wrong in exactly this way, so that $6 is a rate applied to a population whose rate
demonstrably varies, not a forecast.
