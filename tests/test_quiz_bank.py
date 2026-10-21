"""The quiz's question bank (judge/quiz_bank.py).

What is pinned here is the line between the model and the page: a draft is
stored only in the right SHAPE, it is stored `pending`, and nothing reaches the
daily quiz until a person approves it. The model call itself is replaced - no
test here spends money.
"""

from __future__ import annotations

import pathlib

import psycopg
import pytest

from judge import quiz_bank
from judge.config import quiz_drafter_settings

SCHEMA = pathlib.Path(__file__).resolve().parents[1] / "contract" / "tables.sql"
TOPIC = quiz_drafter_settings()["topics"][0]


def _q(text="What does a tokenizer turn text into?", **kw):
    q = {
        "question": text,
        "options": ["Tokens", "Embeddings only", "Gradients", "Attention heads"],
        "answer_index": 0,
        "explanation": "A tokenizer splits text into the units the model reads.",
        "difficulty": "easy",
    }
    q.update(kw)
    return q


class TestShapeChecks:
    def test_a_well_formed_question_passes(self):
        assert quiz_bank.problem(_q()) is None

    @pytest.mark.parametrize(
        "bad, why",
        [
            ({"options": ["a", "b", "c"]}, "four"),
            ({"options": ["Tokens", "tokens", "Gradients", "Heads"]}, "same thing"),
            ({"answer_index": 4}, "answer"),
            ({"answer_index": True}, "answer"),
            ({"options": ["Tokens", "Bytes", "Words", "All of the above"]}, "all/none"),
            ({"question": "How much does $5 per million tokens buy?"}, "price"),
            ({"question": "Why?"}, "question"),
            ({"difficulty": "trivial"}, "difficulty"),
            ({"explanation": ""}, "explanation"),
        ],
    )
    def test_a_draft_with_the_wrong_shape_is_refused_with_a_reason(self, bad, why):
        assert why in (quiz_bank.problem(_q(**bad)) or "")

    def test_the_id_ignores_case_and_punctuation(self):
        assert quiz_bank.question_id("What is a token?") == quiz_bank.question_id("what is a TOKEN")


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as c:
        c.execute("DROP SCHEMA IF EXISTS public CASCADE")
        c.execute("CREATE SCHEMA public")
        c.execute(SCHEMA.read_text(encoding="utf-8"))
        c.commit()
        yield c


def _stub(monkeypatch, drafted):
    monkeypatch.setattr(
        quiz_bank, "_call", lambda *a, **k: (drafted, {"served": "deepseek/x", "usage": {}})
    )


class TestDraftingStoresPendingOnly:
    def test_usable_drafts_are_stored_pending_and_the_rest_counted(self, conn, monkeypatch):
        _stub(monkeypatch, [_q(), _q("What is a context window?"), _q(answer_index=7)])
        out = quiz_bank.draft(conn, TOPIC)
        assert (out["proposed"], out["stored"]) == (3, 2)
        assert sum(out["refused"].values()) == 1
        assert {r[0] for r in conn.execute("SELECT state FROM quiz_question").fetchall()} == {
            "pending"
        }

    def test_the_same_question_drafted_twice_is_one_row(self, conn, monkeypatch):
        _stub(monkeypatch, [_q()])
        quiz_bank.draft(conn, TOPIC)
        again = quiz_bank.draft(conn, TOPIC)
        assert (again["stored"], again["already_in_bank"]) == (0, 1)

    def test_a_topic_outside_the_contract_is_refused(self, conn, monkeypatch):
        _stub(monkeypatch, [_q()])
        with pytest.raises(ValueError):
            quiz_bank.draft(conn, "Something nobody listed")


class TestReview:
    def test_approve_reject_and_undo(self, conn, monkeypatch):
        _stub(monkeypatch, [_q()])
        quiz_bank.draft(conn, TOPIC)
        qid = quiz_bank.listing(conn)[0]["id"]
        assert quiz_bank.review(conn, qid, "approved")["state"] == "approved"
        assert [q["id"] for q in quiz_bank.approved(conn)] == [qid]
        quiz_bank.review(conn, qid, "rejected", "the answer is wrong")
        assert quiz_bank.approved(conn) == []
        assert quiz_bank.listing(conn, "rejected")[0]["review_note"] == "the answer is wrong"
        quiz_bank.review(conn, qid, "pending")
        assert conn.execute("SELECT reviewed_at FROM quiz_question").fetchone()[0] is None
        assert quiz_bank.review(conn, "qq_nope", "approved") is None
        with pytest.raises(ValueError):
            quiz_bank.review(conn, qid, "maybe")
