"""Stages 4-6 for one value: normalise and check it (doc 7, 8, 20.1 L4).

The metric is never guessed here: every mapping states it (sources.yaml), so
classification is the config's. A value that fails is REJECTED with a reason
and its raw text; it is never written.

    parse_score("88.7%", "percent")   -> 88.7
    parse_score("0.887", "fraction")  -> 88.7
    parse_score("88.7 ± 1.2", ...)    -> 88.7
    parse_rank("T-3")                 -> rank 3, tied
    parse_rank("3–5")                 -> rank 3, rank_high 5
    "—", "n/a", ""                    -> EMPTY (no value, not an error)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

EMPTY_TOKENS = {"", "-", "—", "–", "n/a", "na", "null", "none", "?", "tbd", "nan"}
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?(?:e-?\d+)?", re.I)


@dataclass
class Value:
    value: float | None = None
    rank_high: int | None = None
    tied: bool = False
    empty: bool = False
    error: str | None = None  # invalid_value reason, with the raw text


def _clean(text: str) -> str:
    return str(text or "").strip().lower().replace(",", "").replace(" ", "")


def parse_score(text: str, scale: str) -> Value:
    t = _clean(text)
    if t in EMPTY_TOKENS:
        return Value(empty=True)
    found = _NUMBER.search(t)
    if not found:
        return Value(error=f"invalid_value: no number in {text!r}")
    n = float(found.group(0))
    if scale == "fraction":
        if not 0 <= n <= 1:
            return Value(error=f"invalid_value: {text!r} is outside 0-1 for a fraction")
        n *= 100
    if not 0 <= n <= 100:
        return Value(error=f"invalid_value: {text!r} is outside 0-100")
    return Value(value=round(n, 2))


def parse_rating(text: str, rating_range: tuple[int, int]) -> Value:
    t = _clean(text)
    if t in EMPTY_TOKENS:
        return Value(empty=True)
    found = _NUMBER.search(t)
    if not found:
        return Value(error=f"invalid_value: no number in {text!r}")
    n = round(float(found.group(0)))
    low, high = rating_range
    if not low <= n <= high:
        return Value(error=f"invalid_value: rating {text!r} is outside {low}-{high}")
    return Value(value=float(n))


_RANGE = re.compile(r"^(\d+)\s*(?:–|—|-|to)\s*(\d+)$")
_TIED = re.compile(r"^(?:t-?|=)(\d+)$|^(\d+)(?:=|t)$")
_PLAIN = re.compile(r"^(?:#|rank)?(\d+)(?:st|nd|rd|th)?$")


def parse_rank(text: str, out_of: int | None) -> Value:
    t = str(text or "").strip().lower().replace(" ", "")
    if t in EMPTY_TOKENS:
        return Value(empty=True)
    rank = high = None
    tied = False
    if m := _RANGE.match(t):
        rank, high = int(m.group(1)), int(m.group(2))
    elif m := _TIED.match(t):
        rank = int(m.group(1) or m.group(2))
        tied = True
    elif m := _PLAIN.match(t):
        rank = int(m.group(1))
    if rank is None:
        return Value(error=f"invalid_value: {text!r} is not a rank")
    high = high if high is not None else rank
    if rank < 1:
        return Value(error=f"invalid_value: rank {text!r} is below 1")
    if high < rank:
        return Value(error=f"invalid_value: rank range {text!r} runs backwards")
    if out_of is not None and high > out_of:
        return Value(error=f"invalid_value: rank {text!r} is beyond the board's {out_of} entries")
    return Value(value=float(rank), rank_high=high, tied=tied)
