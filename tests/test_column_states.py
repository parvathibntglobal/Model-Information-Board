"""Every schema column's state is DECLARED rather than DISCOVERED.

The property this guards is not "every column is read" — write_only is often
correct, and `contract/column_states.yaml` marks several deliberately so. It is
that somebody wrote down which, and why.

WHY STEP 1 IS THE WHOLE VALUE

A snapshot test over today's 306 columns passes forever and says nothing about
the 307th. `test_every_column_is_declared` fails on a column with no entry, which
is the same arrangement as `tests/test_cli_write_gate.py`'s AST guard, where
read-only commands must be listed explicitly so an unclassified one fails rather
than running unguarded — and for the reason that guard records: **a behavioural
test cannot see a path that never had a check.**

WHAT IS DELIBERATELY NOT ASSERTED HERE

Whether a column is POPULATED. `harvest_run.truncated_by` is 41.3% populated and
`pages_fetched` is 0.0%, and both classify identically to the static audit. As a
test that check passes on an empty CI database and green-lights the
`pages_fetched` defect exactly where it matters least, so it belongs in the
nightly report beside triage survival.

Requires a database, for the column list only. See docs/dev-database.md.
"""

from __future__ import annotations

import pytest
import yaml

from collect.config import CONTRACT_DIR
from scripts.audit_columns import (
    NEITHER,
    UNWRITTEN_READ,
    WRITTEN_READ,
    WRITTEN_UNREAD,
    columns_of,
    discover,
)
from tests.conftest import assert_disposable, assert_safe_target

MANIFEST = CONTRACT_DIR / "column_states.yaml"

#: Which discovered states each declaration is consistent with.
#:
#: `read_not_by_query` accepts ANY discovered state, because the reader is by
#: definition invisible to the audit — so it is the one state that requires a
#: `why` naming the reader, enforced below. Without that requirement it would be
#: a hole big enough to file every awkward column through.
CONSISTENT_WITH = {
    "read": {WRITTEN_READ},
    "write_only": {WRITTEN_UNREAD},
    "read_not_by_query": {WRITTEN_READ, WRITTEN_UNREAD, UNWRITTEN_READ, NEITHER},
    "generated": {UNWRITTEN_READ, NEITHER},
    "defaulted": {UNWRITTEN_READ, NEITHER},
    "unwired": {UNWRITTEN_READ, NEITHER},
    "reserved": {NEITHER},
}

#: States whose declaration is a claim about intent that the code does not yet
#: satisfy. They must carry `known_gap` saying so.
NEEDS_GAP = {"unwired"}


@pytest.fixture(scope="module")
def schema(test_dsn):
    from collect.db import apply_schema, connect

    assert_safe_target(test_dsn)
    conn = connect(test_dsn)
    try:
        assert_disposable(conn, test_dsn)
        conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        apply_schema(conn)
        conn.commit()
        yield columns_of(conn)
    finally:
        conn.close()


@pytest.fixture(scope="module")
def manifest():
    raw = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    assert raw and "columns" in raw, f"{MANIFEST} has no `columns` block"
    return raw["columns"]


@pytest.fixture(scope="module")
def found(schema):
    return discover(schema)


def _entry(manifest, table, column):
    return (manifest.get(table) or {}).get(column)


class TestEveryColumnIsDeclared:
    """Step 1. The property that makes this a guard rather than a snapshot."""

    def test_every_column_in_the_schema_has_an_entry(self, schema, manifest):
        missing = [
            f"{t}.{c}" for t, cols in sorted(schema.items()) for c in cols
            if _entry(manifest, t, c) is None
        ]
        assert not missing, (
            f"{len(missing)} column(s) have no entry in {MANIFEST.name}: "
            f"{missing[:12]}. A new column is a decision about whether anything "
            f"reads it, and this file is where that decision is written down "
            f"instead of discovered nine months later."
        )

    def test_no_entry_names_a_column_that_does_not_exist(self, schema, manifest):
        """A dropped column must not leave a declaration behind."""
        stale = [
            f"{t}.{c}" for t, cols in sorted(manifest.items()) for c in (cols or {})
            if c not in schema.get(t, [])
        ]
        assert not stale, (
            f"{MANIFEST.name} declares column(s) the schema does not have: {stale}. "
            f"A stale declaration reads as a considered state for something that "
            f"is gone."
        )


class TestDeclaredMatchesDiscovered:
    """Step 2, with `known_gap` as the only way to differ."""

    def test_every_state_is_in_the_vocabulary(self, manifest):
        bad = [
            f"{t}.{c}={(e or {}).get('state')!r}"
            for t, cols in sorted(manifest.items()) for c, e in (cols or {}).items()
            if (e or {}).get("state") not in CONSISTENT_WITH
        ]
        assert not bad, f"unknown state(s): {bad}. Known: {sorted(CONSISTENT_WITH)}"

    def test_discovered_state_matches_declared_unless_a_gap_is_named(
        self, schema, manifest, found
    ):
        mismatched = []
        for table, cols in sorted(schema.items()):
            for column in cols:
                entry = _entry(manifest, table, column) or {}
                declared = entry.get("state")
                if declared not in CONSISTENT_WITH:
                    continue  # the vocabulary test owns this
                if entry.get("known_gap"):
                    continue  # declared intent, gap acknowledged
                info = found[(table, column)]
                actual = info["state"]
                if actual not in CONSISTENT_WITH[declared]:
                    line = (
                        f"{table}.{column}: declared {declared!r}, "
                        f"discovered {actual!r}"
                    )
                    # NAME THE FILE THAT CAUSED IT, NOT JUST THE COLUMN.
                    # A web-only read is the audit's known false-positive class
                    # (#203): a JS builtin accessor colliding with a
                    # single-owner column name. Three times the failure named a
                    # backend column while the cause was a frontend token, and
                    # the reader had 25 web files and no line number. The
                    # evidence is already in `read_at`; printing it is the fix.
                    evidence = info.get("read_at") or []
                    web = info.get("web_reads") or []
                    if info.get("read_only_from_web"):
                        line += (
                            "\n      the ONLY read evidence is a web-text match: "
                            + "; ".join(web)
                            + "\n      If that token is a JS builtin (a Set/Map/Blob"
                            " .size, an Error .name, a CSS property in a style"
                            "\n      object, a UI config key) then this is a FALSE"
                            " POSITIVE in the audit — fix"
                            "\n      scripts/audit_columns.py or scope the scan."
                            " Do NOT edit the column's state, and do"
                            "\n      NOT reword the web file to dodge the token."
                        )
                    elif evidence:
                        line += "\n      read evidence: " + "; ".join(evidence)
                    if info.get("written_at"):
                        line += "\n      write evidence: " + "; ".join(info["written_at"])
                    mismatched.append(line)
        assert not mismatched, (
            f"{len(mismatched)} column(s) are not in the state they declare:\n  "
            + "\n  ".join(mismatched[:20])
            + "\n\n"
            "IF THE DISCOVERED STATE IS NOW CORRECT, DO NOT ONLY EDIT THE STATE.\n"
            "Set `reviewed: true` and add a `why` naming the reader or writer that\n"
            "changed. A state edited without its reason is a snapshot wearing a\n"
            "declaration's clothes, which is the thing this file exists to prevent\n"
            "- and it has happened twice, because THIS MESSAGE used to name the\n"
            "state and not the reason, so the smallest green-making edit was one\n"
            "word. thread_context.assembled_at and harvest_run.id, 2026-08-27/28.\n"
            "\n"
            "If the declaration is the intent and the code has not caught up, add\n"
            "`known_gap` instead - that is the acknowledged-gap path, not a\n"
            "failure."
        )

    def test_read_not_by_query_names_its_reader(self, manifest):
        """The escape hatch requires saying who reads it.

        `read_not_by_query` accepts any discovered state, so without this it is
        a hole every awkward column gets filed through — and the exceptions
        become the interesting part, which is what a declared state exists to
        prevent.
        """
        silent = [
            f"{t}.{c}" for t, cols in sorted(manifest.items()) for c, e in (cols or {}).items()
            if (e or {}).get("state") == "read_not_by_query" and not (e or {}).get("why")
        ]
        assert not silent, (
            f"{silent} declare `read_not_by_query` and name no reader. The audit "
            f"cannot see this reader by definition, so the `why` is the only "
            f"evidence it exists."
        )

    def test_unwired_names_what_is_missing(self, manifest):
        """Only for `reviewed: true` entries, and that scoping is deliberate.

        An unreviewed entry is a SNAPSHOT of what the audit found, not a claim
        anybody made. Demanding a justification from it would demand a decision
        that has explicitly not been taken — which is the state `reviewed: false`
        exists to record. The moment somebody reviews an `unwired` column they
        have to say what stage is missing.
        """
        silent = [
            f"{t}.{c}" for t, cols in sorted(manifest.items()) for c, e in (cols or {}).items()
            if (e or {}).get("reviewed")
            and (e or {}).get("state") in NEEDS_GAP
            and not (e or {}).get("known_gap")
        ]
        assert not silent, (
            f"{silent} declare a state the code does not satisfy and name no "
            f"`known_gap`. 'A reader exists and the writer does not' is a "
            f"statement about a missing stage, and the stage should be named."
        )


def test_report_the_undeclared_debt(schema, manifest, capsys):
    """NOT an assertion. The count of unreviewed entries, printed.

    `reviewed: false` means the entry is a snapshot of what the audit found and
    nobody has ruled on it. It is not a pass, and laundering 282 of those into
    "declared" is exactly the defect this file exists to stop — so the number is
    printed on every run and the test never fails on it.

    Turning it into a ratchet was considered and refused: a ratchet on this
    number would make declaring a column a prerequisite for adding one, and the
    declaring pass is a couple of hours of reading that should not block a
    migration.
    """
    total = sum(len(cols) for cols in schema.values())
    unreviewed = [
        f"{t}.{c}" for t, cols in sorted(manifest.items()) for c, e in (cols or {}).items()
        if not (e or {}).get("reviewed")
    ]
    with capsys.disabled():
        print(
            f"\ncolumn states: {total} columns, "
            f"{total - len(unreviewed)} reviewed, {len(unreviewed)} still a snapshot "
            f"({100 * len(unreviewed) / total:.0f}% undeclared)"
        )
    assert len(unreviewed) <= total
