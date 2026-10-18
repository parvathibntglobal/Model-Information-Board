"""The topic harvest's platform arms (2026-10-18): Hacker News stories, dev.to
articles and Hugging Face daily papers, by each topic's own terms.

No network and no database: each platform's gated `harvester_for_source` is
replaced by a fake, so these test what the harvest KEEPS, not what a platform
answers.
"""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _script():
    spec = importlib.util.spec_from_file_location(
        "harvest_topics", ROOT / "scripts" / "harvest_topics.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


NOW = datetime.now(UTC)
RECENT = (NOW - timedelta(days=2)).isoformat()
OLD = (NOW - timedelta(days=400)).isoformat()
TOPICS = [
    {"key": "agent-security", "terms": ["agent security", "multi-agent system", "unused third"]}
]


class FakeHN:
    def __init__(self):
        self.queries = []

    def search_stories(self, q, *, since_ts, per_page):
        self.queries.append(q)
        return [
            {
                "objectID": "1",
                "title": "Agent security in practice",
                "points": 50,
                "num_comments": 7,
                "url": "https://example.com/a",
                "author": "x",
                "created_at": RECENT,
            },
            {"objectID": "2", "title": "A quiet post", "points": 1, "created_at": RECENT},
        ]


class FakeDevto:
    def __init__(self):
        self.queries = []

    def search(self, q):
        self.queries.append(q)
        hit = lambda i, when: SimpleNamespace(  # noqa: E731
            article_id=i,
            title=f"Post {i}",
            description="d",
            url=f"https://dev.to/u/post-{i}",
            published_at=when,
            author_handle="u",
        )
        return SimpleNamespace(hits=[hit(10, RECENT), hit(11, OLD)])


class FakeHF:
    def __init__(self):
        self.days = []

    def daily_papers(self, day):
        self.days.append(day)
        return [
            {
                "paper": {
                    "id": "2610.00001",
                    "title": "A paper",
                    "summary": "s",
                    "upvotes": 9,
                    "authors": [{"name": "A. Author"}],
                    "publishedAt": RECENT,
                }
            }
        ]


def _run(monkeypatch, refuse=()):
    mod = _script()
    fakes = {"hackernews": FakeHN(), "devto": FakeDevto(), "huggingface": FakeHF()}

    def factory(name):
        def build(source, **kw):
            if name in refuse:
                raise PermissionError("ruling does not hold")
            return fakes[name]

        return build

    for name in fakes:
        monkeypatch.setattr(getattr(mod, name), "harvester_for_source", factory(name))
    monkeypatch.setattr(
        mod,
        "_platform_cfg",
        lambda: {
            "queries_per_topic": 2,
            "window_days": 30,
            "hackernews": {"per_query": 20, "min_points": 3},
            "devto": {"per_query": 15},
            "huggingface_papers": {"daily": True},
        },
    )
    contract = SimpleNamespace(platforms=[{"id": n} for n in fakes], rulings=[])
    items, notes = mod.harvest_platforms(contract, None, None, TOPICS)
    return items, notes, fakes


def test_each_platform_contributes_what_passes_its_filter(monkeypatch):
    items, _notes, _ = _run(monkeypatch)
    ids = sorted(i["id"] for i in items)
    # HN story 2 is under the points floor; dev.to post 11 is outside the window.
    assert ids == ["devto:10", "hackernews:1", "hfpapers:2610.00001"]


def test_only_the_first_terms_are_queried_and_devto_gets_no_hyphen(monkeypatch):
    _items, _notes, fakes = _run(monkeypatch)
    assert fakes["hackernews"].queries == ["agent security", "multi-agent system"]
    # dev.to answers HTTP 500 to a hyphenated query; a space finds the same posts.
    assert fakes["devto"].queries == ["agent security", "multi agent system"]
    assert len(fakes["huggingface"].days) == 30


def test_a_hacker_news_item_links_the_discussion_and_names_the_article(monkeypatch):
    items, _notes, _ = _run(monkeypatch)
    hn = next(i for i in items if i["id"] == "hackernews:1")
    assert hn["url"] == "https://news.ycombinator.com/item?id=1"
    assert "https://example.com/a" in hn["summary"] and "50 points" in hn["summary"]


def test_a_refused_platform_is_reported_and_the_others_still_run(monkeypatch):
    items, notes, _ = _run(monkeypatch, refuse=("devto",))
    assert any(n.startswith("devto: refused") for n in notes)
    assert {i["source"] for i in items} == {"hackernews", "huggingface"}


def test_the_config_has_no_defaults(monkeypatch):
    mod = _script()
    monkeypatch.setattr("judge.topics.config", lambda: {"platforms": {"window_days": 30}})
    with pytest.raises(SystemExit, match="platforms"):
        mod._platform_cfg()


def test_a_paper_already_stored_from_arxiv_is_not_stored_twice():
    """Compared on the BARE id: arXiv rows are versioned ("arxiv:2610.00001v1")
    and Hugging Face's are not. An exact-id check never matched (2026-10-18)."""
    mod = _script()

    class Conn:
        def __init__(self):
            self.inserted, self.deleted = [], []

        def execute(self, sql, params):
            if sql.startswith("SELECT 1"):
                hit = params[1] == "arxiv:2610.00001v%"
                return SimpleNamespace(fetchone=lambda: (1,) if hit else None)
            if sql.startswith("DELETE"):
                self.deleted.append(params[0])
                return SimpleNamespace(rowcount=1)
            self.inserted.append(params["id"])
            return SimpleNamespace(rowcount=1)

    conn = Conn()
    base = {"kind": "paper", "title": "t", "summary": "s", "url": "u", "authors": [],
            "published_at": NOW}
    hf = {**base, "source": "huggingface"}
    n = mod.store_items(conn, [{**hf, "id": "hfpapers:2610.00001"},
                               {**hf, "id": "hfpapers:2610.99999"}])
    assert conn.inserted == ["hfpapers:2610.99999"] and n == 1
    # arXiv arriving later replaces its Hugging Face twin: it is the paper's own source.
    mod.store_items(conn, [{**base, "source": "arxiv", "id": "arxiv:2610.99999v2"}])
    assert conn.deleted == ["hfpapers:2610.99999"]


def test_a_hacker_news_thread_reads_as_plain_text_in_order():
    """live_text's flattener (generate_sample_blogs._hn_thread_text): the story,
    then each comment before its replies, tags stripped and entities decoded."""
    import generate_sample_blogs as g

    item = {
        "title": "Show HN: a thing",
        "text": "<p>We built it &amp; it works</p>",
        "children": [
            {"text": "First <i>comment</i>", "children": [{"text": "a reply", "children": []}]},
            {"text": "", "children": []},
            {"text": "Second comment", "children": []},
        ],
    }
    lines = g._hn_thread_text(item).split("\n\n")
    assert lines == ["Show HN: a thing", "We built it & it works", "First comment", "  a reply",
                     "Second comment"]
