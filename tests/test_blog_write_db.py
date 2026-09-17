"""Blog articles become `document` and `thread_context` rows, against Postgres.

The path `assemble_article` did not have a caller for. These FAIL rather than
skip with no database, like the other write-path tests.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import psycopg
import pytest

from tests.conftest import require_feed_libraries

# Above the imports it guards. See tests/conftest.py:require_feed_libraries.
#
# THE FIFTH MODULE, and it was missed. conftest's note says "the four test
# modules that genuinely parse feeds" - this is a fifth, `write_blog_run`
# reaches `parse.py` the same way, and without the guard its COLLECTION
# error interrupted the whole suite. That is the exact failure the other
# four were given this guard to stop: on 2026-09-11 a full run reported
# `Interrupted: 1 error during collection` and nothing executed.
require_feed_libraries()

from collect.adapters.blog.write import write_blog_run  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402

SCHEMA = Path(__file__).resolve().parents[1] / "contract" / "tables.sql"

ARTICLE = (
    b"<html><head><title>T</title></head><body><article>"
    b"<p>We moved to Claude Opus 5 and the context window held up past 200k "
    b"tokens, which the previous model did not manage on the same corpus.</p>"
    b"<p>Latency went from 4.2s to 1.8s at p95 across forty thousand tickets "
    b"a week, measured over a fortnight rather than a demo.</p>"
    b"<p>Tool calling stayed reliable at fourteen tools, where we had been "
    b"seeing silent failures at eight before the migration.</p>"
    b"</article></body></html>"
)


@dataclass
class _Entry:
    entry_id: str
    url: str | None
    published_at: datetime | None = None


@dataclass
class _Artifact:
    ref: str
    content_hash: str


@dataclass
class _ArticleFetch:
    entry: _Entry
    artifact: _Artifact | None

    @property
    def stored(self) -> bool:
        return self.artifact is not None


@dataclass
class _FeedRun:
    articles: list
    pipeline_version: str = "collect-0.1.0"


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn) as connection:
        connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
        connection.execute("CREATE SCHEMA public")
        connection.execute(SCHEMA.read_text(encoding="utf-8"))
        connection.commit()
        yield connection


@pytest.fixture
def store():
    return RawStore(Path(tempfile.mkdtemp()))


def _run(store: RawStore, *, entry_id: str = "https://example.test/post-1", body=ARTICLE):
    stored = store.put(body)
    return _FeedRun(articles=[
        _ArticleFetch(_Entry(entry_id, entry_id), _Artifact(stored.ref, stored.content_hash))
    ])


def test_an_article_becomes_a_document_and_a_one_member_thread(conn, store):
    report = write_blog_run(conn, _run(store), store=store)
    conn.commit()

    assert report.articles_seen == 1
    assert report.documents_inserted == 1
    assert report.contexts_inserted == 1
    assert report.nothing_extracted == 0

    source, status, author = conn.execute(
        "SELECT source, status, author_id FROM document"
    ).fetchone()
    assert source == "blog", "the platform, which platform_count counts"
    assert status == "kept", "the default: this stage did not filter"
    assert author is None, "unknown, not anonymous - authors resolve elsewhere"

    method, children, observed, hidden, unsized, ratio = conn.execute(
        "SELECT selection_method, child_count, observed_children, "
        "hidden_children_min, hidden_branches_unsized, coverage_ratio "
        "FROM thread_context"
    ).fetchone()
    assert method == "whole_document", "nothing was ranked"
    assert children == 0
    assert observed == 0, "a measurement: we looked, none stored"
    assert hidden is None, "rule 6: include_comments=False means WE withheld"
    assert unsized == 0
    assert ratio is None, "0/0 is not full coverage"


@pytest.mark.parametrize("body, what", [
    (b'<html><body><div id="root"></div><script>app()</script></body></html>', "a JS shell"),
    (b"<html><head><title>T</title></head></html>", "head only"),
    (b'{"json": true}', "not HTML at all"),
])
def test_nothing_extracted_is_counted_and_writes_no_row(conn, store, body, what):
    """Not an empty article, and never written as a body-less row.

    `<nav>Home</nav>` is deliberately NOT one of these cases: trafilatura
    extracts `'Home'` from it, so it is a one-word article rather than nothing.
    Checked rather than assumed — the first version of this test used it and
    passed for the wrong reason.
    """
    report = write_blog_run(conn, _run(store, body=body), store=store)
    conn.commit()

    assert report.nothing_extracted == 1
    assert report.documents_inserted == 0
    assert report.contexts_inserted == 0
    assert conn.execute("SELECT count(*) FROM document").fetchone()[0] == 0


def test_a_refetch_of_an_unchanged_article_is_not_an_error(conn, store):
    """`ON CONFLICT DO NOTHING`. For thread_context it is stronger than
    politeness: replacing an `offset_map` in place would silently invalidate
    every claim already stored against it."""
    write_blog_run(conn, _run(store), store=store)
    conn.commit()
    again = write_blog_run(conn, _run(store), store=store)
    conn.commit()

    assert again.articles_seen == 1
    assert again.documents_inserted == 0
    assert again.already_present == 1
    assert conn.execute("SELECT count(*) FROM document").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM thread_context").fetchone()[0] == 1


def test_the_offset_map_survives_the_round_trip(conn, store):
    """`offset_map` is what every quote resolves against, so it is the column
    worth reading back rather than trusting the insert."""
    write_blog_run(conn, _run(store), store=store)
    conn.commit()

    stored_map = conn.execute("SELECT offset_map FROM thread_context").fetchone()[0]
    assert isinstance(stored_map, list) and stored_map
    assert {s["document_id"] for s in stored_map} == {"blog:https://example.test/post-1"}
    cursor = 0
    for segment in sorted(stored_map, key=lambda s: s["flat_start"]):
        assert segment["flat_start"] == cursor, "a hole in the map"
        cursor = segment["flat_end"]


def test_a_blog_row_and_a_reddit_row_reach_platform_count_two(conn, store):
    """End to end, through the real writer rather than a hand-written 'blog'."""
    from psycopg.types.json import Json

    write_blog_run(conn, _run(store), store=store)
    conn.execute(
        "INSERT INTO document (id, source, external_id, url, fetched_at, text_ref, "
        "content_hash, status) VALUES (%s,%s,%s,%s,now(),%s,%s,%s)",
        ("reddit:t1_x", "reddit", "t1_x", "https://reddit.test/x",
         "raw/x", "hx", "kept"),
    )
    conn.commit()
    assert Json  # imported for parity with the other write-path tests

    platforms = {
        row[0] for row in conn.execute("SELECT DISTINCT source FROM document").fetchall()
    }
    assert platforms == {"blog", "reddit"}
    assert len(platforms) == 2, (
        "judge/store/cells.py counts DISTINCT document.source as platform_count; "
        "two here is what takes a cell off `insufficient` for the right reason"
    )


# ── the harvest_run link, wired 2026-09-17 ──────────────────────────────


def test_no_run_id_writes_no_run_for_source_and_a_null_link(conn, store):
    """The default, and it stays TRUE for a caller with no run.

    `write_blog_run` is reachable without a ledger row - every test above does
    it - so the absence of a run must remain expressible. Replacing the old
    hardcoded literal with the other literal would have made those callers
    assert a run that never happened.
    """
    write_blog_run(conn, _run(store), store=store)
    conn.commit()

    provenance, run_id = conn.execute(
        "SELECT retrieval_provenance, harvest_run_id FROM document"
    ).fetchone()
    assert provenance == "no_run_for_source"
    assert run_id is None


def test_a_run_id_writes_run_recorded_and_the_link(conn, store):
    """The pair the schema refuses to let disagree.

    `document_retrieval_provenance_agrees_ck` asserts
    `(retrieval_provenance = 'run_recorded') = (harvest_run_id IS NOT NULL)`,
    so this would be refused by the database if `_provenance` set one without
    the other. Asserted here rather than trusted, because the constraint only
    fires on the WRONG combination and a test that never writes the right one
    proves nothing about the writer.
    """
    conn.execute(
        "INSERT INTO source (id, platform, endpoint, base_trust, tos_notes, provenance) "
        "VALUES ('blog:t.example', 'blog', 'https://t.example/feed', 0.9, 'x', 'seed') "
        "ON CONFLICT (id) DO NOTHING"
    )
    conn.execute(
        "INSERT INTO harvest_run (id, source_id, query_key, pipeline_version) "
        "VALUES ('hr_test_blog', 'blog:t.example', 'https://t.example/feed', 'test')"
    )
    write_blog_run(conn, _run(store), store=store, harvest_run_id="hr_test_blog")
    conn.commit()

    provenance, run_id = conn.execute(
        "SELECT retrieval_provenance, harvest_run_id FROM document"
    ).fetchone()
    assert provenance == "run_recorded"
    assert run_id == "hr_test_blog"
