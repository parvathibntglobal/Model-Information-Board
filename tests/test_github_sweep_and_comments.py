"""The multi-shape sweep, the comment write path, and the third assembly shape.

DB-BACKED WHERE IT WRITES. `test_dsn`, so with no database these FAIL rather
than skip — the convention `collect/` paid six defects to establish.

THREE PROPERTIES CARRY MOST OF THIS

    the sweep runs SHAPES, not a shape     title n repro is 9 of 188, so a
                                           second arm roughly doubles unique
                                           documents rather than re-finding
                                           the first arm's
    a bot is not a voice                   github-actions[bot] is the busiest
                                           commenter in the corpus and nothing
                                           filtered bots anywhere
    an assembled thread says what it did   observed / hidden, so coverage_ratio
                                           NOT read distinguishes a thread we read from one
                                           we sampled
"""

from __future__ import annotations

import psycopg
import pytest

from collect.adapters.github import DOCUMENT_SOURCE, StoredComment
from collect.adapters.queries.github import (
    REFUSED_SHAPES,
    SWEEP_SHAPES,
    RefusedShape,
    sweep_cost,
    sweep_requests,
)


def a_comment(
    n: int,
    *,
    issue_api_url: str = "https://api.github.com/repos/o/r/issues/1",
    handle: str = "alice",
    external_id: str | int | None = 4242,
    author_type: str = "User",
    body: str = "same here on 4.8, tool calls drop the second argument",
) -> StoredComment:
    return StoredComment(
        external_id=f"gh-comment:{n}",
        issue_api_url=issue_api_url,
        html_url=f"https://github.com/o/r/issues/1#issuecomment-{n}",
        author_handle=handle,
        author_external_id=str(external_id) if external_id is not None else None,
        author_type=author_type,
        created_at="2026-08-20T10:00:00Z",
        body=body,
        ref=f"raw/sha256/aa/bb/{n:064d}",
        content_hash=f"{n:064d}",
        already_present=False,
    )


class TestTheSweepRunsSeveralShapes:
    def test_shape_major_so_a_truncated_run_loses_the_weakest_arm(self):
        """A run cut off at request 4 of 6 must have title on every model.

        Surface-major would give title+repro for the first two models and
        nothing for the third — losing both arms on a third of the registry
        instead of the weakest arm on all of it.
        """
        planned = sweep_requests(["alpha-1", "beta-2", "gamma-3"], budget=4)
        assert [r.shape for r in planned] == ["title", "title", "title", "repro"]
        assert {r.surface for r in planned if r.shape == "title"} == {
            "alpha-1", "beta-2", "gamma-3"
        }

    def test_the_two_arms_render_different_queries_for_one_surface(self):
        planned = sweep_requests(["claude-sonnet-4.5"])
        queries = {r.shape: r.query for r in planned}
        assert queries["title"] == '"claude-sonnet-4.5" in:title type:issue'
        assert queries["repro"] == '"claude-sonnet-4.5" traceback type:issue'

    def test_shapes_are_ordered_by_the_ranking_whatever_order_they_arrive_in(self):
        planned = sweep_requests(["a-1"], shapes=("repro", "title"))
        assert [r.shape for r in planned] == ["title", "repro"]

    def test_a_duplicate_query_is_issued_once(self):
        """`github_alias_form` collapses spacing, so two surfaces can collide.

        Issuing it twice spends a request from a 30-per-minute bucket to fetch
        the same hundred candidates.
        """
        planned = sweep_requests(["gpt-5.2", "gpt-5.2"], shapes=("title",))
        assert len(planned) == 1

    def test_rank_is_contiguous_so_a_truncated_run_can_say_how_far_it_got(self):
        planned = sweep_requests(["a-1", "b-2"], shapes=("title", "repro"))
        assert [r.rank for r in planned] == [0, 1, 2, 3]


class TestLabelIsRefusedAndSaysWhy:
    def test_asking_for_label_raises_rather_than_filtering_silently(self):
        """Dropping it quietly would let a sweep report coverage it never tried."""
        with pytest.raises(RefusedShape) as exc:
            sweep_requests(["a-1"], shapes=("title", "label"))
        assert exc.value.shape == "label"

    def test_the_refusal_names_both_reasons_and_not_only_the_arithmetic(self):
        """9.7 unique per request is the weakest of the three arguments.

        The two that matter are that structural qualifiers measured as doing
        nothing at max_pages=1, and that label:bug narrows toward complaints —
        which makes the positive half of the silent-failure capabilities
        structurally unreachable. That is rule 4 arriving through the query, and
        a refusal citing only the yield would be re-argued the first time
        somebody wanted more documents.
        """
        reason = REFUSED_SHAPES["label"]
        assert "9.7" in reason and "UNIQUE" in reason
        assert "3.65x" in reason and "IDENTICAL 100 ids" in reason
        assert "POSITIVE" in reason and "unreachable" in reason

    def test_the_refusal_does_not_overclaim_what_was_measured(self):
        """`is:issue state:open` was measured; `label:` was not.

        Saying label WILL reproduce the null would be a figure answering a
        question it was not asked — the qualifier tested is not this one.
        """
        reason = REFUSED_SHAPES["label"]
        assert "not strictly covered" in reason
        assert "most likely to reproduce" in reason

    def test_signal_is_refused_too_and_for_its_own_reason(self):
        assert "0" in REFUSED_SHAPES["signal"] or "ZERO" in REFUSED_SHAPES["signal"]
        assert "sieve question" in REFUSED_SHAPES["signal"]
        with pytest.raises(RefusedShape):
            sweep_requests(["a-1"], shapes=("signal",))

    def test_label_is_not_in_the_shapes_a_sweep_runs(self):
        assert "label" not in SWEEP_SHAPES
        assert "signal" not in SWEEP_SHAPES

    def test_costing_a_refused_shape_refuses_too(self):
        """Otherwise a plan could be priced that can never be issued."""
        with pytest.raises(RefusedShape):
            sweep_cost(30, shapes=("title", "label"))


class TestWhatTheSweepCosts:
    def test_requests_scale_with_models_times_shapes(self):
        assert sweep_cost(11, shapes=("title",)).requests == 11
        assert sweep_cost(11, shapes=("title", "repro")).requests == 22
        assert sweep_cost(342, shapes=("title", "repro")).requests == 684

    def test_minutes_come_from_the_measured_bucket_not_a_guess(self):
        """30/minute, from GET /rate_limit and recorded in the adapter."""
        cost = sweep_cost(342, shapes=("title", "repro"))
        assert cost.minutes == pytest.approx(684 / 30)

    def test_surfaces_per_model_is_a_float_because_it_is_an_average(self):
        """Rounding it to an int understates exactly the models with most aliases."""
        assert sweep_cost(10, shapes=("title",), surfaces_per_model=1.5).requests == 15


class TestABotIsNotAVoice:
    def test_user_type_decides_and_not_the_handle(self):
        """The API declares it; the suffix is a string a human can choose."""
        assert a_comment(1, handle="github-actions[bot]", author_type="Bot").is_bot
        assert not a_comment(2, handle="releasebot", author_type="User").is_bot
        assert not a_comment(3, handle="alice", author_type="User").is_bot

    def test_a_missing_user_type_is_not_a_bot(self):
        """Absent is not True. A payload with no user is a deleted account."""
        assert not a_comment(4, author_type=None).is_bot

    def test_the_suffix_disagreeing_with_the_field_is_counted(self):
        """Zero on the 148 measured, and the only thing that would tell us the
        heuristic and the field have diverged."""
        assert a_comment(5, handle="notabot", author_type="Bot").bot_suffix_disagrees
        assert a_comment(6, handle="x[bot]", author_type="User").bot_suffix_disagrees
        assert not a_comment(7, handle="x[bot]", author_type="Bot").bot_suffix_disagrees
        assert not a_comment(8, handle="alice", author_type="User").bot_suffix_disagrees


@pytest.fixture
def conn(test_dsn):
    from pathlib import Path

    schema = (
        Path(__file__).resolve().parent.parent / "contract" / "tables.sql"
    ).read_text(encoding="utf-8")
    with psycopg.connect(test_dsn, connect_timeout=10) as connection:
        connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
        connection.execute("CREATE SCHEMA public")
        connection.execute(schema)
        connection.commit()
        yield connection


@pytest.fixture
def with_issue(conn):
    """One issue document for comments to hang off."""
    conn.execute(
        "INSERT INTO document (id, source, external_id, url, fetched_at, text_ref, "
        "content_hash, status) VALUES (%s,%s,%s,%s,now(),%s,%s,'kept')",
        ("doc_issue", DOCUMENT_SOURCE, "gh-issue:1",
         "https://github.com/o/r/issues/1", "raw/x", "h1"),
    )
    conn.commit()
    return conn


API_URL = "https://api.github.com/repos/o/r/issues/1"
BY_URL = {API_URL: "doc_issue"}


class TestTheCommentWritePath:
    def _harvester(self):
        from collect.adapters.github import GitHubHarvester

        return GitHubHarvester.__new__(GitHubHarvester)

    def test_a_human_comment_becomes_a_kept_document_with_an_author(self, with_issue):
        """148 comments were fetched and nothing stored them. This is the close."""
        counts = self._harvester().write_comments(
            with_issue,
            [a_comment(1)],
            issue_document_id_by_api_url=BY_URL,
        )
        assert counts["inserted"] == 1 and counts["human"] == 1

        row = with_issue.execute(
            "SELECT status, author_id, parent_id, thread_root_id, filter_reasons "
            "FROM document WHERE external_id = 'gh-comment:1'"
        ).fetchone()
        status, author_id, parent, root, reasons = row
        assert status == "kept"
        assert author_id is not None, "a human comment is a voice"
        assert parent == "doc_issue" and root == "doc_issue"
        assert not reasons
        assert with_issue.execute(
            "SELECT count(*) FROM author WHERE id = %s", (author_id,)
        ).fetchone()[0] == 1

    def test_a_bot_comment_is_stored_filtered_and_is_not_a_voice(self, with_issue):
        """Stored, named, and not counted. The ruling stays open either way.

        Dropping the row would prejudge it — "rejected is not deleted" exists
        for exactly this — and keeping it as a voice is the thing that must not
        happen before Engineer 2 rules.
        """
        counts = self._harvester().write_comments(
            with_issue,
            [a_comment(2, handle="github-actions[bot]", author_type="Bot",
                       external_id=99)],
            issue_document_id_by_api_url=BY_URL,
        )
        assert counts["bot_filtered"] == 1 and counts["human"] == 0

        status, author_id, reasons = with_issue.execute(
            "SELECT status, author_id, filter_reasons FROM document "
            "WHERE external_id = 'gh-comment:2'"
        ).fetchone()
        assert status == "filtered"
        assert author_id is None, "a bot must not be a voice"
        assert reasons == ["bot_author"], "and /filtered must be able to name the rule"
        assert with_issue.execute(
            "SELECT count(*) FROM author WHERE external_id = '99'"
        ).fetchone()[0] == 0, "no author row at all, not even an unreferenced one"

    def test_the_busiest_commenter_in_the_corpus_is_the_one_this_stops(self, with_issue):
        """github-actions[bot] was 22 of 148, linear[bot] one more."""
        comments = [
            a_comment(10 + i, handle="github-actions[bot]", author_type="Bot",
                      external_id=99)
            for i in range(22)
        ] + [
            a_comment(50, handle="linear[bot]", author_type="Bot", external_id=98),
            a_comment(51, handle="alice", author_type="User", external_id=1),
        ]
        counts = self._harvester().write_comments(
            with_issue, comments, issue_document_id_by_api_url=BY_URL
        )
        assert counts["bot_filtered"] == 23
        assert counts["bot_accounts"] == 2
        assert counts["human"] == 1
        assert with_issue.execute(
            "SELECT count(*) FROM document WHERE status = 'kept' "
            "AND external_id LIKE 'gh-comment:%'"
        ).fetchone()[0] == 1

    def test_a_deleted_account_gets_no_author_and_no_sentinel(self, with_issue):
        """A shared sentinel merges every deleted account into one voice."""
        counts = self._harvester().write_comments(
            with_issue,
            [a_comment(3, external_id=None)],
            issue_document_id_by_api_url=BY_URL,
        )
        assert counts["unattributable"] == 1
        assert with_issue.execute(
            "SELECT author_id FROM document WHERE external_id = 'gh-comment:3'"
        ).fetchone()[0] is None

    def test_two_comments_by_one_person_are_one_author_row(self, with_issue):
        """n_eff counts people. Five comments by one engineer is one voice."""
        self._harvester().write_comments(
            with_issue,
            [a_comment(4, external_id=7), a_comment(5, external_id=7)],
            issue_document_id_by_api_url=BY_URL,
        )
        assert with_issue.execute(
            "SELECT count(*) FROM author WHERE source = 'github'"
        ).fetchone()[0] == 1

    def test_a_comment_whose_issue_is_unknown_is_counted_not_guessed(self, with_issue):
        """A broken map must not read as a well-filtered sweep."""
        counts = self._harvester().write_comments(
            with_issue,
            [a_comment(6, issue_api_url="https://api.github.com/repos/o/r/issues/999")],
            issue_document_id_by_api_url=BY_URL,
        )
        assert counts["skipped_no_issue"] == 1 and counts["inserted"] == 0

    def test_harvest_run_id_and_provenance_move_together(self, with_issue):
        """Documents with no provenance exist because the column did not exist.

        These are not going to join them. The CHECK refuses a row where the two
        disagree, so this asserts the value rather than the intent.

        THE COUNT USED TO BE IN THIS DOCSTRING AND IT IS GONE ON PURPOSE. It
        said 344, which was true when written and was 1,788 by 2026-08-31 -
        reddit 1,492, github 176, blog 120 - having grown 1,148 in four days.
        A figure pinned in a docstring beside an assertion that does not test it
        goes stale in one direction only: downward-looking, so it keeps reading
        as a small settled gap. The live count belongs in a measurement that
        re-derives it (`docs/measurements/todays-reddit-writes-carry-no-harvest-
        run.md`), not here, where nothing would ever fail to correct it.
        """
        # `harvest_run.source_id` references `source`, so the row it names
        # has to exist. Seeded here rather than in the shared fixture: only
        # this test needs a run, and a fixture that quietly created sources
        # would hide a missing foreign key from every other test.
        with_issue.execute(
            "INSERT INTO source (id, platform, endpoint, base_trust, tos_notes, "
            "provenance) VALUES ('github', 'github', 'https://api.github.com', 0.9, "
            "'reviewed', 'seed')"
        )
        with_issue.execute(
            "INSERT INTO harvest_run (id, source_id, query_key, started_at, "
            "pipeline_version) VALUES ('hr1', 'github', 'q', now(), 'collect-0.1.0')"
        )
        self._harvester().write_comments(
            with_issue,
            [a_comment(7)],
            issue_document_id_by_api_url=BY_URL,
            harvest_run_id="hr1",
        )
        run_id, provenance = with_issue.execute(
            "SELECT harvest_run_id, retrieval_provenance FROM document "
            "WHERE external_id = 'gh-comment:7'"
        ).fetchone()
        assert run_id == "hr1" and provenance == "run_recorded"

    def test_without_a_run_id_the_provenance_is_not_recorded(self, with_issue):
        """`not_recorded`, never `no_run_for_source`: a run exists for every
        github document, so a missing id means this caller did not supply one."""
        self._harvester().write_comments(
            with_issue, [a_comment(8)], issue_document_id_by_api_url=BY_URL
        )
        run_id, provenance = with_issue.execute(
            "SELECT harvest_run_id, retrieval_provenance FROM document "
            "WHERE external_id = 'gh-comment:8'"
        ).fetchone()
        assert run_id is None and provenance == "not_recorded"

    def test_rewriting_the_same_comment_does_not_add_a_second_voice(self, with_issue):
        h = self._harvester()
        h.write_comments(with_issue, [a_comment(9)], issue_document_id_by_api_url=BY_URL)
        second = h.write_comments(
            with_issue, [a_comment(9)], issue_document_id_by_api_url=BY_URL
        )
        assert second["inserted"] == 0
        assert with_issue.execute(
            "SELECT count(*) FROM document WHERE external_id = 'gh-comment:9'"
        ).fetchone()[0] == 1


class TestTheThirdAssemblyShape:
    def _store(self, tmp_path):
        from collect.rawstore import RawStore

        return RawStore(tmp_path)

    def _comments(self, n, *, bots=0):
        from collect.assemble.issue import AssemblyComment

        out = [
            AssemblyComment(
                document_id=f"doc_c{i}",
                body=f"tool calling drops the second argument at {i} tools, gpt-5.2",
                external_id=f"gh-comment:{i}",
            )
            for i in range(n)
        ]
        out += [
            AssemblyComment(
                document_id=f"doc_bot{i}",
                body="This issue was automatically closed by a workflow run.",
                external_id=f"gh-comment:bot{i}",
                is_bot=True,
            )
            for i in range(bots)
        ]
        return out

    def test_it_is_a_different_selection_method_from_the_body_only_shape(self, tmp_path):
        from collect.assemble.issue import ISSUE_BODY_ONLY, assemble_issue_thread

        assembled = assemble_issue_thread(
            root_document_id="doc_issue",
            root_text="gpt-5.2 drops arguments",
            comments=self._comments(2),
            comment_count=2,
            store=self._store(tmp_path),
            version_aliases={},
        )
        assert assembled.selection_method == "issue_with_comments"
        assert assembled.selection_method != ISSUE_BODY_ONLY

    def test_the_comments_reach_the_flattened_text(self, tmp_path):
        from collect.assemble.issue import assemble_issue_thread

        assembled = assemble_issue_thread(
            root_document_id="doc_issue",
            root_text="gpt-5.2 drops arguments",
            comments=self._comments(2),
            comment_count=2,
            store=self._store(tmp_path),
            version_aliases={},
        )
        assert len(assembled.member_document_ids) == 3, "root plus two comments"
        assert "second argument" in assembled.flattened.text

    def test_a_bot_is_not_a_member_so_it_cannot_be_quoted(self, tmp_path):
        """The guard that matters. author_id NULL is not enough on its own:
        cells.py maps a NULL author to a shared anonymous voice per platform."""
        from collect.assemble.issue import assemble_issue_thread

        assembled = assemble_issue_thread(
            root_document_id="doc_issue",
            root_text="gpt-5.2 drops arguments",
            comments=self._comments(1, bots=3),
            comment_count=4,
            store=self._store(tmp_path),
            version_aliases={},
        )
        assert not any("bot" in m for m in assembled.member_document_ids)
        assert "automatically closed" not in assembled.flattened.text

    def test_coverage_counts_humans_and_hides_what_was_not_fetched(self, tmp_path):
        """observed / (observed + hidden). An issue reporting 12 comments of
        which we hold 8 is 0.667 covered, not 1.0."""
        from collect.assemble.issue import assemble_issue_thread

        assembled = assemble_issue_thread(
            root_document_id="doc_issue",
            root_text="gpt-5.2 drops arguments",
            comments=self._comments(8),
            comment_count=12,
            store=self._store(tmp_path),
            version_aliases={},
        )
        assert assembled.observed_children == 8
        assert assembled.hidden_children_min == 4

    def test_the_cap_limits_what_is_read_not_what_is_counted(self, tmp_path):
        """`observed_children` is the voices we hold; members are what the
        extractor reads. Conflating them reports a five-comment cap as a
        five-comment thread."""
        from collect.assemble.issue import MAX_ISSUE_COMMENTS, assemble_issue_thread

        assembled = assemble_issue_thread(
            root_document_id="doc_issue",
            root_text="gpt-5.2 drops arguments",
            comments=self._comments(9),
            comment_count=9,
            store=self._store(tmp_path),
            version_aliases={},
        )
        assert assembled.observed_children == 9
        assert len(assembled.member_document_ids) == MAX_ISSUE_COMMENTS + 1
        assert assembled.hidden_children_min == 0

    def test_selection_is_deterministic_so_a_rerun_gives_the_same_offset_map(
        self, tmp_path
    ):
        from collect.assemble.issue import assemble_issue_thread

        kwargs = dict(
            root_document_id="doc_issue",
            root_text="gpt-5.2 drops arguments",
            comments=self._comments(9),
            comment_count=9,
            store=self._store(tmp_path),
            version_aliases={},
        )
        first = assemble_issue_thread(**kwargs)
        second = assemble_issue_thread(**kwargs)
        assert first.member_document_ids == second.member_document_ids

    def test_an_empty_root_refuses_rather_than_verifying_against_nothing(self, tmp_path):
        from collect.assemble.issue import assemble_issue_thread

        with pytest.raises(ValueError, match="no stored root text"):
            assemble_issue_thread(
                root_document_id="doc_issue",
                root_text="   ",
                comments=self._comments(1),
                comment_count=1,
                store=self._store(tmp_path),
                version_aliases={},
            )

    def test_vote_less_comments_are_ranked_by_content_not_by_id(self):
        """A GitHub comment has no score. Under the old PRODUCT
        `specificity x log1p(score)` every comment ranked 0.0 and the "ranking"
        was a sort by comment id. The ranking is a SUM since 2026-09-24, so a
        missing score costs the engagement term only - asserted by behaviour
        rather than by reading source, which is what the old test did.
        """
        from types import SimpleNamespace

        from collect.assemble.ranking import rank_children

        plain = SimpleNamespace(external_id="a_first_by_id", body="Thanks, same here.", score=None)
        specific = SimpleNamespace(
            external_id="z_last_by_id",
            body="I tried it: `TypeError: tool_choice` after 3 calls at 128k tokens.",
            score=None,
        )
        ranked = rank_children([plain, specific], version_aliases=set())
        assert ranked[0].member is specific, "id order would have put `plain` first"
        assert ranked[0].score > 0
