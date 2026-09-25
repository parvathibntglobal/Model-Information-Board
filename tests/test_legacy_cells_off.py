"""The legacy capability-card path switched OFF (`judge/legacy.py`).

With `LEGACY_CELLS` off - the production default since 2026-09-24:

  1. the extractor is not asked for the ratified-twelve field, proposals or
     `unclassified` - not in the prompt and not in the tool schema;
  2. the pipeline writes no claim, claim_weight or cell rows and does not run
     `close_the_night`, but still writes every board entry;
  3. the roster sends `evidence: null` so the frozen cell badge is hidden;
  4. the cell CLI commands refuse.

`tests/conftest.py` pins the switch ON for the rest of the suite; every test
here turns it off itself. No database.
"""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from judge import pipeline as pipeline_mod
from judge.extract.client import strip_legacy_fields, tool_schema_for
from judge.extract.prompt import build_system_prompt
from judge.extract.runner import ExtractionRun
from judge.extract.schema import ExtractedClaim, ExtractionResult
from judge.legacy import legacy_cells_enabled


@pytest.fixture
def off(monkeypatch):
    monkeypatch.setenv("LEGACY_CELLS", "off")


class TestTheSwitch:
    @pytest.mark.parametrize("value", [None, "", "off", "0", "no", "banana"])
    def test_anything_but_on_is_off(self, monkeypatch, value):
        if value is None:
            monkeypatch.delenv("LEGACY_CELLS", raising=False)
        else:
            monkeypatch.setenv("LEGACY_CELLS", value)
        assert legacy_cells_enabled() is False

    @pytest.mark.parametrize("value", ["on", "ON", "1", "true", "yes"])
    def test_on_is_on(self, monkeypatch, value):
        monkeypatch.setenv("LEGACY_CELLS", value)
        assert legacy_cells_enabled() is True


class TestTheExtractorIsNotAskedForTheTwelve:
    def test_the_prompt_carries_no_ratified_list(self, off):
        prompt = build_system_prompt([])
        for gone in ("RATIFIED CAPABILITY KEYS", "ratified list", "proposed_capabilities",
                     "stretch a quote to fit a key", "unclassified"):
            assert gone not in prompt, gone
        assert "A claim needs three things" in prompt
        assert "EXEMPLARS FOR THE THREE BOARD SECTIONS" in prompt, "the board half stays"

    def test_the_legacy_prompt_is_unchanged_when_on(self):
        prompt = build_system_prompt(["code.generation"], legacy=True)
        assert "RATIFIED CAPABILITY KEYS" in prompt
        assert "  - code.generation" in prompt

    def test_on_still_refuses_an_empty_vocabulary(self):
        with pytest.raises(ValueError):
            build_system_prompt([], legacy=True)

    def test_the_tool_schema_has_no_slot_for_them(self):
        schema = strip_legacy_fields(tool_schema_for(ExtractionResult))
        item = schema["properties"]["claims"]["items"]
        assert "capability" not in item["properties"]
        assert "capability" not in item.get("required", [])
        assert "proposed_capabilities" not in schema["properties"]
        assert "unclassified" not in schema["properties"]
        assert "board_entries" in item["properties"], "the board field stays"

    def test_a_moved_schema_refuses_rather_than_passing_unstripped(self):
        with pytest.raises(ValueError, match="shape moved"):
            strip_legacy_fields({"properties": {"claims": {"items": {"properties": {}}}}})

    def test_the_runner_sends_the_stripped_pair(self, off):
        from judge.extract.client import FakeClient
        from judge.extract.runner import ThreadInput, extract

        seen = {}

        class Capture(FakeClient):
            def complete(self, *, system, user, tool_schema):
                seen["system"], seen["schema"] = system, tool_schema
                return super().complete(system=system, user=user, tool_schema=tool_schema)

        client = Capture(responses=['{"claims": [], "no_claim_reason": "nothing"}'])
        thread = ThreadInput(thread_context_id="t", flattened_text="some text",
                             offset_map=(), raw_text_of={"d": "some text"})
        extract(thread, client=client, capability_keys=[])

        assert "RATIFIED CAPABILITY KEYS" not in seen["system"]
        assert "proposed_capabilities" not in seen["schema"]["properties"]


# ── the pipeline ──────────────────────────────────────────────────────────


def _claim() -> ExtractedClaim:
    return ExtractedClaim.model_validate({
        "source_comment_id": "d",
        "model_ref": {"surface": "GPT-5.5", "resolved_version_id": "gpt-5.5",
                      "specificity": "version", "resolution_confidence": 0.9,
                      "speaking": "own-experience"},
        "board_entries": [{"section": "capability", "slug": "development-speed",
                           "name": "Development speed",
                           "definition": "Whether it shortens implementation time."}],
        "polarity": "positive", "quote": "it was fast", "quote_offset": [0, 11],
        "relevance": "central",
    })


def _pipeline(monkeypatch, *, boards: list):
    run = ExtractionRun(thread_context_id="t")
    run.verified = [(_claim(), SimpleNamespace(document_id="d", display_text="it was fast"))]
    monkeypatch.setattr(pipeline_mod, "extract", lambda *a, **k: run)

    def no_claims(*_a, **_k):
        raise AssertionError("a claim row was written with the legacy path off")

    def capture(_conn, rows, **_kw):
        boards.extend(rows)
        return {"proposed": len(rows), "stored": len(rows), "skipped_unverified": 0}

    import judge.store.board_entries as board_store
    monkeypatch.setattr(board_store, "store_entries", capture)
    p = pipeline_mod.Pipeline(conn=None, client=None, capability_keys=[], extractor_model="m")
    monkeypatch.setattr(p._claims, "write", no_claims)
    monkeypatch.setattr(p, "_vet", lambda *a, **k: set())
    return p


FACTS = {"d": SimpleNamespace(has_numbers=False, has_conditions=False, platform="devto",
                              created_at=date(2026, 9, 20), author_id="a1")}


class TestThePipelineWritesTheBoardOnly:
    def test_no_claim_row_and_no_refusal_but_the_board_entry_is_written(self, off, monkeypatch):
        boards: list = []
        p = _pipeline(monkeypatch, boards=boards)

        result = p.run(SimpleNamespace(thread_context_id="t"), facts=FACTS,
                       model_version_of={"gpt-5.5": "mv_gpt"}, rebuild_cells=False)

        assert result.stored_claim_ids == []
        assert result.cell_refusals == [], "a retired path is not a refusal"
        assert [(b["slug"], b["model_version_id"], b["claim_id"]) for b in boards] == [
            ("development-speed", "mv_gpt", None)
        ]
        assert result.board_entries_stored == 1

    def test_the_batch_rebuilds_no_cells_and_closes_no_night(self, off, monkeypatch):
        boards: list = []
        p = _pipeline(monkeypatch, boards=boards)
        monkeypatch.setattr(p._cells, "rebuild_all",
                            lambda **k: pytest.fail("cells rebuilt with the path off"))
        monkeypatch.setattr(pipeline_mod, "close_the_night",
                            lambda *a, **k: pytest.fail("close_the_night ran"))
        monkeypatch.setattr(p._ledger, "record", lambda record: None)

        from judge.curate.labels import Driver

        results = p.run_all(
            [SimpleNamespace(thread_context_id="t", flattened_text="x")],
            facts=FACTS, model_version_of={"gpt-5.5": "mv_gpt"},
            already_extracted={}, driver=Driver("new-evidence"),
        )
        assert len(results) == 1 and len(boards) == 1


# ── the readers ───────────────────────────────────────────────────────────


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else (None,)


class _Conn:
    """Roster SQL -> one model row; the priced-at query -> None."""

    def execute(self, sql, *args):
        if "max(observed_at)" in sql:
            return _Rows([(None,)])
        row = ("mv_1", "Model", "acme", "acme/m", 1, 2, None, 1000, 100,
               True, False, False, False, "active",
               3, 1, ["code.generation"], 5, {"capability": 5})
        return _Rows([row])


class TestTheReaders:
    def test_the_roster_sends_no_cell_verdict(self, off):
        from judge.pages.roster import RosterReader

        roster = RosterReader(_Conn()).all()
        model = (roster.models if hasattr(roster, "models") else roster["models"])[0]
        assert model["evidence"] is None, "a frozen cell verdict must not read as live"
        assert model["board"], "the board badge is unaffected"

    def test_the_roster_keeps_the_verdict_when_on(self, monkeypatch):
        monkeypatch.setenv("LEGACY_CELLS", "on")
        from judge.pages.roster import RosterReader

        roster = RosterReader(_Conn()).all()
        model = (roster.models if hasattr(roster, "models") else roster["models"])[0]
        assert model["evidence"]["state"] == "published"

    def test_the_cell_commands_refuse(self, off, capsys):
        from judge.cli import _refuse_if_legacy_off

        assert _refuse_if_legacy_off("rebuild-cells") == 2
        assert "LEGACY_CELLS=on" in capsys.readouterr().err

    def test_the_frontend_hides_the_badge_on_null(self):
        from pathlib import Path

        src = Path("web/src/routes/Models.jsx").read_text(encoding="utf-8")
        body = src[src.index("function EvidenceBadge"):]
        assert body.index("if (e === null) return null") < body.index("'unreported'")
