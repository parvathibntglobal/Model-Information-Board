"""`author` rows — FR-17's precondition, not FR-17.

Three tests carry the weight, and all three come from things the corpus actually
contains rather than from cases I invented:

  the deleted accounts   three comments in the fixture thread have no
                         `author_fullname`, and they must not become one voice
  the handle             needed transiently, retained nowhere
  the stable id          GitHub hands over `user.id`, which survives a rename,
                         and the adapter was throwing it away
"""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

import pytest

from collect.assemble.authors import (
    AuthorRow,
    from_github,
    from_reddit,
    hash_handle,
    overlap_by_handle,
)

FIXTURE = (Path(__file__).resolve().parents[1]
           / "fixtures" / "reddit" / "thread-1u1b22l-getPostComments.json")


class Hit:
    """A SearchHit's author-relevant surface."""

    def __init__(self, author, author_external_id):
        self.author = author
        self.author_external_id = author_external_id


class Item:
    """A RedditPost or RedditComment's author-relevant surface."""

    def __init__(self, author, author_fullname):
        self.author = author
        self.author_fullname = author_fullname


@pytest.fixture(scope="module")
def thread_comments():
    from collect.adapters.reddit_comments import parse_thread

    payload = json.loads(FIXTURE.read_bytes())
    return parse_thread(payload, url="https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/")


# ── the deleted accounts, from the real fixture ──────────────────────────


def test_the_fixture_really_contains_authorless_comments(thread_comments):
    """Guards the premise. If the fixture changes, the next test means nothing."""
    missing = [c for c in thread_comments.comments if not c.author_fullname]
    assert len(missing) == 3, "three deleted accounts in this thread"


def test_authorless_comments_get_no_row_and_do_not_collapse(thread_comments):
    """The failure this exists to prevent.

    `author` is UNIQUE (source, external_id). A NULL id cannot be inserted and a
    sentinel would give every deleted account the SAME row — so three gone
    accounts would become one voice, and FR-17 would count that voice
    corroborating itself.
    """
    result = from_reddit(thread_comments.comments)
    assert result.unattributable == 3
    assert all(r.external_id for r in result.rows)
    assert len({r.external_id for r in result.rows}) == result.distinct_authors
    assert "no stable author id" in result.describe()


def test_a_placeholder_handle_is_treated_as_absent_not_hashed():
    """`[deleted]` is a marker, not somebody's name.

    Hashing it would give every such author the SAME `handle_hash` — the
    shared-value collision this module refuses for a missing handle, arriving by
    another door. Caught by a test that was checking something weaker.
    """
    for placeholder in ("[deleted]", "[removed]", "[UNAVAILABLE]"):
        assert hash_handle(placeholder) is None

    result = from_reddit([Item("[deleted]", "t2_gone"), Item("alice", "t2_a")])
    by_id = {r.external_id: r for r in result.rows}
    assert by_id["t2_gone"].handle_hash is None, "no row shares a placeholder hash"
    assert by_id["t2_a"].handle_hash is not None
    assert result.distinct_handles == 1, "the placeholder is not a handle"


# ── the handle is retained nowhere ───────────────────────────────────────


def test_no_field_on_the_row_holds_the_handle():
    """Structural, not a code reading. A future field called `author` would fail."""
    names = {f.name for f in fields(AuthorRow)}
    assert "handle" not in names
    assert "author" not in names
    assert "login" not in names
    assert "username" not in names
    assert "handle_hash" in names


def test_the_written_row_contains_no_handle():
    row = AuthorRow(source="github", external_id="45689065",
                    handle_hash=hash_handle("lawong888"))
    written = row.as_row()
    assert "lawong888" not in json_dump(written)
    assert written["handle_hash"] == hash_handle("lawong888")


def json_dump(value) -> str:
    return json.dumps(value, default=str)


def test_the_extraction_reports_a_count_of_handles_not_the_handles():
    result = from_github([Hit("alice", "1"), Hit("bob", "2"), Hit("ALICE", "3")])
    assert result.distinct_handles == 2, "casefolded"
    assert "alice" not in json_dump([r.as_row() for r in result.rows])


def test_hashing_is_casefolded_so_a_case_rename_is_one_author():
    assert hash_handle("Alice") == hash_handle("alice") == hash_handle(" alice ")


def test_a_missing_handle_hashes_to_none_not_to_a_shared_value():
    """Every handle-less author would otherwise share one hash."""
    assert hash_handle(None) is None
    assert hash_handle("") is None
    assert hash_handle("   ") is None


# ── the stable ids ───────────────────────────────────────────────────────


def test_github_uses_the_numeric_account_id_not_the_login():
    """`user.id` survives a rename; `login` does not.

    A renamed account would otherwise arrive as a new author, and a reused name
    would merge two people — the second being the over-clustering
    `collect/CLAUDE.md` calls worse.
    """
    result = from_github([Hit("oldname", "45689065")])
    assert result.rows[0].external_id == "45689065"


def test_a_github_rename_is_the_same_author():
    """The property the numeric id buys, asserted directly."""
    before = from_github([Hit("oldname", "45689065")]).rows[0]
    after = from_github([Hit("newname", "45689065")]).rows[0]
    assert before.external_id == after.external_id
    assert before.id == after.id, "the same author row"
    assert before.handle_hash != after.handle_hash, "and a visibly changed handle"


def test_a_github_hit_with_no_user_gets_no_row():
    result = from_github([Hit(None, None), Hit("alice", "7")])
    assert result.unattributable == 1
    assert len(result.rows) == 1


def test_reddit_ids_are_canonicalised_through_the_t2_form():
    """`t2_abc` and `abc` are one author. Two rows would split a voice."""
    result = from_reddit([Item("alice", "t2_abc"), Item("alice", "abc")])
    assert result.distinct_authors == 1
    assert result.rows[0].external_id == "t2_abc"


def test_the_two_platforms_never_share_a_row_by_accident():
    """A numeric GitHub id and a `t2_` id cannot collide, and `source` separates
    them anyway — so an overlap found later is a real finding rather than a
    key clash."""
    rows = from_github([Hit("x", "45689065")]).rows + from_reddit(
        [Item("x", "t2_45689065")]).rows
    assert len({(r.source, r.external_id) for r in rows}) == 2
    assert len({r.id for r in rows}) == 2


# ── FR-17 is not built, and the row says so ──────────────────────────────


def test_identity_cluster_id_is_always_none():
    """NULL means not clustered, never clustered alone.

    FR-17 has no observed case in this corpus, so nothing here clusters. Writing a
    cluster id per author would make every author look resolved into a singleton
    cluster, which is a claim rather than an absence.
    """
    rows = from_github([Hit("a", "1")]).rows + from_reddit([Item("b", "t2_b")]).rows
    assert all(r.identity_cluster_id is None for r in rows)
    assert all(r.as_row()["identity_cluster_id"] is None for r in rows)


def test_overlap_is_a_measurement_and_stores_nothing():
    """It answers "does FR-17 have anything to match", not "is this one person".

    `jsmith` on both platforms is two people far more often than one, so the
    result feeds a decision rather than a merge.
    """
    shared = overlap_by_handle({"alice", "bob"}, {"alice", "carol"})
    assert shared == {"alice"}
    assert overlap_by_handle(set(), {"alice"}) == set()


def test_deduplication_is_by_source_and_external_id():
    result = from_reddit([Item("a", "t2_x"), Item("a", "t2_x"), Item("b", "t2_y")])
    assert result.distinct_authors == 2
    assert len(result.rows) == 2


# ── blogs: the unit is the feed, not the article ──────────────────────────


class TestFromBlog:
    """`blog/write.py` wrote no author on a recorded reason, and the reason was
    about per-ARTICLE rows. The contract already rules this per FEED, in
    `contract/sources.yaml` under `measured` — so these cases are the contract's,
    not a judgement made here."""

    def test_a_feed_declared_byline_is_one_voice_however_many_articles(self):
        from collect.assemble.authors import from_blog

        feed = {
            "id": "blog:simonwillison.net",
            "measured": {
                "byline_source": "feed_declared",
                "declared_author": "Simon Willison",
                "resolves_to_voices": 1,
            },
        }
        extraction = from_blog(feed, entries=[object()] * 30)

        assert len(extraction.rows) == 1, (
            "thirty articles from one byline is ONE voice; a row per article is "
            "the inflation the write path refused and was right to refuse"
        )
        row = extraction.rows[0]
        assert row.source == "blog"
        assert row.external_id == "blog:simonwillison.net"
        assert row.handle_hash and "Simon Willison" not in row.handle_hash, (
            "the digest is stored and the name is not, exactly as for Reddit"
        )

    def test_a_team_byline_is_also_one_voice(self):
        from collect.assemble.authors import from_blog

        extraction = from_blog({
            "id": "blog:netflixtechblog.com",
            "measured": {"byline_source": "team",
                         "declared_author": "Netflix Technology Blog",
                         "resolves_to_voices": 1},
        })
        assert len(extraction.rows) == 1

    def test_no_byline_writes_no_row_rather_than_an_anonymous_one(self):
        from collect.assemble.authors import from_blog

        extraction = from_blog({
            "id": "blog:vickiboykis.com",
            "measured": {"byline_source": "none", "resolves_to_voices": None},
        })
        assert extraction.rows == [], (
            "NULL author_id is unknown; a shared anonymous row would make every "
            "unattributed article one voice and inflate n_eff"
        )

    def test_an_entry_byline_feed_yields_one_row_per_distinct_author(self):
        from collect.assemble.authors import from_blog

        class E:
            def __init__(self, author):
                self.author = author

        extraction = from_blog(
            {"id": "blog:slack.engineering",
             "measured": {"byline_source": "entry", "resolves_to_voices": 7}},
            entries=[E("A Dev"), E("B Dev"), E("A Dev"), E(None), E("  ")],
        )
        assert len(extraction.rows) == 2, "deduplicated, and blanks are not authors"
        assert {r.external_id for r in extraction.rows} == {
            "blog:slack.engineering#A Dev", "blog:slack.engineering#B Dev"
        }

    def test_a_declared_byline_with_no_name_is_unattributable_not_invented(self):
        from collect.assemble.authors import from_blog

        extraction = from_blog({
            "id": "blog:example.com",
            "measured": {"byline_source": "feed_declared", "resolves_to_voices": 1},
        })
        assert extraction.rows == []
        assert extraction.unattributable == 1, (
            "the contract says the byline is the feed's and does not say whose; "
            "counted rather than given a row with no identity"
        )
