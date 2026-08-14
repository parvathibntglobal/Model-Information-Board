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
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from collect.ids import model_version_id
from collect.registry.aliases import (
    AliasRow,
    all_alias_rows,
    check_no_collisions,
    check_spelling_coverage,
    spelling_gaps,
)
from collect.registry.models import SeedModel
from collect.registry.policy import RegistryPolicy, load_registry_policy
from collect.registry.seed import gaps_by_model, load_seed_file, source_gaps
from collect.registry.window import in_window, window_report, window_start

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

#: `in_window` is deliberately absent from the UPDATE set.
#:
#: OWNERSHIP: the nightly `registry recompute-window` job owns this column.
#: It is a function of `release_date` and *today*, not of the seed file, so
#: its correct value changes on days when nothing is loaded at all. Letting
#: the loader write it on every run would mean the value depends on whichever
#: of the two ran last, which is a race with no owner.
#:
#: The loader still supplies a value on INSERT, because the column is NOT
#: NULL and a fresh row needs one. After that it never writes it again.
_NEVER_UPDATED = ("in_window",)


class ProvenanceDowngradeError(RuntimeError):
    """A polled row was about to be overwritten by seed data.

    Week 5 replaces `contract/seed_models.yaml` with OpenRouter polling
    writing into this same table. After that, one stray `registry load-seed`
    would flip polled rows back to `provenance = 'seed'`, and
    `assert_no_fixtures` would then refuse to boot production over models
    that are perfectly real.

    Refusing loudly rather than skipping is deliberate: a silent skip is how
    the seed file quietly stops matching the database, and nobody finds out
    until the two disagree about a price.

    Promotion in the other direction is allowed. `seed` becoming `polled` is
    exactly what week 5 is for.
    """

    def __init__(self, canonical_ids: list[str]) -> None:
        self.canonical_ids = canonical_ids
        listed = ", ".join(sorted(canonical_ids))
        super().__init__(
            f"Refusing to load: {len(canonical_ids)} row(s) already carry "
            f"provenance='polled' and this load would downgrade them to 'seed': "
            f"{listed}. Seeded models are a build fixture that polling replaces; "
            "reversing that would make assert_no_fixtures refuse to start."
        )


@dataclass(frozen=True)
class CoverageGap:
    """Something the board does not know, in a shape a page can render.

    Gaps that live only in CLI output become permanent the first time
    somebody scripts the load. FR-11's principle generalises past budget
    caps: a gap nobody can see reads as "we looked everywhere" when we did
    not.
    """

    kind: str  # unsourced-field | missing-spelling | out-of-window | unknown-release-date
    subject: str  # canonical_id
    detail: str


@dataclass
class LoadReport:
    """What a load run did. Printed by the CLI, and the input to ops later."""

    models_inserted: int = 0
    models_updated: int = 0
    models_unchanged: int = 0
    aliases_inserted: int = 0
    aliases_existing: int = 0
    #: Live rows superseded and closed out by setting `valid_until` (FR-4).
    aliases_closed: int = 0
    #: Item 18. Tier bands written for models whose price is length-dependent.
    price_tiers_written: int = 0
    events: list[tuple[str, str]] = field(default_factory=list)
    unsourced_fields: dict[str, list[str]] = field(default_factory=dict)

    #: FR-1 coverage. `window_unknown` is a guess made in the safe direction,
    #: not a fact, so it is counted separately from models genuinely inside.
    out_of_window: list[str] = field(default_factory=list)
    window_unknown: list[str] = field(default_factory=list)

    #: Models a search API cannot find by one of the three renderings. A
    #: missing spelling yields silence, not an error, so it has to be counted.
    missing_spellings: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @property
    def unsourced_field_count(self) -> int:
        return sum(len(fields) for fields in self.unsourced_fields.values())

    def coverage_gaps(self) -> list[CoverageGap]:
        """Every gap this load carried, for the coverage surface.

        `summary()` is for a human reading a terminal. This is the same
        information in a shape something can store and render, so that an
        override like `--allow-missing-spellings` cannot quietly become the
        permanent state of the system.
        """
        gaps: list[CoverageGap] = []
        for canonical_id, fields in sorted(self.unsourced_fields.items()):
            for field_name in fields:
                gaps.append(
                    CoverageGap("unsourced-field", canonical_id, f"{field_name} cites no source")
                )
        for canonical_id, missing in sorted(self.missing_spellings.items()):
            for style in missing:
                gaps.append(
                    CoverageGap(
                        "missing-spelling",
                        canonical_id,
                        f"no {style} form declared, so it cannot be searched",
                    )
                )
        for canonical_id in sorted(self.out_of_window):
            gaps.append(
                CoverageGap("out-of-window", canonical_id, "released before the trailing window")
            )
        for canonical_id in sorted(self.window_unknown):
            gaps.append(
                CoverageGap(
                    "unknown-release-date",
                    canonical_id,
                    "no release date, counted as in-window",
                )
            )
        return gaps

    def summary(self) -> str:
        lines = [
            f"models   : {self.models_inserted} inserted, "
            f"{self.models_updated} updated, {self.models_unchanged} unchanged",
            f"aliases  : {self.aliases_inserted} inserted, "
            f"{self.aliases_existing} already present, "
            f"{self.aliases_closed} superseded and closed (append-only)",
            f"tiers    : {self.price_tiers_written} price bands written",
            f"events   : {len(self.events)}",
        ]
        for event_type, detail in self.events:
            lines.append(f"           {event_type}: {detail}")
        if self.out_of_window:
            lines.append(
                f"window   : {len(self.out_of_window)} outside the trailing window: "
                f"{', '.join(sorted(self.out_of_window))}"
            )
        if self.window_unknown:
            lines.append(
                f"window   : {len(self.window_unknown)} with no release date, counted "
                f"as in-window: {', '.join(sorted(self.window_unknown))}"
            )
        for canonical_id, missing in sorted(self.missing_spellings.items()):
            lines.append(f"spelling : {canonical_id} has no {', '.join(missing)} form")
        if self.unsourced_fields:
            lines.append(
                f"FR-2 gap : {self.unsourced_field_count} populated field(s) with no "
                f"source, across {len(self.unsourced_fields)} model(s)"
            )
            for canonical_id, fields in sorted(self.unsourced_fields.items()):
                lines.append(f"           {canonical_id}: {', '.join(fields)}")
        return "\n".join(lines)


def _sources_json(model: SeedModel) -> dict[str, dict[str, Any]]:
    """FR-2's `{field: {url, retrieved_at}}`, plus whether the URL is a
    provider page.

    `provider_page` reaches the database rather than staying in the YAML,
    because a cost estimate built on a third-party price decays silently and
    the answer path has no other way to know.
    """
    return {
        field_name: {
            "url": ref.url,
            "retrieved_at": ref.retrieved_at.isoformat(),
            "provider_page": ref.provider_page,
        }
        for field_name, ref in model.sources.items()
    }


def model_row(
    model: SeedModel,
    *,
    provenance: str = "seed",
    as_of: date | None = None,
    policy: RegistryPolicy | None = None,
) -> dict[str, Any]:
    """The `model_version` row for one seeded model.

    `as_of` is explicit so the window boundary can be pinned in a test. It
    defaults to today because that is what a nightly run means, not because
    the caller may safely ignore it.
    """
    policy = policy or load_registry_policy()
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
        # FR-1. A function of today's date, so it is stale the day after it
        # is written and `registry recompute-window` refreshes it nightly.
        "in_window": in_window(
            model.release_date,
            as_of=as_of or date.today(),
            months=policy.in_window_months,
        ),
    }


def _changed_fields(existing: dict[str, Any], incoming: dict[str, Any]) -> list[str]:
    """Which written columns differ. `id` is derived, so it never differs."""
    changed = []
    for column in _MODEL_COLUMNS:
        # `id` is derived, and `in_window` belongs to the recompute job, so
        # neither is something this loader changed.
        if column == "id" or column in _NEVER_UPDATED:
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

    if (
        existing is not None
        and existing["provenance"] == "polled"
        and row["provenance"] == "seed"
    ):
        raise ProvenanceDowngradeError([row["canonical_id"]])

    params = dict(row)
    params["sources"] = Json(row["sources"])

    placeholders = ", ".join(f"%({column})s" for column in _MODEL_COLUMNS)
    columns = ", ".join(_MODEL_COLUMNS)
    updatable = [
        c for c in _MODEL_COLUMNS if c not in ("id", "canonical_id", *_NEVER_UPDATED)
    ]
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


def _record_prices(conn: psycopg.Connection[Any], row: dict[str, Any]) -> datetime | None:
    """Append to `pricing_history` when prices are new or have moved.

    Returns the `observed_at` of the row it wrote, or None when it wrote
    nothing. That timestamp becomes the event's `occurred_at`, which ties an
    event to the observation that revealed it.

    This no longer decides whether a *change* happened. It used to, and it
    got it wrong: with no history row but an existing model, it reported a
    price-change for a price that had never moved. Whether prices moved is a
    question about `model_version`, and `_changed_fields` already answers it.
    """
    if all(row[column] is None for column in _PRICE_COLUMNS):
        # A row of three NULLs asserts nothing. Open-weight models priced by
        # the host rather than the provider would otherwise accumulate one
        # empty history row per run.
        return None

    from psycopg.rows import dict_row

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT price_in, price_out, price_cached_read FROM pricing_history "
            "WHERE model_version_id = %s ORDER BY observed_at DESC LIMIT 1",
            (row["id"],),
        )
        latest = cur.fetchone()

    incoming = {c: row[c] for c in _PRICE_COLUMNS}
    if latest is not None and _prices_equal({c: latest[c] for c in _PRICE_COLUMNS}, incoming):
        return None

    cur = conn.execute(
        "INSERT INTO pricing_history (model_version_id, price_in, price_out, "
        "price_cached_read) VALUES (%s, %s, %s, %s) RETURNING observed_at",
        (row["id"], row["price_in"], row["price_out"], row["price_cached_read"]),
    )
    written = cur.fetchone()
    return written[0] if written else None


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
    *,
    occurred_at: datetime | date | None = None,
    payload: dict[str, Any] | None = None,
) -> str:
    """Append one `model_event`. Returns its id.

    **Event ids are not deterministic, and that is the fix.**

    They used to be `hash(model_version_id, type, detail)` where `detail` was
    a constant string like ``"google/gemini-2.5-flash: ['price_in']"`` -- no
    values, no timestamp. Every price move after the first hashed to an id
    already present and was dropped by `ON CONFLICT DO NOTHING`.
    `pricing_history` recorded the move, `model_event` did not, and alerting
    reads events, so FR-3 failed on its own acceptance criterion.

    Folding the observed values in would not have fixed it either: a price
    going 1.00 to 2.00 and later 1.00 to 2.00 again is the same tuple and
    still collapses. Only a timestamp separates them, and an id built from a
    timestamp is a UUID with extra steps -- it gives up the re-run
    idempotency that was the point of determinism, and buys nothing.

    A deterministic id encodes "this is the same fact". An event is not a
    fact, it is an occurrence, and two identical transitions on different
    days are two occurrences. So idempotency lives in the *condition* that
    decides whether an occurrence happened -- a comparison against stored
    state, which is directly testable -- and the id just names it.

    `occurred_at` is when the thing happened, as against `detected_at` which
    defaults to now. For a price change that is the observation which
    revealed it; for a new model it is the release date. Both are real
    timestamps rather than a restatement of when this code ran.
    """
    from psycopg.types.json import Json

    event_id = f"ev_{uuid4().hex[:16]}"
    conn.execute(
        "INSERT INTO model_event (id, model_version_id, type, occurred_at, payload) "
        "VALUES (%s, %s, %s, %s, %s)",
        (event_id, model_version_id_, event_type, occurred_at, Json(payload or {})),
    )
    return event_id


def _write_price_tiers(conn: psycopg.Connection[Any], model: SeedModel) -> int:
    """Replace this model's tier bands with what the seed file declares.

    Delete-then-insert rather than upsert, because a provider changing its
    band boundaries means the old bands no longer exist. Leaving a stale band
    behind would let a workload price against a boundary the provider has
    retired, which is the same class of error as a lowest-tier fallback.

    `pricing_history` is untouched: it records observations of
    `model_version` prices, and a tiered model has none.
    """
    from psycopg.types.json import Json

    if not model.price_tiers:
        return 0

    mv_id = model_version_id(model.canonical_id)
    conn.execute("DELETE FROM price_tier WHERE model_version_id = %s", (mv_id,))

    for tier in model.price_tiers:
        conn.execute(
            "INSERT INTO price_tier (model_version_id, dimension, min_tokens, "
            "max_tokens, price, price_cached_read, sources) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                mv_id,
                tier.dimension,
                tier.min_tokens,
                tier.max_tokens,
                tier.price,
                tier.price_cached_read,
                Json(
                    {
                        field: {
                            "url": ref.url,
                            "retrieved_at": ref.retrieved_at.isoformat(),
                            "provider_page": ref.provider_page,
                        }
                        for field, ref in tier.sources.items()
                    }
                ),
            ),
        )
    return len(model.price_tiers)


def _refuse_provenance_downgrade(
    conn: psycopg.Connection[Any], models: list[SeedModel]
) -> None:
    """Raise before writing anything if this load would downgrade polled rows."""
    rows = conn.execute(
        "SELECT canonical_id FROM model_version "
        "WHERE provenance = 'polled' AND canonical_id = ANY(%s)",
        ([m.canonical_id for m in models],),
    ).fetchall()
    if rows:
        raise ProvenanceDowngradeError([row[0] for row in rows])


def recompute_window(
    conn: psycopg.Connection[Any],
    *,
    as_of: date | None = None,
    policy: RegistryPolicy | None = None,
) -> dict[str, int]:
    """Refresh `model_version.in_window`. The sole writer of that column.

    `in_window` is a stored function of today's date, so it is stale the day
    after it is written and goes stale on days when nothing is loaded at all.
    Cron runs this nightly, after the load.

    Returns counts, so a caller can alert when the number moves further than
    a day's worth of releases would explain.
    """
    policy = policy or load_registry_policy()
    as_of = as_of or date.today()
    boundary = window_start(as_of, policy.in_window_months)

    cur = conn.execute(
        "UPDATE model_version SET in_window = computed.value, updated_at = now() "
        "FROM (SELECT id, (release_date IS NULL OR release_date >= %s) AS value "
        "      FROM model_version) AS computed "
        "WHERE model_version.id = computed.id AND model_version.in_window IS DISTINCT FROM "
        "      computed.value",
        (boundary,),
    )
    changed = cur.rowcount

    inside = conn.execute("SELECT count(*) FROM model_version WHERE in_window").fetchone()
    outside = conn.execute("SELECT count(*) FROM model_version WHERE NOT in_window").fetchone()

    # `in_window` for a model with no release date is an ASSUMPTION, not a
    # computation: FR-1 makes a missing model the worse error, so absence
    # resolves to "in". Reporting it inside the in-window count would let the
    # roster assert a window it cannot compute, which is exactly the shape of
    # gap the coverage page exists to show.
    assumed = conn.execute(
        "SELECT count(*) FROM model_version WHERE in_window AND release_date IS NULL"
    ).fetchone()

    return {
        "changed": changed,
        "in_window": int(inside[0]) if inside else 0,
        "out_of_window": int(outside[0]) if outside else 0,
        "assumed_in_window": int(assumed[0]) if assumed else 0,
    }


def _close_at(existing_from: date | None, incoming_from: date | None) -> date:
    """When a superseded alias row stops being valid.

    The new row's `valid_from`, never earlier than the old row's, so the
    closed interval can never be inverted. A corrected release date that
    moves *backwards* leaves the old row with a zero-length window, which is
    the honest record: we no longer believe it ever validly applied, and we
    have not rewritten what it claimed.
    """
    if incoming_from is None:
        return date.today()
    if existing_from is None:
        return incoming_from
    return max(existing_from, incoming_from)


def _sync_alias(conn: psycopg.Connection[Any], alias: AliasRow) -> str:
    """Append one alias, closing any live row it supersedes (FR-4).

    Reads before it writes. The old code inserted blind against
    `ON CONFLICT (id) DO NOTHING`, which cannot see that a *different* row
    already holds the same `normalized` for the same model, so a changed
    alias left two live rows claiming one surface at once.

    The only write this issues against an existing row is `valid_until`.
    Closing an interval does not rewrite what that row asserted about its own
    window, which is why it is the one write FR-4 permits. Nothing else is
    ever updated and nothing is ever deleted.

    Returns ``inserted``, ``unchanged`` or ``replaced``.
    """
    from psycopg.rows import dict_row

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT id, valid_from FROM model_alias "
            "WHERE normalized = %s AND model_version_id = %s AND valid_until IS NULL",
            (alias.normalized, alias.model_version_id),
        )
        live = cur.fetchall()

    if any(row["id"] == alias.id for row in live):
        return "unchanged"

    superseded = [row for row in live if row["id"] != alias.id]
    for row in superseded:
        conn.execute(
            "UPDATE model_alias SET valid_until = %s WHERE id = %s AND valid_until IS NULL",
            (_close_at(row["valid_from"], alias.valid_from), row["id"]),
        )

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

    # The rowcount matters. The live-row query above only sees rows with
    # `valid_until IS NULL`, so an alias belonging to a RETIRED model is
    # never "live" and this function would otherwise report a fresh insert
    # on every run while ON CONFLICT quietly did nothing. Reporting writes
    # that did not happen is how a load report stops being worth reading.
    if cur.rowcount == 0:
        return "unchanged"
    return "replaced" if superseded else "inserted"


def load_seed(
    conn: psycopg.Connection[Any],
    *,
    path: Any = None,
    strict_sources: bool = True,
    strict_spelling: bool = True,
    as_of: date | None = None,
) -> LoadReport:
    """Load `contract/seed_models.yaml` into the registry.

    Args:
        conn: an open connection. The caller commits.
        path: override the seed file, for tests.
        strict_sources: refuse to load any field that asserts a value without
            citing where it came from (FR-2). The seed file ships with known
            gaps; passing False loads anyway and records them in the report,
            where the coverage surface can show them.
        strict_spelling: refuse to load a model that cannot be found by one of
            the three renderings people write. Same escape hatch, same
            reason: the gap is real, it is recorded, and it is a contract
            fix rather than a code one.
    """
    from collect.registry.seed import check_source_coverage

    seed = load_seed_file(path)
    if strict_sources:
        check_source_coverage(seed)
    if strict_spelling:
        check_spelling_coverage(seed.models)

    aliases = all_alias_rows(seed.models)
    check_no_collisions(aliases)

    # Pre-flight, so the refusal can name every affected row rather than
    # whichever one the loop reached first.
    _refuse_provenance_downgrade(conn, seed.models)

    policy = load_registry_policy()
    window = window_report(
        seed.models, as_of=as_of or date.today(), months=policy.in_window_months
    )
    report = LoadReport(
        unsourced_fields=gaps_by_model(seed) if source_gaps(seed) else {},
        out_of_window=window.out_of_window,
        window_unknown=window.unknown,
        missing_spellings={g.canonical_id: g.missing for g in spelling_gaps(seed.models)},
    )

    for model in seed.models:
        row = model_row(model, provenance="seed", as_of=as_of, policy=policy)
        verdict, changed = _upsert_model(conn, row)

        if verdict == "inserted":
            report.models_inserted += 1
            _record_event(
                conn,
                row["id"],
                "new-model",
                occurred_at=model.release_date,
                payload={"canonical_id": model.canonical_id},
            )
            report.events.append(("new-model", model.canonical_id))
        elif verdict == "updated":
            report.models_updated += 1
        else:
            report.models_unchanged += 1

        # Whether prices moved is a question about `model_version`, and
        # `_changed_fields` has already answered it. Asking `pricing_history`
        # instead reported a change whenever a history row was missing.
        moved = [c for c in changed if c in _PRICE_COLUMNS]
        observed_at = _record_prices(conn, row)

        if moved and observed_at is not None:
            detail = f"{model.canonical_id}: {moved}"
            _record_event(
                conn,
                row["id"],
                "price-change",
                occurred_at=observed_at,
                payload={
                    "canonical_id": model.canonical_id,
                    "changed": moved,
                    "to": {c: str(row[c]) for c in moved},
                },
            )
            report.events.append(("price-change", detail))

    for model in seed.models:
        report.price_tiers_written += _write_price_tiers(conn, model)

    for alias in aliases:
        verdict = _sync_alias(conn, alias)
        if verdict == "inserted":
            report.aliases_inserted += 1
        elif verdict == "replaced":
            report.aliases_inserted += 1
            report.aliases_closed += 1
        else:
            report.aliases_existing += 1

    return report
