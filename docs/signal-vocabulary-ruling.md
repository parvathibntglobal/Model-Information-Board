# Ruling: the signal vocabulary is a term-selection problem, and here is what changes

*2026-08-25. Rules on `docs/proposals/for-engineer-2-per-platform-signal-terms.md`
and the measurement `docs/measurements/the-signal-group.md`. `contract/queries.yaml`
is shared; this ruling decides what may change it and in what order.*

Every figure below was read off the committed count files
(`docs/measurements/signal-term-counts.json`, `…-prose.json`) — not the sweep
store, which is host-local. So this ruling is reproducible from the repository
alone.

---

## What is ruled

**1 · Per-platform signal terms: REJECTED, and the proposer already withdrew it.**

The per-platform argument was withdrawn the same day it was made, on its own
pre-registered test, and the count files confirm why with a number the withdrawal
did not quote:

```
signal terms dead on BOTH GitHub and prose        101 of 207
dead on GitHub but firing on prose                  1
dead on prose but firing on GitHub                 90   (prose corpus is 315 docs,
                                                        so this is corpus size, not fit)
```

**One term** would be recovered by rendering GitHub-specific vocabulary. The gap
is not per-platform; it is the same 101 dead terms everywhere. Ruling: do not
build per-platform rendering. It addresses under 1% of the problem and adds a
branch to the one place — query rendering — where a silent mistake is invisible
from the collect side.

**2 · The cause is term SELECTION, not the exclusion set and not locality.**

Both alternatives were measured out and I accept both:

- **Exclusion set** costs 15%, not 90% (`the-signal-group.md` §3). The median
  GitHub issue is 78.5% prose. The two false positives that motivated the
  exclusions were bought cheaply. **Do not relax the exclusions.**
- **Locality window** is ruled out by the code path, not a measurement
  (`the-signal-group.md` §7): `signal_hits` is computed before the window is
  consulted, so widening the window cannot raise the signal rate. It operates on
  candidates that already have all three groups.

What remains is that the vocabulary was written in the **essay register** and the
platform speaks the **issue register**. The dead-on-both list reads as prose —
`applied cleanly`, `compiled first try`, `arguments were correct`, `always picked
the right`. The 105 that fire read as bug titles — `truncat`, `invalid json`,
`unparseable`, `infinite loop`. That is the whole finding.

**3 · Widen per-entry signal sets in the issue register, on BOTH platforms.**

The per-entry rate is what a request actually asks (median 8 of the 207 terms),
and it is **0.39% on GitHub and 0.42% on prose — identical**. So the fix is
platform-independent and it is the order-of-magnitude lever: the per-entry rate
can rise toward the 16.25% the full vocabulary already reaches, where the
locality window is capped at 1.3% and downstream of the failing group.

**4 · ADD before DELETE, and neither is a free edit.**

- **ADD is specified here, executed where the sweep store is.** New signal terms
  must obey the file's own term rules: multi-word carrying a relation, or a
  single word rare enough to justify an allowlist entry in
  `tests/test_queries_contract.py` with a reason. A bare adjective like
  `accurate` produced both false positives of the first run. Deriving terms from
  the actual near-misses — candidates where subject and topic hit and signal did
  not — needs the candidate text in `_sweep_store`, which is not on every
  machine. So the mining runs where the store is; this ruling authorises it and
  fixes the register (§5), it does not hand-invent terms into shared config.

- **DELETE waits for the fuller corpus.** The 101 dead terms are dead across
  **7 models, overwhelmingly `anthropic/*`**. A term dead on Claude issues may
  fire on `llama` or `qwen` ones, and the 33 unreached models are where that gets
  tested. A dead ANY-OF term costs almost nothing to keep. Cutting it now trades
  a measured recall risk on unmeasured models for tidiness. **Re-measure after
  the remaining nights, then cut what is still dead.**

**5 · Priority: the three 0.00% entries and the positive stances first.**

```
extraction.faithfulness:negative        0.00%
format.structured_output:positive       0.00%
tool_calling.schema_accuracy:positive   0.00%
context.effective_window:positive       0.07%
```

Four of the worst five entries are positive, because praise is essay prose and
complaints are terse. And the four **silent-failure** capabilities depend on
positive evidence — `contract/harvest.yaml` is explicit that "nobody complained"
is not evidence when you would not find out. So the positive entries are both the
worst-matched and the ones the gate cannot reach without. They go first.

**6 · The stemming gap `queries.yaml` warns about is already closed — do not
spend the lever twice.**

The file's term rules say the sieve "does not stem the final noun, so 275 of 275
multi-word terms fail to match their own plural," and instruct carrying both
forms "until that lands." **It has landed.** Verified 2026-08-25 against the
current sieve:

```
_pattern_for("invalid argument")  ->  \binvalid\s+argument\w{0,4}\b
matches "invalid arguments":  True
```

The `\w{0,4}` on the final word covers the plural. So this is not an available
lever — it is a completed one, and the `queries.yaml` note is stale by one fix.

More important, this **confirms the diagnosis rather than competing with it.**
Every one of the 101 dead-on-both terms self-matches under the current sieve —
`applied cleanly` matches the string `applied cleanly`, and its plural too. So
they are dead because **the phrases do not occur in the corpus**, not because the
matcher misses them. The essay register genuinely is not what engineers write in
issues; there is no pattern fix that revives it, only better terms.

Ruling: strike the stale "until that lands" instruction from `queries.yaml` when
the vocabulary is next edited, and do not treat stemming as pending work.

---

## Sequence

1. Run the remaining nights as a **measurement, not a baseline** — the instrument
   is about to change, so a baseline now is one nobody can compare against.
2. On the machine with `_sweep_store`, mine the near-misses per entry, in the
   issue register (§3–5), obeying the term rules (§4). Add them to
   `contract/queries.yaml` through a PR, since it is shared. Start with the three
   0.00% entries and the positive stances (§5).
3. Re-measure the 101 dead terms against the fuller corpus; cut what is still
   dead, and strike the stale stemming note (§4, §6).
4. **Then** run the definitive baseline, with a settled instrument behind it.

What this ruling refuses: finishing the current sweep, calling it the baseline,
and changing the vocabulary afterwards — an instrument that moved between the two
readings. This project has already retired one figure for exactly that.

---

## What did not need a ruling, recorded so it is not re-litigated

- The `1.3%` / `16.25%` / `0.39%` figures are three different questions and all
  correct (`the-signal-group.md` §2). Do not quote them interchangeably (rule 7).
- GitHub's median document is 2,228 characters, not the 65,502 tail sample; the
  sieve cost model is right to use ~2.2k (`the-signal-group.md` §8).
