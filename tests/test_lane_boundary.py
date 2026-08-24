"""The rules a helpful refactor will otherwise quietly violate.

These are cheap, mechanical checks over the source of `collect/`. They exist
because the lane boundary and the no-LLM rule are invariants, and an
invariant nobody checks is a comment.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COLLECT = ROOT / "collect"

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


#: The gate is two modules: `robots.py` fetches and caches the ruling,
#: `rules.py` decides what the rules mean. Both touch `RobotFileParser` and
#: neither may fetch with it. Widening this set is a decision — the property
#: being protected is that there is exactly one path to the network, through
#: `build_client`.
ROBOTS_GATE = frozenset({"robots.py", "rules.py"})


@pytest.mark.parametrize("name", sorted(ROBOTS_GATE))
def test_the_robots_gate_never_calls_read(name):
    """`RobotFileParser.read()` fetches with urllib. `parse()` takes lines.

    Neither gate module has a legitimate `.read()`, so forbidding the
    attribute outright is exact rather than heuristic.
    """
    module = COLLECT / "adapters" / "blog" / name
    assert module.exists()
    assert "read" not in _attribute_names(module), (
        f"collect/adapters/blog/{name} references .read — RobotFileParser.read() "
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
            assert path.name in ROBOTS_GATE, (
                f"{path} imports robotparser outside the gate. The gate is "
                f"{sorted(ROBOTS_GATE)}; anything else reaching for it is a "
                "second interpretation of robots.txt, and two interpretations "
                "disagree eventually."
            )


# ── the reverse direction, and the two write bans ─────────────────────────
#
# ADDED 2026-08-18, AFTER NOTICING THE ASYMMETRY. `collect/ -> judge/` was
# enforced from the start and `judge/ -> collect/` never was, so Engineer 2
# complied for weeks with a rule that did not exist. An audit of the four
# symmetric statements in the two lane docs found THREE unenforced:
#
#     collect never imports judge                 enforced
#     judge never imports collect                 NOT enforced   <- now is
#     judge never writes document/thread_context  NOT enforced   <- now is
#     collect never writes claim/cell/label       NOT enforced   <- now is
#
# The class is the finding rather than any one of them: an invariant stated in
# prose and enforced on one side reads, to anyone checking, as enforced.

#: `INSERT INTO x`, `UPDATE x`, `DELETE FROM x` — the three ways to write a row.
#: Matched against SQL text rather than the AST, because the SQL is a string
#: literal and the AST cannot see inside it.
_WRITE_SQL = re.compile(
    r"\b(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+\"?(\w+)\"?", re.IGNORECASE
)

#: Tables `collect/` fills. `judge/` reads them and never writes them — the
#: one-directional rule that lets two people work without coordinating.
INTERFACE_TABLES = {"document", "thread_context"}

#: Tables `judge/` fills. `collect/` never writes them: FR-5's guarantee is that
#: a post can trigger a re-check and can never write a judgement.
JUDGEMENT_TABLES = {"claim", "claim_weight", "cell", "label", "label_change"}


def _tables_written(path: Path) -> set[str]:
    return {m.group(1).lower() for m in _WRITE_SQL.finditer(path.read_text(encoding="utf-8"))}


@pytest.mark.parametrize("path", sorted((ROOT / "judge").rglob("*.py")), ids=str)
def test_judge_never_imports_collect(path: Path):
    """The mirror of `test_collect_never_imports_judge`, absent until 2026-08-18.

    `judge/CLAUDE.md` says *"Never import from `collect/`"* and nothing checked
    it. `judge/store/claims.py` duplicates connection handling rather than
    reusing `collect/db.py` and documents why — voluntary compliance with an
    unenforced rule, which is exactly the state that decays quietly.
    """
    assert "collect" not in _imported_roots(path), f"{path} imports collect/"


@pytest.mark.parametrize("path", sorted((ROOT / "judge").rglob("*.py")), ids=str)
def test_judge_never_writes_the_interface_tables(path: Path):
    """`document` and `thread_context` are the handover. judge/ reads them.

    A write here would make the interface bidirectional, and the whole reason
    two people can work in parallel is that it is not.
    """
    written = _tables_written(path) & INTERFACE_TABLES
    assert not written, f"{path} writes {sorted(written)}, which collect/ owns"


@pytest.mark.parametrize("path", sorted((ROOT / "collect").rglob("*.py")), ids=str)
def test_collect_never_writes_the_judgement_tables(path: Path):
    """FR-5's other half. A post may trigger a re-check; it may never write one.

    `test_registry_never_imports_harvest` enforces the structural half — the
    registry cannot SEE harvest. This is the half about the tables themselves,
    and it was stated in `collect/CLAUDE.md` and never checked.
    """
    written = _tables_written(path) & JUDGEMENT_TABLES
    assert not written, f"{path} writes {sorted(written)}, which judge/ owns"


# ── the bridge the top-level check cannot see ─────────────────────────────
#
# ADDED 2026-08-20, AFTER MEASURING WHAT THE CHECK ABOVE ACTUALLY MATCHES.
# `_imported_roots` takes `name.split(".")[0]`, so it sees a TOP-LEVEL name and
# nothing else:
#
#     from collect.rawstore_reader import X   ->  {"collect"}          CAUGHT
#     import rawstore_reader                 ->  {"rawstore_reader"}  not caught
#     from store.rawstore_reader import X     ->  {"store"}            not caught
#
# So the two lane assertions are total over what they can see, and what they
# cannot see is **anything that is not a lane**. A root-level module or a third
# package is invisible to both — which matters because the proposal on the table
# is to move a shared reader to exactly such a place. The check would keep
# passing and would have stopped saying anything about the case it was quoted
# for.
#
# `collect/rawstore_reader.py` is inside a lane today, so `judge/` importing it
# IS caught. This closes the hole that opens the moment it is not: a one-hop
# bridge, asserted directly rather than by an allowlist of permitted modules.
#
# One hop rather than a full graph walk, deliberately. A transitive closure over
# every import turns one refusal into a chain a reader has to reconstruct, and
# the failure this catches is a module sitting between the lanes on purpose —
# which is one hop by construction. Deeper than that is a different defect and
# wants a different message.


def _repo_module_path(module: str) -> Path | None:
    """The file a dotted module name resolves to inside this repo, if any."""
    parts = module.split(".")
    candidates = (ROOT.joinpath(*parts).with_suffix(".py"), ROOT.joinpath(*parts, "__init__.py"))
    return next((c for c in candidates if c.is_file()), None)


@pytest.mark.parametrize("path", sorted((ROOT / "judge").rglob("*.py")), ids=str)
def test_judge_never_imports_a_module_that_imports_collect(path: Path):
    """No module may sit between the lanes and pass bytes across.

    The pair this asserts is `judge/` and `collect/`, the same pair as
    `test_judge_never_imports_collect` — this one reaches through a module that
    is in neither. Modelled on `test_registry_never_imports_harvest`: a specific
    pair, asserted directly, rather than a list of modules that are allowed to be
    in the middle. A list would answer "is this on the list" where the question
    is "does this cross the boundary", and it grows one reasonable case at a time.
    """
    bridges = {}
    for module in _imported_modules(path):
        if module.split(".")[0] in {"collect", "judge"}:
            continue  # the direct case; the assertions above own it
        target = _repo_module_path(module)
        if target is None:
            continue  # third-party or stdlib
        if "collect" in _imported_roots(target):
            bridges[module] = target.relative_to(ROOT).as_posix()

    assert not bridges, (
        f"{path.relative_to(ROOT).as_posix()} imports "
        + ", ".join(f"{m} ({p})" for m, p in sorted(bridges.items()))
        + " — and that module imports collect/. A shared module that can reach a "
        "lane is a corridor between the lanes, and the top-level import check "
        "cannot see it: `import x` yields the root `x`, never `collect`."
    )


def test_the_bridge_check_can_actually_fail(tmp_path):
    """Habit 3: a guard nobody has watched fail is a guard nobody has tested.

    Builds the exact shape the assertion above exists to refuse — a module
    outside both lanes that imports `collect/` — and confirms the predicate
    catches it. Without this, the parametrised test passes because the shape does
    not exist yet rather than because it is refused.
    """
    bridge = ROOT / "_bridge_probe.py"
    consumer = tmp_path / "consumer.py"
    consumer.write_text("import _bridge_probe\n", encoding="utf-8")
    bridge.write_text("from collect.rawstore import RawStore\n", encoding="utf-8")
    try:
        found = {
            module: _repo_module_path(module)
            for module in _imported_modules(consumer)
            if module.split(".")[0] not in {"collect", "judge"}
        }
        assert found == {"_bridge_probe": bridge}, "the module did not resolve to a repo file"
        assert "collect" in _imported_roots(bridge), "the bridge's own import was not seen"
    finally:
        bridge.unlink()
