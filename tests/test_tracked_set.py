"""The tracked set: which models get swept, and what the count was drawn from.

The load-bearing tests are the ones about `None`. A model the corpus never
observed must not sort, rank or read as a model observed zero times — 268 of
the 340 registry models are in that state, and a `0` would make "we did not
look" indistinguishable from "we looked and found nothing" (rule 6).

The second group is rule 7: the ambiguous surfaces carry 1,530 mentions that
several models could be meant by, and attributing them would invent the
attribution the extract refuses.
"""

from __future__ import annotations

from datetime import date

import pytest

from collect.registry.tracked import (
    BY_LAUNCH_WINDOW,
    BY_MENTIONS,
    TrackedSetPolicy,
    attributable,
    distribution,
    select,
    summarise,
)

AS_OF = date(2026, 8, 18)

#: Real rows from `fixtures/openrouter/observed-surfaces.json`, one of each verdict.
EXTRACT = [
    {"surface": "opus 5", "mentions": 1445, "documents": 281,
     "verdict": "attested-gap", "models": ["anthropic/claude-opus-5"]},
    {"surface": "opus-5", "mentions": 78, "documents": 39,
     "verdict": "attested-gap", "models": ["anthropic/claude-opus-5"]},
    {"surface": "gemini 2.5 flash", "mentions": 406, "documents": 120,
     "verdict": "resolved", "models": ["google/gemini-2.5-flash"]},
    {"surface": "claude", "mentions": 8149, "documents": 2100,
     "verdict": "attested-gap-ambiguous",
     "models": ["anthropic/claude-opus-5", "anthropic/claude-sonnet-5"]},
    {"surface": "llamacpp", "mentions": 12, "documents": 9,
     "verdict": "unknown-model", "models": []},
]

MODELS = [
    ("anthropic/claude-opus-5", "Anthropic: Claude Opus 5", date(2026, 7, 24)),
    ("google/gemini-2.5-flash", "Google: Gemini 2.5 Flash", date(2025, 4, 17)),
    ("qwen/qwen3.8-27b", "Qwen: Qwen3.8 27B", date(2026, 8, 14)),
    ("mistralai/mistral-large-3", "Mistral: Large 3", date(2025, 11, 2)),
]


def _policy(floor: int = 20, window: int = 30) -> TrackedSetPolicy:
    return TrackedSetPolicy(mention_floor=floor, launch_window_days=window)


# ── attribution: only surfaces naming exactly one model ──────────────────


def test_only_single_model_verdicts_are_attributed():
    observed = attributable(EXTRACT)
    assert set(observed) == {"anthropic/claude-opus-5", "google/gemini-2.5-flash"}


def test_an_ambiguous_surface_is_excluded_rather_than_assigned():
    """8,149 mentions of `claude`, and no model may claim them.

    Taking `models[0]` would hand every one of them to whichever id sorted
    first — the largest single misattribution available in this extract.
    """
    observed = attributable(EXTRACT)
    assert sum(a.mentions for a in observed["anthropic/claude-opus-5"]) == 1523
    assert all(a.surface != "claude" for a in observed["anthropic/claude-opus-5"])


def test_an_unknown_model_surface_names_nothing_and_is_dropped():
    observed = attributable(EXTRACT)
    assert not any("llamacpp" in (a.surface for a in v) for v in observed.values())


def test_surfaces_are_ordered_by_mentions_so_the_primary_is_the_common_form():
    observed = attributable(EXTRACT)
    assert [a.surface for a in observed["anthropic/claude-opus-5"]] == ["opus 5", "opus-5"]


# ── rule 6: unmeasured is not zero ───────────────────────────────────────


def test_an_unobserved_model_carries_none_mentions_not_zero():
    """The whole point. `mistral-large-3` is absent from the extract.

    The detector needs a family word plus a version token and `large` is not a
    family word, so it could not have seen this model written. That is recall
    unmeasured, and `0` would assert a count nobody took.
    """
    selection = select(MODELS, attributable(EXTRACT), policy=_policy(), as_of=AS_OF)
    absent = next(
        m
        for m in selection.tracked + selection.rejected
        if m.canonical_id == "mistralai/mistral-large-3"
    )
    assert absent.mentions is None
    assert absent.surfaces is None
    assert not absent.measured


def test_an_unmeasured_model_is_never_seated_by_count():
    """It has no count, so no floor can admit it. Only the rule can."""
    selection = select(MODELS, attributable(EXTRACT), policy=_policy(), as_of=AS_OF)
    for model in selection.tracked:
        if not model.measured:
            assert model.grounds == (BY_LAUNCH_WINDOW,)


def test_a_floor_of_zero_is_refused():
    """It would seat all 340 by count, recording evidence that does not exist."""
    with pytest.raises(ValueError, match="at least 1"):
        TrackedSetPolicy(mention_floor=0, launch_window_days=30)


def test_the_surface_median_omits_unmeasured_models():
    """A median over 0s from models nobody looked at is a coverage figure
    wearing the clothes of a usage figure."""
    selection = select(MODELS, attributable(EXTRACT), policy=_policy(), as_of=AS_OF)
    assert selection.surface_sizes == [1, 2]  # flash 1, opus-5 2 — qwen omitted


# ── the two grounds ──────────────────────────────────────────────────────


def test_a_new_model_nobody_has_discussed_is_seated_by_the_launch_window():
    """`qwen3.8-27b`, released four days before `as_of`, zero mentions.

    The case the rule exists for: a model has no discussion history because it
    has not existed long enough to have one.
    """
    selection = select(MODELS, attributable(EXTRACT), policy=_policy(), as_of=AS_OF)
    qwen = next(m for m in selection.tracked if m.canonical_id == "qwen/qwen3.8-27b")
    assert qwen.grounds == (BY_LAUNCH_WINDOW,)
    assert qwen.mentions is None


def test_an_old_model_people_still_discuss_is_seated_by_mentions():
    """`gemini-2.5-flash` is 16 months old and outside every recent window.

    A date sort would drop it. That is why the ranking is by mentions.
    """
    selection = select(MODELS, attributable(EXTRACT), policy=_policy(), as_of=AS_OF)
    flash = next(
        m for m in selection.tracked if m.canonical_id == "google/gemini-2.5-flash"
    )
    assert flash.grounds == (BY_MENTIONS,)


def test_both_grounds_are_recorded_when_both_apply():
    """`claude-opus-5` is 25 days old AND the most-discussed model in the corpus.

    Kept as two grounds rather than one boolean, so removing either rule shows
    exactly which models it would cost.
    """
    selection = select(MODELS, attributable(EXTRACT), policy=_policy(), as_of=AS_OF)
    opus = next(
        m for m in selection.tracked if m.canonical_id == "anthropic/claude-opus-5"
    )
    assert opus.grounds == (BY_MENTIONS, BY_LAUNCH_WINDOW)


def test_a_model_below_the_floor_and_outside_the_window_is_rejected():
    selection = select(MODELS, attributable(EXTRACT), policy=_policy(floor=500),
                       as_of=AS_OF)
    rejected = {m.canonical_id for m in selection.rejected}
    assert "google/gemini-2.5-flash" in rejected  # 406 mentions, below 500
    assert "anthropic/claude-opus-5" not in rejected  # still in the window


def test_a_model_that_has_not_launched_is_not_in_its_launch_window():
    """An age of -43 days is trivially "within 30" if only the upper bound is
    checked, so a mis-parsed date would seat a model that does not exist."""
    models = [("vendor/tomorrow", "Tomorrow", date(2026, 9, 30))]
    selection = select(models, {}, policy=_policy(), as_of=AS_OF)
    assert not selection.tracked


def test_a_future_dated_row_is_listed_rather_than_silently_excluded():
    """A poller finding. Excluded and unmentioned is the failure, not excluded."""
    models = [("vendor/tomorrow", "Tomorrow", date(2026, 9, 30))]
    selection = select(models, {}, policy=_policy(), as_of=AS_OF)
    assert [m.canonical_id for m in selection.future_dated] == ["vendor/tomorrow"]


def test_an_absent_release_date_never_enters_by_the_window():
    """Rule 6 again: an unknown date is not a recent one."""
    models = [("vendor/undated", "Undated", None)]
    selection = select(models, {}, policy=_policy(), as_of=AS_OF)
    assert not selection.tracked
    assert selection.rejected[0].grounds == ()


# ── ordering and reporting ───────────────────────────────────────────────


def test_the_order_is_stable_across_runs():
    """Two runs of the same inputs must diff to nothing, or the artifact churns."""
    observed = attributable(EXTRACT)
    first = select(MODELS, observed, policy=_policy(), as_of=AS_OF)
    second = select(list(reversed(MODELS)), observed, policy=_policy(), as_of=AS_OF)
    assert [m.canonical_id for m in first.tracked] == [
        m.canonical_id for m in second.tracked
    ]


def test_the_summary_says_unmeasured_rather_than_zero():
    selection = select(MODELS, attributable(EXTRACT), policy=_policy(), as_of=AS_OF)
    text = summarise(selection)
    assert "recall unmeasured, not zero" in text
    assert "by launch window alone" in text


def test_the_distribution_states_its_platform_and_denominator():
    """Rule 7: a figure that travels without its population is not evidence."""
    selection = select(
        MODELS, attributable(EXTRACT), policy=_policy(), as_of=AS_OF,
        basis={"platform": "Reddit", "documents": 5546},
    )
    text = distribution(selection)
    assert "Reddit" in text
    assert "5546 documents" in text


def test_the_distribution_says_so_when_nothing_was_measured():
    """No extract means the floor cannot be derived — not that it is zero."""
    selection = select(MODELS, {}, policy=_policy(), as_of=AS_OF)
    assert "cannot be derived" in distribution(selection)
