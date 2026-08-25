"""#33 Q3: the tracked set cannot outrun the decay curve, and it fails loudly.

A 340-model rotation takes ~31 nights against a 30-day fast half-life, so a full
pass never catches up — and no timestamp fixes that; only a smaller set does.
`assert_staleness_within_bound` makes that a structural refusal, like
`assert_within_budget`: the model count falls out of a defended bound rather than
being chosen, and adding a model either fits or fails.
"""

from __future__ import annotations

import pytest

from collect.adapters.queries.cadence import (
    StalenessBoundError,
    _load_rotation,
    assert_staleness_within_bound,
    implied_staleness_days,
)

CAP = 900  # sweep_budget.daily.max_requests


class TestTheMathMatchesTheIssue:
    """The numbers #33 argued from, pinned so the config cannot drift silently."""

    @pytest.mark.parametrize("models,nights", [(11, 1), (55, 5), (77, 7), (78, 8), (340, 31)])
    def test_rotation_nights(self, models, nights):
        _, rpm = _load_rotation()
        got = implied_staleness_days(models, daily_request_cap=CAP, requests_per_model=rpm)
        assert got == nights

    def test_zero_models_is_zero_staleness_not_a_division(self):
        assert implied_staleness_days(0, daily_request_cap=CAP, requests_per_model=81.45) == 0

    def test_a_model_costlier_than_a_whole_night_is_a_budget_error(self):
        with pytest.raises(StalenessBoundError, match="no model fits in a night"):
            implied_staleness_days(5, daily_request_cap=100, requests_per_model=200)


class TestTheBoundIsStructural:
    def test_the_current_bound_fits_77_and_refuses_78(self):
        assert_staleness_within_bound(77)                       # 7 nights, at the bound
        with pytest.raises(StalenessBoundError) as caught:
            assert_staleness_within_bound(78)                   # 8 nights, over it
        msg = str(caught.value)
        assert "78 models" in msg and "8-night" in msg
        assert "fits 77 models" in msg, "the refusal names what would fit"

    def test_the_refusal_names_the_decay_reason_not_just_the_number(self):
        with pytest.raises(StalenessBoundError, match="30-day fast half-life"):
            assert_staleness_within_bound(200)

    def test_todays_small_tracked_set_is_well_within_bound(self):
        # 7-11 models today: nowhere near the ceiling, so this never fires in
        # normal operation — it is a guard on growth, not a daily obstacle.
        assert_staleness_within_bound(11)

    def test_an_injected_bound_overrides_the_file(self):
        # A deliberate looser bound is allowed — it is a decision, made in the
        # open — so the assertion honours an override rather than hardcoding 7.
        assert_staleness_within_bound(150, rotation=(14.0, 81.45))  # 14-day bound fits ~154


class TestTheConfigIsPresent:
    def test_the_rotation_block_exists_and_is_read(self):
        bound, rpm = _load_rotation()
        assert bound == 7.0
        assert rpm == 81.45
