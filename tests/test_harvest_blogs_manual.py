"""Feeds harvested by hand are left out of the scheduled run (2026-11-05, #599).

Substack refuses robots.txt to GitHub's runners, so its newsletters are seated
with `harvest: manual` and read from a developer machine. The nightly run
passes --scheduled: such a feed is left out before any request, named, and not
counted as refused - the run did not try it. A run started by hand includes
it. An unknown `harvest:` value is refused rather than read as "scheduled".

No network and no database: dry runs, with observing and fetching faked, so
the tests are about which feeds are tried.
"""

from __future__ import annotations

import contextlib
import importlib.util
from pathlib import Path

from collect.adapters.blog.fetch import observe_use_basis

ROOT = Path(__file__).resolve().parents[1]
SCHEDULED = "blog:simonwillison.net"
BY_HAND = "blog:epochai.substack.com"
#: A Substack newsletter on its own domain, which the runner reads (#601 review).
OWN_DOMAIN = "blog:www.thealgorithmicbridge.com"


def _script(monkeypatch, feeds_and_marks):
    path = ROOT / "scripts" / "harvest_blogs.py"
    spec = importlib.util.spec_from_file_location("harvest_blogs", path)
    hb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hb)
    monkeypatch.setattr(hb, "build_client", lambda: contextlib.nullcontext(None))
    monkeypatch.setattr(hb, "RobotsGate", lambda *a, **k: None)
    contract = hb.load_sources()
    rows = {f["id"]: f for f in contract.feeds}
    feeds = []
    for feed_id, mark in feeds_and_marks:
        row = dict(rows[feed_id])
        row.pop("harvest", None)
        if mark is not None:
            row["harvest"] = mark
        feeds.append(row)
    monkeypatch.setattr(hb, "load_sources", lambda: type("C", (), {
        "feeds": feeds, "rulings": contract.rulings})())
    observed, reached = [], []

    def observe(feed, robots):
        observed.append(feed["id"])
        return {"endpoint_is_null": False, "robots_status": "rules", "robots_http": 200,
                "feed_path_allowed": True, **observe_use_basis()}

    def fetcher(feed, **kw):
        reached.append(feed["id"])
        raise hb.NotAFetchTargetError("test: no request is made")

    monkeypatch.setattr(hb, "observe_source", observe)
    monkeypatch.setattr(hb, "fetcher_for_source", fetcher)
    return hb, observed, reached


def test_the_scheduled_run_leaves_a_manual_feed_out_before_any_request(monkeypatch, capsys):
    hb, observed, reached = _script(monkeypatch, [(SCHEDULED, None), (BY_HAND, "manual")])
    code = hb.main(["--dry-run", "--scheduled"])
    out = capsys.readouterr().out
    assert code == 0, "a feed the run did not try is not a refusal"
    assert observed == [SCHEDULED], "not even robots.txt is asked for a manual feed"
    assert reached == [SCHEDULED]
    assert "1 feed(s) are harvested by hand and left to a manual run: " + BY_HAND in out
    assert "REFUSED" not in out


def test_a_run_started_by_hand_includes_the_manual_feed(monkeypatch, capsys):
    hb, observed, reached = _script(monkeypatch, [(SCHEDULED, None), (BY_HAND, "manual")])
    code = hb.main(["--dry-run"])
    assert code == 0
    assert observed == [SCHEDULED, BY_HAND]
    assert reached == [SCHEDULED, BY_HAND]


def test_limit_counts_feeds_tried_so_it_applies_after_the_manual_filter(monkeypatch, capsys):
    """`--scheduled --limit 2` tries two feeds, not two minus the manual ones among them."""
    hb, observed, reached = _script(
        monkeypatch, [(BY_HAND, "manual"), (SCHEDULED, None), (OWN_DOMAIN, None)])
    assert hb.main(["--dry-run", "--scheduled", "--limit", "2"]) == 0
    assert observed == [SCHEDULED, OWN_DOMAIN]


def test_an_unknown_harvest_value_is_refused_not_read_as_scheduled(monkeypatch, capsys):
    hb, observed, reached = _script(monkeypatch, [(SCHEDULED, None), (BY_HAND, "manaul")])
    code = hb.main(["--dry-run", "--scheduled"])
    err = capsys.readouterr().err
    assert code == 1
    assert observed == [] and reached == []
    assert "unknown `harvest:` value(s) manaul" in err


def test_every_substack_newsletter_is_harvested_by_hand_and_the_nightly_job_says_scheduled():
    hb_src = (ROOT / "scripts" / "harvest_blogs.py").read_text(encoding="utf-8")
    assert '"--scheduled"' in hb_src
    wf = (ROOT / ".github" / "workflows" / "scheduled-fetches.yml").read_text(encoding="utf-8")
    assert "python scripts/harvest_blogs.py --scheduled" in wf
    import yaml

    text = (ROOT / "contract" / "sources.yaml").read_text(encoding="utf-8")
    feeds = yaml.safe_load(text)["feeds"]
    substack = [f for f in feeds if f["id"].endswith(".substack.com")]
    assert substack, "the *.substack.com rows exist"
    assert all(f.get("harvest") == "manual" for f in substack), (
        "a *.substack.com feed on the scheduled run is refused robots.txt every night")
    # The converse (#601 review): Substack serves its own-domain newsletters to the
    # runner, so a manual row off *.substack.com would drop a feed the runner reads.
    manual = [f["id"] for f in feeds if f.get("harvest") == "manual"]
    assert sorted(manual) == sorted(f["id"] for f in substack)
    assert OWN_DOMAIN in {f["id"] for f in feeds} and OWN_DOMAIN not in manual
