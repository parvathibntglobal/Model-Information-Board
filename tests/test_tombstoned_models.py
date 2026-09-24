"""A deliberately deleted model stays deleted: the poll skips it and says so.

Four claims:
  1. a tombstoned id - and its service tiers, which parse_models folds into the
     base id - never reaches write_model_versions, and the skip is COUNTED;
  2. a missing or malformed tombstone file RAISES; it is never read as an empty
     list, because an empty list is the silent failure this exists to prevent;
  3. a hand-insert path refuses a tombstoned id;
  4. the committed contract file itself loads, with no duplicates.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from collect.registry.openrouter import parse_models
from collect.registry.tombstones import (
    TOMBSTONES,
    TombstonedModel,
    TombstoneFileError,
    apply_tombstones,
    load_tombstones,
    refuse_if_tombstoned,
)


def _entry(model_id: str) -> dict:
    return {"id": model_id, "name": model_id, "created": 1700000000,
            "pricing": {"prompt": "0.000001", "completion": "0.000002"},
            "context_length": 8192}


def _feed(*ids: str):
    return parse_models({"data": [_entry(i) for i in ids]}, retrieved_at=datetime.now(UTC))


class TestThePollSkipsATombstone:
    def test_the_tombstoned_id_and_its_tier_are_dropped_and_counted(self):
        result = _feed("openai/gpt-4o", "openai/gpt-4o:batch", "anthropic/claude-opus-5")
        kept, dropped = apply_tombstones(result, frozenset({"openai/gpt-4o"}))

        assert [m.canonical_id for m in kept.models] == ["anthropic/claude-opus-5"]
        assert dropped == ("openai/gpt-4o",)

    def test_nothing_tombstoned_changes_nothing(self):
        result = _feed("anthropic/claude-opus-5")
        kept, dropped = apply_tombstones(result, frozenset())
        assert kept.models == result.models and dropped == ()

    def test_the_chain_stage_reads_the_file_and_reports_the_skip(self):
        import inspect

        from collect.ops import chain

        src = inspect.getsource(chain._poll_registry_stage)
        write_at = src.index("write_model_versions(conn, result)")
        assert src.index("apply_tombstones(result, load_tombstones())") < write_at, (
            "tombstones must be applied BEFORE the write, or the write re-creates them"
        )
        assert '"tombstoned_skipped"' in src


class TestABadFileIsLoudNotEmpty:
    def test_a_missing_file_raises(self, tmp_path):
        with pytest.raises(TombstoneFileError):
            load_tombstones(tmp_path / "absent.yaml")

    def test_an_entry_without_an_id_raises(self, tmp_path):
        f = tmp_path / "t.yaml"
        f.write_text("tombstoned:\n  - reason: forgot the id\n", encoding="utf-8")
        with pytest.raises(TombstoneFileError):
            load_tombstones(f)

    def test_a_duplicate_raises(self, tmp_path):
        f = tmp_path / "t.yaml"
        f.write_text("tombstoned:\n  - canonical_id: a/b\n  - canonical_id: a/b\n",
                     encoding="utf-8")
        with pytest.raises(TombstoneFileError):
            load_tombstones(f)

    def test_a_file_that_lists_nothing_is_an_honest_empty_set(self, tmp_path):
        f = tmp_path / "t.yaml"
        f.write_text("version: '1.0'\ntombstoned: []\n", encoding="utf-8")
        assert load_tombstones(f) == frozenset()


class TestAHandInsertRefuses:
    def test_refuses_a_tombstoned_id(self):
        with pytest.raises(TombstonedModel):
            refuse_if_tombstoned("openai/gpt-4o", frozenset({"openai/gpt-4o"}))

    def test_allows_anything_else(self):
        refuse_if_tombstoned("anthropic/claude-opus-5", frozenset({"openai/gpt-4o"}))

    def test_the_unpolled_loader_checks_before_it_writes(self):
        from pathlib import Path

        script = Path(__file__).resolve().parents[1] / "scripts" / "load_unpolled_models.py"
        src = script.read_text(encoding="utf-8")
        assert src.index("refuse_if_tombstoned(") < src.index("load_seed(conn, path=contract")


class TestTheCommittedContract:
    def test_it_loads_with_no_duplicates(self):
        stones = load_tombstones(TOMBSTONES)
        assert stones, "the committed file lists the deleted models"
        assert all("/" in s for s in stones), "every entry is a vendor/model canonical id"
