"""The alias proposer: two inputs, and empty slots left empty.

The load-bearing tests are the INCOMPLETE ones. Engineer 2's argument: a
generated list that looks complete is worse than a short one known to be short —
the same argument as `phrase_present = None` versus 0. So a slot with no evidence
must be legibly missing, not plausibly filled.
"""

from __future__ import annotations

import pytest

from collect.registry.propose import (
    FAMILY_WORDS,
    INCOMPLETE,
    Attested,
    mechanical_variants,
    propose,
    summarise,
    to_yaml,
)

MODELS = [
    ("anthropic/claude-opus-5", "Anthropic: Claude Opus 5"),
    ("google/gemini-3-pro", "Google: Gemini 3 Pro"),
    ("openai/gpt-5", "OpenAI: GPT-5"),
]

#: Real counts from the extract over 5,546 stored documents.
OBSERVED = {
    "anthropic/claude-opus-5": [Attested("opus 5", 1445, 281), Attested("opus-5", 78, 39)],
    "openai/gpt-5": [Attested("gpt-5", 311, 103), Attested("gpt 5", 55, 30),
                     Attested("gpt5", 33, 18)],
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


def test_attested_surfaces_come_before_mechanical_ones():
    proposal = next(p for p in propose(MODELS, OBSERVED)
                    if p.canonical_id == "openai/gpt-5")
    variants = proposal.variants
    assert variants.index("gpt 5") < variants.index("gpt5") or "gpt5" in variants
    assert "gpt 5" in variants


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
