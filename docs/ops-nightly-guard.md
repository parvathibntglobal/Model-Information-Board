# The nightly runs: once each, in order

GitHub's `schedule` trigger starts our workflows 3 to 10 hours late (measured 2026-11-13; `contract/nightly_guard.yaml` has the figures). Running late, the agent and model fetches used to run at the same time on one daily extraction budget, and past UTC midnight.

There is no timer outside GitHub: anooj decided against one for now on 2026-11-13. So the crons are set early to absorb the delay, and the runs follow each other:

| Workflow | Starts |
|---|---|
| Agent fetch | Cron 04:00 UTC. With the delay it usually lands near 10:00–11:00. |
| Model fetch | When the agent fetch finishes. Its cron, 16:00 UTC, is only a backup. |
| Evidence feed | When the model fetch finishes, as before. |
| Topic harvest | Cron 19:00 UTC, independent. |

Agents (up to about 6 hours) and then models (up to 355 minutes) end near 22:30 UTC on a usual night, inside the day the extraction cap counts. On a night GitHub starts the agents at the 10-hour end, it still runs past midnight; only an on-time start would prevent that.

## The guard

`python scripts/nightly_guard.py --workflow <file>` is the first job (`guard`) of each of the four workflows, and the main job runs only when it says so. A `schedule` start, or a chained `workflow_run` start, ends without doing anything when:

- **it is a chained start and the run that finished wasn't the night's real run.** A test started by hand, or a late schedule run that stood down, starts nothing.
- **the workflow it waits for is still running.** The model fetch's 16:00 backup stands down while the night's agent run is going; the agents' finish starts the model fetch.
- **it already did real work tonight.** For a schedule start, "tonight" begins at 04:00 UTC (the agent cron), not "the last 12 hours". For a chained start, it begins when the run that finished was created.

A run you start by hand from the Actions tab is never stopped.

## Hand-started runs

- **With `slot` left empty, it's a test.** It runs, holds nothing off, and when it finishes it starts nothing (the model fetch does not follow an agent test).
- **With `slot` set to `nightly`, it stands in for the night's run.** Use this when a night's run failed. Its run name ends in "(nightly)", it counts as that night's run, and its finish starts the next workflow.

## How to tell it's working

- Each run's first job, **guard**, says why it ran or why it stood down.
- The agent fetch runs once a night, with `schedule` as its trigger.
- The model fetch begins when the agent fetch ends, with `workflow_run` as its trigger.
- The model fetch's late `schedule` run ends in about a minute, with its main job skipped.
- The two never show as running at the same time.
