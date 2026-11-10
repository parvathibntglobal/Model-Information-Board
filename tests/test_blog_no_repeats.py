"""The blog planner does not retell a story or repeat an FAQ question.

Measured 2026-10-30 over the 283 stored posts not rejected: 38 pairs of posts
shared half or more of their sources, and 81 FAQ questions were answered in 2
to 5 posts each. The topic planner's fresh-first rule read only the packs on the
machine that ran it, so on any other machine it did nothing. No database here.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("gsb", ROOT / "generate_sample_blogs.py")
g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g)


def _rec(subject, docs=(), faq=(), plan_key=None):
    return {"plan_key": plan_key, "subject": subject, "documents": set(docs), "faq": list(faq)}


def test_faq_questions_are_read_from_an_exported_body():
    body = [["h2", {"text": "How it works", "id": "how"}], ["h3", "Not a question"],
            ["h2", {"text": "Questions people ask", "num": "FAQ", "id": "faq"}],
            ["h3", "Is GPT-6 Sol good for coding?"], ["p", "Yes."],
            ["h3", "How much does GPT-6 Sol cost?"], ["p", "..."],
            ["h3", "List prices"]]
    # "List prices" is an h3 after the FAQ with no h2 between: export_post
    # writes it there, and it is not a question.
    assert g.faq_questions(body)[:2] == ["Is GPT-6 Sol good for coding?",
                                         "How much does GPT-6 Sol cost?"]


def test_used_sources_are_gathered_by_subject():
    used, by = g.used_sources([_rec("openai/gpt-6-sol", ["t1", "t2"]), _rec("concept/rag", ["i1"]),
                               _rec(None, ["t9"])])
    assert used == {"t1", "t2", "i1", "t9"}
    assert by == {"openai/gpt-6-sol": {"t1", "t2"}, "concept/rag": {"i1"}}


def test_a_post_mostly_from_used_sources_is_a_repeat():
    same = {"t1", "t2", "t3"}
    assert g.repeat_share(["t1", "t2", "t3", "t4"], same) == 0.75
    assert g.repeat_share(["t4", "t5"], same) == 0.0
    assert g.repeat_share([], same) == 0.0


def test_faq_questions_are_taken_per_subject_and_per_model():
    recs = [_rec("openai/gpt-6-sol", faq=["Is GPT-6 Sol good for coding?"]),
            _rec("anthropic/claude-opus-5+openai/gpt-6-sol",
                 faq=["Is GPT-6 Sol cheaper than Opus 5?"]),
            _rec("concept/rag", faq=["What is RAG?"]),
            _rec("concept/memory", faq=["How does agent memory work?"])]
    sol = g.taken_faq(recs, "openai/gpt-6-sol")
    assert g.norm_heading("Is GPT-6 Sol good for coding?") in sol
    # A pair naming the model counts too.
    assert g.norm_heading("Is GPT-6 Sol cheaper than Opus 5?") in sol
    assert g.norm_heading("What is RAG?") not in sol
    assert g.taken_faq(recs, "concept/rag") == {g.norm_heading("What is RAG?")}


def test_a_repeated_faq_question_is_refused_and_a_new_one_passes():
    taken = {g.norm_heading("Why do LLMs hallucinate?")}
    faq = [{"question": "why do LLMs hallucinate?", "answer": "x"},
           {"question": "Can retrieval stop hallucinations?", "answer": "x"}]
    v = g.faq_violations(faq, taken)
    assert len(v) == 1 and v[0].startswith("faq[0].question")


def test_the_repeat_cut_is_required_and_bounded():
    assert g.max_repeat_share(g.load_formats()) == pytest.approx(0.5)
    for bad in ({}, {"planner": {}}, {"planner": {"max_repeat_share": 0}},
                {"planner": {"max_repeat_share": 1.5}}):
        with pytest.raises(g.BuildError):
            g.max_repeat_share(bad)


def test_rejected_posts_free_their_sources(tmp_path, monkeypatch):
    """Only the files on this machine here; the shared table is read with the
    same rule (`state <> 'rejected'`) in post_records."""
    monkeypatch.setattr(g, "POSTS_OUT", tmp_path / "posts")
    monkeypatch.setattr(g, "PACKS", tmp_path / "packs")
    (tmp_path / "posts").mkdir()
    (tmp_path / "packs").mkdir()
    assert g.post_records(None) == []
    assert g.used_topic_items(None) == set()


def test_a_rewrite_is_not_refused_for_its_own_questions():
    """--format/--subject replaces the post, so its own FAQ is not taken; another
    post on the same subject still is (#588 review)."""
    recs = [_rec("openai/gpt-6-sol", faq=["Is GPT-6 Sol good for coding?"],
                 plan_key="field-report:openai/gpt-6-sol"),
            _rec("openai/gpt-6-sol", faq=["How much does GPT-6 Sol cost?"],
                 plan_key="cost-teardown:openai/gpt-6-sol")]
    taken = g.taken_faq(recs, "openai/gpt-6-sol", own_key="field-report:openai/gpt-6-sol")
    assert taken == {g.norm_heading("How much does GPT-6 Sol cost?")}


class _FakeTable:
    """Stands in for a connection to the shared blog_post table."""

    def __init__(self, rows):
        self.rows = rows

    def transaction(self):
        import contextlib
        return contextlib.nullcontext()

    def cursor(self, row_factory=None):
        rows = self.rows

        class _Cur:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def execute(self, sql, params=None):
                pass

            def fetchall(self):
                return rows
        return _Cur()


def test_the_table_decides_for_any_post_it_holds(tmp_path, monkeypatch):
    """A local export of a post the table rejected no longer holds its sources on
    the machine that wrote it; a pack the table has never seen still counts."""
    import json

    posts, packs = tmp_path / "posts", tmp_path / "packs"
    posts.mkdir()
    (packs / "p1").mkdir(parents=True)
    monkeypatch.setattr(g, "POSTS_OUT", posts)
    monkeypatch.setattr(g, "PACKS", packs)
    (posts / "r.json").write_text(json.dumps({
        "provenance": {"plan_key": "field-report:m/rejected", "documents": ["t-rej"]},
        "body": []}), encoding="utf-8")
    (packs / "p1" / "pack.json").write_text(json.dumps({
        "post": {"plan": {"plan_key": "field-report:m/in-progress"}},
        "docs": [{"thread_context_id": "t-new"}]}), encoding="utf-8")
    table = _FakeTable([("field-report:m/rejected", "rejected", ["t-rej"], []),
                        ("field-report:m/live", "approved", ["t-live"], [])])
    used, _by = g.used_sources(g.post_records(table))
    assert used == {"t-live", "t-new"}
