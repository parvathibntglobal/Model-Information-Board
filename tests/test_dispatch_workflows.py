"""The on-time dispatcher and its guard (contract/dispatch_schedule.yaml).

No network: GitHub is a fake. What these pin:
* the schedule is read strictly (rule 12);
* a workflow is started once per slot, inside the catch-up window, and never when
  it already did real work in its window;
* the window is ANCHORED to the most recent `window_opens_utc`, not rolling
  (#631 review: agents end 13:20, GitHub's model schedule fires 02:48);
* only a nightly start counts: a hand-started test holds nothing off;
* a `workflow_run` start follows only a finished run that did real nightly work
  (#631 review: a morning agent test must not start the model fetch);
* a guarded trigger stands down after real work; an unguarded one always runs;
* a run the guard stood down is NOT real work, so it cannot hold off the next;
* a run still waiting in its guard counts only if it is older (no mutual stand-down);
* the four workflows are wired: guard job first, main job gated on it, the
  dispatched ones mark a nightly start in their run name, and the model fetch
  follows the agent fetch.
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


def _at(day, hh, mm=0):
    return datetime(2026, 11, day, hh, mm, tzinfo=UTC)


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
    # The model fetch's day begins at the agent slot, not at its own fallback.
    assert s.entries["scheduled-fetches.yml"].window_opens == (13, 0)


@pytest.mark.parametrize(
    "mutate, says",
    [
        (lambda r: r.pop("catch_up_minutes"), "catch_up_minutes"),
        (lambda r: r["workflows"]["agent-fetches.yml"].pop("counts_events"), "counts_events"),
        (lambda r: r["workflows"]["agent-fetches.yml"].pop("window_opens_utc"), "window_opens"),
        (lambda r: r["workflows"]["agent-fetches.yml"].update(dispatch_at_utc="1pm"), "HH:MM"),
        (lambda r: r["workflows"]["agent-fetches.yml"].update(dispatch_at_utc="25:00"), "HH:MM"),
        (lambda r: r["workflows"]["agent-fetches.yml"].update(window_opens_utc=13), "HH:MM"),
        (
            lambda r: r["workflows"]["agent-fetches.yml"].update(guard_events=["push"]),
            "guard_events",
        ),
        # A hand-started run is never guarded: it is either a test or the dispatcher.
        (
            lambda r: r["workflows"]["agent-fetches.yml"].update(
                guard_events=["workflow_dispatch"]
            ),
            "guard_events",
        ),
        # Counting every hand start is the defect #631's review found; refused by name.
        (
            lambda r: r["workflows"]["agent-fetches.yml"].update(
                counts_events=["schedule", "workflow_dispatch"]
            ),
            "counts_events",
        ),
        # Opening the window after the dispatch slot would look back a whole day.
        (
            lambda r: r["workflows"]["scheduled-fetches.yml"].update(window_opens_utc="22:00"),
            "too long before",
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
    late = _at(14, 16, 1)  # 13:00 + 181 min: past catch-up
    assert "agent-fetches.yml" not in [f for f, _ in dw.to_dispatch(s, late, never)]
    assert dw.to_dispatch(s, _at(14, 12, 59), never) == []


def test_a_workflow_that_already_did_real_work_is_not_dispatched():
    s = _sched()
    assert dw.to_dispatch(s, NOW, lambda e, since: True) == []


def test_the_window_is_anchored_to_the_slot_not_rolling():
    """#631 review, Parvathi: on a light night the agents end at 13:20 and the
    model fetch follows at once; GitHub's 20:30 model schedule has arrived as
    late as 02:48. A rolling 12 hours lets that second run through, after UTC
    midnight, on the next day's budget. Anchored at 13:00, it stands down."""
    model = _sched().entries["scheduled-fetches.yml"]
    real_runs = [_at(14, 13, 20)]  # the model fetch the agent run started

    def did_real_work(e, since):
        return any(t >= since for t in real_runs)

    late_schedule = _at(15, 2, 48)
    run, why = dw.guard_decision(model, "schedule", late_schedule, did_real_work)
    assert run is False, why
    assert "2026-11-14 13:00Z" in why

    # ... and the NEXT day's agent-started model fetch still runs.
    next_day = _at(15, 13, 25)
    trigger = (True, "agent-fetches.yml run 1 ran `fetch` (success)")
    assert dw.guard_decision(model, "workflow_run", next_day, did_real_work, trigger)[0] is True


def test_the_fallback_slot_does_not_repeat_an_afternoon_model_fetch():
    """The 21:00 fallback sees the 13:20 run, which a rolling 12 hours also did -
    but a window anchored at 21:00 would not. The anchor is the agent slot."""
    s = _sched()
    model_ran_at = _at(14, 13, 20)
    due = dw.to_dispatch(s, _at(14, 21, 5), lambda e, since: model_ran_at >= since)
    assert "scheduled-fetches.yml" not in [f for f, _ in due]


def test_a_guarded_trigger_stands_down_and_an_unguarded_one_runs():
    e = _sched().entries["scheduled-fetches.yml"]
    ran = lambda e, since: True  # noqa: E731
    ok = (True, "the night's agent run ran")
    assert dw.guard_decision(e, "schedule", NOW, ran)[0] is False
    assert dw.guard_decision(e, "workflow_run", NOW, ran, ok)[0] is False
    # A person, or our dispatcher: never guarded.
    assert dw.guard_decision(e, "workflow_dispatch", NOW, ran)[0] is True
    assert dw.guard_decision(e, "schedule", NOW, lambda e, since: False)[0] is True


def test_a_guarded_workflow_run_without_the_finished_runs_verdict_is_refused():
    e = _sched().entries["scheduled-fetches.yml"]
    with pytest.raises(ValueError, match="verdict"):
        dw.guard_decision(e, "workflow_run", NOW, lambda e, since: False)


# ── which starts count ──────────────────────────────────────────────────────


def test_only_a_nightly_hand_start_counts():
    agent = _sched().entries["agent-fetches.yml"]
    assert dw.counted_start(
        agent, {"event": "workflow_dispatch", "display_title": "Agent fetches (nightly)"}
    )
    assert not dw.counted_start(
        agent, {"event": "workflow_dispatch", "display_title": "Agent fetches"}
    )
    assert dw.counted_start(agent, {"event": "schedule", "display_title": "Agent fetches"})
    feed = _sched().entries["evidence-feed.yml"]
    # The feed counts no hand start at all, nightly-named or not.
    assert not dw.counted_start(
        feed, {"event": "workflow_dispatch", "display_title": "Evidence feed (nightly)"}
    )


# ── the run that finished, for a workflow_run start ─────────────────────────


def _finished(event, title, run_id=7, path=".github/workflows/agent-fetches.yml"):
    return {"id": run_id, "event": event, "display_title": title, "path": path}


def _job(conclusion):
    return lambda run_id, name: {"name": name, "status": "completed", "conclusion": conclusion}


def test_a_morning_agent_test_does_not_start_the_model_fetch():
    """#631 review, Parvathi: the 2026-11-12 05:20Z agent run was a test started
    by hand with `max_models`; its completion must not start the full model
    fetch - it would, and then the 21:00 fallback would start a second one."""
    s = _sched()
    test_run = _finished("workflow_dispatch", "Agent fetches")
    ok, why = dw.trigger_verdict(s, test_run, _job("success"))
    assert ok is False and "not a nightly start" in why
    model = s.entries["scheduled-fetches.yml"]
    run, _ = dw.guard_decision(
        model, "workflow_run", _at(12, 6, 30), lambda e, since: False, (ok, why)
    )
    assert run is False


def test_the_nightly_agent_run_starts_the_model_fetch():
    s = _sched()
    for finished in (
        _finished("workflow_dispatch", "Agent fetches (nightly)"),
        _finished("schedule", "Agent fetches"),
    ):
        assert dw.trigger_verdict(s, finished, _job("success"))[0] is True
        # It finished badly: the model fetch still follows. A failed agent run
        # did real work and is not a reason to skip the models.
        assert dw.trigger_verdict(s, finished, _job("failure"))[0] is True


def test_a_late_schedule_that_stood_down_does_not_start_the_model_fetch_early():
    """GitHub's late agent schedule stands down while the night's agent run is
    still going, and completes at once. Following it would start the model fetch
    with the agents still running."""
    s = _sched()
    stood_down = _finished("schedule", "Agent fetches")
    ok, why = dw.trigger_verdict(s, stood_down, _job("skipped"))
    assert ok is False and "stood down" in why
    ok, _ = dw.trigger_verdict(s, stood_down, lambda run_id, name: None)
    assert ok is False


def test_the_feed_follows_only_a_model_fetch_that_ran():
    s = _sched()
    model_run = _finished(
        "workflow_run", "Scheduled fetches", path=".github/workflows/scheduled-fetches.yml"
    )
    assert dw.trigger_verdict(s, model_run, _job("success"))[0] is True
    assert dw.trigger_verdict(s, model_run, _job("skipped"))[0] is False
    model_test = _finished(
        "workflow_dispatch", "Scheduled fetches", path=".github/workflows/scheduled-fetches.yml"
    )
    assert dw.trigger_verdict(s, model_test, _job("success"))[0] is False


def test_a_finished_run_from_an_unlisted_workflow_is_refused():
    with pytest.raises(SystemExit, match="refusing to guess"):
        dw.trigger_verdict(
            _sched(),
            _finished("schedule", "X", path=".github/workflows/ci.yml"),
            _job("success"),
        )


# ── the real-work check against GitHub's run list ───────────────────────────


class _FakeGH:
    """Runs of one workflow, each with its main job's status and conclusion."""

    repo = "o/r"

    def __init__(self, runs):
        # [(id, event, job_status, job_conclusion[, display_title])];
        # job_status None = no main job yet
        self.runs = [r if len(r) == 5 else (*r, "Scheduled fetches") for r in runs]

    def get(self, path):
        if "/jobs" in path:
            rid = int(path.split("/runs/")[1].split("/")[0])
            st, concl = next((s, c) for i, _, s, c, _ in self.runs if i == rid)
            return {
                "jobs": [] if st is None else [{"name": "fetch", "status": st, "conclusion": concl}]
            }
        return {
            "workflow_runs": [
                {"id": i, "event": ev, "display_title": t} for i, ev, _, _, t in self.runs
            ]
        }


ENTRY = dw.Entry(
    "scheduled-fetches.yml",
    "fetch",
    (21, 0),
    (13, 0),
    frozenset({"schedule", "workflow_run"}),
    frozenset({"schedule", "workflow_run", "nightly_dispatch"}),
)
SINCE = _at(14, 13)


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


def test_a_hand_started_test_is_not_real_work_and_a_nightly_one_is():
    test = [(10, "workflow_dispatch", "completed", "success", "Scheduled fetches")]
    assert dw.real_work_checker(_FakeGH(test), this_run_id=20)(ENTRY, SINCE) is False
    nightly = [(10, "workflow_dispatch", "completed", "success", "Scheduled fetches (nightly)")]
    assert dw.real_work_checker(_FakeGH(nightly), this_run_id=20)(ENTRY, SINCE) is True


def test_a_run_still_in_its_guard_counts_only_if_older():
    """Two runs starting together must not both stand down."""
    waiting = [(10, "schedule", None, None)]
    assert dw.real_work_checker(_FakeGH(waiting), this_run_id=20)(ENTRY, SINCE) is True
    assert dw.real_work_checker(_FakeGH(waiting), this_run_id=5)(ENTRY, SINCE) is False


def test_this_run_and_uncounted_events_are_ignored():
    gh = _FakeGH([(20, "schedule", "completed", "success")])
    assert dw.real_work_checker(gh, this_run_id=20)(ENTRY, SINCE) is False
    weekly_only = dw.Entry(
        "evidence-feed.yml",
        "fetch",
        None,
        (13, 0),
        frozenset({"workflow_run"}),
        frozenset({"workflow_run"}),
    )
    assert (
        dw.real_work_checker(_FakeGH([(10, "schedule", "completed", "success")]), this_run_id=20)(
            weekly_only, SINCE
        )
        is False
    )


# ── the workflows ───────────────────────────────────────────────────────────


def _wf(file):
    return yaml.safe_load((ROOT / ".github" / "workflows" / file).read_text(encoding="utf-8"))


def test_the_four_workflows_are_wired_to_the_guard():
    for file, entry in _sched().entries.items():
        wf = _wf(file)
        jobs = wf["jobs"]
        assert list(jobs)[0] == "on-time", file
        assert f"--workflow {file}" in jobs["on-time"]["steps"][-1]["run"], file
        main = jobs[entry.job]
        assert main["needs"] == "on-time" and main["if"] == "needs.on-time.outputs.run == 'true'", (
            file
        )
        assert wf["permissions"]["actions"] == "read", file
    model = _wf("scheduled-fetches.yml")
    assert model[True]["workflow_run"]["workflows"] == ["Agent fetches"]  # `on:` reads as True
    assert _wf("agent-fetches.yml")["name"] == "Agent fetches"


def test_every_dispatched_workflow_accepts_the_input_and_names_the_nightly_run():
    """GitHub refuses a dispatch carrying an input the workflow does not declare,
    and the guard can only tell the night's run by the suffix the run name adds."""
    ((key, value),) = dw.NIGHTLY_INPUTS.items()
    for file, entry in _sched().entries.items():
        if entry.dispatch_at is None:
            continue
        wf = _wf(file)
        assert key in (wf[True]["workflow_dispatch"] or {}).get("inputs", {}), file
        run_name = wf["run-name"]
        assert f"inputs.{key} == '{value}'" in run_name, file
        assert f"'{{0}}{dw.NIGHTLY_SUFFIX}'" in run_name, file
