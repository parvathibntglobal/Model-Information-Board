"""Board entries whose model is not in the registry yet: held, then attributed.

#602, 2026-11-05. `judge/pipeline.py` used to drop a verified claim whose model
name resolved to no registry row, keeping only the name for the run log. Its
board entries are now held in `unresolved_entry` instead (see the migration
`20261105T1300_unresolved_entry.sql`), and `attribute_held` files them onto the
board once the model is seated - resolved by the SAME resolver extraction uses,
so a name that was correctly refused (a family, an ambiguous codename, a range)
stays refused, and nothing calls a model a second time.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any

from judge.store.claims import PIPELINE_VERSION

_COLUMNS = (
    "id", "surface", "document_id", "thread_context_id", "section", "slug", "name",
    "definition", "unit", "value_verbatim", "basis", "parent_proposed", "axis_verbatim",
    "subject_verbatim", "polarity", "quote", "proposer_model", "pipeline_version",
)


#: SPELLED OUT, not joined from `_COLUMNS` at runtime: `scripts/audit_columns.py`
#: reads SQL string literals to find each column's writer and reader (rule 9),
#: and a generated list names no column it can see.
_INSERT = (
    "INSERT INTO unresolved_entry (id, surface, document_id, thread_context_id, "
    "section, slug, name, definition, unit, value_verbatim, basis, parent_proposed, "
    "axis_verbatim, subject_verbatim, polarity, quote, proposer_model, pipeline_version) "
    "VALUES (%(id)s, %(surface)s, %(document_id)s, %(thread_context_id)s, %(section)s, "
    "%(slug)s, %(name)s, %(definition)s, %(unit)s, %(value_verbatim)s, %(basis)s, "
    "%(parent_proposed)s, %(axis_verbatim)s, %(subject_verbatim)s, %(polarity)s, "
    "%(quote)s, %(proposer_model)s, %(pipeline_version)s) "
)


def held_id(*, document_id: str, section: str, slug: str, quote: str, surface: str,
            pipeline_version: str) -> str:
    """Content hash of the natural key, so re-reading a thread cannot double a row."""
    key = "\x1f".join([document_id, section, slug, quote, surface, pipeline_version])
    return "ue_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def hold_entries(conn: Any, rows: list[dict], *, proposer_model: str,
                 pipeline_version: str = PIPELINE_VERSION) -> int:
    """Append held rows. Returns how many were new. Never raises on a re-run."""
    if not rows:
        return 0
    held = 0
    with conn.cursor() as cur:
        for r in rows:
            values = {
                **{c: r.get(c) for c in _COLUMNS},
                "proposer_model": proposer_model,
                "pipeline_version": pipeline_version,
            }
            values["id"] = held_id(
                document_id=r["document_id"], section=r["section"], slug=r["slug"],
                quote=r["quote"], surface=r["surface"], pipeline_version=pipeline_version,
            )
            cur.execute(
                _INSERT + "ON CONFLICT (id) DO NOTHING",
                values,
            )
            held += cur.rowcount
    return held


def held_by_name(conn: Any) -> dict[str, tuple[int, int]]:
    """{surface: (entries still held, distinct authors)}, for the seating bar.

    Authors through the held row's document: a report whose author is unknown
    adds an entry and no author, as the catalogue counts voices.
    """
    rows = conn.execute(
        "SELECT u.surface, count(*), count(DISTINCT d.author_id) "
        "FROM unresolved_entry u JOIN document d ON d.id = u.document_id "
        "WHERE u.attributed_at IS NULL GROUP BY u.surface"
    ).fetchall()
    return {s: (int(n), int(a)) for s, n, a in rows}


def held_surfaces(conn: Any) -> Counter:
    """{surface: rows still held}, for the run report and the attribution dry run."""
    return Counter(dict(conn.execute(
        "SELECT surface, count(*) FROM unresolved_entry WHERE attributed_at IS NULL "
        "GROUP BY surface"
    ).fetchall()))


def attribute_held(conn: Any, resolve_surface, *, dry_run: bool = True) -> dict[str, Any]:
    """File every held row whose surface now resolves, through `store_entries`.

    `resolve_surface` is a `judge.pipeline.SurfaceResolver` - in practice
    `RegistrySurfaceResolver.from_connection(conn)`, the one extraction used.
    A row that still resolves to nothing stays held, untouched.
    """
    from judge.store.board_entries import entry_id, normalise_slug, store_entries

    rows = conn.execute(
        "SELECT id, surface, document_id, thread_context_id, section, slug, name, "
        "definition, unit, value_verbatim, basis, parent_proposed, axis_verbatim, "
        "subject_verbatim, polarity, quote, proposer_model, pipeline_version "
        "FROM unresolved_entry WHERE attributed_at IS NULL ORDER BY created_at, id"
    ).fetchall()
    by_model: Counter = Counter()
    still: Counter = Counter()
    #: Why a resolved row did not become a NEW board row - store_entries'
    #: own refusals, or an identical row already on the board. Said, so
    #: "12 resolvable, 5 filed" never leaves 7 unexplained.
    not_filed: Counter = Counter()
    filed = 0
    for row in rows:
        r = dict(zip(_COLUMNS, row, strict=True))
        model = resolve_surface(r["surface"])
        if model is None:
            still[r["surface"]] += 1
            continue
        by_model[model] += 1
        if dry_run:
            continue
        entry = {
            "section": r["section"], "slug": r["slug"], "name": r["name"],
            "definition": r["definition"], "parent": r["parent_proposed"],
            "unit": r["unit"], "value_verbatim": r["value_verbatim"], "basis": r["basis"],
            "axis_verbatim": r["axis_verbatim"], "subject_verbatim": r["subject_verbatim"],
            "model_version_id": model, "document_id": r["document_id"], "claim_id": None,
            # Verified at extraction, before the row was held: the quote is the
            # one the substring check passed, stored as it was then.
            "quote": r["quote"], "quote_verified": True, "polarity": r["polarity"],
        }
        outcome = store_entries(conn, [entry], proposer_model=r["proposer_model"],
                                pipeline_version=r["pipeline_version"])
        filed += outcome["stored"]
        if not outcome["stored"]:
            for why, n in (outcome.get("refused_by") or {}).items():
                not_filed[f"refused: {why}"] += n
            if outcome.get("skipped_unverified"):
                not_filed["skipped: no slug or unverified"] += outcome["skipped_unverified"]
            if not outcome.get("refused_by") and not outcome.get("skipped_unverified"):
                not_filed["already on the board (same document, section, slug, quote)"] += 1
        board_id = entry_id(
            document_id=r["document_id"], section=r["section"],
            slug=normalise_slug(r["slug"]), quote=r["quote"],
            pipeline_version=r["pipeline_version"],
        ) if outcome["stored"] else None
        conn.execute(
            "UPDATE unresolved_entry SET attributed_at = now(), attributed_to = %s, "
            "attributed_entry = %s WHERE id = %s AND attributed_at IS NULL",
            (model, board_id, r["id"]),
        )
    return {
        "held": len(rows),
        "resolvable": sum(by_model.values()),
        "by_model": dict(by_model),
        "filed": filed,
        "not_filed": dict(not_filed),
        "still_held": dict(still),
    }
