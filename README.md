# Model Information Board

**What engineers actually report about AI models, filed by the job they were doing, in their own words.**

Leaderboards give each model one score. Engineers who have shipped with these models write about them every day, in GitHub issues, on Hacker News, dev.to, Hugging Face and engineering blogs. This board collects those reports, keeps only what can be checked against its source, and files each one under:

- **Best for:** the jobs a model was used for
- **Capabilities:** what it is good or bad at
- **Metrics:** figures engineers measured

Every entry is the engineer's exact words with a link to where they wrote it. It is a verdict and a count, never a score.

## What's on it

- **Board:** every job, capability and metric, with the reports filed under each
- **Models:** one model across every section it's discussed in
- **Compare:** up to three models side by side
- **Blogs:** posts written from the evidence, published after review

## How it works

```
registry → harvest → assemble → screen → classify → verify → board
```

Models come from a polled registry. Reports are harvested from public sources, flattened and deduplicated, screened by rules, then classified into board sections by one model call. A quote is kept only if it appears word for word in its source.

## The rules

1. **No claim without a verbatim quote,** verified in code by exact substring match.
2. **A model may propose, never decide.** No model counts, weighs, ranks or filters.
3. **No synthesised number reaches a page.** Every figure is counted or measured.
4. **Silence is not criticism.** "Nobody has discussed this" never looks like criticism.
5. **Config in versioned YAML, not code** (`contract/`).

The full set is in `CLAUDE.md`.

## Layout

```
collect/     registry, harvest, assemble, triage
judge/       screen, classify, verify, board, blogs, the API
web/         the React + Vite frontend
contract/    versioned config, schema and migrations
scripts/     operational scripts
tests/       the test suite
docs/        design notes and measurements
```

## Getting started

```bash
pip install -e ".[dev]"
cp .env.example .env              # see the comments in it for what each value unlocks
python -m collect.cli db migrate  # needs DATABASE_URL

python run-backend.py --write     # or --staging for read-only
cd web && npm install && npm run dev
```

Tests: `pytest -q`. The Postgres-backed tests need `TEST_DATABASE_URL`.

## Documents

| | |
|---|---|
| `CLAUDE.md` | The rules and working conventions |
| `BUILD-PLAN.md` | The original plan and requirements |
| `BUILD-PLAN-UPDATES.md` | How each requirement stands today |
| `docs/logic-and-workflow.md` | The pipeline design |
