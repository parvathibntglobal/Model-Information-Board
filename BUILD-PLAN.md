# Model Information Board — Build Plan

**Requirements and the eight weeks that satisfy them, divided between two engineers.**

*Version 1.0 · 2026-08-08 · 8 weeks · 2 engineers*

> This document is about **building** it. How the machinery works is specified in `docs/logic-and-workflow.md` — read that when a requirement here refers to a mechanism and you want the detail.
>
> Move this file to the repo root once the repo is scaffolded.

---

## Contents

1. [What we're building](#1--what-were-building)
2. [The split](#2--the-split)
3. [Day one — the scaffold](#3--day-one--the-scaffold)
4. [Requirements](#4--requirements)
5. [The eight weeks](#5--the-eight-weeks)
6. [Sequencing constraints](#6--sequencing-constraints)
7. [Working agreements](#7--working-agreements)
8. [Deferred register](#8--deferred-register)
9. [Done](#9--done)

---

## 1 · What we're building

Coding agents pick their own models for every sub-agent they spawn, and they reach for the strongest one almost everywhere. Most sub-agents don't need it — summarizing a page, classifying an intent, extracting four fields. Something 10–40× cheaper usually does those at parity, and across thousands of requests a day that difference is the operating cost.

So we want to override those picks. The difficulty is knowing when it's *safe*. Benchmarks can't tell you — they measure curated tasks, leak into training data, and average away the per-capability distinction that matters. Engineers who already shipped can tell you, and they publish constantly, but their reports are buried in vendor marketing and they decay as providers silently update models behind the same names.

**The board collects those reports, strips the paid and fake content, and states what engineers actually found — in their words.** Then an Ask box: describe a task, get the models that qualify, cheapest first, with the quotes that earned each one's place.

**Two surfaces.** A page per model, showing what people say about each capability with the verbatim quotes underneath. And the Ask box, which takes a task description — or a pasted agent config — and returns ranked candidates with their evidence.

---

## 2 · The split

```
  ENGINEER 1 — Collection                ENGINEER 2 — Judgement & product
  ─────────────────────────              ────────────────────────────────
  E1  registry                           E5  extract      ← LLM
  E2  harvest                            E6  vet
  E3  assemble                           E7  curate
  E4  triage                             E8  publish
  E9  ops                                Q1–Q7 answer path ← LLM

  Never touches a language model         Owns both LLM stages
  Pure data engineering                  Evaluation + product

              ┌─────────────────────────────────────┐
  E1  ───────▶│  document  +  thread_context        │───────▶  E2
              │  (carrying offset_map)              │
              └─────────────────────────────────────┘
                    one interface, one direction
```

**Engineer 1 fills `document`. Engineer 2 reads it. Nothing flows back.**

That single rule is what makes two people work without constant coordination. Everything else is private to a lane — E1 never needs to know how vetting weights a claim, E2 never needs to know how Reddit pagination works.

**Why the boundary sits here.** Both LLM stages land with one person, so prompt discipline and evaluation are learned once rather than half-learned twice. And the data only crosses once, in one direction — if extraction sat with E1 instead, claims would flow one way and cells the other, and every schema question would need both people all eight weeks.

**Skill fit.** E1 is APIs, rate limits, Postgres, near-duplicate detection. E2 is prompt work, measurement, judgement rules, and the product surface. If one of you is stronger on pipelines, that's E1.

---

## 3 · Day one — the scaffold

**One of you scaffolds and pushes. The other waits.** Two people scaffolding in parallel produces two incompatible skeletons and an annoying hour untangling them.

Everything below can be typed without another decision.

### 3.1 · Repo tree

```
modelboard/
  CLAUDE.md                    shared context for both Claude Code sessions
  BUILD-PLAN.md                this file
  docs/
    logic-and-workflow.md      the mechanism spec
  contract/                    ← THE ONLY SHARED CODE. Changes go through a PR.
    tables.sql
    capabilities.yaml
    conditions.yaml
    seed_models.yaml
  collect/                     ← Engineer 1, exclusively
    registry/                  seed loader, later the poller, aliases, diffing
    adapters/                  github.py, blogs.py, reddit.py
    assemble/                  dedupe.py, flatten.py
    triage/                    gates.py
    ops/                       alerts.py
  judge/                       ← Engineer 2, exclusively
    extract/                   prompt.py, schema.py, verify.py
    vet/                       reject.py, weight.py
    curate/                    voices.py, gate.py, phrases.py
    pages/                     model.py, capability.py, filtered.py,
                               changelog.py, coverage.py
    ask/                       requirements.py, pipeline.py
    app.py
  fixtures/
    hand_cells.yaml            E2's week-2 hand-written cells
    golden/                    week-3 labelled sets
    threads/                   shared, built together around week 4
  tests/
```

### 3.2 · `CLAUDE.md`

**`CLAUDE.md` is the file. This section is not.**

This section previously carried its full text, so day one could be typed
without further decisions. That job is done — the file exists, both Claude Code
sessions load it every time, and it has since grown a sixth rule. A prose copy
here would drift the way §3.3's schema copy did, and be trusted the same way.

Read `CLAUDE.md` at the repo root, plus `collect/CLAUDE.md` and
`judge/CLAUDE.md` for lane-specific conventions — Claude Code applies those on
top of the root file.

What it carries, so you know when to go and read it: **lane ownership** and the
one-directional interface · the **six non-negotiable rules** a helpful refactor
would otherwise quietly violate · **stack decisions already made**, listed so
they are not relitigated · conventions for provenance, pipeline versioning and
immutable raw payloads · the **build fixtures** currently in place and the week
each is deleted.

**The rules are the part that matters most**, because each one is load-bearing
and none of them is self-evident from the code. Rule 6 in particular was
written after both lanes independently broke it — see §3.3 on why a
duplicate-and-drift is worse than a pointer.
### 3.3 · `contract/tables.sql`

**`contract/tables.sql` is the schema. This section is not.**

This section previously carried a copy of the DDL. It drifted — it listed
eight tables while the file had twenty-six — and two review findings in Phase 1
were wrong because they trusted the copy over the file. A prose duplicate of a
schema is worse than no duplicate, because it is authoritative-looking and
unversioned. Read the file.

What belongs here instead is the part the DDL cannot say: **which tables are
the lane interface, and what changing them costs.**

```
collect/  ──►  document + thread_context  ──►  judge/
```

**`document` and `thread_context` are the interface.** `collect/` fills them,
`judge/` reads them, nothing flows back. They are the only two tables where a
change breaks the other person's work in progress, so they are the two that get
agreed before either lane writes against them.

`thread_context.offset_map` is the load-bearing column. It maps spans in the
flattened text the extractor reads back to spans in the raw text a reader is
shown, and quote verification is meaningless without it. It is **segment-based,
not comment-based** — normalisation rewrites text in place and changes lengths,
so an emoji becoming `[upside_down_face]` is one character becoming eighteen,
and a constant per-comment offset silently resolves to the wrong span. See the
comment above the column, and `tests/test_verify.py::TestDisplay`.

**Everything else is lane-local.** `collect/` owns the registry, harvest and
dedup tables; `judge/` owns claims, weights, cells, labels and the answer path
tables. Neither lane reads the other's.

**Changing `contract/` goes through a PR** — see §7. It should change perhaps
five times in eight weeks, each time on purpose. Phase 1 spent one of those
five, on twenty items batched into a single review, for exactly the reason §7
gives: eleven separate reviews of a shared interface is how two people working
in parallel start disagreeing about what the interface is.

**Indexes to add now**, not later: `claim(model_version_id, capability_key,
condition_bucket, created_at)` — the aggregation hot path. `document(simhash)`
and `document(minhash)` with an LSH sidecar.
### 3.4 · `contract/capabilities.yaml`

`failure_mode` is the field that matters — it decides how much evidence the answer path demands.

```yaml
- key: instruction.adherence
  failure_mode: loud
  sounds_like: ["ignores the format", "adds preamble", "won't stick to the schema"]

- key: format.structured_output
  failure_mode: loud
  sounds_like: ["invalid JSON", "extra keys", "wraps it in markdown"]

- key: tool_calling.schema_accuracy
  failure_mode: loud
  sounds_like: ["invalid arguments", "invents tools that don't exist"]

- key: tool_calling.long_chain_reliability
  failure_mode: loud
  sounds_like: ["fails at the 7th call", "loops forever after an error"]

- key: context.effective_window
  failure_mode: silent
  sounds_like: ["loses recall past X", "forgets the middle"]

- key: summarization.fidelity
  failure_mode: silent
  sounds_like: ["dropped a key detail", "made something up"]

- key: extraction.faithfulness
  failure_mode: silent
  sounds_like: ["invents values for fields that weren't there"]

- key: code.editing_diff_fidelity
  failure_mode: loud
  sounds_like: ["breaks the diff", "truncates the file", "// rest unchanged"]

- key: code.generation
  failure_mode: loud
  sounds_like: ["hallucinated the API", "doesn't compile", "wrong import"]

- key: reasoning.multistep
  failure_mode: silent
  sounds_like: ["falls apart on anything layered", "can't follow the chain"]

- key: over_refusal
  failure_mode: loud
  sounds_like: ["refuses ordinary requests", "moralises and breaks the output"]

- key: ops.latency_ttft
  failure_mode: loud
  sounds_like: ["TTFT", "slow in practice", "fast enough for chat"]
```

### 3.5 · `contract/conditions.yaml`

```yaml
tool_count:
  bands: [none, "1-5", "6-15", "16+"]
context_size:
  bands: ["<8k", "8k-32k", "32k-128k", "128k+"]
structured_mode:
  bands: [on, off]
```

Fixed bands, because condition buckets have to be countable. *"Fine under 5 tools, breaks above 10"* is the whole answer, and it only exists if the buckets are discrete.

### 3.6 · `contract/seed_models.yaml`

Ten models, hardcoded. The OpenRouter poller replaces this in week 5 — writing into **the same table**, so the swap is a data-source change, not a rewrite.

**Fill prices and dates from the provider pages the day you write this**, and record the URL. Hardcoded shouldn't mean unsourced, and it means the seed file already practises the pattern the poller inherits (FR-2).

```yaml
- canonical_id: google/gemini-2.5-flash
  provider: google
  family: gemini-flash
  release_date: 2025-06-17
  price_in: 0.075
  price_out: 0.30
  advertised_context: 1000000
  max_output_tokens: 65536
  supports_tools: true
  supports_structured_output: true
  supports_vision: true
  provenance: seed
  aliases:
    surface: "gemini 2.5 flash"
    variants: ["gemini flash", "gemini-2.5-flash", "flash 2.5",
               "gemini flash 2.5", "gemini2.5flash"]
  sources:
    price_in:           {url: "https://ai.google.dev/pricing",  retrieved_at: "2026-08-08"}
    price_out:          {url: "https://ai.google.dev/pricing",  retrieved_at: "2026-08-08"}
    advertised_context: {url: "https://ai.google.dev/gemini-api/docs/models", retrieved_at: "2026-08-08"}
    release_date:       {url: "https://blog.google/...",        retrieved_at: "2026-08-08"}
```

**Choose the ten for variety, not popularity** — the answer path needs real edge cases to hit:

| Count | Slot | Why |
|---|---|---|
| 2 | Frontier | The reference point — "what you'd have picked anyway" |
| 3 | Mid-tier | Where runners-up come from |
| 3 | Budget | Where the savings are; the likely recommendations |
| 1 | Open-weight | Different provider shape, different hosting story |
| 1 | Released in the last month | So `just-launched` actually fires |

Two constraints that cut across the table:

- **At least one same-family pair** — two tiers of one model line. This is the case that breaks entity resolution: a post saying *"sonnet"* attaching to the wrong tier. Include it deliberately rather than hoping one turns up.
- **At least one with a known advertised-vs-real context gap** — otherwise the inflation logic sits untested until week 7.

### 3.7 · The startup assertion

Write it on day one, while you'll remember why:

```python
def assert_no_fixtures(conn):
    """Production must never serve seeded models or hand-written cells."""
    seeded = conn.scalar("SELECT count(*) FROM model_version WHERE provenance='seed'")
    handmade = conn.scalar("SELECT count(*) FROM cell WHERE provenance='hand_curated'")
    if seeded or handmade:
        raise SystemExit(
            f"Refusing to start: {seeded} seeded models, {handmade} hand-written cells. "
            "These are build fixtures and must not reach production."
        )
```

Both fixtures are load-bearing during the build and poisonous afterwards. Ten invented models and 180 hand-written opinions rendered identically to evidence, permanently and undetectably, is exactly what this prevents.

---

## 4 · Requirements

**FR-n** are functional, **NFR-n** non-functional. Each carries a statement, the failure it prevents, an acceptance criterion **checkable without interpretation**, and an owner.

If an acceptance criterion needs debate to settle, rewrite the criterion rather than arguing about it.

### Registry — Engineer 1

| | Requirement | Owner |
|---|---|---|
| **FR-1** | **List 100% of models released in the trailing 18 months, within 24 hours of release.**<br>*Why:* a model missing from the board reads as a model that does not exist.<br>*Accept:* roster matches a hand-checked list with zero omissions. **Deferred to week 5** — weeks 1–4 run on the ten seeded models. | E1 |
| **FR-2** | **Record a source URL and retrieval timestamp for every registry field.**<br>*Why:* pricing and context claims get quoted back at us.<br>*Accept:* every populated field on any **registry** row has a matching entry in `sources` — `model_version` and any table that extends it, currently `price_tier`. Applies to seeded rows too. Naming one table would leave a sourced value invisible to the thing auditing provenance the moment a value moves, which is what happened when item 18 moved Gemini's prices into tier rows. | E1 |
| **FR-3** | **Detect model changes by diffing raw provider API responses daily, not by reading changelogs.**<br>*Why:* providers change models behind stable names with no announcement — the case that matters most.<br>*Accept:* a price change is detected within 24h; a silently repointed alias raises `possibly-changed` with no announcement existing. | E1 |
| **FR-4** | **Append-only, time-aware alias table; resolution uses the post's timestamp.**<br>*Why:* old aliases must keep resolving old quotes, and `latest` in March is not `latest` in June.<br>*Accept:* no DELETE or UPDATE ever issued against `model_alias`; a March post resolving `-latest` maps to the March snapshot. | E1 |
| **FR-5** | **Community content may trigger a registry re-check but may never write to it.**<br>*Why:* facts and opinions must not mix.<br>*Accept:* no code path from `document` or `claim` to a registry write. Enforced by DB permissions. | E1 |

### Harvest — Engineer 1

| | Requirement | Owner |
|---|---|---|
| **FR-6** | **Harvest from three platforms, one of which is structurally positive.**<br>*Why:* the publication gate needs two platforms, and nobody opens a GitHub issue to say something worked. Without blogs, a cheaper summariser can never be approved — the single recommendation this product exists to make.<br>*Accept:* all three adapters returning content; at least one published cell carries positive consensus for a silent-failure capability. | E1 |
| **FR-7** | **Every tracked capability has at least one harvest query.**<br>*Why:* harvest is entirely query-driven. A capability nobody searches for has empty cells forever.<br>*Accept:* automated check — capabilities in the vocabulary equals capabilities with a query. Fails the build otherwise. | E1 |
| **FR-8** | **Negative-stance queries for every capability.**<br>*Why:* platforms surface positive content by default; failure reports are the entire basis of the `criticised-for` labels.<br>*Accept:* each capability's query set includes failure language; the corpus contains negative claims for most seeded models. | E1 |
| **FR-9** | **Persist pagination cursors durably; resume exactly where consumption paused.**<br>*Why:* data loss during a rate-limit spike is silent and permanent.<br>*Accept:* kill a harvest mid-run; it resumes from the stored cursor with no gap and no refetch. | E1 |
| **FR-10** | **Every adapter reports its own yield per run.**<br>*Why:* a sudden drop means the site changed its markup, not that the internet went quiet. Cheapest possible detector for a silently broken parser.<br>*Accept:* break a selector on purpose; the alert fires within one cycle. | E1 |
| **FR-11** | **Log and display any harvest truncated by a budget cap.**<br>*Why:* silent truncation reads as "we looked everywhere" when we didn't.<br>*Accept:* force a cap; the truncation appears on the coverage page naming the model and query. | E1 |

### Evidence — split at the flattening boundary

| | Requirement | Owner |
|---|---|---|
| **FR-14** | **Flatten each thread — root plus 3–5 specificity-ranked children — before extraction.**<br>*Why:* a reply carries its meaning in its parent. *"It wrote the bash scripts perfectly"* read alone is positive and names no model at all.<br>*Accept:* extraction runs on `flattened_text`, never an isolated comment. Measured against isolated extraction on the same threads, week 5. | **E1** |
| **FR-15** | **Emit an offset map linking every flattened span back to its source document and raw span.**<br>*Why:* the string the extractor reads is not the string the reader sees. Without it, verification either fails on everything or silently passes against the wrong text.<br>*Accept:* every `thread_context` has a non-empty `offset_map`; every claim resolves to a source document and raw span. | **E1** |
| **FR-16** | **Deduplicate before anything is counted; syndicated copies contribute to reach, never weight.**<br>*Why:* one blog syndicated four times and quoted twice is one person. Counted naively it looks like six-source consensus.<br>*Accept:* seed a known syndicated set; the affected cell's voice count increments by exactly one. | **E1** |
| **FR-17** | **Cluster author identities across platforms before counting voices.**<br>*Why:* one engineer posting to GitHub and Reddit would otherwise satisfy the two-platform rule alone — the exact condition that rule prevents.<br>*Accept:* a seeded cross-platform identity with matching handle and cross-linked profile merges to one `identity_cluster_id`. | **E1** |
| **FR-12** | **Every claim carries a verbatim quote, verified in code by exact substring match.**<br>*Why:* the anti-fabrication guarantee the product rests on, and the injection backstop — an injected instruction cannot produce a verifiable span.<br>*Accept:* 200-item audit at 100%. No row exists with `quote_verified = false`. | **E2** |
| **FR-13** | **Discard any claim whose quote fails verification; flag its document.**<br>*Why:* a rule with no enforcement is a comment.<br>*Accept:* inject a fabricated quote; the claim is absent from the database and the failure is logged. | **E2** |
| **FR-18** | **Hard-reject promotional documents on binary criteria; retain and display them with the trigger named.**<br>*Why:* a filter you cannot inspect cannot be trusted, and this audience will audit it.<br>*Accept:* a document with an affiliate link is rejected, stays in the database, and appears on `/filtered` naming the trigger. | **E2** |
| **FR-19** | **Weight every surviving claim by seven documented factors, itemised per claim.**<br>*Why:* "why does this page say that?" must be answerable with a table.<br>*Accept:* every `claim_weight` row has all seven populated; their product equals `w_final`. | **E2** |
| **FR-20** | **Compute the launch-window factor at extraction and freeze it.**<br>*Why:* recomputed at aggregation, every launch-week hype post snaps to full weight once the model turns 22 days old — the discount deletes itself.<br>*Accept:* a claim written on day 3 still carries `f_launch ≈ 0.53` when read on day 60. | **E2** |

### Publication — Engineer 2

| | Requirement | Owner |
|---|---|---|
| **FR-21** | **Publish a consensus phrase only when the publication gate passes.**<br>*Why:* an honest "we don't know yet, here's the one solid report" beats a fabricated consensus. Fake precision is how these systems lose trust.<br>*Accept:* no `published` cell violates any gate condition. Enforced by constraint or assertion. | E2 |
| **FR-22** | **State consensus in words assembled from counts; never compute or display a synthesised score.**<br>*Why:* no defensible arithmetic turns a sentence into 78 rather than 74 — and a score destroys the threshold that made the quote useful.<br>*Accept:* no 0–100 capability figure exists in the schema or on any page. | E2 |
| **FR-23** | **Display quotes exactly as written — the raw span, never the normalised form.**<br>*Why:* emoji are stored as bracketed tags internally. `[upside_down_face]` reaching the page is not what the engineer wrote.<br>*Accept:* a quote from a comment containing an emoji renders the emoji. | E2 |
| **FR-24** | **Report silence explicitly, rendered distinctly from criticism.**<br>*Why:* "nobody has discussed this" and "engineers report problems" are opposite states. Blurring them lets absence of evidence read as evidence of capability.<br>*Accept:* an undiscussed capability appears under its own heading with its own treatment. | E2 |
| **FR-25** | **Preserve conditional consensus rather than flattening it to an average.**<br>*Why:* *"fine under 5 tools, breaks above 10"* is the whole answer. Averaging says "mediocre" — true-ish, useless, and it buries the rule.<br>*Accept:* a model with opposing evidence across two condition buckets publishes both, with the condition in the phrase. | E2 |
| **FR-26** | **Every label stores and links the quote IDs that earned it.**<br>*Why:* "click the label, see the words" must be a property of the data, not a UI promise.<br>*Accept:* every label row has non-empty `earned_by_quote_ids`; every ID resolves to a verified claim. | E2 |
| **FR-27** | **Record every label gained or lost in a changelog, with its cause.**<br>*Why:* a board that changes its answers without explaining why doesn't get trusted twice.<br>*Accept:* force a label change; an entry appears naming the driver and linking the triggering quotes. | E2 |

### Answer path — Engineer 2

| | Requirement | Owner |
|---|---|---|
| **FR-28** | **Accept three input shapes: a task, a product brief, or a pasted agent config.**<br>*Why:* the pasted-config path is the direct "the coding agent picked its own models, change them" route.<br>*Accept:* all three produce a recommendation; a config produces per-role overrides against what's pinned. | E2 |
| **FR-29** | **Decompose a brief into roles, each with a runs-per-request figure.**<br>*Why:* a role running 10× per request is worth 10× more to downgrade, and that multiplier is invisible without decomposing.<br>*Accept:* recommendations ordered by `runs_per_request × cost_saved`, checked against hand-labelled briefs. | E2 |
| **FR-30** | **Show every inferred assumption as an editable field; re-run on edit.**<br>*Why:* guessing silently is the failure mode of every "AI picks for you" product.<br>*Accept:* every unstated field is editable; editing one re-runs the recommendation. | E2 |
| **FR-31** | **Filter on reported effective context, never the advertised window.**<br>*Why:* advertised windows overstate usable ones, often several-fold.<br>*Accept:* a model advertising 1M with a reported ceiling of 180k is excluded from a 400k task. | E2 |
| **FR-32** | **Gate on evidence before ranking; rank qualified candidates by cost alone.**<br>*Why:* cost must never buy a model past a criticism.<br>*Accept:* a cheaper model failing a gated capability never appears in the recommended band, at any price. | E2 |
| **FR-33** | **Segregate unevidenced candidates from the ranked list.**<br>*Why:* absence of evidence rendering as evidence is the most dangerous failure here — but hiding them makes the board conservative in a way that quietly costs money.<br>*Accept:* never in the ranked list, always in their own section with distinct wording. | E2 |
| **FR-34** | **Bind every sentence of justification to a quote ID.**<br>*Why:* the advisor is a language model, and this is exactly where it would invent a persuasive rationale.<br>*Accept:* automated check — every justification sentence resolves to a claim whose text supports it. Zero tolerance. | E2 |
| **FR-35** | **Abstain when evidence is insufficient, naming the capability that lacks it.**<br>*Why:* a confident answer built on nothing is worse than no answer.<br>*Accept:* a task needing a capability with no published cell returns an abstention naming it. | E2 |
| **FR-36** | **Answer "why not X?" and "show me the evidence against it" as first-class queries.**<br>*Why:* an advisor that can't defend a rejection isn't being consulted, it's being obeyed.<br>*Accept:* every rejected candidate carries a stored reason and its quotes, retrievable on demand. | E2 |

### Non-functional

| | Requirement | Owner |
|---|---|---|
| **NFR-1** | **Answer path p95 under 800ms cold.** The Ask box is interactive; slower and people go back to guessing.<br>*Accept:* load test over representative tasks. | E2 |
| **NFR-2** | **Query time never touches the evidence pipeline.** A broken harvest must never degrade the product surface.<br>*Accept:* stop the pipeline entirely; the Ask box stays fully functional. | E2 |
| **NFR-3** | **Hard daily extraction budget that degrades to triage-only rather than overrunning.** An alert that fires after the money is gone is not a control.<br>*Accept:* set the ceiling low; extraction stops, triage continues, truncation surfaces per FR-11. | **both** |
| **NFR-4** | **`pipeline_version` on every derived row; full rebuild from the raw store always possible.**<br>*Accept:* drop all claims and cells, rebuild, reproduce identical output for an unchanged version. | **both** |
| **NFR-5** | **Official APIs and public feeds only · robots.txt · identifying User-Agent · no paywall circumvention · quote + attribution + link, never full text.**<br>*Accept:* per-source ToS reviewed and recorded; no page renders more than a bounded quote. | E1 |
| **NFR-6** | **Honour upstream deletion and takedown via a tombstone path.** Immutability means not silently rewriting history, not refusing a deletion.<br>*Accept:* tombstone a document; its quotes vanish next run, only the content hash remains. | **both** |
| **NFR-7** | **Extraction hardened against prompt injection** — isolated untrusted block, forced schema, no tools, no network egress, least-privilege writes.<br>*Accept:* a seeded injection payload produces no claim and no side effect. | E2 |
| **NFR-8** | **Exactly two stages use a language model.** No model in counting, weighting, gating, ranking, filtering or phrase assembly.<br>*Accept:* code inspection confirms invocation only in `judge/extract/` and `judge/ask/`. | **both** |
| **NFR-9** | **One extractor, pinned in config, with a halt-and-flag on silent regression.** `google/gemini-2.5-flash` via OpenRouter, decided rather than selected. The founding premise is that models change silently behind stable names and the extractor is one such model — with nothing to fail over to, the mitigation is detection.<br>*Accept:* force a `ValidationError` spike; the batch halts, is flagged for re-run, and the alert names the extractor and its `pipeline_version`. | E2 |
| **NFR-10** | **All thresholds, weights, half-lives, capability list, alias variants and filter rules in versioned config, not code.**<br>*Accept:* changing a threshold requires no code deploy and produces a version diff. | **both** |

---

## 5 · The eight weeks

| | **Engineer 1 — Collection** | **Engineer 2 — Judgement & product** |
|---|---|---|
| **Wk 1** | Seed loader (2 days) · **GitHub adapter**<br><br>*Gate:* ten models in `model_version` with sources; GitHub returning real issues for one model<br>`FR-2` `FR-5` | `judge/ask/requirements.py` — pure logic, no data needed · app scaffold<br><br>*Gate:* a task description produces a structured requirement profile<br>`FR-30` groundwork |
| **Wk 2** | **Blog adapter, Reddit adapter** · durable cursors, backoff<br><br>*Gate:* all three returning content; kill mid-run and it resumes cleanly<br>`FR-6` `FR-9` `FR-10` `NFR-5` | **Ask box end to end** · `fixtures/hand_cells.yaml` for ~15 models × 12 capabilities<br><br>*Gate:* type a task, get a ranked answer with quotes<br>`FR-28` `FR-29` `FR-31` `FR-32` `FR-33` `NFR-1` `NFR-2` |
| **Wk 3** | Raw store · dedupe (MinHash short, simhash long) · **flattening + `offset_map`** · author identity clustering<br><br>**→ hands over the document contract**<br>`FR-14` `FR-15` `FR-16` `FR-17` | ★ **THE GATE: three real model decisions through the box**<br>+ label `fixtures/golden/` — extraction 80, entity resolution 200, filter 200<br>*E1 cross-labels ~50 for an agreement number*<br><br>*Also decide this week:* the publication-gate thresholds |
| **Wk 4** | Triage gates · query budget caps · **registry poller begins**<br><br>*Gate:* ~10–15% survival to extraction, tracked from day one<br>`FR-7` `FR-8` `FR-11` `NFR-3` | **Quote verification** against a hand-made `thread_context` · model page · capability page<br><br>*Gate:* a fabricated quote never persists<br>`FR-12` `FR-13` `FR-23` `FR-24` |
| **Wk 5** | Registry: real polling, alias table, variant generation, daily API diffing<br><br>*Gate:* roster completeness 100%; price change caught within 24h<br>`FR-1` `FR-3` `FR-4` | **Extraction** — prompt, Pydantic schema, temperature-0 retry, injection defence<br><br>*Gate:* extraction F1 ≥0.85 on the golden set; seeded injection produces nothing<br>`NFR-7` `NFR-4` |
| **Wk 6** | Change detection, `possibly-changed` events, backfill from the raw store<br>`FR-3` `NFR-4` `NFR-6` | **Extractor measured against the golden set** · vetting: hard rejects + seven-factor weight<br><br>*Gate:* filter precision ≥0.90, **≤5% false-positive on genuine expert content**<br>`FR-18` `FR-19` `FR-20` `NFR-9` |
| **Wk 7** | Ops, the five alerts, coverage-page data, nightly job chain<br>`FR-10` `FR-11` `NFR-3` | **Curation** — voice counting, publication gate, consensus phrases, condition buckets · filtered page · changelog<br><br>*Gate:* every published phrase traceable to its quotes in one click<br>`FR-21` `FR-22` `FR-25` `FR-26` `FR-27` |
| **Wk 8** | **Both.** Ask box switched to real cells · **seeds and hand-cells deleted, startup assertion live** · abstention · guards · outcome logging · harden<br><br>*Gate:* §9<br>`FR-34` `FR-35` `FR-36` `NFR-8` `NFR-10` | |

> **Building six months of ingestion before anyone types a task is how you end up with a beautifully-scored dataset nobody can use.** The riskiest question is whether anyone wants this. Week 3 answers it, on hand-written evidence, before the expensive half begins. The UX test cannot tell that the data is fake.

**Query budget, so it doesn't surprise you:** `10 models × 5 alias variants × 12 capabilities = 600 queries per platform` — about 20 minutes at GitHub's 30/min. While developing an adapter, run against **one model and three capabilities**, and widen only when it works.

---

## 6 · Sequencing constraints

Two dependencies cross the lane boundary and are unrecoverable if missed.

### `offset_map` before the first extraction run

**E1 ships it end of week 3. E2 needs it week 4.**

It is roughly ten lines while already walking the thread tree, and **impossible to reconstruct afterwards**. Every quote extracted without it must be re-run.

*Mitigation:* E2 builds verification in week 4 against a **hand-made `thread_context` fixture**, before E1's real one arrives. Then the handover is a swap, not an integration.

### Golden sets before the first extraction run

**E2 labels before extraction runs against real documents.**

There is no selection step. The extractor is `google/gemini-2.5-flash` via OpenRouter, decided rather than chosen, so the golden set is not a selection instrument and there is no week-6 bake-off to sequence around.

It is still unrecoverable if missed, for a different reason: it is the only instrument that can see extraction failing. A missed claim produces no error, no log line and no wrong-looking output. A misfiled one produces a verified quote in the wrong cell, and the page then says something false with a real quote underneath it. Neither is visible in the output, so a labelled set is the only way either becomes visible at all.

*E1 cross-labels ~50 items.* If two people who both read the spec disagree on what counts as good evidence, the criteria aren't clear enough to automate — far cheaper to learn in week 3 than week 6.

### And one soft constraint

**Decide the publication-gate thresholds in week 3, not week 7.** They determine whether the §9 targets are reachable, and therefore whether week 8 has a meaningful pass condition.

---

## 7 · Working agreements

**Trunk-based, small pushes.** Your lanes barely overlap, so the usual reason for long-lived branches doesn't apply — and pushing often means a `contract/` change surfaces in hours rather than at week 5.

**`contract/` changes go through a PR.** It's the only place you can break each other. It should change perhaps five times in eight weeks, each time on purpose.

**Ten minutes daily.** One real question weekly: *does the `document` contract still look right to both of us?* That's the only thing that drifts silently.

**Build `fixtures/threads/` together around week 4** — twenty real threads with the claims they should produce, hand-written. E1 flattens them, E2 extracts from them. Fastest way to find a contract mismatch while fixing it still costs an hour.

**Don't edit outside your lane.** If you need something changed in the other's directory, ask. It costs a message and saves a merge.

---

## 8 · Deferred register

Not built in version 1, with the reason and **the trigger that brings it back**. Deferral with a trip-wire is not the same as cutting.

| Deferred | Why not now | Trigger |
|---|---|---|
| **The four paid-content tests** — vendor phrase echo, embargo clustering, never-negative history, coordination graph | All need accumulated author or launch history that doesn't exist on day one | **These are the moat.** Build once ~6 months of author history exists |
| LLM-as-judge sampling | A code-verified span already catches fabrication; weekly human audit catches semantics | Volume exceeds weekly human spot-audit — and even then it **routes to a human, never issues a verdict** |
| LLM contradiction adjudication | Deciding whether a conflict is real or a condition mismatch is a judgement about truth, and would silently change what is published | **Never as an automatic decider.** Compare conditions structurally in code; escalate the residue |
| LLM slop classifier | Needs ~1,000 hand-labelled documents; the specificity floor removes most junk deterministically | The labels exist. Even then, only alongside the deterministic signals |
| Author reputation (Beta model) | Needs claims that later got ground truth. Cold-starting is guessing | ~6 months of claims to backfill against |
| Bradley–Terry ratings | Counting voices is legible and sufficient at 12 capabilities | Cells routinely have comparatives but fail the publication gate |
| Confidence intervals / posteriors | Nothing needs a posterior when you publish counts and phrases | Ranking within a band needs finer resolution than cost |
| Benchmark anchors | Benchmarks never generate a claim anyway | The board contradicts a well-known leaderboard and users ask why |
| Spike / change-point detection | The daily API diff already catches alias moves, the dangerous case | A silent update is missed and the community caught it first |
| Output verbosity in the cost model | Needs per-model output-length tracking that doesn't exist | Cost-estimate error exceeds ~25% |
| Backtesting, filter ablations | Needs six months of claim history | Six months of claims exist |
| Platforms 4–9, non-English | Each adapter is cheap; each adds noise the trust layer isn't ready for | Filter precision targets met on the first three |
| Media modalities | Different venues, different reviewer populations, weaker evidence | Text coverage targets met |
| API, MCP server, CI lockfile | Nothing to serve until the board is trustworthy | §9 met |
| **The auto-routing proxy** | **Auto-routing production traffic on unreliable consensus is worse than not routing at all** | The board has been right, tracked, for months |

---

## 9 · Done

| Measure | Target |
|---|---|
| **Roster completeness** | **100%** of in-window models present — the premise, non-negotiable |
| **Quote fidelity** | **100%** — every displayed quote verifiably present at its offset, attributed to the right comment |
| Models with ≥1 consensus label | ≥25 of the ~40 deep-harvested |
| Extraction F1 (golden set) | ≥0.85 |
| Entity resolution at snapshot specificity | ≥0.95 |
| Filter precision / false-positive on expert content | ≥0.90 / **≤5%** |
| Hard-constraint recall in the answer path | **1.00** — missing "needs vision" is unforgivable |
| **False qualification rate** | **Zero.** A qualified pick that fails in production is the worst possible output — push borderline cases to no-evidence |
| Contested rate | Tracked, **not minimised** — suspiciously low means disagreement is being hidden |
| Extraction `ValidationError` rate | <2%, alert on trend |
| Time from launch to first label | ≤21 days |
| **Zero fixtures in production** | No seeded models, no hand-written cells. Asserted at startup |
| **Decisions made and tracked** | **≥10 real recommendations adopted, with outcomes recorded** |

> **The measure that decides whether this continues:** of the recommendations adopted, did the cheaper model hold?
>
> Every other metric measures internal consistency. This one measures usefulness — and it's the only one that can tell us we were wrong.
