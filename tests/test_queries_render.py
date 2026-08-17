"""The rendering half: loader, sieve, and GitHub retrieval.

Every rule under test came from a measurement in issue #4 or issue #5, and the
test names say which failure it prevents rather than which function it calls.
"""

from __future__ import annotations

import pytest

from collect.adapters.queries.contract import (
    MissingPlaceholderError,
    QueryContractError,
    QueryEntry,
    TermSet,
    load_queries,
)
from collect.adapters.queries.github import (
    FORBIDDEN_SYNTAX,
    SearchRequest,
    Unrenderable,
    UnrenderableError,
    assert_renderable_syntax,
    github_alias_form,
    plan_searches,
    render_search,
)
from collect.adapters.queries.sieve import matches, normalize, sieve, tally

ALIASES = ("claude sonnet 5", "claude-sonnet-5", "sonnet 5")
SWEEP = ("repo:langchain-ai/langchain", "repo:run-llama/llama_index")


def entry(**overrides) -> QueryEntry:
    base = {
        "kind": "capability",
        "capability": "summarization.fidelity",
        "stance": "negative",
        "terms": TermSet(
            subject=("{alias}",),
            topic=("summary", "summarization", "condense"),
            signal=("dropped", "left out", "should have been null"),
        ),
        "records_condition": "context_size",
    }
    base.update(overrides)
    return QueryEntry(**base)


# ── the contract loads, and says what it said before ─────────────────────


def test_the_real_contract_loads():
    """Derived from capabilities.yaml, not hardcoded.

    This asserted 16 and then 24 was correct, which is a test that fails every
    time the contract grows — and growing the contract is what the contract is
    for. What is actually invariant is the rule PR #8 established: every
    capability carries both stances. `tests/test_queries_contract.py` enforces
    that rule from the contract side; this checks the loader sees all of it.
    """
    from collect.adapters.queries.cadence import load_failure_modes

    queries = load_queries()
    capabilities = load_failure_modes()

    assert len(queries.capabilities) == len(capabilities)
    assert len(queries.capability_queries) == len(capabilities) * 2, (
        "every capability carries both stances — see queries.yaml, "
        "'EVERY CAPABILITY CARRIES BOTH STANCES'"
    )
    assert len(queries.substitution) == 2
    assert all(e.records_condition for e in queries.all_entries)


def test_both_substitution_entries_declare_direction_from_extraction():
    """The flag is what keeps a semantic call out of this renderer."""
    queries = load_queries()
    assert all(e.direction_from_extraction for e in queries.substitution)
    assert not any(e.direction_from_extraction for e in queries.capability_queries)


def test_a_missing_contract_raises_rather_than_defaulting(tmp_path):
    """A built-in query set renders identically to the real one and diverges."""
    with pytest.raises(QueryContractError):
        load_queries(tmp_path / "absent.yaml")


def test_every_substitution_entry_is_seen_to_need_a_second_model():
    """The assertion that would have caught it, against the real contract.

    `needs_second_model` read `topic + signal`. Both aliases now live in
    `subject` — all-of, so both models must appear — and a topic-only read
    returns False, no `alias_b` is supplied, and `substitute()` raises. The
    contract half and this half have to land together for either to work.
    """
    queries = load_queries()
    assert all(e.needs_second_model for e in queries.substitution)
    assert not any(e.needs_second_model for e in queries.capability_queries)


def test_a_second_model_is_found_in_any_group_not_two_of_three():
    """Group-by-group is how the last one was missed, so the check is all-of-them."""
    for group in ("subject", "topic", "signal"):
        terms = {"subject": ("{alias}",), "topic": ("replaced",), "signal": ("held up",)}
        terms[group] = (*terms[group], "{alias_b}")
        assert entry(terms=TermSet(**terms)).needs_second_model, group


def test_an_unrecognised_direction_is_refused_at_load(tmp_path):
    """A typo would load, read as absent, and turn the constraint off silently.

    `stance` and `records_condition` were validated and `direction` was not, so
    the one machine-readable constraint in the contract was the only unchecked
    field. `decided_at_extration` would have made
    `direction_from_extraction` False, and GitHub would have rendered
    substitution as though the direction survived retrieval.
    """
    path = tmp_path / "queries.yaml"
    path.write_text(
        "version: test\n"
        "queries:\n"
        "  - capability: summarization.fidelity\n"
        "    stance: negative\n"
        "    direction: decided_at_extration\n"
        "    records_condition: context_size\n"
        "    terms:\n"
        "      subject: ['{alias}']\n"
        "      topic: ['summary']\n"
        "      signal: ['dropped']\n",
        encoding="utf-8",
    )
    with pytest.raises(QueryContractError, match="decided_at_extration"):
        load_queries(path)


def test_alias_b_is_required_where_the_contract_uses_it():
    """Rendering `{alias_b}` literally would match nothing and read as silence."""
    directional = TermSet(subject=("{alias}",), topic=("replaced {alias_b}",), signal=("kept it",))
    with pytest.raises(MissingPlaceholderError):
        directional.substitute("claude sonnet 5")
    rendered = directional.substitute("claude sonnet 5", "gpt-4.1 mini")
    assert rendered.topic == ("replaced gpt-4.1 mini",)
    assert rendered.unresolved == ()


# ── the sieve: what the index cannot do ──────────────────────────────────


def test_a_phrase_is_a_phrase_here_even_though_it_is_not_on_github():
    """`"should have been null"` returns 1,836 unrelated results as a query.

    Four required tokens scattered through a document is what the index reads.
    The sieve reads the phrase, which is the entire reason the terms are written
    for it.
    """
    scattered = "you should ask what could have been done; the field was left as a null"
    exact = "the field was absent and it should have been null in the output"
    assert not matches("should have been null", normalize(scattered))
    assert matches("should have been null", normalize(exact))


def test_a_phrase_matches_across_a_line_break():
    """Real HTML wraps. A term that fails on a newline fails silently."""
    assert matches("left out", normalize("it consistently left\n   out the clause"))


def test_deliberate_stems_work_here_and_only_here():
    """`moralis` matches exactly one document on GitHub — issue #4 of this repo.

    It is written as a stem for the sieve, where it does the job intended.
    """
    assert matches("moralis", normalize("it kept moralising at me"))
    assert matches("moraliz", normalize("constant moralizing preamble"))
    assert matches("hallucinat", normalize("it hallucinated the API"))


def test_inflections_match_because_the_index_does_no_stemming():
    """`truncate` 2,136 · `truncates` 180 · `truncated` 1,334 — three tokens there."""
    for text in ("it truncated the file", "it truncates output", "it will truncate"):
        assert matches("truncate", normalize(text)), text


def test_short_terms_are_not_extended_into_other_words():
    """`code` must not reach `codebase`, or the sieve stops narrowing anything."""
    assert not matches("code", normalize("the codebase is large"))
    assert matches("code", normalize("the code is wrong"))


def test_typographic_apostrophes_do_not_break_a_term():
    """The contract writes `didn't follow`; people type `didn’t follow`."""
    assert matches("didn't follow", normalize("it didn’t follow the schema"))


def test_subject_is_all_of_and_the_other_groups_are_any_of():
    terms = entry().terms.substitute("claude sonnet 5")
    document = "claude sonnet 5 dropped the cancellation clause from every summary"
    verdict = sieve(terms, document)
    assert verdict.passed
    assert verdict.subject == ("claude sonnet 5",)
    assert set(verdict.topic) == {"summary"}
    assert verdict.signal == ("dropped",)


def test_a_document_missing_the_model_fails_and_says_which_group():
    terms = entry().terms.substitute("claude sonnet 5")
    verdict = sieve(terms, "the summary dropped a clause")
    assert not verdict.passed
    assert verdict.missing == ("subject",)


def test_a_spelling_the_contract_does_not_carry_is_not_invented_here():
    """`summariser` is not reachable from `summary`, and should not be.

    The stem expansion is bounded on purpose. Covering both spellings is the
    contract's job — the real file lists `summarize` and `summarise` side by
    side — and guessing at it here would put vocabulary in code, where rule 5
    says it does not belong.
    """
    assert not matches("summary", normalize("the summariser dropped a clause"))
    assert matches("summarise", normalize("the summariser dropped a clause"))


def test_an_off_topic_document_fails_on_topic_not_on_subject():
    terms = entry().terms.substitute("claude sonnet 5")
    verdict = sieve(terms, "claude sonnet 5 dropped a tool call")
    assert not verdict.passed
    assert verdict.missing == ("topic",)


def test_an_empty_group_fails_rather_than_passing_vacuously():
    """`subject` alone is the collapsed state issue #4 documents."""
    hollow = TermSet(subject=("{alias}",), topic=(), signal=("dropped",))
    verdict = sieve(hollow.substitute("claude sonnet 5"), "claude sonnet 5 dropped it")
    assert not verdict.passed
    assert "topic" in verdict.missing


def test_tally_counts_and_never_drops():
    """The yield figure `yields_claim_when` needs, one layer earlier."""
    terms = entry().terms.substitute("claude sonnet 5")
    documents = [
        "claude sonnet 5 dropped the clause from the summary",
        "claude sonnet 5 is fast",
        "some other model dropped a summary detail",
    ]
    counts = tally("q1", (sieve(terms, d) for d in documents))
    assert counts.candidates == 3
    assert counts.kept == 1
    assert counts.missing_subject == 1
    assert round(counts.pass_rate, 2) == 0.33


# ── GitHub retrieval ─────────────────────────────────────────────────────


def test_a_trailing_numeral_is_hyphenated_so_it_cannot_match_an_issue_number():
    """`"claude sonnet 5"` collected issue #5 from 89 unrelated repositories."""
    assert github_alias_form("claude sonnet 5") == "claude-sonnet-5"
    assert github_alias_form("sonnet 5") == "sonnet-5"
    assert github_alias_form("claude haiku 4.5") == "claude-haiku-4.5"


def test_an_alias_whose_numeral_is_not_last_is_left_alone():
    assert github_alias_form("gpt-4.1 mini") == "gpt-4.1 mini"
    assert github_alias_form("claude sonnet") == "claude sonnet"


def test_no_rendered_query_contains_syntax_the_index_discards():
    queries = load_queries()
    plan = plan_searches(queries.capability_queries, ALIASES, scope=SWEEP)
    assert plan.requests
    for request in plan.requests:
        for token in FORBIDDEN_SYNTAX:
            assert token not in request.query, f"{request.query!r} contains {token!r}"


def test_the_syntax_guard_refuses_rather_than_warning():
    with pytest.raises(UnrenderableError):
        assert_renderable_syntax('"claude" (summar* OR condense) type:issue')


def test_one_request_per_entry_and_alias_not_per_term_pair():
    """830 topic × signal pairs × 59 aliases is 48,616 requests and 30.9 hours."""
    queries = load_queries()
    plan = plan_searches(queries.capability_queries, ALIASES, scope=SWEEP)
    # ALIASES holds three spellings that render to two distinct queries:
    # `claude sonnet 5` and `claude-sonnet-5` are one request on this index.
    distinct = {github_alias_form(a) for a in ALIASES}
    assert plan.request_count == len(queries.capability_queries) * len(distinct)
    assert plan.minutes_at(30) < 3


def test_scope_qualifiers_are_carried_through_because_they_union():
    """`org:langchain-ai` 475 + `org:run-llama` 56 = exactly 531 together."""
    rendered = render_search(entry(), "claude sonnet 5", scope=SWEEP)
    assert isinstance(rendered, SearchRequest)
    for qualifier in SWEEP:
        assert qualifier in rendered.query
    assert "type:issue" in rendered.query


def test_one_narrowing_token_is_chosen_and_multi_word_terms_are_left_to_the_sieve():
    rendered = render_search(entry(), "claude sonnet 5", scope=SWEEP)
    assert rendered.narrowing_token == "summarization"
    assert "left out" not in rendered.query
    assert "should have been null" not in rendered.query


def test_an_entry_with_no_usable_token_still_renders():
    """Fewer terms is a broader query, not a failed one — the sieve narrows it."""
    weak = entry(terms=TermSet(subject=("{alias}",), topic=("the", "a"), signal=("dropped",)))
    rendered = render_search(weak, "claude sonnet 5")
    assert isinstance(rendered, SearchRequest)
    assert rendered.narrowing_token is None
    assert rendered.query.startswith("claude-sonnet-5")


def test_substitution_is_refused_with_the_measurement_in_the_reason():
    """53 against 52. The retrieved set cannot carry direction.

    THIS TEST ASSERTS THE MEASUREMENT, NOT THE FIELD NAME, and that is the point
    of it. The failure mode it exists for is a refusal decaying into a bare
    `NotImplementedError` — it has caught that once already. A refusal that has
    lost its numbers is indistinguishable from one that never had them, and the
    numbers are what let a reader disagree.

    So the field rename from `requires: phrase_binding` to
    `direction: decided_at_extraction` deliberately did not touch these
    assertions: they were never about the flag.
    """
    queries = load_queries()
    plan = plan_searches(queries.substitution, ALIASES, scope=SWEEP)
    assert plan.request_count == 0
    assert len(plan.refusals) == 2
    assert all(isinstance(r, Unrenderable) for r in plan.refusals)

    reason = plan.refusals[0].reason
    assert "53" in reason and "52" in reason, "the measurement, without which it is an opinion"
    assert "direction" in reason
    assert "superset" in reason, "and what retrieval CAN still do"


def test_both_aliases_are_hyphenated_for_retrieval_and_neither_for_the_sieve():
    """Latent behind the refusal, and it stopped being harmless on this change.

    `parts` is built from the SUBJECT group, so moving `{alias_b}` there puts the
    second model into the query. Hyphenating one alias and not the other issues
    `claude-opus-5 "claude sonnet 5"` and collects issue #5 from unrelated
    repositories through the half that kept its trailing numeral — 89 of 123
    results at one scope, measured, which is what `github_alias_form` exists to
    stop.

    Rendered from a capability-shaped entry, since substitution never reaches
    here: the direction refusal returns first, by design.
    """
    both = entry(
        terms=TermSet(
            subject=("{alias}", "{alias_b}"), topic=("replaced",), signal=("held up",)
        )
    )
    rendered = render_search(both, "claude opus 5", alias_b="claude sonnet 5")
    assert isinstance(rendered, SearchRequest)
    assert "claude-opus-5" in rendered.query and "claude-sonnet-5" in rendered.query
    assert '"claude opus 5"' not in rendered.query, "the spaced form collects issue #5"
    # The sieve still reads what a human wrote, both times.
    assert rendered.terms.subject == ("claude opus 5", "claude sonnet 5")


def test_a_refusal_is_returned_not_raised():
    """Coverage the platform cannot provide belongs on a page, not in a traceback."""
    directional = entry(direction="decided_at_extraction")
    assert isinstance(render_search(directional, "claude sonnet 5"), Unrenderable)


def test_the_query_key_is_the_query_as_issued():
    """`watermark.query_key` and `harvest_run.query_key` must name what ran."""
    rendered = render_search(entry(), "claude sonnet 5", scope=SWEEP)
    assert rendered.query_key == rendered.query


def test_retrieval_is_broad_and_the_sieve_is_what_narrows():
    """The two halves, end to end, on one document.

    The rendered query is deliberately loose — alias plus one token — and the
    document that survives is chosen locally.
    """
    plan = plan_searches([entry()], ("claude sonnet 5", "claude-sonnet-5"), scope=SWEEP)
    request = plan.requests[0]
    assert request.query.startswith("claude-sonnet-5"), "retrieval hyphenates the numeral"

    prose = "claude sonnet 5 dropped the cancellation clause from the summary"
    identifier = "claude-sonnet-5 dropped the cancellation clause from the summary"
    junk = "claude-sonnet-5 summarization is great, no complaints"

    assert request.sieve(prose).passed, "the spelling people actually write"
    assert request.sieve(identifier).passed
    assert not request.sieve(junk).passed


# ── deduplication: the index collapses spellings, the sieve must not ──────


def test_spellings_that_collapse_on_the_index_are_one_request(tmp_path):
    """`claude opus 5` and `claude-opus-5` hyphenate to the same query.

    Issuing both buys the same documents twice — 59 alias strings do not mean 59
    distinct GitHub queries.
    """
    plan = plan_searches([entry()], ("claude sonnet 5", "claude-sonnet-5"), scope=SWEEP)
    assert plan.request_count == 1
    assert plan.requests[0].query.startswith("claude-sonnet-5")
    # One request, both human spellings kept — the sieve needs the prose form.
    assert plan.requests[0].aliases == ("claude sonnet 5", "claude-sonnet-5")


def test_a_deduplicated_request_keeps_every_spelling_for_the_sieve():
    """Retrieve once, sieve against every form.

    The document says one spelling or the other. A sieve given only the
    hyphenated form drops every post written in prose, which is most of them.
    """
    plan = plan_searches([entry()], ("claude sonnet", "claude-sonnet-5"), scope=SWEEP)
    forms = {v.alias for request in plan.requests for v in request.variants}
    assert "claude sonnet" in forms
    assert "claude-sonnet-5" in forms

    prose = "claude sonnet dropped the clause from the summary"
    identifier = "claude-sonnet-5 dropped the clause from the summary"
    for document in (prose, identifier):
        assert any(
            sieve(v, document).passed for request in plan.requests for v in request.variants
        ), document


def _real_plans():
    """The two sweeps as they would actually be issued, split by cadence."""
    from collect.adapters.queries.cadence import split_by_cadence
    from collect.registry.aliases import all_alias_rows, search_queries
    from collect.registry.seed import seed_models

    queries = load_queries()
    aliases = search_queries(all_alias_rows(seed_models()))
    groups = split_by_cadence(queries.capability_queries)
    return queries, aliases, {
        cadence: plan_searches(entries, aliases, scope=SWEEP)
        for cadence, entries in groups.items()
    }


def test_the_real_sweep_is_costed_before_it_runs():
    """The number issue #4 says nobody computed until an adapter was written.

    Costed per cadence, because that is the constraint that is real. One
    number over everything said 1,344 against 900 after PR #8 and offered no
    move except raising it.
    """
    from collect.adapters.queries.cadence import THE_MOVES, assert_within_budget

    queries, aliases, plans = _real_plans()

    for cadence, plan in plans.items():
        # Raises HarvestBudgetError naming the cadence, the new figure and the
        # three moves. That message is the whole point — see
        # test_the_refusal_reads_as_a_decision_not_an_obstacle.
        assert_within_budget(cadence, plan)

    cartesian = sum(
        len(e.terms.topic) * len(e.terms.signal) for e in queries.capability_queries
    ) * len(aliases)
    total = sum(plan.request_count for plan in plans.values())
    assert total < cartesian / 50, f"the pair rendering costs 30.9 hours. {THE_MOVES}"


def test_the_daily_headroom_is_small_enough_to_need_a_decision():
    """A finding, pinned so it cannot be discovered again in production.

    Four requests as this lands. One more capability or alias variant breaches
    the daily budget by construction, which is the cap working — but only if
    whoever hits it reads a decision rather than an obstacle.

    Deliberately does NOT re-assert the ceiling. `assert_within_budget` owns
    that, and two tests failing for one cause is two chances to misread it.
    """
    from collect.adapters.queries.cadence import headroom, load_budgets

    _, _, plans = _real_plans()
    left = headroom("daily", plans["daily"])
    cap = load_budgets()["daily"].max_requests

    if left < 0:
        pytest.skip(
            f"daily sweep is {-left} requests over the {cap} ceiling — "
            "test_the_real_sweep_is_costed_before_it_runs is the failure to read"
        )

    assert left < 60, (
        f"daily headroom has grown to {left} of {cap} requests. Either the "
        "sweep shrank or the ceiling moved; if the ceiling moved, the reason "
        "belongs in contract/harvest.yaml next to the number."
    )


def test_the_cadence_split_drops_nothing():
    """The split has to move cost, not lose queries.

    Derived from the plans rather than pinned to 1,344: a hardcoded total
    breaks the day a capability is added, which is the one day this test needs
    to be readable, and it breaks saying "nothing was dropped" when the real
    news is that the sweep grew.
    """
    from collect.adapters.queries.cadence import split_by_cadence

    queries, aliases, plans = _real_plans()
    whole = plan_searches(queries.capability_queries, aliases, scope=SWEEP)

    split_total = plans["daily"].request_count + plans["weekly"].request_count
    assert split_total == whole.request_count, "the split moved cost, not queries"

    groups = split_by_cadence(queries.capability_queries)
    assert sum(len(g) for g in groups.values()) == len(queries.capability_queries)

    amortised = plans["daily"].request_count + plans["weekly"].request_count / 7
    assert amortised < split_total, "weekly costs less per day than daily, by definition"


def test_the_refusal_reads_as_a_decision_not_an_obstacle():
    """`assert 900 < 900` invites raising the constant. This must not.

    Whoever sees this is part-way through adding a capability and looking for
    the cheapest way out. The message has to carry the new figure — so the
    cost is concrete — and the three moves that are decisions, next to the one
    that is not.
    """
    from collect.adapters.queries.cadence import (
        CadenceBudget,
        HarvestBudgetError,
        assert_within_budget,
    )

    _, _, plans = _real_plans()
    cost = plans["daily"].request_count
    tiny = {"daily": CadenceBudget("daily", max_requests=10, max_minutes=1, every_days=1)}

    with pytest.raises(HarvestBudgetError) as excinfo:
        assert_within_budget("daily", plans["daily"], budgets=tiny)

    message = str(excinfo.value)
    assert "daily sweep is over budget" in message
    assert f"{cost} requests against a ceiling of 10" in message, (
        "the message must name what the sweep actually costs now, derived — "
        "a pinned figure here goes stale the moment the sweep changes"
    )
    for move in ("alias_search", "longer cadence", "partition the models"):
        assert move in message, f"the message must name the {move!r} move"
    assert "is the option that is not a decision" in message

    # And it must NOT offer the one that was measured to do nothing: scope is
    # a qualifier inside a query, not a multiplier of queries, so one repo and
    # two repos cost the same. Naming an inert lever at the cap is worse than
    # naming one fewer, because somebody reaches for it.
    assert "narrow the sweep scope" not in message
    assert "NOT a narrower sweep scope" in message


def test_an_undeclared_cadence_is_refused_rather_than_waved_through():
    """Rule 6: no budget is not an unlimited budget."""
    from collect.adapters.queries.cadence import HarvestBudgetError, assert_within_budget

    _, _, plans = _real_plans()
    with pytest.raises(HarvestBudgetError, match="no budget declared"):
        assert_within_budget("hourly", plans["daily"])


def test_two_entries_sharing_a_query_keep_their_own_sieve_terms():
    """Deduplicating across entries would drop the positive stance silently.

    `context.effective_window` negative and positive narrow on the same token,
    so their queries are identical. Their signal terms are opposites, and the
    positive one exists so a silent-failure capability can reach positive
    consensus at all.
    """
    queries = load_queries()
    window = queries.for_capability("context.effective_window")
    assert {e.stance for e in window} == {"negative", "positive"}

    plan = plan_searches(window, ("claude sonnet 5",), scope=SWEEP)
    assert plan.request_count == 2, "one per entry"
    assert plan.distinct_queries <= 2

    held = "claude sonnet 5 recall held up fine at 200k in our eval"
    lost = "claude sonnet 5 recall degrades past 180k, loses the middle"
    by_stance = {r.entry_label: r for r in plan.requests}
    assert by_stance["context.effective_window:positive"].sieve(held).passed
    assert not by_stance["context.effective_window:positive"].sieve(lost).passed
    assert by_stance["context.effective_window:negative"].sieve(lost).passed


def test_a_request_sieves_with_every_spelling_not_the_one_that_found_the_document():
    """The live defect: which spelling FOUND a document says nothing about how
    the document NAMES the model.

    Measured on the first GitHub run — checking only the retrieving spelling put
    the subject-miss rate at 88.6%, checking all six forms put it at 66.9% over
    the same 136 documents. Twenty-eight recovered for zero extra requests.
    """
    forms = ("claude sonnet", "claude-sonnet-5", "sonnet 5")
    plan = plan_searches([entry()], forms, scope=SWEEP)

    for request in plan.requests:
        assert set(request.aliases) == set(forms), request.query

    # A request rendered from one spelling must keep a document that uses another.
    request = plan.requests[0]
    written_another_way = "claude-sonnet-5 dropped the clause from the summary"
    assert request.sieve(written_another_way).passed


def test_subject_forms_can_be_supplied_when_a_sweep_spans_models():
    """Mixing two models' spellings into one subject check would let a post about
    one satisfy a query about the other."""
    plan = plan_searches(
        [entry()], ("claude sonnet 5",), scope=SWEEP, subject_forms=("claude sonnet 5",)
    )
    assert plan.requests[0].aliases == ("claude sonnet 5",)
    assert not plan.requests[0].sieve("gpt-4.1 mini dropped the summary clause").passed
