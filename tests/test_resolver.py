"""The contract this lane names for text it does not store.

Option (a): judge/ says what it needs, whoever composes the application
provides it. These are the assertions that the three outcomes cannot collapse
and that nothing here knows about a store.
"""

from __future__ import annotations

import pytest

from judge.extract.resolver import (
    Outcome,
    RawTextResolver,
    RefusingResolver,
    ResolvedText,
)


class TestTheThreeOutcomesCannotCollapse:
    """A tombstone is a deletion we honoured; a missing blob is a bug. The
    repair for the first is nothing and for the second is urgent, so this is
    rule 6 at the one place both lanes read."""

    def test_there_are_four_and_not_three(self):
        """CORRUPT was added after E1 found the adapter's `except Exception`
        folding it into MISSING - a blob that had been ALTERED and one that was
        never written coming back identically."""
        assert set(Outcome) == {
            Outcome.FOUND,
            Outcome.TOMBSTONED,
            Outcome.MISSING,
            Outcome.CORRUPT,
        }

    def test_tombstoned_and_missing_name_opposite_repairs(self):
        """Nothing to do versus something to chase.

        This asserted `"need investigating"` on MISSING and broke when that
        message was rewritten to name the repair as upstream - a test pinned to
        wording rather than to meaning. Now asserts the distinction each
        message has to carry; `test_every_failure_explains_itself_differently`
        covers all three generally.
        """
        with pytest.raises(LookupError) as tomb:
            ResolvedText("r1", Outcome.TOMBSTONED).require()
        with pytest.raises(LookupError) as missing:
            ResolvedText("r1", Outcome.MISSING).require()

        assert "nothing is broken" in str(tomb.value)
        assert "repair is upstream" in str(missing.value)

    def test_no_failure_is_falsy_in_a_way_that_reads_as_the_other(self):
        for outcome in (Outcome.TOMBSTONED, Outcome.MISSING, Outcome.CORRUPT):
            assert ResolvedText("r1", outcome).found is False
        assert ResolvedText("r1", Outcome.FOUND, "x").found is True

    def test_every_failure_explains_itself_differently(self):
        """Three ways to have no text, three different repairs. A shared
        message would make the enum decorative."""
        messages = set()
        for outcome in (Outcome.TOMBSTONED, Outcome.MISSING, Outcome.CORRUPT):
            with pytest.raises(LookupError) as caught:
                ResolvedText("r1", outcome).require()
            messages.add(str(caught.value))
        assert len(messages) == 3

    def test_a_new_outcome_cannot_be_added_without_a_reason_for_it(self):
        """`_WHY` is a mapping rather than a branch chain, so an outcome added
        without a reader raises KeyError here rather than falling through to
        whatever the last `else` happened to say."""
        from judge.extract.resolver import _WHY

        assert set(_WHY) == set(Outcome) - {Outcome.FOUND}


class TestTheRefTravelsWithEveryOutcome:
    """A MISSING that does not say which ref sends whoever reads it back to the
    database to find out, and that is the moment they start guessing."""

    @pytest.mark.parametrize("outcome", [Outcome.TOMBSTONED, Outcome.MISSING, Outcome.CORRUPT])
    def test_the_failure_message_names_the_ref(self, outcome):
        with pytest.raises(LookupError, match="raw/sha256/abc"):
            ResolvedText("raw/sha256/abc", outcome).require()

    def test_the_ref_is_on_the_value_too_not_only_the_exception(self):
        assert ResolvedText("raw/x", Outcome.MISSING).ref == "raw/x"


class TestTheStatesCannotBeConstructedInconsistently:
    def test_found_with_no_text_is_refused(self):
        """The case a boolean would have hidden."""
        with pytest.raises(ValueError, match="FOUND with no text"):
            ResolvedText("r1", Outcome.FOUND)

    def test_a_failure_carrying_text_is_refused(self):
        """Returning text anyway would let a caller read past the outcome it
        was given."""
        with pytest.raises(ValueError, match="with text attached"):
            ResolvedText("r1", Outcome.MISSING, "sneaky")


class TestNothingHereKnowsAboutAStore:
    """The dependency has to run one way. This file naming a path, a bucket or
    a `collect/` symbol would be the lane boundary crossed in a docstring."""

    def test_the_module_mentions_no_store_implementation(self):
        import inspect

        import judge.extract.resolver as mod

        source = inspect.getsource(mod)
        for leak in ("RawStore", "import collect", "from collect", "boto3", "Path("):
            assert leak not in source, f"the resolver contract mentions {leak}"

    def test_a_plain_object_satisfies_it_without_importing_anything(self):
        """Protocol rather than ABC, so the implementation does not import this
        file either - neither lane depends on the other in either direction."""

        class Anything:
            def resolve(self, ref: str) -> ResolvedText:
                return ResolvedText(ref, Outcome.FOUND, "text")

        assert isinstance(Anything(), RawTextResolver)

    def test_the_protocol_offers_exactly_one_method(self):
        """get and nothing else, so read-only is structural rather than
        conventional.

        Checked through `dir()` rather than `__protocol_attrs__`, which is
        3.12+ and absent here - the first version of this test asserted against
        an attribute that does not exist on this interpreter and failed for a
        reason unrelated to what it was testing.
        """
        members = {m for m in dir(RawTextResolver) if not m.startswith("_")}

        assert members == {"resolve"}
        for writer in ("put", "delete", "write", "evict", "list"):
            assert writer not in members, f"the resolver exposes {writer}"

    def test_an_object_offering_a_write_still_satisfies_it_and_that_is_fine(self):
        """A Protocol checks what is PRESENT, not what is absent, so it cannot
        forbid a resolver's implementation from having other methods.

        Worth stating rather than pretending otherwise: get-only is a property
        of what THIS LANE can call, not of the object handed in. The protection
        is that nothing here can reach a method it does not name.
        """

        class AlsoWrites:
            def resolve(self, ref: str) -> ResolvedText:
                return ResolvedText(ref, Outcome.FOUND, "x")

            def put(self, data: bytes) -> str:
                raise AssertionError("judge/ must never call this")

        assert isinstance(AlsoWrites(), RawTextResolver)
        import inspect

        import judge.extract.resolver as mod

        assert ".put(" not in inspect.getsource(mod)


class TestTheDefaultRefusesRatherThanReturningNothing:
    """A None default would let a caller that forgot to wire a resolver run to
    completion having read nothing, extract no claims, and report a clean
    batch - the failure this project has found fourteen times."""

    def test_it_raises_at_the_first_ref(self):
        with pytest.raises(LookupError, match="no resolver is wired"):
            RefusingResolver().resolve("raw/x")

    def test_it_says_missing_dependency_rather_than_missing_payload(self):
        with pytest.raises(LookupError, match="missing dependency"):
            RefusingResolver().resolve("raw/x")

    def test_it_satisfies_the_protocol_so_it_can_be_the_default(self):
        assert isinstance(RefusingResolver(), RawTextResolver)


class TestCorruptIsNotMissing:
    """MISSING says nothing is there and the repair is upstream. CORRUPT says
    something is there and we cannot trust what we stored."""

    def test_only_corrupt_says_the_store_is_untrustworthy(self):
        """A caller needs three answers, not two: proceed, skip this thread, or
        STOP. Missing and tombstoned are both "skip this one"; corrupt is the
        only one that says anything about the NEXT payload."""
        assert ResolvedText("r1", Outcome.CORRUPT).store_is_untrustworthy
        for other in (Outcome.TOMBSTONED, Outcome.MISSING):
            assert not ResolvedText("r1", other).store_is_untrustworthy
        assert not ResolvedText("r1", Outcome.FOUND, "x").store_is_untrustworthy

    def test_its_message_says_present_and_altered_rather_than_absent(self):
        with pytest.raises(LookupError) as caught:
            ResolvedText("r1", Outcome.CORRUPT).require()

        message = str(caught.value)
        assert "does not match its hash" in message
        assert "not a missing blob" in message

    def test_it_carries_no_text_like_the_other_failures(self):
        """Present-but-altered is still nothing a caller may read: returning
        the bytes would hand somebody a quote from a payload known to be
        wrong."""
        with pytest.raises(ValueError, match="with text attached"):
            ResolvedText("r1", Outcome.CORRUPT, "altered bytes")


class TestAMirroredEnumFromTheOtherLaneNormalises:
    """The specific hazard of a type duplicated across a lane boundary.

    `collect/rawstore_reader.py` defines `ReadOutcome` mirroring `Outcome`,
    deliberately, because neither lane may import the other. Nothing checks
    that the two stay in step, and StrEnum members of different classes compare
    EQUAL by value while never being IDENTICAL - so every `is` comparison in
    this module would silently take the wrong branch on a foreign member.
    """

    def test_the_two_enums_are_equal_by_value_and_never_identical(self):
        from collect.rawstore_reader import ReadOutcome

        assert ReadOutcome.MISSING == Outcome.MISSING
        assert ReadOutcome.MISSING is not Outcome.MISSING

    def test_a_foreign_member_is_normalised_on_construction(self):
        """Without this, a FOUND payload reads as not-found and a CORRUPT one
        reads as trustworthy - silently, in the safe-looking direction."""
        from collect.rawstore_reader import ReadOutcome

        result = ResolvedText("raw/x", ReadOutcome.MISSING)

        assert result.outcome is Outcome.MISSING
        assert isinstance(result.outcome, Outcome)

    def test_a_bare_string_normalises_too(self):
        assert ResolvedText("raw/x", "corrupt").store_is_untrustworthy

    def test_an_unknown_value_is_refused_loudly(self):
        with pytest.raises(ValueError, match="not a valid Outcome"):
            ResolvedText("raw/x", "nonsense")

    def test_the_mirrored_enum_is_missing_our_fourth_value(self):
        """Recorded rather than worked around: `ReadOutcome` has three values
        and this has four, so the reader cannot yet REPORT corruption even
        though this lane can represent it.

        The normalisation above means nothing breaks - a corrupt payload simply
        arrives as MISSING, which is the defect E1 asked for CORRUPT to fix,
        surviving in the other half of the pair. Their side to close.
        """
        from collect.rawstore_reader import ReadOutcome

        assert not hasattr(ReadOutcome, "CORRUPT")
        assert hasattr(Outcome, "CORRUPT")
