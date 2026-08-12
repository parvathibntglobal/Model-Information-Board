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
