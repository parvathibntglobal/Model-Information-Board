"""No test may re-import or replace a project module that is already loaded (#436).

WHY. pytest imports every test file before running any of them. A test that
calls `importlib.reload(judge.extract.client)` re-executes that module into the
same namespace, so each class in it becomes a NEW class. Any other test file
that imported `ExtractorUnavailable` at collection time still holds the OLD
one, and its `pytest.raises` or `except` silently stops matching - but only
when the reloading file happens to run first. The suite was green partly
because of alphabetical file names.

WHAT THIS REFUSES, in any file under `tests/`:

    importlib.reload(...) / reload(...)          any reload at all
    del sys.modules[...] / sys.modules.pop(...)   forgetting a module to re-import it
    sys.modules["judge..." | "collect..."] = ...  replacing a project module by name

WHAT IT ALLOWS, deliberately. Registering a SCRIPT loaded from a file path
(`importlib.util.spec_from_file_location` + `sys.modules[spec.name] = mod`) puts
a new name in `sys.modules` that nothing else holds. Two files do this today
(`test_fetch_stop.py`, `test_rebuild_platform_contexts.py`) and neither is this
bug, so a write with a non-literal key is allowed only in a file that loads a
module from a file path. A check that flagged them would teach people to
ignore it.

NO WAIVER LIST, as agreed on #436: a check that ships with known exceptions
whitelisted teaches the next person that a waiver is the fix. The two former
offenders were changed to read their setting on use instead.
"""

from __future__ import annotations

import ast
import pathlib

TESTS = pathlib.Path(__file__).resolve().parent
PROJECT = ("judge", "collect")


def _is_sys_modules(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "modules"
        and isinstance(node.value, ast.Name)
        and node.value.id == "sys"
    )


def _literal(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _offences(path: pathlib.Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    loads_from_file = "spec_from_file_location" in source
    found = []
    for node in ast.walk(tree):
        # importlib.reload(x), or a bare reload(x) after `from importlib import reload`
        if isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
            if name == "reload":
                found.append(f"{path.name}:{node.lineno} reloads a module")
            if (isinstance(fn, ast.Attribute) and fn.attr == "pop"
                    and _is_sys_modules(fn.value)):
                found.append(f"{path.name}:{node.lineno} pops a module from sys.modules")
        # del sys.modules[...]
        if isinstance(node, ast.Delete):
            for target in node.targets:
                if isinstance(target, ast.Subscript) and _is_sys_modules(target.value):
                    found.append(f"{path.name}:{node.lineno} deletes a module from sys.modules")
        # sys.modules[key] = value
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if not (isinstance(target, ast.Subscript) and _is_sys_modules(target.value)):
                    continue
                key = _literal(target.slice)
                if key is not None:
                    if key.split(".")[0] in PROJECT:
                        found.append(f"{path.name}:{node.lineno} replaces project module {key!r}")
                elif not loads_from_file:
                    found.append(
                        f"{path.name}:{node.lineno} writes sys.modules with a computed key "
                        "outside a file that loads a script from a path"
                    )
    return found


def test_no_test_file_reloads_or_replaces_a_project_module():
    me = pathlib.Path(__file__).name
    offences = [
        o for path in sorted(TESTS.glob("test_*.py")) if path.name != me
        for o in _offences(path)
    ]
    assert not offences, (
        "a test re-imports or replaces a loaded module, which swaps its classes "
        "under every other test file and makes the suite order-dependent (#436). "
        "Read the setting on use instead:\n  " + "\n  ".join(offences)
    )


def test_the_check_catches_the_shapes_it_names(tmp_path):
    """The check is only worth having if it fires. Each refused shape, once."""
    cases = {
        "importlib.reload(m)\n": "reloads",
        "from importlib import reload\nreload(m)\n": "reloads",
        "import sys\ndel sys.modules['judge.x']\n": "deletes",
        "import sys\nsys.modules.pop('collect.x')\n": "pops",
        "import sys\nsys.modules['judge.extract.client'] = object()\n": "replaces",
    }
    for i, (src, word) in enumerate(cases.items()):
        f = tmp_path / f"test_case_{i}.py"
        f.write_text(src, encoding="utf-8")
        got = _offences(f)
        assert got and word in got[0], (src, got)


def test_registering_a_script_from_a_path_is_allowed(tmp_path):
    f = tmp_path / "test_script_loader.py"
    f.write_text(
        "import importlib.util, sys\n"
        "spec = importlib.util.spec_from_file_location('fetch_model', 'scripts/fetch_model.py')\n"
        "mod = importlib.util.module_from_spec(spec)\n"
        "sys.modules[spec.name] = mod\n",
        encoding="utf-8",
    )
    assert _offences(f) == []
