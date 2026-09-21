"""A run whose stage errored may not end `ok` (#327).

THE DEFECT WAS ONE MISSING CONSULTATION, NOT A MISSING HANDLER. Every stage in
`main` is wrapped in its own `try/except` deliberately — a Reddit quota error
must not throw away a GitHub harvest that already succeeded — and that isolation
is right and stays. What was absent is the last step: nothing asked whether any
of those handlers had fired before writing `end · ok · fetch complete`.

MEASURED ON THREE POPULATIONS, none of them hypothetical:

    local run logs, machine A      10 of 16 runs ended `ok` with a stage errored
    local run logs, machine B      11 of 23
    the shared `fetch_log` table   12 of 50

The worst carried **eleven** errored stages and still said `fetch complete`.

AND THE TWO THAT PROMPTED THE FIX. On 2026-09-21 two fetches were run to check
whether a metric change had taken effect. Both reported `fetch complete`:

    mv_0510680735d3c79a-…   E5 error: provider 504, "Upstream idle timeout exceeded"
    mv_568e0eb3a95b5113-…   E5 error: provider 502, "upstream model did not
                            return a valid tool call for the requested tool_choice"

E5 raising means E5c, E5b, E6 and E7 never ran, and E7 is what recomputes cells.
So both runs collected documents, extracted nothing, reached no page, and were
indistinguishable at the summary line from runs that had worked. The question
they were run to answer could not be answered, and the log said they were fine.

These are unit tests over `Progress`: no database, no network, no fetch.
"""

from __future__ import annotations

import json

import pytest

import scripts.fetch_model as fm


@pytest.fixture()
def prog(monkeypatch, tmp_path):
    """A `Progress` writing to a temp dir, with the shared-table mirror off.

    The mirror is best-effort and never raises, but it would still try to reach
    `DATABASE_URL` if one happens to be set in the environment running the
    suite. A unit test over the end record must not depend on whether the
    person running it has a database configured.
    """
    monkeypatch.setattr(fm, "FETCH_DIR", tmp_path)
    p = fm.Progress("run-under-test", "mv_1")
    p._mirror = False
    return p


def _end(prog) -> dict:
    """The run's end record, read back off disk rather than from the object."""
    records = [
        json.loads(line)
        for line in prog.path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    ends = [r for r in records if r.get("kind") == "end"]
    assert len(ends) == 1, f"expected exactly one end record, got {len(ends)}"
    return ends[0]


class TestTheEndRecordIsDerivedNotAsserted:
    def test_the_runs_of_2026_09_21_would_now_report_error(self, prog):
        # The sequence exactly: the harvest arms succeeded, E5 lost the
        # provider mid-stream, and `main` fell through to done("ok").
        prog.stage("E1", "Registry", "ok")
        prog.stage("E2", "Harvest", "ok")
        prog.stage("E4", "Triage", "ok")
        prog.stage("E5", "Extract", "error",
                   detail="the provider reported an error mid-stream: 504")

        assert prog.done("ok", "fetch complete") == "error"
        assert _end(prog)["status"] == "error"

    def test_it_names_which_stages_rather_than_only_that_one_did(self, prog):
        # Rule 4: a caused absence has to say it was caused. "error" alone
        # sends the reader back to the log to learn what the log already knew.
        prog.stage("E2R", "Harvest · reddit", "error", detail="quota")
        prog.stage("E5", "Extract", "error", detail="504")
        prog.done("ok", "fetch complete")

        detail = _end(prog)["detail"]
        assert "E2R" in detail and "E5" in detail
        assert "2 stage(s) errored" in detail
        # And the sentence it replaced must be gone: that is the whole defect.
        assert "fetch complete" not in detail

    def test_a_stage_that_errored_twice_is_named_once(self, prog):
        # `_Db.live` can report the same stage id more than once across a
        # reconnect. A count that double-counts is a different wrong number.
        prog.stage("E5", "Extract", "error", detail="first")
        prog.stage("E5", "Extract", "error", detail="second")
        prog.done("ok", "fetch complete")

        assert "1 stage(s) errored" in _end(prog)["detail"]

    def test_a_clean_run_still_says_ok(self, prog):
        # The guard must not cry wolf, or it gets read past like the old one.
        prog.stage("E1", "Registry", "ok")
        prog.stage("E2", "Harvest", "ok")

        assert prog.done("ok", "fetch complete") == "ok"
        end = _end(prog)
        assert end["status"] == "ok" and end["detail"] == "fetch complete"

    def test_a_skipped_stage_is_not_an_error(self, prog):
        # E2B skips on every single-model fetch by design — "blogs are
        # feed-based, no per-model search". A run of them is a normal run.
        prog.stage("E2B", "Harvest · blogs", "skipped", detail="not run for one model")
        prog.stage("E2A", "Harvest · arxiv", "ok")

        assert prog.done("ok", "nothing to harvest") == "ok"


class TestItOnlyEverDowngradesOk:
    def test_a_deliberate_stop_stays_stopped(self, prog):
        # A halt somebody asked for is not a failure, and #327 is not a licence
        # to call it one. `RunStopped` derives from `BaseException` precisely so
        # this distinction survives, and that reasoning is unchanged here.
        prog.stage("E5", "Extract", "error", detail="504")
        prog.stage("STOP", "Stopped by request", "skipped")

        assert prog.done("stopped", "stopped by request") == "stopped"
        assert _end(prog)["detail"] == "stopped by request"

    def test_an_explicit_error_keeps_its_own_detail(self, prog):
        # The caller's traceback line says which exception escaped `main`.
        # A list of stage ids is strictly less specific, so it must not
        # overwrite it.
        prog.stage("E3", "Assemble", "error", detail="the connection is lost")

        prog.done("error", "psycopg.OperationalError: the connection is lost")
        assert _end(prog)["detail"] == "psycopg.OperationalError: the connection is lost"


class TestTheExitCodeAgreesWithTheLog:
    """A run that reports `error` to the log and 0 to its caller has only moved
    the defect: the nightly chain reads the exit code, not the JSONL."""

    def test_done_returns_the_status_it_wrote(self, prog):
        prog.stage("E5", "Extract", "error", detail="504")
        # `main` branches on this return value, so it has to be the written
        # status and not the requested one.
        assert prog.done("ok", "fetch complete") == "error"

    def test_main_returns_nonzero_when_a_stage_errored(self):
        # Structural rather than behavioural: running `main` needs a database
        # and a network. What is asserted is that the success path's exit code
        # is derived from `done()` instead of being the literal 0 it was.
        import inspect

        source = inspect.getsource(fm.main)
        assert 'prog.done("ok", "fetch complete")' in source
        assert "return 0 if prog.done" in source, (
            "the success path must derive its exit code from the end record; "
            "a bare `return 0` under it is the same defect in the other channel"
        )
