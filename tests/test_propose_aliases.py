"""The alias proposer: three inputs, and empty slots left empty.

The load-bearing tests are the INCOMPLETE ones. Engineer 2's argument: a
generated list that looks complete is worse than a short one known to be short —
the same argument as `phrase_present = None` versus 0. So a slot with no evidence
must be legibly missing, not plausibly filled.

The by-rule tests are load-bearing for a second reason: the vendor-drop rule is
derived from an observation, and the tests that matter are the ones pinning where
it REFUSES to derive. A rule that fired everywhere would be judgement again.
"""

from __future__ import annotations

import pytest

from collect.registry.propose import (
    FAMILY_WORDS,
    INCOMPLETE,
    VENDOR_DROP,
    Attested,
    mechanical_variants,
    propose,
    rule_variants,
    source_split,
    summarise,
    to_yaml,
)

MODELS = [
    ("anthropic/claude-opus-5", "Anthropic: Claude Opus 5"),
    ("google/gemini-3-pro", "Google: Gemini 3 Pro"),
    ("openai/gpt-5", "OpenAI: GPT-5"),
]

#: Real counts from the extract over 5,546 stored documents.
#: `opus 5` carries a by_source split; `gpt-5` deliberately does not, so both
#: branches of `source_split` are covered by the one fixture — a printed split and
#: the honest "split unrecorded" for an extract row that never had one.
OBSERVED = {
    "anthropic/claude-opus-5": [
        Attested("opus 5", 1445, 281,
                 by_source={"reddit-sweep": 1092, "substitution-slice": 348,
                            "reddit-comments": 5}),
        Attested("opus-5", 78, 39, by_source={"reddit-sweep": 70, "substitution-slice": 8}),
    ],
    "openai/gpt-5": [Attested("gpt-5", 311, 103), Attested("gpt5", 50, 10),
                     Attested("gpt 5", 38, 14)],
}


# ── mechanical: derivable, and nothing more ──────────────────────────────


def test_spacing_hyphenation_and_concatenation_are_derived():
    forms = mechanical_variants("google/gemini-3-pro", "Google: Gemini 3 Pro")
    assert "gemini 3 pro" in forms
    assert "gemini-3-pro" in forms
    assert "gemini3pro" in forms


def test_the_vendor_prefix_is_stripped_from_the_display_name():
    """`Google: Gemini 3 Pro` is the feed's form; nobody types the prefix."""
    assert not any(f.startswith("google:") for f in
                   mechanical_variants("google/gemini-3-pro", "Google: Gemini 3 Pro"))


def test_a_bare_family_word_is_never_mechanical():
    """`opus` names a line, not a tier.

    `classify_specificity` ranks it `family`, and a family-specificity claim never
    counts as independent corroboration — so proposing it would add a surface that
    can record a claim and cannot lift a cell.
    """
    for form in mechanical_variants("anthropic/claude-opus-5", "Claude Opus 5"):
        assert form not in FAMILY_WORDS
    assert "opus" not in mechanical_variants("anthropic/opus", "Opus")


def test_short_forms_are_dropped():
    """Below four characters a surface collides with ordinary words."""
    assert all(len(f) >= 4 for f in mechanical_variants("x/o1", "O1"))


def test_mechanical_needs_no_corpus():
    """It is coverage, not recall. A model nobody has mentioned still gets forms."""
    forms = mechanical_variants("z-ai/glm-5v-turbo", "Z.AI: GLM 5V Turbo")
    assert forms


# ── by rule: derived from an observation, and it fires narrowly ───────────


def test_the_vendor_word_is_dropped_and_rendered_three_ways():
    """`claude-opus-5` -> `opus-5` -> `opus 5`, the rule the corpus supplied.

    4,556 mentions sit in `attested-gap`, the largest verdict by mentions, and
    they are one rule: people drop the vendor word.
    """
    assert rule_variants("anthropic/claude-opus-5", "Anthropic: Claude Opus 5") == [
        "opus 5", "opus-5", "opus5",
    ]


def test_the_rule_generalises_across_the_family():
    """Every Anthropic tier, including one the corpus has never attested."""
    assert "sonnet 4.5" in rule_variants("anthropic/claude-sonnet-4.5")
    assert "haiku 4.5" in rule_variants("anthropic/claude-haiku-4.5")
    assert "fable 5" in rule_variants("anthropic/claude-fable-5")


def test_the_rule_refuses_a_reordering():
    """`gemini-2.5-flash` would leave `2.5 flash`. People write `flash 2.5`.

    Reordering is judgement, not a rendering, so the rule stops. The attested
    input is what supplies `flash 2.5` where the corpus has seen it.
    """
    assert rule_variants("google/gemini-2.5-flash", "Google: Gemini 2.5 Flash") == []


def test_the_rule_refuses_a_tier_word_the_corpus_has_not_supplied():
    """`mistral-large-3` almost certainly has a vendor-dropped form.

    `large` is not a family word here, and inventing the tier vocabulary is the
    judgement this module refuses. Returning nothing is a REFUSAL TO DERIVE and
    not a claim that no such surface exists — the reviewer sees the same
    INCOMPLETE slots either way.
    """
    assert rule_variants("mistralai/mistral-large-3") == []


def test_the_rule_stops_at_a_dated_snapshot_id():
    """`haiku 4 5 20251001` is not a form anyone writes.

    18 of 10,255 attested mentions carry a date-shaped token at all.
    """
    assert rule_variants("anthropic/claude-haiku-4-5-20251001") == []


def test_the_rule_refuses_a_route_suffix():
    """`opus 5:batch` is not a form anyone writes, and `opus 5` is not free either.

    Stripping `:batch` would derive the same surface for two canonical ids with
    overlapping validity windows — the ambiguity `AliasCollisionError` refuses at
    load. The dry run over the 155 ids the extract names produced four of these
    before the guard existed.
    """
    assert rule_variants("anthropic/claude-opus-5:batch") == []
    assert rule_variants("anthropic/claude-fable-5:batch") == []
    assert rule_variants("anthropic/claude-opus-5") == ["opus 5", "opus-5", "opus5"]


def test_the_feed_name_cannot_smuggle_a_route_suffix_back_in():
    """The refusal is per MODEL, not per seed.

    A routed id refuses both seeds, or `Anthropic: Claude Opus 5 (batch)` would
    derive `opus 5 (batch)` after the id itself had been turned away.
    """
    assert rule_variants(
        "anthropic/claude-opus-5:batch", "Anthropic: Claude Opus 5 (batch)"
    ) == []
    # And punctuation on an unrouted id is refused on its own account.
    assert rule_variants("anthropic/claude-opus-5", "Anthropic: Claude Opus 5 (beta)") == [
        "opus 5", "opus-5", "opus5",
    ]


def test_the_rule_never_reaches_the_family_surface():
    """It keeps the version token; a family surface is what dropping it produces."""
    for canonical_id in ("anthropic/claude-opus-5", "anthropic/claude-sonnet-4.5"):
        forms = rule_variants(canonical_id)
        assert forms
        assert not any(f in FAMILY_WORDS for f in forms)
        assert all(any(ch.isdigit() for ch in f) for f in forms)


def test_two_tokens_leave_nothing_to_propose():
    """Dropping from `gpt-5` leaves a bare version, and from `deepseek-v3` a bare
    one-token form. Neither is a surface."""
    assert rule_variants("openai/gpt-5", "OpenAI: GPT-5") == []
    assert rule_variants("deepseek/deepseek-v3") == []


def test_a_rule_derived_surface_is_not_the_primary_and_does_not_change_the_status():
    """Two derivations are still no observation.

    A status that improved on a derivation would report the rule's confidence as
    the model's evidence, which is the `phrase_present = None` versus 0 mistake
    with an extra step.
    """
    proposal = next(p for p in propose([("anthropic/claude-fable-5", "Claude Fable 5")]))
    assert proposal.by_rule == ["fable 5", "fable-5", "fable5"]
    assert proposal.surface == INCOMPLETE
    assert proposal.status == "mechanical-only"
    assert "attested_surfaces" in proposal.incomplete


def test_observed_beats_derived_in_the_variant_order():
    """Attested first, then by-rule, then merely derivable."""
    proposal = next(p for p in propose(MODELS, OBSERVED)
                    if p.canonical_id == "anthropic/claude-opus-5")
    variants = proposal.variants
    assert variants.index("opus5") < variants.index("claude opus 5")


def test_a_surface_that_is_both_attested_and_derived_is_the_rules_own_evidence():
    """`opus 5` at 1,445 mentions is what makes the rule more than a guess."""
    proposal = next(p for p in propose(MODELS, OBSERVED)
                    if p.canonical_id == "anthropic/claude-opus-5")
    assert proposal.corroborated_by_rule == ["opus 5", "opus-5"]


def test_the_yaml_keeps_the_three_categories_apart():
    """And it says so on the primary line, where the reviewer starts reading."""
    text = to_yaml(propose(MODELS, OBSERVED))
    assert f"# by rule ({VENDOR_DROP}), unattested" in text
    assert (f"# attested 1445 mentions [sweep 1092, slice 348, comments 5]; "
            f"also derived by {VENDOR_DROP}") in text
    assert (f"# attested 78 mentions [sweep 70, slice 8]; "
            f"also derived by {VENDOR_DROP}") in text
    assert "# mechanical, unattested" in text


def test_the_summary_counts_the_rule_and_its_corroboration():
    summary = summarise(propose(MODELS, OBSERVED))
    assert f"1 carry a {VENDOR_DROP} surface, 1 of those corroborated" in summary


# ── attested: measured, and it drives the primary ────────────────────────


def test_the_primary_surface_is_the_most_mentioned_attested_one():
    """What people actually type, not the first mechanical form.

    `opus 5` at 1,445 mentions beats `claude opus 5`, which is derivable and which
    the corpus shows almost nobody writes.
    """
    proposal = next(p for p in propose(MODELS, OBSERVED)
                    if p.canonical_id == "anthropic/claude-opus-5")
    assert proposal.surface == "opus 5"
    assert proposal.status == "attested"


def test_attested_surfaces_are_ordered_by_how_often_they_were_observed():
    """`gpt5` at 50 mentions before `gpt 5` at 38.

    All three of this model's surfaces are also mechanically derivable, so the
    order here is decided by the counts and by nothing else.
    """
    proposal = next(p for p in propose(MODELS, OBSERVED)
                    if p.canonical_id == "openai/gpt-5")
    variants = proposal.variants
    assert proposal.surface == "gpt-5"
    assert variants.index("gpt5") < variants.index("gpt 5")


def test_proposals_are_ranked_by_how_much_the_corpus_discusses_the_model():
    ranked = [p.canonical_id for p in propose(MODELS, OBSERVED)]
    assert ranked[0] == "anthropic/claude-opus-5", "1,523 mentions"
    assert ranked[-1] == "google/gemini-3-pro", "unattested, so last"


# ── INCOMPLETE: the part that must not be filled ─────────────────────────


def test_the_family_surface_is_always_incomplete():
    """Never derived and never taken from the corpus.

    62% of family-word mentions carry no version at all, so a bare family word is
    attested constantly and attributable to no single model. Proposing one from
    that evidence would be inventing an attribution the data cannot support.
    """
    for proposal in propose(MODELS, OBSERVED):
        assert "family_surface" in proposal.incomplete


def test_a_model_with_no_attested_surface_says_so_rather_than_guessing():
    """`mechanical-only` means recall is UNMEASURED, not zero.

    The primary stays INCOMPLETE rather than becoming the first derivable form
    dressed up as a choice.
    """
    proposal = next(p for p in propose(MODELS, OBSERVED)
                    if p.canonical_id == "google/gemini-3-pro")
    assert proposal.status == "mechanical-only"
    assert proposal.surface == INCOMPLETE
    assert "attested_surfaces" in proposal.incomplete
    assert proposal.mechanical, "coverage is still offered"


def test_the_yaml_is_not_loadable_as_a_finished_alias_list():
    """A generated list that could be merged unread is the failure to prevent.

    Every entry carries an INCOMPLETE marker, so a reviewer has to touch each one.
    """
    text = to_yaml(propose(MODELS, OBSERVED))
    # Count the `incomplete:` LINES, not occurrences of the word — the header
    # explains `family_surface` too, and a substring count would have been
    # counting the explanation.
    slots = [ln for ln in text.splitlines() if ln.strip().startswith("incomplete: [")]
    assert len(slots) == len(MODELS)
    assert all("family_surface" in ln for ln in slots)
    assert INCOMPLETE in text
    assert "review required" in text


def test_the_yaml_labels_each_variant_attested_or_mechanical():
    """Three things visible separately: derivable, attested, missing."""
    text = to_yaml(propose(MODELS, OBSERVED))
    assert "# attested 1445 mentions" in text
    assert "# mechanical, unattested" in text


def test_the_summary_states_what_is_unmeasured():
    summary = summarise(propose(MODELS, OBSERVED))
    assert "mechanical-only" in summary
    assert "INCOMPLETE" in summary


def test_an_unmeasured_surface_count_is_never_rendered_as_zero():
    """`median 0, max 0` is the same table cell as a model measured at zero.

    `deepseek r1` is NOT MEASURED — the detector cannot see letter-prefixed
    versions, so there is no observation to report. It is not measured as zero.
    Somebody will eventually prune on a zero, and the two are indistinguishable
    once printed.
    """
    summary = summarise(propose(MODELS))
    assert "not measured" in summary
    assert "median 0" not in summary and "max 0" not in summary


# ── the boundary ─────────────────────────────────────────────────────────


def test_nothing_here_calls_a_model():
    """Deterministic string work. `collect/` never calls an LLM, not once."""
    import ast
    from pathlib import Path

    import collect.registry.propose as mod

    tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported & {"anthropic", "openai", "litellm", "httpx", "requests"}


def test_proposing_twice_gives_the_same_answer():
    """Deterministic, so a reviewer's diff is about the corpus and not the run."""
    assert to_yaml(propose(MODELS, OBSERVED)) == to_yaml(propose(MODELS, OBSERVED))


@pytest.mark.parametrize("observed", [None, {}])
def test_no_observations_is_handled_as_unmeasured(observed):
    proposals = propose(MODELS, observed)
    assert all(p.status == "mechanical-only" for p in proposals)
    assert all(p.surface == INCOMPLETE for p in proposals)


# ── the source split: rule 7 in the file the seats are read from ──────────


def test_the_split_is_printed_beside_every_attested_count():
    """A total alone cannot say whether a seat rests on the corpus or one slice.

    `sonnet 4.5` reads 416 mentions of which 393 are substitution-slice, and
    `opus 5` reads 1445 of which 1092 are the general sweep. Before the split was
    printed those two seats looked like the same kind of evidence.
    """
    text = to_yaml(propose(MODELS, OBSERVED))
    assert "[sweep 1092, slice 348, comments 5]" in text
    # Descending by count, so the dominant source is read first.
    assert "[slice 348, sweep 1092" not in text


def test_a_missing_split_says_so_rather_than_implying_one_source():
    """Rule 6. `gpt-5` has no by_source in the fixture."""
    text = to_yaml(propose(MODELS, OBSERVED))
    assert "# attested 311 mentions [split unrecorded]" in text


def test_a_split_that_does_not_reconcile_is_flagged_on_the_line():
    """A denominator that disagrees with its figure is a second unverified number."""
    rendered = source_split(Attested("x", 100, 10, by_source={"reddit-sweep": 60}))
    assert "!! sums to 60, not 100" in rendered


def test_the_header_explains_the_notation():
    """The artifact must be readable without opening this module."""
    text = to_yaml(propose(MODELS, OBSERVED))
    assert "EVERY MENTION COUNT IS A SUM" in text
    assert "[slice N, sweep N, comments N]" in text
