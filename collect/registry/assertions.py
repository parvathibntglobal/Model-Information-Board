"""Startup assertions.

Both build fixtures are load-bearing during the build and poisonous
afterwards:

  - `contract/seed_models.yaml`  — 10 hardcoded models so work can start
    before the registry poller exists. Removed week 5.

  - `fixtures/hand_cells.yaml`   — hand-written cells so the Ask box works
    before any evidence exists. Removed week 8.

Ten invented models and ~180 hand-written opinions, rendered identically to
real evidence, permanently and undetectably, is exactly what this prevents.

Wire `assert_no_fixtures()` into application startup on day one, while you
still remember why it is there.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from collect.registry.policy import RegistryPolicy
    from collect.registry.sources import TermsRuling


class FixtureLeakError(RuntimeError):
    """Build fixtures reached an environment that must not have them."""


class UnversionedConfigError(RuntimeError):
    """Policy came from built-in defaults rather than versioned config."""


class TermsNotReviewedError(RuntimeError):
    """A source's terms of service were never reviewed (NFR-5)."""

    def __init__(self, message: str, refusals: list[TermsRefusal] | None = None) -> None:
        super().__init__(message)
        self.refusals = refusals or []


@dataclass(frozen=True)
class TermsRefusal:
    """One source, and the one thing wrong with its terms record."""

    source_id: str
    kind: str
    detail: str

    def __str__(self) -> str:
        return f"{self.source_id}: {self.detail}"


def source_field(source, name: str, default=None):
    """Read a field from a contract entry or a `source` row, indifferently."""
    if isinstance(source, Mapping):
        value = source.get(name, default)
    else:
        value = getattr(source, name, default)
    return default if value is None else value


def assert_terms_reviewed(
    sources,
    *,
    rulings: Mapping[str, TermsRuling] | None = None,
    observations: Mapping[str, Mapping[str, Any]] | None = None,
    today: date | None = None,
    marker: str = "REVIEW REQUIRED",
) -> None:
    """Refuse to harvest from a source whose terms nobody has read (NFR-5).

    NFR-5's acceptance is that terms are *reviewed and recorded per source*.
    The first version of this check grepped `tos_notes` for a placeholder
    marker, which caught the case where nobody had done the reading at all and
    nothing else. It let through the worse case: a ruling made once, in
    August, asserted forever against a site that changed its terms in October.
    A dated placeholder is still a placeholder.

    So the gate is four things, and a source has to pass all of them:

      1. It names a **known ruling**. No id, or an id nothing declares, and
         the run stops. This is what blocks `reddit`: there is no ruling to
         name, which is a stronger statement than a string in a comment.
      2. The ruling is **not expired** — `reviewed_on + review_valid_days`.
      3. The source's own **recorded evidence is not stale**, and every fact
         the ruling conditions on is present in it and acceptable. Missing
         evidence is not passing evidence (rule 6).
      4. Every **live precondition is re-verified on this run** and matches.
         An observation the caller did not supply refuses the source. This is
         the half that notices October: robots.txt is re-read every run, so a
         host that adds `Disallow: /` is obeyed the same day.

    Same shape and same reasoning as `assert_no_fixtures` and
    `assert_contract_backed`: a convenience needs a hard expiry, or it is just
    a second source of truth with better manners.

    Args:
        sources: an iterable of mappings or row objects carrying `id`,
            `tos_notes`, `terms_ruling` and `terms_evidence`.
        rulings: id → `TermsRuling`. Defaults to `contract/sources.yaml`.
        observations: source id → the facts observed on this run. A source
            with no entry fails every live precondition it has.
        today: the date the expiries are measured against.
        marker: the placeholder string, from `sources.yaml:review_marker`.
            No longer the gate — a row that names a ruling *and* still carries
            the marker is contradicting itself, and that is what this catches.

    Raises:
        TermsNotReviewedError: naming every source refused, and why.
    """
    from collect.registry.sources import load_sources

    if rulings is None:
        rulings = load_sources().rulings
    if today is None:
        today = date.today()
    observations = observations or {}

    refusals: list[TermsRefusal] = []
    for source in sources:
        refusals.extend(
            _refusals_for(source, rulings, observations, today, marker)
        )

    if refusals:
        listed = "\n  - ".join(str(refusal) for refusal in refusals)
        names = sorted({refusal.source_id for refusal in refusals})
        raise TermsNotReviewedError(
            f"Refusing to harvest: {len(names)} source(s) failed the NFR-5 "
            f"terms check ({', '.join(names)}):\n  - {listed}\n"
            "NFR-5 requires the terms be reviewed and recorded per source "
            "before any request is made, and this check additionally requires "
            "that the ruling has not expired and that its preconditions still "
            "hold on this run. Record what the terms say in "
            "contract/sources.yaml, re-measure the evidence, and re-run.",
            refusals,
        )


def _refusals_for(source, rulings, observations, today, marker):
    source_id = source_field(source, "id", "?")
    named = source_field(source, "terms_ruling")
    notes = source_field(source, "tos_notes", "")

    if not named:
        return [
            TermsRefusal(
                source_id,
                "no-ruling",
                "names no terms ruling. Read the terms, add a ruling to "
                "contract/sources.yaml:terms_rulings, and name it here.",
            )
        ]

    ruling = rulings.get(named)
    if ruling is None:
        known = ", ".join(sorted(rulings)) or "none declared"
        return [
            TermsRefusal(
                source_id,
                "unknown-ruling",
                f"names ruling {named!r}, which nothing declares. Known: {known}.",
            )
        ]

    refusals: list[TermsRefusal] = []

    if marker and marker in notes:
        refusals.append(
            TermsRefusal(
                source_id,
                "placeholder",
                f"names ruling {named!r} but its tos_notes still carries "
                f"{marker!r}. One of the two is wrong.",
            )
        )

    expires = ruling.expires_on()
    if expires < today:
        refusals.append(
            TermsRefusal(
                source_id,
                "ruling-expired",
                f"ruling {named!r} was read on {ruling.reviewed_on} and expired "
                f"on {expires}. Re-read the terms rather than extending the date.",
            )
        )

    evidence = source_field(source, "terms_evidence", {}) or {}
    checked_on = source_field(source, "terms_checked_on") or evidence.get("checked_on")
    if not isinstance(checked_on, date):
        refusals.append(
            TermsRefusal(
                source_id,
                "no-evidence-date",
                "carries no date for its terms evidence. An undated "
                "measurement cannot be told from one made two years ago.",
            )
        )
    else:
        stale_on = ruling.evidence_expires_on(checked_on)
        if stale_on < today:
            refusals.append(
                TermsRefusal(
                    source_id,
                    "evidence-stale",
                    f"terms evidence was measured on {checked_on} and went "
                    f"stale on {stale_on}. Re-check robots.txt and the feed.",
                )
            )

    refusals.extend(
        _check_facts(
            source_id,
            ruling.recorded_evidence,
            evidence,
            kind="recorded-evidence",
            missing_detail=(
                "ruling {ruling} conditions on {key}, which this source's "
                "terms_evidence does not record. Absent is not acceptable "
                "(rule 6) — measure it."
            ),
            ruling_id=named,
        )
    )
    refusals.extend(
        _check_facts(
            source_id,
            ruling.live_preconditions,
            observations.get(source_id) or {},
            kind="precondition",
            missing_detail=(
                "ruling {ruling} requires {key} to be re-verified on this run, "
                "and the run observed nothing. An observation that was not "
                "made is not an observation that passed (rule 6)."
            ),
            ruling_id=named,
        )
    )
    return refusals


def _check_facts(source_id, required, observed, *, kind, missing_detail, ruling_id):
    refusals = []
    for key, accepted in required.items():
        if key not in observed:
            refusals.append(
                TermsRefusal(
                    source_id,
                    f"{kind}-missing",
                    missing_detail.format(ruling=ruling_id, key=key),
                )
            )
            continue
        value = observed[key]
        if value not in accepted:
            refusals.append(
                TermsRefusal(
                    source_id,
                    f"{kind}-failed",
                    f"ruling {ruling_id} requires {key} to be one of "
                    f"{accepted!r}; observed {value!r}.",
                )
            )
    return refusals


def assert_contract_backed(policy: RegistryPolicy, *, environment: str) -> None:
    """Refuse to start on built-in defaults outside development (NFR-10).

    NFR-10's acceptance is that changing a threshold requires no code deploy
    and produces a version diff. Defaults in code pass that test today and
    quietly stop passing it the day somebody edits a default instead of the
    YAML: the threshold change then ships as a deploy, with no diff, and the
    two sources disagree with nothing to notice.

    Same reasoning as `assert_no_fixtures`, so the same mechanism. A
    development convenience needs a hard expiry, or it is just a second
    source of truth with better manners.

    Args:
        policy: the loaded policy, carrying where it came from.
        environment: ``"development"`` skips the check; anything else
            enforces it.

    Raises:
        UnversionedConfigError: if the policy did not come from `contract/`.
    """
    from collect.registry.policy import CONTRACT, REGISTRY_YAML

    if environment == "development":
        return
    if policy.source == CONTRACT:
        return

    raise UnversionedConfigError(
        f"Refusing to start in {environment!r}: registry policy came from "
        f"built-in defaults, not from versioned config. Expected "
        f"{REGISTRY_YAML}. NFR-10 requires that changing a threshold needs "
        "no code deploy and produces a version diff, which defaults in code "
        "cannot provide."
    )


def assert_no_fixtures(conn, *, environment: str) -> None:
    """Refuse to start if build fixtures are present outside development.

    Args:
        conn: a DB-API connection or anything exposing ``execute``.
        environment: ``"development"`` skips the check; anything else
            enforces it.

    Raises:
        FixtureLeakError: if seeded models or hand-curated cells are found.
    """
    if environment == "development":
        return

    seeded = _scalar(
        conn, "SELECT count(*) FROM model_version WHERE provenance = 'seed'"
    )
    handmade = _scalar(
        conn, "SELECT count(*) FROM cell WHERE provenance = 'hand_curated'"
    )
    # Item 20. `reported_context.reported_low` is read by FR-31 as a hard
    # filter, so a hand-seeded threshold does not render as a claim somebody
    # can disagree with. It renders as an absence, and nobody audits a model
    # that was never in the list.
    thresholds = _scalar(
        conn, "SELECT count(*) FROM reported_context WHERE provenance = 'hand_seeded'"
    )

    if seeded or handmade or thresholds:
        raise FixtureLeakError(
            f"Refusing to start in {environment!r}: "
            f"{seeded} seeded model(s), {handmade} hand-curated cell(s), "
            f"{thresholds} hand-seeded context threshold(s) present. "
            "These are build fixtures. Seeded models are replaced by the "
            "OpenRouter poller in week 5; hand-curated cells are deleted in "
            "week 8. Hand-seeded thresholds feed FR-31's hard filter and would "
            "exclude models silently. None may ever be served as evidence."
        )


def _scalar(conn, sql: str) -> int:
    cur = conn.execute(sql)
    row = cur.fetchone()
    return int(row[0]) if row else 0
