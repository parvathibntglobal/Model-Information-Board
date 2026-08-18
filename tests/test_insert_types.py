"""Every INSERT in `judge/` passes a type Postgres will accept.

WHY THIS EXISTS, AND WHY IT IS GENERATED FROM THE SCHEMA

Three CI failures in a row were the same defect wearing different column types:
a value handed to Postgres in a shape it refuses. Missing NOT NULL columns,
then `int4range` given a list, then `interval` given an integer.

Each time I widened a hand-written check to cover the type that had just
failed, and each time the next failure was a type the widened check still did
not know about. **A check enumerating the cases it has already seen is a
changelog, not a check.**

So this reads the schema, finds every column whose type Python does NOT map to
directly, and asserts the writer wraps it. Adding a `numeric` or a `bytea`
column to a table `judge/` writes makes this fail without anybody remembering
to widen anything.

It runs without a database, which is the point — the whole class it covers was
only ever caught by a Postgres round trip.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = (ROOT / "contract" / "tables.sql").read_text(encoding="utf-8")

#: Types psycopg maps from a plain Python value with no wrapper.
DIRECTLY_MAPPED = {
    "text", "varchar", "char",
    "boolean", "bool",
    "int", "integer", "int2", "int4", "int8", "bigint", "smallint", "serial",
    "real", "float", "float4", "float8", "double",
    "date", "timestamptz", "timestamp", "time",
}

#: How a non-trivial type must be supplied, and what goes wrong otherwise.
#: The message is the finding, not the rule — somebody hitting this needs the
#: consequence, not a lecture.
WRAPPER_FOR = {
    "jsonb": ("Json(", "a dict is sent as text and the column refuses it"),
    "json": ("Json(", "a dict is sent as text and the column refuses it"),
    "int4range": ("Range(", "a list is sent as smallint[]; use Range(a, b, '[)')"),
    "int8range": ("Range(", "a list is sent as bigint[]; use Range(a, b, '[)')"),
    "interval": ("timedelta(", "an int is sent as smallint; a duration is a timedelta"),
    "bytea": ("bytes", "a str is sent as text; bytea wants bytes"),
    "numeric": ("Decimal(", "a float loses precision silently on a money column"),
}

#: Tables `judge/` is allowed to write. `document` and `thread_context` are
#: `collect/`'s and are read only, so their column types are not this lane's
#: problem — but a test fixture that seeds them IS, which is why the fixture
#: files are scanned too.
JUDGE_WRITES = {"claim", "claim_weight", "cell"}

WRITERS = [
    ROOT / "judge" / "store" / "claims.py",
    ROOT / "judge" / "store" / "cells.py",
]


def column_types(table: str) -> dict[str, str]:
    match = re.search(rf"CREATE TABLE {table} \((.*?)\n\);", SCHEMA, re.S)
    assert match, f"{table} is not in contract/tables.sql"
    out: dict[str, str] = {}
    for line in match.group(1).splitlines():
        line = line.split("--")[0].strip().rstrip(",")
        if not line or line.startswith(
            ("CONSTRAINT", "PRIMARY", "UNIQUE", "CHECK", "FOREIGN")
        ):
            continue
        parts = line.split()
        # A multi-line CHECK continues onto lines beginning `OR`/`AND`, and a
        # naive split reads `OR severity IN (...)` as a column named OR of type
        # severity. Both tokens must look like what they claim to be.
        if len(parts) >= 2 and parts[0].isidentifier() and parts[0].upper() not in (
            "OR", "AND", "NOT"
        ):
            out[parts[0]] = parts[1].split("(")[0]
    return out


def _source_of(table: str) -> str:
    """The writer that inserts into this table."""
    for path in WRITERS:
        text = path.read_text(encoding="utf-8")
        if f"INSERT INTO {table}" in text:
            return text
    pytest.fail(f"no writer in judge/store/ inserts into {table}")
    raise AssertionError  # pragma: no cover


@pytest.mark.parametrize("table", sorted(JUDGE_WRITES))
def test_non_trivial_columns_are_wrapped(table: str) -> None:
    """A column type Python cannot hand over directly must be wrapped.

    Generated from the schema rather than listed here, so a new `numeric` or
    `bytea` column fails this without anyone remembering to update it.
    """
    source = _source_of(table)
    problems = []

    for column, sql_type in column_types(table).items():
        if sql_type.endswith("[]") or sql_type in DIRECTLY_MAPPED:
            continue
        if sql_type not in WRAPPER_FOR:
            problems.append(
                f"{table}.{column} is {sql_type!r}, which this test has no rule "
                "for. Add one to WRAPPER_FOR rather than deleting the column "
                "from the check."
            )
            continue
        # Only columns the writer actually supplies are checked; a column it
        # deliberately leaves to a DEFAULT is not its problem.
        # Capture to the NEXT parameter key rather than to end of line. A value
        # can be a parenthesised conditional spanning several lines, and a
        # line-bounded regex captured "(" and reported it as unwrapped — the
        # check failing on correct code, which is how a check gets deleted.
        binding = re.search(
            rf'"{column}":\s*(.*?)(?=\n\s*"[a-z_]+":|\n\s*\}})', source, re.S
        )
        if binding is None:
            continue
        wrapper, consequence = WRAPPER_FOR[sql_type]
        if wrapper not in binding.group(1):
            problems.append(
                f"{table}.{column} ({sql_type}) is passed as "
                f"{binding.group(1).strip()!r} — {consequence}"
            )

    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("table", sorted(JUDGE_WRITES))
def test_every_required_column_is_supplied(table: str) -> None:
    """NOT NULL with no DEFAULT means the writer must supply it.

    This was the first of the three CI failures, and it is here so the two
    checks live together rather than one being remembered and the other not.
    """
    match = re.search(rf"CREATE TABLE {table} \((.*?)\n\);", SCHEMA, re.S)
    required = set()
    for line in match.group(1).splitlines():
        line = line.split("--")[0].strip().rstrip(",")
        if not line or line.startswith(
            ("CONSTRAINT", "PRIMARY", "UNIQUE", "CHECK", "FOREIGN")
        ):
            continue
        parts = line.split()
        if parts and ("NOT NULL" in line or "PRIMARY KEY" in line) and "DEFAULT" not in line:
            required.add(parts[0])

    source = _source_of(table)
    insert = re.search(rf"INSERT INTO {table} \((.*?)\)\s*VALUES", source, re.S)
    assert insert, f"cannot find the INSERT INTO {table}"
    supplied = {
        column.strip()
        for column in re.sub(r"\s+", " ", insert.group(1)).split(",")
        if column.strip().isidentifier()
    }

    missing = sorted(required - supplied)
    assert not missing, (
        f"{table} requires {missing} and the writer does not supply them. "
        "NOT NULL with no default fails at INSERT, which is a database round "
        "trip away and only visible in CI."
    )
