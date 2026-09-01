# Extractor A/B — DeepSeek V4 Flash vs Gemini 2.5 Flash

**Date:** 2026-09-01 · **Author:** Parvathi · **For:** E1 review

**Question:** if we swap the E5 extractor from `google/gemini-2.5-flash` to
DeepSeek V4 Flash, does it find the same claims, verify them at the same rate,
and classify them the same way — at what cost?

---

## Which model was used

**`deepseek/deepseek-v4-flash`** — the **undated alias** passed to OpenRouter,
i.e. "latest", **not** a pinned dated build (`0423` / `0731`). The alias resolves
to whatever OpenRouter currently serves; the run did **not** capture the resolved
build from the response, so this is not a claim about a specific dated model. To
pin, re-run with the exact slug and print `completion.model`.

## Method

- Ran DeepSeek **in memory** over the exact threads that produced DeepSeek: R1's
  stored Gemini claims, via `judge.extract.runner.extract` — the same code path,
  the same forced-tool-call schema, the same rule-1 quote verification as
  production.
- Compared against the **already-stored** Gemini claims for those same threads —
  Gemini was not re-run, so its cost is unchanged and only the candidate spent.
- The DB connection was **Postgres-enforced read-only**
  (`default_transaction_read_only=on`); **nothing was written**. The threads are
  held fixed, so a difference is the **model**, not the corpus.
- Harness: `scripts/test_extractor_swap.py`.

## ⚠ Sample size (rule 7)

**n = 2 threads.** DeepSeek: R1 has only 2 threads on the board that produced
Gemini claims, and both resolved from the local store. Those 2 threads carry
**12** Gemini claims (about every model mentioned in them, not only R1);
DeepSeek produced **17** over the same 2 threads. This is a **smoke test**, not a
calibration — enough to settle the binary risks (schema, fidelity), too small to
quantify the classification differences.

## Results

| | Gemini 2.5 Flash (stored) | DeepSeek V4 Flash (fresh) |
|---|---|---|
| verified claims (same 2 threads) | 12 | **17** |
| quote-verify pass rate | — | **100%** |
| fabricated (invented quotes) | — | **0** |
| schema retries / provider errors | — | **0 / 0** |
| input / output tokens | — | 11,388 / 2,643 |
| wall time | — | 73s (~37s/thread) |

**Capability distribution (verified claims):**

- Gemini: `ops.latency_ttft`:5, `extraction.faithfulness`:4, `instruction.adherence`:2, `context.effective_window`:1
- DeepSeek: `reasoning.multistep`:6, `extraction.faithfulness`:5, `instruction.adherence`:3, `ops.latency_ttft`:3

**Speaking-role distribution:**

- Gemini: `own-experience`:11, `relayed-from-elsewhere`:1
- DeepSeek: `own-experience`:17 (nothing else)

**Verbatim-quote overlap** (sentences BOTH models quoted exactly): **3**
— same capability **2/3**, same speaking-role **2/3**.

## ✅ What this clears (binary risks — n=2 is sufficient for these)

- **Schema compatibility: clean.** DeepSeek emits valid forced tool-calls against
  `emit_claims` — **0 retries, 0 provider errors**, no `prefixItems`-style
  rejection. This was the largest integration risk and it is gone.
- **Quote fidelity: 100% pass, 0 fabricated.** Rule 1 holds — it does not invent
  quotes; the worst case of a bad extractor (fake but verifiable-looking quotes)
  does not occur.
- **Recall: higher, not quieter** — 17 vs 12. A swap will not empty the board.

## 🟡 What diverges (the real finding — needs a larger sample)

DeepSeek is **a different labeller**, not a drop-in classifier:

- **Capability:** it leans on `reasoning.multistep` (6 claims) where Gemini used
  it **zero** times, and under-uses `ops.latency_ttft` (3 vs 5) and
  `context.effective_window` (0 vs 1). Same threads, **different cells**.
- **Speaking-role:** DeepSeek labelled **all 17 own-experience** (0 relayed);
  Gemini found 1 relayed. `speaking` **sets the evidence tier**, so a model that
  systematically calls everything first-hand would **inflate tiers** — directly
  relevant to the #194 tier work.
- **Even on identical quotes**, they disagree ~1/3 of the time (2/3 agreement on
  both capability and speaking).

## Verdict

**Mechanically viable — a genuine green light on integration.** DeepSeek V4 Flash
speaks our schema cleanly and verifies quotes at 100%, so there is no technical
blocker to a swap. **But it classifies differently enough that a swap reshapes
the board's content, not just its volume** — the speaking→tier skew most of all.
That divergence, not the schema, is what must be measured before committing.

## Recommended next step

The schema/fidelity questions are **answered**; the classification divergence is
**not** (n=2). To quantify it cheaply:

1. Re-run on a model with **more threads** (15–30) — `scripts/test_extractor_swap.py`
   takes `--model-name` and `--limit`; spend stays ~$0.002/thread.
2. Since `speaking` drives the tier, score DeepSeek against the **golden set**
   (`fixtures/threads/golden`), so the divergence is measured against human
   ground truth, not only against Gemini.
3. If adopted, **bump `pipeline_version`** and pin the exact dated build, so
   DeepSeek claims are attributable and diffable against the Gemini ones (the
   client already records `extractor_model` per claim).
