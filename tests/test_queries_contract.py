"""FR-7 and FR-8, enforced rather than asserted in a comment.

`contract/queries.yaml` shipped with these three rules written in its header
and nothing reading them. The 12/12 was verified once, by hand, in a script
that was thrown away — which is FR-7's acceptance ("fails the build") not
being met by the file claiming to meet it.

Harvest is entirely query-driven. A capability with no query has empty cells
forever, and that failure is an ABSENCE: the capability simply never appears
on any page, and nothing surfaces to disagree with. Adding a capability
without its queries has to be loud, and this is where it gets loud.

Reads the three contract files and nothing else. No lane code is imported, so
this test is owned by neither lane and breaks for both.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

CONTRACT = Path(__file__).resolve().parent.parent / "contract"


def _load(name: str) -> dict:
    return yaml.safe_load((CONTRACT / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def capabilities() -> dict[str, str]:
    """key -> failure_mode."""
    return {c["key"]: c["failure_mode"] for c in _load("capabilities.yaml")["capabilities"]}


@pytest.fixture(scope="module")
def queries() -> dict:
    return _load("queries.yaml")


@pytest.fixture(scope="module")
def entries(queries) -> list[dict]:
    """Capability queries only. Substitution is cross-capability by design."""
    return queries["queries"]


class TestCoverage:
    def test_every_capability_has_a_query(self, capabilities, entries):
        """FR-7. A capability nobody searches for has empty cells forever."""
        missing = sorted(set(capabilities) - {e["capability"] for e in entries})
        assert not missing, (
            f"{len(missing)} capabilities have no harvest query: {missing}. "
            "Harvest is query-driven, so these can never produce a cell."
        )

    def test_every_capability_has_a_negative_query(self, capabilities, entries):
        """FR-8. Platforms surface positive content by default.

        Failure reports are the entire basis of the `criticised-for` labels,
        and nothing else surfaces them.
        """
        negative = {e["capability"] for e in entries if e["stance"] == "negative"}
        missing = sorted(set(capabilities) - negative)
        assert not missing, f"no negative-stance query for: {missing}"

    def test_every_silent_capability_has_a_positive_query(self, capabilities, entries):
        """Not in FR-8's wording, and it should be.

        A silent-failure capability requires POSITIVE consensus — "nobody
        complained" is not evidence when you would not find out. With only
        negative queries the gate can never pass, so the cell never publishes,
        so the capability never appears. It fails as an absence.

        This is the capability class that includes summarisation, which is the
        single recommendation this product exists to make.
        """
        positive = {e["capability"] for e in entries if e["stance"] == "positive"}
        silent = {k for k, mode in capabilities.items() if mode == "silent"}
        missing = sorted(silent - positive)
        assert not missing, (
            f"silent-failure capabilities with no positive query: {missing}. "
            "Positive consensus is unreachable for these, so their cells can "
            "never publish and they will silently never appear."
        )

    def test_no_query_names_a_capability_that_does_not_exist(self, capabilities, entries):
        """A typo here is a query that runs forever and attaches to nothing."""
        unknown = sorted({e["capability"] for e in entries} - set(capabilities))
        assert not unknown, f"queries for capabilities not in the vocabulary: {unknown}"


class TestShape:
    def test_stances_are_from_the_closed_set(self, entries, queries):
        """FR-8's check has to be mechanical, not a reading of the terms."""
        for e in entries + queries["substitution"]:
            assert e["stance"] in {"positive", "negative"}, e

    def test_records_condition_matches_the_dominant_dimension(self, entries):
        """Q5 reads the cell at the task's bucket.

        A query recording the wrong dimension produces claims that land in a
        bucket the answer path never looks in.
        """
        dominant = _load("conditions.yaml")["dominant_dimension"]
        wrong = [
            (e["capability"], e["records_condition"], dominant[e["capability"]])
            for e in entries
            if e["records_condition"] != dominant[e["capability"]]
        ]
        assert not wrong, f"(capability, declared, expected): {wrong}"

    def test_every_entry_states_its_intent_and_its_yield_condition(self, entries, queries):
        """`yields_claim_when` is what stops a query costing budget for nothing.

        A query retrieving 500 documents that all fail extraction looks like a
        successful harvest from `collect/` — the documents are real hits. The
        cost only shows up as an empty cell weeks later.
        """
        for e in entries + queries["substitution"]:
            label = f"{e.get('capability', 'substitution')}/{e['stance']}"
            assert e.get("intent", "").strip(), f"{label} has no intent"
            assert e.get("yields_claim_when", "").strip(), f"{label} has no yields_claim_when"

    def test_some_subject_term_references_the_alias(self, entries, queries):
        """Without it, a query harvests posts about nothing in particular.

        The rule is "SOME element references the alias", not "the list is
        exactly ['{alias}']". `subject` is all-of, so extra required terms are
        legitimate — `['{alias}', 'production']` is a narrower query, not a
        malformed one — but at least one of them has to identify the model.

        The first version asserted `"{alias}" in subject`, which on a list is
        exact membership. It passed only because every subject happens to be
        `['{alias}']` today, and would have rejected `['{alias} 2.5']` while
        reading as though it allowed it.
        """
        for e in entries + queries["substitution"]:
            label = e.get("capability", "substitution")
            subject = e["terms"]["subject"]
            assert subject, f"{label} has an empty subject"
            assert any("{alias}" in term for term in subject), (
                f"{label}: no subject term references {{alias}}, so this query "
                f"retrieves documents that need not mention any model"
            )

    def test_topic_and_signal_terms_are_all_non_empty(self, entries):
        """`subject` alone is the collapsed state issue #4 documents.

        Checks the ELEMENTS, not just the list. `assert e["terms"]["topic"]`
        passes for `[""]` — a list holding an empty string is truthy — which
        is the same weakness as the alias assertion above, found by auditing
        for it rather than by hitting it.
        """
        for e in entries:
            for group in ("topic", "signal"):
                terms = e["terms"][group]
                assert terms, f"{e['capability']} has no {group} terms"
                blank = [i for i, t in enumerate(terms) if not t or not t.strip()]
                assert not blank, f"{e['capability']} has empty {group} terms at {blank}"


class TestSubstitution:
    def test_directional_templates_declare_phrase_binding(self, queries):
        """"replaced X with Y" and "replaced Y with X" are opposite claims
        built from identical tokens. An index that does not bind phrases
        cannot tell them apart.

        The flag states the semantic property. It is deliberately not a
        `platforms:` list, which would write today's measurement of one index
        into a platform-neutral file — the thing ruling (b) removed.
        """
        for e in queries["substitution"]:
            directional = any("{alias_b}" in t for t in e["terms"]["topic"])
            if directional:
                assert e.get("requires") == "phrase_binding", (
                    "a directional substitution template must declare "
                    "phrase_binding, or an adapter has to make that semantic "
                    "call unilaterally in code"
                )

    def test_substitution_references_a_second_model(self, queries):
        for e in queries["substitution"]:
            assert any("{alias_b}" in t for t in e["terms"]["topic"]), e["stance"]
