"""`collect/`'s side of judge's `SurfaceResolver`.

The field this replaces was never populated by anything, so these tests are the
first thing that has ever driven surface resolution on the store path.
"""

from __future__ import annotations

import pytest

from collect.surface_resolver import RegistrySurfaceResolver
from collect.triage.entity import build_population, normalize

# (canonical_id, display_name) exactly as `model_version` supplies them.
REGISTRY = [
    ("anthropic/claude-fable-5", "Anthropic: Claude Fable 5"),
    ("anthropic/claude-opus-4.8", "Anthropic: Claude Opus 4.8"),
    ("google/gemini-2.5-flash", "Google: Gemini 2.5 Flash"),
]
IDS = {
    "anthropic/claude-fable-5": "mv_fable5",
    "anthropic/claude-opus-4.8": "mv_opus48",
    "google/gemini-2.5-flash": "mv_flash",
}


def _resolver(registry=REGISTRY, ids=IDS, population=None) -> RegistrySurfaceResolver:
    return RegistrySurfaceResolver(population or build_population(registry), ids)


class TestItSatisfiesTheProtocol:
    def test_judge_accepts_it_without_importing_collect(self):
        from judge.pipeline import SurfaceResolver

        assert isinstance(_resolver(), SurfaceResolver)


class TestTheSpellingsAHumanWrites:
    @pytest.mark.parametrize(
        "surface",
        ["Fable 5", "fable 5", "fable-5", "FABLE5", "Claude Fable 5", "claude-fable-5"],
    )
    def test_every_spelling_of_one_model_lands_on_one_id(self, surface):
        """`normalize` folds spacing and hyphens, so these are one surface."""
        assert _resolver()(surface) == "mv_fable5"

    def test_a_surface_carrying_extra_words_still_resolves(self):
        """Containment fallback. The extractor returns the surface as written,
        and a human writes conditions into it."""
        assert _resolver()("Claude Opus 4.8 (xhigh)") == "mv_opus48"

    def test_the_longest_match_wins(self):
        """`opus 4.8` and `opus 4` both appear in the text; the specific one is
        the claim about identity that was actually made."""
        assert _resolver()("Opus 4.8") == "mv_opus48"


class TestWhatItRefuses:
    def test_a_bare_family_word_resolves_to_nothing(self):
        """`fable` is one of the 26 FAMILY_WORDS `_admissible` excludes, so it
        is not in the population and NO SEATING FIXES IT.

        This is not a gap in the registry. It is the priced side of a trade:
        the exclusion keeps `pro` out of "problem" and `free` out of "freeze",
        and it costs us `oqocfjv` - the only first-hand capability observation
        in the seven.
        """
        r = _resolver()
        assert r("Fable") is None
        assert r("fable") is None
        assert "Fable" in r.report.unmatched

    def test_a_model_we_do_not_track_resolves_to_nothing(self):
        r = _resolver()
        assert r("GPT-9 Turbo") is None
        assert "GPT-9 Turbo" in r.report.unmatched

    def test_an_ambiguous_surface_is_refused_rather_than_picked(self):
        """A surface owned by two models comes back None.

        An arbitrary pick attaches a real quote to the wrong model, which is
        worse than dropping it: an unresolved claim is a counted absence, a
        mis-resolved one is evidence against a model that nobody discussed.
        """
        population = build_population(REGISTRY)
        shared = next(s for s in sorted(population.surfaces) if population.owners.get(s))
        # FORGE EVERY SPELLING OF THE KEY, not one of them. Resolution is by
        # normalised key with owners unioned across spellings, so seeding two
        # owners onto a single spelling leaves its siblings contributing the real
        # owner and the union is three. That is the keyed lookup working: the
        # thing being tested is what happens when a KEY has two owners.
        key = normalize(shared)
        owners = {
            **population.owners,
            **{s: ("a/one", "b/two") for s in population.surfaces if normalize(s) == key},
        }
        forged = type(population)(
            surfaces=population.surfaces,
            contributions=population.contributions,
            model_count=population.model_count,
            declared_model_count=population.declared_model_count,
            owners=owners,
        )
        r = RegistrySurfaceResolver(forged, {"a/one": "mv_a", "b/two": "mv_b"})
        assert r(shared) is None
        assert r.report.ambiguous[shared] == ("a/one", "b/two")

    def test_one_spelling_owned_and_another_not_is_one_owner(self):
        """The nondeterminism this file did not catch, as a test.

        Three of the 414 real keys have both owned and unowned spellings, because
        `build_population` records owners per spelling and a declared surface has
        none. The old lookup took the first frozenset member matching the key and
        broke, so the answer depended on PYTHONHASHSEED: `gpt-4.1 mini` resolved
        at seed 3 and came back None at 1, 2, 4 and 5.

        An unowned spelling is an owner the population DECLINED TO GUESS, not a
        claim that there is none - so the union is one owner, and this asserts
        the answer rather than the mechanism.
        """
        population = build_population(REGISTRY, declared=["claude fable-5"])
        assert normalize("claude fable-5") == normalize("claude fable 5")
        declared_only = next(
            s for s in population.surfaces
            if normalize(s) == normalize("claude fable 5")
            and not population.owners.get(s)
        )
        r = _resolver(population=population)
        assert r(declared_only) == "mv_fable5"
        assert declared_only in r.report.resolved
        assert declared_only not in r.report.no_owner
        assert declared_only not in r.report.ambiguous

    def test_a_surface_no_model_derives_is_not_counted_as_ambiguous(self):
        """Owned by nothing and owned by several are opposite facts.

        Both return None, so no claim was ever mis-stored. The report is what
        was wrong: it said "several models answer to this spelling" about a
        declared surface no derivation produces, with an empty candidate tuple
        beside it. 1,103 occurrences over the substitution corpus were being
        counted under `ambiguous`, so anyone reading that number to decide
        whether ambiguity was a problem was reading mostly this instead.
        """
        population = build_population(REGISTRY, declared=["totally made up tier"])
        surface = "totally made up tier"
        assert surface in population.surfaces
        assert population.owners.get(surface, ()) == ()

        r = _resolver(population=population)
        assert r(surface) is None
        assert surface in r.report.no_owner
        assert surface not in r.report.ambiguous
        assert surface not in r.report.unmatched
        assert "matched a surface no model derives" in r.report.summary()

    def test_an_owner_with_no_registry_row_is_counted_not_invented(self):
        r = _resolver(ids={})
        assert r("Fable 5") is None
        assert r.report.owner_without_row["Fable 5"] == "anthropic/claude-fable-5"

    @pytest.mark.parametrize("surface", ["", "   ", None])
    def test_an_empty_surface_is_not_a_lookup(self, surface):
        assert _resolver()(surface) is None


class TestTheReportCountsWhatWasRefused:
    def test_the_denominator_is_everything_asked(self):
        """A run resolving 8 of 8 and one resolving 8 of 40 are different runs,
        and the 32 are invisible in a claim count (rule 7)."""
        r = _resolver()
        for s in ("Fable 5", "Opus 4.8", "Fable", "GPT-9 Turbo"):
            r(s)
        assert r.report.asked == 4
        assert len(r.report.resolved) == 2
        assert len(r.report.unmatched) == 2
        assert "2 of 4 resolved" in r.report.summary()

class TestTheFinderAndSubjectInheritance:
    """`subject_inherited` is DERIVED, and this is why that matters.

    Three of the four claims in the table quote text naming no model, and all
    four record `specificity=version`. `claim` has no `surface` column, so the
    string that justified `version` is not in the row. A field the extractor
    filled could assert `false` about a quote naming nothing and nothing would
    catch it; a derived one cannot lie.
    """

    def test_it_satisfies_judge_s_protocol_without_judge_importing_collect(self):
        from collect.surface_resolver import RegistrySurfaceFinder
        from judge.pipeline import SurfaceFinder

        assert isinstance(RegistrySurfaceFinder(build_population(REGISTRY)), SurfaceFinder)

    def test_a_quote_naming_a_model_is_not_inherited(self):
        from collect.surface_resolver import RegistrySurfaceFinder
        from judge.pipeline import subject_was_inherited

        finder = RegistrySurfaceFinder(build_population(REGISTRY))
        assert subject_was_inherited(
            "we moved to Claude Fable 5 last week",
            model_version_id="mv_fable5",
            find_surfaces=finder,
        ) is False

    def test_a_quote_naming_nothing_is_inherited(self):
        """The real case: the subject came from elsewhere in the document."""
        from collect.surface_resolver import RegistrySurfaceFinder
        from judge.pipeline import subject_was_inherited

        finder = RegistrySurfaceFinder(build_population(REGISTRY))
        assert subject_was_inherited(
            "We'll keep refining the safeguards to reduce false positives.",
            model_version_id="mv_fable5",
            find_surfaces=finder,
        ) is True

    def test_absent_is_absent_rather_than_false(self):
        """Rule 6. "Nobody checked" and "checked and it names one" differ."""
        from collect.surface_resolver import RegistrySurfaceFinder
        from judge.pipeline import subject_was_inherited

        finder = RegistrySurfaceFinder(build_population(REGISTRY))
        assert subject_was_inherited(
            "anything", model_version_id="mv_fable5", find_surfaces=None
        ) is None
        assert subject_was_inherited(
            "anything", model_version_id=None, find_surfaces=finder
        ) is None

    def test_the_model_is_never_asked(self):
        """Asserted on the source, because a field would be the tempting fix.

        Asking the extractor whether it inherited the subject makes an LLM
        decide something code can check - the `resolved_version_id` mistake.
        """
        import inspect

        from judge.extract.schema import ModelRef
        from judge.pipeline import quote_subject_verdict, subject_was_inherited

        assert "subject_inherited" not in ModelRef.model_fields
        assert "inherited" not in {f.lower() for f in ModelRef.model_fields}

        # THE DERIVATION MOVED, THE PROPERTY DID NOT. `subject_was_inherited` is
        # now a projection of `quote_subject_verdict`, which is where
        # `find_surfaces(quote)` lives — one resolution answering both "did the
        # quote name a model" and "did it name THIS one", so the two cannot
        # disagree about the same quote. Asserted on both halves rather than
        # relaxed to one, because the point of a source assertion is that the
        # tempting fix is a field on the schema.
        assert "find_surfaces(quote)" in inspect.getsource(quote_subject_verdict)
        assert "quote_subject_verdict(" in inspect.getsource(subject_was_inherited)


# ── the surface is more specific than anything we hold ───────────────────────
#
# `gpt-5` is the longest alias matching `GPT-5.6 Sol Ultra`, has exactly ONE
# owner, and resolved with full confidence to a different model. Measured
# 2026-08-21: five stored claims about GPT-5.6 were filed against GPT-5, and
# three of them rendered as quotes on `/models/openai/gpt-5`.
#
# NOT ambiguity. `len(owners) != 1` was correct and its input was wrong. The
# tell is the character after the match: a digit means the version continues
# past everything we know about, so the surface names a model we do not track
# and a counted drop is what that is.

class _TinyPop:
    def __init__(self, surfaces, owners):
        self.surfaces = tuple(surfaces)
        self.owners = owners


def _seated(surfaces_to_owner):
    owners = {s: (o,) for s, o in surfaces_to_owner.items()}
    pop = _TinyPop(surfaces_to_owner, owners)
    return RegistrySurfaceResolver(pop, {o: o for o in surfaces_to_owner.values()})


@pytest.mark.parametrize(
    "surface",
    ["GPT-5.6 Sol Ultra", "GPT-5.6", "gpt-5.6", "GPT-5.6 Luna"],
)
def test_a_surface_more_specific_than_the_seated_alias_is_refused(surface):
    r = _seated({"gpt-5": "mv_gpt5"})
    assert r(surface) is None
    assert surface in r.report.more_specific_than_seated


def test_it_is_counted_rather_than_dropped():
    """A silent drop and a refusal are different findings (rule 6)."""
    r = _seated({"gpt-5": "mv_gpt5"})
    r("GPT-5.6")
    assert r.report.more_specific_than_seated == {"GPT-5.6": "gpt5"}
    assert "GPT-5.6" not in r.report.unmatched
    assert "GPT-5.6" not in r.report.ambiguous


def test_a_trailing_non_digit_still_resolves():
    """`Claude Opus 4.8 (xhigh)` is the containment case the fallback is FOR."""
    r = _seated({"claude opus 4.8": "mv_opus48"})
    assert r("Claude Opus 4.8 (xhigh)") == "mv_opus48"
    assert not r.report.more_specific_than_seated


def test_an_exact_match_is_never_treated_as_a_prefix():
    """An exact normalised match consumed the whole surface."""
    r = _seated({"claude haiku 4.5": "mv_haiku45"})
    assert r("Claude Haiku 4.5") == "mv_haiku45"
    assert not r.report.more_specific_than_seated


def test_the_seated_longer_version_wins_over_the_shorter_one():
    """With both seated, longest-first ordering already picks correctly.

    This is the case the guard must NOT break: the fix is for a version we do
    not hold, not for one we do.
    """
    r = _seated({"claude sonnet 4": "mv_sonnet4",
                   "claude sonnet 4.5": "mv_sonnet45"})
    assert r("Claude Sonnet 4.5") == "mv_sonnet45"
