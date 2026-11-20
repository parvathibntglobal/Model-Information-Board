"""The media generators' specs (judge/content_workspace/media_specs.py) and the
generators themselves (tools/media/).

The builders are tested on fake board rows, so no database: each look's
arithmetic, its ordering, the publication rules it keeps (withheld sources are
never split out; cards are stored paraphrases, never a held source) and every
refusal it shares with its generator. The generators need Chromium to render,
which CI does not have; what CI can check is that every look in workspace.yaml
has a generator, and every font a generator loads is in tools/media/fonts with
its licence. A generator's own spec refusal is run with Node when the generator
can be loaded at all.
"""

from __future__ import annotations

import copy
import json
import re
import shutil
import subprocess
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from judge import publication
from judge.content_workspace import media_specs as ms
from judge.content_workspace import settings

REPO = Path(__file__).resolve().parents[1]
MEDIA = REPO / "tools" / "media"
S = settings.load()


# ── field report ─────────────────────────────────────────────────────────────


def _fr_readers(weeks=None, release="2026-10-01", said=None):
    def model(_conn, model_id):
        if model_id != "a/m1":
            return None
        return {"id": "a/m1", "name": "Provider: Model One", "release_date": release, "price": "-"}

    def week(_conn, _mv, start, _today):
        i = (start - date(2026, 10, 1)).days // 7
        people, posts, pos, neg = (weeks or {}).get(i, (0, 0, 0, 0))
        return {"people": people, "posts": posts,
                "by_polarity": {"positive": {"posts": pos}, "negative": {"posts": neg}},
                "said": (said or {}).get(i)}

    return {"model": model, "week": week}


def _said(side, text, platform="hackernews", at="2026-10-03T00:00:00Z"):
    return {side: [{"text": text, "on": [], "at": at, "source": {"platform": platform}}]}


class TestFieldReport:
    def test_weeks_and_proofs(self):
        r = _fr_readers(weeks={0: (5, 6, 4, 1), 1: (9, 11, 7, 3)},
                        said={0: _said("positive", "Held a long refactor together."),
                              1: _said("negative", "Lost a rule given early.", "devto",
                                       "2026-10-09T00:00:00Z")})
        spec = ms.field_report(None, "a/m1", S, weeks=2, today=date(2026, 11, 19), readers=r)
        assert spec["title"] == "Model One" and spec["start"] == "2026-10-01"
        assert [w["people"] for w in spec["weeks"]] == [5, 9]
        assert spec["weeks"][1] == {"from": "2026-10-08", "to": "2026-10-14", "people": 9,
                                    "posts": 11, "pos": 7, "neg": 3}
        assert [(p["side"], p["week"], p["platform"]) for p in spec["proofs"]] == [
            ("positive", 1, "Hacker News"), ("negative", 2, "dev.to")]

    @pytest.mark.parametrize("kwargs,match", [
        ({"weeks": 5}, "1 to 4 weeks"),
        ({"weeks": 0}, "1 to 4 weeks"),
        ({"model_id": "z/none"}, "no model"),
        ({"weeks": 4, "today": date(2026, 10, 20)}, "still running"),
    ])
    def test_refusals(self, kwargs, match):
        args = {"model_id": "a/m1", "weeks": 2, "today": date(2026, 11, 19), **kwargs}
        with pytest.raises(ms.MediaSpecError, match=match):
            ms.field_report(None, args.pop("model_id"), S, readers=_fr_readers(), **args)

    def test_no_release_date_needs_a_start(self):
        with pytest.raises(ms.MediaSpecError, match="no recorded release date"):
            ms.field_report(None, "a/m1", S, weeks=1, today=date(2026, 11, 19),
                            readers=_fr_readers(release=None))

    def test_an_unknown_platform_refuses_rather_than_printing_an_id(self):
        r = _fr_readers(weeks={0: (1, 1, 1, 0)}, said={0: _said("positive", "Fine.", "mastodon")})
        with pytest.raises(ms.MediaSpecError, match="no display name for platform 'mastodon'"):
            ms.field_report(None, "a/m1", S, weeks=1, today=date(2026, 11, 19), readers=r)


# ── data card ────────────────────────────────────────────────────────────────

TEXT = {"headline": "people reported on it", "path": "/reviews/capabilities/x",
        "sides": {"negative": {"stat": "s", "legend": "l", "bar": "b"},
                  "positive": {"stat": "s", "legend": "l", "bar": "b"}},
        "page2_head": ["a", "b"], "page2_note": "n", "not_a_measurement": "m"}
READ_AT = datetime(2026, 11, 19, 5, 0, tzinfo=UTC)


def _dc_got(rows, shown):
    return {"names": [("Usage limits", 9)], "rows": rows, "shown_rows": shown, "read_at": READ_AT}


def _dc(rows, shown, text=TEXT):
    return ms.data_card_from_rows("usage-limits", "capability", text, date(2026, 10, 19),
                                  date(2026, 11, 18), date(2026, 11, 19), _dc_got(rows, shown))


class TestDataCard:
    rows = [("m1", "P: Beta", "negative", "a1", "devto"),
            ("m1", "P: Beta", "positive", "a2", "reddit"),
            ("m2", "P: Alpha", "negative", "a3", "reddit"),
            ("m2", "P: Alpha", "negative", None, "x"),       # no author: an entry, not a person
            ("m3", "P: Gamma", "negative", "a4", "x")]
    shown = [("devto", "a1")]                                  # reddit and x are withheld

    def test_totals_rows_and_order(self):
        spec = _dc(self.rows, self.shown)
        t = spec["totals"]
        assert (t["people"], t["negative"], t["positive"], t["models"], t["entries"],
                t["no_author_entries"]) == (4, 3, 1, 3, 5, 1)
        # most people first; ties by name
        assert [r["model"] for r in spec["rows"]] == ["Beta", "Alpha", "Gamma"]

    def test_withheld_sources_are_never_split_out(self):
        spec = _dc(self.rows, self.shown)
        assert spec["sources"] == [{"platform": "dev.to", "people": 1}]
        assert spec["sources_not_named"] == {"people": 3, "platforms": 2}
        assert not any(s["platform"] in ("Reddit", "X") for s in spec["sources"])

    def test_more_than_eight_models_become_the_rest(self):
        rows = [(f"m{i}", f"P: M{i:02d}", "negative", f"a{i}", "devto") for i in range(11)]
        spec = _dc(rows, [("devto", f"a{i}") for i in range(11)])
        assert len(spec["rows"]) == 8 and spec["rest"]["models"] == 3

    def test_too_many_platforms_refuses(self):
        srcs = list(ms.PLATFORM_NAMES)[:9]
        rows = [("m1", "P: M", "negative", f"a{i}", s) for i, s in enumerate(srcs)]
        with pytest.raises(ms.MediaSpecError, match="page 3 holds 8"):
            _dc(rows, [(s, f"a{i}") for i, s in enumerate(srcs)])

    def test_a_persons_words_are_never_defaulted(self):
        text = {k: v for k, v in TEXT.items() if k != "headline"}
        with pytest.raises(ms.MediaSpecError, match="missing \\['headline'\\]"):
            _dc(self.rows, self.shown, text)

    def test_an_unknown_label_refuses(self):
        with pytest.raises(ms.MediaSpecError, match="spelled whole"):
            ms.data_card_from_rows("usage", "capability", TEXT, date(2026, 10, 19),
                                   date(2026, 11, 18), date(2026, 11, 19),
                                   {**_dc_got([], []), "names": []})

    def test_a_running_window_refuses_unless_asked(self):
        with pytest.raises(ms.MediaSpecError, match="still running"):
            ms.data_card_window(30, date(2026, 11, 19), date(2026, 11, 19))
        frm, to, running = ms.data_card_window(30, date(2026, 11, 19), date(2026, 11, 19),
                                               allow_running=True)
        assert running and frm == date(2026, 10, 20)
        assert ms.data_card_window(30, None, date(2026, 11, 19))[1] == date(2026, 11, 18)

    def test_an_uncounted_section_refuses_before_reading(self):
        with pytest.raises(ms.MediaSpecError, match="not counted on public pages"):
            ms.data_card(None, "speed", TEXT, section="not-a-section",
                         to=date(2026, 11, 18), today=date(2026, 11, 19))


# ── evidence board ───────────────────────────────────────────────────────────


def _price(day, i_from, i_to, o_from, o_to):
    return (datetime.fromisoformat(f"{day}T12:00:00+00:00"),
            {"from": {"price_in": i_from, "price_out": o_from},
             "to": {"price_in": i_to, "price_out": o_to}})


def _eb_got(prices=None, people=None, cards=None):
    return {"model": ("mv_1", "P: Model Two"), "read_at": READ_AT,
            "prices": prices if prices is not None else [
                _price("2026-10-01", 0.3, 0.2, 1.2, 0.8),
                _price("2026-11-05", 0.2, 0.3, 0.8, 1.2)],
            "people": people if people is not None else [
                ("positive", "a1", date(2026, 9, 1)), ("negative", "a2", date(2026, 9, 2)),
                ("neutral", "a3", date(2026, 9, 3)), ("positive", None, date(2026, 9, 4))],
            "cards": cards if cards is not None else [
                ("d1", "Reports that prompt caching saved money.", "devto", date(2026, 9, 1),
                 ["positive|prompt-caching"]),
                ("d2", "Reports that coding reliability slipped on long files.", "github",
                 date(2026, 9, 2), ["negative|coding-reliability"]),
                ("d3", "x" * 200, "devto", date(2026, 9, 3), ["positive|speed"]),
                ("d4", "Says nothing about the label.", "devto", date(2026, 9, 4),
                 ["positive|reasoning"])]}


class TestEvidenceBoard:
    def test_people_prices_and_cards(self):
        spec = ms.evidence_board_from_rows("p/model-two", _eb_got(), S, cards=6)
        assert spec["model"] == "Model Two" and spec["path"].endswith("/p/model-two")
        assert spec["people"] == {"all": 3, "for": 1, "against": 1, "neither": 1, "entries": 4,
                                  "no_author_entries": 1}
        assert [c["side"] for c in spec["cards"]] == ["for", "against"]   # alternating
        assert spec["cards"][0]["source"] == "dev.to"
        # a card over 160 characters, and one whose label is not in its text, are left out
        assert "1 whose label is not in their text left out" in spec["population"]
        # nobody posted since the last change: said, as silence (rule 4)
        assert spec["note"] == "nobody has reported on it since the 5 Nov rise"
        assert spec["extra_stats"][0]["value"] == 0

    def test_a_held_source_is_never_carded(self):
        held = [k for k in ms.PLATFORM_NAMES if publication.feed_hides(k)]
        if not held:
            pytest.skip("no source is held by the evidence feed's terms today")
        got = _eb_got(cards=[("d1", "Reports that prompt caching saved money.", held[0],
                              date(2026, 9, 1), ["positive|prompt-caching"])])
        with pytest.raises(ms.MediaSpecError, match="no cardable paraphrase"):
            ms.evidence_board_from_rows("p/model-two", got, S)

    @pytest.mark.parametrize("got,match", [
        (_eb_got(prices=[]), "no price change"),
        (_eb_got(prices=[_price(f"2026-10-0{i}", 0.3, 0.3, 1.0, 1.0) for i in range(1, 7)]),
         "case card holds 5"),
        (_eb_got(prices=[_price("2026-10-01", 0.3, 0.2, 1.2, 0.8),
                         _price("2026-11-05", 0.25, 0.3, 0.8, 1.2)]), "does not start where"),
        (_eb_got(prices=[(datetime(2026, 10, 1, tzinfo=UTC), {"from": {}, "to": {}})]),
         "a missing price is not 0"),
        (_eb_got(people=[]), "no counted report"),
        (_eb_got(people=[("positive", f"a{i}", date(2026, 9, 1)) for i in range(41)]),
         "a pin row holds 40"),
        ({"model": None, "read_at": READ_AT}, "no model"),
    ])
    def test_refusals(self, got, match):
        with pytest.raises(ms.MediaSpecError, match=match):
            ms.evidence_board_from_rows("p/model-two", got, S)

    @pytest.mark.parametrize("kwargs,match", [
        ({"cards": 0}, "cards is 1 to 6"),
        ({"cards": 7}, "cards is 1 to 6"),
        ({"text": {"headline": "x"}}, "does not read"),
        ({"text": {"card_documents": ["d9"]}}, "not a cardable stored paraphrase"),
    ])
    def test_request_refusals(self, kwargs, match):
        with pytest.raises(ms.MediaSpecError, match=match):
            ms.evidence_board_from_rows("p/model-two", _eb_got(), S, **kwargs)


# ── the command ──────────────────────────────────────────────────────────────


class TestTheCommand:
    def test_it_needs_the_boards_database(self, monkeypatch, capsys):
        from judge.content_workspace import __main__ as cli

        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setattr(cli, "load_dotenv", lambda *a, **k: None)
        assert cli.main(["media-spec", "field-report", "--model", "a/m1"]) == 2
        assert "DATABASE_URL is unset" in capsys.readouterr().out

    def test_it_will_not_overwrite_a_spec(self, tmp_path, capsys):
        from judge.content_workspace import __main__ as cli

        out = tmp_path / "spec.json"
        out.write_text("{}", encoding="utf-8")
        assert cli.main(["media-spec", "field-report", "--model", "a/m1", "--out",
                         str(out)]) == 2
        assert "--force" in capsys.readouterr().out

    def test_it_is_not_a_write_command(self):
        from judge.content_workspace import __main__ as cli

        assert "media-spec" not in cli.WRITE_COMMANDS


# ── the generators ───────────────────────────────────────────────────────────


def _generators():
    return {k: REPO / v["generator"] for k, v in S["looks"].items()}


def test_every_look_has_a_generator():
    from judge.content_workspace import recipes

    for look, path in _generators().items():
        assert path.is_file(), f"{look}: {path}"
    s = copy.deepcopy(S)
    s["looks"]["field_report"]["generator"] = "tools/media/nowhere.mjs"
    assert any("does not exist" in p for p in recipes.problems(s, settings.seed()))


def test_every_font_a_generator_loads_is_committed_with_its_licence():
    fonts = MEDIA / "fonts"
    for look, path in _generators().items():
        names = re.findall(r"F\('([^']+)'\)", path.read_text(encoding="utf-8"))
        assert names, f"{look}: no font found; the pattern no longer matches the generator"
        for name in names:
            assert (fonts / name).is_file(), f"{look} loads {name}, not in tools/media/fonts"
            family = name.split("-", 1)[0]
            assert (fonts / f"{family}-OFL.txt").is_file(), f"{name} has no licence file"


def test_no_generator_or_example_names_a_personal_path():
    for path in MEDIA.rglob("*"):
        if path.is_file() and path.suffix in (".mjs", ".md", ".json", ".py") \
                and "node_modules" not in path.parts:
            text = path.read_text(encoding="utf-8")
            assert not re.search(r"C:[/\\]Users|\.claude[/\\]", text), path


def test_examples_are_synthetic():
    for look in ("field-report", "data-card", "evidence-board"):
        spec = json.loads((MEDIA / look / "examples" / "example.json").read_text(encoding="utf-8"))
        blob = json.dumps(spec)
        assert "Example Model" in blob or "Example capability" in blob, look


NODE = shutil.which("node")
LOADABLE = (MEDIA / "node_modules" / "playwright-core").is_dir()


@pytest.mark.skipif(not (NODE and LOADABLE),
                    reason="needs Node and `npm install` in tools/media (the generators import "
                           "playwright-core before they read a spec); CI installs neither")
@pytest.mark.parametrize("look", ["field_report", "data_card", "evidence_board"])
def test_a_generator_refuses_a_bad_spec_before_rendering(look, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    r = subprocess.run([NODE, str(_generators()[look]), str(bad), str(tmp_path / "out")],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode != 0
    assert "spec" in (r.stdout + r.stderr).lower()
    assert not (tmp_path / "out").exists() or not list((tmp_path / "out").glob("*.png"))
