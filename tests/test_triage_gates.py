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


# ── gates that cannot run return None, never False ───────────────────────


def test_language_is_unavailable_with_no_allow_list():
    assert wrong_language(doc("hello"), allowed=None) is None


def test_language_is_unavailable_when_the_document_has_no_detected_language():
    """`document.lang` is nullable and nothing populates it. Treating NULL as
    English would pass every document while looking like a gate."""
    assert wrong_language(doc("hello", lang=None), allowed=frozenset({"en"})) is None


def test_language_drops_only_on_a_real_detection():
    assert wrong_language(doc("bonjour", lang="fr"), allowed=frozenset({"en"})) is True
    assert wrong_language(doc("hi", lang="en-GB"), allowed=frozenset({"en"})) is False


def test_the_bot_gate_is_unavailable_with_no_list():
    """No list exists in contract/. That is not an empty list."""
    assert known_bot(doc("x", author="somebot"), bots=None) is None


def test_an_empty_bot_list_is_a_different_statement_from_no_list():
    assert known_bot(doc("x", author="somebot"), bots=frozenset()) is False


def test_the_bot_gate_is_unavailable_when_the_author_is_unknown():
    assert known_bot(doc("x", author=None), bots=frozenset({"bot"})) is None


def test_a_link_post_gate_is_unavailable_where_the_platform_has_no_such_notion():
    """A blog article must not be dropped by a Reddit-shaped rule."""
    assert pure_link_post(doc("an article", is_self_post=None)) is None


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


def test_the_window_gate_is_unavailable_when_nothing_matched():
    """The entity gate owns that document. This one has no opinion."""
    pop = population()
    assert out_of_window((), population=pop, in_window={}) is None


def test_the_window_gate_is_unavailable_when_no_match_has_a_known_owner():
    """A declared-only surface has no owner, so the document cannot be placed."""
    pop = population()
    matched = resolve("deepseek r1 was fine", pop)
    assert matched
    assert out_of_window(matched, population=pop, in_window={"x/y": False}) is None


def test_a_model_absent_from_the_window_map_is_unknown_not_out():
    """Rule 6: an absent flag is not a False one."""
    pop = population()
    matched = resolve("claude opus 5", pop)
    assert out_of_window(matched, population=pop, in_window={}) is None


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
    assert set(result.unavailable) == {LANGUAGE, OUT_OF_WINDOW, KNOWN_BOT}
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
    assert "GATES THAT DID NOT RUN" in text
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
