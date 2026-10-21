"""The arXiv arm of fetch_model searches the model name as a phrase and keeps
the papers it fetches.

Until 2026-10-07 it did neither, and nothing tested it: the bare name went in as
the search_query (any of its words matched - 10,275 hits for "DeepSeek V4"
against 169 for the phrase), and each fetched paper was dropped because
`fetch_paper` returns it without adding it to `run.stored`, the list
`write_documents` writes. 57 runs on the shared database stored 0 papers.
No network, no database: the harvester is a fake.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from collect.adapters.queries.arxiv import arxiv_query


def test_the_name_is_a_phrase_in_title_or_abstract():
    assert arxiv_query("DeepSeek V4") == 'ti:"DeepSeek V4" OR abs:"DeepSeek V4"'


def test_a_quote_cannot_end_the_phrase_early_and_whitespace_collapses():
    assert arxiv_query(' GPT "5"  Sol ') == 'ti:"GPT 5 Sol" OR abs:"GPT 5 Sol"'


def test_an_empty_name_refuses_rather_than_matching_everything():
    with pytest.raises(ValueError):
        arxiv_query("  ")


class FakeHarvester:
    def __init__(self):
        self.queries, self.written = [], []

    def harvest(self, query, terms=None, *, max_fetch=None):
        self.queries.append((query, max_fetch))
        found = [f"p{i}" for i in range(8)]
        return SimpleNamespace(papers=found, stored=found[:max_fetch], http_errors=0)

    def write_documents(self, conn, run, retrieval_provenance):
        self.written.append(list(run.stored))
        return SimpleNamespace(inserted=len(run.stored))


def test_the_papers_it_fetches_are_the_papers_it_writes(monkeypatch):
    import scripts.fetch_model as fm

    fake = FakeHarvester()
    monkeypatch.setattr(fm, "_gated_harvester", lambda *a, **k: (fake, None))
    monkeypatch.setattr(fm, "build_client", lambda **k: None)
    monkeypatch.setattr(fm, "RawStore", lambda *a, **k: None)
    stages = []
    prog = SimpleNamespace(stage=lambda *a, **k: stages.append((a, k)))
    conn = SimpleNamespace(commit=lambda: None)

    inserted = fm.harvest_arxiv(conn, prog, ["DeepSeek V4", "DeepSeek-V4", "unused"], max_queries=2)

    assert [q for q, _ in fake.queries] == [arxiv_query("DeepSeek V4"), arxiv_query("DeepSeek-V4")]
    assert all(n == fm.ARXIV_PAPERS_PER_QUERY for _, n in fake.queries)
    assert fake.written == [[f"p{i}" for i in range(fm.ARXIV_PAPERS_PER_QUERY)]] * 2
    assert inserted == 2 * fm.ARXIV_PAPERS_PER_QUERY
    assert stages[-1][1]["papers"] == 2 * fm.ARXIV_PAPERS_PER_QUERY
