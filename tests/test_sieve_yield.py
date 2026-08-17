"""The three-number yield: retrieved, phrase-containing, sieve-passing.

Engineer 2's case, on #18: 75 posts at 24% containment produces a yield that
looks healthy and a usable count that does not, and nothing downstream could
tell them apart. `candidates` and `kept` are two of the three numbers; this
covers the third.

The rule-6 tests are the load-bearing ones. `phrase_present = 0` is a finding —
no candidate contained the phrase. `phrase_present = None` is "we did not look".
Collapsing the second into the first would report a query that asked for nothing
as a query whose phrase nothing matched.
"""

from __future__ import annotations

from collect.adapters.queries.sieve import (
    SieveVerdict,
    count_phrase_present,
    quoted_phrases,
    tally,
)


def _verdicts(passed: int, failed: int):
    return (
        [SieveVerdict(passed=True) for _ in range(passed)]
        + [SieveVerdict(passed=False, missing=("signal",)) for _ in range(failed)]
    )


# ── extracting what the query asked for ──────────────────────────────────


def test_quoted_phrases_reads_the_query_not_the_text():
    assert quoted_phrases('"switched back" claude opus 5') == ("switched back",)
    assert quoted_phrases('"replaced gpt-5"') == ("replaced gpt-5",)


def test_a_query_with_no_quotes_asked_for_no_phrase():
    assert quoted_phrases("claude opus 5 tool calling") == ()


def test_multiple_phrases_are_all_returned_in_order():
    assert quoted_phrases('"a b" and "c d"') == ("a b", "c d")


def test_an_empty_pair_of_quotes_is_not_a_phrase():
    assert quoted_phrases('"" "real phrase"') == ("real phrase",)


# ── containment, by the sieve's own rules ────────────────────────────────


def test_containment_uses_the_sieves_matching_standard():
    """Comparable to `kept` only if measured the same way.

    `matches` over normalised text: adjacency modulo whitespace and stemming.
    A different standard here would make the middle number incommensurable with
    the third.
    """
    texts = [
        "We rolled back to the old one",      # present
        "ROLLED BACK last week",              # present, capitalised
        "we rolled\nback yesterday",          # present, wrapped
        "we reverted instead",                # absent
    ]
    assert count_phrase_present("rolled back", texts) == 3


def test_containment_of_a_phrase_nothing_carries_is_zero():
    assert count_phrase_present("rolled back", ["nothing like it here"]) == 0


# ── the three numbers together ───────────────────────────────────────────


def test_all_three_numbers_are_reported():
    y = tally("q", _verdicts(passed=3, failed=72), phrase_present=18)
    assert (y.candidates, y.phrase_present, y.kept) == (75, 18, 3)


def test_the_case_from_issue_18():
    """75 retrieved at 24% containment. The two rates say different things."""
    y = tally('"rolled back"', _verdicts(passed=3, failed=72), phrase_present=18)
    assert y.pass_rate == 3 / 75          # 4% — reads as a bad query
    assert y.phrase_rate == 18 / 75       # 24% — retrieval did not honour it
    assert y.usable_rate == 3 / 18        # 17% — the honest denominator
    assert y.pass_rate < y.usable_rate, (
        "pass_rate understates the query because the denominator includes "
        "documents retrieval should never have returned"
    )


def test_a_fully_binding_phrase_makes_the_two_rates_agree():
    """`"went back to"` came back at 100% containment. Then nothing is hidden."""
    y = tally('"went back to"', _verdicts(passed=5, failed=70), phrase_present=75)
    assert y.phrase_rate == 1.0
    assert y.pass_rate == y.usable_rate


# ── rule 6 ───────────────────────────────────────────────────────────────


def test_not_measured_is_none_not_zero():
    """The distinction the third number exists to preserve.

    A query that quoted nothing has no phrase to comply with. Reporting 0 would
    assert that no candidate contained a phrase — a finding — where the truth is
    that none was asked for.
    """
    y = tally("claude opus 5 tool calling", _verdicts(passed=1, failed=9))
    assert y.phrase_present is None
    assert y.phrase_rate is None
    assert y.usable_rate is None


def test_zero_containment_is_a_finding_and_reads_differently():
    y = tally('"replaced opus 5"', _verdicts(passed=0, failed=2), phrase_present=0)
    assert y.phrase_present == 0
    assert y.phrase_rate == 0.0, "measured, and the measurement is zero"
    assert y.usable_rate is None, "no honest denominator exists at zero"


def test_pass_rate_still_works_when_containment_was_not_measured():
    """Adding the third number must not make the first two conditional on it."""
    y = tally("bare query", _verdicts(passed=2, failed=8))
    assert y.pass_rate == 0.2


# ── the adapter wires it ─────────────────────────────────────────────────


def test_reddit_run_reports_containment_from_its_own_query():
    from collect.adapters.reddit import RedditPost, RedditRun

    def post(text: str, ident: str) -> RedditPost:
        return RedditPost(
            external_id=ident, url="u", title=text, selftext="", author="a",
            author_fullname="t2_a", subreddit="s", created_utc=1.0,
            score=1, num_comments=0, upvote_ratio=1.0,
        )

    run = RedditRun(query='"rolled back"', sort="RELEVANCE", started_at=None)
    run.posts = [post("we rolled back", "t3_1"), post("unrelated", "t3_2")]
    run.verdicts = _verdicts(passed=1, failed=1)
    y = run.sieve_yield
    assert y.candidates == 2
    assert y.phrase_present == 1
    assert y.kept == 1


def test_reddit_run_leaves_containment_unmeasured_for_an_unquoted_query():
    from collect.adapters.reddit import RedditRun

    run = RedditRun(query="claude opus 5", sort="RELEVANCE", started_at=None)
    run.verdicts = _verdicts(passed=0, failed=1)
    assert run.sieve_yield.phrase_present is None


# ── phrase_rate and usable_rate are not interchangeable ──────────────────
#
# Engineer 2's warning on #18, pinned rather than commented. No index we have
# measured binds a phrase, so containment measures how COMMON the phrase is.
# The metric therefore improves by making the query vaguer, which is the
# opposite of what it looks like. Same treatment as the two specificity floors
# differing at 0.3 and 0.0.


def _yield(query, *, retrieved, present, kept):
    return tally(query, _verdicts(passed=kept, failed=retrieved - kept),
                 phrase_present=present)


#: Both shapes are measured, not invented. `"went back to"` returned 75 posts at
#: 100% containment; `"replaced gemini 2.5 pro"` returned 6 at 50%.
COMMON = _yield('"went back to"', retrieved=75, present=75, kept=5)
SPECIFIC = _yield('"replaced gemini 2.5 pro"', retrieved=6, present=3, kept=2)


def test_the_two_rates_rank_the_same_pair_in_opposite_orders():
    """The property that makes substituting one for the other change conclusions."""
    assert COMMON.phrase_rate > SPECIFIC.phrase_rate, "containment prefers the common phrase"
    assert COMMON.usable_rate < SPECIFIC.usable_rate, "usable_rate prefers the specific one"


def test_optimising_phrase_rate_makes_the_evidence_worse():
    """The Goodhart direction, stated as arithmetic.

    Swapping a specific phrase for a common one takes containment from 50% to
    100% while the share of carrying candidates that survive the sieve falls
    from 67% to 7%. A dashboard tracking phrase_rate would record that as
    improvement.
    """
    assert SPECIFIC.phrase_rate == 0.5
    assert COMMON.phrase_rate == 1.0
    assert SPECIFIC.usable_rate > COMMON.usable_rate * 5


def test_usable_rate_cannot_be_moved_by_making_the_query_vaguer():
    """Its denominator is phrase-carrying candidates, not candidates.

    Retrieval returning more non-carrying documents changes `candidates` and
    `phrase_rate` and leaves `usable_rate` untouched — which is what makes it
    the one to watch.
    """
    tight = _yield('"replaced opus 5"', retrieved=10, present=4, kept=2)
    padded = _yield('"replaced opus 5"', retrieved=75, present=4, kept=2)
    assert padded.phrase_rate < tight.phrase_rate
    assert padded.usable_rate == tight.usable_rate == 0.5


def test_a_perfect_containment_rate_says_nothing_about_yield():
    """100% containment with nothing kept is the reading the warning is about."""
    y = _yield('"went back to"', retrieved=75, present=75, kept=0)
    assert y.phrase_rate == 1.0, "looks like retrieval working perfectly"
    assert y.usable_rate == 0.0, "and the query produced no evidence at all"
