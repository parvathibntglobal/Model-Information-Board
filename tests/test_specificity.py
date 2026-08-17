"""E4's specificity components and floor.

The tests that matter here are the rule-6 ones. A scorer that reads NULL as
"no signals present" drops every document written before it existed, and does
it silently — which is the shape both lanes have already shipped once.
"""

from __future__ import annotations

import pytest

from collect.triage.specificity import (
    COMPONENTS,
    FloorVerdict,
    Specificity,
    SpecificityContractError,
    filter_reason,
    floor_components,
    floor_verdict,
    has_code,
    has_conditions,
    has_error_strings,
    has_numbers,
    names_version,
    score_document,
    weights,
)

VERSION_ALIASES = ("claude opus 5", "gemini 2.5 flash", "haiku 4.5")


# ── numbers: a quantity, not a digit ─────────────────────────────────────


@pytest.mark.parametrize("text", [
    "p95 was 4.2s under load",
    "it took 1.8s to first token",
    "we ran it on 40k tickets a week",
    "costs $4.10 per million",
    "accuracy dropped 12%",
    "we gave it 14 tools",
    "32k tokens of context",
])
def test_quantities_with_units_are_numbers(text):
    assert has_numbers(text), text


@pytest.mark.parametrize("text", [
    "see issue 4438 for the details",
    "fixes #2685",
    "- 1. first point\n- 2. second point",
    "no numbers here at all, just opinion",
])
def test_bare_digits_are_not_numbers(text):
    """Issue numbers and list markers are the noise this detector must reject.

    A bare integer is what most documents contain and what carries no
    information; counting it would fire the floor on everything.
    """
    assert not has_numbers(text), text


def test_a_version_token_alone_is_not_a_number():
    """`names_version` already counts it. Counting it twice double-weights it."""
    assert not has_numbers("we tried claude opus 5 on this")


# ── error strings: shapes, not vocabulary ────────────────────────────────


@pytest.mark.parametrize("text", [
    "Traceback (most recent call last)",
    "raised a KeyError on the second call",
    "ValidationError: field required",
    "error: cannot find module",
    "got a 429 too many requests every time",
    'File "app.py", line 42',
])
def test_error_shapes_are_detected(text):
    assert has_error_strings(text), text


def test_error_detection_does_not_read_the_capability_vocabulary():
    """A contract signal term is not, by itself, an error string.

    Reusing `contract/queries.yaml`'s error-shaped terms here would couple a
    document-level property to the capability vocabulary: editing one
    capability's terms would silently re-rank thread children in every other
    capability. This test is what makes that coupling fail loudly if added.
    """
    assert not has_error_strings("the json was invalid and it failed to parse")


# ── code: one definition, shared with the sieve ──────────────────────────


@pytest.mark.parametrize("text", [
    "here:\n```python\nprint(1)\n```",
    "run `pip install foo` first",
    "output:\n\n    Traceback\n    boom",
    "<pre>stack trace</pre>",
])
def test_code_containers_are_detected(text):
    assert has_code(text), text


def test_prose_alone_is_not_code():
    assert not has_code("We tried it for a month and it was fine, mostly.")


def test_code_detection_reuses_the_sieve_exclusions():
    """Not a second definition of what code looks like.

    `author_prose` removes these spans to find what the author asserted; this
    reads their presence. Same fact, opposite direction — two definitions
    would drift apart and nobody would notice which was stale.
    """
    from collect.adapters.queries.sieve import author_prose

    text = "before ```code``` after"
    assert author_prose(text) != text
    assert has_code(text)


# ── conditions ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("text", [
    "with 14 tools in scope",
    "at 128k context it fell over",
    "we had json mode on",
    "using response_format with a strict schema",
])
def test_condition_values_are_detected(text):
    assert has_conditions(text), text


def test_conditions_is_the_weakest_detector():
    """Documented as weak, and the test says so rather than pretending.

    A condition stated in prose the pattern does not cover is missed. This is
    a floor input, not a bucket assignment — assigning the band is judge/'s
    and happens per claim.
    """
    assert not has_conditions("we gave it quite a lot of tools at once")


# ── version naming ───────────────────────────────────────────────────────


def test_a_versioned_surface_names_a_version():
    assert names_version("we moved to claude opus 5 in March", VERSION_ALIASES)


def test_a_family_surface_does_not():
    """A bare `sonnet` names a line, not a tier.

    The caller passes version/snapshot surfaces only, so a family mention must
    not score — a migration attributed to a tier nobody used is worse than one
    not scored at all.
    """
    assert not names_version("we moved to sonnet in March", VERSION_ALIASES)


# ── the composite ────────────────────────────────────────────────────────


def test_all_five_components_score_one():
    text = (
        "At 128k context with 14 tools, p95 was 4.2s on claude opus 5:\n"
        "```\nValidationError: field required\n```"
    )
    result = score_document(text, version_aliases=VERSION_ALIASES)
    assert result.components == dict.fromkeys(COMPONENTS, True)
    assert result.score == pytest.approx(1.0)


def test_no_components_score_zero_but_are_not_null():
    result = score_document("It felt worse to me.", version_aliases=VERSION_ALIASES)
    assert result.components == dict.fromkeys(COMPONENTS, False)
    assert result.score == 0.0


def test_the_row_carries_components_and_composite():
    """Six columns. A composite alone cannot explain the floor's verdict."""
    row = score_document("p95 was 4.2s", version_aliases=VERSION_ALIASES).as_row()
    assert set(row) == set(COMPONENTS) | {"specificity_score"}


def test_weights_come_from_the_contract_and_cover_every_component():
    configured = weights()
    assert set(configured) == set(COMPONENTS)
    assert all(v > 0 for v in configured.values())


def test_an_unweighted_component_raises_rather_than_scoring_zero(monkeypatch):
    """A component with no weight would contribute nothing, silently.

    That is a change to every score in the corpus presenting as a working run,
    which is why the loader refuses rather than defaulting (rule 5).
    """
    import collect.triage.specificity as mod

    mod._contract.cache_clear()
    monkeypatch.setattr(mod, "_contract", lambda: {"weights": {"has_numbers": 1.0}})
    with pytest.raises(SpecificityContractError, match="missing"):
        weights()


# ── the floor, and rule 6 ────────────────────────────────────────────────


def test_floor_keeps_a_document_with_one_component():
    components = dict.fromkeys(COMPONENTS, False) | {"has_numbers": True}
    assert floor_verdict(components) is FloorVerdict.KEPT


def test_floor_drops_a_document_with_none():
    assert floor_verdict(dict.fromkeys(COMPONENTS, False)) is FloorVerdict.DROPPED


def test_an_unscored_document_is_unknown_not_dropped():
    """RULE 6. The one that bites on day one.

    Every `document` row written before this module existed carries NULL in all
    six columns. Reading NULL as false drops the entire back catalogue as
    "opinion, not evidence" — an absence with nothing on the page to disagree
    with, which is the expensive class.
    """
    assert floor_verdict(None) is FloorVerdict.UNKNOWN
    assert floor_verdict(dict.fromkeys(COMPONENTS, None)) is FloorVerdict.UNKNOWN


def test_a_partially_scored_document_is_unknown_too():
    """One NULL is enough. A partial row cannot answer the floor's question."""
    components = dict.fromkeys(COMPONENTS, False) | {"has_code": None}
    assert floor_verdict(components) is FloorVerdict.UNKNOWN


def test_unknown_records_itself_in_filter_reasons():
    """Kept-because-unscored must be distinguishable from kept-because-cleared."""
    assert filter_reason(FloorVerdict.KEPT) is None
    assert filter_reason(FloorVerdict.DROPPED) == "specificity-floor"
    assert filter_reason(FloorVerdict.UNKNOWN) == "specificity-unscored"


def test_floor_reads_the_contract_not_a_literal():
    assert set(floor_components()) <= set(COMPONENTS)
    assert floor_components(), "an empty floor would keep everything silently"


# ── the boundary with judge/ ─────────────────────────────────────────────


def test_specificity_is_not_comparable_to_the_claim_weight_factor():
    """They share a word and a range overlap, and mean different things.

    Engineer 2's point, kept as a test rather than only a comment: a reader
    seeing 0.7 in both will want them to mean the same thing. This asserts the
    ranges genuinely differ, so anyone "unifying" them breaks a test.
    """
    from judge.vet.weight import specificity_factor

    floor_of_claim_factor = specificity_factor(
        version_named=False, has_numbers=False,
        has_conditions=False, has_repro_steps=False,
    )
    document_floor = Specificity(
        has_numbers=False, has_error_strings=False, has_code=False,
        has_conditions=False, names_version=False, score=0.0,
    ).score
    assert floor_of_claim_factor == pytest.approx(0.3)
    assert document_floor == 0.0
    assert floor_of_claim_factor != document_floor


def test_has_numbers_falsifies_an_extractor_claim_but_cannot_confirm_it():
    """The asymmetry judge/ depends on, asserted so it cannot be lost.

    False here makes a claim asserting `has_numbers: true` a fabrication —
    there is no number in the document for the quote to contain. True here says
    nothing about whether that particular quote contains one, and reading it as
    confirmation would launder an unverified extractor boolean.
    """
    opinionated = "It felt slower than before, honestly."
    assert not has_numbers(opinionated)

    mixed = "p95 was 4.2s. Separately, it felt slower than before."
    assert has_numbers(mixed)
    quote_without_a_number = "it felt slower than before"
    assert not has_numbers(quote_without_a_number)
