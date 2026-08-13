"""The trailing release window (FR-1).

Every date here is pinned. A test that calls `date.today()` to check a
window boundary passes today and fails in three months, which is worse than
no test at all.
"""

from __future__ import annotations

from datetime import date

import pytest

from collect.registry.load import model_row
from collect.registry.policy import DEFAULT_POLICY
from collect.registry.seed import load_seed_file
from collect.registry.window import in_window, window_report, window_start

#: The day the seed file was written, so the expected verdicts below are the
#: ones a reviewer can check by hand against `seed_models.yaml`.
AS_OF = date(2026, 8, 12)
BOUNDARY = date(2025, 2, 12)

#: Expected at AS_OF with an 18 month window.
#:
#: Two of the eleven are outside. `mistral-large-2411` used to be a third,
#: but the 2026-08-13 sourcing pass removed its release_date: Mistral does
#: not publish one, and an unsourced date is a claim with nothing behind it.
#: It is therefore counted in-window and flagged as unknown, which is the
#: safe direction under FR-1 and a visible gap rather than a quiet guess.
EXPECTED_OUT = {
    "deepseek/deepseek-v3",  # 2024-12-26
    "deepseek/deepseek-r1",  # 2025-01-20, 23 days the wrong side
}

#: Providers that publish no release date at all.
EXPECTED_UNKNOWN = {
    "anthropic/claude-opus-5",
    "anthropic/claude-sonnet-5",
    "anthropic/claude-haiku-4-5-20251001",
    "mistral/mistral-large-2411",
    "deepseek/deepseek-v4-flash",
}


def _models():
    return load_seed_file().models


# ── the boundary itself ───────────────────────────────────────────────────


def test_the_eighteen_month_boundary_is_where_we_think_it_is():
    assert window_start(AS_OF, 18) == BOUNDARY


def test_default_window_is_eighteen_months():
    assert DEFAULT_POLICY.in_window_months == 18


def test_month_arithmetic_clamps_to_the_shorter_month():
    """31 March minus one month is 28 February, not an invalid date."""
    assert window_start(date(2026, 3, 31), 1) == date(2026, 2, 28)
    assert window_start(date(2024, 3, 31), 1) == date(2024, 2, 29)  # leap year


def test_window_crosses_the_year_boundary():
    assert window_start(date(2026, 1, 15), 18) == date(2024, 7, 15)


def test_a_zero_month_window_starts_today():
    assert window_start(AS_OF, 0) == AS_OF


def test_negative_window_is_rejected():
    with pytest.raises(ValueError):
        window_start(AS_OF, -1)


# ── membership ────────────────────────────────────────────────────────────


def test_the_boundary_is_inclusive():
    assert in_window(BOUNDARY, as_of=AS_OF, months=18) is True
    assert in_window(date(2025, 2, 11), as_of=AS_OF, months=18) is False


def test_unknown_release_date_counts_as_in_window():
    """FR-1 makes a missing model the worse error, so absence does not hide it."""
    assert in_window(None, as_of=AS_OF, months=18) is True


def test_a_future_release_is_in_window():
    assert in_window(date(2027, 1, 1), as_of=AS_OF, months=18) is True


def test_window_length_is_honoured():
    r1 = date(2025, 1, 20)
    assert in_window(r1, as_of=AS_OF, months=18) is False
    assert in_window(r1, as_of=AS_OF, months=24) is True


# ── against the real seed file ────────────────────────────────────────────


def test_exactly_two_seeded_models_fall_outside_the_window():
    outside = {
        m.canonical_id
        for m in _models()
        if not in_window(m.release_date, as_of=AS_OF, months=18)
    }
    assert outside == EXPECTED_OUT


def test_model_row_computes_in_window_rather_than_asserting_it():
    rows = {m.canonical_id: model_row(m, as_of=AS_OF) for m in _models()}
    assert {cid for cid, row in rows.items() if not row["in_window"]} == EXPECTED_OUT


def test_in_window_moves_with_as_of():
    """The value is a function of the date, which is why cron recomputes it."""
    r1 = next(m for m in _models() if m.canonical_id == "deepseek/deepseek-r1")
    assert model_row(r1, as_of=date(2026, 7, 1))["in_window"] is True
    assert model_row(r1, as_of=AS_OF)["in_window"] is False


def test_the_open_weight_slot_is_now_covered():
    """Sign-off item 8, applied.

    `deepseek-v3` fell outside the window, so the open-weight slot existed
    but tested nothing. `mistral-large-3` is Apache 2.0, released after the
    boundary, and the direct successor to the retired `mistral-large-2411`.
    """
    open_weight = [m for m in _models() if m.slot == "open-weight"]
    ids = {m.canonical_id for m in open_weight}
    assert ids == {"mistral/mistral-large-3", "deepseek/deepseek-v3"}

    live = [m for m in open_weight if model_row(m, as_of=AS_OF)["in_window"]]
    assert [m.canonical_id for m in live] == ["mistral/mistral-large-3"]


def test_window_report_keeps_unknown_release_dates_separate():
    """An unknown release date is a guess, not a fact, so it is counted apart.

    Five of the eleven now have none, because Anthropic, Mistral and DeepSeek
    do not publish release dates for these models and the sourcing pass
    removed the unsourced values rather than keeping them.
    """
    report = window_report(_models(), as_of=AS_OF, months=18)
    assert set(report.out_of_window) == EXPECTED_OUT
    assert set(report.unknown) == EXPECTED_UNKNOWN
    assert len(report.in_window) + len(report.out_of_window) == len(_models())


def test_unknown_release_dates_are_counted_in_window():
    """FR-1 makes a missing model the worse error, so absence does not hide it."""
    report = window_report(_models(), as_of=AS_OF, months=18)
    assert set(report.in_window) >= EXPECTED_UNKNOWN


def test_an_unknown_release_date_is_counted_in_window_and_flagged():
    """Both at once: it does not hide the model, and it does not hide itself."""
    models = list(_models())
    models[0] = models[0].model_copy(update={"release_date": None})
    report = window_report(models, as_of=AS_OF, months=18)
    assert models[0].canonical_id in report.unknown
    assert models[0].canonical_id in report.in_window
