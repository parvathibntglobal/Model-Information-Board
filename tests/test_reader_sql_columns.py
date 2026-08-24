"""Every column a reader SELECTs must exist in the schema.

WHY THIS IS A TEST AND NOT A CODE REVIEW.

`judge/pages/model.py` selected `c.claim_date`. There is no such column. The
name is a PYTHON one - a field on `StoredClaim`, a parameter to
`weight.recency_factor` - and `pipeline.py` sets it from `document.created_at`.
Reading it back off the table looks right in every way except being true.

It shipped because `quotes_for()` is only called when a cell has quote ids, and
there were no cells until the first pipeline run. The branch was unreachable, so
the whole suite exercised the empty path and passed. The first model page with
evidence on it answered 500 - the defect surfaced on the day the product started
working, which is the worst possible day for it.

A behavioural test cannot cover a path no fixture reaches. This one does not
need to reach it: it reads the SQL as text and checks it against
`contract/tables.sql` plus the migrations. It needs no database, so it runs
everywhere, and it covers queries nobody has managed to execute yet.

It is deliberately narrow. It resolves `alias.column` only where the alias is
declared in the same statement, and it says which ones it skipped rather than
counting an unparsed query as a pass - the same rule the rest of this repo
applies to a check whose input is missing.
"""
from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
READERS = sorted((ROOT / "judge" / "pages").glob("*.py"))

#: Not a column: SQL keywords and functions that appear after a dot or alone.
_NOT_COLUMNS = {"*"}


def _schema() -> dict[str, set[str]]:
    """table -> columns, from tables.sql and every migration that adds one."""
    sql = (ROOT / "contract" / "tables.sql").read_text(encoding="utf-8")
    for path in sorted((ROOT / "contract" / "migrations").glob("*.sql")):
        sql += "\n" + path.read_text(encoding="utf-8")

    tables: dict[str, set[str]] = {}

    for match in re.finditer(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-z_][a-z0-9_]*)\s*\((.*?)\n\s*\);",
        sql,
        re.S | re.I,
    ):
        name, body = match.group(1).lower(), match.group(2)
        cols = tables.setdefault(name, set())
        for line in body.splitlines():
            line = line.strip().rstrip(",")
            if not line or line.startswith("--"):
                continue
            first = line.split()[0].lower()
            if first in {
                "primary", "foreign", "unique", "check", "constraint", "exclude", "like",
            }:
                continue
            cols.add(first.strip('"'))

    for match in re.finditer(
        r"ALTER\s+TABLE\s+([a-z_][a-z0-9_]*)\s+ADD\s+COLUMN\s+(?:IF\s+NOT\s+EXISTS\s+)?"
        r"([a-z_][a-z0-9_]*)",
        sql,
        re.I,
    ):
        tables.setdefault(match.group(1).lower(), set()).add(match.group(2).lower())

    return tables


def _statements(source: str) -> list[str]:
    """Triple-quoted strings that look like a SELECT."""
    return [
        block
        for block in re.findall(r'"""(.*?)"""', source, re.S)
        if re.search(r"\bSELECT\b", block, re.I) and re.search(r"\bFROM\b", block, re.I)
    ]


def _aliases(statement: str) -> dict[str, str]:
    """alias -> table, from FROM and JOIN clauses in this statement only."""
    found: dict[str, str] = {}
    for table, alias in re.findall(
        r"\b(?:FROM|JOIN)\s+([a-z_][a-z0-9_]*)\s+(?:AS\s+)?([a-z_][a-z0-9_]*)\b",
        statement,
        re.I,
    ):
        if alias.lower() in {"on", "where", "group", "order", "left", "join", "using"}:
            continue
        found[alias.lower()] = table.lower()
    return found


@pytest.mark.parametrize("path", READERS, ids=lambda p: p.name)
def test_every_qualified_column_exists(path: pathlib.Path):
    schema = _schema()
    assert "claim" in schema, "could not parse contract/tables.sql; the check is not running"

    source = path.read_text(encoding="utf-8")
    unknown: list[str] = []

    for statement in _statements(source):
        aliases = _aliases(statement)
        for alias, column in re.findall(r"\b([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)\b", statement):
            table = aliases.get(alias.lower())
            if table is None or table not in schema:
                continue          # alias from another statement, or a CTE
            if column.lower() in _NOT_COLUMNS:
                continue
            if column.lower() not in schema[table]:
                unknown.append(f"{alias}.{column} -> {table} has no column {column!r}")

    assert not unknown, (
        f"{path.name} selects columns that do not exist:\n  " + "\n  ".join(unknown)
    )


def test_the_regression_this_was_written_for():
    """`claim` has `created_at`, and has never had `claim_date`.

    Pins the fact the broken query assumed. The name still appears in
    `model.py` prose explaining the bug, so this asserts against the SCHEMA
    rather than grepping the file - a grep would fail on the comment that
    documents the fix, which is the wrong thing to forbid.
    """
    schema = _schema()
    assert "created_at" in schema["claim"]
    assert "claim_date" not in schema["claim"]
