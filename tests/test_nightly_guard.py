"""The nightly guard (contract/nightly_guard.yaml, scripts/nightly_guard.py).

No network: GitHub is a fake. What these pin:
* the contract is read strictly (rule 12);
* "tonight" is ANCHORED: a `schedule` start counts from `window_opens_utc`, not a
  rolling span (#631 review: model ran in the afternoon, GitHub's model schedule
  fires 02:48); a `workflow_run` start counts from the finished run's creation;
* only a nightly start counts: a hand-started test holds nothing off;
* a `workflow_run` start follows only a finished run that did real nightly work
  (#631 review: a morning agent test must not start the model fetch);
* the model fetch's backup cron stands down while the agents' nightly run is going;
* a run the guard stood down is NOT real work, so it cannot hold off the next;
* a run still waiting in its guard counts only if it is older (no mutual stand-down);
* the workflows are wired: guard job first, main job gated on it, crons where
  anooj put them (2026-11-13), and the model fetch follows the agent fetch.
"""

from __future__ import annotations

import pathlib
from datetime import UTC, datetime

import pytest
import yaml

from scripts import nightly_guard as ng

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _at(day, hh, mm=0):
    return datetime(2026, 11, day, hh, mm, tzinfo=UTC)


def _entries():
    return ng.load_contract()


def _raw():
    return yaml.safe_load((ROOT / "contract" / "nightly_guard.yaml").read_text(encoding="utf-8"))


NOTHING_RUNS = lambda file: (False, f"no nightly run of {file} is going")  # noqa: E731
NEVER = lambda e, since: False  # noqa: E731


def _ok(created):
    return ng.Trigger(True, "the night's run ran", created)


# ── the contract ────────────────────────────────────────────────────────────


def test_the_contract_loads_and_names_the_four_workflows():
    e = _entries()
    assert set(e) == {
        "agent-fetches.yml",
        "scheduled-fetches.yml",
        "topic-harvest.yml",
        "evidence-feed.yml",
    }
    assert e["scheduled-fetches.yml"].waits_for == "agent-fetches.yml"
    assert "workflow_run" in e["scheduled-fetches.yml"].guard_events
    # The night begins at the agent cron (anooj, 2026-11-13), for the agents,
    # the model fetch that follows them, and the feed that follows that.
    for f in ("agent-fetches.yml", "scheduled-fetches.yml", "evidence-feed.yml"):
        assert e[f].window_opens == (4, 0), f


@pytest.mark.parametrize(
    "mutate, says",
    [
        (lambda r: r["workflows"]["agent-fetches.yml"].pop("counts_events"), "counts_events"),
        (lambda r: r["workflows"]["agent-fetches.yml"].pop("window_opens_utc"), "window_opens"),
        (lambda r: r["workflows"]["agent-fetches.yml"].pop("waits_for"), "waits_for"),
        (lambda r: r["workflows"]["agent-fetches.yml"].update(window_opens_utc="4am"), "HH:MM"),
        (lambda r: r["workflows"]["agent-fetches.yml"].update(window_opens_utc=4), "HH:MM"),
        (lambda r: r["workflows"]["agent-fetches.yml"].update(window_opens_utc="24:00"), "HH:MM"),
        (
            lambda r: r["workflows"]["agent-fetches.yml"].update(guard_events=["push"]),
            "guard_events",
        ),
        # A hand start is never guarded: a person asked for it.
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
        (
            lambda r: r["workflows"]["scheduled-fetches.yml"].update(waits_for="ci.yml"),
            "waits_for",
        ),
        (
            lambda r: r["workflows"]["scheduled-fetches.yml"].update(
                waits_for="scheduled-fetches.yml"
            ),
            "waits_for",
        ),
    ],
)
def test_a_missing_or_wrong_setting_is_refused(mutate, says):
    raw = _raw()
    mutate(raw)
    with pytest.raises(ng.GuardConfigError, match=says):
        ng.parse_contract(raw)


# ── tonight ─────────────────────────────────────────────────────────────────


def test_the_window_is_anchored_not_rolling():
    """#631 review, Parvathi: GitHub's model schedule has arrived as late as
    02:48. After an afternoon model fetch, a rolling 12 hours lets that second
    run through, after UTC midnight, on the next day's budget. Anchored at the
    agent cron, it stands down."""
    model = _entries()["scheduled-fetches.yml"]
    real_runs = [_at(14, 16, 30)]  # the model fetch the agents' finish started

    def did_real_work(e, since):
        return any(t >= since for t in real_runs)

    run, why = ng.guard_decision(
        model, "schedule", _at(15, 2, 48), did_real_work, still_running=NOTHING_RUNS
    )
    assert run is False, why
    assert "2026-11-14 04:00Z" in why

    # ... and the NEXT night's agent-started model fetch still runs.
    run, why = ng.guard_decision(
        model,
        "workflow_run",
        _at(15, 16, 35),
        did_real_work,
        trigger=_ok(_at(15, 10, 30)),
        still_running=NOTHING_RUNS,
    )
    assert run is True, why


def test_a_chained_start_counts_from_the_finished_run_not_the_anchor():
    """A backup model fetch fired near 02:00 ends after 04:00, and its feed ran
    at 08:00 - inside the next night's window. Counted from the anchor, that feed
    would hold off the next night's feed; counted from the model run that
    finished, it does not."""
    feed = _entries()["evidence-feed.yml"]
    feed_ran = [_at(15, 8, 0)]

    def did_real_work(e, since):
        return any(t >= since for t in feed_ran)

    run, why = ng.guard_decision(
        feed,
        "workflow_run",
        _at(15, 22, 30),
        did_real_work,
        trigger=_ok(_at(15, 16, 30)),  # tonight's model fetch
    )
    assert run is True, why
    # A second feed for the SAME model run is the duplicate, and stands down.
    run, _ = ng.guard_decision(
        feed, "workflow_run", _at(15, 9, 0), did_real_work, trigger=_ok(_at(15, 2, 0))
    )
    assert run is False


def test_the_model_backup_stands_down_while_the_agents_run():
    """The 16:00 backup fires 3-10 hours late; if the agents are still going, it
    stands down and their finish starts the model fetch."""
    model = _entries()["scheduled-fetches.yml"]
    busy = lambda file: (True, f"{file} run 9 is still going")  # noqa: E731
    run, why = ng.guard_decision(model, "schedule", _at(14, 19, 0), NEVER, still_running=busy)
    assert run is False and "agent-fetches.yml" in why
    # Agents not running and no model fetch tonight: the backup runs.
    run, _ = ng.guard_decision(model, "schedule", _at(14, 19, 0), NEVER, still_running=NOTHING_RUNS)
    assert run is True


def test_a_workflow_that_waits_for_another_needs_the_check():
    model = _entries()["scheduled-fetches.yml"]
    with pytest.raises(ValueError, match="waits for"):
        ng.guard_decision(model, "schedule", _at(14, 19), NEVER)


def test_a_guarded_start_stands_down_after_real_work_and_a_hand_start_runs():
    e = _entries()["scheduled-fetches.yml"]
    ran = lambda e, since: True  # noqa: E731
    now = _at(14, 19)
    assert ng.guard_decision(e, "schedule", now, ran, still_running=NOTHING_RUNS)[0] is False
    assert (
        ng.guard_decision(
            e, "workflow_run", now, ran, trigger=_ok(_at(14, 10)), still_running=NOTHING_RUNS
        )[0]
        is False
    )
    assert ng.guard_decision(e, "workflow_dispatch", now, ran)[0] is True


def test_a_guarded_workflow_run_without_the_finished_runs_verdict_is_refused():
    e = _entries()["scheduled-fetches.yml"]
    with pytest.raises(ValueError, match="verdict"):
        ng.guard_decision(e, "workflow_run", _at(14, 19), NEVER, still_running=NOTHING_RUNS)


# ── which starts count ──────────────────────────────────────────────────────


def test_only_a_nightly_hand_start_counts():
    agent = _entries()["agent-fetches.yml"]
    assert ng.counted_start(
        agent, {"event": "workflow_dispatch", "display_title": "Agent fetches (nightly)"}
    )
    assert not ng.counted_start(
        agent, {"event": "workflow_dispatch", "display_title": "Agent fetches"}
    )
    assert ng.counted_start(agent, {"event": "schedule", "display_title": "Agent fetches"})
    feed = _entries()["evidence-feed.yml"]
    assert not ng.counted_start(
        feed, {"event": "workflow_dispatch", "display_title": "Evidence feed (nightly)"}
    )


# ── the run that finished, for a workflow_run start ─────────────────────────


def _finished(event, title, run_id=7, path=".github/workflows/agent-fetches.yml"):
    return {
        "id": run_id,
        "event": event,
        "display_title": title,
        "path": path,
        "created_at": "2026-11-14T10:30:00Z",
    }


def _job(conclusion):
    return lambda run_id, name: {"name": name, "status": "completed", "conclusion": conclusion}


def test_a_morning_agent_test_does_not_start_the_model_fetch():
    """#631 review, Parvathi: the 2026-11-12 05:20Z agent run was a test started
    by hand with `max_models`; its finish must not start the full model fetch."""
    e = _entries()
    t = ng.trigger_verdict(e, _finished("workflow_dispatch", "Agent fetches"), _job("success"))
    assert t.ok is False and "not a nightly start" in t.why
    run, _ = ng.guard_decision(
        e["scheduled-fetches.yml"],
        "workflow_run",
        _at(12, 6, 30),
        NEVER,
        trigger=t,
        still_running=NOTHING_RUNS,
    )
    assert run is False


def test_the_nightly_agent_run_starts_the_model_fetch():
    e = _entries()
    for finished in (
        _finished("workflow_dispatch", "Agent fetches (nightly)"),
        _finished("schedule", "Agent fetches"),
    ):
        t = ng.trigger_verdict(e, finished, _job("success"))
        assert t.ok is True and t.created == _at(14, 10, 30)
        # It finished badly: the model fetch still follows. A failed agent run
        # did real work and is not a reason to skip the models.
        assert ng.trigger_verdict(e, finished, _job("failure")).ok is True


def test_a_schedule_run_that_stood_down_starts_nothing():
    """A late agent `schedule` that stood down completes within a minute;
    following it would start the model fetch while the agents still run."""
    e = _entries()
    stood_down = _finished("schedule", "Agent fetches")
    t = ng.trigger_verdict(e, stood_down, _job("skipped"))
    assert t.ok is False and "stood down" in t.why
    assert ng.trigger_verdict(e, stood_down, lambda run_id, name: None).ok is False


def test_the_feed_follows_only_a_model_fetch_that_ran():
    e = _entries()
    path = ".github/workflows/scheduled-fetches.yml"
    model_run = _finished("workflow_run", "Scheduled fetches", path=path)
    assert ng.trigger_verdict(e, model_run, _job("success")).ok is True
    assert ng.trigger_verdict(e, model_run, _job("skipped")).ok is False
    model_test = _finished("workflow_dispatch", "Scheduled fetches", path=path)
    assert ng.trigger_verdict(e, model_test, _job("success")).ok is False


def test_a_finished_run_from_an_unlisted_workflow_is_refused():
    with pytest.raises(SystemExit, match="refusing to guess"):
        ng.trigger_verdict(
            _entries(),
            _finished("schedule", "X", path=".github/workflows/ci.yml"),
            _job("success"),
        )


# ── against GitHub's run list ───────────────────────────────────────────────


class _FakeGH:
    """Runs of one workflow, each with its run status and its main job."""

    repo = "o/r"

    def __init__(self, runs):
        # [(id, event, job_status, job_conclusion, display_title, run_status)];
        # job_status None = no main job yet
        defaults = ("Scheduled fetches", "completed")
        self.runs = [r + defaults[len(r) - 4 :] for r in runs]

    def get(self, path):
        if "/jobs" in path:
            rid = int(path.split("/runs/")[1].split("/")[0])
            st, concl = next((r[2], r[3]) for r in self.runs if r[0] == rid)
            return {
                "jobs": [] if st is None else [{"name": "fetch", "status": st, "conclusion": concl}]
            }
        return {
            "workflow_runs": [
                {"id": i, "event": ev, "display_title": t, "status": s}
                for i, ev, _, _, t, s in self.runs
            ]
        }


ENTRY = ng.Entry(
    "scheduled-fetches.yml",
    "fetch",
    (4, 0),
    None,
    frozenset({"schedule", "workflow_run"}),
    frozenset({"schedule", "workflow_run", "nightly_dispatch"}),
)
SINCE = _at(14, 4)


def test_a_stood_down_run_is_not_real_work():
    gh = _FakeGH([(10, "schedule", "completed", "skipped")])
    assert ng.real_work_checker(gh, this_run_id=20)(ENTRY, SINCE) is False


def test_a_finished_or_running_main_job_is_real_work():
    for conclusion in ("success", "failure"):
        gh = _FakeGH([(10, "workflow_run", "completed", conclusion)])
        assert ng.real_work_checker(gh, this_run_id=20)(ENTRY, SINCE)
    gh = _FakeGH([(30, "schedule", "in_progress", None)])
    assert ng.real_work_checker(gh, this_run_id=20)(ENTRY, SINCE)


def test_a_hand_started_test_is_not_real_work_and_a_nightly_one_is():
    test = [(10, "workflow_dispatch", "completed", "success", "Scheduled fetches")]
    assert ng.real_work_checker(_FakeGH(test), this_run_id=20)(ENTRY, SINCE) is False
    nightly = [(10, "workflow_dispatch", "completed", "success", "Scheduled fetches (nightly)")]
    assert ng.real_work_checker(_FakeGH(nightly), this_run_id=20)(ENTRY, SINCE) is True


def test_a_run_still_in_its_guard_counts_only_if_older():
    """Two runs starting together must not both stand down."""
    waiting = [(10, "schedule", None, None)]
    assert ng.real_work_checker(_FakeGH(waiting), this_run_id=20)(ENTRY, SINCE) is True
    assert ng.real_work_checker(_FakeGH(waiting), this_run_id=5)(ENTRY, SINCE) is False


def test_this_run_and_uncounted_events_are_ignored():
    gh = _FakeGH([(20, "schedule", "completed", "success")])
    assert ng.real_work_checker(gh, this_run_id=20)(ENTRY, SINCE) is False
    weekly_only = ng.Entry(
        "evidence-feed.yml",
        "fetch",
        (4, 0),
        None,
        frozenset({"workflow_run"}),
        frozenset({"workflow_run"}),
    )
    gh = _FakeGH([(10, "schedule", "completed", "success")])
    assert ng.real_work_checker(gh, this_run_id=20)(weekly_only, SINCE) is False


def test_only_a_going_nightly_agent_run_holds_the_model_backup():
    e = _entries()
    going = ("schedule", "in_progress", None, "Agent fetches", "in_progress")
    check = ng.running_checker(_FakeGH([(5, *going)]), e)
    assert check("agent-fetches.yml")[0] is True
    # A hand-started test that is going does not hold the models off.
    test = ("workflow_dispatch", "in_progress", None, "Agent fetches", "in_progress")
    assert ng.running_checker(_FakeGH([(5, *test)]), e)("agent-fetches.yml")[0] is False
    # Nor does a finished run, or a run whose guard already stood it down.
    done = ("schedule", "completed", "success", "Agent fetches", "completed")
    assert ng.running_checker(_FakeGH([(5, *done)]), e)("agent-fetches.yml")[0] is False
    closing = ("schedule", "completed", "skipped", "Agent fetches", "in_progress")
    assert ng.running_checker(_FakeGH([(5, *closing)]), e)("agent-fetches.yml")[0] is False


# ── the workflows ───────────────────────────────────────────────────────────


def _wf(file):
    return yaml.safe_load((ROOT / ".github" / "workflows" / file).read_text(encoding="utf-8"))


def test_the_four_workflows_are_wired_to_the_guard():
    for file, entry in _entries().items():
        wf = _wf(file)
        jobs = wf["jobs"]
        assert list(jobs)[0] == "guard", file
        assert f"scripts/nightly_guard.py --workflow {file}" in jobs["guard"]["steps"][-1]["run"]
        main = jobs[entry.job]
        assert main["needs"] == "guard", file
        assert main["if"] == "needs.guard.outputs.run == 'true'", file
        assert wf["permissions"]["actions"] == "read", file
    model = _wf("scheduled-fetches.yml")
    assert model[True]["workflow_run"]["workflows"] == ["Agent fetches"]  # `on:` reads as True
    assert _wf("agent-fetches.yml")["name"] == "Agent fetches"
    assert _wf("scheduled-fetches.yml")["name"] == "Scheduled fetches"


def test_the_crons_are_where_anooj_put_them():
    """2026-11-13, #631: no timer outside GitHub; the agent cron moves to 04:00
    so the delayed run lands near 10:00-11:00 and the night ends inside one UTC
    day. The model cron is a backup after the agents' latest start seen."""
    assert _wf("agent-fetches.yml")[True]["schedule"] == [{"cron": "0 4 * * *"}]
    assert _wf("scheduled-fetches.yml")[True]["schedule"] == [{"cron": "0 16 * * *"}]


def test_every_workflow_counting_a_nightly_hand_start_can_be_given_one():
    """The guard can only tell a stand-in for the night by the run name, and
    GitHub refuses a start carrying an input the workflow does not declare."""
    key, value = ng.NIGHTLY_INPUT
    for file, entry in _entries().items():
        if "nightly_dispatch" not in entry.counts_events:
            continue
        wf = _wf(file)
        assert key in (wf[True]["workflow_dispatch"] or {}).get("inputs", {}), file
        run_name = wf["run-name"]
        assert f"inputs.{key} == '{value}'" in run_name, file
        assert f"'{{0}}{ng.NIGHTLY_SUFFIX}'" in run_name, file
