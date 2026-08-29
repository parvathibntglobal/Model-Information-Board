

class TestBothAliasFormsAreEmittedInPriorityOrder:
    """The two forms retrieve DISJOINT sets, so one of them is not redundant.

    Measured over 1,019 harvest runs, per document rather than per request:

        found ONLY by concatenated     4
        found by both                  0
        found ONLY by hyphenated      48

    Zero overlap. `docs/measurements/what-github-needs-before-a-sweep.md`.
    """

    def test_hyphenated_comes_first(self):
        from collect.adapters.queries.github import github_alias_forms

        forms = github_alias_forms("claude sonnet 4.5")
        assert forms[0] == "claude-sonnet-4.5", (
            "hyphenated fetches 74.2 per run against concatenated's 5.6, so it "
            "must be issued first when a budget truncates the plan"
        )

    def test_the_concatenated_form_is_still_emitted(self):
        """EXPENSIVE AND USELESS ARE DIFFERENT STATES.

        5.6 fetched per run reads as noise until you ask what it uniquely
        produced: 4 documents, 7.7% of the corpus, findable no other way.
        Dropping it would have been the easy read and would have cost real
        evidence.
        """
        from collect.adapters.queries.github import github_alias_forms

        assert "claudesonnet4.5" in github_alias_forms("claude sonnet 4.5")

    def test_a_single_token_alias_is_not_issued_twice(self):
        # Two identical requests cost two of a 30/minute budget for one
        # candidate set.
        from collect.adapters.queries.github import github_alias_forms

        assert github_alias_forms("opus") == ("opus",)
        assert github_alias_forms("claude-opus-4.8") == ("claude-opus-4.8",)

    def test_an_alias_with_no_trailing_numeral_keeps_its_shape(self):
        """`github_alias_form`'s rule is untouched: only a COLLISION triggers it.

        `gpt-4.1 mini` has its numeral mid-string, so nothing matches issue #5
        and the spaced form is kept.
        """
        from collect.adapters.queries.github import github_alias_forms

        assert github_alias_forms("gpt-4.1 mini")[0] == "gpt-4.1 mini"

    def test_empty_surface_yields_nothing_rather_than_an_empty_query(self):
        from collect.adapters.queries.github import github_alias_forms

        assert github_alias_forms("   ") == ()


class TestTitleOnlyIsAShapeNotAFinding:
    """76 of 100 on-subject on one query, against a pooled 0.404% all-time.

    The largest retrieval improvement measured on this platform, and it belongs
    in the renderer rather than in a document.
    """

    def test_it_restricts_to_the_title_field(self):
        from collect.adapters.queries.github import title_only_query

        q = title_only_query("claude sonnet 4.5")
        assert "in:title" in q
        assert "type:issue" in q

    def test_it_uses_the_hyphenated_retrieval_form(self):
        # 57.9% of concatenated queries fetch nothing at all.
        from collect.adapters.queries.github import title_only_query

        assert '"claude-sonnet-4.5"' in title_only_query("claude sonnet 4.5")

    def test_the_alias_is_quoted_so_the_index_cannot_split_it(self):
        from collect.adapters.queries.github import title_only_query

        assert title_only_query("gpt-5.2").startswith('"gpt-5.2"')

    def test_repro_is_kept_as_a_shape_for_uniqueness_not_yield(self):
        """61 of its 95 on-subject documents were found by no other shape.

        It kept 0, like every shape tested. `unique` is the number that matters
        when shapes are disjoint.
        """
        from collect.adapters.queries.github import repro_query

        assert repro_query("qwen3.8-27b") == '"qwen3.8-27b" traceback type:issue'

    def test_shapes_are_ranked_with_title_first(self):
        from collect.adapters.queries.github import SHAPES

        assert SHAPES[0] == "title", (
            "title measured 31.0 on-subject documents per request against "
            "repro's 15.8; a truncated sweep must issue it first"
        )
