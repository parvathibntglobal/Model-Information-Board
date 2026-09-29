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

## What is code, and what is the service's (yours)

| | |
|---|---|
| **code (built here)** | the selector (`judge/scheduler.rank_due`), the runner (`scripts/run_scheduled_fetches.py`), the per-source scope (`fetch_model --sources`), the host-free summary (`judge/scheduler.summarise_runs`) |
| **yours, on Railway** | a second **service** from this image whose start command is the runner; a **cron** schedule; a mounted **volume** for the raw store (`RAW_STORE_PATH`); a **token** that may only comment on issues, and `SCHEDULER_ISSUE` naming the one it posts to; the **plan** that pays for the container time; and finally `SCHEDULER_ENABLED` |

The admin page's settings section shows `SCHEDULER_ENABLED` and `SCHEDULER_ISSUE`
as set / not set, so their state is visible from the board without opening
Railway.

## The selection rule

`rank_due` returns the tracked, in-window models that are due:

- **never fetched → a first fetch**, at the larger thread cap (its whole backlog
  is unread);
- **last success ≥ 7 days ago → a refresh**, at the smaller cap;
- ordered **first fetches first, then the longest-stale**. It never drops a model
  on a yield guess: a model a schedule stopped fetching reads exactly like one
  nobody discusses (rule 4). Yield-ordering within a night is a later refinement
  and waits for the end-record fields (#489) to accumulate.

New models reach the list by being added to `contract/tracked_models.yaml`; the
promotion report (#492) is how a person decides which untracked models earn that.

## Turning it on, once the basis is honest

1. Provision the volume and point `RAW_STORE_PATH` into it. Without a volume,
   every deploy wipes the payloads NFR-4 requires kept.
2. Set the service's variables: a write-capable `DATABASE_URL`,
   `OPENROUTER_API_KEY`, `EXTRACTION_DAILY_BUDGET_USD`, `ENVIRONMENT=production`,
   the GitHub and RapidAPI credentials, `USER_AGENT`.
3. Create an issue for the summaries and set `SCHEDULER_ISSUE` to its number, and
   give the token issue-comment scope. The issue is public; the summary carries
   model names and counts only — no quotes, authors or hosts.
4. Add the cron (UTC).
5. **Last: set `SCHEDULER_ENABLED=1`.** Before this, every scheduled run exits
   having harvested nothing.

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
