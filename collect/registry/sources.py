"""Load `contract/sources.yaml`: the platforms, the seeded feeds, the rulings.

Same pattern as `collect/registry/seed.py` → `model_version`, and for the same
reason: the initial list is a decision somebody made, so it lives somewhere
reviewable and diffable, and it becomes ordinary `source` rows at runtime.
Feeds discovered from links in already-harvested content are inserted into
`source` directly and never written back here.

The difference from `seed_models.yaml` is that this is **not a build fixture**
and has no removal date. `assert_no_fixtures()` does not look at `source` and
must not be taught to: a seeded feed is a curation decision, not a stand-in for
machinery that does not exist yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache
from typing import Any, Mapping

import yaml

from collect.config import CONTRACT_DIR

SOURCES_YAML = CONTRACT_DIR / "sources.yaml"


class SourcesContractError(ValueError):
    """`contract/sources.yaml` does not say what the loader needs it to say."""


@dataclass(frozen=True)
class TermsRuling:
    """One reading of one party's terms, dated, with an expiry.

    A ruling is about a *party* — a self-hosting publisher, or a platform —
    never about a URL. `live_preconditions` are re-verified on every run;
    `recorded_evidence` is measured by hand per source and goes stale.
    """

    id: str
    reviewed_on: date
    review_valid_days: int
    evidence_valid_days: int
    summary: str
    klass: str | None = None
    party: str | None = None
    platform_host: str | None = None

    #: False means the feed is the only permitted retrieval for this party.
    #: `BlogFetcher` refuses to request articles when it is False, so this is
    #: an enforced ruling rather than a note somebody has to remember.
    fetch_articles: bool = True

    live_preconditions: Mapping[str, list[Any]] = field(default_factory=dict)
    recorded_evidence: Mapping[str, list[Any]] = field(default_factory=dict)

    def expires_on(self) -> date:
        return self.reviewed_on + timedelta(days=self.review_valid_days)

    def evidence_expires_on(self, checked_on: date) -> date:
        return checked_on + timedelta(days=self.evidence_valid_days)


@dataclass(frozen=True)
class SourcesContract:
    """Everything `sources.yaml` declares, parsed once."""

    version: str
    review_marker: str
    rulings: Mapping[str, TermsRuling]
    platforms: list[dict[str, Any]]
    feeds: list[dict[str, Any]]

    def source_rows(self) -> list[dict[str, Any]]:
        """The `source` rows this contract seeds — platforms and feeds alike.

        Every feed is a source row at runtime. `provenance` is `seed` for all
        of them; a discovered feed carries `discovered` and is inserted into
        `source` directly.
        """
        return [_source_row(row) for row in (*self.platforms, *self.feeds)]


_SOURCE_COLUMNS = (
    "id",
    "platform",
    "endpoint",
    "base_trust",
    "tos_notes",
    "provenance",
    "terms_ruling",
    "terms_evidence",
)


def _source_row(entry: Mapping[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {
        column: entry.get(column) for column in _SOURCE_COLUMNS
    }
    evidence = entry.get("terms_evidence") or {}
    row["terms_evidence"] = dict(evidence)
    row["terms_checked_on"] = evidence.get("checked_on")
    return row


def _as_date(value: Any, *, what: str) -> date:
    if isinstance(value, date):
        return value
    raise SourcesContractError(f"{what} must be a date, got {value!r}")


def _ruling_from(entry: Mapping[str, Any]) -> TermsRuling:
    try:
        ruling_id = entry["id"]
    except KeyError:  # pragma: no cover - a malformed contract file
        raise SourcesContractError("a terms ruling has no id") from None

    missing = [
        key
        for key in ("reviewed_on", "review_valid_days", "evidence_valid_days")
        if entry.get(key) is None
    ]
    if missing:
        raise SourcesContractError(
            f"ruling {ruling_id!r} is missing {', '.join(missing)}. A ruling "
            "without a review date and an expiry is a placeholder with a name."
        )

    return TermsRuling(
        id=ruling_id,
        reviewed_on=_as_date(entry["reviewed_on"], what=f"{ruling_id}.reviewed_on"),
        review_valid_days=int(entry["review_valid_days"]),
        evidence_valid_days=int(entry["evidence_valid_days"]),
        summary=entry.get("summary", ""),
        klass=entry.get("class"),
        party=entry.get("party"),
        platform_host=entry.get("platform_host"),
        fetch_articles=bool(entry.get("fetch_articles", True)),
        live_preconditions=dict(entry.get("live_preconditions") or {}),
        recorded_evidence=dict(entry.get("recorded_evidence") or {}),
    )


def parse_sources(document: Mapping[str, Any]) -> SourcesContract:
    """Parse a loaded `sources.yaml` document. Never reads the filesystem."""
    rulings = {
        ruling.id: ruling
        for ruling in (
            _ruling_from(entry) for entry in document.get("terms_rulings") or []
        )
    }
    return SourcesContract(
        version=str(document.get("version", "")),
        review_marker=document.get("review_marker", "REVIEW REQUIRED"),
        rulings=rulings,
        platforms=list(document.get("sources") or []),
        feeds=list(document.get("feeds") or []),
    )


@lru_cache(maxsize=1)
def load_sources() -> SourcesContract:
    """Read and parse `contract/sources.yaml`."""
    document = yaml.safe_load(SOURCES_YAML.read_text(encoding="utf-8"))
    return parse_sources(document)


def ruling_for(source, *, rulings: Mapping[str, TermsRuling] | None = None):
    """The ruling governing one source, or None if it names none.

    Accepts a mapping or a row object, because the caller may be holding
    either the contract entry or the `source` table row.
    """
    from collect.registry.assertions import source_field

    if rulings is None:
        rulings = load_sources().rulings
    named = source_field(source, "terms_ruling")
    return rulings.get(named) if named else None
