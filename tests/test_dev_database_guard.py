"""The guard that stops the suite destroying a database it should not.

`tests/test_registry_load_db.py` runs DROP SCHEMA public CASCADE before every
test. These are the checks that decide whether it is allowed to, and they run
without a database of their own.
"""

from __future__ import annotations

import pytest

from tests.conftest import (
    SENTINEL,
    UnsafeTestDatabase,
    _from_env_test,
    _same_target,
    assert_disposable,
    assert_safe_target,
)

LOCAL = "postgresql://postgres@localhost:5433/modelboard_test"


# ── layer 1: host allowlist ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "dsn",
    [
        "postgresql://user:pw@prod.abc123.eu-west-1.rds.amazonaws.com:5432/modelboard_test",
        "postgresql://user@10.0.0.7:5432/modelboard_test",
        "postgresql://user@db.internal:5432/modelboard_test",
    ],
)
def test_a_remote_host_is_refused(dsn: str):
    with pytest.raises(UnsafeTestDatabase, match="Refusing"):
        assert_safe_target(dsn)


def test_the_remote_message_names_the_host_not_the_sentinel():
    """The message must match the mistake.

    Someone who pointed this at RDS should read "this is not localhost", not
    "no sentinel table found", which sounds like a setup problem rather than
    the near miss it is.
    """
    dsn = "postgresql://user@prod.rds.amazonaws.com:5432/modelboard_test"
    with pytest.raises(UnsafeTestDatabase) as excinfo:
        assert_safe_target(dsn)
    assert "prod.rds.amazonaws.com" in str(excinfo.value)
    assert SENTINEL not in str(excinfo.value)


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1"])
def test_local_hosts_pass_layer_one(host: str):
    assert_safe_target(f"postgresql://postgres@{host}:5433/modelboard_test")


# ── layer 2: the database name ────────────────────────────────────────────


@pytest.mark.parametrize("dbname", ["modelboard", "postgres", "modelboard_prod"])
def test_a_database_not_named_test_is_refused(dbname: str):
    with pytest.raises(UnsafeTestDatabase, match="_test"):
        assert_safe_target(f"postgresql://postgres@localhost:5433/{dbname}")


# ── layer 3: the sentinel ─────────────────────────────────────────────────


class FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


class FakeConn:
    """Answers the two sentinel queries: does it exist, and what does it say."""

    def __init__(self, *, exists: bool, recorded: list[str] | None = None):
        self.exists = exists
        self.recorded = recorded or []

    def execute(self, sql: str, params=None):
        if "to_regclass" in sql:
            return FakeCursor([(self.exists,)])
        return FakeCursor([(dsn,) for dsn in self.recorded])


def test_an_unmarked_database_is_refused():
    """A real database will not carry the mark, and nobody adds it by accident."""
    with pytest.raises(UnsafeTestDatabase, match="dev-postgres"):
        assert_disposable(FakeConn(exists=False), LOCAL)


def test_a_marked_database_matching_its_dsn_is_accepted():
    assert_disposable(FakeConn(exists=True, recorded=[LOCAL]), LOCAL)


def test_a_sentinel_copied_from_another_database_is_refused():
    """Closes the "copy the table to unblock myself" route.

    The mark records the DSN it was created for, so lifting it into a
    different database does not make that database disposable.
    """
    other = "postgresql://postgres@localhost:5433/somethingelse_test"
    with pytest.raises(UnsafeTestDatabase, match="different target"):
        assert_disposable(FakeConn(exists=True, recorded=[other]), LOCAL)


def test_layer_three_still_enforces_the_earlier_layers():
    """assert_disposable is safe called on its own."""
    remote = "postgresql://postgres@prod.example.com:5432/modelboard_test"
    with pytest.raises(UnsafeTestDatabase, match="prod.example.com"):
        assert_disposable(FakeConn(exists=True, recorded=[remote]), remote)


# ── DSN comparison ────────────────────────────────────────────────────────


def test_credentials_and_options_do_not_affect_the_match():
    assert _same_target(
        "postgresql://postgres@localhost:5433/modelboard_test",
        "postgresql://someone:secret@localhost:5433/modelboard_test?sslmode=disable",
    )


@pytest.mark.parametrize(
    "other",
    [
        "postgresql://postgres@localhost:5432/modelboard_test",  # port
        "postgresql://postgres@127.0.0.1:5433/modelboard_test",  # host spelling
        "postgresql://postgres@localhost:5433/other_test",  # database
    ],
)
def test_a_different_target_does_not_match(other: str):
    assert not _same_target(LOCAL, other)


# ── the .env.test reader ──────────────────────────────────────────────────


def test_env_test_is_read_despite_a_utf8_bom(tmp_path, monkeypatch):
    """Windows PowerShell 5.1 writes a BOM, which would hide the first key."""
    import tests.conftest as conftest

    path = tmp_path / ".env.test"
    path.write_text("TEST_DATABASE_URL=" + LOCAL + "\n", encoding="utf-8-sig")
    monkeypatch.setattr(conftest, "ENV_TEST", path)
    assert _from_env_test() == LOCAL


def test_a_missing_env_test_is_not_an_error(tmp_path, monkeypatch):
    import tests.conftest as conftest

    monkeypatch.setattr(conftest, "ENV_TEST", tmp_path / "absent")
    assert _from_env_test() is None
