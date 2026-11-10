"""A regenerate keeps every name the vocabulary already has (#606).

`board_curation.py write-contract` used to name every slug from the database's
commonest name, so a run to add two entries would have renamed 41 others, some
plausibly and wrongly (`humaneval` -> "Coding benchmarks"), and each rename
changes the extractor's prompt. Now: a pinned name wins, an existing name is
kept, and the database names a NEW slug only.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PROPOSALS = ROOT / "docs" / "proposals"
VOCABULARY = ROOT / "contract" / "board_vocabulary.yaml"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, PROPOSALS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bc = _load("board_curation")
EXISTING = {("metric", "humaneval"): "HumanEval", ("metric", "fast-mode"): "Time to first token"}
FROM_DB = {("metric", "humaneval"): "Coding benchmarks", ("metric", "fast-mode"): "Fast Mode",
           ("metric", "brand-new"): "Brand New"}


class TestChooseName:
    def test_an_existing_name_is_kept_over_the_database(self):
        assert bc.choose_name("metric", "humaneval", pinned={}, existing=EXISTING,
                              from_db=FROM_DB) == ("HumanEval", "kept")

    def test_a_pin_wins_over_the_existing_name(self):
        assert bc.choose_name("metric", "fast-mode", pinned={"fast-mode": "Fast mode"},
                              existing=EXISTING, from_db=FROM_DB) == ("Fast mode", "pinned")

    def test_only_a_new_slug_takes_the_database_name(self):
        assert bc.choose_name("metric", "brand-new", pinned={}, existing=EXISTING,
                              from_db=FROM_DB) == ("Brand New", "new, from the database")

    def test_a_new_slug_with_no_rows_is_named_from_itself(self):
        assert bc.choose_name("metric", "no-rows-yet", pinned={}, existing=EXISTING,
                              from_db=FROM_DB) == ("No rows yet", "new, from the slug")


def test_a_pin_for_a_slug_the_proposal_does_not_keep_is_refused(monkeypatch):
    """Dropped silently, the chosen name would never reach the file (rule 12)."""
    stray = SimpleNamespace(SECTION="metric", PARENTS={}, CLUSTERS={}, DECLINE={},
                            NAMES={"not-kept": "Not Kept"})
    others = [SimpleNamespace(SECTION=s, PARENTS={}, CLUSTERS={}, DECLINE={})
              for s in ("best_for", "capability")]
    with pytest.raises(SystemExit, match="metric/not-kept"):
        bc.write_contract("postgresql://unused", [*others, stray])


def test_every_pinned_name_is_the_name_in_the_contract():
    """The proposals and the generated file agree: a pin nobody regenerated
    would read as decided while the extractor is still shown the old name."""
    vocab = yaml.safe_load(VOCABULARY.read_text(encoding="utf-8"))
    names = {(section, item["slug"]): item["name"]
             for section, heads in vocab.items() for items in heads.values() for item in items}
    for module in ("job_curation_2026_10_14", "capability_curation_2026_10_14",
                   "metric_curation_2026_10_14"):
        p = _load(module)
        for slug, name in getattr(p, "NAMES", {}).items():
            assert names.get((p.SECTION, slug)) == name, (p.SECTION, slug)


def test_the_names_the_regenerate_would_have_broken_are_kept():
    """Three of #606's examples, which the commonest-name rule renamed wrongly."""
    vocab = yaml.safe_load(VOCABULARY.read_text(encoding="utf-8"))
    names = {item["slug"]: item["name"] for items in vocab["metric"].values() for item in items}
    assert names["humaneval"] == "HumanEval"
    assert names["pass-at-1"] == "Pass@1 rate"
    assert names["osworld"] == "OSWorld 2.0"
