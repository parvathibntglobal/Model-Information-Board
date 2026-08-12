# Model Information Board

**You describe the work. The board names the models engineers have actually
made that work with, cheapest first, and shows you their exact words.**

Coding agents pick their own models for every sub-agent they spawn, and they
reach for the strongest one almost everywhere. Most sub-agents don't need it.
Something 10-40x cheaper usually does the job - but *"use something cheaper"*
is a hope, not a decision.

Benchmarks can't tell you which. Engineers who already shipped can, and they
publish constantly - in GitHub issues, on Reddit, on engineering blogs. That
evidence is buried in marketing, and it decays as providers silently update
models behind the same names.

This collects it, strips the paid and fake content, and states what people
actually found - in their words.

## Documents

| | |
|---|---|
| **`BUILD-PLAN.md`** | Requirements (36 FR, 10 NFR), the eight weeks, and who does what |
| **`docs/logic-and-workflow.md`** | How the machinery works - the nine pipeline stages and the answer path |
| **`CLAUDE.md`** | Conventions and non-negotiable rules, read by both Claude Code sessions |

## Layout

```
contract/     shared. the interface between two engineers. changes go via PR
collect/      Engineer 1 - registry, harvest, assemble, triage, ops
judge/        Engineer 2 - extract, vet, curate, publish, answer path
fixtures/     hand-written cells, golden sets, shared test threads
docs/         the specification
```

Two engineers work this repo in parallel. The data crosses the lane boundary
exactly once, in one direction:

```
collect/  ---->  document + thread_context  ---->  judge/
```

## Getting started

```bash
cp .env.example .env          # then fill in the credentials below
pip install -e ".[dev]"
psql "$DATABASE_URL" -f contract/tables.sql
```

**Credentials needed:**

| | Setup | Limit |
|---|---|---|
| GitHub | Personal access token - five minutes | 30 search req/min |
| Reddit | Register a script app - client id + secret, ~15 min | 60 req/min |
| Blogs | Nothing. RSS and sitemaps | be polite: ~1 req/sec |

**Before writing any other code:** finish `contract/seed_models.yaml`. Nine
models are filled in with real identifiers and aliases; every price, context
window and date is marked `# VERIFY` and must be read off the provider page,
with the URL recorded. Slot 10 is empty on purpose - it needs a model released
in the last 30 days, which only you can know. The checklist is at the bottom
of that file.

## The five rules

1. **No claim without a verbatim quote**, verified in code by exact substring
   match. No quote, no claim.
2. **Exactly two stages call a language model** - `judge/extract/` and
   `judge/ask/`. An LLM may propose; it may never decide.
3. **No synthesised number reaches a page.** Every figure shown is counted or
   measured. Consensus is a phrase, never a score.
4. **Silence is not criticism.** *"Nobody has discussed this"* must never look
   like *"engineers report problems"*.
5. **Config in versioned YAML, not code.**

Full context in `CLAUDE.md`.
