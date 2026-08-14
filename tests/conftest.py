"""Database access for the write-path tests, and the guards around it.

Two jobs, and the first one matters more than it looks.

**Silence is the defect.** Six real defects survived a green suite because
`tests/test_registry_load_db.py` skipped for want of a database, and a skip
reads as success. It gets worse as the suite grows: 247 passed with 9 silent
skips looks healthier than the 139 that originally hid the bugs. So a missing
database is a **failure** by default, not a skip. `ALLOW_MISSING_TEST_DB=1`
degrades it to a skip for a laptop that genuinely has no server, and says so
loudly in the run summary, because an override whose consequence is invisible
becomes permanent the first time somebody puts it in a shell profile.

**The suite destroys the database it points at.** `conn` runs
DROP SCHEMA public CASCADE before every test. Pointed at anything real, that
is a very bad afternoon. Three layers stop it, cheapest and clearest first.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
ENV_TEST = ROOT / ".env.test"

ALLOW_MISSING = "ALLOW_MISSING_TEST_DB"
DSN_VAR = "TEST_DATABASE_URL"

#: Written by scripts/dev-postgres.ps1, in its own schema so that it survives
#: the DROP SCHEMA public CASCADE the fixture runs on every test.
SENTINEL = "modelboard_meta.disposable"

_override_used = False


# ── resolving the DSN ─────────────────────────────────────────────────────


def _from_env_test() -> str | None:
    """Read TEST_DATABASE_URL out of .env.test, if the bring-up script wrote one.

    Deliberately not python-dotenv: this must work before any dependency is
    importable, and it is four lines.
    """
    if not ENV_TEST.exists():
        return None
    # utf-8-sig, not utf-8: Windows PowerShell 5.1's `Set-Content -Encoding
    # utf8` writes a BOM, which would otherwise make the first key parse as
    # "﻿TEST_DATABASE_URL" and silently fail to match.
    for line in ENV_TEST.read_text(encoding="utf-8-sig").splitlines():
        key, _, value = line.partition("=")
        if key.strip() == DSN_VAR and value.strip():
            return value.strip()
    return None


def test_database_url() -> str | None:
    """The environment wins; .env.test is the convenience fallback."""
    return os.getenv(DSN_VAR) or _from_env_test()


_MISSING_MESSAGE = f"""
The registry write-path tests have no database, so the write path is NOT covered.

This is a failure rather than a skip on purpose. Six defects in `collect/`
reached a commit because these exact tests skipped silently while the suite
reported green.

To fix it:
    pwsh scripts/dev-postgres.ps1        # creates a disposable local instance
                                         # and writes .env.test

To acknowledge it and move on:
    set {ALLOW_MISSING}=1                # the run will say the write path is uncovered

See docs/dev-database.md.
""".strip()


# ── the three safety layers ───────────────────────────────────────────────


class UnsafeTestDatabase(RuntimeError):
    """The target is not a database this suite is allowed to destroy."""


def assert_safe_target(dsn: str) -> None:
    """Layers 1 and 2, checked **before** a connection is opened.

    Ordering is deliberate. These two need no database, so a DSN pointing at
    RDS is rejected without ever authenticating against it. Layered so the
    message matches the mistake: somebody who pointed TEST_DATABASE_URL at a
    real server should be told "this is not localhost", not "no sentinel
    table found", which reads like a setup problem rather than the near miss
    it is.
    """
    parts = urlsplit(dsn)

    if parts.hostname not in ("localhost", "127.0.0.1", "::1"):
        raise UnsafeTestDatabase(
            f"Refusing to run destructive tests against {parts.hostname!r}. "
            f"These tests DROP SCHEMA public CASCADE, and {DSN_VAR} must point "
            "at a local disposable instance. See docs/dev-database.md."
        )

    dbname = parts.path.lstrip("/")
    if not dbname.endswith("_test"):
        raise UnsafeTestDatabase(
            f"Refusing to run destructive tests against database {dbname!r}: "
            "the name must end with '_test'. These tests DROP SCHEMA public "
            "CASCADE. See docs/dev-database.md."
        )


def assert_disposable(conn: Any, dsn: str) -> None:
    """Layer 3, the one that actually works, checked once connected.

    Layers 1 and 2 are guessable: somebody runs a local proxy, or names a
    real database `modelboard_test`. The sentinel requires a deliberate act,
    and it records the DSN it was created for, so copying the table into a
    real database to unblock yourself does not work either.

    Callers must run `assert_safe_target` first; this re-runs it so the
    function is safe on its own.
    """
    assert_safe_target(dsn)

    marked = conn.execute("SELECT to_regclass(%s) IS NOT NULL", (SENTINEL,)).fetchone()
    if not (marked and marked[0]):
        raise UnsafeTestDatabase(
            f"Refusing to run destructive tests against {dsn}: no {SENTINEL} "
            "table, so this instance was not created by scripts/dev-postgres.ps1. "
            "These tests DROP SCHEMA public CASCADE. If this really is a "
            "throwaway database, run the script against it rather than creating "
            "the table by hand."
        )

    rows = conn.execute(f"SELECT dsn FROM {SENTINEL}").fetchall()  # noqa: S608
    if not any(_same_target(dsn, recorded[0]) for recorded in rows):
        raise UnsafeTestDatabase(
            f"Refusing to run destructive tests against {dsn}: the {SENTINEL} "
            f"mark was created for a different target ({[r[0] for r in rows]}). "
            "A sentinel copied into another database does not make that "
            "database disposable."
        )


def _same_target(left: str, right: str) -> bool:
    """Compare host, port and database name, ignoring credentials and options."""
    a, b = urlsplit(left), urlsplit(right)
    return (a.hostname, a.port, a.path) == (b.hostname, b.port, b.path)


# ── fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def test_dsn() -> str:
    """The DSN for destructive tests, or a loud failure explaining its absence."""
    global _override_used

    dsn = test_database_url()
    if dsn:
        return dsn

    if os.getenv(ALLOW_MISSING):
        _override_used = True
        pytest.skip(
            f"WRITE PATH NOT COVERED: no {DSN_VAR}, and {ALLOW_MISSING} is set. "
            "These tests were not run.",
            allow_module_level=True,
        )

    pytest.fail(_MISSING_MESSAGE, pytrace=False)
    raise AssertionError("unreachable")  # pragma: no cover


# ── the blog parse path's optional dependencies ───────────────────────────
#
# `feedparser` and `trafilatura` are needed by exactly one module,
# `collect/adapters/blog/parse.py`. Without them installed, the four test
# modules that genuinely parse feeds raised at import time, pytest reported
# `Interrupted: 5 errors during collection`, and NOTHING RAN — six hundred
# tests with no relationship to feed parsing, silently not executed.
#
# So those four skip instead, and say so loudly. Same reasoning as the
# database banner above and the same danger: a skip reads as success, so an
# uncovered path that announces itself in the summary is the only acceptable
# version of one.

FEED_LIBRARIES = ("feedparser", "trafilatura")
_feed_skip_used = False


def missing_feed_libraries() -> list[str]:
    """Which of the blog parse path's libraries are not installed."""
    from importlib.util import find_spec

    missing = []
    for name in FEED_LIBRARIES:
        try:
            found = find_spec(name) is not None
        except (ImportError, ModuleNotFoundError, ValueError):
            found = False
        if not found:
            missing.append(name)
    return missing


def require_feed_libraries() -> None:
    """Skip the calling module if the blog parse path cannot be imported.

    Called ABOVE the imports it guards, which is why those imports sit below
    it rather than at the top of the file: the point is to skip before the
    ImportError, not to catch one afterwards.
    """
    missing = missing_feed_libraries()
    if not missing:
        return

    global _feed_skip_used
    _feed_skip_used = True
    pytest.skip(
        f"BLOG PARSE PATH NOT COVERED: {', '.join(missing)} not installed. "
        "These tests were not run.",
        allow_module_level=True,
    )


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    """Say it in the summary, not only in a skip reason nobody reads.

    Skip reasons need `-rs` to show. An override that hides its own
    consequence is how the next set of defects gets through.
    """
    if _override_used:
        terminalreporter.write_sep("=", "WRITE PATH NOT COVERED", red=True, bold=True)
        terminalreporter.write_line(
            f"  The registry write-path tests did not run: {ALLOW_MISSING} is set "
            f"and {DSN_VAR} is unset."
        )
        terminalreporter.write_line(
            "  A green result here does NOT mean the database write path works. "
            "Run scripts/dev-postgres.ps1."
        )

    if _feed_skip_used:
        terminalreporter.write_sep("=", "BLOG PARSE PATH NOT COVERED", red=True, bold=True)
        terminalreporter.write_line(
            f"  Not installed: {', '.join(missing_feed_libraries())}. The blog "
            "feed parsing and fetch tests did not run."
        )
        terminalreporter.write_line(
            "  A green result here does NOT mean the blog adapter works — and "
            "blogs are the only positive-evidence channel. Run: "
            "pip install -e '.[blog]'  (or the project's full dev install)."
        )
