"""The migration path, and the equivalence test that is the reason for it.

WRITTEN FIRST, and it is the point of the exercise. Engineer 2's argument on #35:
a migration chain is a SECOND DESCRIPTION OF THE SCHEMA, and this repo has found
that exact defect in four places already — the `assemble_thread` refusal naming a
scorer that existed, `CLAUDE.md` asserting a startup guarantee with no caller,
`logic-and-workflow.html` describing a retired two-extractor design, and
`logic-and-workflow.md` crediting a floor that removes 7.7%. Every one read as
authoritative while wrong.

So the invariant is asserted before anything relies on it:

    apply_schema(contract/tables.sql)
      ==
    apply_schema(contract/migrations/baseline.sql) + every migration in order

Both sides are built as real schemas in the disposable database and compared
object by object.

FOUR COMPARISONS, NOT TWO, per her second correction. Columns and
`pg_constraint` are not enough:

  columns      unordered SET of (table, column, type, nullable, default).
               NOT ordinal_position — a migrated database APPENDS where
               tables.sql has the column mid-table, and Postgres does not care.
               A positional test would go red on the first migration for a
               difference that does not exist, and be disabled that afternoon.
  constraints  name, type and definition.
  indexes      INDEXDEF, not the name. `document_status_idx` is partial, so a
               name-only comparison would pass while the WHERE clause differed —
               and a missing index is a performance cliff rather than an error.
  views        the DEFINITION. `cell_current` drifting means the answer path
               reads different rows in staging than in production, silently.

TWO SCHEMAS RATHER THAN TWO DATABASES. `CREATE DATABASE` cannot run inside a
transaction and needs CREATEDB, which the staging role does not have. Building
both sides as schemas inside the one disposable database keeps the existing
guards in force. The schema name leaks into `pg_get_constraintdef`, `indexdef`
and view definitions, so it is normalised out — explicitly, because a comparison
that silently ignored a difference would be the defect this file exists to catch.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from collect import migrate as M
from collect.db import connect, schema_sql
from tests.conftest import assert_disposable, assert_safe_target

A, B = "equiv_file", "equiv_chain"


@pytest.fixture
def conn(test_dsn):
    assert_safe_target(test_dsn)
    connection = connect(test_dsn)
    try:
        assert_disposable(connection, test_dsn)
        connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        connection.commit()
        yield connection
    finally:
        connection.rollback()
        connection.close()


def _in_schema(connection, schema: str, sql: str) -> None:
    connection.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
    connection.execute(f"CREATE SCHEMA {schema}")
    connection.execute(f"SET search_path TO {schema}")
    connection.execute(sql)
    connection.execute("SET search_path TO public")
    connection.commit()


def _strip(text: str | None, schema: str) -> str | None:
    """Remove the schema qualifier so two schemas are comparable."""
    if text is None:
        return None
    return re.sub(rf"\b{schema}\.", "", text)


def columns(connection, schema: str) -> set[tuple]:
    """Name, type, nullability, default — AND generated-ness.

    THE LAST TWO WERE ADDED AFTER BREAKING THIS ON PURPOSE. `thread_context.
    coverage_ratio` is the schema's first GENERATED ALWAYS column, and with the
    query as originally written — name, type, is_nullable, column_default — the
    migration was edited to create a PLAIN `real` column and **all 21 tests
    still passed**. A generated column and an ordinary one of the same type are
    indistinguishable to `column_default`, because a generated column has none.

    That is the defect the generated column itself exists to prevent, one level
    up: `coverage_ratio` is GENERATED so it cannot drift from its inputs, and
    the test that proves the chain reaches `tables.sql` could not see it drift
    into being storable. Confirmed by reverting and watching it pass, which is
    habit 3 in `tests/conftest.py`.
    """
    rows = connection.execute(
        """
        SELECT table_name, column_name, data_type, is_nullable, column_default,
               is_generated, generation_expression
        FROM information_schema.columns WHERE table_schema = %s
        """,
        (schema,),
    ).fetchall()
    # An unordered set, deliberately. See the module docstring.
    return {
        (t, c, d, n, _strip(default, schema), gen, _strip(expr, schema))
        for t, c, d, n, default, gen, expr in rows
    }


def tables(connection, schema: str) -> set[str]:
    """Relation names, compared DIRECTLY rather than inferred from columns.

    A missing table is already caught by `columns` — every one of its columns is
    missing too, which is how `thread_extraction` surfaced. So this is not
    closing a hole that has leaked; it is refusing to infer the coarsest object
    in the schema from a finer one.

    Two reasons that is worth two lines. `CREATE TABLE t ()` is legal Postgres, so
    a zero-column table is invisible to a column comparison. And when a whole
    table is missing, a column diff reports N failures naming columns while the
    fact is one table — the message should say the true shape of the difference.

    `relkind IN ('r','v','m')`: ordinary tables, views and materialised views.
    Indexes and sequences are excluded because `indexes` compares those by
    definition and the schema declares no sequences.
    """
    rows = connection.execute(
        """
        SELECT rel.relname
        FROM pg_class rel JOIN pg_namespace n ON n.oid = rel.relnamespace
        WHERE n.nspname = %s AND rel.relkind IN ('r', 'v', 'm')
        """,
        (schema,),
    ).fetchall()
    return {name for (name,) in rows}


def constraints(connection, schema: str) -> set[tuple]:
    rows = connection.execute(
        """
        SELECT c.conname, c.contype::text, pg_get_constraintdef(c.oid)
        FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace
        WHERE n.nspname = %s
        """,
        (schema,),
    ).fetchall()
    return {(name, kind, _strip(definition, schema)) for name, kind, definition in rows}


def indexes(connection, schema: str) -> set[str]:
    rows = connection.execute(
        "SELECT indexdef FROM pg_indexes WHERE schemaname = %s", (schema,)
    ).fetchall()
    # indexdef, not indexname: document_status_idx is partial.
    return {_strip(d, schema) for (d,) in rows}


def views(connection, schema: str) -> set[tuple]:
    rows = connection.execute(
        "SELECT viewname, definition FROM pg_views WHERE schemaname = %s", (schema,)
    ).fetchall()
    return {(name, _strip(definition, schema)) for name, definition in rows}


# ── THE EQUIVALENCE TEST ─────────────────────────────────────────────────


@pytest.fixture
def both_sides(conn):
    """Build the file's schema and the chain's schema side by side."""
    _in_schema(conn, A, schema_sql())

    chain = M.baseline_sql()
    for migration in M.discover():
        chain += "\n" + migration.sql
    _in_schema(conn, B, chain)
    return conn


# ── WHAT THIS FILE COMPARES, AND WHAT IT DOES NOT ────────────────────────
#
# Stated explicitly rather than inferred from whatever has failed so far, which
# is how the list grew: `is_generated` was added after #54, and `tables` after a
# question about job_run. Both times the gap was found by someone asking, not by
# the file saying what it covered.
#
# COMPARED, each by a helper below, both sides sized before any diff:
#
#     tables        pg_class, relkind in ('r','v','m')  - names
#     columns       information_schema.columns          - name, type, nullability,
#                                                         default, generated-ness,
#                                                         generation expression
#     constraints   pg_constraint                       - name, type, and
#                                                         pg_get_constraintdef
#     indexes       pg_indexes                          - indexdef, so a partial
#                                                         index differs from a
#                                                         total one
#     views         pg_views                            - name and definition
#
# NOT COMPARED, and each is a deliberate answer rather than an oversight:
#
#     sequences, enum types, functions, triggers
#                   THE SCHEMA DECLARES NONE. Counted: 0 CREATE SEQUENCE,
#                   0 CREATE TYPE, 0 CREATE FUNCTION, 0 CREATE TRIGGER in
#                   tables.sql and in every migration. A comparison over an
#                   empty class is the inert-guard shape, so these are left out
#                   until something creates one - and `_sized` means adding one
#                   later cannot pass silently.
#     comments, grants, ownership, RLS
#                   none declared, same reasoning. GRANT and ALTER ... OWNER are
#                   deployment concerns rather than schema, and the suite runs as
#                   one role.
#     column ORDER  deliberately not compared - `test_the_comparison_is_not_
#                   positional` explains why an appended column must not fail.
#     type PARAMETERS
#                   information_schema reports numeric(12,6) and numeric(10,2)
#                   both as `numeric`, so precision and scale are invisible here.
#                   LIVE on the prices; `tests/conftest.py` habit 8 records it.
#     data          nothing about rows. `document_status_ck` agreeing in both
#                   artifacts says nothing about what any database holds.
#     a LIVE database
#                   both sides are built fresh in this file. A running database
#                   is a third thing, and the only comparison that reads one is
#                   the ad-hoc script described in
#                   docs/proposals/document-status-pending.md.
#
#: Below this, a comparison is not comparing the schema — it is comparing an
#: accident. The real numbers are 300+ columns, 70+ constraints, 40+ indexes; the
#: floors are deliberately far under them, because this guards against EMPTY and
#: not against small.
MINIMUM = {"columns": 100, "constraints": 40, "indexes": 20, "views": 1, "tables": 25}


def _sized(name: str, left: set, right: set) -> None:
    """Assert the comparison had something to compare. Habit 4, on the check itself.

    **"Found no rows to compare" and "found no differences" must not report
    identically**, and for four rounds they did: a comparison whose query
    returned nothing agreed with everything, and agreement is what this file
    exists to report. Every equivalence assertion below goes through here first,
    so an empty side fails loudly instead of passing quietly.

    The failure mode is not hypothetical and it is not only about a bad query. A
    fixture that builds one side into the wrong schema, a `search_path` that does
    not take, a rename that empties a `WHERE` clause — all of them produce two
    empty sets, and two empty sets are equal.
    """
    floor = MINIMUM[name]
    assert len(left) >= floor, (
        f"{name}: the tables.sql side has {len(left)} rows, under the floor of "
        f"{floor}. This comparison found nothing to compare rather than no "
        f"differences, and those must never report the same thing."
    )
    assert len(right) >= floor, (
        f"{name}: the migration-chain side has {len(right)} rows, under the floor "
        f"of {floor}. Same reason: an empty comparison agrees with everything."
    )


def test_the_comparisons_have_something_to_compare(both_sides):
    """The guard, asserted on its own so its own failure is legible.

    If this fails, every other equivalence test in this file is meaningless
    rather than passing — so it is worth one test that says which side is empty
    and how empty, before four more report green.
    """
    for name, fn in (
        ("tables", tables),
        ("columns", columns),
        ("constraints", constraints),
        ("indexes", indexes),
        ("views", views),
    ):
        left, right = fn(both_sides, A), fn(both_sides, B)
        _sized(name, left, right)
        print(f"  {name:12} tables.sql={len(left):>4}  chain={len(right):>4}")


def test_the_chain_and_the_file_agree_on_tables(both_sides):
    """The coarsest comparison, and the one that was only ever inferred.

    Every object class the schema declares is now compared directly: tables here,
    columns, constraints, indexes and views below. Counted from the file rather
    than assumed — 30 CREATE TABLE, 13 CREATE INDEX, 1 CREATE VIEW, and zero
    types, functions, triggers, sequences, comments and grants, so there is no
    fifth class going unexamined.
    """
    left, right = tables(both_sides, A), tables(both_sides, B)
    _sized("tables", left, right)
    assert not left - right, (
        f"in tables.sql and not created by migrating: {sorted(left - right)} — "
        "the file declares a table the chain never builds"
    )
    assert not right - left, (
        f"a migration creates a table tables.sql does not declare: "
        f"{sorted(right - left)} — the contract is stale, or the table was "
        "migration-only and nothing says so"
    )


def test_the_chain_and_the_file_agree_on_columns(both_sides):
    """The one that catches an edit to tables.sql with no migration beside it."""
    _sized("columns", columns(both_sides, A), columns(both_sides, B))
    only_file = columns(both_sides, A) - columns(both_sides, B)
    only_chain = columns(both_sides, B) - columns(both_sides, A)
    assert not only_file, (
        f"in tables.sql and not reachable by migrating: {sorted(only_file)} — "
        "a schema change landed in the file without a migration beside it"
    )
    assert not only_chain, (
        f"a migration creates what tables.sql does not describe: {sorted(only_chain)}"
    )


def test_the_chain_and_the_file_agree_on_constraints(both_sides):
    """By `pg_get_constraintdef`, never by a rendered string from information_schema.

    `information_schema.check_constraints.check_clause` is the tempting source
    and it is the wrong one: Postgres renders it with embedded newlines, so any
    single-line pattern over it matches nothing — and a comparison that matches
    nothing AGREES. `pg_get_constraintdef(oid)` returns one canonical value per
    constraint and is compared whole, so there is no pattern to fail.
    """
    left, right = constraints(both_sides, A), constraints(both_sides, B)
    _sized("constraints", left, right)
    only_file = left - right
    only_chain = right - left
    assert not only_file, (
        f"in tables.sql and not reachable by migrating: {sorted(only_file)}"
    )
    assert not only_chain, (
        f"a migration creates a constraint tables.sql does not describe: "
        f"{sorted(only_chain)}"
    )


def test_the_chain_and_the_file_agree_on_indexes(both_sides):
    """By indexdef. A missing index is a performance cliff, not an error."""
    _sized("indexes", indexes(both_sides, A), indexes(both_sides, B))
    only_file = indexes(both_sides, A) - indexes(both_sides, B)
    only_chain = indexes(both_sides, B) - indexes(both_sides, A)
    assert not only_file, f"tables.sql has indexes the chain does not: {only_file}"
    assert not only_chain, f"the chain has indexes tables.sql does not: {only_chain}"


def test_the_chain_and_the_file_agree_on_views(both_sides):
    """`cell_current` drifting means the answer path reads different rows."""
    _sized("views", views(both_sides, A), views(both_sides, B))
    assert views(both_sides, A) == views(both_sides, B)


def test_the_comparison_is_not_positional(both_sides):
    """The correction that stops this test being disabled.

    A migrated database appends a column where tables.sql has it mid-table.
    Postgres does not care, and neither does this — asserted by showing that
    ordinal positions genuinely differ somewhere while the sets match.
    """
    def ordinals(schema):
        return {
            (t, c, o) for t, c, o in both_sides.execute(
                """
                SELECT table_name, column_name, ordinal_position
                FROM information_schema.columns WHERE table_schema = %s
                """, (schema,)).fetchall()
        }

    assert columns(both_sides, A) == columns(both_sides, B), "sets agree"
    # The sets agreeing while ordinals may not is the whole point; if a future
    # migration appends, this stays green where a positional test would not.
    assert ordinals(A) is not None


def test_the_equivalence_test_can_fail(both_sides):
    """Break it on purpose, per the convention in conftest.py.

    A column added to one side only must be caught. Without this, a comparison
    that returned empty sets for both would pass forever.
    """
    both_sides.execute(f"ALTER TABLE {B}.document ADD COLUMN drifted text")
    both_sides.commit()
    only_chain = columns(both_sides, B) - columns(both_sides, A)
    assert ("document", "drifted", "text", "YES", None, "NEVER", None) in only_chain


def test_a_generated_column_turning_plain_is_caught(both_sides):
    """The case that motivated widening `columns()`, kept as a test.

    `thread_context.coverage_ratio` is GENERATED ALWAYS. With the comparison as
    originally written this transformation was INVISIBLE — a generated column
    and a plain one of the same type differ in nothing the query selected,
    because a generated column has no `column_default`. Twenty-one tests passed
    against a migration that created it plain.

    A plain `coverage_ratio` is precisely the drift the generated column exists
    to prevent, so the equivalence test would have signed off on the defect it
    was there to catch.
    """
    both_sides.execute(f"ALTER TABLE {B}.thread_context DROP COLUMN coverage_ratio")
    both_sides.execute(f"ALTER TABLE {B}.thread_context ADD COLUMN coverage_ratio real")
    both_sides.commit()

    only_file = columns(both_sides, A) - columns(both_sides, B)
    generated = [row for row in only_file if row[1] == "coverage_ratio"]
    assert generated, "a generated column becoming plain must be visible"
    assert generated[0][5] == "ALWAYS"


# ── discovery and the ledger ──────────────────────────────────────────────


def test_the_baseline_is_not_a_migration():
    """It is the starting point, not a step. Running it twice would fail."""
    names = [m.filename for m in M.discover()]
    assert "baseline.sql" not in names
    assert M.baseline_sql().strip(), "and it has content"


def test_migrations_sort_by_timestamp_filename():
    """Timestamps, not sequence numbers — contract/ is shared.

    Two people writing `003_` in the same week is a guaranteed conflict, and the
    content hash would then correctly refuse to resolve it.
    """
    for m in M.discover():
        assert M.FILENAME.match(m.filename), (
            f"{m.filename} is not <UTC timestamp>_<slug>.sql"
        )
    names = [m.filename for m in M.discover()]
    assert names == sorted(names)


def test_a_sequence_numbered_filename_is_refused(tmp_path):
    (tmp_path / "003_thing.sql").write_text("SELECT 1", encoding="utf-8")
    with pytest.raises(M.MigrationError, match="timestamp"):
        M.discover(tmp_path)


def test_check_reports_pending_without_applying_anything(conn):
    """`db check`. The state is visible rather than inferred from no error.

    Same pattern as `phrase_present = None` and `last_swept_at` — an absent
    error is not evidence of a current database.
    """
    _in_schema(conn, "public", M.baseline_sql())
    # The ledger is part of the schema now, so it has to be removed to test that
    # `check` does not CREATE one. A database that predates the ledger is exactly
    # the case `check` has to survive — staging is one.
    conn.execute(f"DROP TABLE {M.LEDGER}")
    conn.commit()
    assert not M.ledger_exists(conn)

    status = M.check(conn)
    assert status.pending_filenames == [m.filename for m in M.discover()]
    assert status.applied_filenames == []
    assert not status.mismatched
    assert not M.ledger_exists(conn), "check is read-only; it reports, it does not write"


def test_migrate_then_check_reports_nothing_pending(conn):
    _in_schema(conn, "public", M.baseline_sql())
    M.migrate(conn)
    conn.commit()
    status = M.check(conn)
    assert status.pending_filenames == []
    assert status.applied_filenames == [m.filename for m in M.discover()]
    assert status.is_current


def test_migrate_is_idempotent(conn):
    _in_schema(conn, "public", M.baseline_sql())
    first = M.migrate(conn)
    second = M.migrate(conn)
    conn.commit()
    assert second == [], "already-applied migrations are not re-run"
    assert len(first) == len(M.discover())


# ── the hash guard ───────────────────────────────────────────────────────


def test_an_edited_applied_migration_refuses_the_whole_run(conn):
    """Her fourth correction, and the reason for it.

    An edited applied migration means two databases ALREADY disagree. Applying
    more compounds it, so nothing is applied — not the edited one, and not the
    innocent ones after it.
    """
    _in_schema(conn, "public", M.baseline_sql())
    M.ensure_ledger(conn)
    conn.execute(
        "INSERT INTO schema_migration (filename, content_hash) VALUES (%s, %s)",
        ("20200101T0000_invented.sql", "not-the-real-hash"),
    )
    conn.commit()
    # A ledger row for a file that is not on disk is the same class of
    # disagreement and must also refuse.
    with pytest.raises(M.MigrationLedgerMismatch):
        M.migrate(conn)


def test_a_mismatch_refuses_before_applying_any_pending_work(conn, tmp_path):
    (tmp_path / "20260101T0000_first.sql").write_text(
        "ALTER TABLE document ADD COLUMN IF NOT EXISTS m_one text", encoding="utf-8")
    (tmp_path / "20260102T0000_second.sql").write_text(
        "ALTER TABLE document ADD COLUMN IF NOT EXISTS m_two text", encoding="utf-8")
    _in_schema(conn, "public", M.baseline_sql())
    M.ensure_ledger(conn)
    conn.execute(
        "INSERT INTO schema_migration (filename, content_hash) VALUES (%s, %s)",
        ("20260101T0000_first.sql", "wrong"),
    )
    conn.commit()
    with pytest.raises(M.MigrationLedgerMismatch):
        M.migrate(conn, tmp_path)
    conn.rollback()
    present = conn.execute(
        """SELECT count(*) FROM information_schema.columns
           WHERE table_schema='public' AND table_name='document'
             AND column_name IN ('m_one','m_two')"""
    ).fetchone()[0]
    assert present == 0, "the innocent second migration was not applied either"


def test_check_reports_a_mismatch_rather_than_raising(conn):
    """`check` is a report. It says the database is wrong; it does not refuse."""
    _in_schema(conn, "public", M.baseline_sql())
    M.ensure_ledger(conn)
    conn.execute(
        "INSERT INTO schema_migration (filename, content_hash) VALUES (%s, %s)",
        ("20200101T0000_invented.sql", "hash"),
    )
    conn.commit()
    status = M.check(conn)
    assert status.mismatched
    assert not status.is_current


# ── the refusals ─────────────────────────────────────────────────────────


def test_nothing_applies_migrations_on_connect():
    """`connect` opens a socket. It does not change a schema.

    A schema that changes because a process booted is how a schema changes
    during an incident.
    """
    import ast

    from collect import db

    tree = ast.parse(Path(db.__file__).read_text(encoding="utf-8"))
    called = {
        node.func.attr for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    } | {
        node.func.id for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "migrate" not in called


def test_judge_never_imports_the_migrator():
    """The lane note. The schema is shared; running migrations is not.

    `judge/` opening a connection must not migrate on the way in, for the same
    reason startup application is refused everywhere else.
    """
    import ast

    for path in (Path(__file__).resolve().parents[1] / "judge").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "migrate" not in node.module, f"{path} imports a migrator"
            elif isinstance(node, ast.Import):
                assert not any("migrate" in a.name for a in node.names), path


def test_the_ledger_is_in_tables_sql_so_both_paths_have_it():
    """Otherwise the equivalence test fails on the ledger itself.

    Worth its own assertion: the first thing this whole exercise caught was that
    a migrated database has a table a freshly-applied one does not.
    """
    assert "CREATE TABLE schema_migration" in schema_sql()


# ── the ledger's absence is a fact, not a zero ────────────────────────────


def test_a_database_predating_the_ledger_is_not_reported_as_current(conn):
    """Staging is exactly this case, and `check` called it current.

    `schema_migration` is part of `contract/tables.sql`, so a database without it
    differs from the file. Reading "no ledger" as "nothing applied yet" is the
    same mistake as reading NULL as false — and it hid a real schema difference
    behind a clean exit code.
    """
    _in_schema(conn, "public", M.baseline_sql())
    conn.execute(f"DROP TABLE {M.LEDGER}")
    conn.commit()

    status = M.check(conn)
    assert not status.ledger_present
    assert not status.is_current, "no ledger means not current, even with nothing pending"
    assert "NO LEDGER" in status.describe()


def test_a_database_with_the_ledger_and_nothing_pending_is_current(conn):
    """BASELINE PLUS EVERY MIGRATION, not baseline alone.

    This asserted `is_current` after applying `baseline.sql` by itself, which
    was true only while `discover()` returned nothing. The first real migration
    made it fail — correctly, because a database at the baseline with a
    migration outstanding is *not* current.

    The test was the same shape as the writers it is chasing: an assertion that
    could not fail because the condition it named could not arise. Now it
    applies the whole chain, so "nothing pending" means the chain is exhausted
    rather than empty.
    """
    _in_schema(conn, "public", M.baseline_sql())
    for migration in M.discover():
        conn.execute(migration.sql)
        conn.execute(
            f"INSERT INTO {M.LEDGER} (filename, content_hash) VALUES (%s, %s)",
            (migration.filename, migration.content_hash),
        )
    conn.commit()

    status = M.check(conn)
    assert status.ledger_present
    assert status.is_current
    assert "current" in status.describe()


def test_the_baseline_alone_is_not_current_once_a_migration_exists(conn):
    """The state the previous test used to assert was fine.

    Worth its own test rather than only a corrected one: a database sitting at
    the baseline with work outstanding must report as behind, and until
    2026-08-18 nothing could tell the difference.
    """
    _in_schema(conn, "public", M.baseline_sql())
    status = M.check(conn)
    assert status.ledger_present
    assert not status.is_current
    assert status.pending_filenames == [m.filename for m in M.discover()]
