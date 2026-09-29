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

#: FUNCTIONS THAT REACH A CONSOLE, NOT ONLY `print`.
#:
#: ⚠ THIS GUARD WENT BLIND THE DAY A SCRIPT STOPPED USING `print`.
#:   `scripts/fetch_model.py` renders a whole run through its own `_say()`
#:   helper - header, per-stage headings, per-thread lines, footer - and every
#:   one of them was invisible here, because the walk matched the NAME `print`
#:   and nothing else. A `·` separator went in, rendered as `?` on this console,
#:   and 72 tests passed over it.
#:
#:   It is the shape this file already records twice: a check whose population
#:   is narrower than the thing it protects. The population was "calls to
#:   print", the thing protected is "text that reaches a stream", and a helper
#:   is all it takes for those to stop being the same set.
#:
#:   NAMES RATHER THAN RESOLUTION, for the reason the returned-string note
#:   gives: matching a name over-collects and needs no call graph, and a guard
#:   that needs a call graph is a guard nobody maintains. A new console helper
#:   must be added here - which is a real gap, and a smaller one than matching
#:   a single builtin.
WRITERS = frozenset({"print", "_say"})


def _printed_literals(tree: ast.AST):
    """Every string constant that reaches a `print` call, or is returned to one.

    ⚠ `print` ARGUMENTS ALONE WERE NOT ENOUGH, AND THIS GUARD MISSED ONE OF ITS
      OWN. `report_rollup_delta.baseline_refusal` RETURNS its message and the
      caller prints it - so an em-dash in the returned f-string reached a
      console the walk had never looked at. Found by eye, in output this test
      exists to make impossible, which is the same shape as everything else it
      records: a check whose population is narrower than the thing it protects.

      RETURNED STRINGS ARE INCLUDED, and the false-positive cost is accepted.
      Not every returned string is printed, so this over-collects - a returned
      literal that only ever reaches a log or a comparison is now constrained to
      ASCII for no reason. That is the cheap direction: the alternative is
      tracing which returns reach a stream, which needs the call graph, and a
      guard that needs a call graph is a guard nobody maintains.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and node.value is not None:
            for inner in ast.walk(node.value):
                if isinstance(inner, ast.Constant) and isinstance(inner.value, str):
                    yield inner.lineno, inner.value
            continue
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = getattr(func, "id", None) or getattr(func, "attr", None)
        if name not in WRITERS:
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

# ── the gap the scripts-only scope left ──────────────────────────────────


def test_the_report_objects_a_script_prints_are_encodable():
    """A string RETURNED from `collect/` and PRINTED by a script.

    THE SCOPE ABOVE IS `scripts/` on the stated grounds that collect/ and judge/
    use the character correctly and never print it. That assumption broke on
    2026-09-08: `collect/triage/run.py:TriageStoreRun.describe` built a line
    beginning with U+26A0, `scripts/triage_stored_corpus.py` printed it, and the
    first new-platform triage run died with `UnicodeEncodeError` **after** the
    per-source table and the gate breakdown had already scrolled past - so the
    useful half of the report was produced and then thrown away.

    A static scan of `scripts/` cannot see that, because the literal lives one
    module over. This calls the report builders instead, with every counter
    populated so no branch is skipped, and asserts what the console will do.
    """
    from collect.triage.run import TriageStoreRun, gate_availability

    run = TriageStoreRun(
        eligible=200, triaged=190, kept=100, dropped=90, written=190,
        unreadable=5, not_prose=4, unmapped_source=1,
        by_reason={"no-resolvable-entity": 40, "too-short-no-artifact": 50},
        never_ran={"wrong-language": 190}, not_applicable={"pure-link-post": 150},
        by_flag={"known-bot-counted": 3},
        subject_inherited=7, root_unresolvable=2, root_unreadable=1,
        by_source={"hackernews": {"eligible": 190, "triaged": 190, "kept": 100,
                                  "dropped": 90}},
        population_fingerprint="deadbeefdeadbeef",
    )
    for name, text in (
        ("describe", run.describe()),
        ("per_source_table", run.per_source_table()),
        ("gate_availability", gate_availability(run)),
    ):
        try:
            text.encode("cp1252")
        except UnicodeEncodeError as exc:
            raise AssertionError(
                f"TriageStoreRun.{name}() returns a character a cp1252 console "
                f"cannot print: {exc.object[exc.start:exc.end]!r}. A script "
                "prints this, so the run dies part-way through its own report. "
                "Use ASCII in anything a report builder returns."
            ) from None
