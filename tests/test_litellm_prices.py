"""LiteLLM as a FALLBACK price source, in its own unit (#602 items 3 and 4).

No database and no network: the contract is the real file, the price list is a
small dict in LiteLLM's shape. These pin the refusals Anooj asked for on #602 -
no nearest-name mapping, an unmapped id gets no price and is named, a figure is
only written where OpenRouter publishes none - plus the ones that keep a wrong
figure out: the wrong mode, an unknown cost field, a zero.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from collect.registry import litellm
from collect.registry.litellm import LitellmContract, load_contract, rows_from
from judge.catalog import _variant_order

AT = datetime(2026, 11, 5, tzinfo=UTC)

CONTRACT = LitellmContract(
    source_url="https://example.invalid/prices.json",
    fields={
        "output_cost_per_second": ("second_of_video", "output"),
        "input_cost_per_image": ("image", "input"),
    },
    modes=frozenset({"video_generation"}),
    models={
        "minimax/hailuo-3-max": "minimax/MiniMax-H3-Max",
        "google/veo-3.1": "gemini/veo-3.1-generate-001",
        "acme/gone": "acme/removed-key",
        "acme/music": "acme/music-1",
    },
    excluded={"google/lyria-3-pro-preview": "priced per image"},
)

PRICES = {
    "minimax/MiniMax-H3-Max": {
        "mode": "video_generation",
        "output_cost_per_second": 0.08,
        "output_cost_per_second_480p": 0.05,
        "output_cost_per_second_768p": 0.08,
        "input_cost_per_image": 0.074,
        "input_cost_per_token": 0,
        "output_cost_per_pixel": 0.0001,
    },
    "gemini/veo-3.1-generate-001": {"mode": "video_generation", "output_cost_per_second": 0.4,
                                    "input_cost_per_image": 0},
    # A NEAR NAME. If the map ever falls back to similarity, `acme/gone` lands here.
    "acme/removed-key-v2": {"mode": "video_generation", "output_cost_per_second": 9.0},
    "acme/music-1": {"mode": "chat", "output_cost_per_image": 0.08},
}


def _run(**kw):
    args = dict(
        unpriced={"minimax/hailuo-3-max", "google/veo-3.1", "acme/gone", "acme/music",
                  "kwaivgi/kling-v3.0-pro", "google/lyria-3-pro-preview"},
        priced=set(),
        retrieved_at=AT,
    )
    args.update(kw)
    return rows_from(PRICES, CONTRACT, **args)


def test_each_tier_is_its_own_row_in_its_own_unit():
    rep = _run()
    h3 = {(r.unit, r.direction, r.variant): r.usd for r in rep.rows
          if r.canonical_id == "minimax/hailuo-3-max"}
    assert h3 == {
        ("second_of_video", "output", "default"): 0.08,
        ("second_of_video", "output", "480p"): 0.05,
        ("second_of_video", "output", "768p"): 0.08,
        ("image", "input", "default"): 0.074,
    }
    assert {r.source_key for r in rep.rows if r.canonical_id == "minimax/hailuo-3-max"} == {
        "minimax/MiniMax-H3-Max"}
    assert all(r.retrieved_at == AT and r.source == "litellm" for r in rep.rows)


def test_a_missing_key_is_named_and_never_replaced_by_a_near_one():
    rep = _run()
    assert rep.missing_keys["acme/gone"] == "acme/removed-key"
    assert not [r for r in rep.rows if r.canonical_id == "acme/gone"]


def test_the_wrong_mode_is_refused_whole():
    """Lyria's shape: a music model LiteLLM prices per image."""
    rep = _run()
    assert "acme/music" in rep.wrong_mode
    assert not [r for r in rep.rows if r.canonical_id == "acme/music"]


def test_unknown_cost_fields_and_zeros_are_reported_not_stored():
    rep = _run()
    # A field with no unit is unread whatever its value; a zero on a field the
    # contract reads is a zero, and neither is stored.
    assert rep.unread_fields["minimax/hailuo-3-max"] == ["input_cost_per_token",
                                                         "output_cost_per_pixel"]
    assert rep.zero_fields == {"google/veo-3.1": ["input_cost_per_image"]}


def test_an_unpriced_model_outside_the_map_is_named():
    rep = _run()
    assert rep.unmapped == ["kwaivgi/kling-v3.0-pro"]
    assert "google/lyria-3-pro-preview" in rep.excluded
    rep.summary().encode("cp1252")  # printed by a script on a Windows console


def test_a_model_openrouter_prices_gets_no_fallback():
    rep = _run(unpriced={"minimax/hailuo-3-max"}, priced={"google/veo-3.1"})
    assert rep.skipped_priced == ["google/veo-3.1"]
    assert {r.canonical_id for r in rep.rows} == {"minimax/hailuo-3-max"}


def test_the_contract_file_loads_and_maps_no_id_twice():
    c = load_contract()
    assert c.source_url.startswith("https://raw.githubusercontent.com/BerriAI/litellm/")
    assert not set(c.models) & set(c.excluded)
    assert len(set(c.models.values())) == len(c.models), "one LiteLLM key per model"
    assert "video_generation" in c.modes


def test_a_contract_missing_a_key_raises(tmp_path):
    p = tmp_path / "litellm_prices.yaml"
    p.write_text("version: 1\nsource_url: x\nfields: {}\nmodels: {}\n", encoding="utf-8")
    with pytest.raises(litellm.LitellmContractError):
        load_contract(p)


def test_tiers_sort_default_first_then_by_size():
    tiers = ["4k", "1080p", "default", "480p", "2k", "720p"]
    assert sorted(tiers, key=_variant_order) == ["default", "480p", "720p", "1080p", "2k", "4k"]
