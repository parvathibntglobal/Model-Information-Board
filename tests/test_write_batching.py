"""One round trip per batch, not per row — and honest insert counts.

`write_authors` took ten minutes for 4,391 rows against a remote instance,
roughly 130ms of latency each and almost no work, and 3.8 seconds batched. Two
other writers had the same shape and had never met volume:
`github.write_documents` (never run against a remote at all) and
`openrouter.write_model_versions` (340 rows, nightly).

THE SHAPE IS WHAT THESE TESTS PIN, not the timing. A latency assertion would
pass on a local Postgres where 130ms is 1ms, which is exactly why the defect
survived: every run so far was local. Counting statements against a fake
connection fails on a per-row loop wherever it runs.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from collect.adapters.github import GitHubHarvester


class _Cursor:
    """Records what was issued, and nothing else."""

    def __init__(self, log: list[tuple[str, int]]) -> None:
        self._log = log
        self.rowcount = 0
        self.pgresult = None

    def execute(self, statement, params=None):
        self._log.append(("execute", 1))
        return self

    def executemany(self, statement, params_seq, *, returning=False):
        rows = list(params_seq)
        self._log.append(("executemany", len(rows)))
        self.rowcount = len(rows)
        return None

    def fetchone(self):
        return None

    def nextset(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeConn:
    def __init__(self) -> None:
        self.log: list[tuple[str, int]] = []

    def cursor(self, **kwargs):
        return _Cursor(self.log)

    def execute(self, statement, params=None):
        cur = _Cursor(self.log)
        return cur.execute(statement, params)

    @property
    def statements(self) -> int:
        return len(self.log)


# ── github.write_documents ────────────────────────────────────────────────


@dataclass
class _Hit:
    created_at = None
    comment_count = 3
    reactions = 1


@dataclass
class _Stored:
    external_id: str
    html_url: str = "https://github.com/o/r/issues/1"
    ref: str = "raw/ab/cd"
    content_hash: str = "abcd"
    hit: _Hit = None

    def __post_init__(self):
        self.hit = self.hit or _Hit()


class _Run:
    def __init__(self, count: int) -> None:
        self.stored = [_Stored(external_id=f"i{n}") for n in range(count)]


@pytest.mark.parametrize(("rows", "batch", "expected"), [(0, 500, 0), (1, 500, 1),
                                                         (500, 500, 1), (1200, 500, 3)])
def test_documents_cost_one_statement_per_batch(rows, batch, expected):
    """1,200 documents used to be 1,200 round trips. It is now three."""
    conn = FakeConn()
    GitHubHarvester.write_documents(None, conn, _Run(rows), batch=batch)
    assert conn.log == [("executemany", min(batch, rows - i * batch))
                        for i in range(expected)]


def test_documents_report_inserts_separately_from_rows_seen():
    """A sweep legitimately returns the same issue twice; it is written once.

    The old counter incremented once per row and called the total `written`, so a
    conflict — the normal case, and the reason `ON CONFLICT DO NOTHING` is there
    — was reported as a write.
    """
    conn = FakeConn()
    result = GitHubHarvester.write_documents(None, conn, _Run(3))
    assert result == {"inserted": 3, "seen": 3}


def test_an_empty_run_issues_nothing():
    conn = FakeConn()
    assert GitHubHarvester.write_documents(None, conn, _Run(0)) == {
        "inserted": 0, "seen": 0
    }
    assert conn.statements == 0, "a sweep with no survivors should not talk to the database"


# ── openrouter.write_model_versions ───────────────────────────────────────


def test_the_poller_batches_and_keeps_counting_inserts_apart_from_updates():
    """340 models, one round trip each, is about 44 seconds of pure latency.

    The per-row `RETURNING (xmax = 0)` has to survive the batching, or the poller
    stops being able to tell a new model from a price change — and FR-3's alert
    reads exactly that distinction.
    """
    from collect.registry.openrouter import write_model_versions

    source_calls: list[tuple[str, int]] = []

    class _ReturningCursor(_Cursor):
        """Yields one result set per row, the way `returning=True` does."""

        def executemany(self, statement, params_seq, *, returning=False):
            rows = list(params_seq)
            assert returning, "the per-row RETURNING must be requested"
            source_calls.append(("executemany", len(rows)))
            self._pending = [(True,)] * len(rows)
            self.pgresult = object()
            return None

        def fetchone(self):
            return self._pending[0] if self._pending else None

        def nextset(self):
            self._pending.pop(0)
            return True if self._pending else None

    class _ReturningConn(FakeConn):
        def cursor(self, **kwargs):
            return _ReturningCursor(self.log)

    @dataclass
    class _Model:
        canonical_id: str

        def as_row(self):
            return {"canonical_id": self.canonical_id, "sources": {}}

    @dataclass
    class _Result:
        models: list

    conn = _ReturningConn()
    counts = write_model_versions(conn, _Result([_Model(f"v/m{n}") for n in range(450)]),
                                 batch=200)
    assert [n for _, n in source_calls] == [200, 200, 50], "three round trips, not 450"
    assert counts == {"inserted": 450, "updated": 0}
