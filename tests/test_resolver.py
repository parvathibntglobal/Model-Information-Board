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

    def test_there_are_three_and_not_two(self):
        assert set(Outcome) == {Outcome.FOUND, Outcome.TOMBSTONED, Outcome.MISSING}

    def test_the_two_failures_say_different_things(self):
        tomb = ResolvedText("r1", Outcome.TOMBSTONED)
        missing = ResolvedText("r1", Outcome.MISSING)

        with pytest.raises(LookupError) as t:
            tomb.require()
        with pytest.raises(LookupError) as m:
            missing.require()

        assert "nothing is broken" in str(t.value)
        assert "need investigating" in str(m.value)
        assert str(t.value) != str(m.value)

    def test_neither_failure_is_falsy_in_a_way_that_reads_as_the_other(self):
        assert ResolvedText("r1", Outcome.TOMBSTONED).found is False
        assert ResolvedText("r1", Outcome.MISSING).found is False
        assert ResolvedText("r1", Outcome.FOUND, "x").found is True


class TestTheRefTravelsWithEveryOutcome:
    """A MISSING that does not say which ref sends whoever reads it back to the
    database to find out, and that is the moment they start guessing."""

    @pytest.mark.parametrize("outcome", [Outcome.TOMBSTONED, Outcome.MISSING])
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
