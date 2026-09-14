"""What a WRITER puts behind `document.text_ref` must be the platform's bytes.

THE MIRROR OF `tests/test_assembly_prose.py`, AND WHY IT WAS MISSING
--------------------------------------------------------------------

That test asks of a `thread_context`: *does the flattened text parse as JSON?*
It catches **an envelope where prose belongs** — the defect that had just
happened when it was written, to 80 github contexts and nearly to 1,512 reddit
ones.

This asks the opposite question, of the writers: **does anything store prose
where the payload belongs?** Same axis, opposite sign, and nothing asked it for
fourteen days while three writers did exactly that.

    2026-08-28 17:55   the ruling: `text_ref` locates the bytes the platform
                       gave us; prose is DERIVED AT ASSEMBLY
    2026-08-28 19:17   `prose.py` and `test_assembly_prose.py` land
    2026-09-14         three writers still storing prose are found by hand

`collect/ops/sweep_reddit.py` had no commits in between. Its comment predated
the ruling by three hours and argued the losing side, so every reader who
stopped there found a fluent case for the wrong thing.

WHY THIS IS THE CHECK THAT MATTERS, AND IT IS NOT SUBTLE
---------------------------------------------------------

Every other mechanism we have is triggered by somebody TOUCHING something:

    rules 7, 8, 9     reviewer questions, and there was no change to review
    column_states     sees a column that IS declared and IS read; it just
                      held the wrong thing
    the invariant     `content_hash(resolve(text_ref)) == content_hash` HOLDS
                      on every affected row, because both columns were written
                      together. It catches a mismatch, never a wrong choice.

A test runs whether or not anyone opens the file. That is the whole argument
for putting this in the suite rather than in a document.

WHY AST AND NOT BEHAVIOUR
--------------------------

The offending expressions sit inline in long functions that need a network, a
contract and a database to reach. A behavioural test would cover the writers it
could drive and silently skip the ones it could not — and the defect lived in
exactly the hard-to-drive ones. Precedent is `cli.py`'s AST gate test, added for
the same reason: *a behavioural test over existing commands cannot see a path
that never had a check.*

UNCLASSIFIED FAILS RATHER THAN PASSES
--------------------------------------

A `put()` whose argument this cannot classify is a FAILURE, not a skip. That is
the preflight lesson: `registry load-seed` went unguarded for weeks because
nothing forced an unclassified path to declare itself. Adding a writer that
stores something new means naming it here.
"""

from __future__ import annotations

import ast
import pathlib
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SEARCHED = ("collect", "scripts")

#: Attribute tails that ARE the platform's own bytes.
PAYLOAD_ATTRS = {"content", "payload", "raw"}

#: Calls that produce the platform's own bytes.
PAYLOAD_CALLS = {"dumps", "read_bytes", "read_text"}

#: Files whose `put()` calls are exempt, each with the reason. A file is listed
#: here only when storing DERIVED text is the correct thing for it to do.
EXEMPT: dict[str, str] = {
    # The assemblers write FLATTENED prose, which is the point of assembly. The
    # namespace kwarg already says so and is checked below; these are listed so
    # a reader does not have to infer it.
    "collect/assemble/article.py": "flattened prose, namespace=FLATTENED",
    "collect/assemble/issue.py": "flattened prose, namespace=FLATTENED",
    "collect/assemble/reddit.py": "flattened prose, namespace=FLATTENED",
    "collect/assemble/thread.py": "flattened prose, namespace=FLATTENED",
    # A one-off correction that deliberately stored prose, superseded the same
    # day by `restore_reddit_payload_refs.py`. Kept for the historical record.
    "scripts/repoint_reddit_text_refs.py": (
        "the 2026-08-28 defect itself, superseded by restore_reddit_payload_refs.py"
    ),
    # Emits INSERT text for review rather than executing it. STILL WRONG, and
    # its docstring says so at the top in as many words: a reviewer who pastes
    # the generated load.sql reproduces the defect. Exempted to keep this test
    # about live writers, not to bless the shape.
    "scripts/export_thread_contexts.py": (
        "emits SQL for review; defect acknowledged in its own docstring"
    ),
}


def _py_files() -> list[pathlib.Path]:
    """Every TRACKED `.py` under the searched trees.

    Tracked, not "every file on disk", for one reason and it is not tidiness:
    an untracked scratch script is not part of the repo's contract, and letting
    one turn this guard red locally is how a guard gets skipped, then deleted.
    `scripts/measure_key_constraint.py` is broken and untracked on this
    checkout today and would have done exactly that.

    Falls back to the filesystem if git is unavailable, because a guard that
    silently scans NOTHING is worse than one that scans a little extra - which
    is what `test_the_scan_found_the_writers_it_is_meant_to_guard` is for.
    """
    try:
        listed = subprocess.run(
            ["git", "ls-files", "--", *[f"{t}/*.py" for t in SEARCHED]],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=30,
        ).stdout.split()
    except (OSError, subprocess.SubprocessError):  # pragma: no cover
        out: list[pathlib.Path] = []
        for top in SEARCHED:
            out.extend(sorted((ROOT / top).rglob("*.py")))
        return out
    return sorted((ROOT / rel) for rel in listed if (ROOT / rel).is_file())


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _strip_encode(node: ast.AST) -> ast.AST:
    """`X.encode("utf-8")` stores the same bytes as `X`."""
    while (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "encode"
    ):
        node = node.func.value
    return node


def _assignments(tree: ast.AST) -> dict[str, ast.AST]:
    """`name -> the value it stands for`, over the whole module.

    Three shapes, because the real writers use all three and a checker that
    handled only the first would have called two of today's call sites
    "unclassified":

        blob = json.dumps(...)              a plain assignment
        refs[k] = json.dumps(...)           a subscript store into a dict
        for k, text in payloads.items()     a loop over that dict

    Last-wins is deliberate: if a name stands for two things and either is
    prose, the prose one should decide.
    """
    found: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    found[target.id] = node.value
                elif isinstance(target, ast.Subscript) and isinstance(
                    target.value, ast.Name
                ):
                    # `payloads[eid] = json.dumps(...)` makes `payloads` stand
                    # for what it holds, so a later loop over it resolves.
                    found.setdefault(f"{target.value.id}[]", node.value)
        elif isinstance(node, ast.For):
            # `for k, v in mapping.items():` -> `v` stands for mapping's values.
            src = node.iter
            container = None
            if (
                isinstance(src, ast.Call)
                and isinstance(src.func, ast.Attribute)
                and src.func.attr in {"items", "values"}
            ):
                container = src.func.value
            elif isinstance(src, ast.Name):
                container = src
            if container is None:
                continue
            if isinstance(node.target, ast.Tuple) and len(node.target.elts) == 2:
                value_target = node.target.elts[1]
            elif isinstance(node.target, ast.Name):
                value_target = node.target
            else:
                continue
            if isinstance(value_target, ast.Name) and isinstance(container, ast.Name):
                found[value_target.id] = ast.Name(id=f"{container.id}[]", ctx=ast.Load())
    return found


def _functions(tree: ast.AST) -> dict[str, ast.AST]:
    """`name -> the expression it returns`, for single-return local helpers.

    `scripts/fetch_model.py` wraps its serialisation in a nested `_payload(obj)`.
    A checker that cannot follow one call into a local function would report it
    unclassified forever, and the natural response to that is to add it to
    EXEMPT - which is how a guard stops guarding.
    """
    found: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            returns = [
                n.value
                for n in ast.walk(node)
                if isinstance(n, ast.Return) and n.value is not None
            ]
            if len(returns) == 1:
                found[node.name] = returns[0]
    return found


def _classify(
    arg: ast.AST,
    names: dict[str, ast.AST],
    funcs: dict[str, ast.AST] | None = None,
    *,
    depth: int = 0,
) -> str:
    """'payload', 'derived', or 'unclassified'."""
    funcs = funcs or {}
    arg = _strip_encode(arg)
    if depth > 5:
        return "unclassified"

    # A locally built string: concatenation, f-string, or a literal.
    if isinstance(arg, (ast.BinOp, ast.JoinedStr)):
        return "derived"
    if isinstance(arg, ast.Constant):
        return "derived"

    if isinstance(arg, ast.Dict):
        # A dict of payloads is payloads. Empty stays unclassified rather than
        # passing by vacuity.
        verdicts = {_classify(v, names, funcs, depth=depth + 1) for v in arg.values}
        if verdicts == {"payload"}:
            return "payload"
        if "derived" in verdicts:
            return "derived"
        return "unclassified"

    if isinstance(arg, ast.Attribute):
        if arg.attr in PAYLOAD_ATTRS:
            return "payload"
        # `.body`, `.selftext`, `.title`, `.text` - a field WE picked out.
        return "derived"

    if isinstance(arg, ast.Call):
        func = arg.func
        if isinstance(func, ast.Attribute) and func.attr in PAYLOAD_CALLS:
            return "payload"
        if isinstance(func, ast.Name) and func.id in PAYLOAD_CALLS:
            return "payload"
        # One step into a local helper - `_payload(obj)` in fetch_model.py.
        if isinstance(func, ast.Name) and func.id in funcs:
            return _classify(funcs[func.id], names, funcs, depth=depth + 1)
        return "unclassified"

    if isinstance(arg, ast.Subscript):
        # `payload["data"][0]...` - indexing into the parsed payload.
        return "payload"

    if isinstance(arg, ast.Name):
        target = names.get(arg.id)
        if target is not None:
            return _classify(target, names, funcs, depth=depth + 1)
        return "unclassified"

    return "unclassified"


def _namespace_of(call: ast.Call) -> str | None:
    for kw in call.keywords:
        if kw.arg == "namespace":
            if isinstance(kw.value, ast.Name):
                return kw.value.id
            if isinstance(kw.value, ast.Attribute):
                return kw.value.attr
    return None


UNPARSED: list[str] = []


def _put_calls() -> list[tuple[str, int, ast.Call, dict[str, ast.AST], dict[str, ast.AST]]]:
    out = []
    unparsed = UNPARSED
    for path in _py_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError) as exc:
            # A FILE THAT WILL NOT PARSE IS NOT A FILE WITH NO WRITERS.
            # `continue` here was the same hole this whole test exists to
            # close: the scan would drop `sweep_reddit.py` on a syntax error
            # and every assertion about it would pass by absence. Caught while
            # proving the test catches the original defect - the injection
            # broke the file, the file vanished from the scan, and only the
            # count assertion noticed.
            unparsed.append(f"{_rel(path)}: {type(exc).__name__}: {exc}")
            continue
        names = _assignments(tree)
        funcs = _functions(tree)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "put"
                and node.args
            ):
                out.append((_rel(path), node.lineno, node, names, funcs))
    return out


CALLS = _put_calls()


def test_every_scanned_file_parsed() -> None:
    """An unreadable file must fail loudly, never drop out of the scan.

    Separate from the count assertion below because the two say different
    things: that one catches a scan that found nothing, this one catches a scan
    that found less than it should and could not say so.
    """
    assert not UNPARSED, (
        "these files could not be parsed, so their `put()` calls were NOT "
        "checked - fix the file rather than leaving the scan blind:\n  "
        + "\n  ".join(UNPARSED)
    )


def test_the_scan_found_the_writers_it_is_meant_to_guard() -> None:
    """A scan that matches nothing passes every assertion below it.

    The failure mode this test exists to prevent is its own: rename `put()` or
    move the writers and every assertion silently becomes vacuous. Six is the
    count of live RAW writers on 2026-09-14 with room to spare; the point is
    that it is not zero.
    """
    assert len(CALLS) >= 15, (
        f"only {len(CALLS)} `put()` call sites found - the scan has stopped "
        "seeing the writers, so everything below it is vacuous"
    )
    files = {rel for rel, _, _, _, _ in CALLS}
    for expected in ("collect/ops/sweep_reddit.py", "scripts/fetch_model.py"):
        assert expected in files, f"{expected} is no longer scanned"


@pytest.mark.parametrize(
    ("rel", "lineno", "call", "names", "funcs"),
    [pytest.param(*c, id=f"{c[0]}:{c[1]}") for c in CALLS],
)
def test_a_raw_store_write_stores_the_platforms_bytes(
    rel: str, lineno: int, call: ast.Call, names: dict[str, ast.AST], funcs: dict[str, ast.AST]
) -> None:
    if rel in EXEMPT:
        pytest.skip(f"{rel}: {EXEMPT[rel]}")
    if _namespace_of(call) == "FLATTENED":
        return

    verdict = _classify(call.args[0], names, funcs)
    assert verdict != "derived", (
        f"{rel}:{lineno} stores DERIVED TEXT where the payload belongs.\n"
        "`docs/engineer-1/ruling-what-content-hash-identifies.md`: `text_ref` "
        "locates the bytes the platform gave us, `content_hash` identifies "
        "them, and prose is derived at ASSEMBLY by `collect/assemble/prose.py`.\n"
        "Storing prose breaks NFR-6 (the hash must fingerprint what the AUTHOR "
        "published, not a string we assembled) and NFR-4 (the row must name a "
        "raw artifact to reprocess from). It also cannot be undone later: a row "
        "whose payload was never stored needs a re-fetch, and on Reddit there "
        "is none for an old thread.\n"
        "Store the payload here and let the assembler extract."
    )
    assert verdict == "payload", (
        f"{rel}:{lineno} stores something this test cannot classify.\n"
        "Unclassified FAILS rather than passes, on purpose - a writer nobody "
        "classified is how `registry load-seed` ran unguarded for weeks. Either "
        "store the platform's bytes, or add the case to `_classify`, or list "
        "the file in `EXEMPT` with the reason storing derived text is correct "
        "there."
    )


class TestTheHouseSpellingIsOneSpelling:
    """`json.dumps` flags decide the hash, so a divergent one splits the store."""

    def test_every_payload_dump_uses_the_house_spelling(self) -> None:
        """`sort_keys=True, ensure_ascii=False` everywhere, or dedup breaks.

        `scripts/fetch_model.py` omitted `ensure_ascii=False` until 2026-09-14,
        so the SAME post fetched by that arm and by `sweep_reddit.py` produced
        two byte strings, two hashes and two stored objects on any non-ASCII
        text. That is not only waste: `restore_reddit_payload_refs.py` repairs a
        broken row by finding the same post's payload under another sweep's
        hash, so a second spelling silently shrinks the set of rows that can
        ever be repaired.
        """
        offenders = []
        for rel, lineno, call, names, _funcs in CALLS:
            if rel in EXEMPT or _namespace_of(call) == "FLATTENED":
                continue
            node = _strip_encode(call.args[0])
            if isinstance(node, ast.Name):
                node = _strip_encode(names.get(node.id, node))
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "dumps"
            ):
                continue
            flags = {
                kw.arg: getattr(kw.value, "value", None)
                for kw in node.keywords
                if kw.arg in {"sort_keys", "ensure_ascii"}
            }
            if flags.get("sort_keys") is not True or flags.get("ensure_ascii") is not False:
                offenders.append(f"{rel}:{lineno} has {flags or 'no flags'}")

        assert not offenders, (
            "payload serialisation must be `json.dumps(x, ensure_ascii=False, "
            "sort_keys=True)` so the same artifact hashes identically wherever "
            "it is written:\n  " + "\n  ".join(offenders)
        )
