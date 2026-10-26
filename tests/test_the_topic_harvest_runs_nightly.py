"""The blog's topic harvest runs nightly in its own workflow (2026-10-26).

Until then `scripts/harvest_topics.py` ran only from Admin -> Blogs. It has its
own workflow so its ~9 minutes never come out of the model fetch's time budget,
and it obeys the same switch as every scheduled harvest.
"""

from __future__ import annotations

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "topic-harvest.yml"


def _wf() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_it_runs_on_a_schedule_and_by_hand():
    wf = _wf()
    on = wf.get("on") or wf.get(True)  # YAML 1.1 reads a bare `on` as True
    assert on["schedule"] and "workflow_dispatch" in on


def test_it_writes_only_as_staging_and_only_when_switched_on():
    job = _wf()["jobs"]["harvest"]
    assert job["env"]["ENVIRONMENT"] == "staging", "the write guard refuses anything else"
    assert job["env"]["SCHEDULER_ENABLED"] == "${{ vars.SCHEDULER_ENABLED }}"
    steps = job["steps"]
    run = next(s for s in steps if "harvest_topics.py" in (s.get("run") or ""))
    assert run["if"] == "steps.gate.outputs.enabled == 'true'"
    assert "--dry-run" not in run["run"], "a nightly run that stores nothing is not a harvest"
    assert job["timeout-minutes"] >= 15, "a full harvest took 550 s on 2026-10-26"


def test_it_is_not_a_step_of_the_model_fetch():
    fetch = (ROOT / ".github" / "workflows" / "scheduled-fetches.yml").read_text(encoding="utf-8")
    assert "harvest_topics.py" not in fetch, "it would come out of the fetch's time budget"
