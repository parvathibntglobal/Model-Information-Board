"""Kite Pulse outreach: design guards over EVERY outreach folder.

  * nothing in it sends a write request to any platform (no posting: a person
    posts every reply by hand). GitHub's GraphQL takes reads as POSTs, so
    `github/client.py` is the ONE file allowed a POST, and only GraphQL
    queries: no outreach file may contain a mutation;
  * it imports nothing from collect/ except collect.config, so it can never
    reach MIB's evidence writers.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

OUTREACH = Path(__file__).resolve().parent.parent / "web" / "src" / "kitepulse" / "outreach"

_WRITE_CALL = re.compile(
    r"\.(post|put|patch|delete)\s*\(|method\s*=\s*[\"'](POST|PUT|PATCH|DELETE)",
    re.I,
)


def _sources() -> list[Path]:
    found = sorted(OUTREACH.rglob("*.py"))
    # The guard must be guarding something: an empty scan passes by construction.
    assert any(p.parent.name == "hackernews" for p in found)
    assert any(p.parent.name == "discourse" for p in found)
    assert any(p.parent.name == "devto" for p in found)
    assert any(p.parent.name == "github" for p in found)
    return found


# The GraphQL client: its POSTs carry queries only (checked below).
_GRAPHQL_CLIENT = Path("github") / "client.py"


def test_no_outreach_code_sends_a_write_request():
    offenders = [f"{p.relative_to(OUTREACH)}:{n}"
                 for p in _sources()
                 for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
                 if _WRITE_CALL.search(line)
                 and not (p.relative_to(OUTREACH) == _GRAPHQL_CLIENT
                          and ".post(self.base + GRAPHQL," in line)]
    assert offenders == [], f"outreach must only read from platforms: {offenders}"


def test_the_graphql_client_posts_only_to_graphql_and_sends_no_mutation():
    client = OUTREACH / _GRAPHQL_CLIENT
    posts = [ln for ln in client.read_text(encoding="utf-8").splitlines() if ".post(" in ln]
    assert len(posts) == 1 and ".post(self.base + GRAPHQL," in posts[0], posts
    mutations = [f"{p.relative_to(OUTREACH)}:{n}"
                 for p in _sources()
                 for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
                 if re.search(r"\bmutation\b", line, re.I)]
    assert mutations == [], f"no GraphQL mutation may appear in outreach: {mutations}"


def test_outreach_imports_nothing_from_collect_but_config():
    allowed = {"collect.config"}
    found = set()
    for p in _sources():
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module and (
                    node.module == "collect" or node.module.startswith("collect.")):
                found.add(node.module)
            elif isinstance(node, ast.Import):
                found |= {a.name for a in node.names if a.name.split(".")[0] == "collect"}
    assert found <= allowed, f"unexpected collect/ imports: {found - allowed}"
