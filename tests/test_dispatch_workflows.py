"""The on-time dispatcher and its guard (contract/dispatch_schedule.yaml).

No network: GitHub is a fake. What these pin:
* the schedule is read strictly (rule 12);
* a workflow is started once per slot, inside the catch-up window, and never when
  it already did real work in its window;
* a guarded trigger stands down after real work; an unguarded one always runs;
* a run the guard stood down is NOT real work, so it cannot hold off the next;
* a run still waiting in its guard counts only if it is older (no mutual stand-down);
* the four workflows are wired: guard job first, main job gated on it, and the
  model fetch follows the agent fetch.
"""

from __future__ import annotations

import pathlib
from datetime import UTC, datetime

import pytest
import yaml

from scripts import dispatch_workflows as dw

ROOT = pathlib.Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 14, 13, 5, tzinfo=UTC)


def _sched():
    return dw.load_schedule()


def test_the_real_schedule_loads_and_names_the_four_workflows():
    s = _sched()
    assert set(s.entries) == {
        "agent-fetches.yml",
        "scheduled-fetches.yml",
        "topic-harvest.yml",
        "evidence-feed.yml",
    }
    assert s.entries["agent-fetches.yml"].dispatch_at == (13, 0)
    assert s.entries["evidence-feed.yml"].dispatch_at is None  # follows the model fetch
    assert "workflow_run" in s.entries["scheduled-fetches.yml"].guard_events


@pytest.mark.parametrize(
    "mutate, says",
    [
        (lambda r: r.pop("catch_up_minutes"), "catch_up_minutes"),
        (lambda r: r["workflows"]["agent-fetches.yml"].pop("counts_events"), "counts_events"),
        (lambda r: r["workflows"]["agent-fetches.yml"].update(dispatch_at_utc="1pm"), "HH:MM"),
        (lambda r: r["workflows"]["agent-fetches.yml"].update(dispatch_at_utc="25:00"), "HH:MM"),
        (
            lambda r: r["workflows"]["agent-fetches.yml"].update(guard_events=["push"]),
            "guard_events",
        ),
        (
            lambda r: r["workflows"]["agent-fetches.yml"].update(skip_if_ran_within_hours=0),
            "positive",
        ),
    ],
)
def test_a_missing_or_wrong_setting_is_refused(mutate, says):
    raw = yaml.safe_load((ROOT / "contract" / "dispatch_schedule.yaml").read_text(encoding="utf-8"))
    mutate(raw)
    with pytest.raises(dw.ScheduleError, match=says):
        dw.parse_schedule(raw)


def test_a_slot_is_dispatched_once_inside_the_catch_up_window():
    s = _sched()
    never = lambda e, since: False  # noqa: E731
    assert [f for f, _ in dw.to_dispatch(s, NOW, never)] == ["agent-fetches.yml"]
    late = datetime(2026, 11, 14, 16, 1, tzinfo=UTC)  # 13:00 + 181 min: past catch-up
    assert "agent-fetches.yml" not in [f for f, _ in dw.to_dispatch(s, late, never)]
    before = datetime(2026, 11, 14, 12, 59, tzinfo=UTC)
    assert dw.to_dispatch(s, before, never) == []


def test_a_workflow_that_already_did_real_work_is_not_dispatched():
    s = _sched()
    assert dw.to_dispatch(s, NOW, lambda e, since: True) == []


def test_a_guarded_trigger_stands_down_and_an_unguarded_one_runs():
    e = _sched().entries["scheduled-fetches.yml"]
    ran = lambda e, since: True  # noqa: E731
    assert dw.guard_decision(e, "schedule", NOW, ran)[0] is False
    assert dw.guard_decision(e, "workflow_run", NOW, ran)[0] is False
    assert (
        dw.guard_decision(e, "workflow_dispatch", NOW, ran)[0] is True
    )  # a person, or our dispatcher
    assert dw.guard_decision(e, "schedule", NOW, lambda e, since: False)[0] is True


class _FakeGH:
    """Runs of one workflow, each with its main job's status and conclusion."""

    repo = "o/r"

    def __init__(self, runs):
        self.runs = (
            runs  # [(id, event, job_status, job_conclusion)] ; job_status None = no main job yet
        )

    def get(self, path):
        if "/jobs" in path:
            rid = int(path.split("/runs/")[1].split("/")[0])
            st, concl = next((s, c) for i, _, s, c in self.runs if i == rid)
            return {
                "jobs": [] if st is None else [{"name": "fetch", "status": st, "conclusion": concl}]
            }
        return {"workflow_runs": [{"id": i, "event": ev} for i, ev, _, _ in self.runs]}


ENTRY = dw.Entry(
    "scheduled-fetches.yml",
    "fetch",
    (21, 0),
    12,
    frozenset({"schedule", "workflow_run"}),
    frozenset({"schedule", "workflow_dispatch", "workflow_run"}),
)
SINCE = datetime(2026, 11, 14, 1, 0, tzinfo=UTC)


def test_a_stood_down_run_is_not_real_work():
    gh = _FakeGH([(10, "schedule", "completed", "skipped")])
    assert dw.real_work_checker(gh, this_run_id=20)(ENTRY, SINCE) is False


def test_a_finished_or_running_main_job_is_real_work():
    assert dw.real_work_checker(
        _FakeGH([(10, "workflow_run", "completed", "success")]), this_run_id=20
    )(ENTRY, SINCE)
    assert dw.real_work_checker(
        _FakeGH([(10, "workflow_run", "completed", "failure")]), this_run_id=20
    )(ENTRY, SINCE)
    assert dw.real_work_checker(_FakeGH([(30, "schedule", "in_progress", None)]), this_run_id=20)(
        ENTRY, SINCE
    )


def test_a_run_still_in_its_guard_counts_only_if_older():
    """Two runs starting together must not both stand down."""
    waiting = [(10, "schedule", None, None)]
    assert (
        dw.real_work_checker(_FakeGH(waiting), this_run_id=20)(ENTRY, SINCE) is True
    )  # older one wins
    assert (
        dw.real_work_checker(_FakeGH(waiting), this_run_id=5)(ENTRY, SINCE) is False
    )  # this one is older


def test_this_run_and_uncounted_events_are_ignored():
    gh = _FakeGH([(20, "schedule", "completed", "success")])
    assert dw.real_work_checker(gh, this_run_id=20)(ENTRY, SINCE) is False
    weekly_only = dw.Entry(
        "evidence-feed.yml",
        "fetch",
        None,
        12,
        frozenset({"workflow_run"}),
        frozenset({"workflow_run"}),
    )
    assert (
        dw.real_work_checker(_FakeGH([(10, "schedule", "completed", "success")]), this_run_id=20)(
            weekly_only, SINCE
        )
        is False
    )


def test_the_four_workflows_are_wired_to_the_guard():
    for file, entry in _sched().entries.items():
        wf = yaml.safe_load((ROOT / ".github" / "workflows" / file).read_text(encoding="utf-8"))
        jobs = wf["jobs"]
        assert list(jobs)[0] == "on-time", file
        assert f"--workflow {file}" in jobs["on-time"]["steps"][-1]["run"], file
        main = jobs[entry.job]
        assert main["needs"] == "on-time" and main["if"] == "needs.on-time.outputs.run == 'true'", (
            file
        )
        assert wf["permissions"]["actions"] == "read", file
    model = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "scheduled-fetches.yml").read_text(encoding="utf-8")
    )
    assert model[True]["workflow_run"]["workflows"] == [
        "Agent fetches"
    ]  # PyYAML reads `on:` as True
    agent = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "agent-fetches.yml").read_text(encoding="utf-8")
    )
    assert agent["name"] == "Agent fetches"
