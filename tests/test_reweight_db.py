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
from judge.reweight import FROZEN, READ
from judge.store.claims import CONNECT_TIMEOUT_SECONDS, claim_id_for

OLD = "e5.0-test"
#: The tier ruling's fork. Named so the tests run the same two steps a person
#: does - tier first at FROZEN, document facts second at READ - rather than
#: collapsing both into one call that measures neither.
TIER = "e5.2-test"
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

    `has_conditions=False` and `has_numbers=False` are what e5.1 EFFECTIVELY
    priced these rows at: `judge/cli.py:_document_facts` passed a literal
    `None`, the refusal tested `is UNSUPPLIED` and missed it, and
    `specificity_factor` read it as falsy. Since 2026-08-30 `compute()` refuses
    `None`, so the fixture states the value rather than relying on the hole.
    """
    from judge.vet.weight import LEGACY_SPECIFICITY_WEIGHTS, compute

    return compute(
        # THE FOUR-SIGNAL FORM, because that is what wrote these rows. Using
        # today's two-signal form here would make the fixture agree with the
        # code under test by construction, and the drift check - whose whole job
        # is to catch a before/after computed with different arithmetic - would
        # be asserting that a thing equals itself.
        specificity_weights=LEGACY_SPECIFICITY_WEIGHTS,
        evidence_tier=tier,
        platform=platform,
        capability_key=CAPABILITY,
        relevance="central",
        specificity="version",
        claim_date=date.today() - timedelta(days=days_ago),
        release_date=None,
        as_of=date.today(),
        version_named=True,
        has_conditions=False,
        has_numbers=False,
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

        report = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=FROZEN,
                               specificity=reweight.LEGACY)
        reweight.apply(seeded, report)
        seeded.commit()

        rows = dict(
            seeded.execute(
                "SELECT pipeline_version, evidence_tier FROM claim ORDER BY 1"
            ).fetchall()
        )
        assert rows == {OLD: "D", TIER: "B"}, (
            "both versions coexist and only the new one carries the new tier"
        )

    def test_the_new_id_is_the_contract_s_and_not_this_module_s(self, seeded):
        _document(seeded, "d1", author="a1")
        _claim(seeded, "c1", "d1", speaking="own-experience", repro=True, numbers=True)
        seeded.commit()

        report = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=FROZEN,
                               specificity=reweight.LEGACY)
        assert report.deltas[0].claim_id_after == claim_id_for(
            thread_context_id="tc1",
            source_comment_id="d1",
            capability_key=CAPABILITY,
            quote_flat_offset=(0, 10),
            pipeline_version=TIER,
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

        report = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=FROZEN,
                               specificity=reweight.LEGACY)
        reweight.apply(seeded, report)
        seeded.commit()

        key = CellKey("mv1", CAPABILITY, BUCKET)
        before = CellStore(seeded, pipeline_version=OLD).compute(key)
        after = CellStore(seeded, pipeline_version=TIER).compute(key)

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

        report = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=FROZEN,
                               specificity=reweight.LEGACY)
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

        report = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=FROZEN,
                               specificity=reweight.LEGACY)
        delta = report.deltas[0]
        assert delta.tier_after == "F"
        assert not delta.promoted
        assert report.provider_domain_promotions() == []

    def test_a_relay_stays_at_E(self, seeded):
        _document(seeded, "d1", author="a1")
        _claim(seeded, "c1", "d1", speaking="relayed-from-elsewhere",
               repro=True, numbers=True, tier="E")
        seeded.commit()

        report = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=FROZEN,
                               specificity=reweight.LEGACY)
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

        report = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=FROZEN,
                               specificity=reweight.LEGACY)
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

        report = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=FROZEN,
                               specificity=reweight.LEGACY)
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

        report = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=FROZEN,
                               specificity=reweight.LEGACY)
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

        report = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=FROZEN,
                               specificity=reweight.LEGACY)
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

        report = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=FROZEN,
                               specificity=reweight.LEGACY)
        assert report.provider_domain_promotions() == []
        assert (
            "no TIER promotion on a provider's own domain"
            in reweight.summarise(report)
        )


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

        report = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=FROZEN,
                               specificity=reweight.LEGACY)
        assert report.read == 1
        assert report.written == 0
        assert report.refusals["evidence_tier"] == 1
        assert "REFUSED" in reweight.summarise(report)


class TestTheDocumentFactsRuling:
    """READ mode — the second of the two 2026-08-30 rulings, on its own fork.

    `judge/cli.py:_document_facts` passed a literal `None` for `has_numbers` and
    `has_conditions`; `compute()`'s refusal tested `is UNSUPPLIED` and did not
    catch it; `specificity_factor` read it as falsy. Every claim in the table
    was weighted as though both were False. These assert what changes when the
    columns genuinely arrive — and that it is a SEPARATE fork from the tier, so
    neither diff carries two causes.
    """

    def test_a_present_column_moves_f_specificity_and_says_how_many(self, seeded):
        _document(seeded, "d1", author="a1", has_numbers=True, has_conditions=True)
        _claim(seeded, "c1", "d1", speaking="own-experience", repro=False,
               numbers=True)
        seeded.commit()

        report = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=READ, specificity=reweight.LEGACY)
        moved = report.specificity_moves()
        assert len(moved) == 1
        was, now = moved[0].f_specificity_before, moved[0].factors.f_specificity
        assert now > was, "the old value was the minimum - it can only rise"
        assert "f_specificity moved on 1 of 1" in reweight.summarise(report)

    def test_a_null_column_refuses_rather_than_scoring_it_false(self, seeded):
        """The whole finding, at the layer that was hiding it.

        A NULL is not a False and never was. Under the repaired check it is a
        refusal — which drops the claim, and that is the cost the measurement
        script exists to price before anyone runs this for real.
        """
        _document(seeded, "d1", author="a1", has_numbers=None, has_conditions=None)
        _claim(seeded, "c1", "d1", speaking="own-experience", repro=True,
               numbers=True)
        seeded.commit()

        report = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=READ, specificity=reweight.LEGACY)
        assert report.read == 1
        assert report.written == 0
        assert report.refusals["has_numbers"] == 1
        assert report.refusals["has_conditions"] == 1
        assert "REFUSED" in reweight.summarise(report)

    def test_option_1_shrinks_which_nulls_refuse_at_all(self, seeded):
        """An unread input must not drop a claim, and Option 1 made one unread.

        Under the legacy formula a NULL `document.has_numbers` refused the
        claim. Under Option 1 that column reaches only the TIER falsifier, which
        WITHHOLDS a promotion rather than refusing — so the same row survives,
        at the tier its other signal earns. A refusal over an input the function
        no longer reads would be a gate that had stopped meaning anything and
        went on dropping documents.
        """
        _document(seeded, "d1", author="a1", has_numbers=None, has_conditions=False)
        _claim(seeded, "c1", "d1", speaking="own-experience", repro=True,
               numbers=True)
        seeded.commit()

        legacy = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=READ, specificity=reweight.LEGACY)
        assert legacy.written == 0 and legacy.refusals["has_numbers"] == 1

        current = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                                document_facts=READ, specificity=reweight.CURRENT)
        assert current.written == 1, "the claim survives"
        assert current.refusals == {}
        assert current.deltas[0].tier_after == "C", "promoted on repro alone"
        assert current.unconfirmed["has_numbers"] == 1, "withheld, and said so"

    def test_frozen_mode_does_not_refuse_the_same_claim(self, seeded):
        """The two modes differ on exactly this row, which is why there are two.

        Running the tier ruling in READ mode would have dropped this claim and
        attributed the loss to the tier. FROZEN prices it the way e5.1 did, so
        the tier diff measures the tier.
        """
        _document(seeded, "d1", author="a1", has_numbers=None, has_conditions=None)
        _claim(seeded, "c1", "d1", speaking="own-experience", repro=True,
               numbers=True)
        seeded.commit()

        frozen = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=FROZEN,
                               specificity=reweight.LEGACY)
        assert frozen.written == 1
        assert frozen.deltas[0].tier_after == "C", (
            "promoted on repro steps alone. The NUMBERS rung is still withheld - "
            "the falsifier reads the same NULL column in both modes, because "
            "FROZEN is about f_specificity and not about the ladder"
        )
        assert frozen.unconfirmed["has_numbers"] == 1

    def test_frozen_mode_holds_f_specificity_and_the_drift_check_proves_it(self, seeded):
        _document(seeded, "d1", author="a1", has_numbers=True, has_conditions=True)
        _claim(seeded, "c1", "d1", speaking="own-experience", repro=False,
               numbers=True)
        seeded.commit()

        report = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=FROZEN, specificity=reweight.LEGACY)
        assert report.factor_drift == {}
        assert report.specificity_moves() == []
        assert "only f_evidence moved" in reweight.summarise(report)

    def test_the_mode_is_on_the_report_not_only_in_the_caller(self, seeded):
        """A set of numbers whose cause is not attached to them is the failure."""
        _document(seeded, "d1", author="a1")
        _claim(seeded, "c1", "d1", speaking="own-experience", repro=True, numbers=True)
        seeded.commit()

        report = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=READ)
        assert report.document_facts == READ
        assert "document facts: read" in reweight.summarise(report)

    def test_an_unknown_mode_refuses(self, seeded):
        with pytest.raises(ValueError, match="document_facts must be"):
            reweight.plan(seeded, from_version=OLD, to_version=TIER,
                          document_facts="whatever")


class TestPromotedIsNotTheSameQuestionAsHeavier:
    """A vendor claim can gain weight without being misfiled — and Option 1
    closed the route by which it did.

    Under the legacy four-signal `f_specificity`, an announcement's own numbers
    and repro steps lifted its weight while it sat correctly at F. Reading that
    as "promoted" put a correctly-filed claim under a warning saying `speaking`
    had misfiled it — a false accusation about the one row this whole change is
    checked against.

    Under Option 1 neither signal reaches `f_specificity` at all, so the route
    is gone: a vendor claim's numbers now buy it nothing anywhere. The
    distinction still has to exist in the code, because `f_specificity` can
    still move on `has_conditions`.
    """

    def test_under_the_legacy_formula_it_got_heavier_at_the_same_tier(self, seeded):
        _document(seeded, "d1", platform="blog",
                  url="https://www.anthropic.com/news/fable-5", author="vendor",
                  has_numbers=True, has_conditions=True)
        _claim(seeded, "c1", "d1", speaking="vendor-about-own-product",
               repro=True, numbers=True, tier="F", platform="blog")
        seeded.commit()

        report = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=READ, specificity=reweight.LEGACY)
        delta = report.deltas[0]
        assert delta.tier_after == "F"
        assert delta.heavier, "the announcement's own numbers lifted it"
        assert not delta.promoted, "the TIER did not move, and only that is a promotion"
        assert report.provider_domain_promotions() == []
        assert len(report.provider_domain_heavier_without_promotion()) == 1

    def test_option_1_closes_that_route(self, seeded):
        """The result worth having: a vendor's numbers now buy it nothing.

        `has_numbers` and `has_repro_steps` reach only the tier, and the tier
        has no vendor rung. So the second door into E2's worry — an
        announcement getting heavier through `f_specificity` rather than through
        the ladder — is shut, and this claim gets LIGHTER rather than heavier.
        """
        _document(seeded, "d1", platform="blog",
                  url="https://www.anthropic.com/news/fable-5", author="vendor",
                  has_numbers=True, has_conditions=True)
        _claim(seeded, "c1", "d1", speaking="vendor-about-own-product",
               repro=True, numbers=True, tier="F", platform="blog")
        seeded.commit()

        report = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=READ, specificity=reweight.CURRENT)
        delta = report.deltas[0]
        assert delta.tier_after == "F"
        assert not delta.heavier
        assert delta.w_after < delta.w_before
        assert report.provider_domain_heavier_without_promotion() == []

    def test_the_two_lists_are_reported_separately(self, seeded):
        _document(seeded, "d1", platform="blog",
                  url="https://www.anthropic.com/news/fable-5", author="vendor",
                  has_numbers=True, has_conditions=True)
        _claim(seeded, "c1", "d1", speaking="vendor-about-own-product",
               repro=True, numbers=True, tier="F", platform="blog")
        seeded.commit()

        text = reweight.summarise(
            reweight.plan(seeded, from_version=OLD, to_version=TIER,
                          document_facts=READ, specificity=reweight.LEGACY)
        )
        assert "no TIER promotion on a provider's own domain" in text
        assert "HEAVIER ON A PROVIDER'S OWN DOMAIN WITHOUT A TIER MOVE" in text

    def test_a_tier_promotion_is_still_flagged_as_one(self, seeded):
        _document(seeded, "d1", platform="blog",
                  url="https://www.anthropic.com/news/fable-5", author="a1",
                  has_numbers=True, has_conditions=True)
        _claim(seeded, "c1", "d1", speaking="own-experience", repro=True,
               numbers=True, platform="blog")
        seeded.commit()

        report = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=READ)
        assert report.deltas[0].promoted
        assert len(report.provider_domain_promotions()) == 1
        assert report.provider_domain_heavier_without_promotion() == []


class TestTheBoardGettingQuieterIsAResult:
    """Voices and platforms only ever go DOWN because a claim was refused.

    A refusal is a claim we dropped, so a cell that falls from two platforms to
    one has stopped being publishable for a reason `n_eff` does not show — and
    `n_eff` can RISE on the same run that costs the cell its second platform.
    Every other line in this report notices evidence arriving; this is the one
    that notices it leaving.
    """

    def _two_platform_cell(self, seeded, *, second_doc_numbers):
        _document(seeded, "d1", platform="reddit", author="a1",
                  has_numbers=True, has_conditions=False)
        _claim(seeded, "c1", "d1", speaking="own-experience", repro=True,
               numbers=True, thread="tc1")
        _document(seeded, "d2", platform="blog", author="a2",
                  has_numbers=second_doc_numbers, has_conditions=None)
        _claim(seeded, "c2", "d2", speaking="own-experience", repro=True,
               numbers=True, platform="blog", thread="tc2")
        seeded.commit()

    def test_a_refusal_that_costs_a_cell_its_second_platform_is_reported(self, seeded):
        from judge.reweight import cell_deltas, quieter_cells, summarise_losses

        # d2's has_conditions is NULL, so under the legacy formula its claim is
        # refused - and it was the cell's only blog voice.
        self._two_platform_cell(seeded, second_doc_numbers=True)
        report = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=READ, specificity=reweight.LEGACY)
        reweight.apply(seeded, report)

        losses = quieter_cells(cell_deltas(seeded, report))
        assert len(losses) == 1
        loss = losses[0]
        assert (loss.voices_before, loss.voices_after) == (2, 1)
        assert (loss.platforms_before, loss.platforms_after) == (2, 1)
        assert loss.lost_publishability, "two platforms to one is the gate condition"
        assert not loss.gone

        text = summarise_losses(losses)
        assert "THE BOARD GOT QUIETER" in text
        assert "NO LONGER PUBLISHABLE" in text

    def test_no_loss_is_printed_as_a_result_and_not_as_silence(self, seeded):
        """A section that appears only on bad news teaches that its absence
        means nothing was checked. "0 cells lost voices" is something to rely on.
        """
        from judge.reweight import summarise_losses

        assert "GOT NO QUIETER" in summarise_losses([])

    def test_a_cell_losing_every_voice_is_marked_gone(self, seeded):
        from judge.reweight import cell_deltas, quieter_cells, summarise_losses

        _document(seeded, "d1", author="a1", has_numbers=None, has_conditions=None)
        _claim(seeded, "c1", "d1", speaking="own-experience", repro=True, numbers=True)
        seeded.commit()

        report = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=READ, specificity=reweight.LEGACY)
        reweight.apply(seeded, report)

        losses = quieter_cells(cell_deltas(seeded, report))
        assert len(losses) == 1 and losses[0].gone
        assert "GONE" in summarise_losses(losses)

    def test_n_eff_rising_does_not_hide_a_lost_platform(self, seeded):
        """The case the n_eff column cannot show, asserted directly.

        The surviving voice is promoted, so `n_eff` goes UP on the same run that
        takes the cell from two platforms to one. A report that printed only
        `n_eff` would show this cell improving.
        """
        from judge.reweight import cell_deltas, quieter_cells

        self._two_platform_cell(seeded, second_doc_numbers=True)
        report = reweight.plan(seeded, from_version=OLD, to_version=TIER,
                               document_facts=READ, specificity=reweight.LEGACY)
        reweight.apply(seeded, report)

        pairs = cell_deltas(seeded, report)
        before, after = pairs[0]
        assert after.counts.n_eff > before.counts.n_eff, "n_eff rose"
        assert quieter_cells(pairs)[0].lost_publishability, "and the cell still lost"
