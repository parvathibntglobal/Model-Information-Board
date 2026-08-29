

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
