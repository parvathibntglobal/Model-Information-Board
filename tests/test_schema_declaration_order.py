"""Every foreign key's target must be CREATEd before the table that references it.

WHY THIS TEST EXISTS
--------------------
`contract/tables.sql` is applied top to bottom by `collect.db.apply_schema`, so a
table whose `REFERENCES` points at something declared later fails with
`UndefinedTable` — and it fails at `apply_schema`, which is the FIRST thing every
DB-backed test fixture calls. One misplaced table therefore produced 240 errors
across 25 files, all of them reading `relation "claim" does not exist` and none
of them pointing at the table that was actually wrong.

`board_entry` was inserted next to `capability_candidate`, a hundred lines above
`CREATE TABLE claim`, and it carries `claim_id text REFERENCES claim(id)`.

WHY IT IS A STRING TEST AND NOT A DATABASE ONE
----------------------------------------------
`tests/test_migrations.py` would have caught it, and does — but only where a
Postgres is reachable, which is CI and not most local runs. This reads the file,
so it fails in one second on any machine, and it fails NAMING THE TABLE AND THE
TARGET rather than reporting a missing relation from inside a fixture.

That is the actual defect being fixed: not the ordering, which was a typo-class
mistake, but that nothing cheap could tell anybody which table caused it.
"""

from __future__ import annotations

import re
from pathlib import Path

TABLES_SQL = Path(__file__).resolve().parent.parent / "contract" / "tables.sql"

#: `CREATE TABLE foo (` — the declaration, wherever it sits in the file.
_CREATE = re.compile(r"^CREATE TABLE (?:IF NOT EXISTS )?([a-z_]+)\s*\(", re.M)

#: `REFERENCES foo(id)`, inline or in a table constraint. The target table is
#: what matters; the column is irrelevant to declaration order.
_REFERENCES = re.compile(r"\bREFERENCES\s+([a-z_]+)\s*\(", re.I)


def _sql() -> str:
    return TABLES_SQL.read_text(encoding="utf-8")


def _statement_bodies(sql: str) -> list[tuple[str, int, str]]:
    """(table, declaration offset, body) for every CREATE TABLE, in file order."""
    out = []
    starts = [(m.group(1), m.start()) for m in _CREATE.finditer(sql)]
    for idx, (name, start) in enumerate(starts):
        end = starts[idx + 1][1] if idx + 1 < len(starts) else len(sql)
        out.append((name, start, sql[start:end]))
    return out


def test_the_file_declares_the_tables_we_think_it_does():
    """A guard on the guard: a regex that matches nothing passes everything."""
    names = [n for n, _, _ in _statement_bodies(_sql())]
    assert len(names) > 20, f"only found {len(names)} CREATE TABLE statements"
    for expected in ("model_version", "document", "claim", "cell", "board_entry"):
        assert expected in names, f"{expected} not found; the regex has drifted"


def test_every_foreign_key_target_is_declared_first():
    """The ordering rule, stated once and checked over the whole file.

    A self-reference is allowed — `document.parent_id REFERENCES document(id)`
    is legal inside its own CREATE TABLE — so a table may reference itself.
    """
    sql = _sql()
    bodies = _statement_bodies(sql)
    declared_at = {name: offset for name, offset, _ in bodies}

    violations = []
    for name, offset, body in bodies:
        for target in {t.lower() for t in _REFERENCES.findall(body)}:
            if target == name:
                continue                       # self-reference, fine
            target_offset = declared_at.get(target)
            if target_offset is None:
                violations.append(
                    f"{name} REFERENCES {target}, which contract/tables.sql never "
                    f"declares at all"
                )
            elif target_offset > offset:
                violations.append(
                    f"{name} (line {sql[:offset].count(chr(10)) + 1}) REFERENCES "
                    f"{target}, declared LATER at line "
                    f"{sql[:target_offset].count(chr(10)) + 1}. apply_schema runs "
                    f"top to bottom, so this raises UndefinedTable on every "
                    f"DB-backed fixture."
                )

    assert not violations, (
        "foreign keys pointing at tables declared later:\n  "
        + "\n  ".join(violations)
    )
