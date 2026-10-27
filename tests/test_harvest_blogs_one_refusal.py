"""One feed that fails its terms check must not stop the others (2026-10-27).

The nightly run harvested none of 28 feeds because Substack refused robots.txt
to GitHub's runners for 3 newsletters: the terms check ran over every feed at
once, so one refusal refused them all. The check is unchanged - a refused feed
is still never harvested - but it runs per feed, names the feed it leaves out,
and the step still exits 1 so the run goes red and says which.

No network and no database: a dry run, with the observation and the fetcher
replaced, so the test is about the control flow alone.
"""

from __future__ import annotations

import contextlib
import importlib.util
from pathlib import Path

from collect.adapters.blog.fetch import observe_use_basis

ROOT = Path(__file__).resolve().parents[1]


def _script(monkeypatch):
    """The script, with no HTTP client at all: observing and fetching are faked
    by each test, so nothing here may depend on a machine's USER_AGENT (CI has
    none; a developer's .env does, which hid this on the first run)."""
    path = ROOT / "scripts" / "harvest_blogs.py"
    spec = importlib.util.spec_from_file_location("harvest_blogs", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "build_client", lambda: contextlib.nullcontext(None))
    monkeypatch.setattr(module, "RobotsGate", lambda *a, **k: None)
    return module


def test_a_refused_feed_is_named_and_left_out_and_the_rest_still_run(monkeypatch, capsys):
    hb = _script(monkeypatch)
    feeds = [f for f in hb.load_sources().feeds if f["id"] in
             ("blog:simonwillison.net", "blog:epochai.substack.com", "blog:hamel.dev")]
    assert len(feeds) == 3

    contract = hb.load_sources()
    monkeypatch.setattr(hb, "load_sources", lambda: type("C", (), {
        "feeds": feeds, "rulings": contract.rulings})())

    def observe(feed, robots):
        refused = feed["id"] == "blog:epochai.substack.com"
        return {"endpoint_is_null": False, "robots_status": "refused" if refused else "rules",
                "robots_http": 403 if refused else 200, "feed_path_allowed": not refused,
                **observe_use_basis()}

    monkeypatch.setattr(hb, "observe_source", observe)
    reached = []

    def fetcher(feed, **kw):
        reached.append(feed["id"])
        raise hb.NotAFetchTargetError("test: no request is made")

    monkeypatch.setattr(hb, "fetcher_for_source", fetcher)

    code = hb.main(["--dry-run"])
    out = capsys.readouterr()

    assert code == 1
    assert reached == ["blog:simonwillison.net", "blog:hamel.dev"]
    assert "blog:epochai.substack.com" in out.out and "REFUSED by its terms check" in out.out
    assert "1 feed(s) refused by their terms check" in out.err


def test_with_nothing_refused_the_exit_code_is_zero(monkeypatch, capsys):
    hb = _script(monkeypatch)
    feeds = [f for f in hb.load_sources().feeds if f["id"] == "blog:simonwillison.net"]
    contract = hb.load_sources()
    monkeypatch.setattr(hb, "load_sources", lambda: type("C", (), {
        "feeds": feeds, "rulings": contract.rulings})())
    monkeypatch.setattr(hb, "observe_source", lambda feed, robots: {
        "endpoint_is_null": False, "robots_status": "rules", "robots_http": 200,
        "feed_path_allowed": True, **observe_use_basis()})

    def fetcher(feed, **kw):
        raise hb.NotAFetchTargetError("test: no request is made")

    monkeypatch.setattr(hb, "fetcher_for_source", fetcher)
    assert hb.main(["--dry-run"]) == 0
