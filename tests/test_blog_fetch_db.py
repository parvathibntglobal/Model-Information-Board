"""The blog fetch path against the real schema.

Two things only a database can check:

  1. what the fetch path produces actually fills `document.text_ref` and
     `content_hash`, which are both NOT NULL, without anything being invented
     along the way;

  2. **the FR-10 collision is real, and `harvest_run.outcome` did not close it.**
     A 304 and a feed that yielded nothing are written as identical rows. That
     was true of the columns that existed before `outcome` landed in dab9d41,
     and it is still true after, because the vocabulary that landed
     (`ok | refused | error`) has no word for "unchanged" — see
     `docs/proposals/harvest-run-outcome-vocabulary.md`. Asserted here against
     Postgres rather than argued in a docstring, so the surviving gap has a
     failing-when-fixed test instead of a comment.

Requires a database. See docs/dev-database.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import get_args

import httpx
import pytest

from tests.conftest import (
    assert_disposable,
    assert_safe_target,
    require_feed_libraries,
)

# Above the imports it guards. See tests/conftest.py:require_feed_libraries.
require_feed_libraries()

from collect.adapters.blog.fetch import BlogFetcher, FeedRun, Outcome  # noqa: E402
from collect.adapters.blog.robots import RobotsGate  # noqa: E402
from collect.adapters.blog.validators import InMemoryValidatorStore  # noqa: E402
from collect.http import build_client  # noqa: E402
from collect.limiter import HostLimiter  # noqa: E402
from collect.ops.ledger import ERROR, OK, REFUSED  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402

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
            "INSERT INTO source "
            "  (id, platform, endpoint, base_trust, tos_notes, provenance, "
            "   terms_ruling, terms_checked_on, terms_evidence) "
            "VALUES ('blogs', 'blog', NULL, 0.90, "
            "        'fixture: the platform row; feed rulings are per feed', "
            "        'seed', 'blog-umbrella-not-a-fetch-target', DATE '2026-08-14', "
            "        '{\"endpoint_is_null\": true}'::jsonb)"
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


#: The adapter's fetch DISPOSITION mapped onto the schema's job VERDICT.
#:
#: Two vocabularies for two different concepts that share a column name, and the
#: collision is not settled — `docs/proposals/harvest-run-outcome-vocabulary.md`.
#: `collect/adapters/blog/fetch.py:82` is what the fetch DID
#: (`fetched | not-modified | robots-blocked | error`); `harvest_run.outcome` is
#: how the run CONCLUDED (`ok | refused | error`, `job_run`'s words, chosen
#: deliberately in dab9d41). `error` is the only word in both, and it is the only
#: one that means the same thing in both.
#:
#: This mapping is THIS TEST'S READING, and it lives here rather than in
#: `collect/` because picking it is a `contract/` decision and rule "flag it,
#: don't take it" applies:
#:
#:   fetched, not-modified  -> ok       the sweep ran and concluded normally. An
#:                                     unchanged feed is a successful sweep.
#:   robots-blocked         -> refused  we chose not to fetch, which is what
#:                                      `refused` means at `ledger.py:161` for
#:                                      the terms gate. robots is the same no.
#:   error                  -> error
#:
#: **IT LOSES THE 304, AND THAT LOSS IS THE POINT OF THIS FILE.** `not-modified`
#: and a `fetched` run that yielded nothing both become `ok, items_fetched = 0`,
#: so the FR-10 collision survives the column that was proposed partly to close
#: it. Asserted below rather than left implicit, because an unclosed gap that
#: nobody re-checks reads as closed (rule 4).
DISPOSITION_TO_VERDICT: dict[str, str] = {
    "fetched": OK,
    "not-modified": OK,
    "robots-blocked": REFUSED,
    "error": ERROR,
}


def insert_harvest_run(connection, run: FeedRun) -> dict[str, object]:
    """Write the run. Returns the disposition the verdict could not carry.

    `outcome` is no longer popped — the column exists. It is TRANSLATED, because
    the adapter's value is not in the set `harvest_run_outcome_ck` accepts:
    writing `'fetched'` straight through trades `harvest_run_finish_ck` for
    `harvest_run_outcome_ck` and fixes nothing.

    The return value keeps its shape and changes its meaning: it was "the field
    with no column", it is now "the distinction the column cannot hold".
    """
    fields = run.harvest_run_fields()
    disposition = fields["outcome"]
    if disposition not in DISPOSITION_TO_VERDICT:
        raise AssertionError(
            f"no verdict mapped for disposition {disposition!r}. A fifth value was "
            "added to collect/adapters/blog/fetch.py:Outcome without deciding how "
            "harvest_run.outcome should record it — see "
            "docs/proposals/harvest-run-outcome-vocabulary.md"
        )
    fields["outcome"] = DISPOSITION_TO_VERDICT[disposition]
    columns = ", ".join(fields)
    placeholders = ", ".join(["%s"] * len(fields))
    connection.execute(
        f"INSERT INTO harvest_run ({columns}) VALUES ({placeholders})",  # noqa: S608
        tuple(fields.values()),
    )
    return {"disposition": disposition}


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
        "truncated_by, outcome, finished_at IS NOT NULL, pipeline_version FROM harvest_run"
    ).fetchone()
    assert row == ("blogs", FEED_URL, 2, 2, 0, None, None, OK, True, "collect-test")
    assert homeless == {"disposition": "fetched"}


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
        "SELECT items_fetched, items_kept, http_errors, exhausted, truncated_by, outcome "
        "FROM harvest_run ORDER BY query_key"
    ).fetchall()
    assert len(rows) == 2
    assert rows[0] == rows[1], (
        "the two runs are indistinguishable in the schema — and `outcome` is now IN "
        "this SELECT, so the column landing did not close the gap. Both are "
        f"{OK!r} with items_fetched = 0. If this assertion has started failing, the "
        "vocabulary gained a word for 'unchanged' and "
        "docs/proposals/harvest-run-outcome-vocabulary.md has been resolved — invert "
        "this test and say so there."
    )
    # The distinction exists upstream and is dropped at the boundary: the adapter
    # knows which run was which, and nothing it writes can say so.
    assert homeless_304 == {"disposition": "not-modified"}
    assert homeless_broken == {"disposition": "fetched"}
    assert homeless_304 != homeless_broken


def test_outcome_landed_and_cannot_say_unchanged(conn):
    """Executable form of the contract change that is STILL pending.

    Replaces `test_outcome_has_no_column_yet`, which fired as designed when
    dab9d41 added the column. Its instruction — "stop popping it and write it" —
    was half right: popping had to stop, but writing the adapter's value through
    would have violated `harvest_run_outcome_ck` instead. So the canary is
    re-aimed at the part that did not land, rather than deleted.
    """
    columns = {
        row[0]
        for row in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'harvest_run'"
        ).fetchall()
    }
    assert "outcome" in columns, "harvest_run.outcome was removed — this file assumes it"

    definition = conn.execute(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conname = 'harvest_run_outcome_ck'"
    ).fetchone()[0]
    for verdict in (OK, REFUSED, ERROR):
        assert f"'{verdict}'" in definition, (
            f"{verdict!r} is no longer accepted — collect/ops/ledger.py validates "
            "against these three before the database sees them, so the two would "
            "disagree about which verdicts exist"
        )

    # The gap. Read off the live constraint rather than a copy of it, so this
    # cannot pass against a schema that has moved on.
    assert "not-modified" not in definition, (
        "harvest_run_outcome_ck accepts 'not-modified' now — the 304 is expressible, "
        "so DISPOSITION_TO_VERDICT should stop folding it into 'ok' and "
        "test_a_304_and_a_dead_parser_are_the_same_row should be inverted"
    )
    assert "not_modified" not in columns, (
        "a dedicated column appeared — the proposal asked for a vocabulary value, not "
        "a second boolean; check docs/proposals/harvest-run-outcome-vocabulary.md"
    )


def test_every_disposition_has_a_verdict():
    """The mapping's domain is the adapter's closed set, exactly.

    A fifth `Outcome` value added upstream fails here rather than at an INSERT,
    and a stale entry left behind after one is removed fails here too.

    **No `conn`, deliberately.** This is a statement about two Python vocabularies
    and it needs no database, so it does not ask for one — it is the only test in
    this file that still runs where Postgres is absent, and the mapping is the
    thing most likely to be edited by someone who has not brought one up.
    """
    assert set(DISPOSITION_TO_VERDICT) == set(get_args(Outcome)), (
        "DISPOSITION_TO_VERDICT and blog/fetch.py:Outcome have drifted apart"
    )
    assert set(DISPOSITION_TO_VERDICT.values()) <= {OK, REFUSED, ERROR}, (
        "a verdict was mapped that harvest_run_outcome_ck would refuse"
    )
