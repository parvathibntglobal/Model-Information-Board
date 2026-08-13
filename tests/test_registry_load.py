"""Row building, without a database."""

from __future__ import annotations

from decimal import Decimal

from collect.ids import model_version_id
from collect.registry.load import _changed_fields, _prices_equal, model_row
from collect.registry.seed import load_seed_file


def _models():
    return load_seed_file().models


def test_every_row_is_stamped_as_a_seed():
    """The loader stamps provenance, so the startup assertion can find it."""
    for model in _models():
        assert model_row(model)["provenance"] == "seed"


def test_row_id_is_derived_from_the_canonical_id():
    model = _models()[0]
    assert model_row(model)["id"] == model_version_id(model.canonical_id)


def test_sources_are_serialised_as_url_and_date():
    by_id = {m.canonical_id: m for m in _models()}
    sources = model_row(by_id["openai/gpt-4.1-mini"])["sources"]
    assert sources["price_in"]["url"].startswith("https://")
    assert sources["price_in"]["retrieved_at"] == "2026-08-13"
    assert sources["price_in"]["provider_page"] is True


def test_a_retired_model_has_no_price_rather_than_an_unknown_one():
    """mistral-large-2411 retired 2025-03-30, so there is no current price."""
    by_id = {m.canonical_id: m for m in _models()}
    row = model_row(by_id["mistral/mistral-large-2411"])
    assert row["price_in"] is None
    assert row["lifecycle"] == "retired"
    assert row["retirement_date"] is not None


def test_slot_is_seed_bookkeeping_and_never_written():
    """`slot` records why a model is in the ten. It is not a column."""
    assert "slot" not in model_row(_models()[0])


def test_unchanged_row_reports_no_changes():
    row = model_row(_models()[0])
    assert _changed_fields(row, row) == []


def test_price_movement_is_detected_across_numeric_types():
    row = model_row(_models()[0])
    moved = dict(row, price_in=Decimal("99.0"))
    assert _changed_fields(row, moved) == ["price_in"]


def test_decimal_and_float_of_equal_value_are_not_a_change():
    before = {"price_in": Decimal("5.00"), "price_out": None, "price_cached_read": None}
    after = {"price_in": Decimal("5.0"), "price_out": None, "price_cached_read": None}
    assert _prices_equal(before, after)


def test_missing_price_differs_from_a_zero_price():
    before = {"price_in": None, "price_out": None, "price_cached_read": None}
    after = {"price_in": Decimal("0"), "price_out": None, "price_cached_read": None}
    assert not _prices_equal(before, after)
