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

#: Expected at AS_OF with an 18 month window. Three of the ten are outside.
EXPECTED_OUT = {
    "mistral/mistral-large-2411",  # 2024-11-18
    "deepseek/deepseek-v3",  # 2024-12-26
    "deepseek/deepseek-r1",  # 2025-01-20, 23 days the wrong side
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


def test_exactly_three_seeded_models_fall_outside_the_window():
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


def test_the_open_weight_slot_leaves_the_window():
    """The open-weight fixture is outside the window, so that slot is untested.

    A fixture problem, not a code one, recorded here so it cannot live only
    in a conversation. **This test is designed to fail once the fixture is
    fixed**, and its failure message says so, because the alternative is the
    next person reading a red test as a regression and reverting the fix.
    """
    open_weight = [m for m in _models() if m.slot == "open-weight"]
    assert len(open_weight) == 1, (
        f"expected exactly one open-weight fixture, found {len(open_weight)}: "
        f"{[m.canonical_id for m in open_weight]}"
    )
    model = open_weight[0]
    assert model_row(model, as_of=AS_OF)["in_window"] is False, (
        f"THIS IS NOT A REGRESSION. The open-weight fixture "
        f"{model.canonical_id} is now inside the trailing window, which means "
        f"sign-off item 6 has been actioned and contract/seed_models.yaml now "
        f"carries an open-weight model released after {BOUNDARY}. This test "
        f"existed only to keep that gap visible. Delete it."
    )


def test_window_report_keeps_unknown_release_dates_separate():
    """An unknown release date is a guess, not a fact, so it is counted apart."""
    report = window_report(_models(), as_of=AS_OF, months=18)
    assert set(report.out_of_window) == EXPECTED_OUT
    assert report.unknown == []  # every seeded model states a release date
    assert len(report.in_window) + len(report.out_of_window) == len(_models())


def test_an_unknown_release_date_is_counted_in_window_and_flagged():
    """Both at once: it does not hide the model, and it does not hide itself."""
    models = list(_models())
    models[0] = models[0].model_copy(update={"release_date": None})
    report = window_report(models, as_of=AS_OF, months=18)
    assert models[0].canonical_id in report.unknown
    assert models[0].canonical_id in report.in_window
