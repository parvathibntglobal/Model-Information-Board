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

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from collect.registry.policy import RegistryPolicy


class FixtureLeakError(RuntimeError):
    """Build fixtures reached an environment that must not have them."""


class UnversionedConfigError(RuntimeError):
    """Policy came from built-in defaults rather than versioned config."""


class TermsNotReviewedError(RuntimeError):
    """A source's terms of service were never reviewed (NFR-5)."""


def assert_terms_reviewed(sources, *, marker: str = "REVIEW REQUIRED") -> None:
    """Refuse to harvest from a source whose terms nobody has read (NFR-5).

    `contract/sources.yaml` ships `tos_notes` placeholders so the `source`
    rows can exist, which unblocks FR-9's foreign key without pretending a
    reading task has been done. The placeholder says so in the value itself.

    But a placeholder a human has to notice is a lie you will eventually
    forget. NFR-5's acceptance is that terms are *reviewed and recorded per
    source*, so one surviving to first harvest is a requirement failure, and
    it should stop the run rather than be discovered afterwards.

    Same shape and same reasoning as `assert_no_fixtures` and
    `assert_contract_backed`: a development convenience needs a hard expiry,
    or it is just a second source of truth with better manners.

    Args:
        sources: an iterable of objects or mappings carrying `id` and
            `tos_notes`.
        marker: the placeholder string, from `sources.yaml:review_marker`.

    Raises:
        TermsNotReviewedError: naming every source still unreviewed.
    """
    unreviewed = []
    for source in sources:
        if isinstance(source, dict):
            source_id = source.get("id", "?")
            notes = source.get("tos_notes") or ""
        else:
            source_id = getattr(source, "id", "?")
            notes = getattr(source, "tos_notes", "") or ""
        if marker in notes:
            unreviewed.append(source_id)

    if unreviewed:
        raise TermsNotReviewedError(
            f"Refusing to harvest: {len(unreviewed)} source(s) still carry the "
            f"{marker!r} placeholder in tos_notes: {', '.join(sorted(unreviewed))}. "
            "NFR-5 requires the terms be reviewed and recorded per source before "
            "any request is made. Read them, record what they say in "
            "contract/sources.yaml, and re-run."
        )


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
