"""The source-table writer, and the NFR-5 gates against real rows.

`tests/test_source_terms.py` exercises the gates against contract entries and
hand-built mappings. That proves the logic and not the wiring: a column that
does not round-trip, an evidence blob that comes back as strings, a NOT NULL
nobody can satisfy. All three are invisible until rows go through Postgres.

So this file inserts the fourteen and then asks the four gates to do their job
against what came back out. (Twelve until 2026-09-08, when arXiv and X were
ratified into `contract/sources.yaml`.)

    pwsh scripts/dev-postgres.ps1
    .venv\\Scripts\\python.exe -m pytest tests/test_source_load_db.py -q
"""

from __future__ import annotations

from datetime import date

import psycopg
import pytest

from collect.registry.assertions import TermsNotReviewedError, assert_terms_reviewed
from collect.registry.sources import (
    SourceProvenanceConflictError,
    load_source_rows,
    load_sources,
)
from tests.conftest import assert_disposable, assert_safe_target

REVIEWED_ON = date(2026, 8, 14)


@pytest.fixture
def conn(test_dsn):
    """A schema-fresh connection to a database proven safe to destroy."""
    from collect.db import apply_schema, connect

    assert_safe_target(test_dsn)
    connection = connect(test_dsn)
    try:
        assert_disposable(connection, test_dsn)
        connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        apply_schema(connection)
        connection.commit()
        yield connection
    finally:
        connection.rollback()
        connection.close()


def _rows(connection):
    from psycopg.rows import dict_row

    with connection.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM source ORDER BY id")
        return {row["id"]: row for row in cur.fetchall()}


# ── writing ───────────────────────────────────────────────────────────────


def test_every_source_row_lands(conn):
    """Twelve until 2026-09-08, then arXiv and X, then dev.to / HN / Hugging Face.

    THE PLATFORM SET IS ASSERTED AS A SET, not counted. A count passes on a
    file that lost `reddit` and gained two others, and a platform leaving the
    contract renders as an absence rather than as an error (rule 4).
    """
    report = load_source_rows(conn)
    assert (report.inserted, report.updated, report.unchanged) == (17, 0, 0)

    rows = _rows(conn)
    assert len(rows) == 17
    # THE SET, which the docstring says is the assertion that matters. A count
    # passes on a file that lost `reddit` and gained two others; this does not.
    assert {r["platform"] for r in rows.values()} == {
        "github", "blog", "reddit", "arxiv", "x",
        "devto", "hackernews", "huggingface",
    }
    assert sum(1 for r in rows.values() if r["platform"] == "blog") == 10  # 9 + umbrella


def test_a_second_load_changes_nothing(conn):
    """Idempotent, like load_seed. `source` is re-seeded on every ruling change.

    A loader that reported seventeen updates every time would make the one row
    that genuinely moved impossible to see in the report.
    """
    load_source_rows(conn)
    conn.commit()

    again = load_source_rows(conn)
    assert (again.inserted, again.updated, again.unchanged) == (0, 0, 17)
    assert again.changed_columns == {}


def test_a_changed_ruling_shows_up_as_one_updated_row(conn):
    load_source_rows(conn)
    conn.commit()
    conn.execute(
        "UPDATE source SET tos_notes = 'stale prose' WHERE id = 'blog:hamel.dev'"
    )
    conn.commit()

    report = load_source_rows(conn)
    assert (report.inserted, report.updated, report.unchanged) == (0, 1, 16)
    assert report.changed_columns == {"blog:hamel.dev": ["tos_notes"]}


def test_the_evidence_blob_round_trips(conn):
    """jsonb has no date type, so `checked_on` comes back as a string.

    The date that has to stay a date is the column, because that is what the
    staleness check reads.
    """
    load_source_rows(conn)
    row = _rows(conn)["blog:engineering.grab.com"]

    assert row["terms_checked_on"] == REVIEWED_ON
    assert row["terms_evidence"]["checked_on"] == "2026-08-14"
    assert row["terms_evidence"]["robots_status"] == "no-rules"
    assert row["terms_evidence"]["robots_http"] == 404


def test_harvest_state_survives_a_reseed(conn):
    """FR-10's yield history is the harvest's, not the contract's.

    Resetting it on a re-seed would look exactly like the source going quiet,
    which is the one thing the yield alert exists to detect.
    """
    load_source_rows(conn)
    conn.execute(
        "UPDATE source SET health_status = 'ok', last_yield = 7 "
        "WHERE id = 'blog:slack.engineering'"
    )
    conn.commit()

    load_source_rows(conn)
    row = _rows(conn)["blog:slack.engineering"]
    assert (row["health_status"], row["last_yield"]) == ("ok", 7)


# ── provenance ────────────────────────────────────────────────────────────


def test_a_reseed_refuses_to_overwrite_a_discovered_row(conn):
    """Task 2's shape in a new table, and here it refuses in both directions.

    A discovered feed carries a ruling made about its own host. A re-seed that
    replaced it with a class ruling made about somebody else is item 20: a
    value indistinguishable from a vetted one, deciding whether we may fetch.
    """
    load_source_rows(conn)
    conn.commit()
    conn.execute(
        "UPDATE source SET provenance = 'discovered' WHERE id = 'blog:jxnl.co'"
    )
    conn.commit()

    with pytest.raises(SourceProvenanceConflictError) as excinfo:
        load_source_rows(conn)

    message = str(excinfo.value)
    assert "blog:jxnl.co" in message
    assert "stored 'discovered', incoming 'seed'" in message
    assert "Reconcile them by hand" in message


def test_it_refuses_before_writing_anything(conn):
    """A partial load is worse than a refused one: half the table is stale."""
    conn.execute(
        "INSERT INTO source (id, platform, endpoint, base_trust, tos_notes, "
        "                    provenance, terms_ruling, terms_checked_on, terms_evidence) "
        "VALUES ('blog:hamel.dev', 'blog', 'https://hamel.dev/index.xml', 0.90, "
        "        'found by a link', 'discovered', 'blog-class-a-self-hosted', "
        "        DATE '2026-08-14', '{}'::jsonb)"
    )
    conn.commit()

    with pytest.raises(SourceProvenanceConflictError):
        load_source_rows(conn)
    conn.rollback()

    assert set(_rows(conn)) == {"blog:hamel.dev"}, "no other row was written"


def test_a_discovered_row_cannot_be_inserted_without_a_ruling(conn):
    """The schema carries this, because the writer never sees discovered rows.

    A feed that arrived by a link in harvested content has to bring a ruling
    made about its host. Only the hand-curated seed may record an honest
    "nobody has read these terms yet" — which is what `reddit` is.
    """
    with pytest.raises(psycopg.errors.CheckViolation, match="discovered_needs_ruling"):
        conn.execute(
            "INSERT INTO source (id, platform, endpoint, base_trust, tos_notes, provenance) "
            "VALUES ('blog:found.example', 'blog', 'https://found.example/feed', 0.90, "
            "        'no ruling', 'discovered')"
        )
    conn.rollback()


def test_every_platform_row_is_stored_with_its_ruling(conn):
    """Nothing is stored as unreviewed any more, and that is a change of state.

    `reddit` was the one honestly-unreviewed row — NULL ruling, NULL
    checked_on — until it was ruled on 2026-08-18. The mechanism that recorded
    it as unreviewed is unchanged and still asserted, in
    `test_an_unruled_row_is_stored_with_nulls_and_reported`; what moved is
    which rows are in that state.
    """
    report = load_source_rows(conn)
    assert report.unreviewed == []

    row = _rows(conn)["reddit"]
    assert row["terms_ruling"] == "reddit-via-rapidapi"
    assert row["terms_checked_on"] == date(2026, 8, 18)


def test_an_unruled_row_is_stored_with_nulls_and_reported(conn):
    """NULL, not a sentinel ruling. The row exists; the permission does not.

    The half of the previous test that was about the WRITER rather than about
    Reddit, kept on a synthetic row so it cannot go stale when a ruling lands.
    """
    from collect.registry.sources import SourcesContract

    synthetic = SourcesContract(
        version="test",
        review_marker="REVIEW REQUIRED",
        rulings={},
        platforms=[
            {
                "id": "unruled-x",
                "platform": "blog",
                "provenance": "seed",
                "base_trust": 0.5,
                # NOT NULL in the schema, which is NFR-5 enforcement: a source
                # cannot exist without somebody having written down its terms.
                "tos_notes": "REVIEW REQUIRED - synthetic row for this test",
            }
        ],
        feeds=[],
    )
    report = load_source_rows(conn, synthetic)
    assert report.unreviewed == ["unruled-x"]
    assert "cannot be harvested: unruled-x" in report.summary()

    row = _rows(conn)["unruled-x"]
    assert row["terms_ruling"] is None
    assert row["terms_checked_on"] is None


# ── the four gates, against rows rather than fixtures ─────────────────────


def test_gate_one_every_stored_feed_is_cleared_to_harvest(conn):
    """The nine, read back out of Postgres, pass the terms check."""
    contract = load_sources()
    load_source_rows(conn)
    stored = _rows(conn)

    feeds = [stored[feed["id"]] for feed in contract.feeds]
    observations = {
        row["id"]: {
            "endpoint_is_null": False,
            "robots_status": row["terms_evidence"]["robots_status"],
            "feed_path_allowed": True,
        }
        for row in feeds
    }
    assert_terms_reviewed(
        feeds,
        rulings=contract.rulings,
        observations=observations,
        today=REVIEWED_ON,
    )


def test_gate_two_the_stored_reddit_row_refuses_without_its_live_observation(conn):
    """It named no ruling until 2026-08-18 and refused for that.

    It now names one, and still refuses when the run supplies no observation
    for the basis that ruling rests on — which is the stronger check, because
    it is the one that keeps refusing after a permission exists.
    """
    load_source_rows(conn)
    row = _rows(conn)["reddit"]

    with pytest.raises(TermsNotReviewedError):
        assert_terms_reviewed([row], observations={}, today=date(2026, 8, 18))


def test_gate_three_the_stored_umbrella_row_refuses_as_a_fetch_target(conn, tmp_path):
    """It passes the terms check and is still not a thing you can fetch."""
    pytest.importorskip("feedparser", reason="the blog fetcher imports the parse path")

    import httpx

    # THE BLOG FETCH PATH NEEDS THE FEED LIBRARIES, and these two tests are
    # about the SOURCE GATE rather than about parsing anything - they only
    # reach `fetcher_for_source` to prove it refuses. Skipped rather than
    # failed when the parser is absent, for the reason
    # `tests/conftest.py:require_feed_libraries` gives: a missing optional
    # dependency should cost the tests that need it and nothing else.
    pytest.importorskip('trafilatura', reason='the blog fetch path needs it')
    from collect.adapters.blog.fetch import NotAFetchTargetError, fetcher_for_source
    from collect.adapters.blog.robots import RobotsGate
    from collect.http import build_client
    from collect.rawstore import RawStore

    load_source_rows(conn)
    row = _rows(conn)["blogs"]

    ua = "modelboard/0.1 (+https://modelboard.invalid/about)"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(404, content=b"")
    )
    with pytest.raises(NotAFetchTargetError, match="not a fetch target"):
        fetcher_for_source(
            row,
            client=build_client(user_agent=ua, transport=transport),
            store=RawStore(tmp_path / "raw_store"),
            robots=RobotsGate(
                build_client(user_agent=ua, transport=transport), user_agent=ua
            ),
        )


def test_gate_four_a_stored_medium_row_permits_the_feed_and_refuses_articles(
    conn, tmp_path
):
    """The class B ruling, carried from Postgres into the fetcher's behaviour."""
    pytest.importorskip("feedparser", reason="the blog fetcher imports the parse path")

    import httpx

    pytest.importorskip('trafilatura', reason='the blog fetch path needs it')
    from collect.adapters.blog.fetch import FeedOnlyError, fetcher_for_source
    from collect.adapters.blog.robots import RobotsGate
    from collect.http import build_client
    from collect.rawstore import RawStore

    load_source_rows(conn)
    row = _rows(conn)["blog:netflixtechblog.com"]

    ua = "modelboard/0.1 (+https://modelboard.invalid/about)"
    feed = (tmp_path / "feed.xml")
    feed.write_bytes(b"<rss version='2.0'><channel><title>t</title></channel></rss>")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, content=b"User-agent: *\nAllow: /\n")
        return httpx.Response(
            200,
            content=feed.read_bytes(),
            headers={"content-type": "application/rss+xml"},
        )

    transport = httpx.MockTransport(handler)
    fetcher = fetcher_for_source(
        row,
        client=build_client(user_agent=ua, transport=transport),
        store=RawStore(tmp_path / "raw_store"),
        robots=RobotsGate(
            build_client(user_agent=ua, transport=transport), user_agent=ua
        ),
    )

    # The feed is permitted...
    run = fetcher.harvest_feed("https://netflixtechblog.com/feed")
    assert run.outcome == "fetched"
    assert run.articles == []

    # ... and the article path is not, however politely it is asked for.
    with pytest.raises(FeedOnlyError, match="Do not work around it"):
        fetcher.harvest_feed("https://netflixtechblog.com/feed", fetch_articles=True)


def test_the_report_names_its_denominator_and_any_skip(conn):
    """A loader that reports only what it wrote cannot prove it wrote everything.

    `12 inserted` reads as complete whether the contract held 12 entries or 14 —
    the same shape as a comparison that finds no rows and reports no differences.
    So the report carries entries READ against rows WRITTEN, with the denominator
    counted from the contract's own sections rather than from `source_rows()`:
    `len(rows)` against `len(rows)` is a check that cannot fail.
    """
    from collect.registry.sources import load_source_rows, load_sources

    contract = load_sources()
    report = load_source_rows(conn, contract)

    expected = len(contract.platforms) + len(contract.feeds)
    assert report.declared == expected
    assert report.total == expected, "every declared entry reached a row"
    assert report.skipped == []
    assert f"{report.total} of {report.declared} contract entries" in report.summary()

    # github and reddit specifically, because both are API sources and the worry
    # was that a required `endpoint` had dropped them. `endpoint` is nullable and
    # `_source_row` reads every column with `.get()`, so nothing can be dropped
    # for a missing field — but the row that PROVES the nullable path is `blogs`,
    # which declares no endpoint and loads.
    landed = {r[0]: r[1] for r in conn.execute("SELECT id, endpoint FROM source").fetchall()}
    assert "github" in landed and "reddit" in landed
    assert landed["blogs"] is None, "the endpoint-less platform row still lands"


def test_a_contract_entry_that_never_reaches_a_row_is_named(conn):
    """The skip path, exercised by making one — since nothing skips today.

    A guard that has never fired is a guard nobody has seen work.
    """
    from collect.registry.sources import load_source_rows, load_sources

    contract = load_sources()
    full = contract.source_rows()
    dropped = {"github", "reddit"}

    class Filtered:
        """A contract whose row builder omits two declared entries.

        This is the future defect, made present: a filter, a parse that gives up
        on an entry, a field requirement that excludes an API source with no feed
        URL. The point is that the report says so instead of counting what
        survived.
        """

        platforms = contract.platforms
        feeds = contract.feeds

        def source_rows(self):
            return [row for row in full if row["id"] not in dropped]

    report = load_source_rows(conn, Filtered())

    assert report.declared == len(contract.platforms) + len(contract.feeds)
    assert report.total == report.declared - 2
    assert sorted(report.skipped) == ["github", "reddit"]

    summary = report.summary()
    assert f"{report.total} of {report.declared}" in summary
    assert "SKIPPED" in summary and "github" in summary and "reddit" in summary
    assert "harvest_run.source_id" in summary, (
        "the skip has to say what it costs — a source with no row cannot carry a "
        "harvest run, which is the blocker this loader was built to remove"
    )
