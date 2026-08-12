"""Write the registry into Postgres.

`model_version` is upserted — a poller re-reading a provider page must be
able to correct a price. `model_alias` is **append-only** (FR-4): old aliases
have to keep resolving old quotes, and `latest` in March is not `latest` in
June, so nothing here ever issues an UPDATE or a DELETE against it.

Every price movement is recorded in `pricing_history` and raised as a
`model_event`, which is the same mechanism week 5's daily API diff uses
(FR-3). Seeding and polling differ in where the facts come from, not in what
happens to them afterwards.

FR-5: nothing in this module reads `document`, `claim` or anything else
produced by harvest. Community content may trigger a registry re-check; it
may never write to the registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from collect.ids import model_event_id, model_version_id
from collect.registry.aliases import AliasRow, all_alias_rows, check_no_collisions
from collect.registry.models import SeedModel
from collect.registry.seed import gaps_by_model, load_seed_file, source_gaps

if TYPE_CHECKING:  # pragma: no cover - typing only
    import psycopg

#: Columns written from a seed or polled record, in a fixed order.
_MODEL_COLUMNS: tuple[str, ...] = (
    "id",
    "canonical_id",
    "provider",
    "family",
    "display_name",
    "release_date",
    "deprecation_date",
    "retirement_date",
    "lifecycle",
    "advertised_context",
    "max_output_tokens",
    "knowledge_cutoff",
    "price_in",
    "price_out",
    "price_cached_read",
    "batch_discount",
    "supports_tools",
    "supports_structured_output",
    "supports_vision",
    "supports_caching",
    "supports_batch",
    "regions",
    "sources",
    "provenance",
    "in_window",
)

_PRICE_COLUMNS = ("price_in", "price_out", "price_cached_read")


@dataclass
class LoadReport:
    """What a load run did. Printed by the CLI, and the input to ops later."""

    models_inserted: int = 0
    models_updated: int = 0
    models_unchanged: int = 0
    aliases_inserted: int = 0
    aliases_existing: int = 0
    events: list[tuple[str, str]] = field(default_factory=list)
    unsourced_fields: dict[str, list[str]] = field(default_factory=dict)

    @property
    def unsourced_field_count(self) -> int:
        return sum(len(fields) for fields in self.unsourced_fields.values())

    def summary(self) -> str:
        lines = [
            f"models   : {self.models_inserted} inserted, "
            f"{self.models_updated} updated, {self.models_unchanged} unchanged",
            f"aliases  : {self.aliases_inserted} inserted, "
            f"{self.aliases_existing} already present (append-only)",
            f"events   : {len(self.events)}",
        ]
        for event_type, detail in self.events:
            lines.append(f"           {event_type}: {detail}")
        if self.unsourced_fields:
            lines.append(
                f"FR-2 gap : {self.unsourced_field_count} populated field(s) with no "
                f"source, across {len(self.unsourced_fields)} model(s)"
            )
            for canonical_id, fields in sorted(self.unsourced_fields.items()):
                lines.append(f"           {canonical_id}: {', '.join(fields)}")
        return "\n".join(lines)


def _sources_json(model: SeedModel) -> dict[str, dict[str, str]]:
    return {
        field_name: {"url": ref.url, "retrieved_at": ref.retrieved_at.isoformat()}
        for field_name, ref in model.sources.items()
    }


def model_row(model: SeedModel, *, provenance: str = "seed") -> dict[str, Any]:
    """The `model_version` row for one seeded model."""
    return {
        "id": model_version_id(model.canonical_id),
        "canonical_id": model.canonical_id,
        "provider": model.provider,
        "family": model.family,
        "display_name": model.display_name,
        "release_date": model.release_date,
        "deprecation_date": model.deprecation_date,
        "retirement_date": model.retirement_date,
        "lifecycle": model.lifecycle,
        "advertised_context": model.advertised_context,
        "max_output_tokens": model.max_output_tokens,
        "knowledge_cutoff": model.knowledge_cutoff,
        "price_in": model.price_in,
        "price_out": model.price_out,
        "price_cached_read": model.price_cached_read,
        "batch_discount": model.batch_discount,
        "supports_tools": model.supports_tools,
        "supports_structured_output": model.supports_structured_output,
        "supports_vision": model.supports_vision,
        "supports_caching": model.supports_caching,
        "supports_batch": model.supports_batch,
        "regions": model.regions,
        "sources": _sources_json(model),
        "provenance": provenance,
        # Seeded models are in the window by declaration — they were chosen
        # by hand for exactly that reason. Week 5's poller computes this from
        # the trailing-window rule, and the window length belongs in
        # `contract/` when it does.
        "in_window": True,
    }


def _changed_fields(existing: dict[str, Any], incoming: dict[str, Any]) -> list[str]:
    """Which written columns differ. `id` is derived, so it never differs."""
    changed = []
    for column in _MODEL_COLUMNS:
        if column == "id":
            continue
        before, after = existing.get(column), incoming.get(column)
        if isinstance(before, Decimal) or isinstance(after, Decimal):
            before = None if before is None else Decimal(str(before))
            after = None if after is None else Decimal(str(after))
        if before != after:
            changed.append(column)
    return changed


def _upsert_model(conn: psycopg.Connection[Any], row: dict[str, Any]) -> tuple[str, list[str]]:
    """Insert or update one `model_version`. Returns (verdict, changed columns)."""
    from psycopg.rows import dict_row
    from psycopg.types.json import Json

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM model_version WHERE canonical_id = %s",
            (row["canonical_id"],),
        )
        existing = cur.fetchone()

    params = dict(row)
    params["sources"] = Json(row["sources"])

    placeholders = ", ".join(f"%({column})s" for column in _MODEL_COLUMNS)
    columns = ", ".join(_MODEL_COLUMNS)
    updatable = [c for c in _MODEL_COLUMNS if c not in ("id", "canonical_id")]
    assignments = ", ".join(f"{c} = EXCLUDED.{c}" for c in updatable)

    conn.execute(
        f"INSERT INTO model_version ({columns}) VALUES ({placeholders}) "
        f"ON CONFLICT (canonical_id) DO UPDATE SET {assignments}, updated_at = now()",
        params,
    )

    if existing is None:
        return "inserted", []
    changed = _changed_fields(existing, row)
    return ("updated" if changed else "unchanged"), changed


def _record_prices(
    conn: psycopg.Connection[Any], row: dict[str, Any], *, is_new: bool
) -> str | None:
    """Append to `pricing_history` when prices are new or have moved.

    Returns an event type when a change was recorded, so the caller can raise
    the `model_event` that week 5's alerting consumes.
    """
    from psycopg.rows import dict_row

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT price_in, price_out, price_cached_read FROM pricing_history "
            "WHERE model_version_id = %s ORDER BY observed_at DESC LIMIT 1",
            (row["id"],),
        )
        latest = cur.fetchone()

    incoming = {c: row[c] for c in _PRICE_COLUMNS}
    if latest is not None:
        previous = {c: latest[c] for c in _PRICE_COLUMNS}
        if _prices_equal(previous, incoming):
            return None

    conn.execute(
        "INSERT INTO pricing_history (model_version_id, price_in, price_out, "
        "price_cached_read) VALUES (%s, %s, %s, %s)",
        (row["id"], row["price_in"], row["price_out"], row["price_cached_read"]),
    )
    return None if is_new else "price-change"


def _prices_equal(before: dict[str, Any], after: dict[str, Any]) -> bool:
    for column in _PRICE_COLUMNS:
        left, right = before.get(column), after.get(column)
        left = None if left is None else Decimal(str(left))
        right = None if right is None else Decimal(str(right))
        if left != right:
            return False
    return True


def _record_event(
    conn: psycopg.Connection[Any],
    model_version_id_: str,
    event_type: str,
    detail: str,
    payload: dict[str, Any] | None = None,
) -> None:
    from psycopg.types.json import Json

    conn.execute(
        "INSERT INTO model_event (id, model_version_id, type, payload) "
        "VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
        (
            model_event_id(model_version_id_, event_type, detail),
            model_version_id_,
            event_type,
            Json(payload or {}),
        ),
    )


def _insert_alias(conn: psycopg.Connection[Any], alias: AliasRow) -> bool:
    """Append one alias. Returns False when the row already existed.

    FR-4: INSERT only. `ON CONFLICT DO NOTHING` is what makes a re-run
    idempotent without ever rewriting a row that history depends on.
    """
    cur = conn.execute(
        "INSERT INTO model_alias (id, surface, normalized, variants, provider_hint, "
        "model_version_id, family, specificity, valid_from, valid_until, confidence) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (id) DO NOTHING",
        (
            alias.id,
            alias.surface,
            alias.normalized,
            alias.variants,
            alias.provider_hint,
            alias.model_version_id,
            alias.family,
            alias.specificity,
            alias.valid_from,
            alias.valid_until,
            alias.confidence,
        ),
    )
    return cur.rowcount == 1


def load_seed(
    conn: psycopg.Connection[Any],
    *,
    path: Any = None,
    strict_sources: bool = True,
) -> LoadReport:
    """Load `contract/seed_models.yaml` into the registry.

    Args:
        conn: an open connection. The caller commits.
        path: override the seed file, for tests.
        strict_sources: refuse to load any field that asserts a value without
            citing where it came from (FR-2). The seed file ships with known
            gaps; passing False loads anyway and records them in the report,
            where the coverage surface can show them.
    """
    from collect.registry.seed import check_source_coverage

    seed = load_seed_file(path)
    if strict_sources:
        check_source_coverage(seed)

    aliases = all_alias_rows(seed.models)
    check_no_collisions(aliases)

    report = LoadReport(unsourced_fields=gaps_by_model(seed) if source_gaps(seed) else {})

    for model in seed.models:
        row = model_row(model, provenance="seed")
        verdict, changed = _upsert_model(conn, row)

        if verdict == "inserted":
            report.models_inserted += 1
            _record_event(conn, row["id"], "new-model", model.canonical_id)
            report.events.append(("new-model", model.canonical_id))
        elif verdict == "updated":
            report.models_updated += 1
        else:
            report.models_unchanged += 1

        price_event = _record_prices(conn, row, is_new=verdict == "inserted")
        if price_event:
            detail = f"{model.canonical_id}: {sorted(set(changed) & set(_PRICE_COLUMNS))}"
            _record_event(
                conn,
                row["id"],
                price_event,
                detail,
                {"changed": [c for c in changed if c in _PRICE_COLUMNS]},
            )
            report.events.append((price_event, detail))

    for alias in aliases:
        if _insert_alias(conn, alias):
            report.aliases_inserted += 1
        else:
            report.aliases_existing += 1

    return report
