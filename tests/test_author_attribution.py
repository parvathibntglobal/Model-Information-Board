"""`document.author_id` on Reddit and GitHub — the three things that must hold.

Until 2026-08-21 `collect/adapters/blog/write.py` was the only module in the
repository that set this column: 30 of 64 documents had an author, all blog, and
`author` held ONE row. `judge/curate/gate.py:count` dedups voices off
`claim.author_id`, so a NULL there is not an unknown author — it is no voice —
and every cell read `insufficient` on a corpus of one voice.

Each test here is a failure that has a name and a precedent:

  1. IDS CANONICALISE. `getProfile` returns `2ii4xgakc7` where a post carries
     `t2_2ii4xgakc7`. Taken verbatim, that is two `author` rows for one person:
     a split voice that FR-17 counts twice while believing it counts once.
     GitHub's equivalent is keying on `user.id` rather than the renameable
     `user.login`, which the adapter used to be the only thing it kept.
  2. THE HANDLE IS NOT RETAINED. Only its digest. Data minimisation, so the
     handle cannot be read out of a row, logged, or published by a query that
     forgot a column.
  3. NO AUTHOR MEANS NO ROW, never a shared one. Corpus-wide 115 Reddit
     documents have no `author_fullname`; one shared row or sentinel id would
     merge 115 absences into a single voice that then corroborates itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from collect.adapters.github import github_author_id
from collect.adapters.reddit_write import (
    REDDIT_PROVENANCE,
    author_id_for,
    document_row,
    write_documents,
)
from collect.assemble.authors import AuthorRow, from_github, from_reddit, hash_handle

#: These fakes stand in for a subreddit LISTING - no query was rendered, so a
#: NULL harvest_run_id is complete. Typed rather than defaulted: the writer now
#: refuses to guess, which is the point of the 2026-08-28 change.
LISTING = "no_run_for_source"


@dataclass(frozen=True)
class FakeComment:
    """Enough of `RedditComment` to attribute. Not the real type on purpose —
    these tests are about the attribution rule, not about parsing."""

    external_id: str = "t1_abc"
    parent_id: str = "t3_root"
    thread_root_id: str = "t3_root"
    url: str = "https://reddit.com/r/x/comments/root/_/abc"
    body: str = "it broke at 6 tools"
    author: str | None = "someone"
    author_fullname: str | None = "t2_2ii4xgakc7"
    subreddit: str = "LocalLLaMA"
    created_utc: float | None = None
    score: int | None = 3
    depth: int | None = 1
    controversiality: int | None = 0
    distinguished: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class FakeCursor:
    """Records the statements a write path issues, so ordering is assertable."""

    def __init__(self, calls):
        self.calls = calls
        self.rowcount = 0

    def executemany(self, sql, params):
        self.calls.append((sql.strip(), list(params)))
        self.rowcount = len(list(params))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeConn:
    def __init__(self):
        self.calls = []

    def cursor(self):
        return FakeCursor(self.calls)


@dataclass(frozen=True)
class FakeHit:
    author: str | None = "Simon"
    author_external_id: str | None = "45689065"


class TestIdsCanonicalise:
    def test_reddit_prefixed_and_bare_are_one_author(self):
        """`t2_abc` from a post and `abc` from getProfile are one engineer.

        `author` is UNIQUE (source, external_id), so two spellings taken
        verbatim are two rows — a voice split in half, counted twice.
        """
        prefixed = author_id_for(FakeComment(author_fullname="t2_2ii4xgakc7"))
        bare = author_id_for(FakeComment(author_fullname="2ii4xgakc7"))
        assert prefixed == bare
        assert prefixed is not None

    def test_reddit_rows_carry_the_prefixed_form(self):
        """One canonical spelling in the table, not whichever arrived first."""
        rows = from_reddit([FakeComment(author_fullname="2ii4xgakc7")]).rows
        assert [r.external_id for r in rows] == ["t2_2ii4xgakc7"]

    def test_a_rename_does_not_create_a_second_author(self):
        """The handle moves, the account id does not."""
        before = author_id_for(FakeComment(author="oldname"))
        after = author_id_for(FakeComment(author="newname"))
        assert before == after

    def test_github_keys_on_the_numeric_id_not_the_login(self):
        """`user.login` alone is the failure `t2_` exists to prevent."""
        renamed = github_author_id(FakeHit(author="renamed", author_external_id="45689065"))
        original = github_author_id(FakeHit(author="Simon", author_external_id="45689065"))
        assert renamed == original

        reused_login = github_author_id(FakeHit(author="Simon", author_external_id="999"))
        assert reused_login != original, (
            "two accounts sharing a login must stay two authors"
        )

    def test_the_two_platforms_do_not_collide(self):
        """Same digits on both platforms are two people, not one."""
        assert github_author_id(FakeHit(author_external_id="2ii4xgakc7")) != author_id_for(
            FakeComment(author_fullname="t2_2ii4xgakc7")
        )


class TestTheHandleIsNotRetained:
    def test_the_row_holds_no_field_equal_to_the_handle(self):
        handle = "a-very-distinctive-handle"
        row = AuthorRow(source="reddit", external_id="t2_x", handle_hash=hash_handle(handle))
        serialised = row.as_row()
        assert handle not in {
            v for v in serialised.values() if isinstance(v, str)
        }
        assert handle.casefold() not in repr(serialised).casefold()

    def test_the_digest_is_present_and_is_not_the_handle(self):
        row = from_reddit([FakeComment(author="someone")]).rows[0]
        assert row.handle_hash
        assert row.handle_hash != "someone"

    def test_a_case_only_rename_is_one_digest(self):
        assert hash_handle("SomeOne") == hash_handle("someone")

    def test_the_document_row_carries_no_handle_either(self):
        row = document_row(
            FakeComment(author="a-very-distinctive-handle"), retrieval_provenance=LISTING
        )
        assert "a-very-distinctive-handle" not in repr(row)
        assert row["author_id"] is not None


class TestNoAuthorMeansNoRow:
    def test_a_comment_without_a_fullname_gets_no_author_id(self):
        assert author_id_for(FakeComment(author_fullname=None, author="[deleted]")) is None

    def test_a_placeholder_handle_is_not_hashed(self):
        """Hashing `[deleted]` would give every deleted account ONE digest —
        the shared-value collision arriving by another door."""
        for marker in ("[deleted]", "[removed]", "[unavailable]"):
            assert hash_handle(marker) is None

    def test_many_authorless_comments_produce_no_author_rows_at_all(self):
        """The arithmetic that matters: 115 absences must not become one voice."""
        items = [
            FakeComment(external_id=f"t1_{i}", author_fullname=None, author="[deleted]")
            for i in range(115)
        ]
        extraction = from_reddit(items)
        assert extraction.rows == []
        assert extraction.distinct_authors == 0
        assert extraction.unattributable == 115

        rows = [document_row(c, retrieval_provenance=LISTING) for c in items]
        assert all(r["author_id"] is None for r in rows)
        assert len({r["author_id"] for r in rows}) == 1  # all None, no shared id

    def test_github_deleted_account_gets_no_author_id(self):
        assert github_author_id(FakeHit(author_external_id=None, author=None)) is None

    def test_github_counts_the_unattributable_rather_than_dropping_them(self):
        extraction = from_github([
            FakeHit(author_external_id=None),
            FakeHit(author_external_id="45689065"),
        ])
        assert extraction.unattributable == 1
        assert extraction.distinct_authors == 1

    def test_authorless_documents_do_not_share_a_row_across_platforms(self):
        assert author_id_for(FakeComment(author_fullname=None)) is None
        assert github_author_id(FakeHit(author_external_id=None)) is None


class TestTheDocumentRow:
    def test_a_comment_carries_its_thread_and_parent(self):
        """Discriminated on the fields. An earlier `isinstance(item,
        RedditComment)` wrote NULL linkage for anything of another type."""
        row = document_row(FakeComment(), retrieval_provenance=LISTING)
        assert row["thread_root_id"] == "t3_root"
        assert row["parent_id"] == "t3_root"
        assert row["source"] == "reddit"
        assert row["id"] == "reddit:t1_abc"

    def test_absent_refs_stay_null_rather_than_becoming_empty_strings(self):
        row = document_row(FakeComment(), retrieval_provenance=LISTING)
        assert row["text_ref"] is None
        assert row["content_hash"] is None

    def test_a_post_has_no_parent_because_it_is_its_own_root(self):
        """A self-reference would make "is this a root" unanswerable."""

        @dataclass(frozen=True)
        class FakePost:
            external_id: str = "t3_root"
            url: str = "https://reddit.com/r/x/comments/root/"
            author: str | None = "someone"
            author_fullname: str | None = "t2_2ii4xgakc7"

        row = document_row(FakePost(), retrieval_provenance=LISTING)
        assert row["thread_root_id"] is None
        assert row["parent_id"] is None
        assert row["author_id"] is not None


class TestAnExistingRowStillGetsItsAuthor:
    """`ON CONFLICT DO NOTHING` is right for every column except this one.

    Measured on the first real run: 196 items, 190 inserted, and the 6 that
    conflicted away kept `author_id` NULL — permanently, however often the sweep
    re-ran, because a silent conflict looks exactly like a successful write.
    """

    def test_write_documents_updates_the_author_on_a_conflicting_row(self):
        conn = FakeConn()
        items = [FakeComment(external_id="t1_a"), FakeComment(external_id="t1_b")]
        counts = write_documents(conn, items, retrieval_provenance=LISTING)

        updates = [sql for sql, _ in conn.calls if sql.startswith("UPDATE document")]
        assert updates, "an existing row must still get its author_id"
        assert counts["documents_seen"] == 2

    def test_the_update_never_overwrites_an_attribution(self):
        """A later, possibly worse, parse must not replace a real author."""
        from collect.adapters.reddit_write import _SET_AUTHOR

        assert "author_id IS NULL" in _SET_AUTHOR

    def test_an_authorless_item_is_not_in_the_update_batch(self):
        conn = FakeConn()
        write_documents(conn, [FakeComment(external_id="t1_x", author_fullname=None)],
                        retrieval_provenance=LISTING)
        for sql, params in conn.calls:
            if sql.startswith("UPDATE document"):
                assert params == [], "nothing to attribute, so nothing to update"


class TestRetrievalProvenanceIsTheCallersClaim:
    """The writer refuses to guess which run produced a row.

    `no_run_for_source` was typed into the INSERT for every caller, and the
    per-model fetch's Reddit arm - which issues model-name QUERIES through this
    same writer - wrote 853 rows asserting there had been nothing to record.
    A positive claim that nothing was missing, on rows where something was.
    """

    def test_an_unknown_value_raises_here_rather_than_at_the_check(self):
        with pytest.raises(ValueError) as excinfo:
            document_row(FakeComment(), retrieval_provenance="probably_fine")
        # The message must name the CALLER's problem, not the constraint. A
        # 23514 from Postgres names `document_retrieval_provenance_ck`, which
        # tells whoever reads the traceback nothing about what to pass.
        assert "retrieval_provenance" in str(excinfo.value)
        assert "claim about the RUN" in str(excinfo.value)

    def test_run_recorded_without_an_id_is_refused(self):
        """The `..._agrees_ck` pairing, mirrored so the error names the caller.

        `run_recorded` was deliberately ABSENT from `REDDIT_PROVENANCE` until
        2026-08-28, on the grounds that this writer set no id. Then
        `ops/sweep_reddit.py` started opening a `harvest_run` row per subreddit
        and carrying its id, at which point the value became not merely allowed
        but REQUIRED - the constraint enforces it the moment the id is set.
        """
        with pytest.raises(ValueError) as excinfo:
            document_row(FakeComment(), retrieval_provenance="run_recorded")
        assert "harvest_run_id" in str(excinfo.value)
        assert "agrees_ck" in str(excinfo.value)

    def test_an_id_without_run_recorded_is_refused_too(self):
        """The other direction, which is the one that would have shipped.

        A row carrying an id under `no_run_for_source` claims both that a run
        exists and that there was none to record. Postgres refuses it as a
        23514; this refuses it by name.
        """
        for value in (v for v in REDDIT_PROVENANCE if v != "run_recorded"):
            with pytest.raises(ValueError):
                document_row(
                    FakeComment(), retrieval_provenance=value, harvest_run_id="hr_x"
                )

    def test_the_value_reaches_the_row_rather_than_being_reinterpreted(self):
        for value in REDDIT_PROVENANCE:
            row = document_row(
                FakeComment(),
                retrieval_provenance=value,
                harvest_run_id="hr_x" if value == "run_recorded" else None,
            )
            assert row["retrieval_provenance"] == value

    def test_the_id_reaches_the_row(self):
        row = document_row(
            FakeComment(), retrieval_provenance="run_recorded", harvest_run_id="hr_abc"
        )
        assert row["harvest_run_id"] == "hr_abc"

    def test_every_permitted_value_is_in_the_schema_check(self):
        """The tuple and the CHECK must not drift apart."""
        from collect.config import CONTRACT_DIR

        ddl = (CONTRACT_DIR / "tables.sql").read_text(encoding="utf-8")
        start = ddl.index("document_retrieval_provenance_ck")
        clause = ddl[start:start + 400]
        for value in REDDIT_PROVENANCE:
            assert f"'{value}'" in clause, f"{value} is writable and not in the CHECK"
