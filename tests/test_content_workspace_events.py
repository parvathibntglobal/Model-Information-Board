"""Calendar items joined to the board's evidence (topic selection B, 2026-11-19).

Every launch, price move and retirement shown carries the people who reported on
its models; one nobody reported on stays listed and SAYS it is a calendar item
only (rule 4, rule 8); a read that fails says so rather than "nobody" (rule 6).
"""

from __future__ import annotations

from datetime import UTC, datetime

from judge.content_workspace import recommend, settings

S = settings.load()
NOW = datetime(2026, 11, 19, 12, tzinfo=UTC)


def _update(key, kind, day, models):
    return {"key": key, "kind": kind, "date": day, "models": models, "label": kind,
            "why": None, "styles": [{"headline": f"{key} headline", "detail": "d"}]}


def _readers(updates, people=None, unknown=(), fail_people=False):
    def ppl(conn, model_id, start, end):
        if fail_people:
            raise RuntimeError("connection lost")
        if model_id in unknown:
            return {"people": 0, "posts": 0, "for": 0, "against": 0, "neutral": 0, "known": False}
        n = (people or {}).get(model_id, {})
        # "since the event" reads a later start: half the people, to tell the two apart
        scale = 1 if start.isoformat() < "2026-11-01" else 0.5
        return {"people": int(n.get("people", 0) * scale), "posts": n.get("people", 0),
                "for": n.get("for", 0), "against": n.get("against", 0),
                "neutral": n.get("neutral", 0), "known": True}

    return {"updates": lambda conn, days, now: list(updates),
            "people": ppl,
            "model": lambda conn, m: {"id": m, "name": m.upper(), "release_date": None}}


def _one(kind_key, rows, **kw):
    out = recommend.suggestions(object(), {"key": "x", "topic_kinds": [kind_key]}, S, now=NOW,
                                readers=_readers(rows, **kw))
    return out["kinds"][0]


def test_a_price_move_carries_the_people_who_reported():
    block = _one("price_change", [_update("p1", "price_cut", "2026-11-10", ["a/m1"])],
                 people={"a/m1": {"people": 12, "for": 8, "against": 3, "neutral": 2}})
    item = block["items"][0]
    line = item["evidence"][-1]
    assert "12 people in the 30 days to 2026-11-19" in line
    assert "8 for, 3 against, 2 neutral" in line and "6 of them since 2026-11-10" in line
    assert item["board_people"] == 12 and "no_reports" not in item


def test_an_event_nobody_reported_on_is_listed_and_labelled():
    item = _one("price_change", [_update("p1", "price_cut", "2026-11-10", ["a/m1"])])["items"][0]
    assert "nobody reported on it" in item["evidence"][-1]
    assert "calendar item only" in item["no_reports"]


def test_a_launch_with_no_reports_yet_says_so_in_launch_terms():
    item = _one("release_reaction", [_update("l1", "launch", "2026-11-18", ["a/m1"])])["items"][0]
    assert item["no_reports"] == "No reports on the board yet since the launch on 2026-11-18."


def test_an_unreadable_read_is_not_nobody():
    item = _one("price_change", [_update("p1", "price_cut", "2026-11-10", ["a/m1"])],
                fail_people=True)["items"][0]
    assert "could not be read" in item["evidence"][-1]
    assert "no_reports" not in item


def test_a_model_missing_from_the_registry_is_named_as_such():
    item = _one("price_change", [_update("p1", "price_cut", "2026-11-10", ["z/ghost"])],
                unknown=("z/ghost",))["items"][0]
    assert "not in the board's registry" in item["evidence"][-1]


def test_retirements_are_a_topic_kind_with_their_evidence():
    block = _one("retirement", [_update("r1", "retiring", "2026-11-25", ["a/m3"]),
                                _update("l1", "launch", "2026-11-18", ["a/m1"])],
                 people={"a/m3": {"people": 4, "for": 1, "against": 3, "neutral": 0}})
    assert [i["id"] for i in block["items"]] == ["update:r1"]
    line = block["items"][0]["evidence"][-1]
    # an upcoming retirement has no "since": the event has not happened
    assert "4 people" in line and "since" not in line
    assert block["recipe"]["look"]["key"] == "data_card"
