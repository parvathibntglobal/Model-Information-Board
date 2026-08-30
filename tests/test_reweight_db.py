"""Re-pricing stored claims under a new pipeline version, against a real Postgres.

Uses `test_dsn`, so with no database these FAIL rather than skip — the
convention `collect/` paid six defects to establish.

WHAT THESE ARE FOR. `judge/reweight.py` is the only path in the repository that
changes what a stored claim weighs, and it is the path a `contract/harvest.yaml`
ruling reaches the board through. Two properties carry everything else:

    the fork is real       the e5.1 rows are still there, byte for byte, and
                           the new rows are new. That is what makes the diff a
                           query instead of a snapshot somebody remembered.
    the fork is separated  `n_eff` counts ONE version. An unfiltered aggregate
                           would hand every voice the better of its two tiers.

Both are tested against the table rather than against the report, because the
report is computed by the same module and would agree with itself.
"""

from __future__ import annotations

from datetime import date, timedelta

import psycopg
import pytest
from psycopg.types.json import Json
from psycopg.types.range import Range

from judge import reweight
from judge.store.claims import CONNECT_TIMEOUT_SECONDS, PIPELINE_VERSION, claim_id_for

OLD = "e5.0-test"
CAPABILITY = "summarization.fidelity"
BUCKET = "context_size:8k-32k"


@pytest.fixture
def conn(test_dsn):
    from pathlib import Path

    schema = (
        Path(__file__).resolve().parent.parent / "contract" / "tables.sql"
    ).read_text(encoding="utf-8")
    with psycopg.connect(test_dsn, connect_timeout=CONNECT_TIMEOUT_SECONDS) as connection:
        connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
        connection.execute("CREATE SCHEMA public")
        connection.execute(schema)
        connection.commit()
        yield connection


@pytest.fixture
def seeded(conn):
    conn.execute(
        "INSERT INTO model_version (id, canonical_id, provider, family, display_name, "
        "lifecycle, provenance, sources) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        ("mv1", "anthropic/claude-fable-5", "anthropic", "claude", "Fable 5",
         "ga", "seed", Json({})),
    )
    conn.execute(
        "INSERT INTO capability (key, failure_mode, version) VALUES (%s,%s,%s)",
        (CAPABILITY, "silent", "1.0"),
    )
    conn.commit()
    return conn


def _document(conn, doc_id, *, platform="reddit", url=None, author=None,
              has_numbers=True, has_conditions=False, days_ago=10):
    if author is not None:
        conn.execute(
            "INSERT INTO author (id, source, external_id) VALUES (%s,%s,%s) "
            "ON CONFLICT (id) DO NOTHING",
            (author, platform, author),
        )
    conn.execute(
        "INSERT INTO document (id, source, external_id, url, created_at, fetched_at, "
        "text_ref, content_hash, status, author_id, has_numbers, has_conditions) "
        "VALUES (%s,%s,%s,%s,%s,now(),%s,%s,'kept',%s,%s,%s)",
        (doc_id, platform, doc_id, url or f"https://example.test/{doc_id}",
         date.today() - timedelta(days=days_ago), f"raw/{doc_id}", f"h_{doc_id}",
         author, has_numbers, has_conditions),
    )


def _e51_factors(*, platform, repro, days_ago=10, tier="D"):
    """The weight `judge/pipeline.py` WOULD have written for this claim.

    Computed rather than typed, and that is the point of the fixture. The
    drift check in `plan()` asserts that no factor except `f_evidence` moves,
    so a hand-written `f_platform=0.85` on a blog claim would trip it — and the
    failure would be the fixture disagreeing with the pipeline, which is a real
    finding about the fixture and noise about the code. Building the before-row
    the way the before-code built it means the drift check tests the ruling.

    `has_conditions=None` and `has_numbers=None` reproduce
    `judge/cli.py:_document_facts`, which passes literal `None` for both.
    """
    from judge.vet.weight import compute

    return compute(
        evidence_tier=tier,
        platform=platform,
        capability_key=CAPABILITY,
        relevance="central",
        specificity="version",
        claim_date=date.today() - timedelta(days=days_ago),
        release_date=None,
        as_of=date.today(),
        version_named=True,
        has_conditions=None,
        has_numbers=None,
        has_repro_steps=repro,
    )


def _claim(conn, claim_id, doc_id, *, speaking, repro, numbers, tier="D",
           author=None, version=OLD, thread="tc1", platform="reddit"):
    conn.execute(
        "INSERT INTO thread_context (id, thread_root_id, member_document_ids, "
        "flattened_text_ref, offset_map, child_count, pipeline_version, assembled_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,now()) ON CONFLICT (id) DO NOTHING",
        (thread, doc_id, [doc_id], "flattened/x", Json([]), 0, "e3.1"),
    )
    conn.execute(
        "INSERT INTO claim (id, document_id, thread_context_id, source_comment_id, "
        "author_id, model_version_id, specificity, capability_key, taxonomy_version, "
        "condition_bucket, polarity, quote, quote_flat_offset, quote_raw_offset, "
        "quote_verified, relevance, has_repro_steps, has_numbers, evidence_tier, "
        "speaking, extractor_model, pipeline_version, created_at) "
        "VALUES (%s,%s,%s,%s,%s,'mv1','version',%s,'1.0',%s,'positive','it held up',"
        "%s,%s,true,'central',%s,%s,%s,%s,'google/gemini-2.5-flash',%s,now())",
        (claim_id, doc_id, thread, doc_id, author, CAPABILITY, BUCKET,
         Range(0, 10, "[)"), Range(0, 10, "[)"), repro, numbers, tier, speaking,
         version),
    )
    f = _e51_factors(platform=platform, repro=repro, tier=tier)
    conn.execute(
        "INSERT INTO claim_weight (claim_id, w_final, f_evidence, f_platform, "
        "f_specificity, f_relevance, f_recency, f_launch, f_fuzziness, "
        "pipeline_version) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (claim_id, f.w_final, f.f_evidence, f.f_platform, f.f_specificity,
         f.f_relevance, f.f_recency, f.f_launch, f.f_fuzziness, version),
    )


class TestTheForkIsRealAndSeparated:
    def test_the_old_rows_are_untouched_and_the_new_ones_are_new(self, seeded):
        """"Old rows stay diffable" is the reason a bump is the right instrument."""
        _document(seeded, "d1", author="a1")
        _claim(seeded, "c1", "d1", speaking="own-experience", repro=True, numbers=True)
        seeded.commit()

        report = reweight.plan(seeded, from_version=OLD, to_version=PIPELINE_VERSION)
        reweight.apply(seeded, report)
        seeded.commit()

        rows = dict(
            seeded.execute(
                "SELECT pipeline_version, evidence_tier FROM claim ORDER BY 1"
            ).fetchall()
        )
        assert rows == {OLD: "D", PIPELINE_VERSION: "B"}, (
            "both versions coexist and only the new one carries the new tier"
        )

    def test_the_new_id_is_the_contract_s_and_not_this_module_s(self, seeded):
        _document(seeded, "d1", author="a1")
        _claim(seeded, "c1", "d1", speaking="own-experience", repro=True, numbers=True)
        seeded.commit()

        report = reweight.plan(seeded, from_version=OLD, to_version=PIPELINE_VERSION)
        assert report.deltas[0].claim_id_after == claim_id_for(
            thread_context_id="tc1",
            source_comment_id="d1",
            capability_key=CAPABILITY,
            quote_flat_offset=(0, 10),
            pipeline_version=PIPELINE_VERSION,
        )

    def test_n_eff_counts_one_version_not_a_voice_s_best_across_two(self, seeded):
        """The defect the fork would otherwise introduce, asserted directly.

        `count()` keeps one representative per voice AT ITS HIGHEST WEIGHT. With
        both versions in the table and no filter, a single voice contributes its
        promoted weight to a cell that is supposed to be the OLD one — so the
        before-side of every diff would drift upward, worst on exactly the claims
        the re-tier moved.
        """
        from judge.store.cells import CellKey, CellStore

        _document(seeded, "d1", author="a1")
        _claim(seeded, "c1", "d1", speaking="own-experience", repro=True,
               numbers=True)
        seeded.commit()

        report = reweight.plan(seeded, from_version=OLD, to_version=PIPELINE_VERSION)
        reweight.apply(seeded, report)
        seeded.commit()

        key = CellKey("mv1", CAPABILITY, BUCKET)
        before = CellStore(seeded, pipeline_version=OLD).compute(key)
        after = CellStore(seeded, pipeline_version=PIPELINE_VERSION).compute(key)

        stored = seeded.execute(
            "SELECT w_final FROM claim_weight WHERE claim_id = 'c1'"
        ).fetchone()[0]
        assert before.counts.n_eff == pytest.approx(stored, rel=1e-5), (
            "the old cell still reads exactly what it read before the re-weight"
        )
        assert after.counts.n_eff > before.counts.n_eff
        assert before.counts.independent_voices == after.counts.independent_voices == 1

    def test_it_refuses_to_reweight_into_the_version_it_is_measuring(self, seeded):
        with pytest.raises(ValueError, match="bump PIPELINE_VERSION"):
            reweight.plan(seeded, from_version=OLD, to_version=OLD)


class TestWhatIsPromotedAndWhatIsNot:
    @pytest.mark.parametrize(
        "repro,numbers,expected",
        [(True, True, "B"), (True, False, "C"), (False, True, "C"), (False, False, "D")],
    )
    def test_first_hand_climbs_on_what_the_claim_carries(
        self, seeded, repro, numbers, expected
    ):
        _document(seeded, "d1", author="a1")
        _claim(seeded, "c1", "d1", speaking="own-experience", repro=repro,
               numbers=numbers)
        seeded.commit()

        report = reweight.plan(seeded, from_version=OLD, to_version=PIPELINE_VERSION)
        assert report.deltas[0].tier_after == expected

    def test_a_vendor_announcement_full_of_numbers_stays_at_F(self, seeded):
        """THE CASE THIS CHANGE COULD HAVE MADE WORSE, tested end to end.

        A launch post carries figures by construction. If `has_numbers` reached
        the vendor rung, the announcement would outweigh the engineers arguing
        with it — the fable-5 cell getting HEAVIER on a change meant to reward
        checkable evidence.
        """
        _document(seeded, "d1", platform="blog",
                  url="https://www.anthropic.com/news/fable-5", author="vendor")
        _claim(seeded, "c1", "d1", speaking="vendor-about-own-product",
               repro=True, numbers=True, tier="F", platform="blog")
        seeded.commit()

        report = reweight.plan(seeded, from_version=OLD, to_version=PIPELINE_VERSION)
        delta = report.deltas[0]
        assert delta.tier_after == "F"
        assert not delta.promoted
        assert report.provider_domain_promotions() == []

    def test_a_relay_stays_at_E(self, seeded):
        _document(seeded, "d1", author="a1")
        _claim(seeded, "c1", "d1", speaking="relayed-from-elsewhere",
               repro=True, numbers=True, tier="E")
        seeded.commit()

        report = reweight.plan(seeded, from_version=OLD, to_version=PIPELINE_VERSION)
        assert report.deltas[0].tier_after == "E"

    def test_the_document_falsifies_the_extractor_s_numbers(self, seeded):
        """`document.has_numbers = False` vetoes the promotion. Rule 2's line.

        The extractor said the quote carries numbers and the code counted none
        in the whole document, so there is nothing for the quote to contain.
        Without the veto this is a tier promotion decided by a model.
        """
        _document(seeded, "d1", author="a1", has_numbers=False)
        _claim(seeded, "c1", "d1", speaking="own-experience", repro=False,
               numbers=True)
        seeded.commit()

        report = reweight.plan(seeded, from_version=OLD, to_version=PIPELINE_VERSION)
        assert report.deltas[0].tier_after == "D"

    def test_a_null_document_column_withholds_and_is_counted(self, seeded):
        """Rule 6 — and it is a WEIGHT that does not move, not a dropped claim.

        Documents written before `collect/triage/` existed carry NULL. The claim
        stays on the board at the tier it had, and the withheld promotion is
        counted so "bare opinion" and "nobody counted its numbers" do not read
        as the same D.
        """
        _document(seeded, "d1", author="a1", has_numbers=None)
        _claim(seeded, "c1", "d1", speaking="own-experience", repro=False,
               numbers=True)
        seeded.commit()

        report = reweight.plan(seeded, from_version=OLD, to_version=PIPELINE_VERSION)
        assert report.written == 1, "withheld, not dropped"
        assert report.deltas[0].tier_after == "D"
        assert report.unconfirmed["has_numbers"] == 1
        assert "promotions WITHHELD" in reweight.summarise(report)


class TestTheVendorMisfilingCounter:
    """E6 cannot see a vendor announcement, so this counts what it would miss.

    E6's five triggers are affiliate links, sponsored disclosures, discount
    codes, syndication and predates-model. None of them detects a launch post.
    `speaking` is the only thing standing between an announcement and a
    first-hand tier, and `speaking` is the extractor's unmeasured label — so a
    promotion on a provider's own domain is the case a human should look at.
    """

    def test_a_promotion_on_a_provider_domain_is_counted_and_named(self, seeded):
        _document(seeded, "d1", platform="blog",
                  url="https://www.anthropic.com/news/fable-5", author="a1")
        # MISFILED ON PURPOSE: an announcement the extractor called first-hand.
        _claim(seeded, "c1", "d1", speaking="own-experience", repro=True,
               numbers=True, platform="blog")
        seeded.commit()

        report = reweight.plan(seeded, from_version=OLD, to_version=PIPELINE_VERSION)
        flagged = report.provider_domain_promotions()
        assert [d.provider_host for d in flagged] == ["anthropic.com"]
        assert "PROMOTED ON A PROVIDER'S OWN DOMAIN" in reweight.summarise(report)

    def test_it_counts_and_does_not_block(self, seeded):
        """Rule 8. An unmeasured check ships as a flag, never as a gate."""
        _document(seeded, "d1", platform="blog",
                  url="https://www.anthropic.com/news/fable-5", author="a1")
        _claim(seeded, "c1", "d1", speaking="own-experience", repro=True,
               numbers=True, platform="blog")
        seeded.commit()

        report = reweight.plan(seeded, from_version=OLD, to_version=PIPELINE_VERSION)
        assert report.deltas[0].tier_after == "B", (
            "flagged for review and still promoted - blocking it here would be a "
            "gate decided by an unmeasured signal, which is the thing rule 8 "
            "forbids in both directions"
        )

    def test_an_ordinary_blog_is_not_flagged(self, seeded):
        """The control. A suffix match, not a substring one."""
        _document(seeded, "d1", platform="blog",
                  url="https://notanthropic.com/posts/fable", author="a1")
        _claim(seeded, "c1", "d1", speaking="own-experience", repro=True,
               numbers=True, platform="blog")
        seeded.commit()

        report = reweight.plan(seeded, from_version=OLD, to_version=PIPELINE_VERSION)
        assert report.provider_domain_promotions() == []
        assert "no promotion on a provider's own domain" in reweight.summarise(report)


class TestARefusalIsNotASilentTruncation:
    def test_a_claim_with_no_speaking_is_refused_and_named(self, seeded):
        """The four rows written before the column existed.

        They are not carried to the new version, and that is a TRUNCATION — so
        it has to appear in the report rather than as a smaller row count
        somebody notices later.
        """
        _document(seeded, "d1", author="a1")
        _claim(seeded, "c1", "d1", speaking=None, repro=True, numbers=True)
        seeded.commit()

        report = reweight.plan(seeded, from_version=OLD, to_version=PIPELINE_VERSION)
        assert report.read == 1
        assert report.written == 0
        assert report.refusals["evidence_tier"] == 1
        assert "REFUSED" in reweight.summarise(report)
