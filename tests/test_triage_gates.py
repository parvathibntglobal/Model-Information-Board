"""E4's hard gates, and the surface population they resolve against.

Two groups carry the weight.

**A gate that cannot run has not passed the document.** Language and the bot
list are not built, and a survival rate that counts their absence as a pass is a
number about our coverage wearing the clothes of a number about the corpus.
Every test asserting `unavailable` is defending that.

**The population has an identity.** The same document flips verdict when the
alias set changes - 17.3% of the substitution corpus does - so a verdict without
a fingerprint beside it is not reproducible.
"""

from __future__ import annotations

from collect.triage.entity import (
    DECLARED,
    MECHANICAL,
    VENDOR_DROP,
    build_population,
    normalize,
    resolve,
)
from collect.triage.gates import (
    KNOWN_BOT,
    LANGUAGE,
    NO_ENTITY,
    OUT_OF_WINDOW,
    PURE_LINK,
    TOO_SHORT,
    Document,
    NotRun,
    Verdict,
    known_bot,
    out_of_window,
    pure_link_post,
    too_short,
    triage,
    triage_all,
    wrong_language,
)

MODELS = [
    ("anthropic/claude-opus-5", "Anthropic: Claude Opus 5"),
    ("google/gemini-2.5-flash", "Google: Gemini 2.5 Flash"),
    ("qwen/qwen3.8-27b", "Qwen: Qwen3.8 27B"),
    ("mistralai/mistral-large-3", "Mistral: Large 3"),
]

#: Two of the 27 surfaces in `seed_models.yaml` that no derivation reaches.
DECLARED_SURFACES = ["deepseek r1", "flash 2.5", "opus"]


def population():
    return build_population(MODELS, DECLARED_SURFACES)


def doc(text: str, **kw) -> Document:
    return Document(text=text, **kw)


# ── the population ───────────────────────────────────────────────────────


def test_the_registry_half_makes_a_new_model_resolvable_the_night_it_is_polled():
    """The case the whole union exists for: `qwen3.8-27b` has no hand-written
    alias and must still be recognised."""
    pop = population()
    assert resolve("tried qwen 3.8 27b last night", pop)


def test_a_declared_surface_no_derivation_reaches_is_kept():
    """`deepseek r1` — the detector cannot see letter-prefixed versions and no
    rule derives them, so dropping the declared list loses this document."""
    pop = population()
    assert resolve("deepseek r1 handled the retry fine", pop)


def test_bare_family_words_are_excluded_from_every_part():
    """`opus` is declared, and still must not enter.

    62% of family-word mentions carry no version, so a bare family word names a
    line rather than a tier. Admitting it would pass a document whose claim
    `classify_specificity` ranks `family` — one that can never lift a cell.
    """
    pop = population()
    assert "opus" not in pop.surfaces
    assert not resolve("opus is doing great today", pop)


def test_every_contributing_half_is_counted_separately():
    pop = population()
    assert pop.contributions[MECHANICAL] > 0
    assert pop.contributions[VENDOR_DROP] > 0
    assert pop.contributions[DECLARED] > 0


def test_the_fingerprint_changes_when_the_population_does():
    """The reproducibility guarantee. Same code, one more model, different id."""
    a = build_population(MODELS, DECLARED_SURFACES)
    b = build_population([*MODELS, ("openai/gpt-5", "OpenAI: GPT-5")], DECLARED_SURFACES)
    assert a.fingerprint != b.fingerprint


def test_the_fingerprint_is_stable_across_runs_and_input_order():
    a = build_population(MODELS, DECLARED_SURFACES)
    b = build_population(list(reversed(MODELS)), list(reversed(DECLARED_SURFACES)))
    assert a.fingerprint == b.fingerprint


def test_resolution_is_spelling_insensitive():
    pop = population()
    for spelling in ("Claude Opus 5", "claude-opus-5", "claudeopus5", "opus 5"):
        assert resolve(spelling, pop), spelling


def test_matches_are_returned_most_specific_first():
    """A caller taking the first match should get the one that names the most."""
    pop = population()
    hits = resolve("we moved to claude opus 5 in March", pop)
    assert len(normalize(hits[0])) >= len(normalize(hits[-1]))


def test_a_declared_only_surface_carries_no_owner_rather_than_a_guessed_one():
    """`build_population` was not given the seed file's model mapping, so the
    owner is unknown. Unknown stays unknown (rule 6)."""
    pop = population()
    assert pop.owners.get("deepseek r1") is None


# ── gates that produce no verdict say WHICH KIND of nothing ──────────────
#
# Never False, and since 2026-08-19 never a bare None either. `UNAVAILABLE` is
# a build defect that a fix clears for every document at once; `NOT_APPLICABLE`
# is a property of the document and permanent. Each test below names one.


def test_language_is_unavailable_with_no_allow_list():
    """Nothing is configured. Configuring it fixes the whole corpus."""
    assert wrong_language(doc("hello"), allowed=None) is NotRun.UNAVAILABLE


def test_language_is_not_applicable_when_the_document_has_no_detected_language():
    """`document.lang` is nullable. Treating NULL as English would pass every
    document while looking like a gate.

    The allow-list is supplied here on purpose: with `allowed=None` the gate
    reports UNAVAILABLE first, which is the truthful answer while no detector
    exists. This test is about the OTHER branch, and it is the one that starts
    firing per-document once a detector lands."""
    assert (
        wrong_language(doc("hello", lang=None), allowed=frozenset({"en"}))
        is NotRun.NOT_APPLICABLE
    )


def test_a_missing_allow_list_outranks_a_missing_language():
    """Order matters: a build defect must not be reported as permanent.

    Both are absent today. Reporting NOT_APPLICABLE would say "these documents
    cannot be language-gated", when the truth is "nobody has configured or
    installed anything yet" - a defect that hides itself by looking permanent.
    """
    assert wrong_language(doc("hello", lang=None), allowed=None) is NotRun.UNAVAILABLE


def test_language_drops_only_on_a_real_detection():
    assert wrong_language(doc("bonjour", lang="fr"), allowed=frozenset({"en"})) is True
    assert wrong_language(doc("hi", lang="en-GB"), allowed=frozenset({"en"})) is False


# ── the bot gate: FOUR answers, and it is keyed on the account id ────────
#
# ⚠ REWRITTEN 2026-09-07, AND THE OLD CONTRACT WAS NOT EQUIVALENT. `known_bot`
#   used to match `doc.author`, the handle, against a `frozenset[str]`. It now
#   takes a `BotList` and matches `(doc.source, doc.author_external_id)`.
#
#   The change is not a refactor: a login is mutable wherever renames exist, so
#   a list keyed on one stops matching the day an account is renamed - with no
#   error, no count, and a bot back in the voice pool. `author.external_id` is
#   what `document.author_id` resolves through, so the list is now keyed on the
#   same thing the voice count is.
#
#   It also splits UNAVAILABLE in two: no list at all, and a list that declares
#   nothing for THIS platform. The second shrinks as each platform is curated,
#   which is what UNAVAILABLE is for.


def _bots(source="reddit", ids=(), id_space="reddit_fullname"):
    from collect.triage.bots import BotList, BotSource

    return BotList(
        by_source={
            source: BotSource(
                source=source, id_space=id_space, account_ids=frozenset(ids)
            )
        }
    )


def _bot_doc(**kwargs):
    fields = {"source": "reddit", "author_external_id": "t2_abc", "author": "somebot"}
    fields.update(kwargs)
    return doc("x", **fields)


def test_the_bot_gate_is_unavailable_with_no_list():
    """No list exists in contract/. That is not an empty list."""
    assert known_bot(_bot_doc(), bots=None) is NotRun.UNAVAILABLE


def test_an_empty_bot_list_is_a_different_statement_from_no_list():
    """`accounts: []` on a declared source is a MEASUREMENT: somebody looked."""
    assert known_bot(_bot_doc(), bots=_bots(ids=())) is False


def test_a_source_the_list_does_not_declare_is_unavailable_not_false():
    """The distinction the whole loader exists for.

    A platform nobody has curated is a CURATION GAP - one YAML block fixes it
    for every document on that platform - so it is UNAVAILABLE, and the count
    falls as each platform is read. `False` there would assert that somebody
    checked Hacker News and found no bots, which nobody has.
    """
    assert (
        known_bot(_bot_doc(source="hackernews"), bots=_bots(source="reddit"))
        is NotRun.UNAVAILABLE
    )


def test_the_bot_gate_matches_on_the_id_and_never_on_the_handle():
    """The rename case, which is the reason for the change.

    The document's handle is in the list and its id is not. A handle-keyed gate
    would drop it; this one keeps it, because the handle is not evidence of
    identity - and the same asymmetry is what makes a renamed bot still match.
    """
    listed_by_handle = _bots(ids=("somebot",))
    assert known_bot(_bot_doc(author="somebot"), bots=listed_by_handle) is False

    listed_by_id = _bots(ids=("t2_abc",))
    assert known_bot(_bot_doc(author="a-new-name"), bots=listed_by_id) is True


def test_the_bot_gate_is_not_applicable_when_there_is_no_identity():
    """A deleted account has no id to test, and never will. Not a build defect."""
    assert (
        known_bot(_bot_doc(author_external_id=None), bots=_bots(ids=("t2_abc",)))
        is NotRun.NOT_APPLICABLE
    )


def test_an_id_without_its_platform_is_not_applicable():
    """`author` is UNIQUE (source, external_id), so an id alone is ambiguous.

    Two platforms can legitimately issue the same numeric id, and matching
    without the source would filter a human on the other one.
    """
    assert (
        known_bot(_bot_doc(source=None), bots=_bots(ids=("t2_abc",)))
        is NotRun.NOT_APPLICABLE
    )


def test_a_link_post_gate_is_not_applicable_where_the_platform_has_no_such_notion():
    """A blog article must not be dropped by a Reddit-shaped rule.

    This is the gate that made the single `unavailable` count grow as coverage
    improved: every blog article added one, and the number read as the gates
    degrading while the corpus was widening."""
    assert pure_link_post(doc("an article", is_self_post=None)) is NotRun.NOT_APPLICABLE


# ── gates that do run ────────────────────────────────────────────────────


def test_a_link_post_with_commentary_is_kept():
    """392 of 536 link posts in the corpus carry commentary. Dropping all of
    them would discard the part an engineer wrote."""
    assert pure_link_post(doc("t", is_self_post=False, body="here is why")) is False


def test_a_link_post_with_no_commentary_is_dropped():
    assert pure_link_post(doc("t", is_self_post=False, body="")) is True


def test_a_short_document_carrying_an_artifact_survives():
    """`TypeError: 'NoneType' object is not subscriptable` is a complete bug
    report in eleven tokens. Length alone cannot tell it from 'this is amazing'."""
    assert too_short(doc("TypeError: 'NoneType' object is not subscriptable")) is False


def test_a_short_document_with_no_artifact_is_dropped():
    assert too_short(doc("this is amazing")) is True


def test_a_long_opinion_survives_the_length_gate():
    assert too_short(doc(" ".join(["words"] * 30))) is False


# ── the window gate, and its three refusals ──────────────────────────────


def test_out_of_window_drops_only_when_every_named_model_is_out():
    pop = population()
    matched = resolve("claude opus 5 and gemini 2.5 flash", pop)
    both_out = dict.fromkeys(["anthropic/claude-opus-5", "google/gemini-2.5-flash"], False)
    assert out_of_window(matched, population=pop, in_window=both_out) is True


def test_one_in_window_model_keeps_the_document():
    pop = population()
    matched = resolve("claude opus 5 and gemini 2.5 flash", pop)
    mixed = {"anthropic/claude-opus-5": True, "google/gemini-2.5-flash": False}
    assert out_of_window(matched, population=pop, in_window=mixed) is False


def test_the_window_gate_is_not_applicable_when_nothing_matched():
    """The entity gate owns that document. This one has no opinion."""
    pop = population()
    assert out_of_window((), population=pop, in_window={}) is NotRun.NOT_APPLICABLE


def test_the_window_gate_is_not_applicable_when_no_match_has_a_known_owner():
    """A declared-only surface has no owner, so the document cannot be placed.

    NOT_APPLICABLE rather than UNAVAILABLE: nothing is missing from the build.
    The document names a model we cannot attribute, which is about the document.
    """
    pop = population()
    matched = resolve("deepseek r1 was fine", pop)
    assert matched
    assert (
        out_of_window(matched, population=pop, in_window={"x/y": False})
        is NotRun.NOT_APPLICABLE
    )


def test_a_model_absent_from_the_window_map_is_unknown_not_out():
    """Rule 6: an absent flag is not a False one."""
    pop = population()
    matched = resolve("claude opus 5", pop)
    assert out_of_window(matched, population=pop, in_window={}) is NotRun.NOT_APPLICABLE


# ── the whole stage ──────────────────────────────────────────────────────


def test_a_good_document_is_kept_and_says_which_gates_did_not_run():
    pop = population()
    result = triage(
        doc(
            "We moved the summariser to claude opus 5 and latency went from "
            "1200ms to 400ms across roughly 4k requests a day.",
            is_self_post=True,
        ),
        population=pop,
    )
    assert result.verdict is Verdict.KEPT
    assert result.reasons == ()
    # Three gates produce no verdict, and they are no longer one list. Language
    # and the bot list are unconfigured - a fix clears both for every document.
    # The window gate has nothing to place: no matched surface has a known
    # owner, which is about this document.
    assert set(result.unavailable) == {LANGUAGE, KNOWN_BOT}
    assert set(result.not_applicable) == {OUT_OF_WINDOW}
    assert set(result.no_verdict) == {LANGUAGE, OUT_OF_WINDOW, KNOWN_BOT}
    assert result.fully_gated is False


def test_a_document_naming_no_model_is_dropped():
    pop = population()
    result = triage(
        doc("Danny Trejo has a great tattoo, honestly incredible stuff right here"),
        population=pop,
    )
    assert result.verdict is Verdict.DROPPED
    assert NO_ENTITY in result.reasons


def test_every_gate_runs_so_reasons_are_not_truncated_by_a_short_circuit():
    """A document failing two gates reports two.

    Short-circuiting would also make `unavailable` mean both "cannot run" and
    "not reached", which is the ambiguity the field exists to remove.
    """
    pop = population()
    result = triage(
        doc("nice", is_self_post=False, body=""), population=pop
    )
    assert TOO_SHORT in result.reasons
    assert PURE_LINK in result.reasons
    assert NO_ENTITY in result.reasons


def test_the_verdict_carries_the_population_that_produced_it():
    pop = population()
    result = triage(
        doc("claude opus 5 is fine and it is a long enough sentence now to pass"),
        population=pop,
    )
    assert result.population_fingerprint == pop.fingerprint


def test_the_same_document_flips_verdict_with_the_population():
    """The reproducibility problem, as a test rather than a docstring.

    `qwen 3.8 27b` is DROPPED by a population without the registry half and KEPT
    by one with it. Nothing about the document changed.
    """
    text = "Tried qwen 3.8 27b overnight and the tool calling fell over at six tools."
    narrow = build_population([("anthropic/claude-opus-5", "Claude Opus 5")], [])
    wide = population()
    assert triage(doc(text), population=narrow).verdict is Verdict.DROPPED
    assert triage(doc(text), population=wide).verdict is Verdict.KEPT


# ── the run summary, and the caveat it must carry ────────────────────────


def test_a_survival_rate_states_that_gates_did_not_run():
    pop = population()
    docs = [
        doc(
            "claude opus 5 held up well across a week of production traffic and "
            "nobody has noticed any regression in that time at all",
            is_self_post=True,
        ),
        doc("nice", is_self_post=True),
    ]
    _, run = triage_all(docs, population=pop)
    assert run.kept == 1
    assert run.dropped == 1
    text = run.describe()
    assert "GATES THAT COULD NOT RUN" in text
    assert "UPPER BOUND" in text


def test_survival_over_an_empty_batch_is_none_not_zero():
    """A rate over nothing is not zero survival."""
    _, run = triage_all([], population=population())
    assert run.survival is None
    assert "not measured" in run.describe()


def test_the_summary_names_its_population():
    pop = population()
    _, run = triage_all(
        [doc("claude opus 5 and a sentence that is long enough to survive here")],
        population=pop,
    )
    assert pop.fingerprint in run.describe()


def test_widening_the_corpus_grows_not_applicable_and_not_never_ran():
    """The direction check, and the reason the two counts are separate.

    A blog article has no link-post flag, so adding one adds a NOT_APPLICABLE.
    Under the old single field that arrived as another "gate that did not run",
    so the number climbed as coverage improved and read as the gates getting
    worse. `never_ran` must not move: no gate became less buildable because a
    blog was harvested.
    """
    pop = population()
    reddit_only = [
        doc("claude opus 5 dropped a tool call after 40 turns", is_self_post=True)
    ]
    with_a_blog = reddit_only + [
        doc("claude opus 5 dropped a tool call after 40 turns", is_self_post=None)
    ]

    _, before = triage_all(reddit_only, population=pop)
    _, after = triage_all(with_a_blog, population=pop)

    assert before.not_applicable.get(PURE_LINK, 0) == 0
    assert after.not_applicable.get(PURE_LINK, 0) == 1
    # No gate became less buildable because a blog was harvested. Both tallies
    # are per document, so both grow with the corpus - what must not grow is the
    # SET of gates the build still owes.
    assert set(after.never_ran) == set(before.never_ran)


def test_the_remedy_asymmetry_is_what_the_two_fields_encode():
    """Supply what the build owes and `never_ran` empties. The other does not.

    This is the whole argument for the split in one assertion: configuration
    clears one field entirely and leaves the other exactly where it was, so a
    reader can tell which part of an upper bound is worth chasing.
    """
    pop = population()
    docs = [
        doc("claude opus 5 dropped a tool call after 40 turns", is_self_post=True),
        doc("claude opus 5 dropped a tool call after 40 turns", is_self_post=None),
    ]

    _, owed = triage_all(docs, population=pop)
    assert owed.never_ran, "language and the bot list are unconfigured today"

    _, supplied = triage_all(
        docs,
        population=pop,
        allowed_languages=frozenset({"en"}),
        # A DECLARED EMPTY LIST for the platform these documents are on. An
        # empty `BotList()` would leave the gate UNAVAILABLE, which is the
        # distinction the loader exists for and not what this test is about.
        bots=_bots(source="reddit", ids=()),
    )

    # The bot gate now runs. Language becomes NOT_APPLICABLE rather than
    # vanishing, because `document.lang` is still NULL per document - which is
    # the honest answer and was invisible while both states shared a field.
    assert KNOWN_BOT not in supplied.never_ran
    assert supplied.never_ran == {}
    assert supplied.not_applicable[PURE_LINK] == owed.not_applicable[PURE_LINK]
    assert supplied.not_applicable[LANGUAGE] == len(docs)


def test_the_two_caveats_are_stated_separately_with_different_remedies():
    """Rule 7: a bound travels with what would change it.

    "Build the detector" and "this is the corpus you have" are different
    answers, and a reader who sees one line cannot tell which they are owed.
    """
    pop = population()
    _, run = triage_all(
        [doc("claude opus 5 dropped a tool call after 40 turns", is_self_post=None)],
        population=pop,
    )
    text = run.describe()

    assert "GATES THAT COULD NOT RUN" in text
    assert "BUILDING THEM RESOLVES IT" in text
    assert "GATES WITH NOTHING TO RUN ON" in text
    assert "PERMANENT" in text


# ── the thread-level subject, ruled 2026-09-08 ───────────────────────────
#
# THE PERMISSION IS NARROW AND EACH BOUNDARY IS A TEST. A reading rule that
# quietly became a resolution rule, or that started DROPPING documents on an
# inherited subject, would be the inheritance ruling reopened by accident -
# and it would be invisible, because the evidence would be gone.


def _comment(text: str, root: str | None, **kw) -> Document:
    """An HN-shaped document: body here, subject in another record."""
    return Document(text=text, thread_subject_text=root, **kw)


def test_a_comment_naming_nothing_inherits_its_threads_subject():
    """The 2.2% problem. Without this the comment is dropped unread."""
    result = triage(
        _comment(
            "switched the router over last week and our monthly bill for the same "
            "traffic fell by roughly a third, which nobody here expected",
            "Claude Opus 5 pricing changed today",
        ),
        population=population(),
    )
    assert result.verdict is Verdict.KEPT
    assert NO_ENTITY not in result.reasons
    assert result.subject_was_inherited is True
    assert result.inherited_surfaces
    # The document's OWN matches stay empty. A reader asking what THIS text
    # named gets the right answer.
    assert result.matched_surfaces == ()


def test_the_documents_own_text_wins_and_is_not_counted_as_inherited():
    """`subject_was_inherited` must mean what it says on every kept document.

    A comment that names the model itself is not an inherited document, however
    clearly its root also names one - otherwise the flag inflates and the count
    beside a survival figure stops separating the two reading units.
    """
    result = triage(
        _comment(
            "claude opus 5 dropped a tool call after 40 turns",
            "Claude Opus 5 pricing changed today",
        ),
        population=population(),
    )
    assert result.matched_surfaces
    assert result.inherited_surfaces == ()
    assert result.subject_was_inherited is False


def test_a_root_that_names_nothing_inherits_nothing():
    """Supplying a root is not a licence to keep the document."""
    result = triage(
        _comment(
            "this is the third time this week and I am losing patience with it",
            "An Alien Mind",
        ),
        population=population(),
    )
    assert result.verdict is Verdict.DROPPED
    assert NO_ENTITY in result.reasons
    assert result.subject_was_inherited is False


def test_a_platform_that_supplies_no_root_behaves_exactly_as_before():
    """Additive, and this is the test that says so.

    Reddit, GitHub and the blogs carry their subject inside the document and
    pass `thread_subject_text=None`. Their verdicts must be byte-identical to
    what they were before 2026-09-08, or this was a change to four platforms
    while claiming to be a change to one.
    """
    text = "the router silently downgraded and I could not tell from the logs"
    without_root = triage(doc(text), population=population())
    assert without_root.verdict is Verdict.DROPPED
    assert NO_ENTITY in without_root.reasons
    assert without_root.inherited_surfaces == ()
    assert without_root.subject_was_inherited is False


def test_an_inherited_subject_can_never_drop_a_document_on_the_window():
    """SCOPED TO THE SUBJECT GATE, and this is the boundary that matters.

    `out_of_window` gets the document's OWN matches and never the union. A
    comment placed outside a release window on the strength of a model named
    only in a title is an invented definite answer (rule 6) - and it would be
    invisible, because the document would be gone. So the window gate stays
    NOT_APPLICABLE on an inherited document, exactly as it was when the entity
    gate dropped that document outright.
    """
    pop = population()
    # Every model in the population is out of the window, so the ONLY thing
    # keeping this document is that the gate declines to place it.
    everything_out = {model_id: False for model_id, _ in MODELS}

    inherited = triage(
        _comment(
            "our monthly bill for the same traffic fell by roughly a third after "
            "we switched the router over, which nobody here expected",
            "Claude Opus 5 is out",
        ),
        population=pop,
        in_window=everything_out,
    )
    assert inherited.subject_was_inherited is True
    assert OUT_OF_WINDOW not in inherited.reasons
    assert OUT_OF_WINDOW in inherited.not_applicable
    assert inherited.verdict is Verdict.KEPT

    # Contrast: a document that names the model ITSELF is placed, and dropped.
    own = triage(
        _comment(
            "claude opus 5 cut our monthly bill for the same traffic by roughly "
            "a third after we switched the router over, unexpectedly",
            "Claude Opus 5 is out",
        ),
        population=pop,
        in_window=everything_out,
    )
    assert OUT_OF_WINDOW in own.reasons
    assert own.verdict is Verdict.DROPPED


def test_an_inherited_subject_does_not_rescue_a_document_the_other_gates_drop():
    """The subject gate is one of six. Inheritance answers only its question."""
    result = triage(
        _comment("+1", "Claude Opus 5 pricing changed today"),
        population=population(),
    )
    assert result.verdict is Verdict.DROPPED
    assert TOO_SHORT in result.reasons
    # Kept by the subject gate, dropped by the length gate, and the flag is
    # still set - it describes HOW the subject was reached, not the verdict.
    assert result.subject_was_inherited is True


def test_all_surfaces_is_the_union_own_first():
    result = triage(
        _comment(
            "our monthly bill for the same traffic fell by roughly a third after "
            "we switched the router over, which nobody here expected",
            "Claude Opus 5 pricing changed",
        ),
        population=population(),
    )
    assert result.all_surfaces == result.matched_surfaces + result.inherited_surfaces
    assert result.all_surfaces == result.inherited_surfaces


def test_the_run_counts_inherited_keeps_and_refuses_to_pool_them_silently():
    """Rule 7 on our own reading unit.

    A survival figure over a mixed population is a number about how we read the
    corpus wearing the clothes of a number about the corpus. The count exists so
    the two can be quoted apart, and `describe` says the population is mixed.
    """
    pop = population()
    docs = [
        # own text
        _comment("claude opus 5 dropped a tool call after 40 turns", None),
        # inherited
        _comment(
            "our monthly bill for the same traffic fell by roughly a third after "
            "we switched the router over, which nobody here expected",
            "Claude Opus 5 pricing",
        ),
        _comment(
            "same here, about a third cheaper for us as well, measured over two "
            "full billing cycles rather than a single week of traffic",
            "Claude Opus 5 price",
        ),
    ]
    _, run = triage_all(docs, population=pop)

    assert run.kept == 3
    assert run.subject_inherited == 2
    text = run.describe()
    assert "SUBJECT INHERITED FROM THE THREAD ROOT" in text
    assert "2 of 3 triaged" in text
    assert "MIXED" in text


def test_a_run_with_no_inheritance_says_nothing_about_it():
    """Silence where there is nothing to report, not a `0` nobody asked for.

    Every platform but Hacker News supplies no root, and a line reading
    "0 inherited" on every blog run trains readers to skip the block that
    matters when it is not zero.
    """
    _, run = triage_all(
        [doc("claude opus 5 dropped a tool call after 40 turns")],
        population=population(),
    )
    assert run.subject_inherited == 0
    assert "SUBJECT INHERITED" not in run.describe()
