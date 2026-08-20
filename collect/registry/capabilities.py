"""Load `contract/capabilities.yaml` into `capability`. The table that blocks `claim`.

WHY THIS IS THE SMALLEST UNBLOCKING TASK IN THE REPOSITORY

`claim.capability_key` is `text NOT NULL REFERENCES capability(key)`, and
`capability` holds 0 rows. So **no claim can be inserted at all**, for any model,
from any platform, however good the extraction — the insert fails on a foreign
key. The twelve keys have been sitting in `contract/capabilities.yaml` since the
scaffold with nothing to put them in the table.

`docs/measurements/unwired-tables.md` classified it correctly and it is worth
repeating where the fix lives: *"Not deliberate, and cheap: `capability` blocks
`claim` through a foreign key, and `contract/capabilities.yaml` already holds the
twelve keys. A loader is small and nothing else can proceed without it."*

NOT A FIXTURE, AND NOT `judge/`'S
---------------------------------
The vocabulary is shared contract data, so the rows belong in production and
`assert_no_fixtures` does not look here. The loader is this lane's for the same
reason `sources.py` is: `collect/` owns turning `contract/` into rows, and
`judge/` reads them. `judge/config.py:capabilities()` already reads the same file
directly for the extraction prompt, which is correct and unaffected — the prompt
needs the keys before any database exists.

`sounds_like` IS NOT WRITTEN, AND THAT IS DELIBERATE
----------------------------------------------------
The table has `key`, `failure_mode`, `description`, `version`, `active`, and no
column for it. `sounds_like` is harvest vocabulary — it belongs to the query
contract and to whoever writes terms, not to the aggregation key. Adding a column
for it here would put two sources of truth for the search vocabulary one join
apart from each other.

`active` IS NOT DERIVED FROM ABSENCE
------------------------------------
A key that disappears from the YAML is **not** deactivated by this loader. It is
left as it was, and reported. Rule 6: a capability missing from a file somebody
edited is as likely to be an accident as a decision, and `claim` rows already
reference it — flipping `active` on absence would silently retire a capability
and every cell under it. Deactivation is a decision somebody makes, so it needs
its own edit rather than falling out of a deletion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml

from collect.config import CAPABILITIES_YAML

FAILURE_MODES = ("loud", "silent")


class CapabilityContractError(ValueError):
    """`contract/capabilities.yaml` does not say what the loader needs."""


@dataclass(frozen=True)
class CapabilityRow:
    """One `capability` row, as the contract declares it."""

    key: str
    failure_mode: str
    description: str
    version: str


@dataclass
class CapabilityLoadReport:
    """What one load did. Counts, and the two things worth naming."""

    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    #: Keys in the table that the contract no longer declares. NOT deactivated —
    #: see the module docstring. Named so the divergence is visible rather than
    #: silently corrected in either direction.
    absent_from_contract: list[str] = field(default_factory=list)
    version: str = ""

    @property
    def total(self) -> int:
        return self.inserted + self.updated + self.unchanged

    def summary(self) -> str:
        lines = [
            f"capability: {self.total} key(s) at contract version "
            f"{self.version or 'unversioned'} — {self.inserted} inserted, "
            f"{self.updated} updated, {self.unchanged} unchanged"
        ]
        if self.absent_from_contract:
            lines.append(
                f"  {len(self.absent_from_contract)} key(s) IN THE TABLE AND NOT IN "
                f"THE CONTRACT, left active and untouched: "
                f"{', '.join(sorted(self.absent_from_contract))}. Deactivating on "
                f"absence would retire a capability and every cell under it from a "
                f"file edit — say so deliberately instead."
            )
        return "\n".join(lines)


def parse_capabilities(document: dict[str, Any]) -> tuple[str, list[CapabilityRow]]:
    """Parse a loaded `capabilities.yaml`. Never reads the filesystem.

    Raises rather than defaulting on anything missing. A capability with no
    `failure_mode` cannot be defaulted to either value: `loud` would let a
    silent-failure capability publish on absence of criticism, and `silent`
    would demand positive consensus for one that errors in seconds. Both are
    wrong in a way that shows up as a cell nobody can explain.
    """
    version = str(document.get("version", "")).strip()
    if not version:
        raise CapabilityContractError(
            "capabilities.yaml declares no `version`. `capability.version` is "
            "NOT NULL and a taxonomy change has to be identifiable."
        )

    entries = document.get("capabilities")
    if not entries:
        raise CapabilityContractError(
            "capabilities.yaml declares no capabilities. An empty vocabulary "
            "would load zero rows and leave `claim`'s foreign key unsatisfiable, "
            "which is the state this loader exists to end."
        )

    rows: list[CapabilityRow] = []
    for entry in entries:
        key = str(entry.get("key", "")).strip()
        if not key:
            raise CapabilityContractError("a capability entry has no `key`")
        mode = str(entry.get("failure_mode", "")).strip()
        if mode not in FAILURE_MODES:
            raise CapabilityContractError(
                f"capability {key!r} has failure_mode {mode!r}; expected one of "
                f"{list(FAILURE_MODES)}. It drives how much evidence the answer "
                f"path demands, so it cannot be defaulted."
            )
        rows.append(
            CapabilityRow(
                key=key,
                failure_mode=mode,
                description=str(entry.get("description", "")).strip(),
                version=version,
            )
        )

    duplicates = {r.key for r in rows if sum(1 for x in rows if x.key == r.key) > 1}
    if duplicates:
        raise CapabilityContractError(
            f"duplicate capability key(s): {sorted(duplicates)}. Consensus "
            f"counting groups on this key, so two entries would split one cell."
        )
    return version, rows


def load_capability_file(path=None) -> tuple[str, list[CapabilityRow]]:
    """Read and parse the contract file."""
    target = path or CAPABILITIES_YAML
    raw = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    return parse_capabilities(raw)


def load_capabilities(conn, path=None) -> CapabilityLoadReport:
    """Upsert the vocabulary. Idempotent, and a re-run over an unchanged file
    reports `unchanged` rather than a stream of updates.

    Same discipline as `load_source_rows`: a second run has to be visibly a
    no-op, or a real change is impossible to spot in the report.
    """
    version, rows = load_capability_file(path)
    report = CapabilityLoadReport(version=version)

    existing = {
        r[0]: (r[1], r[2], r[3])
        for r in conn.execute(
            "SELECT key, failure_mode, description, version FROM capability"
        ).fetchall()
    }

    for row in rows:
        before = existing.get(row.key)
        conn.execute(
            """
            INSERT INTO capability (key, failure_mode, description, version)
            VALUES (%(key)s, %(failure_mode)s, %(description)s, %(version)s)
            ON CONFLICT (key) DO UPDATE SET
                failure_mode = EXCLUDED.failure_mode,
                description  = EXCLUDED.description,
                version      = EXCLUDED.version
            """,
            {
                "key": row.key,
                "failure_mode": row.failure_mode,
                "description": row.description,
                "version": row.version,
            },
        )
        if before is None:
            report.inserted += 1
        elif before == (row.failure_mode, row.description, row.version):
            report.unchanged += 1
        else:
            report.updated += 1

    declared = {r.key for r in rows}
    report.absent_from_contract = [k for k in existing if k not in declared]
    return report
