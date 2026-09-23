"""A real Reddit thread, all the way to a sentence.

This is the first test in the repository that runs the whole judgement half in
one go: extract, verify, weight, store, aggregate, phrase. Everything it
exercises was tested alone already — what has never been tested is the four
joins between them, which is where the assumptions live that nobody wrote down.

The text is real. `fixtures/threads/thread-1u1b22l.json` is a harvested Reddit
thread with a computed offset map, six documents and ten substitutions. Only
the model's reply is scripted, and it has to be: a test that depends on what
Gemini says today is not a test.

WHAT THIS DOES NOT PROVE, stated because a green database test invites the
opposite reading.

`ThreadInput` is constructed HERE, from a fixture dict, and handed to the
pipeline. The pipeline cannot tell it from a database read - which means this
test says nothing about whether the pipeline works against STORED
`thread_context` and `document` rows. Claims and cells are written to a real
database and read back; the input never came from one.

That is the seventh shape - a variable the test supplies is a variable the test
cannot check - and Engineer 1 hit the same thing verifying the blog path
against in-memory fixtures on a database with zero document rows. Recorded here
rather than only in that conversation, because this file is where somebody
would otherwise conclude the read path is covered.

It is not a gap that can be closed today: `thread_context.flattened_text_ref`
is a location in an object store and this lane has no reader for one (see
`judge/cli.py`). E1 is building a shared read-only reader. WHEN IT LANDS, THE
TEST TO ADD IS THIS ONE WITH ITS INPUT READ FROM THE DATABASE - and it is the
first thing that would prove the lane interface works rather than that the
types line up.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import psycopg
import pytest
from psycopg.types.json import Json

from judge.curate.gate import CellStatus
from judge.extract.client import FakeClient
from judge.extract.runner import ThreadInput
from judge.extract.verify import OffsetMapping
from judge.pipeline import DocumentFacts, Pipeline
from judge.store.claims import CONNECT_TIMEOUT_SECONDS

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "contract" / "tables.sql"
THREAD = ROOT / "fixtures" / "threads" / "thread-1u1b22l.json"
CAPABILITY = "summarization.fidelity"
MODEL = "mv1"


@pytest.fixture(scope="module")
def fixture() -> dict:
    return json.loads(THREAD.read_text(encoding="utf-8"))


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
def world(conn, fixture):
    """The rows `collect/` would have written for this thread."""
    conn.execute(
        "INSERT INTO model_version (id, canonical_id, provider, family, display_name, "
        "lifecycle, provenance, sources) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            MODEL,
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
    for index, document_id in enumerate(fixture["member_document_ids"]):
        conn.execute(
            "INSERT INTO document (id, source, external_id, url, fetched_at, "
            "created_at, text_ref, content_hash, status, names_version, "
            "has_conditions, has_numbers) VALUES (%s,%s,%s,%s,now(),%s,%s,%s,%s,%s,%s,%s)",
            (
                document_id,
                "reddit",
                document_id,
                f"https://reddit.test/{document_id}",
                date.today() - timedelta(days=20),
                f"raw/{document_id}",
                f"h{index}",
                "kept",
                True,
                True,
                True,
            ),
        )
        conn.execute(
            "INSERT INTO author (id, source, external_id) VALUES (%s,%s,%s)",
            (f"author_{index}", "reddit", f"u{index}"),
        )
    conn.execute(
        "INSERT INTO thread_context (id, thread_root_id, member_document_ids, "
        "flattened_text_ref, offset_map, child_count, pipeline_version, assembled_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,now())",
        (
            fixture["thread_context_id"],
            fixture["thread_root_id"],
            fixture["member_document_ids"],
            "flattened/x",
            Json(fixture["offset_map"]),
            len(fixture["member_document_ids"]) - 1,
            "e3.1",
        ),
    )
    conn.commit()
    return conn


def thread_input(fixture) -> ThreadInput:
    return ThreadInput(
        thread_context_id=fixture["thread_context_id"],
        flattened_text=fixture["flattened_text"],
        offset_map=tuple(OffsetMapping(**s) for s in fixture["offset_map"]),
        raw_text_of=fixture["raw_text_of"],
    )


def span_in(fixture, document_id: str, length: int = 40) -> tuple[int, int]:
    """A real span inside one document, long enough to quote."""
    segment = max(
        (s for s in fixture["offset_map"] if s["document_id"] == document_id),
        key=lambda s: s["flat_end"] - s["flat_start"],
    )
    start = segment["flat_start"] + 1
    return start, min(start + length, segment["flat_end"])


def scripted(fixture, document_id: str, polarity: str = "negative") -> str:
    start, end = span_in(fixture, document_id)
    return json.dumps(
        {
            "claims": [
                {
                    "source_comment_id": document_id,
                    "model_ref": {
                        "surface": "gemini",
                        "resolved_version_id": "google/gemini-2.5-flash",
                        "specificity": "family",
                        "resolution_confidence": 0.7,
                        "speaking": "own-experience",
                    },
                    "board_entries": [{"section": "capability",
                                       "slug": "summarization-fidelity",
                                       "name": "Summarization fidelity",
                                       "definition": "Condenses without dropping a detail."}],
                    "legacy_score_key": CAPABILITY,
                    "polarity": polarity,
                    "quote": fixture["flattened_text"][start:end],
                    "quote_offset": [start, end],
                    "relevance": "central",
                    "has_numbers": True,
                    "conditions": {"context_size": 20000},
                }
            ]
        }
    )


def facts_for(fixture) -> dict[str, DocumentFacts]:
    return {
        document_id: DocumentFacts(
            document_id=document_id,
            platform="reddit",
            created_at=date.today() - timedelta(days=20),
            names_version=True,
            has_conditions=True,
            has_numbers=True,
        )
        for document_id in fixture["member_document_ids"]
    }


def pipeline_for(conn, *responses: str) -> Pipeline:
    return Pipeline(
        conn,
        client=FakeClient(responses=list(responses)),
        capability_keys=[CAPABILITY],
        extractor_model="google/gemini-2.5-flash",
    )


class TestOneDocumentToOneSentence:
    def test_a_real_thread_produces_a_claim_and_a_cell(self, world, fixture):
        """The whole judgement half, on text somebody actually posted.

        Six modules, four joins, one run. Every piece was tested alone before
        this and none of the joins had ever executed.
        """
        document_id = fixture["member_document_ids"][0]
        result = pipeline_for(world, scripted(fixture, document_id)).run(
            thread_input(fixture),
            facts=facts_for(fixture),
            model_version_of={"google/gemini-2.5-flash": MODEL},
        )
        world.commit()

        assert len(result.extraction.verified) == 1
        assert len(result.stored_claim_ids) == 1
        assert len(result.cells) == 1

        row = world.execute(
            "SELECT c.quote, w.w_final, cl.status, cl.consensus_phrase "
            "FROM claim c JOIN claim_weight w ON w.claim_id = c.id "
            "CROSS JOIN cell cl"
        ).fetchone()
        quote, weight, status, phrase = row
        assert quote and 0 < weight <= 0.95
        assert status == "insufficient", "one voice cannot publish, and says so"
        assert phrase

    def test_the_condition_bucket_is_derived_from_the_claim(self, world, fixture):
        """20k tokens lands in 8k-32k, not in a default.

        The bucket is the third of the cell's three dimensions, and getting it
        from a default would silently merge two situations the whole design
        exists to keep apart.
        """
        document_id = fixture["member_document_ids"][0]
        pipeline_for(world, scripted(fixture, document_id)).run(
            thread_input(fixture),
            facts=facts_for(fixture),
            model_version_of={"google/gemini-2.5-flash": MODEL},
        )
        world.commit()

        bucket = world.execute("SELECT condition_bucket FROM claim").fetchone()[0]
        assert bucket == "context_size:8k-32k"

    def test_a_fabricated_quote_reaches_neither_table(self, world, fixture):
        """The guarantee, end to end rather than at the verification seam."""
        invented = json.dumps(
            {
                "claims": [
                    {
                        "source_comment_id": fixture["member_document_ids"][0],
                        "model_ref": {
                            "surface": "gemini",
                            "resolved_version_id": "google/gemini-2.5-flash",
                            "specificity": "family",
                            "resolution_confidence": 0.7,
                            "speaking": "own-experience",
                        },
                        "board_entries": [{"section": "capability",
                                           "slug": "summarization-fidelity",
                                           "name": "Summarization fidelity",
                                           "definition": "Condenses without dropping a detail."}],
                        "legacy_score_key": CAPABILITY,
                        "polarity": "positive",
                        "quote": "gemini summarised everything perfectly for us",
                        "quote_offset": [0, 45],
                        "relevance": "central",
                    }
                ]
            }
        )
        result = pipeline_for(world, invented).run(
            thread_input(fixture),
            facts=facts_for(fixture),
            model_version_of={"google/gemini-2.5-flash": MODEL},
        )
        world.commit()

        assert len(result.extraction.rejected) == 1
        assert result.stored_claim_ids == []
        assert world.execute("SELECT count(*) FROM claim").fetchone()[0] == 0
        assert world.execute("SELECT count(*) FROM cell").fetchone()[0] == 0


class TestWhatItRefusesToGuess:
    def test_an_unresolvable_model_is_skipped_not_invented(self, world, fixture):
        """A claim about a model we do not track attaches to nothing.

        Skipped and logged rather than written against a guess — attaching it
        to the nearest model would put a real quote on the wrong page, which
        is worse than losing it.
        """
        document_id = fixture["member_document_ids"][0]
        result = pipeline_for(world, scripted(fixture, document_id)).run(
            thread_input(fixture),
            facts=facts_for(fixture),
            model_version_of={},
        )
        world.commit()

        assert len(result.extraction.verified) == 1
        assert result.stored_claim_ids == []

    def test_a_document_with_no_facts_is_skipped_not_defaulted(self, world, fixture):
        """An invented platform silently changes f_platform.

        GitHub weights 0.95 and Reddit 0.85, so a guessed platform is a
        guessed weight on a claim that looks fully evidenced.
        """
        document_id = fixture["member_document_ids"][0]
        result = pipeline_for(world, scripted(fixture, document_id)).run(
            thread_input(fixture),
            facts={},
            model_version_of={"google/gemini-2.5-flash": MODEL},
        )
        world.commit()

        assert len(result.extraction.verified) == 1
        assert result.stored_claim_ids == []

    def test_the_extractor_boolean_never_reaches_the_weight(self, world, fixture):
        """Rule 2: a model may not participate in weighting.

        `has_numbers` is counted at ingest by `collect/`. The extractor's
        opinion is recorded as a disagreement and used for nothing.
        """
        document_id = fixture["member_document_ids"][0]
        facts = facts_for(fixture)
        for document in facts.values():
            document.has_numbers = False  # the count says no

        result = pipeline_for(world, scripted(fixture, document_id)).run(
            thread_input(fixture),  # the extractor said yes
            facts=facts,
            model_version_of={"google/gemini-2.5-flash": MODEL},
        )
        world.commit()

        assert result.extractor_disagreements, "a disagreement must be recorded"

        # f_specificity is 0.2 per signal. With names_version and
        # has_conditions true and has_numbers COUNTED false, it must sit below
        # what it would be had the extractor's `true` been used — asserting the
        # two are equal, as the first draft of this did, compares a value to
        # itself and passes whatever the code does.
        f_specificity = world.execute("SELECT f_specificity FROM claim_weight").fetchone()[0]
        assert f_specificity < 1.0
        assert world.execute("SELECT has_numbers FROM claim").fetchone()[0] is True, (
            "the extractor's proposal is still RECORDED on the claim; it is "
            "only barred from the weight"
        )


class TestAccumulation:
    def test_a_second_voice_changes_the_cell(self, world, fixture):
        """Consensus is cumulative, which is the reason any of this persists."""
        first, second = fixture["member_document_ids"][:2]
        pipeline = pipeline_for(world, scripted(fixture, first), scripted(fixture, second))
        arguments = dict(
            facts=facts_for(fixture),
            model_version_of={"google/gemini-2.5-flash": MODEL},
        )

        pipeline.run(thread_input(fixture), **arguments)
        world.commit()
        after_one = world.execute("SELECT independent_voices FROM cell").fetchone()[0]

        pipeline.run(thread_input(fixture), **arguments)
        world.commit()
        after_two = world.execute("SELECT independent_voices FROM cell").fetchone()[0]

        assert after_one == 1
        assert after_two == 1, (
            "both claims are anonymous-per-platform until author_id is wired, "
            "so they collapse to one voice — which is the safe direction"
        )
        assert world.execute("SELECT count(*) FROM claim").fetchone()[0] == 2

    def test_re_running_the_same_thread_adds_nothing(self, world, fixture):
        """Idempotency, through the whole chain rather than at the store."""
        document_id = fixture["member_document_ids"][0]
        arguments = dict(
            facts=facts_for(fixture),
            model_version_of={"google/gemini-2.5-flash": MODEL},
        )

        pipeline_for(world, scripted(fixture, document_id)).run(thread_input(fixture), **arguments)
        world.commit()
        pipeline_for(world, scripted(fixture, document_id)).run(thread_input(fixture), **arguments)
        world.commit()

        assert world.execute("SELECT count(*) FROM claim").fetchone()[0] == 1
        assert world.execute("SELECT count(*) FROM cell").fetchone()[0] == 1
        status = world.execute("SELECT status FROM cell").fetchone()[0]
        assert status == CellStatus.INSUFFICIENT.value


class TestAThreadIsKeptAsSoonAsItIsDone:
    """A run that dies mid-batch used to discard every thread that had finished.

    `run_all` committed once, after the loop, so a stop or a crash at thread 20
    of 24 rolled back all 19 — up to 13.8 minutes of measured extraction, already
    paid for at the provider, with nothing recording that it happened. The Stop
    button made this reachable deliberately rather than by accident: it exists so
    a person can halt a run they can see going wrong.

    ⚠ EVERY TEST HERE OPENS THE OUTER TRANSACTION FIRST, and the first draft did
      not. Without that these tests pass for a reason that has nothing to do with
      the fix: `conn.transaction()` is a SAVEPOINT only when a transaction is
      already open, and when one is not it opens a real transaction and COMMITS
      on exit. Measured on this database:

          no statement since the last commit -> transaction(); rollback() -> row SURVIVES
          one statement first                -> transaction(); rollback() -> row GONE

      `scripts/fetch_model.py` has executed many statements by the time E5 runs,
      so production is always the second case — which is what `pipeline.py:906`
      means by "the caller owns the outer one". A fixture that commits and then
      calls `run_all` is the first case, so it would have shown a thread
      surviving a rollback with the hook removed, and the test would have been
      green and meaningless.
    """

    def _args(self, fixture):
        return dict(
            facts=facts_for(fixture),
            model_version_of={"google/gemini-2.5-flash": MODEL},
            already_extracted={},
        )

    @staticmethod
    def _as_production_does(world):
        """Open the outer transaction, the way a real run already has."""
        world.execute("SELECT 1")

    def test_a_finished_thread_survives_the_run_dying(self, world, fixture):
        document_id = fixture["member_document_ids"][0]
        pipeline = pipeline_for(world, scripted(fixture, document_id))
        self._as_production_does(world)

        pipeline.run_all(
            [thread_input(fixture)], after_thread=world.commit, **self._args(fixture)
        )
        # The run dies here: no outer commit ever happens.
        world.rollback()

        assert world.execute("SELECT count(*) FROM claim").fetchone()[0] == 1, (
            "the thread finished, so its claims must outlive the run that was "
            "reading the next one"
        )

    def test_without_the_hook_the_same_death_loses_it(self, world, fixture):
        """The defect, pinned. This is what makes the test above mean something.

        Also today's behaviour for `cli.py` and `run_extraction_batched.py`, and
        not a complaint about them — a nightly batch nobody is watching has no
        Stop button and a different trade-off. Pinned so the difference stays a
        decision somebody made rather than an accident.
        """
        document_id = fixture["member_document_ids"][0]
        pipeline = pipeline_for(world, scripted(fixture, document_id))
        self._as_production_does(world)

        pipeline.run_all([thread_input(fixture)], **self._args(fixture))
        world.rollback()

        assert world.execute("SELECT count(*) FROM claim").fetchone()[0] == 0

    def test_the_hook_fires_after_the_claim_is_written(self, world, fixture):
        document_id = fixture["member_document_ids"][0]
        pipeline = pipeline_for(world, scripted(fixture, document_id))
        self._as_production_does(world)
        seen = []

        pipeline.run_all(
            [thread_input(fixture)],
            after_thread=lambda: seen.append(
                world.execute("SELECT count(*) FROM claim").fetchone()[0]
            ),
            **self._args(fixture),
        )

        # Once, and AFTER the write. A hook firing before it would commit an
        # empty transaction and lose the thread just as completely.
        assert seen == [1]
