"""Bracketed display names resolve by either half; a released model wins over its
`-preview` row, and only that exact pair (ruled on #602, 2026-11-09).

"Google: Nano Banana 2 (Gemini 3.1 Flash Image)" is written as either half and
never with the brackets, so "Nano Banana 2" resolved to nothing and its claims
were held - while the registry held the model. The preview row carries the same
display name, and the resolver refuses a name with two owners, so the split alone
was not enough: the ruling adds that when the two owners' ids differ by exactly
`-preview`, the released row wins. Any other shared name is still refused.
No database: the registry rows are given.
"""
from __future__ import annotations

from collect.surface_resolver import RegistrySurfaceResolver


class _Conn:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, sql, params=None):
        rows = self._rows
        return type("R", (), {"fetchall": lambda _self: rows})()


REGISTRY = [
    ("google/gemini-3.1-flash-image", "Google: Nano Banana 2 (Gemini 3.1 Flash Image)", "mv_nb2"),
    ("google/gemini-3.1-flash-image-preview",
     "Google: Nano Banana 2 (Gemini 3.1 Flash Image Preview)", "mv_nb2_preview"),
    ("google/gemini-3.1-flash-lite-image",
     "Google: Nano Banana 2 Lite (Gemini 3.1 Flash Lite Image)", "mv_lite"),
    # A shared name that is NOT a `-preview` pair: a dated snapshot.
    ("qwen/qwen3.8-max", "Qwen: Qwen3.8 Max", "mv_q"),
    ("qwen/qwen3.8-max-0902", "Qwen: Qwen3.8 Max", "mv_q_0902"),
]


def _resolver():
    return RegistrySurfaceResolver.from_connection(_Conn(REGISTRY))


def test_the_everyday_half_of_a_bracketed_name_resolves():
    assert _resolver()("Gemini 3.1 Flash Image") == "mv_nb2"


def test_a_released_model_wins_over_its_preview_row():
    r = _resolver()
    assert r("Nano Banana 2") == "mv_nb2"
    assert r.report.by_preview_rule == {"Nano Banana 2": "google/gemini-3.1-flash-image"}


def test_the_longer_name_still_files_under_its_own_row():
    """The #612 review's point 14: "Nano Banana 2 Lite" must not file under
    Nano Banana 2 with "Lite" read as a qualifier."""
    assert _resolver()("Nano Banana 2 Lite") == "mv_lite"


def test_a_shared_name_that_is_not_a_preview_pair_is_still_refused():
    r = _resolver()
    assert r("Qwen3.8 Max") is None
    assert "Qwen3.8 Max" in r.report.ambiguous
    assert r.report.by_preview_rule == {}
