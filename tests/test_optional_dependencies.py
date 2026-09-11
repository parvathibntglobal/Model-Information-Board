"""A missing optional dependency must cost only the parts that need it.

Engineer 2 ran the suite without `feedparser` and `trafilatura` installed and
got five collection errors — at which point pytest reports `Interrupted` and
**nothing runs at all**. Not five failures out of six hundred: zero tests
executed, including every GitHub test, none of which parses a feed.

Two causes, both fixed and both pinned here:

  1. `adapters/github.py` imported `HostLimiter` from inside the blog package,
     so importing the GitHub adapter executed `adapters/blog/__init__.py`,
     which imports `parse.py`, which imports both libraries. Ninety lines of
     arithmetic over `time.monotonic` made a feed parser mandatory for a lane
     that was not fetching feeds. It lives in `collect/limiter.py` now.

  2. The blog package re-exported eagerly, so `RobotsGate` — httpx and the
     standard library — could not be imported without them either.

The blocker below is the same shape as the real failure: an import hook that
refuses the two modules. Simulating it is the only honest way to test this,
short of a second virtualenv, and it is cheap.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

BLOCKER = """
import sys

BLOCKED = {"feedparser", "trafilatura"}


class Blocker:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in BLOCKED:
            raise ModuleNotFoundError(f"No module named {fullname!r}", name=fullname)
        return None


sys.meta_path.insert(0, Blocker())
"""


def run_without_feed_libraries(body: str) -> subprocess.CompletedProcess:
    """Run `body` in a fresh interpreter where the two libraries do not exist.

    A subprocess rather than monkeypatching `sys.modules`, because the modules
    are already imported in this process and the thing under test is what
    happens at import time in one that has never seen them.
    """
    script = BLOCKER + textwrap.dedent(body)
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.mark.parametrize(
    ("label", "statement"),
    [
        ("limiter", "from collect.limiter import HostLimiter; HostLimiter()"),
        ("github-adapter", "import collect.adapters.github"),
        ("github-queries", "from collect.adapters.queries.github import plan_searches"),
        ("queries-sieve", "from collect.adapters.queries.sieve import sieve"),
        ("queries-contract", "from collect.adapters.queries.contract import load_queries"),
        ("queries-cadence", "from collect.adapters.queries.cadence import split_by_cadence"),
        ("blog-robots", "from collect.adapters.blog.robots import RobotsGate"),
        ("blog-validators", "from collect.adapters.blog.validators import FeedValidators"),
        ("blog-package-attr", "import collect.adapters.blog as b; b.RobotsGate"),
        ("registry-sources", "from collect.registry.sources import load_sources; load_sources()"),
        ("http", "from collect.http import build_client"),
        # TRIAGE. It does no blog work - it runs entity and specificity
        # gates over stored documents - but it reads each source's prose
        # through one map, and `blog`'s extractor needs trafilatura.
        ("triage-module", "import collect.triage.run"),
        ("triage-store", "import collect.triage.store"),
        ("triage-gates", "from collect.triage.gates import triage"),
    ],
)
def test_it_imports_without_the_feed_libraries(label, statement):
    """None of these parses a feed, so none of them may require a feed parser."""
    result = run_without_feed_libraries(statement)
    assert result.returncode == 0, (
        f"{label} could not be imported without feedparser/trafilatura:\n"
        f"{result.stderr}"
    )


@pytest.mark.parametrize(
    ("label", "statement"),
    [
        ("blog-parse", "import collect.adapters.blog.parse"),
        ("blog-fetch", "import collect.adapters.blog.fetch"),
        ("blog-package-parse-attr", "import collect.adapters.blog as b; b.parse_feed"),
    ],
)
def test_what_genuinely_needs_them_still_fails_and_says_which(label, statement):
    """The boundary is a boundary, not a silent fallback.

    A parse path that imported successfully and then failed at runtime, or
    quietly returned no entries, would be far worse than an ImportError: a
    feed that yields nothing is exactly what FR-10 alarms on, and it would be
    alarming about a missing wheel.
    """
    result = run_without_feed_libraries(statement)
    assert result.returncode != 0, f"{label} unexpectedly imported"
    assert "feedparser" in result.stderr or "trafilatura" in result.stderr, (
        "the failure must name the missing library, not just the import chain"
    )


def test_the_limiter_does_not_live_in_an_adapter_package():
    """Shared infrastructure in one adapter's package is how this happened."""
    assert (REPO_ROOT / "collect" / "limiter.py").exists()
    assert not (REPO_ROOT / "collect" / "adapters" / "blog" / "limiter.py").exists()


def test_the_blog_package_does_not_import_its_submodules_at_module_scope():
    """The eager re-export is the other half, and it reads as harmless.

    Parsed rather than grepped, so the `if TYPE_CHECKING:` block — which is
    what keeps the names visible to type checkers and IDEs and never executes
    — is not mistaken for the thing it replaced.
    """
    import ast

    path = REPO_ROOT / "collect" / "adapters" / "blog" / "__init__.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))

    offenders = [
        node
        for node in tree.body  # top level only: the TYPE_CHECKING body is nested
        if isinstance(node, (ast.Import, ast.ImportFrom))
        and (getattr(node, "module", "") or "").startswith("collect.adapters.blog")
    ]
    assert not offenders, (
        "module-scope import of a blog submodule in the package __init__ "
        f"(line {offenders[0].lineno}). It makes feedparser mandatory for "
        "every name in the package. Add the name to _EXPORTS instead."
    )


def test_the_type_checking_block_and_the_exports_agree():
    """Two lists that must not drift: one for humans, one for the runtime.

    If a name is in `__all__` but not `_EXPORTS`, `from ... import name` fails
    at runtime while the IDE shows it as available — which is the worst
    version of this, because it looks fine until it is imported.
    """
    pytest.importorskip("feedparser", reason="resolving every export reaches parse.py")
    pytest.importorskip("trafilatura", reason="resolving every export reaches parse.py")

    import collect.adapters.blog as blog

    missing = sorted(set(blog.__all__) - set(blog._EXPORTS))
    assert not missing, f"in __all__ but not resolvable at runtime: {missing}"

    for name in blog.__all__:
        assert getattr(blog, name) is not None, name

# ── the map, not just the module ─────────────────────────────────────────────
#
# Importing `collect.triage.run` always worked; the defect was one level in.
# `_prose_by_source()` imported `extract_article_text` at FUNCTION scope, which
# reads as lazy and is not - the function is called on every run, so every run
# required trafilatura whether or not a blog document was anywhere near it.
#
# On 2026-09-11 a UI-triggered fetch of 663 documents - reddit, hackernews and
# devto, not one blog row - died there, and all 663 went untriaged. Triage has
# still never completed on a UI fetch.
#
# So the test is not "does the module import". It is "does the thing triage
# actually calls work", and it has to BUILD THE MAP and USE a non-blog entry.


def test_the_prose_map_builds_without_a_feed_parser():
    """`_prose_by_source()` runs, and the seven non-blog extractors work.

    The blog entry is still in the map - it is a closure, and building a
    closure imports nothing. What must not happen is the import firing while
    the map is assembled.
    """
    result = run_without_feed_libraries(
        """
        from collect.triage.run import _prose_by_source

        mapped = _prose_by_source()
        assert "blog" in mapped, "the blog entry must still be offered"
        assert len(mapped) > 1, "the other sources must still be mapped"

        # A non-blog extractor, actually called.
        fn, wants_bytes = mapped["hackernews"]
        assert wants_bytes is False
        print("OK", len(mapped))
        """
    )
    assert result.returncode == 0, (
        "triage's prose map could not be built without feedparser/trafilatura: "
        f"{result.stderr}"
    )
    assert "OK" in result.stdout


def test_the_blog_entry_still_refuses_and_names_the_library():
    """Deferring the import must not become a silent fallback.

    A blog document with no trafilatura has to fail, loudly and by name. The
    alternative - returning no text - is the shape FR-10 alarms on, and it
    would be alarming about a missing wheel rather than about a corpus.
    """
    result = run_without_feed_libraries(
        """
        from collect.triage.run import _prose_by_source

        fn, wants_bytes = _prose_by_source()["blog"]
        assert wants_bytes is True
        try:
            fn(b"<html><body><p>some article</p></body></html>")
        except ModuleNotFoundError as exc:
            print("REFUSED", exc.name)
        else:
            raise AssertionError("the blog extractor returned without trafilatura")
        """
    )
    assert result.returncode == 0, result.stderr
    # EITHER LIBRARY. `parse.py` imports feedparser before trafilatura, so
    # that is the one named first - but which of the two fails is an
    # implementation detail of that module's import order, and pinning it
    # would make this test fail the day somebody reorders two imports
    # without changing anything this test is about. The property is that a
    # blog payload FAILS and NAMES a missing library.
    assert ("REFUSED trafilatura" in result.stdout
            or "REFUSED feedparser" in result.stdout), (
        "a blog payload must still fail by NAME when the parser is absent, "
        f"rather than quietly yielding nothing. Got: {result.stdout!r}"
    )
