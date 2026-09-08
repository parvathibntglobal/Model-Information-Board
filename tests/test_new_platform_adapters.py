"""The invariants the five new adapters would otherwise lose quietly.

NO NETWORK AND NO DATABASE. Every test here is about a decision that is cheap
to break by accident and expensive to notice: a provenance claim with nothing
behind it, a shared author row, a comment with no text written as evidence, a
`text_ref` pointing at a container of many documents.

The end-to-end proof lives elsewhere and is a real run:
`scripts/smoke_new_adapters.py`, recorded in
`docs/measurements/new-adapter-smoke-2026-09-07.json`. This file is the part
that has to keep passing after somebody edits the writer at 6pm.
"""

from __future__ import annotations

import json

import pytest

from collect.adapters.documents import (
    NO_TEXT_REASON,
    DocumentDraft,
    ProvenanceDisagreement,
    _as_timestamp,
    assert_provenance,
    document_id,
    write_documents,
)


def _draft(**overrides) -> DocumentDraft:
    fields = {
        "source": "devto",
        "external_id": "1",
        "url": "https://dev.to/a/b",
        "text_ref": "raw/sha256/ab/cd/abcd",
        "content_hash": "abcd",
    }
    fields.update(overrides)
    return DocumentDraft(**fields)


# ── provenance: the pair that cannot disagree ────────────────────────────


class TestProvenance:
    """`document_retrieval_provenance_agrees_ck`, mirrored so errors name callers."""

    def test_run_recorded_without_an_id_is_refused(self):
        with pytest.raises(ProvenanceDisagreement):
            assert_provenance("run_recorded", None)

    def test_an_id_without_run_recorded_is_refused(self):
        # The direction that actually happened: 853 rows landed claiming
        # `no_run_for_source` from a writer that had typed it into the SQL.
        with pytest.raises(ProvenanceDisagreement):
            assert_provenance("not_recorded", "hr_abc")

    def test_an_unknown_value_names_the_vocabulary(self):
        with pytest.raises(ValueError, match="not one of"):
            assert_provenance("unreviewed_writer", None)

    def test_the_three_legitimate_pairings_pass(self):
        assert_provenance("run_recorded", "hr_abc")
        assert_provenance("no_run_for_source", None)
        assert_provenance("not_recorded", None)


# ── absent values stay absent ────────────────────────────────────────────


class TestAbsenceIsNotAValue:
    def test_no_author_id_means_no_author_row_and_never_a_sentinel(self):
        # A shared row would merge every unattributable document into ONE
        # voice, which `judge/curate/gate.py` would then read as corroborating
        # itself.
        assert _draft(author_external_id=None).author_row is None

    def test_a_missing_date_stays_missing(self):
        assert _as_timestamp(None) is None
        assert _as_timestamp("") is None
        assert _as_timestamp("not a date") is None

    def test_an_epoch_and_an_iso_string_both_parse_to_utc(self):
        # Hacker News sends `created_at_i`; the other four send ISO-8601, two of
        # them with a `Z` suffix that `fromisoformat` refuses before 3.11.
        assert _as_timestamp(1788750795).year == 2026
        assert _as_timestamp("2026-09-07T03:13:15Z").tzinfo is not None
        assert _as_timestamp("2026-09-06T22:49:59.000Z").minute == 49

    def test_a_naive_timestamp_is_read_as_utc_rather_than_local(self):
        assert _as_timestamp("2026-09-07T03:13:15").tzinfo is not None

    def test_the_row_carries_the_platform_declared_lang(self):
        """`document.lang` was UN-RESERVED on 2026-09-08. This asserted the
        absence until then, and the absence was the contract's answer rather
        than the writer's.

        `scripts/audit_columns.py` credits a dict key in a module that INSERTs
        as write evidence for that column, so this key and the column in
        `_INSERT` have to move together - and `tests/test_column_states.py`
        failed by name when only one of them did.
        """
        draft = _draft(lang="en")
        row = draft.as_row(retrieval_provenance="not_recorded", harvest_run_id=None)
        assert row["lang"] == "en"
        assert draft.lang == "en"

    def test_an_undeclared_lang_stays_none_rather_than_becoming_english(self):
        """Rule 6, on the column whose gate would silently pass everything.

        `triage.gates.wrong_language` returns NOT_APPLICABLE for a NULL and
        would pass every document if this defaulted to `en` - a gate that ran
        and decided nothing, indistinguishable from one that worked. NULL on
        the three platforms that declare no language, and on all 6,502 rows
        stored before this write existed.
        """
        row = _draft().as_row(retrieval_provenance="not_recorded", harvest_run_id=None)
        assert row["lang"] is None

    def test_the_declared_value_is_not_normalised(self):
        """The platform's answer, not our translation of it.

        X returns `qme` for a post it could not place, and `zxx` for one with
        no linguistic content. Both are the platform's own declaration and are
        stored as sent - lowercasing, truncating to two letters, or mapping
        either to NULL would substitute our reading for theirs.
        """
        for declared in ("qme", "zxx", "pt-BR", "EN"):
            row = _draft(lang=declared).as_row(
                retrieval_provenance="not_recorded", harvest_run_id=None
            )
            assert row["lang"] == declared


class TestOneCallOnePlatform:
    def test_a_mixed_batch_is_refused(self):
        """Pooled counts over two platforms have no single denominator."""
        with pytest.raises(ValueError, match="One call writes"):
            write_documents(
                object(),
                [_draft(source="devto"), _draft(source="arxiv", external_id="2")],
                retrieval_provenance="not_recorded",
            )


class TestDocumentId:
    def test_the_convention_is_source_colon_external_id(self):
        assert document_id("hackernews", "49593453") == "hackernews:49593453"

    def test_thread_links_go_through_the_same_function(self):
        row = _draft(
            source="hackernews",
            external_id="49593453",
            thread_root_external_id="49587217",
            parent_external_id="49591625",
        ).as_row(retrieval_provenance="not_recorded", harvest_run_id=None)
        assert row["thread_root_id"] == "hackernews:49587217"
        assert row["parent_id"] == "hackernews:49591625"


# ── Hacker News: the unit, and the linkage ───────────────────────────────


class TestHackerNewsDrafts:
    def _run_with(self, comment_text):
        from collect.adapters.hackernews import HnComment, HnRun, HnStory, StoredItem

        run = HnRun(query="q", started_at=_as_timestamp(0))
        story = HnStory(
            item_id="1", title="t", url=None, author="alice", text=None,
            points=10, created_at=None, created_at_i=1788750000, child_count=3,
        )
        comment = HnComment(
            object_id="2", author="bob", comment_text=comment_text,
            created_at=None, created_at_i=1788750795, parent_id="1",
            story_id="1", story_title="t", story_url=None,
        )
        item = StoredItem(
            external_id="x", ref="raw/sha256/ab/cd/abcd", content_hash="abcd",
            size=1, already_present=False,
        )
        run.stored_stories.append((story, item))
        run.stored_comments.append((comment, item))
        return run

    def test_a_story_is_its_own_root_and_has_no_parent(self):
        # Inventing a self-reference for `parent_id` would make "is this a
        # root" unanswerable.
        from collect.adapters.hackernews import HackerNewsHarvester

        drafts = HackerNewsHarvester.drafts(object(), self._run_with("a real comment"))
        story = next(d for d in drafts if d.external_id == "1")
        assert story.thread_root_external_id == "1"
        assert story.parent_external_id is None

    def test_a_comment_carries_both_its_parent_and_its_thread_root(self):
        from collect.adapters.hackernews import HackerNewsHarvester

        drafts = HackerNewsHarvester.drafts(object(), self._run_with("a real comment"))
        comment = next(d for d in drafts if d.external_id == "2")
        assert (comment.parent_external_id, comment.thread_root_external_id) == ("1", "1")
        assert comment.status == "kept"

    def test_a_blanked_comment_is_stored_filtered_and_says_why(self):
        """HN blanks dead and flagged comments while keeping the record.

        Rejected is not deleted: the payload is stored either way, and a row
        with no text that reads as kept is a document nobody wrote.
        """
        from collect.adapters.hackernews import HackerNewsHarvester

        drafts = HackerNewsHarvester.drafts(object(), self._run_with(None))
        comment = next(d for d in drafts if d.external_id == "2")
        assert comment.status == "filtered"
        assert comment.filter_reasons == (NO_TEXT_REASON,)

    def test_the_engagement_shape_says_hn_withholds_comment_scores(self):
        from collect.adapters.hackernews import HnComment

        comment = HnComment(
            object_id="2", author=None, comment_text="x", created_at=None,
            created_at_i=None, parent_id=None, story_id=None,
            story_title=None, story_url=None,
        )
        # None, not 0. A zero would say nobody engaged, and E3 ranks on
        # specificity x log(1 + engagement).
        assert comment.engagement == {"score": None, "comments": None}


# ── Hacker News: is_self_post, a mapping rather than a decision ──────────


class TestHackerNewsIsSelfPost:
    """`pure_link_post` reported NOT_APPLICABLE on the one new platform where
    the concept exists, and `NotRun` documents that as PERMANENT.

    Here it was neither permanent nor a property of the document: it was a
    field nobody mapped. The case the gate exists for is the case this platform
    produced — a bare link at 678 points whose evidence was all in its
    comments.
    """

    def _story(self, **overrides):
        from collect.adapters.hackernews import HnStory

        fields = {
            "item_id": "1", "title": "t", "url": None, "author": "alice",
            "text": None, "points": 10, "created_at": None,
            "created_at_i": None, "child_count": 0,
        }
        fields.update(overrides)
        return HnStory(**fields)

    def test_a_story_with_a_url_and_no_text_is_a_link_post(self):
        assert self._story(url="https://example.invalid/x").is_self_post is False

    def test_a_story_with_text_is_a_self_post(self):
        assert self._story(text="Ask HN: how do you...").is_self_post is True

    def test_whitespace_is_not_text(self):
        assert self._story(url="https://example.invalid/x", text="   ").is_self_post is (
            False
        )

    def test_neither_a_url_nor_text_stays_none(self):
        """Reachable, and not a bug. `False` would call it a link post with no
        link, and `pure_link_post` would drop it for having no commentary about
        nothing."""
        assert self._story().is_self_post is None

    def test_a_comment_is_permanently_not_applicable(self):
        """A comment is neither — the distinction is about how a SUBMISSION
        carries its content."""
        from collect.adapters.hackernews import HnComment

        comment = HnComment(
            object_id="2", author="bob", comment_text="it broke", created_at=None,
            created_at_i=None, parent_id="1", story_id="1", story_title="t",
            story_url=None,
        )
        assert comment.is_self_post is None

    def test_the_same_answers_come_from_a_stored_payload(self):
        """The form triage actually needs: the gates run over stored rows, so a
        projection reads the payload rather than a live run's objects."""
        from collect.adapters.hackernews import is_self_post_of

        assert is_self_post_of({"type": "story", "url": "https://x"}) is False
        assert is_self_post_of({"type": "story", "text": "Ask HN"}) is True
        assert is_self_post_of({"type": "story"}) is None

    def test_a_comment_payload_is_identified_by_its_type_and_not_by_absence(self):
        """A link post also has no `text`, so an absence test would call every
        comment a link post and hand `pure_link_post` a verdict on a record the
        rule is not about."""
        from collect.adapters.hackernews import is_self_post_of

        assert is_self_post_of({"type": "comment", "text": "it broke"}) is None
        assert is_self_post_of({"type": "comment"}) is None

    def test_the_gate_then_gives_a_real_verdict_on_an_hn_link_post(self):
        """End to end: the mapping is only worth having if the gate uses it.

        A link post with no commentary of the poster's own is what
        `pure_link_post` drops — and on this platform the story's `text` IS the
        commentary, exactly as `selftext` is on Reddit.
        """
        from collect.triage.gates import Document, NotRun, pure_link_post

        link_post = Document(text="Some Title", is_self_post=False, body="")
        assert pure_link_post(link_post) is True

        with_commentary = Document(
            text="Some Title", is_self_post=False, body="why this matters:"
        )
        assert pure_link_post(with_commentary) is False

        comment = Document(text="it broke", is_self_post=None)
        assert pure_link_post(comment) is NotRun.NOT_APPLICABLE


# ── Hugging Face: two ways to have no text ───────────────────────────────


class TestHuggingFaceFilterReasons:
    def _comment(self, *, body, hidden):
        from collect.adapters.huggingface import HfComment

        return HfComment(
            event_id="e1", repo_id="org/repo", discussion_num=7,
            author_external_id="a1", author_handle="alice", author_type="user",
            created_at=None, body=body, hidden=hidden, payload="{}",
        )

    def test_a_comment_with_text_is_kept(self):
        from collect.adapters.huggingface import _filter_reasons

        assert _filter_reasons(self._comment(body="real text", hidden=False)) is None

    def test_an_empty_comment_is_filtered_even_when_not_hidden(self):
        """The defect the 2026-09-07 control run found, not code review.

        An event with `data.latest.raw` empty and `hidden` false was written
        `kept` and then refused at `huggingface_prose` - a row that looks like
        evidence and has none.
        """
        from collect.adapters.huggingface import _filter_reasons

        assert _filter_reasons(self._comment(body="  ", hidden=False)) == (
            NO_TEXT_REASON,
        )

    def test_both_reasons_are_recorded_where_both_apply(self):
        from collect.adapters.huggingface import HIDDEN_REASON, _filter_reasons

        reasons = _filter_reasons(self._comment(body=None, hidden=True))
        assert reasons == (HIDDEN_REASON, NO_TEXT_REASON)

    def test_the_shared_string_is_shared(self):
        """One spelling for one filter reason, across two platforms."""
        from collect.adapters.hackernews import DEAD_COMMENT_REASON
        from collect.adapters.huggingface import NO_TEXT

        assert DEAD_COMMENT_REASON == NO_TEXT == NO_TEXT_REASON


# ── arXiv: the version, and the single-entry artifact ────────────────────


class TestArxiv:
    def test_the_version_is_kept_in_the_external_id(self):
        """A v2 abstract is a different document.

        Sharing an id with v1 would let `ON CONFLICT DO NOTHING` keep the first
        version forever, silently.
        """
        from collect.adapters.arxiv import arxiv_id_of

        assert arxiv_id_of("http://arxiv.org/abs/2609.03450v2") == "2609.03450v2"

    def test_no_author_id_is_a_property_and_not_a_gap(self):
        from collect.adapters.arxiv import ArxivPaper

        paper = ArxivPaper(
            external_id="1v1", abs_url="https://arxiv.org/abs/1v1", title="t",
            summary="s", published=None, updated=None,
            authors=("Ada Lovelace", "Alan Turing"), primary_category=None,
            comment=None,
        )
        # Two authors and no stable id for either, so the document is
        # unattributable rather than attributed to the first name in the list.
        assert paper.author_external_id is None
        assert paper.engagement == {"score": None, "comments": None, "citations": None}


# ── X: the RapidAPI route, and the credential as the stop ────────────────


class TestXIsBuiltAgainstRapidApi:
    """The route is a RapidAPI scraper provider, NOT X's own API.

    This is the one adapter whose ROUTE is a decision rather than a fact, and
    the first version of it was built against X's own API with a bearer token -
    a different party, a different credential and a different terms ruling.
    These tests are what makes a drift back to that visible.
    """

    def test_no_key_names_the_rapidapi_key_and_not_a_generic_credential(self):
        """A generic "credential missing" sends somebody to the wrong file.

        The credential here is a RapidAPI key - the same one the Reddit path
        uses - so the message has to say so, or the reader goes looking for an
        X developer account.
        """
        from collect.adapters.x import XCredentialMissing, XHarvester

        with pytest.raises(XCredentialMissing) as caught:
            XHarvester(
                client=object(), store=object(), api_key="", provider="twitter241"
            )
        message = str(caught.value)
        assert "RAPIDAPI_KEY" in message
        assert "SCRAPER_PROVIDER" in message
        # And it must not send anybody to X's own API for a key.
        assert "bearer" not in message.casefold()

    def test_the_host_is_derived_from_the_provider_and_not_hardcoded(self):
        from collect.adapters.x import host_for

        assert host_for("twitter241") == "twitter241.p.rapidapi.com"
        # Moving provider follows the variable, with no code change.
        assert host_for("twitter135") == "twitter135.p.rapidapi.com"

    def test_an_unset_provider_refuses_rather_than_defaulting_to_a_vendor(self):
        """An unconfigured process must not quietly call one particular vendor."""
        from collect.adapters.x import XConfigError, host_for

        with pytest.raises(XConfigError, match="SCRAPER_PROVIDER"):
            host_for("")

    def test_a_host_pasted_into_the_provider_slot_is_refused(self):
        """`RAPIDAPI_HOST` already suffered one bad paste in this project."""
        from collect.adapters.x import XConfigError, host_for

        with pytest.raises(XConfigError, match="PROVIDER NAME"):
            host_for("twitter241.p.rapidapi.com")

    def test_the_two_rapidapi_headers_are_sent(self):
        from collect.adapters.x import XHarvester

        harvester = XHarvester(
            client=object(), store=object(), api_key="k", provider="twitter241"
        )
        assert harvester.auth_headers == {
            "X-RapidAPI-Key": "k",
            "X-RapidAPI-Host": "twitter241.p.rapidapi.com",
        }
        assert harvester.host == "twitter241.p.rapidapi.com"

    def test_the_header_host_follows_the_provider(self):
        from collect.adapters.x import XHarvester

        harvester = XHarvester(
            client=object(), store=object(), api_key="k", provider="twitter135"
        )
        assert harvester.auth_headers["X-RapidAPI-Host"] == "twitter135.p.rapidapi.com"

    def test_the_request_shape_is_reviewable_before_a_credential_exists(self):
        from collect.adapters.x import XHarvester

        harvester = XHarvester(
            client=object(), store=object(), api_key="k", provider="twitter241"
        )
        params = harvester.search_params("Fable 5.1", search_type="Top")
        assert params["query"] == "Fable 5.1"
        # `Top` and `Latest` are the two the recorded sweep actually ran.
        assert params["type"] == "Top"
        assert "count" in params

    def test_an_unknown_search_type_is_a_local_error(self):
        from collect.adapters.x import XHarvester

        harvester = XHarvester(
            client=object(), store=object(), api_key="k", provider="twitter241"
        )
        with pytest.raises(ValueError, match="search_type"):
            harvester.search_params("q", search_type="top")

    def test_the_observation_names_the_reseller_route_and_the_provider(
        self, monkeypatch
    ):
        """The gate must be able to pin which provider was reviewed.

        A ruling is a reading of one party's terms; swapping the provider swaps
        the party AND the response envelope, so a swap has to refuse rather
        than silently parse nothing and report the platform as quiet.
        """
        from collect.adapters import x as x_module

        monkeypatch.setattr(
            x_module,
            "settings",
            lambda: _FakeSettings(provider="twitter241", key="k"),
        )
        observed = x_module.observe_x_use()
        assert observed["access_path"] == "rapidapi-reseller"
        assert observed["scraper_provider"] == "twitter241"
        assert observed["credential_present"] is True


class _FakeSettings:
    """Just the two fields `observe_x_use` reads."""

    def __init__(self, *, provider, key):
        self.scraper_provider = provider
        self.rapidapi_key = key


class TestXParsing:
    """The response envelope, and the schema move this project already paid for."""

    def _result(self, **overrides):
        result = {
            "rest_id": "2047527303824236545",
            "legacy": {
                "full_text": "it broke on 1M context",
                "created_at": "Fri Apr 24 10:00:00 +0000 2026",
                "lang": "en",
                "conversation_id_str": "2047527303824236000",
                "in_reply_to_status_id_str": "2047527303824235000",
                "favorite_count": 12,
                "reply_count": 3,
            },
            "core": {
                "user_results": {
                    "result": {"rest_id": "171962385", "screen_name": "bookwormengr"}
                }
            },
        }
        result.update(overrides)
        return result

    def _run(self):
        from collect.adapters.x import XRun

        return XRun(query="q", search_type="Top", started_at=_as_timestamp(0))

    def test_a_reply_carries_its_conversation_and_its_parent(self):
        from collect.adapters.x import _post_of

        post = _post_of(self._result(), self._run())
        assert post.conversation_id == "2047527303824236000"
        assert post.replied_to_id == "2047527303824235000"
        assert post.lang == "en"
        assert (post.author_external_id, post.author_handle) == (
            "171962385",
            "bookwormengr",
        )

    def test_absent_views_stay_absent(self):
        """The recorded sweep: X does not always expose them."""
        from collect.adapters.x import _post_of

        post = _post_of(self._result(), self._run())
        assert post.engagement["views"] is None
        assert post.engagement["score"] == 12

    def test_a_legacy_only_author_is_counted_as_a_fallback(self):
        """The schema move that recorded EVERY author as 0 followers.

        `legacy` comes back empty on search results; the previous provider code
        read it anyway and nothing noticed for a whole sweep. A fallback that is
        not counted is the same defect with a different field.
        """
        from collect.adapters.x import _post_of

        run = self._run()
        result = self._result(
            core={
                "user_results": {
                    "result": {
                        "rest_id": "171962385",
                        "legacy": {"screen_name": "bookwormengr"},
                    }
                }
            }
        )
        post = _post_of(result, run)
        assert post.author_handle == "bookwormengr"
        assert run.author_legacy_fallbacks == 1
        assert post.author_from_legacy is True

    def test_a_long_post_takes_note_tweet_and_not_the_truncated_text(self):
        """A truncated document that reads as complete is the worst shape: a
        quote from its tail fails against text nobody has."""
        from collect.adapters.x import _post_of

        result = self._result(
            note_tweet={"note_tweet_results": {"result": {"text": "the whole thing"}}}
        )
        assert _post_of(result, self._run()).text == "the whole thing"

    def test_tweet_results_are_found_wherever_the_provider_nests_them(self):
        from collect.adapters.x import _tweet_results

        envelope = {
            "result": {
                "timeline": {
                    "instructions": [
                        {
                            "type": "TimelineAddEntries",
                            "entries": [
                                {
                                    "content": {
                                        "itemContent": {
                                            "tweet_results": {"result": self._result()}
                                        }
                                    }
                                }
                            ],
                        }
                    ]
                }
            }
        }
        found = _tweet_results(envelope)
        assert len(found) == 1
        assert found[0]["rest_id"] == "2047527303824236545"

    def test_a_quoted_post_is_not_a_second_document(self):
        """A retweeted or quoted post hangs off this one and was not retrieved
        by this query."""
        from collect.adapters.x import _tweet_results

        outer = self._result()
        outer["quoted_status_result"] = {"result": self._result(rest_id="999")}
        assert [r["rest_id"] for r in _tweet_results({"data": [outer]})] == [
            "2047527303824236545"
        ]

    def test_an_entry_with_no_id_returns_none_rather_than_a_partial_post(self):
        from collect.adapters.x import _post_of

        assert _post_of({"legacy": {"full_text": "x"}, "core": {}}, self._run()) is None

    def test_the_bottom_cursor_is_found(self):
        from collect.adapters.x import _next_cursor

        payload = {
            "entries": [
                {"content": {"cursorType": "Top", "value": "up"}},
                {"content": {"cursorType": "Bottom", "value": "down"}},
            ]
        }
        assert _next_cursor(payload) == "down"
        assert _next_cursor({"entries": []}) is None


# ── prose: the refusal is the value ──────────────────────────────────────


class TestProseRefusesAContainerOfManyDocuments:
    """The check that catches a WRONG CHOICE of artifact.

    `content_hash(resolve(text_ref)) == content_hash` is necessary and not
    sufficient - it cannot see that both columns point at the wrong thing,
    which is the failure that happened twice on two platforms.
    """

    def test_arxiv_refuses_a_multi_entry_search_feed(self):
        from collect.assemble.prose import NotAPayload, arxiv_paper_prose

        feed = (
            '<feed xmlns="http://www.w3.org/2005/Atom">'
            "<entry><title>A</title><summary>a</summary></entry>"
            "<entry><title>B</title><summary>b</summary></entry></feed>"
        )
        with pytest.raises(NotAPayload, match="2 entries"):
            arxiv_paper_prose(feed)

    def test_arxiv_reads_a_single_entry_feed(self):
        from collect.assemble.prose import arxiv_paper_prose

        feed = (
            '<feed xmlns="http://www.w3.org/2005/Atom">'
            "<entry><title>A  title</title><summary>the abstract</summary></entry>"
            "</feed>"
        )
        assert arxiv_paper_prose(feed) == "A title\n\nthe abstract"

    def test_devto_refuses_a_search_page(self):
        from collect.assemble.prose import NotAPayload, devto_article_prose

        with pytest.raises(NotAPayload, match="not an object|no `title`"):
            devto_article_prose(json.dumps([{"id": 1, "title": "x"}]))

    def test_devto_refuses_an_article_with_html_and_no_markdown(self):
        """A crosspost. Named rather than silently substituted."""
        from collect.assemble.prose import NotAPayload, devto_article_prose

        blob = json.dumps({"title": "t", "body_markdown": "", "body_html": "<p>x"})
        with pytest.raises(NotAPayload, match="crosspost"):
            devto_article_prose(blob)

    def test_hackernews_unescapes_entities_and_paragraph_tags(self):
        """A quote of what a reader sees must verify against the prose.

        The API returns the text HTML-escaped, so leaving it would make rule
        1 FAIL for the wrong reason - the mirror of the defect that made it
        pass for the wrong reason.
        """
        from collect.assemble.prose import hackernews_prose

        text = hackernews_prose(
            json.dumps({"text": "I&#x27;m running<p>two projects"})
        )
        assert "I'm running" in text
        assert "<p>" not in text
        assert "&#x27;" not in text

    def test_hackernews_refuses_a_search_response(self):
        from collect.assemble.prose import NotAPayload, hackernews_prose

        with pytest.raises(NotAPayload, match="hits"):
            hackernews_prose(json.dumps({"hits": [{"comment_text": "x"}]}))

    def test_huggingface_reads_a_comment_event_and_a_discussion(self):
        from collect.assemble.prose import huggingface_prose

        event = {"type": "comment", "data": {"latest": {"raw": "it OOMs at 8k"}}}
        assert huggingface_prose(json.dumps(event)) == "it OOMs at 8k"

        discussion = {
            "title": "OOM on load",
            "events": [
                {"type": "status-change", "data": {}},
                {"type": "comment", "data": {"latest": {"raw": "same here"}}},
            ],
        }
        assert huggingface_prose(json.dumps(discussion)) == "OOM on load\n\nsame here"

    def test_huggingface_refuses_a_discussions_list(self):
        from collect.assemble.prose import NotAPayload, huggingface_prose

        with pytest.raises(NotAPayload, match="discussions"):
            huggingface_prose(json.dumps({"discussions": [{"num": 1}], "count": 1}))

    def test_x_refuses_a_search_page(self):
        from collect.assemble.prose import NotAPayload, x_post_prose

        with pytest.raises(NotAPayload, match="LIST"):
            x_post_prose(json.dumps({"data": [{"id": "1", "text": "x"}]}))
