# Starting the daily workflows on time

GitHub's `schedule` trigger starts our workflows 3 to 10 hours late. This was measured on 2026-11-13; `contract/dispatch_schedule.yaml` has the figures. A `workflow_dispatch` start is not delayed. So a small cron that **we** host starts the workflows through GitHub's API at the times in `contract/dispatch_schedule.yaml`:

| Workflow | Starts |
|---|---|
| Agent fetch | 13:00 UTC |
| Model fetch | When the agent fetch finishes, with 21:00 UTC as a fallback |
| Topic harvest | 19:00 UTC |
| Evidence feed | After the model fetch, as before |

## The two halves

- **`python scripts/dispatch_workflows.py dispatch`** runs every 10 minutes on our cron. It starts a workflow when its time has passed (within `catch_up_minutes`), unless that workflow already did real work in its window. Running it more often than needed is harmless: it starts each slot once.
- **`python scripts/dispatch_workflows.py guard --workflow <file>`** is the first job (`on-time`) of each of the four workflows. When GitHub's own late schedule fires, or a chained start arrives (`workflow_run`), the run ends without doing anything if the workflow already did real work. GitHub's schedule stays as a backup: if our cron is down, the late run still happens.

Try it without starting anything: `python scripts/dispatch_workflows.py dispatch --dry-run`.

## What the cron needs

**1. A GitHub token that can start workflows on `parvathibntglobal/Model-Information-Board`.** Either of these works:
- A fine-grained token created by the repository owner, scoped to this repository, with **Actions: Read and write**. Nothing else.
- A classic token from a collaborator with write access, with the `repo` scope. Classic tokens are broader; prefer the fine-grained one.

**2. Two environment variables on the cron host:**
- `GITHUB_DISPATCH_TOKEN`: the token above.
- `GITHUB_REPOSITORY`: `parvathibntglobal/Model-Information-Board`.

**3. The command, every 10 minutes:** `python scripts/dispatch_workflows.py dispatch`

The script needs only Python 3.11+ and PyYAML.

### On Railway (suggested: we already run the app there)

1. Add a new service from the same repository as the app.
2. In the service's settings:
   - set **Cron Schedule** to `*/10 * * * *`;
   - set the **start command** to `pip install pyyaml && python scripts/dispatch_workflows.py dispatch`;
   - add the two environment variables.
3. Railway starts the service on each tick and it exits. Its logs show `started <file>` or `nothing due`.

Do not use a third-party cron website: it would hold a token that can start our workflows.

## How to tell it's working

- Each workflow run's first job, **on-time**, says either why it ran or why it stood down.
- The next agent-fetch run should begin at about 13:00 UTC, with `workflow_dispatch` as its trigger.
- The model fetch should begin when the agent fetch ends, with `workflow_run` as its trigger.
- GitHub's late `schedule` runs should end in about a minute, with their main job skipped.
