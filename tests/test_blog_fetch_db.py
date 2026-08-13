"""The blog fetch path against the real schema.

Two things only a database can check:

  1. what the fetch path produces actually fills `document.text_ref` and
     `content_hash`, which are both NOT NULL, without anything being invented
     along the way;

  2. **the FR-10 collision is real.** A 304 and a feed that yielded nothing are
     written as identical rows by the columns that exist today. That is asserted
     here against Postgres rather than argued in a docstring, so the day the
     `outcome` column lands, this file is where the proof of why it was needed
     lives.

Requires a database. See docs/dev-database.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from collect.adapters.blog.fetch import BlogFetcher, FeedRun
from collect.adapters.blog.limiter import HostLimiter
from collect.adapters.blog.robots import RobotsGate
from collect.adapters.blog.validators import InMemoryValidatorStore
from collect.http import build_client
from collect.rawstore import RawStore
from tests.conftest import assert_disposable, assert_safe_target

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "blog"
UA = "modelboard/0.1 (+https://modelboard.invalid/about)"
FEED_URL = "https://notes.example.invalid/feed.xml"

#: `document.source` is the *platform* label — the schema comment says
#: `github | blog | reddit`. `harvest_run.source_id` is the source row's id,
#: which is `blogs` in contract/sources.yaml. They are deliberately different
#: strings and mixing them up would break the foreign key on one and nothing on
#: the other.
DOCUMENT_SOURCE = "blog"


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


@pytest.fixture
def conn(test_dsn):
    from collect.db import apply_schema, connect

    assert_safe_target(test_dsn)
    connection = connect(test_dsn)
    try:
        assert_disposable(connection, test_dsn)
        connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        apply_schema(connection)
        connection.execute(
            "INSERT INTO source (id, platform, endpoint, base_trust, tos_notes) "
            "VALUES ('blogs', 'blog', NULL, 0.90, 'fixture: terms review is a separate ruling')"
        )
        connection.commit()
        yield connection
    finally:
        connection.rollback()
        connection.close()


def site(feed_headers: dict[str, str] | None = None):
    routes = {
        "/robots.txt": httpx.Response(
            200, content=fixture("robots_allow.txt"), headers={"content-type": "text/plain"}
        ),
        "/feed.xml": httpx.Response(
            200,
            content=fixture("feed_rss.xml"),
            headers={"content-type": "application/rss+xml", **(feed_headers or {})},
        ),
        "/posts/summariser-swap": httpx.Response(
            200, content=fixture("article.html"), headers={"content-type": "text/html"}
        ),
        "/posts/tool-calling-notes": httpx.Response(
            200,
            content=fixture("article_with_comments.html"),
            headers={"content-type": "text/html"},
        ),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        response = routes.get(request.url.path)
        if response is None:
            return httpx.Response(404)
        if request.headers.get("if-none-match") and response.headers.get("etag") == request.headers[
            "if-none-match"
        ]:
            return httpx.Response(304)
        return httpx.Response(
            response.status_code, content=response.content, headers=dict(response.headers)
        )

    return handler


def fetcher_for(handler, tmp_path: Path, validators=None) -> BlogFetcher:
    client = build_client(user_agent=UA, transport=httpx.MockTransport(handler))
    return BlogFetcher(
        client=client,
        store=RawStore(tmp_path / "raw_store"),
        robots=RobotsGate(client, user_agent=UA, clock=lambda: 0.0),
        limiter=HostLimiter(min_interval=0.0, clock=lambda: 0.0, sleeper=lambda _s: None),
        validators=InMemoryValidatorStore() if validators is None else validators,
        pipeline_version="collect-test",
        clock=lambda: datetime(2026, 8, 13, 9, 0, tzinfo=UTC),
    )


def insert_documents(connection, run: FeedRun) -> int:
    """Write one `document` per stored article. Absent values stay NULL."""
    written = 0
    for article in run.articles:
        if not article.stored:
            continue
        artifact = article.artifact
        connection.execute(
            "INSERT INTO document (id, source, external_id, url, created_at, fetched_at, "
            "text_ref, content_hash, status) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'kept')",
            (
                f"blog_{artifact.content_hash[:16]}",
                DOCUMENT_SOURCE,
                article.entry.entry_id,
                article.url,
                # Rule 6 at the database boundary: no publication date means
                # NULL, not the fetch time. A guessed date resolves an alias
                # against the wrong window (FR-4).
                article.entry.published_at,
                artifact.fetched_at,
                artifact.ref,
                artifact.content_hash,
            ),
        )
        written += 1
    return written


def insert_harvest_run(connection, run: FeedRun) -> dict[str, object]:
    """Write the run with the columns that exist. Returns the fields it dropped."""
    fields = run.harvest_run_fields()
    homeless = {"outcome": fields.pop("outcome")}
    columns = ", ".join(fields)
    placeholders = ", ".join(["%s"] * len(fields))
    connection.execute(
        f"INSERT INTO harvest_run ({columns}) VALUES ({placeholders})",  # noqa: S608
        tuple(fields.values()),
    )
    return homeless


# ── what the fetch path fills ────────────────────────────────────────────


def test_stored_articles_fill_text_ref_and_content_hash(conn, tmp_path):
    run = fetcher_for(site(), tmp_path).harvest_feed(FEED_URL)
    assert insert_documents(conn, run) == 2

    rows = conn.execute(
        "SELECT external_id, url, text_ref, content_hash, created_at FROM document "
        "ORDER BY external_id"
    ).fetchall()
    assert len(rows) == 2
    for external_id, url, text_ref, content_hash, _created in rows:
        assert external_id.startswith("urn:uuid:")
        assert url and url.startswith("https://notes.example.invalid/posts/")
        assert text_ref.startswith("raw/sha256/")
        assert text_ref.endswith(content_hash)


def test_text_ref_names_the_article_never_the_feed(conn, tmp_path):
    """One feed covers many entries, so it cannot identify one document.

    Pointing `text_ref` at the feed would make `content_hash` non-unique per
    document, which breaks dedupe and means one post's takedown tombstones a
    blob holding all of them (NFR-6).
    """
    run = fetcher_for(site(), tmp_path).harvest_feed(FEED_URL)
    insert_documents(conn, run)

    feed_ref = run.feed.artifact.ref
    referenced = {row[0] for row in conn.execute("SELECT text_ref FROM document").fetchall()}
    assert feed_ref not in referenced
    assert len(referenced) == 2


def test_the_feed_artifact_has_nowhere_to_be_recorded(conn, tmp_path):
    """The named gap, made visible.

    The feed payload is stored and immutable, and nothing in the schema links a
    document to the feed it was discovered in — `text_ref` is taken by the
    article, for the reason above. Either `document.discovery_ref` or a
    discovery ref on `harvest_run` closes it, and both are in the harvest-tables
    conversation. When one lands, this test should start failing.
    """
    run = fetcher_for(site(), tmp_path).harvest_feed(FEED_URL)
    columns = {
        row[0]
        for row in conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name IN ('document', 'harvest_run')"
        ).fetchall()
    }
    assert run.feed.artifact is not None, "the discovery artifact is stored"
    assert "discovery_ref" not in columns, (
        "a discovery_ref column exists now — bind the feed artifact to it and delete "
        "this test"
    )


def test_a_missing_publication_date_is_stored_as_null(conn, tmp_path):
    """Rule 6. `fetched_at` is when we looked; `created_at` is when they wrote."""
    handler = site()

    def no_dates(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/feed.xml":
            return httpx.Response(
                200,
                content=fixture("feed_no_ids.xml"),
                headers={"content-type": "application/rss+xml"},
            )
        if request.url.path == "/posts/link-only":
            return httpx.Response(
                200, content=fixture("article.html"), headers={"content-type": "text/html"}
            )
        return handler(request)

    run = fetcher_for(no_dates, tmp_path).harvest_feed(FEED_URL)
    assert insert_documents(conn, run) == 1

    created_at, fetched_at = conn.execute(
        "SELECT created_at, fetched_at FROM document"
    ).fetchone()
    assert created_at is None, "an unknown publication date must not become a definite one"
    assert fetched_at is not None


def test_unique_source_external_id_survives_a_second_harvest(conn, tmp_path):
    """A repeat run must not double-count a post as two voices."""
    import psycopg

    fetcher = fetcher_for(site(), tmp_path)
    insert_documents(conn, fetcher.harvest_feed(FEED_URL))
    conn.commit()

    with pytest.raises(psycopg.errors.UniqueViolation):
        insert_documents(conn, fetcher.harvest_feed(FEED_URL))
    conn.rollback()


# ── the FR-10 collision, against the real schema ─────────────────────────


def test_harvest_run_row_writes_with_the_columns_that_exist(conn, tmp_path):
    run = fetcher_for(site(), tmp_path).harvest_feed(FEED_URL)
    homeless = insert_harvest_run(conn, run)
    conn.commit()

    row = conn.execute(
        "SELECT source_id, query_key, items_fetched, items_kept, http_errors, exhausted, "
        "truncated_by, pipeline_version FROM harvest_run"
    ).fetchone()
    assert row == ("blogs", FEED_URL, 2, 2, 0, None, None, "collect-test")
    assert homeless == {"outcome": "fetched"}


def test_a_304_and_a_dead_parser_are_the_same_row(conn, tmp_path):
    """FR-10's acceptance test passes on a fresh feed and fails silently on a cached one.

    Conditional GET makes `items_fetched=0, items_kept=0` the normal outcome for
    an unchanged feed, so a broken parser hides among unchanged feeds
    indefinitely. Both rows are written here and compared as the database sees
    them.
    """
    validators = InMemoryValidatorStore()
    cached = fetcher_for(site({"etag": 'W/"abc123"'}), tmp_path, validators=validators)
    cached.harvest_feed(FEED_URL)  # first run: 200, stores validators
    not_modified = cached.harvest_feed(FEED_URL)
    assert not_modified.outcome == "not-modified"

    def yields_nothing(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(
            200, content=b"", headers={"content-type": "application/rss+xml"}
        )

    broken = fetcher_for(yields_nothing, tmp_path / "second").harvest_feed(
        "https://other.example.invalid/feed.xml"
    )
    assert broken.outcome == "fetched"

    homeless_304 = insert_harvest_run(conn, not_modified)
    homeless_broken = insert_harvest_run(conn, broken)
    conn.commit()

    rows = conn.execute(
        "SELECT items_fetched, items_kept, http_errors, exhausted, truncated_by "
        "FROM harvest_run ORDER BY query_key"
    ).fetchall()
    assert len(rows) == 2
    assert rows[0] == rows[1], (
        "the two runs are indistinguishable in the schema as it stands — this is the "
        "gap the proposed harvest_run.outcome column closes"
    )
    # And distinguishable the moment the column exists.
    assert homeless_304 != homeless_broken


def test_outcome_has_no_column_yet(conn):
    """Executable form of the pending contract change.

    When `harvest_run.outcome` lands, this fails and points at the one line that
    binds it. Better than a comment nobody greps for.
    """
    columns = {
        row[0]
        for row in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'harvest_run'"
        ).fetchall()
    }
    assert "outcome" not in columns, (
        "harvest_run.outcome exists now — stop popping it in insert_harvest_run and "
        "write it, then delete this test"
    )
    assert "not_modified" not in columns
