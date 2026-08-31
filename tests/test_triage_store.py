"""`collect/triage/store.py` — the writer the specificity columns did not have.

WHAT THESE TESTS ARE FOR, AND IT IS NOT THE SCORING. The detectors are already
covered by `tests/test_specificity.py`. What had no coverage — and what failed
for weeks in production while 878 tests stayed green — is that ANYTHING CALLS
THEM AND STORES THE ANSWER. Seven rows of 3,061 carried values, and all seven
came from a one-off export script.

So these test the world's assumption rather than the code's, per the convention
in `tests/conftest.py`: a test that asserts the scorer exists passes whether or
not a writer does, which is #21 exactly.
"""

from __future__ import annotations

import pytest

from collect.ops.chain import default_stages
from collect.triage.store import ScoreRun, score_unscored


class FakeStore:
    """A raw store with a fixed set of readable refs. Everything else raises.

    Raising rather than returning "" is the point of the unreadable test: an
    empty string scores every component False, which is the exact conversion of
    an absent value into a definite one that rule 6 forbids.
    """

    def __init__(self, texts: dict[str, str]) -> None:
        self.texts = texts

    def get_text(self, ref: str) -> str:
        if ref not in self.texts:
            raise FileNotFoundError(ref)
        return self.texts[ref]


class FakeConn:
    """Answers the two SELECTs `score_unscored` issues and records UPDATEs.

    DELIBERATELY HAS NO `transaction()`. The first version of this writer used
    `with conn.transaction():` and stored nothing: `collect.db.connect` leaves
    autocommit off, the SELECT has already opened a transaction, and a nested
    `transaction()` is a SAVEPOINT whose release commits nothing. It reported
    rows written and the table was untouched. A fake that offers both methods
    would let that come back silently, so this one offers only `commit`.
    """

    def __init__(self, pending, models=(("anthropic/claude-opus-5", "Claude Opus 5"),)):
        self.pending = pending
        self.models = list(models)
        self.updates: list[dict] = []
        self.commits = 0

    def execute(self, sql, params=None):
        text = " ".join(sql.split())
        if text.startswith("SELECT canonical_id"):
            return _Result(self.models)
        if text.startswith("SELECT id, source, text_ref"):
            return _Result(list(self.pending))
        if text.startswith("UPDATE document"):
            self.updates.append(params)
            return _Result([])
        raise AssertionError(f"unexpected statement: {text[:60]}")

    def commit(self):
        self.commits += 1


class _Result:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


NUMBERS = "we measured p95 at 420ms on claude opus 5 with 12 tools"
NOTHING = "this is great, really loving it so far, best thing ever honestly"


def test_a_readable_document_is_scored_and_written():
    """The claim, not the mention: a row goes in, an UPDATE comes out."""
    conn = FakeConn([("d1", "reddit", "raw/a")])
    run = score_unscored(conn, FakeStore({"raw/a": NUMBERS}))

    assert run.scored == 1
    assert run.written == 1
    assert len(conn.updates) == 1
    written = conn.updates[0]
    assert written["id"] == "d1"
    assert written["has_numbers"] is True
    assert written["has_conditions"] is True
    assert written["specificity_score"] is not None


def test_an_unreadable_payload_is_left_null_and_named_never_written_false():
    """RULE 6, AND IT IS THE WHOLE REASON THIS MODULE HAS A `unreadable` FIELD.

    1,106 of 3,061 documents on staging have no payload on the machine running
    the backfill. Writing False for those would say "this document contains no
    numbers" about text nobody read — and `judge/`'s numbers rung reads False as
    a veto, so the invented value would silently hold claims at tier D. An
    absence we caused, indistinguishable in the row from one we found.
    """
    conn = FakeConn([("d1", "reddit", "raw/gone")])
    run = score_unscored(conn, FakeStore({}))

    assert run.scored == 0
    assert run.unreadable == 1
    assert run.unreadable_by_source == {"reddit": 1}
    assert conn.updates == [], "an unreadable document must not be written at all"


def test_the_unreadable_are_not_in_the_rate_denominator():
    """A rate over rows nobody scored is a statement about the raw store."""
    conn = FakeConn([
        ("d1", "reddit", "raw/a"),
        ("d2", "reddit", "raw/gone"),
        ("d3", "reddit", "raw/b"),
    ])
    run = score_unscored(conn, FakeStore({"raw/a": NUMBERS, "raw/b": NOTHING}))

    assert run.eligible == 3
    assert run.scored == 2
    assert run.unreadable == 1
    assert run.true_counts["has_numbers"] == 1
    assert "scored 2/3 eligible" in run.describe()
    assert "50.0%" in run.describe(), "the denominator is scored, not eligible"


def test_dry_run_computes_and_writes_nothing():
    conn = FakeConn([("d1", "reddit", "raw/a")])
    run = score_unscored(conn, FakeStore({"raw/a": NUMBERS}), dry_run=True)

    assert run.scored == 1
    assert run.written == 0
    assert conn.updates == []


def test_batching_does_not_lose_the_tail():
    """A remainder smaller than one batch is the row that goes missing."""
    pending = [(f"d{i}", "reddit", f"raw/{i}") for i in range(7)]
    texts = {f"raw/{i}": NUMBERS for i in range(7)}
    conn = FakeConn(pending)
    run = score_unscored(conn, FakeStore(texts), batch=3)

    assert run.written == 7
    assert [u["id"] for u in conn.updates] == [f"d{i}" for i in range(7)]
    assert conn.commits == 3, "three batches of 3, 3 and a tail of 1"


def test_every_batch_is_committed_and_not_merely_savepointed():
    """THE DEFECT THIS WRITER SHIPPED WITH, ASSERTED AS A CLAIM.

    `run.written` counting to 7 proves the loop ran, not that anything landed.
    The first version incremented that same counter while `conn.transaction()`
    released a savepoint inside the SELECT's open transaction, committing
    nothing — so the only assertion that separates a working writer from that
    one is a count of COMMITS.
    """
    conn = FakeConn([("d1", "reddit", "raw/a")])
    score_unscored(conn, FakeStore({"raw/a": NUMBERS}))
    assert conn.commits >= 1


def test_a_dry_run_commits_nothing():
    conn = FakeConn([("d1", "reddit", "raw/a")])
    score_unscored(conn, FakeStore({"raw/a": NUMBERS}), dry_run=True)
    assert conn.commits == 0


def test_the_nightly_chain_actually_calls_it():
    """THE ONE THAT WOULD HAVE CAUGHT THE ORIGINAL DEFECT.

    Every other test here passes against a module nothing invokes — which is
    the state the scorer was in for weeks. This asserts the wiring: a stage
    named `score-documents` exists in the real chain AND has an implementation.
    A `run=None` stage refuses with a nicely-worded starvation notice and writes
    no columns, and from the outside that looks like a chain with a scorer in it.
    """
    stages = {s.name: s for s in default_stages()}
    assert "score-documents" in stages, "no stage writes the specificity columns"
    assert stages["score-documents"].run is not None, "declared but not built"


def test_the_stage_refuses_without_a_connection_rather_than_reporting_zero():
    """Zero scored is a measurement. No connection is not one."""
    from collect.ops.chain import REFUSED, _score_documents_stage

    result = _score_documents_stage({})
    assert result.outcome == REFUSED
    assert result.counts == {}
    assert result.starves, "a refusal must say what it costs"


def test_describe_refuses_to_divide_by_a_population_it_did_not_measure():
    run = ScoreRun(eligible=5, scored=0, unreadable=5)
    described = run.describe()
    assert "nothing was measured" in described
    assert "%" not in described


@pytest.mark.parametrize("text,expected", [(NUMBERS, True), (NOTHING, False)])
def test_the_stored_value_is_the_detector_s_answer_not_a_default(text, expected):
    """Guards the direction the None-slip already broke once downstream."""
    conn = FakeConn([("d1", "reddit", "raw/a")])
    score_unscored(conn, FakeStore({"raw/a": text}))
    assert conn.updates[0]["has_numbers"] is expected
