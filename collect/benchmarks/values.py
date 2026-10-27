"""Stages 4-6 for one value: normalise and check it (doc 7, 8, 20.1 L4).

The metric is never guessed here: every mapping states it (sources.yaml), so
classification is the config's. A value that fails is REJECTED with a reason
and its raw text; it is never written.

    parse_score("88.7%", "percent")   -> 88.7
    parse_score("0.887", "fraction")  -> 88.7
    parse_score("88.7 ± 1.2", ...)    -> 88.7
    parse_score("92.1%, $0.48/task")  -> 92.1   (the one number marked %)
    parse_score("$1.20 / 3.4")        -> REJECTED: two numbers, none marked
    parse_score("v2: 45.1")           -> 45.1   ("v2", "GPT-5" are names, not numbers)
    parse_rank("T-3")                 -> rank 3, tied
    parse_rank("3–5")                 -> rank 3, rank_high 5
    "—", "n/a", ""                    -> EMPTY (no value, not an error)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

EMPTY_TOKENS = {"", "-", "—", "–", "n/a", "na", "null", "none", "?", "tbd", "nan"}


@dataclass
class Value:
    value: float | None = None
    rank_high: int | None = None
    tied: bool = False
    empty: bool = False
    error: str | None = None  # invalid_value reason, with the raw text


def _clean(text: str) -> str:
    return str(text or "").strip().lower().replace(",", "").replace(" ", "")


# A number standing on its own: not the "5" of "GPT-5" or the "2" of "v2".
_STANDALONE = re.compile(r"(?<![a-z0-9.\-])-?\d+(?:\.\d+)?(?:e-?\d+)?(?P<pct>\s*%)?", re.I)
_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")


def _the_number(text: str) -> tuple[float | None, str | None]:
    """The one number a cell states, or why there is not exactly one.

    Taking the FIRST number was wrong (PR #573 review): "$1.20 / 45.1%" stored
    1.2 and "v2: 45.1" stored 2.0, both inside 0-100. An uncertainty after "±"
    is not a second value; a number glued to a name ("GPT-5") is not one at
    all. Of several numbers, the one marked "%" is the score; otherwise the
    cell is refused rather than guessed.
    """
    t = _THOUSANDS.sub("", str(text or "")).split("±")[0].split("+/-")[0]
    found = list(_STANDALONE.finditer(t.lower()))
    if not found:
        return None, f"invalid_value: no number in {text!r}"
    if len(found) > 1:
        marked = [m for m in found if m.group("pct")]
        if len(marked) != 1:
            return None, f"invalid_value: {text!r} states more than one number"
        found = marked
    return float(found[0].group(0).replace("%", "").strip()), None


def parse_score(text: str, scale: str) -> Value:
    if _clean(text) in EMPTY_TOKENS:
        return Value(empty=True)
    n, error = _the_number(text)
    if error:
        return Value(error=error)
    if scale == "fraction":
        if not 0 <= n <= 1:
            return Value(error=f"invalid_value: {text!r} is outside 0-1 for a fraction")
        n *= 100
    if not 0 <= n <= 100:
        return Value(error=f"invalid_value: {text!r} is outside 0-100")
    return Value(value=round(n, 2))


def parse_rating(text: str, rating_range: tuple[int, int]) -> Value:
    if _clean(text) in EMPTY_TOKENS:
        return Value(empty=True)
    value, error = _the_number(text)
    if error:
        return Value(error=error)
    n = round(value)
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
