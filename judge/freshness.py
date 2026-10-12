"""How fresh the board is: when it last changed, and how new its evidence is.

Two dates, because they answer different questions and must not be merged:

    updated_at        when the newest board entry was ADDED - how recently
                      the board itself changed
    newest_report_at  when the newest source post behind an entry was
                      WRITTEN - how recent the evidence is

A board updated today from posts written months ago is fresh in one sense and
stale in the other; showing only the first would overstate the second.

THE SAME POPULATION AS THE BOARD. Declined entries are excluded (as in
`board_sections`), and on a public view so is every entry whose document is
from a withheld source (`judge/publication.py`). A date drawn from rows the
page does not show would describe evidence the reader cannot see.

ABSENT IS NOT ZERO (rule 6). A model with no entry has no dates; it is left out
of `models`, never given a placeholder date.
"""

from __future__ import annotations

from typing import Any


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def board_freshness(conn: Any) -> dict:
    """Overall and per-model freshness, over the entries the board shows."""
    from judge import publication

    pub_sql, pub_args = publication.sql_public_document("be.document_id")
    base = (
        "FROM board_entry be LEFT JOIN document d ON d.id = be.document_id "
        "WHERE be.ruling IS DISTINCT FROM 'declined'" + pub_sql
    )
    overall = conn.execute(
        "SELECT max(be.created_at), max(d.created_at), count(*) " + base,
        pub_args,
    ).fetchone()
    per_model = conn.execute(
        "SELECT be.model_version_id, max(be.created_at), max(d.created_at) " + base
        + " AND be.model_version_id IS NOT NULL GROUP BY be.model_version_id",
        pub_args,
    ).fetchall()
    # The registry's canonical id too, so a page that knows a model by either
    # spelling finds its dates.
    ids = [row[0] for row in per_model]
    canonical = dict(conn.execute(
        "SELECT id, canonical_id FROM model_version WHERE id = ANY(%s)", (ids,)
    ).fetchall()) if ids else {}

    models: dict[str, dict] = {}
    for mv, updated, newest in per_model:
        entry = {"updated_at": _iso(updated), "newest_report_at": _iso(newest)}
        models[mv] = entry
        if canonical.get(mv):
            models[canonical[mv]] = entry
    return {
        "updated_at": _iso(overall[0]),
        "newest_report_at": _iso(overall[1]),
        "entries": overall[2],
        "models": models,
        "view": publication.view(),
    }
