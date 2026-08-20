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

from collect.cli import _refuse_to_discard_review

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


# ── the generator cannot silently discard a review ────────────────────────


class TestRegeneratingCannotSilentlyDiscardAReview:
    """`registry propose-aliases --out` used to overwrite whatever was there.

    Two deepseek reseats and six dropped `(free)` forms lived only in the written
    artifact, and the only thing preventing their loss was that nobody had re-run
    the command. That is not a guard.

    Refuse-to-overwrite rather than an overrides file, and it is the smaller of
    the two: an overrides file needs a location (`contract/` is shared), a schema,
    apply-order semantics, a rule for an override naming a model no longer in the
    tracked set, and tests for each. This needs a flag and a stat.
    """

    def test_an_existing_artifact_is_not_overwritten(self, tmp_path):
        target = tmp_path / "alias-surfaces.yaml"
        target.write_text("proposals: []\n", encoding="utf-8")

        refusal = _refuse_to_discard_review(target, force=False)

        assert refusal is not None
        assert "refusing to overwrite" in refusal
        assert "--force" in refusal

    def test_a_missing_target_proceeds(self, tmp_path):
        assert _refuse_to_discard_review(tmp_path / "new.yaml", force=False) is None

    def test_force_proceeds(self, tmp_path):
        target = tmp_path / "alias-surfaces.yaml"
        target.write_text("proposals: []\n", encoding="utf-8")
        assert _refuse_to_discard_review(target, force=True) is None

    def test_the_refusal_names_the_review_markers_it_found(self, tmp_path):
        """A bare "file exists" is obstructive; naming what is at stake is not."""
        target = tmp_path / "a.yaml"
        target.write_text(
            "    surface: deepseek v4 pro   # reseated 2026-08-19\n"
            "      - deepseek 0813          # DEMOTED\n",
            encoding="utf-8",
        )
        refusal = _refuse_to_discard_review(target, force=False)
        assert "DEMOTED" in refusal
        assert "reseated" in refusal

    def test_it_refuses_on_EXISTENCE_and_not_on_finding_a_marker(self, tmp_path):
        """Rule 6, and habit 11. A reviewer who ACCEPTS an entry leaves no word
        behind, so absence of a marker is not evidence that nobody edited it.
        The refusal must not be conditional on the grep succeeding."""
        target = tmp_path / "pristine.yaml"
        target.write_text("proposals: []\n", encoding="utf-8")

        refusal = _refuse_to_discard_review(target, force=False)

        assert refusal is not None, "existence alone must refuse"
        assert "NOT evidence that nobody edited it" in refusal


def test_every_contract_loader_the_schema_depends_on_has_a_cli_caller():
    """Habit 10, as a guard rather than as a lesson learned twice.

    `load_source_rows` was correct and tested from the day it was written and
    had NO CALLER — no command, no script, no chain stage. `source` therefore
    held 0 rows, and `harvest_run.source_id` is a FOREIGN KEY to `source(id)`,
    so no harvest run could be recorded for any platform.

    Nothing caught it because every tool this repo has walks the import graph:
    `sources.py` is imported all over `collect/`, so every "is this wired"
    question found it. **An import chain is no evidence of a call path.**

    So this asserts the CALL, by AST, inside `cli.py` — the one place a human
    can invoke it. It is deliberately narrow: a loader whose absence breaks a
    foreign key is a different class from a helper nobody happens to use, and
    the list below is the loaders in that class rather than every writer.
    """
    import ast

    called: set[str] = set()
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called.add(func.id)
            elif isinstance(func, ast.Attribute):
                called.add(func.attr)

    # Each entry names what breaks when the loader has no caller.
    required = {
        "load_source_rows": "harvest_run.source_id is a FK to source(id)",
        "load_seed": "model_version has no rows without it",
        "recompute_window": "in_window keeps a schema default that reads as computed",
    }
    missing = {name: why for name, why in required.items() if name not in called}
    assert not missing, (
        "loader(s) with no call site in cli.py: "
        + "; ".join(f"{n} — {w}" for n, w in missing.items())
    )
