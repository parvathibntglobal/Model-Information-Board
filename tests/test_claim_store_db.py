"""The first rows `judge/` has ever written, against a real Postgres.

These use `test_dsn`, so with no database they FAIL rather than skip — the
convention `collect/` paid six defects to establish. A write path covered only
by a skip is a write path nobody has run.

The interesting assertions are the two properties the module exists for:
a claim and its weight arrive together or not at all, and re-running extraction
does not manufacture a second voice.
"""

from __future__ import annotations

from datetime import date

import psycopg
import pytest
from psycopg.types.json import Json
from psycopg.types.range import Range

from judge.extract.schema import ExtractedClaim
from judge.extract.verify import VerifiedQuote
from judge.store.claims import CONNECT_TIMEOUT_SECONDS, ClaimStore, StoredClaim, claim_id_for
from judge.vet.weight import WeightFactors


@pytest.fixture
def conn(test_dsn):
    """A schema-applied database, rolled back after each test."""
    from pathlib import Path

    schema = (Path(__file__).resolve().parent.parent / "contract" / "tables.sql").read_text(
        encoding="utf-8"
    )
    # `connect_timeout` explicitly. psycopg has no default, so a dead
    # instance tries ::1, waits it out, tries 127.0.0.1, waits again -
    # 250 seconds per attempt, which reads as a hanging suite rather
    # than a failure naming the host. Engineer 1 lost ten minutes to
    # exactly this and fixed it in collect/db.py; this lane connects
    # here rather than through that, so it needed its own.
    with psycopg.connect(test_dsn, connect_timeout=CONNECT_TIMEOUT_SECONDS) as connection:
        connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
        connection.execute("CREATE SCHEMA public")
        connection.execute(schema)
        connection.commit()
        yield connection


@pytest.fixture
def seeded(conn):
    """The rows `claim` has foreign keys into. `collect/` owns these tables.

    Written directly rather than through any `collect/` helper: this lane never
    imports from that one, and a test that did would make the boundary a
    suggestion.
    """
    conn.execute(
        "INSERT INTO model_version (id, canonical_id, provider, family, display_name, "
        "lifecycle, provenance, sources) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
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
        "INSERT INTO capability (key, failure_mode, version) VALUES (%s, %s, %s)",
        ("summarization.fidelity", "silent", "1.0"),
    )
    conn.execute(
        "INSERT INTO document (id, source, external_id, url, fetched_at, text_ref, "
        "content_hash, status) VALUES (%s, %s, %s, %s, now(), %s, %s, %s)",
        ("d1", "reddit", "x1", "https://example.test/x1", "raw/x", "hash1", "kept"),
    )
    conn.execute(
        "INSERT INTO thread_context (id, thread_root_id, member_document_ids, "
        "flattened_text_ref, offset_map, child_count, pipeline_version, assembled_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, now())",
        ("tc1", "d1", ["d1"], "flattened/x", Json([]), 0, "e3.1"),
    )
    conn.commit()
    return conn


QUOTE = "dropped the clause"


def a_claim(capability="summarization.fidelity", start=0) -> ExtractedClaim:
    """The offset is DERIVED from the quote, never written beside it.

    It was written beside it, as (0, 20) against an 18-character quote, and
    `ExtractedClaim` rejected it — correctly, since an offset that does not
    delimit exactly the quoted text is the defect verification exists to catch.
    Deriving it means the two cannot disagree, which is the same reason the
    thread fixture computes its offset map rather than stating it.
    """
    return ExtractedClaim.model_validate(
        {
            "source_comment_id": "d1",
            "model_ref": {
                "surface": "flash",
                "resolved_version_id": "google/gemini-2.5-flash",
                "specificity": "family",
                "resolution_confidence": 0.8,
                # REQUIRED since 2026-08-21. These three sites were missed
                # because the local runs excluded every `_db` test, so 28
                # fixed construction sites read as all of them. CI, which
                # has a database, is what found the other three.
                "speaking": "own-experience",
            },
            "capability": capability,
            "polarity": "negative",
            "quote": QUOTE,
            "quote_offset": [start, start + len(QUOTE)],
            "relevance": "central",
            "has_numbers": True,
        }
    )


def a_stored(claim: ExtractedClaim | None = None, **overrides) -> StoredClaim:
    claim = claim or a_claim()
    start, end = claim.quote_offset
    defaults = dict(
        claim=claim,
        quote=VerifiedQuote(
            document_id="d1",
            flat_offset=(start, end),
            raw_offset=(start, end),
            display_text="dropped the clause 🙃",
        ),
        weights=WeightFactors(
            f_evidence=0.9,
            f_platform=0.85,
            f_specificity=0.7,
            f_relevance=1.0,
            f_recency=0.8,
            f_launch=1.0,
            f_fuzziness=0.3,
        ),
        document_id="d1",
        thread_context_id="tc1",
        model_version_id="mv1",
        condition_bucket="context_size:8k-32k",
        evidence_tier="B",
        claim_date=date(2026, 8, 1),
        # what actually ran, as the Completion reports it — never an env default
        extractor_model="google/gemini-2.5-flash",
    )
    defaults.update(overrides)
    return StoredClaim(**defaults)


class TestTheTwoProperties:
    def test_a_claim_and_its_weight_arrive_together(self, seeded):
        store = ClaimStore(seeded)
        claim_id = store.write(a_stored())
        seeded.commit()

        assert store.count_for_thread("tc1") == 1
        weights = store.weights_for(claim_id)
        assert weights is not None
        assert weights["w_final"] == pytest.approx(
            0.9 * 0.85 * 0.7 * 1.0 * 0.8 * 1.0 * 0.3, rel=1e-5
        )

    def test_neither_survives_a_failure_of_the_other(self, seeded):
        """One transaction, so a half-written claim cannot exist.

        A claim with no weight contributes to no count and would present weeks
        later as a cell that will not publish, rather than as a write that
        failed.
        """
        store = ClaimStore(seeded)
        with pytest.raises(psycopg.errors.Error), seeded.transaction():
            store.write(a_stored())
            # a capability that violates the foreign key, after the claim insert
            store.write(a_stored(claim=a_claim(capability="not.a.capability")))

        seeded.rollback()
        assert store.count_for_thread("tc1") == 0

    def test_re_running_extraction_does_not_add_a_second_voice(self, seeded):
        """The worst failure this table could have.

        `n_eff` counts weight, so a duplicated claim is a voice that never
        existed — and a publication gate crossed by re-running a batch would be
        indistinguishable from one crossed by evidence.
        """
        store = ClaimStore(seeded)
        first = store.write(a_stored())
        second = store.write(a_stored())
        seeded.commit()

        assert first == second
        assert store.count_for_thread("tc1") == 1

    def test_two_capabilities_from_one_comment_are_two_claims(self, seeded):
        """Idempotency must not collapse genuinely different claims."""
        seeded.execute(
            "INSERT INTO capability (key, failure_mode, version) VALUES (%s, %s, %s)",
            ("ops.latency_ttft", "loud", "1.0"),
        )
        store = ClaimStore(seeded)
        store.write(a_stored())
        store.write(a_stored(claim=a_claim(capability="ops.latency_ttft")))
        seeded.commit()

        assert store.count_for_thread("tc1") == 2

    def test_a_different_pipeline_version_is_a_different_claim(self, seeded):
        """A re-extraction under a changed prompt is a new claim about old text.

        Collapsing the two would silently discard whichever ran second, which
        is the opposite of what `pipeline_version` exists for.
        """
        store = ClaimStore(seeded)
        store.write(a_stored())
        store.write(a_stored(pipeline_version="e5.2"))
        seeded.commit()

        assert store.count_for_thread("tc1") == 2


class TestWhatTheSchemaEnforces:
    def test_the_database_refuses_an_unverified_claim(self, seeded):
        """Rule 1 is a CHECK, not a convention this module is trusted with.

        `claim_verified_ck` means a future writer that forgets cannot quietly
        succeed — a guarantee held only by the code that happens to write today
        lasts until somebody adds a second writer.
        """
        with pytest.raises(psycopg.errors.CheckViolation), seeded.transaction():
            seeded.execute(
                "INSERT INTO claim (id, document_id, thread_context_id, "
                "source_comment_id, model_version_id, specificity, capability_key, "
                "taxonomy_version, condition_bucket, polarity, quote, "
                "quote_flat_offset, quote_raw_offset, quote_verified, relevance, "
                "evidence_tier, extractor_model, pipeline_version) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,%s,%s,%s,%s)",
                # quote_raw_offset is NOT NULL and both offsets are int4range.
                # Omitting one and passing the other as a list made this raise
                # NotNullViolation and DatatypeMismatch rather than the
                # CheckViolation it claims to assert - so it would have failed
                # loudly while never testing the CHECK at all.
                (
                    "clm_x",
                    "d1",
                    "tc1",
                    "d1",
                    "mv1",
                    "family",
                    "summarization.fidelity",
                    "1.0",
                    "context_size:8k-32k",
                    "negative",
                    "q",
                    Range(0, 1, "[)"),
                    Range(0, 1, "[)"),
                    "central",
                    "B",
                    "google/gemini-2.5-flash",
                    "e5.1",
                ),
            )

    def test_the_raw_span_is_stored_not_the_flattened_one(self, seeded):
        """`[upside_down_face]` is internal and must never reach a page."""
        store = ClaimStore(seeded)
        claim_id = store.write(a_stored())
        seeded.commit()

        row = seeded.execute("SELECT quote FROM claim WHERE id = %s", (claim_id,)).fetchone()
        assert row is not None
        assert "upside_down_face" not in row[0]
        assert "🙃" in row[0]


class TestTheId:
    def test_it_is_derived_from_the_claim_not_the_clock(self):
        args = dict(
            thread_context_id="tc1",
            source_comment_id="d1",
            capability_key="summarization.fidelity",
            quote_flat_offset=(0, 18),
            pipeline_version="e5.1",
        )
        assert claim_id_for(**args) == claim_id_for(**args)

    def test_the_span_is_part_of_it(self):
        """One comment can carry two claims about the same capability."""
        base = dict(
            thread_context_id="tc1",
            source_comment_id="d1",
            capability_key="summarization.fidelity",
            pipeline_version="e5.1",
        )
        assert claim_id_for(**base, quote_flat_offset=(0, 18)) != claim_id_for(
            **base, quote_flat_offset=(40, 58)
        )
