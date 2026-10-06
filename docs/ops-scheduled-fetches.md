# Scheduled per-model fetches — built, and off until a person turns it on

The evidence pipeline runs one model at a time through `scripts/fetch_model.py`.
This adds the piece that decides *which* models are due and runs them in turn, so
the models page stays fresh without somebody clicking Fetch. It is **disabled by
default** and harvests nothing until `SCHEDULER_ENABLED` is set on the service.

## Why it is off

A public repository held a Reddit-derived article, so `contract/sources.yaml`'s
undertaking reads `derived_publication: false` while that is no longer true, and
the seven non-GitHub rulings rest on it. Until the basis is honest again — repo
private, the file gone, the undertaking re-signed — a full harvest must not run.
`SCHEDULER_ENABLED` being unset is the guard that holds that line, and it is a
person's to lift.

Two independent guards, so neither alone is load-bearing:

- **`SCHEDULER_ENABLED`** (this runner) — unset means nothing runs at all.
- **the terms gate** (inside `fetch_model`) — once the undertaking is flipped to
  void, every non-GitHub arm skips itself with its reason, whatever the switch
  says.

## Where it runs: a GitHub Action (since 2026-10-06)

`.github/workflows/scheduled-fetches.yml`, daily at **20:30 UTC (02:00 IST)**,
and by hand from the Actions tab (`workflow_dispatch`, with optional
`max_models` and `sources`). #494 planned a Railway service; the repository is
staying public and standard GitHub-hosted runners are free for public
repositories, so the team chose Actions.

| | |
|---|---|
| **code** | the selector (`judge/scheduler.rank_due`, policy in `contract/scheduler.yaml`), the runner (`scripts/run_scheduled_fetches.py`), the per-source scope (`fetch_model --sources`), the host-free summary (`judge/scheduler.summarise_runs`), the workflow |
| **repository settings (yours)** | secrets `STAGING_DATABASE_URL` (exists), `OPENROUTER_API_KEY`, `RAPIDAPI_KEY` (Reddit), `X_RAPIDAPI_KEY` (X - a separate key for a separate provider); variables `USER_AGENT` (exists), `REDDIT_PROVIDER` (`reddit34`), `SCRAPER_PROVIDER` (`twitter241`), `EXTRACTION_DAILY_BUDGET_USD`, `SCHEDULER_ISSUE`, and last `SCHEDULER_ENABLED=1` |

What an Action changes, and the workflow file says the same:

1. **The 6-hour job limit.** A first fetch at the 100-thread cap measured about
   2-2.5 h on 2026-10-06 (median 28 s, mean 85 s per thread over 26 threads).
   The runner stops *launching* models at `--deadline-minutes 200` and names
   each one it did not run; the next night continues.
2. **The raw store is not kept.** A runner starts empty and is discarded. Every
   row reaches the shared database, so the board is unaffected; re-extraction
   from raw later (NFR-4) is what is lost - the gap that already exists between
   laptops. A shared object store closes it. **Do not use Actions artifacts for
   it**: in a public repository they would publish Reddit and X payloads.
3. **The logs are public.** The runner prints model names, counts and its
   decisions; `fetch_model`'s output is captured, not printed.

`/admin/settings` shows `SCHEDULER_ENABLED` and `SCHEDULER_ISSUE` for the
backend that serves it, not for the Action - check the repository variables.

## The selection rule

`rank_due` returns the tracked, in-window models that are due:

- **never fetched → a first fetch**, at the larger thread cap (its whole backlog
  is unread);
- **last success ≥ 7 days ago → a refresh**, at the smaller cap;
- ordered **first fetches first, then the longest-stale**. It never drops a model
  on a yield guess: a model a schedule stopped fetching reads exactly like one
  nobody discusses (rule 4). Yield-ordering within a night is a later refinement
  and waits for the end-record fields (#489) to accumulate.

The cadence (7 days) and the two caps (100, 25) live in `contract/scheduler.yaml`
since 2026-10-05; there is no default in code, so a missing value refuses.

**The daily budget stops the batch.** `EXTRACTION_DAILY_BUDGET_USD` is one
team-wide figure. The runner checks today's spend before each model; once it
is spent, the remaining models are not launched and each is listed in the
summary as `not run: daily budget spent` - a launched model would harvest,
using platform quota, and extract nothing. An unset budget refuses the batch.

**Reddit depth per fetch** is `FETCH_REDDIT_THREADS` (default 5): how many
Reddit threads have their comments fetched. One thread arrives as hundreds of
documents and is extracted as one thread, so this - not the thread cap - is
usually what bounds a fetch's Reddit evidence.

New models reach the list by being added to `contract/tracked_models.yaml`; the
promotion report (#492) is how a person decides which untracked models earn that.

## Turning it on, once the basis is honest

1. Add the secrets `OPENROUTER_API_KEY`, `RAPIDAPI_KEY` and `X_RAPIDAPI_KEY`, and the
   variables `REDDIT_PROVIDER=reddit34` and `SCRAPER_PROVIDER=twitter241`
   (repository settings -> Secrets and variables -> Actions). Only the
   repository owner can, on a personal-account repository.
2. Add the variables `EXTRACTION_DAILY_BUDGET_USD` and `SCHEDULER_ISSUE` (an
   issue for the nightly summary; it is public, and the summary carries model
   names and counts only - no quotes, authors or hosts).
3. **Set the variable `SCHEDULER_ENABLED=1`**, then straight away run it once by
   hand - Actions -> Scheduled fetches -> Run workflow, `max_models` 1,
   `sources` github - and read its summary on `SCHEDULER_ISSUE` before the
   first nightly run at 02:00 IST.
4. To pause it, set `SCHEDULER_ENABLED` to anything but `1`; the job then ends
   green having done nothing.

## Testing it end to end today, without harvesting on a false basis

GitHub's ruling (`github-api-terms`) does not rest on the undertaking, so a
GitHub-only run breaks nothing while the basis is being fixed. Every other arm is
`skipped` with a reason, never errored — the #491 path.

```
# one model, GitHub only:
python -m scripts.fetch_model <model_version_id> --sources github

# the whole due list, GitHub only, without the enable switch:
python -m scripts.run_scheduled_fetches --dry-run          # what is due, no fetch
SCHEDULER_ENABLED=1 python -m scripts.run_scheduled_fetches --sources github --max-models 1
```

`--dry-run` needs no switch and harvests nothing; it prints what is due. A
`--sources github` run exercises harvest → assemble → triage → extract → curate
end to end on the one source that is safe to run now.
