"""Load the reviewed tracked set into `model_alias`. The bulk path `seat-alias` refused.

`seat-alias` takes one canonical id because *"a bulk loader would defeat the
`INCOMPLETE` markers, and lowering the artifact's guard to admit one would defeat
it for all 63 entries at once."* That argument is answered here rather than
ignored, and not by selecting on `seated_by: attested` — **`status`, `seated_by`
and `incomplete` are all written by `to_yaml`.** They are the generator's
measurements, so a loader keyed on them admits every future entry the generator
labels attested with no human in the path.

WHAT REPLACES A PERSON TYPING AN ID
-----------------------------------
A **manifest**: the ids, the population count, and a fingerprint of each entry's
surfaces *as reviewed*. It is stricter than what `seat-alias` gives, not looser —
typing an id pins nothing about content, so an entry can change between the review
and the seat and nothing can tell. A fingerprint revokes the review for the entry
that moved, and only that one.

The honest limit, stated because it cannot be engineered away: a command can
write a manifest without anybody reviewing anything. The guarantee was never *"a
human read it"*. It is *"a human took a deliberate act naming this exact content,
and any later change to that content revokes it."*

NO UNDO, AND NOT BECAUSE IT IS HARD
-----------------------------------
`model_alias` is append-only under FR-4 and the only write the design permits
against an existing row is closing `valid_until`. So an undo could only be a
window close — and **a window close is a claim about the world, not a
retraction.** `mistral large` meaning `mistral-large-2411` until 2025-03-30 and
`mistral-large-3` after is exactly what that column is for. Closing a window to
undo a mistaken load would assert that a surface *stopped meaning* a model on the
day we noticed our error, and a March post would then resolve differently than it
should.

So the hazard is handled BEFORE the write: `plan()` reports every verdict and
every refusal and touches nothing, and a run that would supersede a live row
refuses unless told otherwise. In an append-only table, prevention is the only
reversal available.

SHIPS WITHOUT FAMILY SURFACES, DELIBERATELY
-------------------------------------------
`model_version.family` is NULL on all 342 registry rows — the poller lists
`family` in `UNAVAILABLE` beside `lifecycle` — and no derivation rule reproduces
even our own eleven curated values. So these seats carry version and snapshot
surfaces only. That is a **coverage** gap, not a correctness one: a mention
written as a bare `sonnet` is not retrieved, and nothing published becomes wrong.

**And a family surface added later is an INSERT beside these rows, not a rewrite
of them** — which is the same append-only property that makes an undo impossible.
`tests/test_load_tracked_set.py` confirms that rather than assuming it: a second
load of the same manifest with a family surface added adds one row and leaves
every existing row untouched, `valid_until` still NULL.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from collect.registry.aliases import AliasRow, check_no_collisions
from collect.registry.seat import (
    DEFAULT_ARTIFACT,
    ReviewedEntry,
    SeatRefused,
    read_entry,
    rows_for,
)

#: Beside the artifact rather than in `contract/`. It is a record of a review, and
#: `contract/` is the shared interface between two people — an addition there wants
#: flagging and scheduling, and this loader is explicitly the thing that must not
#: wait on a contract decision nobody has scheduled. Relocatable later; the format
#: is the same either way.
DEFAULT_MANIFEST = DEFAULT_ARTIFACT.parent / "reviewed-seats.yaml"

PROVISIONAL = "launch-window"
ATTESTED = "attested"

#: The same shapes `tests/test_tracked_set_seating.py` reads, because the mention
#: counts live in trailing comments rather than in keys. Both parses are SIZED:
#: a format change drops the counts to zero, and a check over an empty set passes.
_MENTIONS = re.compile(
    r"^\s+(?:surface:|- )\s*(.+?)\s+# attested (\d+) mentions(?: \[([^\]]*)\])?", re.M
)
_SEATED_BY = re.compile(r"seated_by:\s*(\S+)")
_FLOOR = re.compile(r"^\s+mention_floor:\s*(\d+)", re.M)


class LoadRefused(RuntimeError):
    """The load cannot proceed, and the message carries every reason at once.

    One reason per run turns a five-minute fix into five runs, and the refusals
    here are independent — a fingerprint that drifted says nothing about whether
    some other entry collides.
    """

    def __init__(self, reasons: list[str]) -> None:
        self.reasons = reasons
        listed = "\n  - ".join(reasons)
        super().__init__(
            f"load refused, {len(reasons)} reason(s), nothing written:\n  - {listed}"
        )


def entry_fingerprint(entry: ReviewedEntry) -> str:
    """A hash of what a reviewer accepted: the primary surface and its variants.

    Order-sensitive on purpose. `to_yaml` emits the primary first and the reseats
    turn on WHICH surface is primary, so a reordering is a different review.
    """
    payload = "\n".join([entry.surface, *entry.variants])
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Manifest:
    """A review that happened, recorded as a set rather than as 41 dates."""

    path: Path
    artifact: str
    reviewed_at: str
    reviewed_by: str
    population: int
    seats: dict[str, str]
    finding: str = ""

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(self.seats)


def read_manifest(path: Path | None = None) -> Manifest:
    """Read the manifest, refusing anything that would make it decorative."""
    target = path or DEFAULT_MANIFEST
    if not target.exists():
        raise LoadRefused([
            f"{target} does not exist. The manifest is the record that a review "
            f"happened; without one this command has no population and the "
            f"artifact's own fields are generator output, not a review."
        ])
    raw = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    seats = raw.get("seats") or {}
    if not isinstance(seats, dict) or not seats:
        raise LoadRefused([
            f"{target.name} has no `seats:` mapping. Zero seats and a missing key "
            f"look identical in a count, so this refuses rather than loading nothing."
        ])
    missing = [k for k in ("reviewed_at", "reviewed_by", "population") if k not in raw]
    if missing:
        raise LoadRefused([
            f"{target.name} is missing {', '.join(missing)}. A review with no date "
            f"and no author is not a review anybody can audit."
        ])
    return Manifest(
        path=target,
        artifact=str(raw.get("artifact") or DEFAULT_ARTIFACT.name),
        reviewed_at=str(raw["reviewed_at"]),
        reviewed_by=str(raw["reviewed_by"]),
        population=int(raw["population"]),
        seats={str(k): str(v) for k, v in seats.items()},
        finding=str(raw.get("finding") or ""),
    )


def _artifact_text(path: Path | None) -> str:
    target = path or DEFAULT_ARTIFACT
    if not target.exists():
        raise LoadRefused([f"{target} does not exist; run `registry propose-aliases` first"])
    return target.read_text(encoding="utf-8")


def mention_floor(artifact_path: Path | None = None) -> int:
    """The floor, read from the artifact's own `policy:` header (rule 7).

    Not a constant here. A threshold copied into a checker is a second place for
    it to be wrong, and this one has already misfired once for being far from the
    seats it explains.
    """
    match = _FLOOR.search(_artifact_text(artifact_path))
    if not match:
        raise LoadRefused([
            "no `policy: mention_floor:` in the artifact. `seated_by: "
            "launch-window` means 'below the floor', and which floor is the whole "
            "question — so this refuses rather than assuming one."
        ])
    return int(match.group(1))


def provisional_violations(
    artifact_path: Path | None = None, *, only: set[str] | None = None
) -> list[tuple[str, str, int]]:
    """Entries seated by the launch window that already clear the mention floor.

    **The provisional check, in library code.** It has lived only in
    `tests/test_tracked_set_seating.py`, reading the same file — and a loader that
    re-derived the condition would be the second implementation of one question,
    which is why `unfinished()` exists as a function. The condition is Engineer
    2's: `launch-window` AND `mentions >= floor` means the entry qualifies BY
    COUNT and was not credited for it.

    Returns `(canonical_id, top_surface, total_mentions)`. Empty is the honest
    result today and the reason to build it now: it is vacuous for entries seated
    by attestation, and the day the launch-window entries are ruled on it is not.
    """
    text = _artifact_text(artifact_path)
    floor = mention_floor(artifact_path)
    blocks = re.split(r"\n  - canonical_id: ", text)[1:]
    if not blocks:
        raise LoadRefused([
            "parsed 0 entries out of the artifact. The format changed and this "
            "check would otherwise pass over an empty set (habit 4)."
        ])

    out: list[tuple[str, str, int]] = []
    for block in blocks:
        canonical_id = block.split("\n")[0].strip()
        if only is not None and canonical_id not in only:
            continue
        seat = _SEATED_BY.search(block)
        if not seat or seat.group(1) != PROVISIONAL:
            continue
        counted = [(s.strip(), int(n)) for s, n, _ in _MENTIONS.findall(block)]
        total = sum(n for _, n in counted)
        if counted and total >= floor:
            out.append((canonical_id, max(counted, key=lambda kv: kv[1])[0], total))
    return out


def _live_verdict(conn, alias: AliasRow) -> str:
    """What `_sync_alias` WOULD do, read without writing.

    Mirrors its SELECT deliberately: one implementation would be better and this
    one must not open a transaction, so the duplication is named here rather than
    left for a reader to notice.
    """
    live = conn.execute(
        "SELECT id FROM model_alias "
        "WHERE normalized = %s AND model_version_id = %s AND valid_until IS NULL",
        (alias.normalized, alias.model_version_id),
    ).fetchall()
    ids = {row[0] for row in live}
    if alias.id in ids:
        return "unchanged"
    return "replace" if ids else "insert"


@dataclass
class EntryPlan:
    """One manifest entry, validated, with what each of its rows would do."""

    canonical_id: str
    rows: list[AliasRow] = field(default_factory=list)
    verdicts: dict[str, str] = field(default_factory=dict)

    @property
    def counts(self) -> dict[str, int]:
        out = {"insert": 0, "unchanged": 0, "replace": 0}
        for verdict in self.verdicts.values():
            out[verdict] += 1
        return out


@dataclass
class LoadPlan:
    """Everything the run would do, and every reason it will not."""

    entries: list[EntryPlan] = field(default_factory=list)
    refusals: list[str] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        out = {"insert": 0, "unchanged": 0, "replace": 0}
        for entry in self.entries:
            for key, value in entry.counts.items():
                out[key] += value
        return out

    @property
    def supersedes(self) -> list[str]:
        return [
            f"{entry.canonical_id}: {surface!r}"
            for entry in self.entries
            for surface, verdict in entry.verdicts.items()
            if verdict == "replace"
        ]

    def summary(self) -> str:
        counts = self.counts
        return (
            f"plan     : {len(self.entries)} entr(ies), "
            f"{counts['insert']} insert, {counts['unchanged']} unchanged, "
            f"{counts['replace']} would supersede; {len(self.refusals)} refusal(s)"
        )


def plan(conn, manifest: Manifest, *, artifact_path: Path | None = None) -> LoadPlan:
    """Validate every entry and predict every row. **Writes nothing.**

    Two phases exist for the reason `harvest_run` and `job_run` have two: a
    refusal on entry 30 must not leave 29 loaded, and a partially loaded reviewed
    set is the state nobody can audit. So every guard runs over the whole
    population before the first write.
    """
    result = LoadPlan()

    if len(manifest.seats) != manifest.population:
        result.refusals.append(
            f"{manifest.path.name} declares population {manifest.population} and "
            f"carries {len(manifest.seats)} seats. A figure travels with its "
            f"denominator (rule 7), and a manifest that disagrees with itself may "
            f"have been edited by hand after the review."
        )

    # The provisional condition, over the SELECTED ids rather than the whole file:
    # the launch-window entries nobody has ruled on are not this run's business.
    for canonical_id, surface, total in provisional_violations(
        artifact_path, only=set(manifest.seats)
    ):
        result.refusals.append(
            f"{canonical_id} is seated by the launch window and {surface!r} already "
            f"has {total} mentions, at or above the floor. It qualifies BY COUNT and "
            f"was not credited for it, so `seated_by` understates the evidence — "
            f"reseat as attested, or record why the mentions do not attribute."
        )

    for canonical_id, expected in manifest.seats.items():
        try:
            entry = read_entry(canonical_id, artifact_path)
        except SeatRefused as refusal:
            result.refusals.append(f"{canonical_id}: {refusal}")
            continue

        if entry.blocking_incomplete:
            result.refusals.append(
                f"{canonical_id} still has incomplete slot(s): "
                f"{', '.join(entry.blocking_incomplete)}. `family_surface` is "
                f"permanent by design and does not block; anything else means the "
                f"review is unfinished."
            )
            continue

        actual = entry_fingerprint(entry)
        if expected != actual:
            result.refusals.append(
                f"{canonical_id} has changed since it was reviewed — manifest holds "
                f"{expected[:19]}…, artifact yields {actual[:19]}…. The review "
                f"covered content that is no longer there, so it is revoked for this "
                f"entry and for no other. Re-review and re-attest."
            )
            continue

        try:
            rows = rows_for(conn, entry)
        except SeatRefused as refusal:
            result.refusals.append(f"{canonical_id}: {refusal}")
            continue

        if not rows:
            result.refusals.append(
                f"{canonical_id} produced no alias rows from {entry.surface!r} and "
                f"{len(entry.variants)} variant(s). Zero rows and no entry look "
                f"identical in a count."
            )
            continue

        result.entries.append(
            EntryPlan(
                canonical_id=canonical_id,
                rows=rows,
                verdicts={row.surface: _live_verdict(conn, row) for row in rows},
            )
        )

    # ── the collision check across the UNION, which per-entry seating never did ──
    #
    # `check_no_collisions` runs inside `seat()` over one entry's rows. Nothing has
    # ever seated two models in one operation, so two entries claiming one
    # normalised surface has never been checkable. Over 41 entries it is the most
    # likely single failure, and it must fail before the first insert rather than
    # on row 300.
    if result.entries:
        try:
            check_no_collisions([row for entry in result.entries for row in entry.rows])
        except Exception as collision:  # AliasCollisionError, named by its own message
            result.refusals.append(
                f"two or more entries in this manifest claim one surface: {collision}"
            )
    return result


@dataclass
class LoadReport:
    """What was written. Verdicts come from `_sync_alias`, not from the plan."""

    models: int = 0
    inserted: int = 0
    unchanged: int = 0
    replaced: int = 0
    searchable: int = 0

    def summary(self) -> str:
        return (
            f"loaded   : {self.models} model(s), {self.inserted} alias row(s) "
            f"inserted, {self.unchanged} unchanged, {self.replaced} superseded, "
            f"{self.searchable} search-eligible"
        )


def load(
    conn,
    manifest: Manifest,
    *,
    artifact_path: Path | None = None,
    allow_supersede: bool = False,
) -> LoadReport:
    """Write the plan, or refuse and write nothing.

    `allow_supersede` is the whole of what replaces the generator's `--force`, and
    it guards a narrower thing on purpose. An INSERT is additive and safe; a
    supersede closes a window some earlier run opened, which is FR-4's one
    permitted write against an existing row and not something a bulk path should
    do silently.
    """
    from collect.registry.load import _sync_alias

    prepared = plan(conn, manifest, artifact_path=artifact_path)
    if prepared.refusals:
        raise LoadRefused(prepared.refusals)

    if prepared.supersedes and not allow_supersede:
        raise LoadRefused([
            "this run would supersede "
            f"{len(prepared.supersedes)} live alias row(s): "
            + "; ".join(prepared.supersedes[:5])
            + ("; …" if len(prepared.supersedes) > 5 else "")
            + ". Closing a window asserts that a surface stopped meaning a model, "
            "which is a claim about the world rather than a correction. Pass "
            "--allow-supersede if that is what you mean."
        ])

    report = LoadReport(models=len(prepared.entries))
    for entry in prepared.entries:
        for row in entry.rows:
            verdict = _sync_alias(conn, row)
            if verdict == "inserted":
                report.inserted += 1
            elif verdict == "replaced":
                report.inserted += 1
                report.replaced += 1
            else:
                report.unchanged += 1
            if row.search_eligible:
                report.searchable += 1
    return report
