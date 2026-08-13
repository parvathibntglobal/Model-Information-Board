"""The trailing release window (FR-1).

`in_window` is a stored boolean that is a function of today's date, so it is
wrong the day after it is written and has to be recomputed on a schedule.
Everything here is pure and takes `as_of` explicitly: a function that reads
the clock cannot be tested against a fixed boundary, and this one decides
which models the answer path is allowed to see.

The window length is `in_window_months` in the registry policy, proposed for
`contract/registry.yaml`. It is a threshold the code reads at runtime, so
rule 5 puts it in versioned config rather than here.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date

from collect.registry.models import SeedModel
from collect.registry.policy import DEFAULT_POLICY


def window_start(as_of: date, months: int) -> date:
    """The oldest release date still inside the window on `as_of`.

    Calendar months, not 30-day approximations, and clamped to the length of
    the target month so 31 March minus one month is 28 February rather than
    an invalid date.
    """
    if months < 0:
        raise ValueError(f"window length must not be negative: {months}")
    total = as_of.year * 12 + (as_of.month - 1) - months
    year, month_index = divmod(total, 12)
    month = month_index + 1
    day = min(as_of.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def in_window(
    release_date: date | None,
    *,
    as_of: date,
    months: int | None = None,
) -> bool:
    """Is a model inside the trailing window on `as_of`?

    Inclusive at the boundary: a model released exactly `months` ago is still
    in. An unknown `release_date` counts as in, because FR-1 makes roster
    completeness the premise and a model missing from the board reads as a
    model that does not exist. That is the less damaging error, but it is
    still an error, and an unknown release date belongs on the coverage page.
    """
    if release_date is None:
        return True
    months = DEFAULT_POLICY.in_window_months if months is None else months
    return release_date >= window_start(as_of, months)


@dataclass(frozen=True)
class WindowReport:
    """What the window decided, for the coverage surface to read.

    `unknown` is the one that matters. A model with no release date is
    counted as in-window, which is a guess made in the safe direction rather
    than a fact. If the only place that guess is recorded is a docstring, the
    coverage page has nothing to show and the gap is invisible.
    """

    in_window: list[str]
    out_of_window: list[str]
    unknown: list[str]


def window_report(
    models: list[SeedModel],
    *,
    as_of: date,
    months: int | None = None,
) -> WindowReport:
    """Split models by window membership, keeping unknowns separate."""
    inside: list[str] = []
    outside: list[str] = []
    unknown: list[str] = []
    for model in models:
        if model.release_date is None:
            unknown.append(model.canonical_id)
            inside.append(model.canonical_id)
        elif in_window(model.release_date, as_of=as_of, months=months):
            inside.append(model.canonical_id)
        else:
            outside.append(model.canonical_id)
    return WindowReport(in_window=inside, out_of_window=outside, unknown=unknown)
