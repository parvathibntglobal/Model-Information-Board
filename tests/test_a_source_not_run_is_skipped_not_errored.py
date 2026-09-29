"""A source this run does not use is `skipped`, never `error`.

Under #327 one errored stage turns the whole run to `error`, which is right for
a fault and wrong for a decision. X already reported a missing key or a terms
refusal as `skipped` with the reason; Reddit raised, `main` caught it as an
error, and every run without a Reddit key ended red. Measured 2026-09-28: all 5
E2R errors in the shared `fetch_log` since 2026-09-20 were `RAPIDAPI_KEY is not
set`.
"""

from __future__ import annotations

import json

import pytest

import collect.adapters.reddit as reddit
import scripts.fetch_model as fm


@pytest.fixture()
def prog(monkeypatch, tmp_path):
    monkeypatch.setattr(fm, "FETCH_DIR", tmp_path)
    monkeypatch.setenv("FETCH_QUIET", "1")
    p = fm.Progress("run-under-test", "mv_1")
    p._mirror = False
    return p


def _records(prog):
    return [json.loads(x) for x in prog.path.read_text(encoding="utf-8").splitlines() if x.strip()]


def _e2r(prog):
    return [r for r in _records(prog) if r.get("id") == "E2R" and r.get("status") != "running"]


class _Client:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def close(self):
        pass


def test_a_missing_key_is_skipped_with_its_reason(prog, monkeypatch):
    def no_key(**_):
        raise reddit.RedditConfigError("RAPIDAPI_KEY is not set, so no Reddit request can be made.")

    monkeypatch.setattr(reddit, "build_client", no_key)
    assert fm.harvest_reddit(None, prog, ["fable 5"], max_searches=3, max_threads=5) == 0
    (line,) = _e2r(prog)
    assert line["status"] == "skipped" and "RAPIDAPI_KEY is not set" in line["detail"]


def test_a_terms_refusal_is_skipped_with_its_reason(prog, monkeypatch):
    monkeypatch.setattr(reddit, "build_client", lambda **_: _Client())

    def refuse(source, **_):
        raise RuntimeError("Refusing to harvest: 1 source(s) failed the NFR-5 terms check (reddit)")

    monkeypatch.setattr(reddit, "harvester_for_source", refuse)
    assert fm.harvest_reddit(None, prog, ["fable 5"], max_searches=3, max_threads=5) == 0
    (line,) = _e2r(prog)
    assert line["status"] == "skipped" and "terms check" in line["detail"]


def test_the_run_stays_ok_when_only_reddit_was_not_run(prog, monkeypatch):
    """The #327 consequence, end to end: a harvest that succeeded elsewhere and
    skipped Reddit is an ok run, not an errored one."""
    def no_key(**_):
        raise reddit.RedditConfigError("RAPIDAPI_KEY is not set")

    monkeypatch.setattr(reddit, "build_client", no_key)
    prog.stage("E2", "Harvest", "ok", documents_inserted=3, http_errors=0)
    fm.harvest_reddit(None, prog, ["fable 5"], max_searches=3, max_threads=5)
    assert prog.done("ok", "fetch complete") == "ok"


def test_a_real_fault_still_errors():
    """The control: skipping is for a source not run, not for one that ran and
    broke. Transport errors are still counted and still decide the verdict."""
    assert fm._harvest_verdict(errors=3, produced=0) == "error"
