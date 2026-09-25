"""Seat one reviewed model's alias surfaces. The artifact's missing consumer.

`registry propose-aliases` writes a reviewable artifact and **nothing has ever
read it back**. The only writer of `model_alias` is `load_seed`, which reads
`contract/seed_models.yaml` — a build fixture `assert_no_fixtures` refuses
outside development. So the reviewed list had no path into the database, and the
machinery built for seating produced a file a human reads and a database never
sees. Fifth producer-with-no-consumer on this project.

ONE MODEL AT A TIME, NAMED, AND THAT IS THE DESIGN RATHER THAN A LIMITATION
---------------------------------------------------------------------------
`to_yaml` gives every entry an `INCOMPLETE` slot on purpose: *"a generated list
that could be merged unread is the failure this format exists to prevent."*
A bulk loader would defeat that, and lowering the artifact's guard to admit one
would defeat it for all 63 entries at once.

So this takes a canonical id. A person names the model they have reviewed, the
loader finds that entry, and nothing else moves. `family_surface` stays
`INCOMPLETE` forever by design (a bare `opus` is attested constantly and
attributable to no single model), so it is the one slot that does not block a
seat — and any OTHER incomplete slot refuses, because it means the reviewer has
not finished.

THE FACTS COME FROM THE REGISTRY, THE SURFACES FROM THE ARTIFACT
----------------------------------------------------------------
`alias_rows` needs a provider, a family, and a validity window as well as the
surfaces. Taking those from the artifact would be taking them from a proposal;
taking them from `model_version` takes them from the poller. So the row is
assembled from both, and a model absent from `model_version` cannot be seated at
all — which is the honest failure, because an alias pointing at no model
version is a foreign key waiting to happen.

`provenance` is not on `model_alias`. Worth knowing rather than working around:
these rows are indistinguishable from ones `load_seed` wrote, and the seat is
identifiable only by what is NOT in `seed_models.yaml`. Raised rather than
patched — a column is a contract change.

NO MODEL PARTICIPATES. A YAML read, a registry read, and string transformations
that already existed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from collect.config import CONTRACT_DIR
from collect.registry.aliases import AliasRow, alias_rows, check_no_collisions

#: The artifact `registry propose-aliases` writes.
DEFAULT_ARTIFACT = CONTRACT_DIR.parent / "docs" / "proposals" / "alias-surfaces-tracked-set.yaml"

#: The one slot that stays INCOMPLETE by design and therefore does not block a
#: seat. See `propose.py`: a bare family word is attested constantly and
#: attributable to no single model, so a gate demanding one could only be
#: satisfied by asserting an attribution the data refuses.
PERMANENT_INCOMPLETE = "family_surface"

_ENTRY = re.compile(r"\n  - canonical_id: (?P<id>\S+)")
_SURFACE = re.compile(r"^    surface:\s*(?P<v>.+?)\s*(?:#.*)?$", re.M)
_VARIANT = re.compile(r"^      - (?P<v>.+?)\s*(?:#.*)?$", re.M)
_INCOMPLETE = re.compile(r"^    incomplete:\s*\[(?P<v>[^\]]*)\]", re.M)


class SeatRefused(RuntimeError):
    """The seat cannot be taken, and the message says which of five reasons."""


@dataclass(frozen=True)
class ReviewedEntry:
    """One artifact entry, as reviewed."""

    canonical_id: str
    surface: str
    variants: tuple[str, ...]
    incomplete: tuple[str, ...]

    @property
    def blocking_incomplete(self) -> tuple[str, ...]:
        return tuple(s for s in self.incomplete if s != PERMANENT_INCOMPLETE)


def read_entry(canonical_id: str, path: Path | None = None) -> ReviewedEntry:
    """Find one entry in the artifact. Refuses rather than returning None.

    PARSED FROM PROSE, and that is a known cost stated rather than hidden.
    `to_yaml` writes mention counts into trailing comments, so the file is not
    round-trippable through `yaml.safe_load` for everything this needs. Every
    pattern below is anchored and the parse is SIZED — an entry that yields no
    surface raises instead of seating nothing, because zero surfaces and no
    entry look identical in a row count (habit 4).

    The durable fix is a machine-readable artifact. That is a change to the file
    a human is reviewing, so it is proposed rather than taken.
    """
    target = path or DEFAULT_ARTIFACT
    if not target.exists():
        raise SeatRefused(f"{target} does not exist; run `registry propose-aliases` first")

    text = target.read_text(encoding="utf-8")
    blocks = re.split(_ENTRY, text)
    # re.split with one group yields [pre, id, body, id, body, ...]
    found: dict[str, str] = {}
    for i in range(1, len(blocks) - 1, 2):
        found[blocks[i].strip()] = blocks[i + 1]

    if canonical_id not in found:
        raise SeatRefused(
            f"{canonical_id!r} is not in {target.name}. The artifact holds "
            f"{len(found)} entries, cut to the tracked set — a model outside "
            f"that set has no reviewed surfaces to seat, and inventing them "
            f"here is what the artifact exists to prevent."
        )

    body = found[canonical_id]
    surface = _SURFACE.search(body)
    if surface is None or surface.group("v").strip() == "INCOMPLETE":
        raise SeatRefused(
            f"{canonical_id} has no reviewed primary surface (reads "
            f"{surface.group('v').strip() if surface else 'nothing'}). Nothing "
            f"in the corpus was observed naming this model, so every form under "
            f"it is a derivation and a reviewer has to supply the judgement."
        )

    variants = tuple(
        v for v in (m.group("v").strip() for m in _VARIANT.finditer(body))
        if v and not v.startswith("#")
    )
    incomplete_match = _INCOMPLETE.search(body)
    incomplete = tuple(
        s.strip() for s in (incomplete_match.group("v").split(",") if incomplete_match else [])
        if s.strip()
    )
    return ReviewedEntry(canonical_id, surface.group("v").strip(), variants, incomplete)


@dataclass(frozen=True)
class _Seatable:
    """What `alias_rows` needs, assembled from the registry and the artifact.

    Deliberately NOT a `SeedModel`: constructing one would put artifact-sourced
    surfaces into the type whose whole meaning is "came from the build fixture",
    and `provenance` decisions are made by reading types like that.
    """

    canonical_id: str
    provider: str
    family: str | None
    release_date: date | None
    retirement_date: date | None
    aliases: object


@dataclass(frozen=True)
class _Aliases:
    surface: str
    variants: list[str]


def table_claims(conn, normalized_keys) -> list[AliasRow]:
    """Every row already in `model_alias` for these normalised keys, as AliasRows.

    ⚠ CLOSED ROWS INCLUDED, AND THAT IS THE FIX (#455). A row with a
      `valid_until` still claims its key for the window it covered, so a new
      seat whose window overlaps that one is two models on one surface over the
      same dates - exactly what `find_collisions` refuses. The collision that
      surfaced this was `fable5`: Claude Fable 5.1's CLOSED row (NULL
      `valid_from`, so open-ended before 2026-09-17) against Claude Fable 5's
      new one from 2026-06-09. A check against live rows only, by hand or in
      code, saw nothing.

    NULL `valid_from` is read as open-ended by `intervals_overlap` (date.min),
    never as "no claim". Only the fields `find_collisions` reads are filled;
    the rest are placeholders, because these rows are compared, never written.
    """
    keys = sorted({k for k in normalized_keys if k})
    if not keys:
        return []
    rows = conn.execute(
        "SELECT a.id, a.normalized, a.valid_from, a.valid_until, a.model_version_id, "
        "       COALESCE(v.canonical_id, a.model_version_id) "
        "FROM model_alias a LEFT JOIN model_version v ON v.id = a.model_version_id "
        "WHERE a.normalized = ANY(%s)",
        (keys,),
    ).fetchall()
    return [
        AliasRow(id=rid, surface=normalized, normalized=normalized, variants=[],
                 provider_hint=None, model_version_id=mv_id, family=None,
                 specificity="unknown", valid_from=valid_from, valid_until=valid_until,
                 canonical_id=canonical)
        for rid, normalized, valid_from, valid_until, mv_id, canonical in rows
    ]


def check_against_table(conn, rows: list[AliasRow]) -> None:
    """Refuse if any of `rows` shares a key with ANOTHER model's row over an
    overlapping window - new rows against each other and against the table.

    Same-model rows are skipped by `find_collisions` (a model holding one
    surface across two windows is the append-only handover), so re-seating a
    model does not collide with itself.
    """
    check_no_collisions([*rows, *table_claims(conn, (r.normalized for r in rows))])


def rows_for(conn, entry: ReviewedEntry) -> list[AliasRow]:
    """Build the alias rows. Facts from `model_version`, surfaces from the artifact."""
    row = conn.execute(
        "SELECT provider, family, release_date, retirement_date "
        "FROM model_version WHERE canonical_id = %s",
        (entry.canonical_id,),
    ).fetchone()
    if row is None:
        raise SeatRefused(
            f"{entry.canonical_id} is not in `model_version`. An alias pointing "
            f"at no model version is a foreign key waiting to happen — poll "
            f"first, or the id is wrong."
        )
    provider, family, release_date, retirement_date = row
    seatable = _Seatable(
        canonical_id=entry.canonical_id,
        provider=provider,
        family=family,
        release_date=release_date,
        retirement_date=retirement_date,
        aliases=_Aliases(surface=entry.surface, variants=list(entry.variants)),
    )
    return alias_rows(seatable)  # type: ignore[arg-type]


def seat(conn, canonical_id: str, *, path: Path | None = None) -> dict[str, object]:
    """Seat one reviewed model. Returns what was written.

    Refuses on any blocking `INCOMPLETE` slot, on a missing entry, on a missing
    primary surface, on a model absent from `model_version`, and on a collision
    with an alias another model holds over an overlapping window, live or closed
    (#455) — five reasons, each named.
    """
    entry = read_entry(canonical_id, path)
    if entry.blocking_incomplete:
        raise SeatRefused(
            f"{canonical_id} still has incomplete slot(s): "
            f"{', '.join(entry.blocking_incomplete)}. `{PERMANENT_INCOMPLETE}` "
            f"is permanent and does not block; anything else means the review "
            f"is unfinished."
        )

    rows = rows_for(conn, entry)
    if not rows:
        raise SeatRefused(
            f"{canonical_id} produced no alias rows from surface "
            f"{entry.surface!r} and {len(entry.variants)} variant(s). Zero rows "
            f"and no entry look identical in a count, so this refuses."
        )
    # AGAINST THE TABLE, NOT ONLY THE NEW ROWS (#455). The docstring above has
    # always promised "a collision with an alias already live for a different
    # model"; until 2026-09-25 this compared the new model's rows with each other.
    check_against_table(conn, rows)

    from collect.registry.load import _sync_alias

    written = [_sync_alias(conn, alias) for alias in rows]
    return {
        "canonical_id": canonical_id,
        "surface": entry.surface,
        "rows": len(rows),
        "searchable": sum(1 for r in rows if r.search_eligible),
        "verdicts": written,
    }
