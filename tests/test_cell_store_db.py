"""Claims become cells, against a real Postgres.

The assertions worth reading are the ones about what the gate refuses, because
a cell that will not publish is the output this stage produces most often and
the one a page has to render honestly.

Like `test_claim_store_db.py`, these FAIL rather than skip with no database.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import psycopg
import pytest
from psycopg.types.json import Json
from psycopg.types.range import Range

from judge.curate.gate import CellStatus
from judge.store.cells import CellKey, CellStore
from judge.store.claims import CONNECT_TIMEOUT_SECONDS

SCHEMA = Path(__file__).resolve().parent.parent / "contract" / "tables.sql"
CAPABILITY = "summarization.fidelity"
BUCKET = "context_size:8k-32k"


@pytest.fixture
def conn(test_dsn):
    # `connect_timeout` explicitly. psycopg has no default, so a dead
    # instance tries ::1, waits it out, tries 127.0.0.1, waits again -
    # 250 seconds per attempt, which reads as a hanging suite rather
    # than a failure naming the host. Engineer 1 lost ten minutes to
    # exactly this and fixed it in collect/db.py; this lane connects
    # here rather than through that, so it needed its own.
    with psycopg.connect(test_dsn, connect_timeout=CONNECT_TIMEOUT_SECONDS) as connection:
        connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
        connection.execute("CREATE SCHEMA public")
        connection.execute(SCHEMA.read_text(encoding="utf-8"))
        connection.commit()
        yield connection


@pytest.fixture
def world(conn):
    """A model, a capability, and a thread. `collect/` owns these tables."""
    conn.execute(
        "INSERT INTO model_version (id, canonical_id, provider, family, display_name, "
        "lifecycle, provenance, sources) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            "mv1",
            "google/gemini-2.5-flash",
            "google",
            "gemini",
            "Gemini 2.5 Flash",
            "ga",
            "seed",
            Json({}),
        ),
    )
    conn.execute(
        "INSERT INTO capability (key, failure_mode, version) VALUES (%s,%s,%s)",
        (CAPABILITY, "silent", "1.0"),
    )
    conn.execute(
        "INSERT INTO thread_context (id, thread_root_id, member_document_ids, "
        "flattened_text_ref, offset_map, child_count, pipeline_version, assembled_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,now())",
        ("tc1", "d0", ["d0"], "flattened/x", Json([]), 0, "e3.1"),
    )
    conn.commit()
    return conn


def add_claim(
    conn,
    *,
    claim_id: str,
    author: str | None,
    platform: str = "reddit",
    polarity: str = "positive",
    weight: float = 0.9,
    days_ago: int = 10,
    bucket: str = BUCKET,
) -> None:
    """One claim, its author, its document and its weight."""
    document_id = f"doc_{claim_id}"
    conn.execute(
        "INSERT INTO document (id, source, external_id, url, fetched_at, text_ref, "
        "content_hash, status) VALUES (%s,%s,%s,%s,now(),%s,%s,%s)",
        (
            document_id,
            platform,
            claim_id,
            f"https://example.test/{claim_id}",
            f"raw/{claim_id}",
            f"h_{claim_id}",
            "kept",
        ),
    )
    if author is not None:
        conn.execute(
            "INSERT INTO author (id, source, external_id) VALUES (%s,%s,%s) "
            "ON CONFLICT (id) DO NOTHING",
            (author, platform, author),
        )
    conn.execute(
        "INSERT INTO claim (id, document_id, thread_context_id, source_comment_id, "
        "author_id, model_version_id, specificity, capability_key, taxonomy_version, "
        "condition_bucket, polarity, quote, quote_flat_offset, quote_raw_offset, "
        "quote_verified, relevance, evidence_tier, extractor_model, pipeline_version, "
        "created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true,%s,%s,%s,%s,%s)",
        (
            claim_id,
            document_id,
            "tc1",
            document_id,
            author,
            "mv1",
            "family",
            CAPABILITY,
            "1.0",
            bucket,
            polarity,
            "it held up",
            Range(0, 10, "[)"),
            Range(0, 10, "[)"),
            "central",
            "B",
            "google/gemini-2.5-flash",
            "e5.1",
            date.today() - timedelta(days=days_ago),
        ),
    )
    conn.execute(
        "INSERT INTO claim_weight (claim_id, w_final, f_evidence, f_platform, "
        "f_specificity, f_relevance, f_recency, f_launch, f_fuzziness, pipeline_version) "
        "VALUES (%s,%s,1,1,1,1,1,1,1,%s)",
        (claim_id, weight, "e5.1"),
    )


KEY = CellKey("mv1", CAPABILITY, BUCKET)


class TestWhatTheGateRefuses:
    def test_a_cell_is_written_even_when_it_cannot_publish(self, world):
        """`insufficient` is a finding, and a missing row renders as neither.

        Two voices on one platform is the commonest thing this stage produces.
        If the gate decided whether to WRITE rather than what to SAY, silence
        would be indistinguishable from absence on every page.
        """
        add_claim(world, claim_id="c1", author="a1")
        add_claim(world, claim_id="c2", author="a2")
        world.commit()

        outcome = CellStore(world).compute(KEY)
        CellStore(world).write(outcome)
        world.commit()

        assert outcome.status is CellStatus.INSUFFICIENT
        row = world.execute(
            "SELECT status, independent_voices, platform_count FROM cell"
        ).fetchone()
        assert row == ("insufficient", 2, 1)

    def test_one_platform_does_not_publish_however_many_voices(self, world):
        """Five people on one platform is one selection effect, not five."""
        for i in range(5):
            add_claim(world, claim_id=f"c{i}", author=f"a{i}")
        world.commit()

        outcome = CellStore(world).compute(KEY)
        assert outcome.status is CellStatus.INSUFFICIENT
        assert outcome.counts.platform_count == 1

    def test_two_platforms_and_enough_weight_publishes(self, world):
        for i in range(3):
            add_claim(world, claim_id=f"r{i}", author=f"a{i}", platform="reddit")
        for i in range(3):
            add_claim(world, claim_id=f"g{i}", author=f"b{i}", platform="github")
        world.commit()

        outcome = CellStore(world).compute(KEY)
        assert outcome.status is CellStatus.PUBLISHED, outcome.gate.failures
        assert outcome.counts.platform_count == 2
        assert outcome.consensus.phrase


class TestVoicesArePeople:
    def test_one_author_writing_repeatedly_is_one_voice(self, world):
        """`n_eff` counts people. Six claims from one person is one opinion."""
        for i in range(6):
            add_claim(world, claim_id=f"c{i}", author="a1", platform="reddit")
        for i in range(6):
            add_claim(world, claim_id=f"g{i}", author="a1", platform="github")
        world.commit()

        outcome = CellStore(world).compute(KEY)
        assert outcome.counts.independent_voices == 1
        assert outcome.status is CellStatus.INSUFFICIENT

    def test_anonymous_claims_collapse_to_one_voice_per_platform(self, world):
        """An unknown author is not a known distinct author.

        Counting each anonymous claim as its own voice would manufacture
        exactly the independence the author cap exists to prevent — and it
        would do it silently, since nothing on the page distinguishes five
        strangers from five nulls.
        """
        for i in range(5):
            add_claim(world, claim_id=f"c{i}", author=None, platform="reddit")
        world.commit()

        outcome = CellStore(world).compute(KEY)
        assert outcome.counts.independent_voices == 1

    def test_an_unweighted_claim_is_excluded_not_counted_as_zero(self, world):
        """A claim with no weight is not a zero-weight claim.

        Defaulting it would quietly move `n_eff`, which is the one number the
        gate turns on — rule 6 in the most expensive place it could appear.
        """
        add_claim(world, claim_id="c1", author="a1")
        world.execute("DELETE FROM claim_weight WHERE claim_id = 'c1'")
        world.commit()

        assert CellStore(world).weighted_claims_for(KEY) == []
        assert CellStore(world).compute(KEY).counts.n_eff == 0


class TestRebuild:
    def test_recomputing_is_idempotent(self, world):
        add_claim(world, claim_id="c1", author="a1")
        world.commit()
        store = CellStore(world)

        store.rebuild_all()
        store.rebuild_all()
        world.commit()

        assert world.execute("SELECT count(*) FROM cell").fetchone()[0] == 1

    def test_a_new_claim_changes_the_cell_on_rebuild(self, world):
        add_claim(world, claim_id="c1", author="a1", platform="reddit")
        world.commit()
        store = CellStore(world)
        store.rebuild_all()
        world.commit()

        add_claim(world, claim_id="c2", author="a2", platform="github")
        world.commit()
        store.rebuild_all()
        world.commit()

        row = world.execute("SELECT independent_voices, platform_count FROM cell").fetchone()
        assert row == (2, 2)

    def test_buckets_are_separate_cells(self, world):
        """The distinction a score would destroy.

        "Fine under 5 tools, breaks above 10" only survives because these are
        two rows rather than one average.
        """
        add_claim(world, claim_id="c1", author="a1", bucket="context_size:8k-32k")
        add_claim(world, claim_id="c2", author="a2", bucket="context_size:128k+")
        world.commit()

        outcomes = CellStore(world).rebuild_all()
        assert len({o.key.condition_bucket for o in outcomes}) == 2
        assert world.execute("SELECT count(*) FROM cell").fetchone()[0] == 2


class TestWhatIsWritten:
    def test_provenance_is_harvested_never_hand_curated(self, world):
        """`hand_curated` exists so invented cells can be deleted by column.

        This writer must never produce one — a cell it wrote is by definition
        derived from claims, and claims carry verified quotes.
        """
        add_claim(world, claim_id="c1", author="a1")
        world.commit()
        CellStore(world).rebuild_all()
        world.commit()

        assert world.execute("SELECT provenance FROM cell").fetchone()[0] == "harvested"

    def test_the_quote_ids_that_earned_the_cell_are_stored(self, world):
        """FR-26: click the phrase, see the words. A property of the data."""
        add_claim(world, claim_id="c1", author="a1")
        add_claim(world, claim_id="c2", author="a2")
        world.commit()
        CellStore(world).rebuild_all()
        world.commit()

        quote_ids = world.execute("SELECT quote_ids FROM cell").fetchone()[0]
        assert set(quote_ids) == {"c1", "c2"}

    def test_no_synthesised_score_is_stored(self, world):
        """Rule 3. Every figure on a cell is counted or measured.

        `n_eff` is a sum of weights and `max_author_share` a ratio of counts —
        neither is a rating, and there is no column that could become one.
        """
        columns = {
            row[0]
            for row in world.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'cell'"
            ).fetchall()
        }
        assert not {"score", "rating", "confidence", "grade"} & columns
