"""Evidence stages name the gates they run, read from the code that runs them.

WHAT WAS MISSING. `/admin/stages` explained 22 stages in words and `/admin/
pipeline` counted rows in each. Neither said WHAT GETS THROWN AWAY. Grepping
`web/src` for any gate reason name returned nothing at all: thirty decision
points across the pipeline, and not one of them reachable from a page.

⚠ THAT IS RULE 4 AT THE LARGEST SCALE IT COVERS. Every gate CAUSES AN ABSENCE.
  A metrics tab thin because eleven figures were withheld and one thin because
  nobody ever measured the model render identically, and they are opposite
  statements. A reader who cannot discover that a gate exists has no way to ask
  whether it fired.

THE THIRTY, BY WHERE THEY RUN:

    E4    6 hard gates + 2 flags   collect/triage/gates.py
    E5    9 quote-verification failures   judge/extract/verify.py
    E5c   3 metric refusals (write time)  judge/store/board_entries.py
    E6    5 claim rejections               judge/vet/reject.py
    --    5 metric withholdings (read time)

⚠ NO COUNTS, WHICH IS THE PAGE'S EXISTING RULE RATHER THAN A NEW ONE. How many
  documents a gate dropped is a figure needing its denominator and its run
  (rules 3 and 7), and the fetch log carries it beside the stage. This answers
  what the log cannot: which gates exist, and what each refuses.
"""

from __future__ import annotations

import pathlib
import re

from judge.app import _gates_after_the_run, _gates_at_each_stage

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "judge" / "app.py"
PANEL = ROOT / "web" / "src" / "components" / "StagesPanel.jsx"


def code_only(path: pathlib.Path) -> str:
    """Source with comments and docstrings stripped.

    ⚠ SEVENTH TIME THIS REPOSITORY HAS MET MENTION-VERSUS-USE. The tests below
      assert that gate names do NOT appear in `app.py`, and `app.py` discusses
      `known-bot-counted` at length in a comment explaining why it is a flag.
      A plain `in` check finds the explanation and reports the defect it was
      written to prevent.
    """
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsx":
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        return "\n".join(
            ln for ln in text.splitlines() if not ln.strip().startswith("//")
        )
    text = re.sub(r'"""(?:.|\n)*?"""', "", text)
    return "\n".join(
        ln for ln in text.splitlines() if not ln.strip().lstrip("#:").startswith("#")
        and not ln.strip().startswith("#")
    )


class TestTheGatesAreReadAndNotTranscribed:
    def test_no_gate_name_is_written_out_in_the_endpoint(self):
        """The one failure this whole shape exists to prevent. A list of gates
        typed into `app.py` is a count in prose with extra steps (rule 11):
        true the day it is pasted, silently wrong after the next gate lands,
        and misleading exactly the reader who went looking."""
        src = code_only(APP)
        for name in ("too-short-no-artifact", "no-resolvable-entity",
                     "out-of-window", "pure-link-post", "known-bot",
                     "affiliate_link", "predates_model", "span_crosses_comments",
                     "no quantity", "figure not in its quote"):
            assert name not in src, f"{name} is transcribed into app.py"

    def test_no_gate_name_is_written_out_in_the_panel(self):
        src = code_only(PANEL)
        for name in ("too-short-no-artifact", "affiliate_link",
                     "span_crosses_comments", "no quantity"):
            assert name not in src, f"{name} is transcribed into the panel"

    def test_every_family_names_where_it_was_read_from(self):
        stages, _ = _gates_at_each_stage()
        for sid, block in stages.items():
            assert block.get("source"), f"{sid} does not say where it was read"


class TestTheSixHardGatesArriveWithTheirMeaning:
    def test_e4_carries_every_gate_in_gate_order(self):
        from collect.triage.gates import GATE_ORDER

        stages, _ = _gates_at_each_stage()
        got = {g["name"] for g in stages["E4"]["runs"] if g["kind"] == "gate"}
        assert got == set(GATE_ORDER)

    def test_none_of_them_is_undescribed(self):
        stages, _ = _gates_at_each_stage()
        missing = [g["name"] for g in stages["E4"]["runs"] if g["undescribed"]]
        assert not missing, missing

    def test_a_gate_with_no_meaning_shows_as_undescribed(self, monkeypatch):
        """Drift reported rather than hidden — the direction `/admin/stages`
        already reports it in for stage descriptions. A gate added without a
        line about it must appear as a gap, not vanish.

        ⚠ THE READER IS PATCHED, NOT `collect`'s MODULE. An earlier version of
          this test mutated `collect.triage.gates.GATE_MEANING` and passed
          nothing, because `app.py` does not import that module — it may not,
          and it PARSES THE FILE instead. Patching the import would have been
          testing a path that no longer exists."""
        import judge.app as app_module

        monkeypatch.setattr(
            app_module, "_triage_gates_in_source",
            lambda: (("a-gate-nobody-explained", "known-bot"),
                     {"known-bot": "the platform says so"}, {}),
        )
        stages, _ = app_module._gates_at_each_stage()
        rows = {g["name"]: g for g in stages["E4"]["runs"]}
        assert rows["a-gate-nobody-explained"]["undescribed"] is True
        assert rows["a-gate-nobody-explained"]["drops"] is None
        assert rows["known-bot"]["undescribed"] is False

    def test_a_family_it_cannot_parse_is_named_rather_than_dropped(self, monkeypatch):
        """Rule 6: a stage listing no gates because the parse failed and one
        that genuinely gates nothing look identical, and the first is broken."""
        import judge.app as app_module

        def boom():
            raise ValueError("gates.py moved")

        monkeypatch.setattr(app_module, "_triage_gates_in_source", boom)
        stages, unreadable = app_module._gates_at_each_stage()
        assert "E4" not in stages
        assert any("E4" in u for u in unreadable)


class TestAFlagIsNotAGate:
    def test_the_two_flags_are_marked_as_records_rather_than_drops(self):
        """⚠ RULE 8 IN TWO NAMES, and the page has to keep them apart. Both are
        recorded on a document that is KEPT, because each judgement was
        measured on a population we chose ourselves — the 7 accounts carrying
        `bot` in a login were found by grepping our own corpus, against the 26
        GitHub itself declares. Listing them beside the gates would say the
        pipeline discards twice what it does."""
        from collect.triage.gates import FLAG_MEANING, GATE_ORDER

        stages, _ = _gates_at_each_stage()
        flags = {g["name"] for g in stages["E4"]["runs"] if g["kind"] == "flag"}
        assert flags == set(FLAG_MEANING)
        assert not (flags & set(GATE_ORDER))


class TestTheReadTimeGatesAreNotAFetchStage:
    def test_they_are_returned_beside_the_stages_and_not_inside_one(self):
        """They run when somebody OPENS A PAGE, over rows already stored.
        Filing them under a fetch stage would tell a reader chasing a missing
        figure to go and look at a run that never touched it."""
        after, err = _gates_after_the_run()
        assert err is None
        assert after, "the read-time gates vanished"
        stages, _ = _gates_at_each_stage()
        inside = {
            g["name"] for block in stages.values() for g in block.get("runs", [])
        }
        assert not ({g["name"] for g in after} & inside)

    def test_write_time_and_read_time_split_the_metric_gates(self):
        from judge.store.board_entries import METRIC_GATES

        stages, _ = _gates_at_each_stage()
        write = {g["name"] for g in stages["E5c"]["runs"]}
        read = {g["name"] for g in _gates_after_the_run()[0]}
        assert write | read == {g["reason"] for g in METRIC_GATES}
        assert not (write & read)


class TestTheMetricGatesHaveOneSource:
    def test_every_declared_reason_is_a_string_the_gate_can_return(self):
        """⚠ THE REGISTRY AND THE GATE MUST NOT DRIFT, which is the whole
        reason the reasons became constants. A page listing a reason the code
        cannot produce is worse than a page listing none."""
        from judge.store import board_entries as be

        src = be.__file__
        text = pathlib.Path(src).read_text(encoding="utf-8")
        for gate in be.METRIC_GATES:
            reason = gate["reason"]
            const = next(
                (n for n in dir(be)
                 if n.startswith("GATE_") and getattr(be, n) == reason),
                None,
            )
            assert const, f"{reason!r} is not a declared constant"
            assert f"return {const}" in text or f"{const}.format(" in text, (
                f"{const} is declared and never returned"
            )

    def test_the_reasons_the_gates_return_are_all_declared(self):
        """The other direction: a reason returned by the code and missing from
        the registry would never reach the page."""
        from judge.store import board_entries as be

        declared = {g["reason"] for g in be.METRIC_GATES}
        text = pathlib.Path(be.__file__).read_text(encoding="utf-8")
        returned = set(re.findall(r"return (GATE_[A-Z_]+)", text))
        returned |= set(re.findall(r"return (GATE_[A-Z_]+)\.format", text))
        for const in returned:
            assert getattr(be, const) in declared, f"{const} is not in METRIC_GATES"


class TestItStillShowsNoFigures:
    def test_not_one_count_reaches_the_gate_payload(self):
        """The page's own rule, and it predates this. A count here would need
        its denominator and its run (rules 3 and 7), and the fetch log already
        carries both."""
        stages, _ = _gates_at_each_stage()
        after, _ = _gates_after_the_run()
        rows = [g for b in stages.values() for g in b.get("runs", [])] + after
        for g in rows:
            assert set(g) == {"name", "kind", "drops", "undescribed"}
            for value in g.values():
                assert not isinstance(value, int) or isinstance(value, bool)


class TestAFamilyItCannotReadIsNamed:
    def test_an_unreadable_family_is_reported_rather_than_left_empty(self):
        """Rule 6 at the page level: a stage listing no gates because an import
        failed and one that genuinely gates nothing look identical, and the
        first is a broken page while the second is a fact."""
        src = code_only(APP)
        body = src[src.index("def _gates_at_each_stage"):]
        body = body[:body.index("def _gates_after_the_run")]
        assert body.count("unreadable.append(") >= 4, (
            "each gate family must name itself when it cannot be read"
        )
