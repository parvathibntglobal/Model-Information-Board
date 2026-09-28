"""The registry diff: what arrived, what left, what now expires. Pure logic only."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from collect.registry.openrouter import base_id

_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "registry_diff_under_test", _ROOT / "scripts" / "registry_diff.py")
rd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rd)


def _m(mid, created=1700000000, exp=None):
    return {"id": mid, "name": mid, "created": created, "expiration_date": exp}


REG = {"anthropic/claude-opus-5": {"provenance": "polled", "retirement_date": None},
       "old/gone-model": {"provenance": "polled", "retirement_date": None},
       "hand/unpolled-model": {"provenance": "unpolled", "retirement_date": None}}


def test_arrivals_fold_tiers_list_pro_apart_and_skip_tombstones():
    cat = [_m("anthropic/claude-opus-5"), _m("anthropic/claude-opus-5.5"),
           _m("anthropic/claude-opus-5.5:batch"), _m("openai/gpt-6-astra-pro"),
           _m("openai/gpt-4o")]
    d = rd.compute_diff(cat, REG, frozenset({"openai/gpt-4o"}), base_id)
    assert [b for b, _ in d["arrivals"]] == ["anthropic/claude-opus-5.5"]
    assert [b for b, _ in d["pro_arrivals"]] == ["openai/gpt-6-astra-pro"], (
        "listed apart, and as an ARRIVAL: the poll inserts -pro ids (#463)")
    assert d["tombstoned_in_catalogue"] == ["openai/gpt-4o"]


def test_departures_are_polled_rows_only():
    d = rd.compute_diff([_m("anthropic/claude-opus-5")], REG, frozenset(), base_id)
    assert d["departures"] == ["old/gone-model"], "an unpolled row was never in the catalogue"


def test_expirations_separate_the_sentinel_and_skip_unchanged():
    cat = [_m("anthropic/claude-opus-5", exp="2026-11-11"),
           _m("old/gone-model", exp="2098-12-31")]
    d = rd.compute_diff(cat, REG, frozenset(), base_id)
    assert d["expiring"] == [("anthropic/claude-opus-5", "2026-11-11", None)]
    assert d["sentinel"] == [("old/gone-model", "2098-12-31", None)]
    reg2 = {**REG, "anthropic/claude-opus-5": {"provenance": "polled",
                                                "retirement_date": "2026-11-11"}}
    assert rd.compute_diff(cat, reg2, frozenset(), base_id)["expiring"] == []


def test_the_report_always_says_what_it_cannot_see():
    d = rd.compute_diff([], {}, frozenset(), base_id)
    text = rd.render(d, catalogue_size=0, registry_size=0)
    assert "still need a person" in text and "Seating stays manual" in text


def test_the_workflow_diffs_before_it_polls_and_refuses_when_unconfigured():
    wf = (_ROOT / ".github" / "workflows" / "registry-poll.yml").read_text(encoding="utf-8")
    assert wf.index("registry_diff.py") < wf.index("--only poll-registry")
    assert "exit 1" in wf and "STAGING_DATABASE_URL" in wf


def test_the_poll_skips_latest_pointers_and_counts_them():
    """`~vendor/family-latest` carries `alias_target`: a pointer, not a model."""
    from datetime import UTC, datetime

    from collect.registry.openrouter import parse_models

    feed = {"data": [
        {"id": "openai/gpt-6-astra", "name": "GPT-6 Astra", "created": 1700000000},
        {"id": "~openai/gpt-astra-latest", "name": "GPT Astra Latest", "created": 1700000000,
         "alias_target": {"slug": "openai/gpt-6-astra", "name": "OpenAI: GPT-6 Astra"}},
    ]}
    r = parse_models(feed, retrieved_at=datetime.now(UTC))
    assert [m.canonical_id for m in r.models] == ["openai/gpt-6-astra"]
    assert r.alias_entries == 1 and "1 alias pointer entries skipped" in r.describe()


def test_the_report_does_not_say_pro_ids_are_filtered():
    """#463: it said "filtered out as asked" while the poll inserted them. The
    report exists to show what the write does, so it must not say otherwise."""
    cat = [_m("anthropic/claude-opus-5"), _m("openai/gpt-6-astra-pro")]
    d = rd.compute_diff(cat, REG, frozenset(), base_id)
    text = rd.render(d, catalogue_size=2, registry_size=len(REG))
    assert "filtered out" not in text
    assert "`-pro` tier: 1" in text and "The poll inserts these too" in text
    assert "`openai/gpt-6-astra-pro`" in text
