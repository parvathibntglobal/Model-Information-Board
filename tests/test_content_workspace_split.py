"""A model's reports split by capability and job (topic selection A).

The labels use the board's own E7 thresholds, so they agree with what "mixed"
means on a model page; the list is ordered by people and says so; silence is
said, never shown as a split; and no count is summed where it would double up.
"""

from __future__ import annotations

import copy
from datetime import date

import pytest

from judge.content_workspace import recommend, settings


@pytest.mark.parametrize("pos,neg,label", [
    (25, 3, "mostly for"),            # Fable 5.2 code generation, 19 Nov
    (5, 8, "mixed reports"),          # over-refusal: majority 62% < 70%
    (2, 8, "mostly against"),         # token efficiency: 80%
    (1, 1, "too few to say"),         # under 3 people taking a side
    (0, 0, "discussed, no side taken"),
])
def test_labels_follow_the_boards_thresholds(pos, neg, label):
    assert recommend.split_label(pos, neg) == label


def _readers(rows, people_by_name, people=0, posts=0, themes=None):
    def model(_conn, model_id):
        if model_id != "a/m1":
            return None
        return {"id": "a/m1", "name": "A: M1", "release_date": "2026-11-01", "price": "-"}

    def split(_conn, _mv, _start, _end, _sections):
        return {"rows": rows, "people_by_name": people_by_name, "people": people, "posts": posts}

    def theme_rows(_conn, _mv, _start, _end, _sections, wanted):
        zero = {"people": 0, "for": 0, "against": 0, "neutral": 0}
        return {t: dict((themes or {}).get(t, zero)) for t in wanted}

    return {"model": model, "split": split, "themes": theme_rows}


@pytest.fixture()
def s():
    out = copy.deepcopy(settings.load())
    out["capability_split"]["top"] = 2
    return out


def _row(key, name, polarity, people, section="capability"):
    return {"key": key, "name": name, "section": section, "polarity": polarity,
            "people": people, "posts": people}


def test_ordered_by_people_with_the_rest_counted(s):
    rows = [_row("capability:a", "Alpha", "positive", 2),
            _row("capability:b", "Beta", "positive", 9),
            _row("capability:b", "Beta", "negative", 4),
            _row("capability:c", "Gamma", "negative", 5)]
    got = recommend.capability_split(None, "a/m1", s, today=date(2026, 11, 19),
                                     readers=_readers(rows, {"capability:a": 2, "capability:b": 12,
                                                             "capability:c": 5}, 15, 20))
    assert [c["name"] for c in got["capabilities"]] == ["Beta", "Gamma"]
    assert got["more"] == 1
    beta = got["capabilities"][0]
    # one person can be on both sides: 9 + 4 is not the 12 people
    assert (beta["people"], beta["for"], beta["against"]) == (12, 9, 4)
    assert "posts" not in beta            # never summed across sides
    assert "Ordered by how many people" in got["order"]


def test_silence_is_said(s):
    got = recommend.capability_split(None, "a/m1", s, today=date(2026, 11, 19),
                                     readers=_readers([], {}))
    assert got["capabilities"] == [] and "Silence is not praise" in got["empty"]


def test_a_running_span_says_so(s):
    got = recommend.capability_split(None, "a/m1", s, today=date(2026, 11, 5), days=14,
                                     readers=_readers([], {}))
    assert got["end"] == "2026-11-05" and got["still_running"] is True


@pytest.mark.parametrize("kwargs,match", [
    ({"model_id": "x/none"}, "no model"),
    ({"days": 0}, "days must be"),
    ({"start": date(2027, 1, 1)}, "future"),
])
def test_bad_requests_refuse(s, kwargs, match):
    args = {"model_id": "a/m1", **kwargs}
    with pytest.raises(recommend.TrajectoryRequestError, match=match):
        recommend.capability_split(None, args.pop("model_id"), s, today=date(2026, 11, 19),
                                   readers=_readers([], {}), **args)


def test_pain_angles_carry_counts_labels_and_silence(s):
    got = recommend.capability_split(
        None, "a/m1", s, today=date(2026, 11, 19), readers=_readers(
            [], {}, themes={"cost": {"people": 19, "for": 7, "against": 11, "neutral": 2},
                            "speed": {"people": 2, "for": 1, "against": 1, "neutral": 0}}))
    by = {a["key"]: a for a in got["pain_angles"]}
    assert by["cost"]["in_words"] == "mixed reports"       # 11 of 18 sided: 61% < 70%
    assert by["speed"]["in_words"] == "too few to say"
    assert by["hallucination"]["in_words"] == "nobody reported on it"
    assert got["pain_angles"][0]["key"] == "cost"            # ordered by people
    assert len(got["pain_angles"]) == len(s["pain_angles"])  # none dropped
    assert "Job insecurity" in got["pain_not_counted"]


def test_the_real_pain_config_is_sound():
    from judge.content_workspace import recipes

    assert recipes.pain_problems(settings.load()) == []


def test_a_bad_pain_slug_is_caught(s):
    from judge.content_workspace import recipes

    s["pain_angles"][0]["slugs"] = ["metric:speed", "nocolon"]
    found = recipes.pain_problems(s)
    assert any("'metric:speed' is not section:slug" in p for p in found)
    assert any("'nocolon' is not section:slug" in p for p in found)
