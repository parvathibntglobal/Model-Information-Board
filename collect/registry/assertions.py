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


class FixtureLeakError(RuntimeError):
    """Build fixtures reached an environment that must not have them."""


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

    if seeded or handmade:
        raise FixtureLeakError(
            f"Refusing to start in {environment!r}: "
            f"{seeded} seeded model(s), {handmade} hand-curated cell(s) present. "
            "These are build fixtures. Seeded models are replaced by the "
            "OpenRouter poller in week 5; hand-curated cells are deleted in "
            "week 8. Neither may ever be served as evidence."
        )


def _scalar(conn, sql: str) -> int:
    cur = conn.execute(sql)
    row = cur.fetchone()
    return int(row[0]) if row else 0
