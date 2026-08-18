"""The chain's visibility properties, which are the reason it exists.

Under cron nobody reads a traceback. These tests are all about the difference
between "did not run" and "ran and found nothing", because nine silent-failure
defects in one fortnight were each a version of the second wearing the first's
clothes.
"""

from __future__ import annotations

import json

import pytest

from collect.ops import alerts
from collect.ops.chain import (
    ERROR,
    OK,
    REFUSED,
    Journal,
    Stage,
    StageResult,
    default_stages,
    run_chain,
)
from collect.ops.preflight import PreflightRefused, preflight


def _ok(_context):
    return StageResult(OK, counts={"rows": 1})


def _boom(_context):
    raise RuntimeError("the platform went away")


# ── the journal, written before the work ──────────────────────────────────


def test_a_stage_is_recorded_before_it_runs(tmp_path):
    """A killed process must leave "started, never finished" rather than nothing.

    A record written only on success describes the runs that needed it least.
    """
    journal = Journal(tmp_path / "journal.jsonl")
    run_chain([Stage("work", run=_ok)], {}, journal)

    events = [line["event"] for line in journal.lines]
    assert events.index("stage-started") < events.index("stage-finished")


def test_the_journal_survives_a_stage_that_raises(tmp_path):
    """The chain records; it does not judge. An exception is an outcome."""
    path = tmp_path / "journal.jsonl"
    run = run_chain([Stage("work", run=_boom)], {}, Journal(path))

    assert run.results["work"].outcome == ERROR
    assert "the platform went away" in run.results["work"].detail
    written = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [e["event"] for e in written].count("stage-started") == 1
    assert any(e.get("outcome") == ERROR for e in written)


def test_the_journal_is_flushed_line_by_line(tmp_path):
    """Buffered, it would describe every run except the one that disappeared."""
    path = tmp_path / "journal.jsonl"
    journal = Journal(path)

    def peek(_context):
        # Mid-run, the file must already name this stage.
        assert "peek" in path.read_text(encoding="utf-8")
        return StageResult(OK)

    run_chain([Stage("peek", run=peek)], {}, journal)


# ── a hole is a refusal, and it names what it starves ─────────────────────


def test_an_unbuilt_stage_refuses_rather_than_passing_quietly():
    run = run_chain([Stage("flatten", run=None, starves="thread_context")])

    result = run.results["flatten"]
    assert result.outcome == REFUSED
    assert "not built" in result.detail
    assert result.starves == "thread_context"
    assert result.counts == {}, "a stage that never looked reports no counts"


def test_every_unbuilt_stage_in_the_real_chain_says_what_it_starves():
    """A refusal without a consequence is a skip with better manners."""
    for stage in default_stages():
        if stage.run is None:
            assert stage.starves, f"{stage.name} refuses without saying what it costs"
            assert len(stage.starves) > 20, f"{stage.name}: too vague to act on"


def test_a_blocked_stage_reports_no_counts_rather_than_zero():
    """Zero is a measurement. This stage did not make one."""
    run = run_chain([
        Stage("upstream", run=_boom),
        Stage("downstream", run=_ok, needs=("upstream",), starves="nothing downstream"),
    ])

    downstream = run.results["downstream"]
    assert downstream.outcome == REFUSED
    assert downstream.counts == {}
    assert "upstream" in downstream.detail


def test_independent_stages_are_not_stopped_by_each_other():
    """Losing the blog sweep because GitHub was rate-limited is the expensive one.

    The publication gate needs two platforms, and the three sweeps share only
    the registry they both read.
    """
    run = run_chain([
        Stage("sweep-a", run=_boom),
        Stage("sweep-b", run=_ok),
        Stage("sweep-c", run=_ok),
    ])

    assert run.results["sweep-a"].outcome == ERROR
    assert run.results["sweep-b"].outcome == OK
    assert run.results["sweep-c"].outcome == OK


def test_the_summary_leads_with_how_much_did_not_run():
    run = run_chain(default_stages(), {"environment": "development"})
    head = run.summary().splitlines()[0]
    assert "refused" in head and "errored" in head
    assert run.refused, "tonight most of the chain refuses, and it should say so"


# ── preflight ─────────────────────────────────────────────────────────────


def test_an_absent_input_is_skipped_and_named_never_counted_as_a_pass():
    report = preflight(None, environment="production", policy=None, sources=None)

    assert report.passed == []
    assert len(report.skipped) == 3
    assert all(":" in reason for reason in report.skipped), "each says which check"
    assert report.ok, "nothing failed — but nothing was checked either"


def test_development_skips_the_checks_rather_than_failing_them():
    from collect.registry.policy import DEFAULT_POLICY

    report = preflight(None, environment="development", policy=DEFAULT_POLICY)
    assert report.ok


def test_defaults_outside_development_refuse_with_every_reason_at_once():
    """One reason per run turns a five-minute fix into five runs."""
    from collect.registry.policy import DEFAULT_POLICY

    with pytest.raises(PreflightRefused) as raised:
        preflight(None, environment="production", policy=DEFAULT_POLICY)
    assert "contract-backed" in str(raised.value)


def test_the_real_policy_is_contract_backed_today():
    """`contract/registry.yaml` exists, so this passes rather than refusing.

    Recorded as a test because the first version of the ops report claimed the
    opposite, having read `policy.py`'s docstring instead of the directory.
    """
    from collect.registry.policy import load_registry_policy

    report = preflight(None, environment="production", policy=load_registry_policy())
    assert "contract-backed" in report.passed


# ── the alerts, and the third state ───────────────────────────────────────


def test_every_alert_is_honest_about_having_no_input_tonight():
    verdicts = alerts.evaluate()
    assert len(verdicts) == 5
    computable = [a for a in verdicts if a.state == alerts.FIRED]
    assert not computable
    assert [a.state for a in verdicts].count(alerts.CANNOT_COMPUTE) == 2
    assert [a.state for a in verdicts].count(alerts.NOT_OURS) == 2


def test_the_yield_alert_says_why_it_cannot_compute_rather_than_reporting_quiet():
    alert = alerts.yield_drop(runs=[])
    assert alert.state == alerts.CANNOT_COMPUTE
    assert "harvest_run" in alert.detail
    assert alert.figures == {"runs": 0}


def test_the_yield_alert_will_not_fire_on_a_vocabulary_change():
    """The three runs on record are 0/149, 5/636 and 0/1,678 across three
    vocabularies. Comparing them measures our own edits, which would be the
    tenth instance of the defect class this layer exists to detect.

    Encoded in the code and not only in a document: the baseline is per
    `pipeline_version`, and the alert refuses to compute without two nights of
    one.
    """
    from collect.ops.alerts import yield_drop

    assert "pipeline_version" in yield_drop.__doc__
    assert yield_drop(runs=[{"items_kept": 5}], baseline_nights=1).state == (
        alerts.CANNOT_COMPUTE
    )


def test_the_survival_alert_counts_down_in_public():
    alert = alerts.triage_survival(nights=3, kept=10, candidates=100)
    assert alert.state == alerts.CANNOT_COMPUTE
    assert "3 of 14" in alert.detail
    assert alert.figures["candidates"] == 100, "rule 7: the denominator travels"


def test_the_two_judge_alerts_are_raised_and_not_stubbed():
    """A stub is a producer nobody wrote, reporting quiet forever."""
    for alert in (alerts.extraction_errors(), alerts.quote_verification()):
        assert alert.owner == "judge/"
        assert alert.state == alerts.NOT_OURS
        assert "stub" in alert.detail


def test_a_registry_event_fires_and_names_what_changed():
    alert = alerts.registry_change([{"type": "price-change"}, {"type": "new-model"}])
    assert alert.state == alerts.FIRED
    assert alert.figures == {"events": 2, "price-change": 1, "new-model": 1}
