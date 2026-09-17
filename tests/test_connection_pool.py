"""The connection pool, and the three ways a pool is worse than no pool.

WHY THERE IS A POOL AT ALL. Measured 2026-09-17 against the shared database:
`psycopg.connect` takes 1.58s and a trivial query 0.25s, because the database is
remote. `_conn()` dialled a new connection per request, and `/admin/usage` opened
four of them — five seconds of a sixteen-second endpoint spent on handshakes for
connections that were then thrown away.

⚠ A POOL TRADES ONE FAILURE FOR THREE NEW ONES, and these are the three. Each is
  worse than the slow page it replaced, because each is silent:

    - a connection handed out twice, so two requests share a transaction
    - a dead connection handed out as if it were live
    - a connection to the PREVIOUS database handed out after the DSN changed,
      which reads the wrong data and says nothing

  None is caught by an endpoint test, because all three need either concurrency
  or a second database to show up at all.
"""

from __future__ import annotations

import threading

import pytest

from judge.app import _ConnectionPool


class FakeConnection:
    """Enough of a psycopg connection to exercise the pool's own logic."""

    def __init__(self, url: str = "postgresql://x/y") -> None:
        self.url = url
        self.closed = False
        self.rollbacks = 0
        self.rollback_raises = False

    def rollback(self) -> None:
        self.rollbacks += 1
        if self.rollback_raises:
            raise RuntimeError("this session is broken")

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def pool(monkeypatch):
    """A pool whose `connect` is a counter rather than a network call."""
    made: list[FakeConnection] = []

    def fake_connect(url, **_):
        conn = FakeConnection(url)
        made.append(conn)
        return conn

    import psycopg

    monkeypatch.setattr(psycopg, "connect", fake_connect)
    p = _ConnectionPool()
    p.made = made
    return p


URL = "postgresql://user:pw@db.example.net:5432/boarddb"


def test_a_returned_connection_is_reused_rather_than_redialled(pool):
    """The whole point: the second request must not pay the handshake."""
    first = pool.take(URL)
    pool.give_back(first, reusable=True)
    second = pool.take(URL)

    assert second is first
    assert len(pool.made) == 1, "the pool dialled twice for two sequential uses"


def test_a_connection_is_never_handed_to_two_callers_at_once(pool):
    """⚠ The failure that would make two requests share one transaction."""
    held = [pool.take(URL) for _ in range(_ConnectionPool.MAX)]
    assert len({id(c) for c in held}) == len(held), "the same connection twice"
    for conn in held:
        pool.give_back(conn, reusable=True)


def test_the_pool_never_opens_more_than_its_limit(pool):
    """A hosted database's connection limit is somebody else's to raise.

    The (MAX + 1)th caller must WAIT rather than open another. Asserted by
    showing the extra caller is still blocked while every slot is held, and
    completes the moment one is handed back.
    """
    held = [pool.take(URL) for _ in range(_ConnectionPool.MAX)]
    got = threading.Event()

    def extra():
        conn = pool.take(URL)
        got.set()
        pool.give_back(conn, reusable=True)

    waiter = threading.Thread(target=extra, daemon=True)
    waiter.start()

    assert not got.wait(timeout=0.4), (
        "a caller got a connection while all "
        f"{_ConnectionPool.MAX} slots were held - the limit is not a limit"
    )
    assert len(pool.made) == _ConnectionPool.MAX

    pool.give_back(held.pop(), reusable=True)
    assert got.wait(timeout=5), "the waiting caller was never served"
    waiter.join(timeout=5)

    for conn in held:
        pool.give_back(conn, reusable=True)


def test_a_failed_request_does_not_put_its_connection_back(pool):
    """⚠ RULE 6-shaped: an unknown session state is not a usable one.

    An exception may have left the session mid-transaction or the socket
    half-dead. Reconnecting is cheap; handing that to the next request as if it
    were fresh is not.
    """
    conn = pool.take(URL)
    pool.give_back(conn, reusable=False)

    assert conn.closed
    assert pool.take(URL) is not conn
    assert len(pool.made) == 2


def test_a_dead_connection_is_discarded_rather_than_served(pool):
    """A pooled connection can die while it is sitting in the pool.

    The server restarts, a NAT drops it, and `closed` still reads False. The
    rollback is the cheap probe that finds out, and it must not raise out of
    the pool.
    """
    conn = pool.take(URL)
    pool.give_back(conn, reusable=True)
    conn.rollback_raises = True

    served = pool.take(URL)
    assert served is not conn
    assert conn.closed, "the dead connection was left open"


def test_reuse_clears_the_last_caller_s_transaction(pool):
    """The other half of the liveness probe, and the reason it is a rollback.

    A connection carrying an open transaction from a previous request would let
    one request see another's uncommitted rows.
    """
    conn = pool.take(URL)
    pool.give_back(conn, reusable=True)
    before = conn.rollbacks

    assert pool.take(URL) is conn
    assert conn.rollbacks > before, "the session was reused without being reset"


def test_changing_the_dsn_empties_the_pool(pool):
    """⚠ THE SILENT ONE: a connection to the database we USED to be pointed at.

    Tests point the app at a different database mid-process. Serving a pooled
    connection to the previous one reads the wrong data and raises nothing at
    all, which makes it the only failure here that could be believed.
    """
    old = pool.take(URL)
    pool.give_back(old, reusable=True)

    other = pool.take("postgresql://user:pw@other.example.net:5432/otherdb")
    assert other is not old
    assert old.closed, "a connection to the previous database was kept"
    assert other.url.endswith("otherdb")


def test_a_refused_connection_does_not_leak_a_slot(pool, monkeypatch):
    """A database that is down must not permanently shrink the pool.

    The slot is released on the way out, so MAX failed attempts leave MAX slots
    free rather than none — otherwise the first outage would wedge the board
    until it was restarted.
    """
    import psycopg

    def refuse(*_a, **_k):
        raise OSError("connection refused")

    monkeypatch.setattr(psycopg, "connect", refuse)
    for _ in range(_ConnectionPool.MAX + 2):
        with pytest.raises(OSError):
            pool.take(URL)

    # Every slot is free again, so a recovered database is served immediately.
    monkeypatch.setattr(psycopg, "connect", lambda url, **_: FakeConnection(url))
    held = [pool.take(URL) for _ in range(_ConnectionPool.MAX)]
    assert len(held) == _ConnectionPool.MAX
