"""No script prints a character the console it runs on cannot encode.

WHY THIS EXISTS, AND IT IS NOT TIDINESS. `scripts/measure_document_facts_gap.py`
carried one `⚠` inside an `if stale_before:` block. On Windows, `sys.stdout` is
cp1252 and U+26A0 is unencodable, so the script raised `UnicodeEncodeError`
AFTER printing every figure - the run looked complete, exited non-zero into a
pipe nobody read, and the only thing lost was the warning the block existed to
raise.

**IT IS THE FAILURE MODE THAT MAKES THIS WORTH A TEST.** The crash is not on the
happy path. It fires exactly when there is something to warn about, so the
output is correct on every run where nothing is wrong and truncated on the runs
that matter. A reviewer reading the file sees a warning; a reader of the output
sees nothing and cannot tell the difference between "no warning" and "the
warning killed the process".

And it recurs: the same character was reintroduced into the same file within an
hour of being removed, in a new block, by someone who had just written the
comment explaining why not to.

SCOPE IS `scripts/`, NOT THE WHOLE TREE. Module docstrings and comments in
`collect/` and `judge/` use `⚠` heavily and correctly - they are never written
to a stream. What matters is what reaches stdout, so this walks the AST and
checks the arguments of `print` calls rather than grepping the file.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"

#: What a Windows console encodes to. The narrowest encoding any of us runs on,
#: which is the one worth testing against - passing here passes on utf-8 too.
CONSOLE_ENCODING = "cp1252"


def _printed_literals(tree: ast.AST):
    """Every string constant that reaches a `print` call, with its line."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = getattr(func, "id", None) or getattr(func, "attr", None)
        if name != "print":
            continue
        for argument in node.args:
            for inner in ast.walk(argument):
                if isinstance(inner, ast.Constant) and isinstance(inner.value, str):
                    yield inner.lineno, inner.value


def _script_paths():
    return sorted(p for p in SCRIPTS.glob("*.py") if p.name != "__init__.py")


@pytest.mark.parametrize("path", _script_paths(), ids=lambda p: p.name)
def test_no_script_prints_an_unencodable_character(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    offenders = []
    for lineno, text in _printed_literals(tree):
        try:
            text.encode(CONSOLE_ENCODING)
        except UnicodeEncodeError as error:
            bad = text[error.start : error.end]
            offenders.append(f"{path.name}:{lineno} prints {bad!r} (U+{ord(bad[0]):04X})")

    assert not offenders, (
        "\n  ".join(["these print() calls crash on a cp1252 console:", *offenders])
        + "\n\n"
        "Use ASCII in printed strings - `!!` rather than a warning sign, `->`\n"
        "rather than an arrow. The crash fires only when the branch is taken,\n"
        "so it hides the warning it was written to raise and leaves output that\n"
        "looks complete. Comments and docstrings are unaffected and are not\n"
        "checked: they never reach a stream."
    )


def test_the_check_can_actually_fail():
    """A guard nobody has seen fail is a guard nobody knows the shape of.

    Same reason `alias_match_count` counts hits rather than checking the list is
    non-empty: a test that would pass against a broken implementation records
    identically to one that would not.
    """
    tree = ast.parse('print("danger \\u26a0 here")')
    found = list(_printed_literals(tree))
    assert found, "the AST walk found no printed literal at all"
    with pytest.raises(UnicodeEncodeError):
        found[0][1].encode(CONSOLE_ENCODING)


def test_the_walk_sees_f_strings_and_nested_calls():
    """`print(f"...")` and `print("a" if x else "b")` both reach a console."""
    tree = ast.parse('print(f"count {n} \\u26a0")\nprint("x" if n else "\\u26a0")')
    values = [text for _lineno, text in _printed_literals(tree)]
    assert any("\u26a0" in v for v in values), (
        "the walk missed a literal inside an f-string or a conditional, which "
        "is where these actually appear"
    )
