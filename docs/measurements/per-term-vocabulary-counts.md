# Per-term hit counts — both corpora, re-sieved from the raw store

No fetch. 174 distinct GitHub candidates and 111 blog articles, sieved against the full contract vocabulary. **Signal is counted in the author's own prose only**, as the containment split requires; subject and topic are counted anywhere.

## Read this first, or the numbers mislead

| group | terms | matching nothing | top term's share |
|---|---|---|---|
| subject | 59 | **30 (51%)** | `gemini-2.5-flash` at 28% |
| topic | 88 | **25 (28%)** | `context` at 13% |
| signal | 207 | **186 (90%)** | `good enough` at 19% |

**The corpus is 285 documents.** A phrase like `should have been null` matching zero of those is weak evidence that it is dead and strong evidence only that the corpus is small. Treat the zero list as a *candidate* list, not a deletion list.

**And the GitHub half is narrower than it looks**: those 174 candidates were retrieved for three capabilities and one model, so signal terms belonging to the other eighteen entries never had a fair chance there. The blog 111 are unfiltered, so blogs are the fairer test of recall.

## The cut that matters: entries with no living signal term

A capability query whose entire signal group matches nothing cannot produce a claim from this corpus at all — the empty-cell failure, one layer earlier.

**11 of 26 entries have no signal term that matched anything.**

| entry | signal terms | live | total hits |
|---|---|---|---|
| `over_refusal:negative` | 11 | **0** | 0 |
| `context.effective_window:negative` | 10 | **0** | 0 |
| `extraction.faithfulness:negative` | 8 | **0** | 0 |
| `reasoning.multistep:negative` | 8 | **0** | 0 |
| `context.effective_window:positive` | 7 | **0** | 0 |
| `instruction.adherence:positive` | 6 | **0** | 0 |
| `format.structured_output:positive` | 6 | **0** | 0 |
| `tool_calling.schema_accuracy:positive` | 6 | **0** | 0 |
| `code.generation:positive` | 6 | **0** | 0 |
| `over_refusal:positive` | 6 | **0** | 0 |
| `substitution:negative` | 6 | **0** | 0 |
| `instruction.adherence:negative` | 13 | 1 | 2 |
| `summarization.fidelity:negative` | 10 | 1 | 1 |
| `code.generation:negative` | 9 | 1 | 1 |
| `extraction.faithfulness:positive` | 8 | 1 | 1 |
| `ops.latency_ttft:positive` | 7 | 1 | 4 |
| `tool_calling.long_chain_reliability:positive` | 6 | 1 | 1 |
| `code.editing_diff_fidelity:positive` | 6 | 1 | 2 |
| `tool_calling.schema_accuracy:negative` | 12 | 2 | 4 |
| `summarization.fidelity:positive` | 12 | 2 | 10 |
| `format.structured_output:negative` | 11 | 2 | 2 |
| `tool_calling.long_chain_reliability:negative` | 10 | 2 | 4 |
| `code.editing_diff_fidelity:negative` | 10 | 2 | 8 |
| `ops.latency_ttft:negative` | 9 | 2 | 2 |
| `reasoning.multistep:positive` | 7 | 2 | 5 |
| `substitution:positive` | 9 | 3 | 3 |

## Every signal term that matched anything

| term | github | blogs | total | entries |
|---|---|---|---|---|
| `good enough` | 0 | 9 | **9** | summarization.fidelity:positive |
| `truncat` | 0 | 6 | **6** | code.editing_diff_fidelity:negative |
| `as good as` | 0 | 4 | **4** | reasoning.multistep:positive |
| `fast enough` | 0 | 4 | **4** | ops.latency_ttft:positive |
| `gets stuck` | 1 | 2 | **3** | tool_calling.long_chain_reliability:negative |
| `invalid argument` | 3 | 0 | **3** | tool_calling.schema_accuracy:negative |
| `didn't follow` | 0 | 2 | **2** | instruction.adherence:negative |
| `patch applied` | 0 | 2 | **2** | code.editing_diff_fidelity:positive |
| `search block` | 2 | 0 | **2** | code.editing_diff_fidelity:negative |
| `code fence` | 1 | 0 | **1** | format.structured_output:negative |
| `does not exist in the` | 0 | 1 | **1** | code.generation:negative |
| `hallucinated` | 0 | 1 | **1** | summarization.fidelity:negative |
| `held for` | 0 | 1 | **1** | tool_calling.long_chain_reliability:positive |
| `held up` | 0 | 1 | **1** | extraction.faithfulness:positive, reasoning.multistep:positive, substitution:positive, summarization.fidelity:positive |
| `infinite loop` | 1 | 0 | **1** | tool_calling.long_chain_reliability:negative |
| `invalid for json schema` | 1 | 0 | **1** | format.structured_output:negative |
| `latency spike` | 0 | 1 | **1** | ops.latency_ttft:negative |
| `months later` | 0 | 1 | **1** | substitution:positive |
| `saved us` | 0 | 1 | **1** | substitution:positive |
| `too slow` | 0 | 1 | **1** | ops.latency_ttft:negative |
| `tool that is not` | 1 | 0 | **1** | tool_calling.schema_accuracy:negative |

## The shape of what carries

- 21 signal terms matched at least one document.
- 2 of them are single words; 19 are multi-word.
- mean words per term: **2.3 live** against **2.7 dead**.

## Dead signal terms, in full

<details><summary>186 terms matching zero documents</summary>

- `added preamble`  — instruction.adherence:negative
- `adds preamble`  — instruction.adherence:negative
- `always picked the right`  — tool_calling.schema_accuracy:positive
- `always valid json`  — format.structured_output:positive
- `answered without`  — over_refusal:positive
- `applied cleanly`  — code.editing_diff_fidelity:positive
- `arguments were correct`  — tool_calling.schema_accuracy:positive
- `as an ai`  — over_refusal:negative
- `breaks the diff`  — code.editing_diff_fidelity:negative
- `buried the`  — summarization.fidelity:negative
- `can't follow the`  — reasoning.multistep:negative
- `cheaper per`  — substitution:positive
- `compiled cleanly`  — code.generation:positive
- `compiled first try`  — code.generation:positive
- `complaint from`  — substitution:negative
- `completed the chain`  — tool_calling.long_chain_reliability:positive
- `confidently wrong`  — reasoning.multistep:negative
- `consistent latency`  — ops.latency_ttft:positive
- `correct import`  — code.generation:positive
- `correctly returned null`  — extraction.faithfulness:positive
- `declined a perfectly`  — over_refusal:negative
- `degraded under load`  — ops.latency_ttft:negative
- `degrades past`  — context.effective_window:negative
- `deprecated api`  — code.generation:negative
- `didn't invent`  — extraction.faithfulness:positive
- `didn't match`  — code.editing_diff_fidelity:negative
- `didn't moralis`  — over_refusal:positive
- `didn't notice the`  — reasoning.multistep:negative
- `diff applied`  — code.editing_diff_fidelity:positive
- `does not compile`  — code.generation:negative
- `does not follow`  — instruction.adherence:negative
- `doesn't compile`  — code.generation:negative
- `doesn't follow`  — instruction.adherence:negative
- `drifted from the format`  — instruction.adherence:negative
- `dropped the`  — summarization.fidelity:negative
- `exactly what I asked`  — instruction.adherence:positive
- `extra key`  — format.structured_output:negative
- `extra keys`  — format.structured_output:negative
- `failed at the`  — tool_calling.long_chain_reliability:negative
- `failed to apply`  — code.editing_diff_fidelity:negative
- `failed to parse`  — format.structured_output:negative
- `fails at the`  — tool_calling.long_chain_reliability:negative
- `faithful to the source`  — summarization.fidelity:positive
- `falls apart`  — context.effective_window:negative
- `falls apart on`  — reasoning.multistep:negative
- `false refusal`  — over_refusal:negative
- `fell off past`  — context.effective_window:negative
- `filled in a field`  — extraction.faithfulness:negative
- `fine at`  — context.effective_window:positive
- `finished all`  — tool_calling.long_chain_reliability:positive
- `followed the chain`  — reasoning.multistep:positive
- `followed the instruction`  — instruction.adherence:positive
- `forgets the middle`  — context.effective_window:negative
- `forgets what it called`  — tool_calling.long_chain_reliability:negative
- `full window without`  — context.effective_window:positive
- `gave up after`  — tool_calling.long_chain_reliability:negative
- `got it right`  — reasoning.multistep:positive
- `guessed the`  — extraction.faithfulness:negative
- `had to revert`  — substitution:negative
- `hallucinated a function`  — tool_calling.schema_accuracy:negative
- `hallucinated the`  — extraction.faithfulness:negative
- `hallucinated the api`  — code.generation:negative
- `handled the whole`  — context.effective_window:positive
- `held the constraint`  — reasoning.multistep:positive
- `held the format`  — instruction.adherence:positive
- `held under load`  — ops.latency_ttft:positive
- `held up at`  — context.effective_window:positive
- `high variance`  — ops.latency_ttft:negative
- `ignored the instruction`  — instruction.adherence:negative
- `ignores the earlier`  — context.effective_window:negative
- `ignores the format`  — instruction.adherence:negative
- `ignores the instruction`  — instruction.adherence:negative
- `invalid arguments`  — tool_calling.schema_accuracy:negative
- `invalid json`  — format.structured_output:negative
- `invented a tool`  — tool_calling.schema_accuracy:negative
- `invented a value`  — extraction.faithfulness:negative
- `keeps adding`  — instruction.adherence:negative
- `kept it in production`  — substitution:positive, summarization.fidelity:positive
- `lectured me`  — over_refusal:negative
- `left out the`  — summarization.fidelity:negative
- `loops forever`  — tool_calling.long_chain_reliability:negative
- `loses recall`  — context.effective_window:negative
- `lost in the middle`  — context.effective_window:negative
- `lost the constraint`  — reasoning.multistep:negative
- `lost the detail`  — summarization.fidelity:negative
- `low ttft`  — ops.latency_ttft:positive
- `made something up`  — summarization.fidelity:negative
- `made up a function`  — code.generation:negative
- `made up a tool`  — tool_calling.schema_accuracy:negative
- `made up a value`  — extraction.faithfulness:negative
- `malformed patch`  — code.editing_diff_fidelity:negative
- `matched every time`  — code.editing_diff_fidelity:positive
- `matched the expected`  — reasoning.multistep:positive
- `matched the source`  — extraction.faithfulness:positive
- `misread the`  — summarization.fidelity:negative
- `missed the`  — summarization.fidelity:negative
- `missing required field`  — format.structured_output:negative, tool_calling.schema_accuracy:negative
- `months without`  — summarization.fidelity:positive
- `moralis`  — over_refusal:negative
- `moraliz`  — over_refusal:negative
- `ms to first token`  — ops.latency_ttft:positive
- `never added preamble`  — instruction.adherence:positive
- `never had to fix`  — code.editing_diff_fidelity:positive
- `never invented a tool`  — tool_calling.schema_accuracy:positive
- `never malformed`  — format.structured_output:positive
- `never mentioned the`  — summarization.fidelity:negative
- `never recovered`  — tool_calling.long_chain_reliability:negative
- `never recovers`  — tool_calling.long_chain_reliability:negative
- `never refused`  — over_refusal:positive
- `no complaint from`  — summarization.fidelity:positive
- `no complaints from`  — summarization.fidelity:positive
- `no degradation at`  — context.effective_window:positive
- `no disclaimer`  — over_refusal:positive
- `no edit needed`  — code.generation:positive
- `no hallucinated field`  — extraction.faithfulness:positive
- `no invalid argument`  — tool_calling.schema_accuracy:positive
- `no lecture`  — over_refusal:positive
- `no loop`  — tool_calling.long_chain_reliability:positive
- `no parse error`  — format.structured_output:positive
- `no preamble`  — instruction.adherence:positive
- `no quality drop`  — summarization.fidelity:positive
- `no reasoning error`  — reasoning.multistep:positive
- `no refusal`  — over_refusal:positive
- `no regression`  — extraction.faithfulness:positive, substitution:positive, summarization.fidelity:positive
- `no regressions`  — extraction.faithfulness:positive, substitution:positive, summarization.fidelity:positive
- `no such method`  — code.generation:negative
- `no such tool`  — tool_calling.schema_accuracy:negative
- `no timeout`  — ops.latency_ttft:positive
- `no truncation`  — code.editing_diff_fidelity:positive
- `nobody noticed`  — substitution:positive, summarization.fidelity:positive
- `not in the list`  — tool_calling.schema_accuracy:negative
- `not in the schema`  — tool_calling.schema_accuracy:negative
- `not in the source`  — extraction.faithfulness:negative
- `not valid json`  — format.structured_output:negative
- `nothing wrong with the request`  — over_refusal:negative
- `nulls were right`  — extraction.faithfulness:positive
- `omitted the`  — summarization.fidelity:negative
- `omitted the rest`  — code.editing_diff_fidelity:negative
- `only reliable up to`  — context.effective_window:negative
- `p95 was`  — ops.latency_ttft:positive
- `parsed cleanly`  — format.structured_output:positive
- `plausible but wrong`  — reasoning.multistep:negative
- `quality dropped`  — substitution:negative
- `ran the whole`  — tool_calling.long_chain_reliability:positive
- `ran unmodified`  — code.generation:positive
- `recall dropped`  — context.effective_window:negative
- `recall stayed`  — context.effective_window:positive
- `recovered from the error`  — tool_calling.long_chain_reliability:positive
- `refused a benign`  — over_refusal:negative
- `refuses ordinary`  — over_refusal:negative
- `regression after`  — substitution:negative
- `repeats the same call`  — tool_calling.long_chain_reliability:negative
- `rest unchanged`  — code.editing_diff_fidelity:negative
- `safety filter fired`  — over_refusal:negative
- `schema held`  — format.structured_output:positive, tool_calling.schema_accuracy:positive
- `seconds to first token`  — ops.latency_ttft:negative
- `should have been null`  — extraction.faithfulness:negative
- `skipped a step`  — reasoning.multistep:negative
- `slow in practice`  — ops.latency_ttft:negative
- `started failing`  — substitution:negative
- `still accurate at`  — context.effective_window:positive
- `still running`  — substitution:positive, summarization.fidelity:positive
- `stopped following`  — instruction.adherence:negative
- `stopped obeying`  — instruction.adherence:negative
- `stops using the`  — context.effective_window:negative
- `stuck to the format`  — instruction.adherence:positive
- `stuck to the schema`  — tool_calling.schema_accuracy:positive
- `timed out`  — ops.latency_ttft:negative
- `times out`  — ops.latency_ttft:negative
- `trailing comma`  — format.structured_output:negative
- `unnecessary disclaimer`  — over_refusal:negative
- `unparseable`  — format.structured_output:negative
- `unusable in production`  — ops.latency_ttft:negative
- `wasn't in the document`  — extraction.faithfulness:negative
- `wasn't worth`  — substitution:negative
- `won't stick to`  — instruction.adherence:negative
- `worked first time`  — code.generation:positive
- `wraps it in markdown`  — format.structured_output:negative
- `wrong conclusion`  — reasoning.multistep:negative
- `wrong import`  — code.generation:negative
- `wrong line number`  — code.editing_diff_fidelity:negative
- `wrong line numbers`  — code.editing_diff_fidelity:negative
- `wrong parameter`  — tool_calling.schema_accuracy:negative
- `wrong signature`  — code.generation:negative
- `wrong type`  — tool_calling.schema_accuracy:negative
- `zero invalid`  — format.structured_output:positive

</details>

## Dead topic and subject terms

<details><summary>topic: 25 matching zero</summary>

- `after the error`
- `apply the edit`
- `asked it to write`
- `chain of thought`
- `declined`
- `field extraction`
- `json mode`
- `long context`
- `multistep`
- `p95`
- `pull out the`
- `response format`
- `reverted to`
- `rolled back`
- `search and replace`
- `sequence of call`
- `structured field`
- `switched back`
- `tldr`
- `tokens per second`
- `tool chain`
- `unified diff`
- `went back to`
- `won't answer`
- `wrote the code`

</details>

<details><summary>subject: 30 matching zero</summary>

- `4.1 mini`
- `claude sonnet 5`
- `claude-haiku-4-5`
- `claude-sonnet-5`
- `deepseek 3`
- `deepseek reasoner`
- `deepseek v3`
- `deepseek v4 flash`
- `deepseekr1`
- `deepseekv3`
- `deepseekv4flash`
- `gemini 2.5pro`
- `gemini2.5flash`
- `gemini2.5pro`
- `gpt 4.1 mini`
- `gpt-4.1 mini`
- `gpt41mini`
- `haiku4.5`
- `mistral large`
- `mistral large 2`
- `mistral large 3`
- `mistral-large-2411`
- `mistral-large-3`
- `mistral-large-latest`
- `mistrallarge`
- `mistrallarge3`
- `opus5`
- `pro 2.5`
- `sonnet5`
- `v4 flash`

</details>
