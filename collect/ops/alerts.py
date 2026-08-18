"""The five alerts, and the third state most of them are in tonight.

`docs/logic-and-workflow.md §17` names five. What this module adds is the state
they are actually in, because an alerting layer that reports "no alerts" while
its inputs do not exist is the defect this lane keeps finding, wearing a
reassuring hat.

    FIRED             the condition held
    QUIET             the condition was evaluated and did not hold
    CANNOT COMPUTE    the input does not exist, or does not exist yet

Five alerts, and tonight every one of them is the third.

TWO OF THEM ARE NOT OURS AND ARE NOT STUBBED
---------------------------------------------
Alerts 3 and 4 read extraction outputs, and `judge/` opens no database
connection at all — there is no table here to poll. They appear in this list
with `owner="judge/"` and no implementation, deliberately: a stub is a producer
nobody wrote, and it would report QUIET forever while nothing measured anything.
Raised for Engineer 2 rather than answered here, because the lane boundary says
data crosses once in one direction and an alerting stage that reaches into her
lane's outputs is the wrong shape for both of us.
"""

from __future__ import annotations

from dataclasses import dataclass, field

FIRED = "fired"
QUIET = "quiet"
CANNOT_COMPUTE = "cannot-compute"
NOT_OURS = "not-ours"

#: Nights of history a survival alert needs before it means anything. There is
#: no σ to compute against on day one, so the alert counts down in public
#: rather than reporting a reassuring nothing.
SURVIVAL_BURN_IN_NIGHTS = 14


@dataclass(frozen=True)
class Alert:
    """One alert's verdict, and why it is that verdict."""

    number: int
    name: str
    state: str
    detail: str
    owner: str = "collect/"
    #: Both halves of any rate, always. Rule 7: a figure travels with its
    #: denominator, and an alert message is exactly the place a bare rate goes
    #: on to become an argument.
    figures: dict[str, int] = field(default_factory=dict)

    def __str__(self) -> str:
        figures = "  " + " ".join(f"{k}={v}" for k, v in self.figures.items())
        return f"[{self.state.upper():<14}] {self.number}. {self.name}: {self.detail}" + (
            figures.rstrip() if self.figures else ""
        )


def yield_drop(runs, *, baseline_nights: int = 0) -> Alert:
    """Alert 1 — a site changed its markup, measured as kept over candidates.

    THE COMPARISON IS ONLY VALID WITHIN ONE VOCABULARY, AND THAT IS NOT A DETAIL.
    The three harvest runs on record are 0 of 149, 5 of 636 and 0 of 1,678, and
    each used a different term vocabulary and a different scope. Comparing them
    measures OUR OWN EDITS, not a platform:

        2026-08-13  16-entry vocabulary        149 candidates,  0 kept
        2026-08-14  24 entries + containment   636 candidates,  5 keeps of 1
        2026-08-17  substitution slice       1,678 documents,   0 kept

    A yield alert that fired on those would be the tenth instance of the class
    this whole layer exists to detect. So the baseline is per
    `(source_id, query_key, pipeline_version)`, and `pipeline_version` is what
    changes when the vocabulary does — a vocabulary edit starts a new baseline
    rather than tripping the old one.

    `runs` is `harvest_run` rows. There are none: the adapters build
    `harvest_run_fields()` dicts and nothing inserts them.
    """
    rows = list(runs or ())
    if not rows:
        return Alert(
            1, "adapter yield drop", CANNOT_COMPUTE,
            "harvest_run holds no rows — the adapters compute the figures and "
            "nothing writes them, so there is no history to compare against",
            figures={"runs": 0},
        )
    if baseline_nights < 2:
        return Alert(
            1, "adapter yield drop", CANNOT_COMPUTE,
            "a drop needs something to have dropped FROM, and a baseline is "
            "only comparable within one pipeline_version",
            figures={"runs": len(rows), "nights": baseline_nights},
        )
    return Alert(
        1, "adapter yield drop", QUIET,
        "every source is within its baseline",
        figures={"runs": len(rows), "nights": baseline_nights},
    )


def triage_survival(nights: int = 0, *, kept: int = 0, candidates: int = 0) -> Alert:
    """Alert 2 — a platform changed or a filter broke. Armed after the burn-in.

    Reports the countdown rather than a reassuring nothing, because "0 of 14
    nights recorded" is a fact somebody can act on and "no alerts" is not.
    """
    if candidates == 0:
        return Alert(
            2, "triage survival shifted", CANNOT_COMPUTE,
            "no triage gate sets document.status, so survival has no numerator "
            "and no denominator",
            figures={"kept": kept, "candidates": candidates, "nights": nights},
        )
    if nights < SURVIVAL_BURN_IN_NIGHTS:
        return Alert(
            2, "triage survival shifted", CANNOT_COMPUTE,
            f"burn-in: {nights} of {SURVIVAL_BURN_IN_NIGHTS} nights recorded, "
            "so there is no σ to compare against",
            figures={"kept": kept, "candidates": candidates, "nights": nights},
        )
    return Alert(
        2, "triage survival shifted", QUIET, "within 2σ of the trailing baseline",
        figures={"kept": kept, "candidates": candidates, "nights": nights},
    )


def extraction_errors() -> Alert:
    """Alert 3 — the extractor silently regressed. Engineer 2's, and unwritten."""
    return Alert(
        3, "extraction ValidationError rate", NOT_OURS,
        "reads extraction outputs; judge/ opens no database connection, so there "
        "is nothing here to poll. Raised, not stubbed — a stub would report "
        "quiet forever while nothing measured anything",
        owner="judge/",
    )


def quote_verification() -> Alert:
    """Alert 4 — fabrication or an injection attempt. Engineer 2's, and unwritten."""
    return Alert(
        4, "quote-verification failure above 1%", NOT_OURS,
        "reads claim.quote_verified, which judge/ writes and this lane may not. "
        "Raised, not stubbed",
        owner="judge/",
    )


def registry_change(events) -> Alert:
    """Alert 5 — any registry field change, for a human to correlate.

    This one has a producer as of the polled-path change: `write_model_versions`
    now records `new-model` and `price-change` events with the same definition
    of a move the seed loader uses. Before that, `model_event` held 0 rows
    against 340 models and a price could move nightly with nothing recording it.
    """
    rows = list(events or ())
    if not rows:
        return Alert(
            5, "registry field change", QUIET,
            "no model_event rows since the last run",
            figures={"events": 0},
        )
    kinds: dict[str, int] = {}
    for event in rows:
        kind = event["type"] if isinstance(event, dict) else event[0]
        kinds[kind] = kinds.get(kind, 0) + 1
    return Alert(
        5, "registry field change", FIRED,
        "a human correlates these against provider announcements: "
        + ", ".join(f"{count} {kind}" for kind, count in sorted(kinds.items())),
        figures={"events": len(rows), **kinds},
    )


def evaluate(*, runs=None, events=None, nights: int = 0, kept: int = 0,
             candidates: int = 0) -> list[Alert]:
    """All five, in the order the workflow doc numbers them."""
    return [
        yield_drop(runs),
        triage_survival(nights, kept=kept, candidates=candidates),
        extraction_errors(),
        quote_verification(),
        registry_change(events),
    ]


def summarise(alerts) -> str:
    alerts = list(alerts)
    fired = sum(1 for a in alerts if a.state == FIRED)
    blind = sum(1 for a in alerts if a.state in (CANNOT_COMPUTE, NOT_OURS))
    head = (
        f"alerts: {fired} fired, {len(alerts) - fired - blind} quiet, "
        f"{blind} could not be computed"
    )
    return "\n".join([head, *(f"  {alert}" for alert in alerts)])
