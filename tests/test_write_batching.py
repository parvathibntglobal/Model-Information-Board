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
    # SUBSET, NOT WHOLE-DICT EQUALITY. This test is about `inserted` and `seen`
    # being different numbers; it broke when `author_id` landed and four author
    # counts joined the return value, which is a change it has no opinion on.
    assert result["inserted"] == 3
    assert result["seen"] == 3


def test_documents_report_what_could_not_be_attributed():
    """A hit with no `user.id` gets no author row, and is counted saying so.

    These doubles carry no `author_external_id`, so all three are
    unattributable — which must be reported rather than read as three authored
    documents. A count of 0 authors and a count of 3 unattributable are the two
    halves of the same fact and only one of them is visible without this.
    """
    conn = FakeConn()
    result = GitHubHarvester.write_documents(None, conn, _Run(3))
    assert result["authors_inserted"] == 0
    assert result["distinct_authors"] == 0
    assert result["documents_without_author"] == 3
    assert result["unattributable"] == 3


def test_an_empty_run_issues_nothing():
    conn = FakeConn()
    result = GitHubHarvester.write_documents(None, conn, _Run(0))
    assert result["inserted"] == 0
    assert result["seen"] == 0
    assert result["unattributable"] == 0
    assert conn.statements == 0, "a sweep with no survivors should not talk to the database"


# ── openrouter.write_model_versions ───────────────────────────────────────


class _ReturningCursor(_Cursor):
    """Yields one result set per row, the way `returning=True` does."""

    def execute(self, statement, params=None):
        self._log.append(("execute", 1))
        self._rows = []
        return self

    def executemany(self, statement, params_seq, *, returning=False):
        rows = list(params_seq)
        self._log.append(("executemany", len(rows)))
        # `id` first, then the insert verdict, matching the real RETURNING.
        self._pending = [(row.get("id") or row.get("model_version_id"), True)
                         for row in rows]
        self.pgresult = object() if returning else None
        return None

    def fetchall(self):
        return []

    def fetchone(self):
        return self._pending[0] if getattr(self, "_pending", None) else None

    def nextset(self):
        if getattr(self, "_pending", None):
            self._pending.pop(0)
        return True if getattr(self, "_pending", None) else None


class _ReturningConn(FakeConn):
    def cursor(self, **kwargs):
        return _ReturningCursor(self.log)

    def execute(self, statement, params=None):
        cur = _ReturningCursor(self.log)
        return cur.execute(statement, params)


@dataclass
class _Model:
    canonical_id: str
    price_in: float | None = None

    def as_row(self):
        return {
            "canonical_id": self.canonical_id,
            "sources": {},
            "price_in": self.price_in,
            "price_out": None,
            "price_cached_read": None,
            "release_date": None,
        }


@dataclass
class _Result:
    models: list


def test_the_poller_batches_and_keeps_counting_inserts_apart_from_updates():
    """340 models, one round trip each, is about 44 seconds of pure latency.

    The per-row `RETURNING` has to survive the batching, or the poller stops
    being able to tell a new model from a price change — and FR-3's alert reads
    exactly that distinction. It now returns `id, (xmax = 0)`: the verdict
    travels with the row it belongs to rather than by position, because an event
    attributed by an off-by-one reads as a real price change on a real model.

    `record_changes=False` keeps this a test of the upsert. The producer's own
    round trips are counted below.
    """
    from collect.registry.openrouter import write_model_versions

    conn = _ReturningConn()
    counts = write_model_versions(
        conn,
        _Result([_Model(f"v/m{n}") for n in range(450)]),
        batch=200,
        record_changes=False,
    )
    assert [n for _, n in conn.log] == [200, 200, 50], "three round trips, not 450"
    assert counts == {"inserted": 450, "updated": 0}


def test_the_change_producer_is_batched_too():
    """It reads every prior observation in ONE query and writes in batches.

    `pricing_history` is the table #45's audit named as the next one to bite:
    two round trips per model, harmless at the seed path's eleven and 88 seconds
    of latency at the polled path's 340. A producer built per-model would have
    reintroduced the defect the audit was written about.
    """
    from collect.registry.openrouter import write_model_versions

    conn = _ReturningConn()
    write_model_versions(
        conn, _Result([_Model(f"v/m{n}", price_in=1.0) for n in range(450)]), batch=200
    )

    kinds = [kind for kind, _ in conn.log]
    assert kinds.count("execute") == 1, "one query for every prior observation"
    # 3 upsert batches + 3 history batches + 3 event batches.
    assert kinds.count("executemany") == 9
    assert [n for k, n in conn.log if k == "executemany"] == [200, 200, 50] * 3
