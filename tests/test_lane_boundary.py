"""The rules a helpful refactor will otherwise quietly violate.

These are cheap, mechanical checks over the source of `collect/`. They exist
because the lane boundary and the no-LLM rule are invariants, and an
invariant nobody checks is a comment.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

COLLECT = Path(__file__).resolve().parents[1] / "collect"

#: Anything that would mean this lane is calling a language model. collect/
#: never does — not once. If a task here seems to need one, it belongs in
#: judge/ or it does not belong.
LLM_IMPORTS = {"anthropic", "openai", "litellm", "langchain", "transformers", "ollama"}


def _python_files() -> list[Path]:
    return sorted(COLLECT.rglob("*.py"))


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_there_are_python_files_to_check():
    assert _python_files()


@pytest.mark.parametrize("path", _python_files(), ids=lambda p: p.name)
def test_collect_never_imports_judge(path: Path):
    """collect/ fills the interface; judge/ reads it. Nothing flows back."""
    assert "judge" not in _imported_roots(path), f"{path} imports judge/"


@pytest.mark.parametrize("path", _python_files(), ids=lambda p: p.name)
def test_collect_never_imports_a_model_client(path: Path):
    """NFR-8: exactly two stages may call a language model, and neither is here."""
    offending = LLM_IMPORTS & _imported_roots(path)
    assert not offending, f"{path} imports {sorted(offending)}"


def _imported_modules(path: Path) -> set[str]:
    """Full dotted module names imported by a file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


def test_registry_never_imports_harvest():
    """FR-5: no code path from `document` or `claim` to a registry write.

    A post may trigger a re-check. It may never write. The structural half of
    that guarantee is that the registry cannot even see harvest; the other
    half is database permissions.
    """
    forbidden = {"collect.adapters", "collect.assemble", "collect.triage"}
    for file in sorted((COLLECT / "registry").rglob("*.py")):
        reached = {
            module
            for module in _imported_modules(file)
            if any(module == f or module.startswith(f + ".") for f in forbidden)
        }
        assert not reached, f"{file} reaches into {sorted(reached)}"


# ── the three HTTP bypasses ───────────────────────────────────────────────
#
# feedparser, trafilatura and urllib.robotparser each ship their own HTTP layer,
# and each reaches the network without seeing `assert_identifying_user_agent`:
#
#     feedparser.parse("https://…")        urllib.request, and its own
#                                          plausible-looking User-Agent
#     trafilatura.fetch_url / .downloads   urllib3, pycurl if installed
#     RobotFileParser.read()               urllib.request
#
# Three separate paths around a gate built so that nothing in this lane can make
# an unidentified request. These checks are the cheap half of the enforcement;
# `tests/test_blog_no_network.py` severs the transports and is the half that
# catches what no import list anticipates.

#: Libraries that fetch as well as parse. Importable from exactly one module,
#: whose whole job is to keep them fed with bytes.
PARSER_LIBRARIES = {"feedparser", "trafilatura"}
PARSER_BOUNDARY = COLLECT / "adapters" / "blog" / "parse.py"

#: Submodules that exist to fetch. There is no legitimate importer in this lane.
FETCHING_SUBMODULES = {
    "trafilatura.downloads",
    "trafilatura.spider",
    "trafilatura.sitemaps",
    "trafilatura.feeds",
    "feedparser.http",
}

#: Attribute names that mean a library is being asked to fetch.
FETCHING_ATTRIBUTES = {"fetch_url", "fetch_response", "urlopen"}


def _attribute_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}


def test_only_the_parse_boundary_imports_a_parser_library():
    """One importer, so "was it handed bytes?" is a question about one file."""
    for path in _python_files():
        offending = PARSER_LIBRARIES & _imported_roots(path)
        if path == PARSER_BOUNDARY:
            assert offending, "the parse boundary is where these belong"
            continue
        assert not offending, (
            f"{path} imports {sorted(offending)}. Both libraries fetch as well as "
            "parse; route the bytes through collect/adapters/blog/parse.py."
        )


@pytest.mark.parametrize("path", _python_files(), ids=lambda p: p.name)
def test_nothing_imports_a_fetching_submodule(path: Path):
    reached = FETCHING_SUBMODULES & _imported_modules(path)
    assert not reached, (
        f"{path} imports {sorted(reached)}, which fetch with their own HTTP layer "
        "and their own User-Agent, bypassing collect.http.build_client (NFR-5)."
    )


@pytest.mark.parametrize("path", _python_files(), ids=lambda p: p.name)
def test_nothing_calls_a_library_fetch_helper(path: Path):
    reached = FETCHING_ATTRIBUTES & _attribute_names(path)
    assert not reached, (
        f"{path} references {sorted(reached)}. Fetch through collect.http.build_client, "
        "which is the only place an identifying User-Agent is guaranteed."
    )


def test_only_collect_http_constructs_a_client():
    """`collect/http.py` says this is checked here. Until now it was not.

    The check fires in the client constructor precisely so that no later code
    path can skip it — which only holds while `build_client` is the only
    constructor. An `httpx.Client(...)` in an adapter is the bug that makes the
    gate decorative.
    """
    allowed = COLLECT / "http.py"
    for path in _python_files():
        if path == allowed:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            constructed = (
                isinstance(func, ast.Attribute)
                and func.attr in ("Client", "AsyncClient")
                and isinstance(func.value, ast.Name)
                and func.value.id == "httpx"
            )
            assert not constructed, (
                f"{path}:{node.lineno} constructs httpx.{func.attr} directly. "
                "Use collect.http.build_client: the User-Agent gate lives in that "
                "constructor, and a client built anywhere else has walked around it."
            )


def test_the_robots_gate_never_calls_read():
    """`RobotFileParser.read()` fetches with urllib. `parse()` takes lines.

    The robots module has no legitimate `.read()`, so forbidding the attribute
    outright is exact rather than heuristic.
    """
    robots = COLLECT / "adapters" / "blog" / "robots.py"
    assert robots.exists()
    assert "read" not in _attribute_names(robots), (
        "collect/adapters/blog/robots.py references .read — RobotFileParser.read() "
        "fetches robots.txt with urllib.request and no identifying User-Agent. "
        "Fetch it with build_client and use RobotFileParser.parse(lines)."
    )


def test_only_the_robots_gate_imports_robotparser():
    for path in _python_files():
        imports_it = any(
            module == "urllib.robotparser" or module.endswith("robotparser")
            for module in _imported_modules(path)
        )
        if imports_it:
            assert path.name == "robots.py", f"{path} imports robotparser outside the gate"
