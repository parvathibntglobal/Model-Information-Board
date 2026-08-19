"""Every CLI command that writes runs the startup checks first. Issue #27.

WHY THIS IS A STRUCTURAL TEST AND NOT A BEHAVIOURAL ONE
-------------------------------------------------------
`assert_no_fixtures` and `assert_contract_backed` were written on day one, named
by `contract/tables.sql` as FR-31's only protection, and called from nothing but
tests. The guard read as present and was not.

Wiring them once fixes today. What stops it recurring is a test that fails when
somebody adds a write command without the gate — because the failure mode is not
a broken gate, it is a NEW PATH that never acquired one. A behavioural test over
the commands that exist cannot see a command that does not exist yet.

So this reads `collect/cli.py`'s AST: every command function that opens a
`transaction()` must also call `_gate`. A new writer fails this the day it is
written, naming itself.
"""

from __future__ import annotations

import ast
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "collect" / "cli.py"

#: Read-only commands, deliberately ungated. The state these checks refuse is
#: exactly the state somebody needs a diagnostic in — see `_gate`'s docstring.
#: Listed rather than inferred, so moving one INTO this set is a visible diff.
READ_ONLY = {
    "_cmd_db_check",
    "_cmd_registry_check_sources",
    "_cmd_registry_aliases",
    "_cmd_registry_propose_aliases",
    "_cmd_triage_population",
    # Reads a surface extract and SELECTs the registry; prints the curve and the
    # set. Writes nothing at all — not a row, and unlike `propose-aliases`, not
    # even a file. So it is classified rather than gated, which is the whole
    # point of this set being explicit: the answer to "does this need `_gate`"
    # is recorded here rather than left to whoever reads the function next.
    "_cmd_registry_tracked_set",
    # Runs the checks AS its purpose, and reports instead of raising.
    "_cmd_ops_preflight",
    # Runs the chain, whose first stage is preflight.
    "_cmd_ops_run",
}


def _tree() -> ast.Module:
    return ast.parse(CLI.read_text(encoding="utf-8"))


def _command_functions(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    return {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("_cmd_")
    }


def _calls(node: ast.FunctionDef) -> set[str]:
    names = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            func = child.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


def test_every_command_that_opens_a_transaction_calls_the_gate():
    """A writer without the gate is the defect this test exists for."""
    functions = _command_functions(_tree())
    assert functions, "no _cmd_ functions found - has cli.py been restructured?"

    ungated = sorted(
        name
        for name, node in functions.items()
        if "transaction" in _calls(node) and "_gate" not in _calls(node)
    )
    assert not ungated, (
        f"these commands open a transaction and never call _gate: {ungated}. "
        "A write path that skips the startup checks means assert_no_fixtures "
        "can only report fixtures another path already wrote, which is the "
        "state it exists to prevent. Add `_gate(conn)` inside the transaction, "
        "before the first write."
    )


def test_the_seed_loader_specifically_is_gated():
    """Named because it is the command that CREATES the fixture in question.

    `load_seed` inserts `model_version.provenance = 'seed'`. If any single
    command has to be gated, it is this one, and it was the one that was not.
    """
    node = _command_functions(_tree())["_cmd_registry_load_seed"]
    assert "_gate" in _calls(node)


def test_read_only_commands_are_listed_rather_than_guessed():
    """Every command is either gated or explicitly named read-only.

    A command that is neither has not been thought about, and the default for an
    unclassified command should be to fail this test rather than to run
    unguarded.
    """
    functions = _command_functions(_tree())
    unclassified = sorted(
        name
        for name, node in functions.items()
        if "_gate" not in _calls(node) and name not in READ_ONLY
    )
    assert not unclassified, (
        f"neither gated nor listed as read-only: {unclassified}. Decide which, "
        "and record it - an unclassified command runs unguarded by default."
    )
    stale = sorted(READ_ONLY - set(functions))
    assert not stale, f"READ_ONLY names commands that no longer exist: {stale}"


def test_a_refusal_is_reported_rather_than_raised():
    """`main` catches `PreflightRefused`, so a refused write exits 1 with a
    message instead of a stack trace. A trace reads as a bug in the tool rather
    than as the tool working."""
    main = next(
        node for node in ast.walk(_tree())
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    handled = {
        handler.type.id
        for node in ast.walk(main)
        if isinstance(node, ast.Try)
        for handler in node.handlers
        if isinstance(handler.type, ast.Name)
    }
    assert "PreflightRefused" in handled
