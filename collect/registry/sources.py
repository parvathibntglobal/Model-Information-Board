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

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache
from typing import Any

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

    #: Who read the terms. A ruling is a person's reading, and "somebody
    #: reviewed this" is not a fact anyone can follow up.
    reviewed_by: str | None = None

    #: The condition the ruling RESTS ON, not a description of it. A ruling
    #: with `basis: internal-development-only` stops applying when the
    #: deployment stops being internal — which is a different and much shorter
    #: fuse than `review_valid_days`. Where a basis is named it should also be
    #: a `live_precondition`, so the fuse is checked rather than remembered.
    basis: str | None = None

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

    #: The listing sweep's population, or None where the block is absent.
    #:
    #: ABSENT IS NOT EMPTY. A missing block means nobody has chosen a subreddit
    #: list, and a sweep over an empty list retrieves nothing and reports it as
    #: nobody discussing anything — the shape rule 4 exists for. `sweep_reddit`
    #: raises on None rather than sweeping zero subreddits.
    sweep_subreddits: dict[str, Any] | None = None

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


def _json_safe(value: Any) -> Any:
    """Dates become ISO strings, because `jsonb` has no date type.

    This is not cosmetic. `terms_evidence` round-trips through Postgres as
    JSON, so a `date` written today comes back as a string tomorrow. Leaving
    the contract side as `date` would make every row compare unequal to
    itself, reporting nine updates on every load and hiding the one row that
    genuinely changed — which is exactly the idempotency this is for.
    """
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _source_row(entry: Mapping[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {
        column: entry.get(column) for column in _SOURCE_COLUMNS
    }
    evidence = entry.get("terms_evidence") or {}
    # None rather than `{}` when nothing was measured, because that is what
    # gets written: `jsonb` NULL. Keeping `{}` here made `reddit` — the one
    # honestly unreviewed row — compare unequal to itself on every load and
    # report a phantom update forever.
    row["terms_evidence"] = _json_safe(dict(evidence)) if evidence else None
    # The column keeps a real `date`: it is queryable, and it is what
    # `assert_terms_reviewed` reads to decide whether the evidence is stale.
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
        reviewed_by=entry.get("reviewed_by"),
        basis=entry.get("basis"),
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
        # `or None`, not `or {}`: see the field comment. An empty mapping would
        # let a caller iterate zero subreddits and call that a sweep.
        sweep_subreddits=dict(document.get("sweep_subreddits") or {}) or None,
    )


@lru_cache(maxsize=1)
def load_sources() -> SourcesContract:
    """Read and parse `contract/sources.yaml`."""
    document = yaml.safe_load(SOURCES_YAML.read_text(encoding="utf-8"))
    return parse_sources(document)


# ============================================================================
#  Writing the rows
#
#  Kept here rather than in `collect/registry/load.py`, which is 700 lines of
#  model_version, pricing history and alias intervals. This is one table and
#  one upsert; splitting a small concern across two files to mirror the shape
#  of a large one costs more than it explains.
# ============================================================================


class SourceProvenanceConflictError(RuntimeError):
    """A seeded row and a discovered row collided on the same id.

    `model_version` refuses one direction: seed must never overwrite polled,
    because week 5's poller replaces the fixture and reversing that would make
    `assert_no_fixtures` refuse to boot over models that are perfectly real.
    Promotion the other way is the point of week 5, so it is allowed.

    `source` refuses **both** directions, because neither is a promotion.

      seed over discovered  a re-seed would replace a feed found by link —
                            including its terms ruling and the evidence
                            measured against *its* host — with a class ruling
                            made about somebody else's. That is the item 20
                            failure precisely: a value indistinguishable from
                            a vetted one, deciding whether we may fetch.

      discovered over seed  a link in harvested content would silently rewrite
                            a hand-reviewed row's ruling. Content we harvested
                            must never edit the terms under which we harvest.

    So it raises, before anything is written. A silent skip is how the seed
    file quietly stops matching the database, and nobody finds out until the
    two disagree about whether a host may be fetched at all.
    """

    def __init__(self, collisions: list[tuple[str, str, str]]) -> None:
        self.collisions = collisions
        listed = ", ".join(
            f"{source_id} (stored {stored!r}, incoming {incoming!r})"
            for source_id, stored, incoming in sorted(collisions)
        )
        super().__init__(
            f"Refusing to load: {len(collisions)} source row(s) would change "
            f"provenance: {listed}. A seeded row and a discovered row are not "
            "two versions of the same thing — they carry rulings made about "
            "different parties. Reconcile them by hand: either drop the row, "
            "or move the feed into contract/sources.yaml and re-run."
        )


@dataclass
class SourceLoadReport:
    """What one `load_source_rows` run did."""

    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    changed_columns: dict[str, list[str]] = field(default_factory=dict)

    #: ENTRIES THE CONTRACT OFFERED, counted upstream of `source_rows()`.
    #:
    #: A loader that reports only what it wrote cannot distinguish "wrote
    #: everything" from "wrote everything it could parse". `12 inserted` reads
    #: as complete whether the contract held 12 entries or 14, which is the same
    #: shape as a comparison that finds no rows and reports no differences.
    #:
    #: **The denominator has to come from upstream of the thing being checked.**
    #: Counting it off `source_rows()` would compare a number with itself and
    #: could never see a drop, so it is counted from the contract's own
    #: sections — `platforms` and `feeds` — and the two are compared.
    declared: int = 0

    #: Contract ids that were declared and did not reach a row. Empty today and
    #: named rather than inferred, so a future filter surfaces in the output
    #: instead of inside a count that looks finished.
    skipped: list[str] = field(default_factory=list)

    #: Rows written with no `terms_ruling`. Not an error — `reddit` is
    #: honestly unreviewed and its row still has to exist for the foreign key
    #: — but counted, because an unreviewed source that nobody notices is the
    #: failure this whole design is arranged against.
    unreviewed: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.inserted + self.updated + self.unchanged

    def summary(self) -> str:
        lines = [
            f"sources  : {self.total} of {self.declared} contract entries written "
            f"— {self.inserted} inserted, {self.updated} updated, "
            f"{self.unchanged} unchanged"
        ]
        if self.skipped:
            lines.append(
                f"SKIPPED  : {len(self.skipped)} declared entr(ies) never reached a "
                f"row: {', '.join(sorted(self.skipped))}. A source with no row "
                f"cannot be harvested and cannot carry a harvest_run — "
                f"`harvest_run.source_id` is a foreign key to `source(id)`."
            )
        for source_id, columns in sorted(self.changed_columns.items()):
            lines.append(f"           {source_id}: {', '.join(columns)}")
        if self.unreviewed:
            lines.append(
                f"NFR-5    : {len(self.unreviewed)} source(s) carry no terms "
                f"ruling and cannot be harvested: {', '.join(sorted(self.unreviewed))}"
            )
        return "\n".join(lines)


#: Written on insert and on update alike.
_WRITTEN_COLUMNS: tuple[str, ...] = (
    "id",
    "platform",
    "endpoint",
    "base_trust",
    "tos_notes",
    "provenance",
    "terms_ruling",
    "terms_checked_on",
    "terms_evidence",
)

#: Runtime state owned by the harvest, not by the contract. A re-seed that
#: reset these would erase FR-10's yield history at exactly the moment
#: somebody re-seeded to fix a terms ruling, and the yield alert would read
#: the reset as a source going quiet.
_NEVER_UPDATED: frozenset[str] = frozenset({"health_status", "last_yield"})


def _refuse_provenance_conflicts(conn, rows: list[dict[str, Any]]) -> None:
    """Raise before writing anything if any row would change provenance."""
    by_id = {row["id"]: row for row in rows}
    stored = conn.execute(
        "SELECT id, provenance FROM source WHERE id = ANY(%s)",
        (list(by_id),),
    ).fetchall()

    collisions = [
        (source_id, provenance, by_id[source_id]["provenance"])
        for source_id, provenance in stored
        if provenance != by_id[source_id]["provenance"]
    ]
    if collisions:
        raise SourceProvenanceConflictError(collisions)


def _changed_columns(existing: Mapping[str, Any], incoming: Mapping[str, Any]) -> list[str]:
    changed = []
    for column in _WRITTEN_COLUMNS:
        if column == "id" or column in _NEVER_UPDATED:
            continue
        before, after = existing.get(column), incoming.get(column)
        if isinstance(before, float) or isinstance(after, float):
            # `base_trust` is `real`, so Postgres hands back a float that is
            # not bit-identical to the YAML's 0.9. Comparing raw would report
            # every row as updated on every load, which makes the idempotency
            # this exists to provide unobservable.
            before = None if before is None else round(float(before), 6)
            after = None if after is None else round(float(after), 6)
        if before != after:
            changed.append(column)
    return changed


def load_source_rows(conn, contract: SourcesContract | None = None) -> SourceLoadReport:
    """Upsert the contract's source rows. Idempotent, and safe to re-run.

    `source` is re-seeded every time a terms ruling changes, so a second run
    over an unchanged contract must be a no-op that says so — not a stream of
    updates that makes a real change impossible to spot in the report.

    Discovered feeds are inserted into `source` directly and are not in the
    contract, so this never sees them; `_refuse_provenance_conflicts` is what
    stops a re-seed from walking over one that took the same id.
    """
    from psycopg.rows import dict_row
    from psycopg.types.json import Json

    contract = contract or load_sources()
    rows = contract.source_rows()
    report = SourceLoadReport()

    # Counted from the contract's own sections rather than from `rows`, so the
    # comparison has an independent denominator. `len(rows)` against `len(rows)`
    # is a check that cannot fail.
    declared_ids = [
        entry.get("id") for entry in (*contract.platforms, *contract.feeds)
    ]
    report.declared = len(declared_ids)
    written_ids = {row.get("id") for row in rows}
    report.skipped = [
        source_id for source_id in declared_ids if source_id not in written_ids
    ]

    _refuse_provenance_conflicts(conn, rows)

    columns = ", ".join(_WRITTEN_COLUMNS)
    placeholders = ", ".join(f"%({column})s" for column in _WRITTEN_COLUMNS)
    updatable = [c for c in _WRITTEN_COLUMNS if c != "id" and c not in _NEVER_UPDATED]
    assignments = ", ".join(f"{c} = EXCLUDED.{c}" for c in updatable)

    for row in rows:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM source WHERE id = %s", (row["id"],))
            existing = cur.fetchone()

        params = {column: row[column] for column in _WRITTEN_COLUMNS}
        params["terms_evidence"] = (
            Json(row["terms_evidence"]) if row["terms_evidence"] else None
        )

        conn.execute(
            f"INSERT INTO source ({columns}) VALUES ({placeholders}) "
            f"ON CONFLICT (id) DO UPDATE SET {assignments}",
            params,
        )

        if not row.get("terms_ruling"):
            report.unreviewed.append(row["id"])

        if existing is None:
            report.inserted += 1
            continue
        changed = _changed_columns(existing, row)
        if changed:
            report.updated += 1
            report.changed_columns[row["id"]] = changed
        else:
            report.unchanged += 1

    return report


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
