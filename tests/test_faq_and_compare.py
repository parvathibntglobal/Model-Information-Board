"""The FAQ and the comparison — the two surfaces the landing demo had and the app did not.

Both were built by copying from `model-board-landing-demo.html`, and the demo is
a MOCK-UP: its numbers were written to look plausible. Two of its FAQ answers
name a model and a price ("DeepSeek V4 Flash at $0.14 in and $0.28 out",
"engineers most often report Claude Opus 5") and a third rules on benchmark
saturation. Its comparison table has nine rows, four of which have no source in
this database at all.

So these tests are mostly about what does NOT get copied. Pasting the demo's
answers onto a live page would put figures in front of a reader with nothing
behind them — rule 3 — and it would be invisible, because they read like every
other sentence on the page.

No database is needed for any of this: `/faq` touches none by design, and the
comparison's refusals all happen before it connects.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from judge.app import COMPARE_MAX, COMPARE_UNSOURCED, compare_page, faq_page
from judge.config import evidence_platforms, faq


class TestTheCopyLivesInTheContract:
    def test_all_eleven_questions_from_the_demo_are_present(self):
        # The demo's FAQ had eleven. Fewer would mean one was dropped in the
        # copy; the count is the cheapest possible check on that.
        assert len(faq()["questions"]) == 11

    def test_every_entry_carries_a_basis(self):
        # `policy` describes how the board WORKS and is safe as static copy.
        # `live` asserts something about MODELS and needs evidence. An entry
        # with neither would be served without anyone deciding which it is.
        for entry in faq()["questions"]:
            assert entry.get("basis") in {"policy", "live"}, entry.get("id")

    def test_every_live_entry_names_what_it_claims_and_what_to_say_instead(self):
        for entry in faq()["questions"]:
            if entry.get("basis") != "live":
                continue
            assert entry.get("claims"), f"{entry['id']} claims nothing explicitly"
            assert entry.get("unestablished_answer"), f"{entry['id']} has no honest fallback"
            # The demo wording is KEPT rather than deleted, so the difference
            # between the mock-up and the product stays auditable.
            assert entry.get("demo_answer"), f"{entry['id']} lost the demo wording"


class TestTheDemosFiguresNeverReachThePage:
    @pytest.fixture(scope="class")
    @classmethod
    def served(cls):
        return faq_page()

    def test_three_answers_are_marked_unestablished(self, served):
        unestablished = [q for q in served["questions"] if not q["established"]]
        assert {q["id"] for q in unestablished} == {
            "best-for-coding", "cheapest-per-token", "swe-bench-saturated",
        }

    def test_no_served_answer_carries_the_demos_price(self, served):
        # The exact string from the demo. If this ever appears again, somebody
        # has pasted the mock-up's answer over the honest one.
        for q in served["questions"]:
            assert "$0.14" not in q["answer"]
            assert "$0.28" not in q["answer"]

    def test_no_served_answer_names_a_model_the_corpus_has_not_reported(self, served):
        for q in served["questions"]:
            if q["established"]:
                continue
            assert "Claude Opus 5" not in q["answer"]
            assert "DeepSeek V4 Pro" not in q["answer"]

    def test_the_demo_wording_is_not_shipped_to_the_client(self, served):
        # It stays in the YAML for a reviewer. Sending it would let a frontend
        # render it by mistake, and would hand it to an answer engine.
        for q in served["questions"]:
            assert "demo_answer" not in q

    def test_an_unestablished_answer_still_answers_the_question(self, served):
        # Rule 4: silence is not criticism, and a blank is not an answer. The
        # shape of what the board cannot say is itself the finding.
        for q in served["questions"]:
            assert len(q["answer"]) > 80, q["id"]


class TestThePlatformCountIsReadNotTyped:
    def test_it_comes_from_the_sources_contract(self):
        platforms = evidence_platforms()
        assert platforms, "no platform read from contract/sources.yaml"
        # The demo said TEN and named four platforms with no terms ruling —
        # TikTok, Instagram, Hashnode, WordPress. A hardcoded count would still
        # be wrong by four.
        assert len(platforms) == len(set(platforms))

    def test_the_answer_states_the_real_count(self):
        served = faq_page()
        answer = next(q["answer"] for q in served["questions"] if q["id"] == "where-evidence")
        assert f"{len(served['platforms'])} public platforms" in answer
        for absent in ("TikTok", "Instagram", "Hashnode", "WordPress"):
            assert absent not in answer

    def test_platform_names_are_written_the_way_they_spell_themselves(self):
        platforms = set(evidence_platforms())
        assert "arXiv" in platforms and "Hacker News" in platforms
        assert "arxiv" not in platforms and "hackernews" not in platforms


class TestAComparisonRefusesBeforeItConnects:
    """Every refusal here is establishable from the request alone."""

    def test_one_model_is_not_a_comparison(self):
        with pytest.raises(HTTPException) as e:
            compare_page(ids="anthropic/claude-opus-5")
        assert e.value.status_code == 422
        assert "at least two" in e.value.detail

    def test_no_models_at_all_is_the_same_refusal(self):
        with pytest.raises(HTTPException) as e:
            compare_page(ids="")
        assert e.value.status_code == 422

    def test_a_fourth_column_is_refused_with_the_reason(self):
        with pytest.raises(HTTPException) as e:
            compare_page(ids="a/one,b/two,c/three,d/four")
        assert e.value.status_code == 422
        # The reason is presentational and is said out loud, because a cap with
        # no reason reads as an arbitrary limit.
        assert "scroll sideways" in e.value.detail

    def test_the_cap_matches_what_the_demo_offered(self):
        assert COMPARE_MAX == 3


class TestTheRowsWithNoSourceAreNamed:
    def test_the_four_demo_rows_this_board_cannot_fill_are_declared(self):
        # Licence, benchmark standing and the two hand-written lines. Returned
        # by name so the page can say what is missing: a shorter table with no
        # explanation reads as "the board compared everything it could".
        assert set(COMPARE_UNSOURCED) == {"licence", "benchmark_standing", "one_line"}

    def test_each_one_says_why_rather_than_just_that(self):
        for row, why in COMPARE_UNSOURCED.items():
            assert len(why) > 40, row
            assert "invent" in why or "no " in why or "not " in why, row
