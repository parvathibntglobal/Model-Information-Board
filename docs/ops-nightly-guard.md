# The nightly runs: once each, in order

GitHub's `schedule` trigger starts our workflows 3 to 10 hours late (measured 2026-11-13; `contract/nightly_guard.yaml` has the figures). Running late, the agent and model fetches used to run at the same time on one daily extraction budget, and past UTC midnight.

There is no timer outside GitHub: anooj decided against one for now on 2026-11-13. So the crons are set early to absorb the delay, and the runs follow each other.

**Since 2026-11-25 the agent fetch is started by hand only** (anooj), from Admin → Scheduler → Model fetches → "Run agents now". The model fetch's own cron is its trigger:

| Workflow | Starts |
|---|---|
| Agent fetch | By hand only. No cron (it was 04:00 UTC from 2026-11-13). |
| Model fetch | Its cron, 04:00 UTC (was a 16:00 backup behind the agents). With the delay it lands near 07:00–14:00. A nightly agent run's finish also starts it. |
| Evidence feed | When the model fetch finishes, as before. |
| Topic harvest | Cron 19:00 UTC, independent. |

The model fetch's job stops by 355 minutes, so even a start 10 hours late ends inside the UTC day the extraction cap counts.

## The guard

`python scripts/nightly_guard.py --workflow <file>` is the first job (`guard`) of each of the four workflows, and the main job runs only when it says so. A `schedule` start, or a chained `workflow_run` start, ends without doing anything when:

- **it is a chained start and the run that finished wasn't the night's real run.** A test started by hand, or a late schedule run that stood down, starts nothing.
- **the workflow it waits for is still running.** The model fetch's cron run stands down while a nightly agent run is going; the agents' finish starts the model fetch.
- **it already did real work tonight.** For a schedule start, "tonight" begins at 04:00 UTC (the agent cron), not "the last 12 hours". For a chained start, it begins when the run that finished was created.

A run you start by hand from the Actions tab is never stopped.

## Hand-started runs

- **With `slot` left empty, it's a test.** It runs, holds nothing off, and when it finishes it starts nothing (the model fetch does not follow an agent test).
- **With `slot` set to `nightly`, it stands in for the night's run.** Use this when a night's run failed. For the agent fetch, which has no cron since 2026-11-25, it is how every real run is started. Its run name ends in "(nightly)", it counts as that night's run, and its finish starts the next workflow.
- **Its finish starts the model fetch even if the models already ran today.** A chained start counts from the creation of the run that finished, not from 04:00. So if the agent run failed, the models chained after it, and you then rerun the agents with `slot: nightly`, the models and the evidence feed run a second time. Little is due on that second pass, so the cost is small. If the models already ran and you only want the agents, leave `slot` empty. (Parvathi, #631 review, 2026-11-13.)

## How to tell it's working

- Each run's first job, **guard**, says why it ran or why it stood down.
- The agent fetch runs only when someone starts it, with `workflow_dispatch` as its trigger.
- The model fetch runs once a day from its `schedule`, or from `workflow_run` after a nightly agent run.
- A model `schedule` run that finds the models already ran that day ends in about a minute, with its main job skipped.
- The two never show as running at the same time.
