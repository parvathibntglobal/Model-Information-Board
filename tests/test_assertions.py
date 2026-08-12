"""The startup assertion that keeps build fixtures out of production."""

from __future__ import annotations

import pytest

from collect.registry.assertions import FixtureLeakError, assert_no_fixtures


class FakeCursor:
    def __init__(self, value: int) -> None:
        self._value = value

    def fetchone(self):
        return (self._value,)


class FakeConn:
    """Answers the two count queries with fixed numbers."""

    def __init__(self, seeded: int, handmade: int) -> None:
        self.seeded = seeded
        self.handmade = handmade
        self.queries: list[str] = []

    def execute(self, sql: str):
        self.queries.append(sql)
        return FakeCursor(self.seeded if "model_version" in sql else self.handmade)


def test_development_skips_the_check():
    conn = FakeConn(seeded=10, handmade=180)
    assert_no_fixtures(conn, environment="development")
    assert conn.queries == []


def test_clean_database_starts():
    assert_no_fixtures(FakeConn(0, 0), environment="production")


@pytest.mark.parametrize("seeded,handmade", [(10, 0), (0, 180), (10, 180)])
def test_any_fixture_refuses_to_start(seeded: int, handmade: int):
    with pytest.raises(FixtureLeakError):
        assert_no_fixtures(FakeConn(seeded, handmade), environment="production")


def test_the_error_names_what_it_found():
    with pytest.raises(FixtureLeakError, match="10 seeded model"):
        assert_no_fixtures(FakeConn(10, 0), environment="production")
