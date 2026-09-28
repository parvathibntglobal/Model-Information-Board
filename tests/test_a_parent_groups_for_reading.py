""""A parent groups for reading and never implies the leaves are the same
measurement." #410.

WHAT THESE PROTECT

The member lists in `contract/slug_parents.yaml` are one reader's judgement
over 296 slugs and **cannot be reviewed by reading** — a second reader agreeing
is not validation, because two people with the same priors are one prior. So
the lists are not what these tests check.

What they check is the property that makes a wrong member list CHEAP: a parent
groups for reading, never collapses a leaf, and never publishes a number of its
own. Under that property a wrong list costs a reader one click. Without it, it
costs the board a figure nobody can trace to a writer.

Four constraints, one per test class, each mechanical rather than a convention.
"""

from __future__ import annotations

import re

import pytest
import yaml

from judge.board_grouping import coverage, group_section, group_sections, parent_of
from judge.config import CONTRACT_DIR, slug_parents

RAW = yaml.safe_load((CONTRACT_DIR / "slug_parents.yaml").read_text(encoding="utf-8"))

#: A parent carrying any of these could publish a consensus about a category no
#: writer named. The schema has no field for one; this refuses one being added.
FORBIDDEN_KEYS = re.compile(r"voices|n_eff|weight|score|consensus", re.I)


def leaf(slug: str, reports: int = 1) -> dict:
    """The shape `board_sections()` emits, trimmed to what grouping reads."""
    return {"slug": slug, "name": slug.replace("-", " ").title(), "reports": reports}


class TestItCountsLeavesNotVoices:
    """Ruling 1, and it is arithmetic before it is a rule.

    Summing leaf `reports` double-counts every document appearing under two
    leaves of one parent — measured at 55 against a true union of 51 on
    `coding` — and sums a figure that is already a floor.
    """

    def test_the_file_has_no_field_that_could_hold_a_voice_count(self):
        text = (CONTRACT_DIR / "slug_parents.yaml").read_text(encoding="utf-8")
        for line in text.splitlines():
            bare = line.split("#", 1)[0]
            if ":" in bare:
                key = bare.split(":", 1)[0].strip().lstrip("- ")
                assert not FORBIDDEN_KEYS.search(key), (
                    f"{key!r} is a key a parent could publish a voice count "
                    "under. A parent carries a count of LEAVES."
                )

    def test_a_parent_emits_leaves_and_nothing_numeric_besides(self):
        rows = group_section(
            [leaf("code-generation", 55), leaf("code-review", 18)], section="capability"
        )
        parent = next(r for r in rows if r["kind"] == "parent")
        assert parent["leaves"] == 2
        numeric = {k for k, v in parent.items() if isinstance(v, (int, float))}
        assert numeric == {"leaves"}, f"a parent also carries {numeric - {'leaves'}}"

    def test_the_parent_count_is_not_the_sum_of_its_children(self):
        """The regression that would matter, stated as an inequality.

        55 + 18 = 73 is available and wrong. 2 is the answer.
        """
        rows = group_section(
            [leaf("code-generation", 55), leaf("code-review", 18)], section="capability"
        )
        parent = next(r for r in rows if r["kind"] == "parent")
        assert parent["leaves"] != 73
        assert parent["leaves"] == 2


class TestNoCatchAll:
    """Ruling 2. `extraction.faithfulness` took 12 facial-recognition claims
    without one candidate proposal, and never complained."""

    def test_no_parent_is_in_the_denylist(self):
        forbidden = {n.strip().lower() for n in RAW["forbidden_parents"]}
        for section, parents in RAW["sections"].items():
            for parent in parents:
                assert parent.strip().lower() not in forbidden, (
                    f"{parent!r} in {section!r} is a catch-all name"
                )

    def test_the_denylist_covers_the_shapes_that_already_exist_as_leaves(self):
        """`quality`, `general-purpose` and friends are LIVE SLUGS today, and
        harmless only because each is a singleton. Promoting one to a parent is
        the move this list exists to refuse."""
        forbidden = {n.strip().lower() for n in RAW["forbidden_parents"]}
        for name in ("general-purpose", "quality", "other", "misc", "overall"):
            assert name in forbidden

    def test_no_parent_name_is_also_a_leaf_slug(self):
        """A parent that is also a leaf collects under its own heading, which
        is how a heading quietly becomes a container."""
        for section, parents in RAW["sections"].items():
            leaves = {
                leaf_slug.strip().lower()
                for members in parents.values()
                for leaf_slug in members
            }
            for parent in parents:
                assert parent.strip().lower() not in leaves, (
                    f"{parent!r} is both a parent and a leaf in {section!r}"
                )


class TestParentsNeverRewriteLeaves:
    """Ruling 3. The repair of a backwards merge (#406) was one field, because
    no slug had been rewritten."""

    def test_every_leaf_survives_grouping_with_its_own_slug(self):
        items = [leaf("code-generation"), leaf("code-review"), leaf("long-context")]
        rows = group_section(items, section="capability")
        seen = [
            child["slug"]
            for row in rows
            for child in (row["children"] if row["kind"] == "parent" else [row])
        ]
        assert sorted(seen) == sorted(i["slug"] for i in items)

    def test_a_leaf_keeps_every_field_it_arrived_with(self):
        item = leaf("code-review", 18) | {"quotes": ["q"], "definition": "d"}
        rows = group_section([item], section="capability")
        child = rows[0]["children"][0]
        for key, value in item.items():
            assert child[key] == value

    def test_the_caller_s_list_is_not_mutated(self):
        items = [leaf("code-review")]
        before = [dict(i) for i in items]
        group_section(items, section="capability")
        assert items == before

    def test_the_file_has_no_field_naming_a_replacement_slug(self):
        text = (CONTRACT_DIR / "slug_parents.yaml").read_text(encoding="utf-8")
        for bad in ("rename", "replaces", "instead_of", "ruling_target", "merge"):
            for line in text.splitlines():
                bare = line.split("#", 1)[0]
                assert not bare.strip().startswith(f"{bad}:"), f"{bad!r} is a rewrite"


class TestUngroupedIsTheDefault:
    """Absence is not a defect (rule 6), and there is no residual bucket."""

    def test_an_unmapped_leaf_renders_at_the_top_level(self):
        rows = group_section([leaf("instruction-following", 81)], section="capability")
        assert rows[0]["kind"] == "leaf"
        assert rows[0]["parent"] is None

    def test_the_two_largest_capability_slugs_are_deliberately_ungrouped(self):
        """Forcing these under a heading to complete the taxonomy is the
        forcing defect one layer up."""
        assert parent_of("instruction-following", section="capability") is None
        assert parent_of("long-context", section="capability") is None

    def test_there_is_no_other_parent(self):
        for parents in RAW["sections"].values():
            assert "other" not in parents
            assert "misc" not in parents

    def test_best_for_has_no_parents_and_that_is_not_an_oversight(self):
        """Deferred pending #412: `coding-agent` is 142 of 282 entries and 106
        of the 142 do not belong under it."""
        assert "best_for" not in RAW["sections"]
        assert "best_for" not in slug_parents()

    def test_a_section_with_no_map_comes_back_unchanged_in_shape(self):
        items = [leaf("coding-agent", 142), leaf("classification", 10)]
        rows = group_section(items, section="best_for")
        assert [r["kind"] for r in rows] == ["leaf", "leaf"]
        assert all(r["parent"] is None for r in rows)
        assert [r["slug"] for r in rows] == ["coding-agent", "classification"]


class TestTheMapItself:
    def test_no_leaf_sits_under_two_parents(self):
        """A leaf under two parents is counted twice by any reader walking the
        map, and the loader refuses it — this pins the file itself."""
        for section, parents in RAW["sections"].items():
            seen: dict[str, str] = {}
            for parent, members in parents.items():
                for member in members:
                    assert member not in seen, (
                        f"{member!r} is under {seen[member]!r} and {parent!r} "
                        f"in {section!r}"
                    )
                    seen[member] = parent

    def test_the_loader_refuses_a_leaf_under_two_parents(self, monkeypatch):
        import judge.config as config

        slug_parents.cache_clear()
        monkeypatch.setattr(
            config,
            "_read",
            lambda name: {
                "forbidden_parents": [],
                "sections": {"capability": {"a": ["x"], "b": ["x"]}},
            },
        )
        with pytest.raises(ValueError, match="under both"):
            slug_parents()
        slug_parents.cache_clear()

    def test_the_loader_refuses_a_forbidden_parent(self, monkeypatch):
        import judge.config as config

        slug_parents.cache_clear()
        monkeypatch.setattr(
            config,
            "_read",
            lambda name: {
                "forbidden_parents": ["general-purpose"],
                "sections": {"capability": {"general-purpose": ["x"]}},
            },
        )
        with pytest.raises(ValueError, match="forbidden_parents"):
            slug_parents()
        slug_parents.cache_clear()

    def test_the_file_carries_no_counts(self):
        """Rule 11, by demonstration: the proposal behind this file went stale
        three times in 47 minutes. Anything countable is recomputed."""
        for section, parents in RAW["sections"].items():
            for parent, members in parents.items():
                assert isinstance(members, list), f"{parent} in {section}"
                assert all(isinstance(m, str) for m in members)


class TestCoverageIsComputed:
    def test_it_counts_what_is_there_rather_than_what_was_recorded(self):
        items = [leaf("code-generation"), leaf("code-review"), leaf("long-context")]
        got = coverage(items, section="capability")
        assert got == {"leaves": 3, "grouped": 2, "ungrouped": 1, "parents": 1}


class TestOrderingIsInherited:
    def test_a_parent_takes_the_position_of_its_highest_ranked_leaf(self):
        rows = group_section(
            [leaf("instruction-following", 81), leaf("code-generation", 55)],
            section="capability",
        )
        assert rows[0]["kind"] == "leaf" and rows[0]["slug"] == "instruction-following"
        assert rows[1]["kind"] == "parent" and rows[1]["parent"] == "software-engineering"

    def test_grouping_ranks_nothing_of_its_own(self):
        """Ranking parents would need a parent-level figure, and the only
        honest one is `leaves` — which sorts 29 thin leaves above 3 good ones."""
        rows = group_section(
            [leaf("reasoning", 80), leaf("code-generation", 55)], section="capability"
        )
        assert [r["parent"] for r in rows if r["kind"] == "parent"] == [
            "reasoning-and-math",
            "software-engineering",
        ]


def test_group_sections_covers_every_section_it_is_given():
    got = group_sections(
        {
            "capability": [leaf("code-review")],
            "metric": [leaf("cost-per-token", 167)],
            "best_for": [leaf("coding-agent", 142)],
        }
    )
    assert set(got) == {"capability", "metric", "best_for"}
    assert got["capability"][0]["parent"] == "software-engineering"
    assert got["metric"][0]["parent"] == "price"
    assert got["best_for"][0]["parent"] is None


class TestTheRenamedParents:
    """Three parents were renamed because a test above caught them colliding
    with live leaf slugs. Pinned, so the obvious word cannot creep back."""

    def test_the_obvious_names_are_not_used(self):
        for section, parents in RAW["sections"].items():
            for taken in ("coding", "reasoning", "token-usage"):
                assert taken not in parents, (
                    f"{taken!r} is a live leaf slug; a heading sharing a name "
                    f"with its own member is the catch-all shape ({section})"
                )

    def test_the_replacements_are_in_place(self):
        assert "software-engineering" in RAW["sections"]["capability"]
        assert "reasoning-and-math" in RAW["sections"]["capability"]
        assert "token-volume" in RAW["sections"]["metric"]

    def test_the_generic_leaves_still_sit_under_them(self):
        """The rename moved a label, not the clustering."""
        assert parent_of("coding", section="capability") == "software-engineering"
        assert parent_of("reasoning", section="capability") == "reasoning-and-math"
        assert parent_of("token-usage", section="metric") == "token-volume"


class TestAParentHasAHeading:
    """#416. Every LEAF has a display name because the extractor is required to
    produce one — *"Two to four words, title case … This is the heading the
    board renders."* Parents are written by hand and were the one heading with
    no such rule, so the board would have rendered `reasoning-and-math` directly
    above `Reasoning`, `CoT controllability` and `Over-thinking`.
    """

    def test_every_parent_has_a_name(self):
        """The CONTRACT is complete even though the CODE is permissive.

        `parent_heading()` falls back to the slug so a new parent renders
        rather than crashing a page; this makes shipping one nameless fail
        here instead of on the board.
        """
        named = {k.strip().lower() for k in RAW["parent_names"]}
        for section, parents in RAW["sections"].items():
            for parent in parents:
                assert parent.strip().lower() in named, (
                    f"{parent!r} in {section!r} has no display name, so the "
                    "board would render the slug as a heading"
                )

    def test_no_name_is_written_for_a_parent_that_does_not_exist(self):
        parents = {p.lower() for s in RAW["sections"].values() for p in s}
        for name in RAW["parent_names"]:
            assert name.strip().lower() in parents, f"{name!r} names no parent"

    def test_a_parent_row_carries_the_heading_beside_the_slug(self):
        """Beside, not instead of. A leaf carries both `slug` and `name`; a
        parent carrying only one would be the row a reader cannot look up."""
        rows = group_section([leaf("reasoning", 80)], section="capability")
        parent = rows[0]
        assert parent["parent"] == "reasoning-and-math"
        assert parent["name"] == "Reasoning and maths"

    def test_the_heading_falls_back_to_the_slug_when_unnamed(self):
        from judge.config import parent_heading, parent_names

        parent_names.cache_clear()
        assert parent_heading("a-parent-nobody-named") == "a-parent-nobody-named"

    def test_a_heading_is_not_a_count(self):
        """A name is display text. It must not smuggle a figure onto a row that
        is forbidden from carrying one."""
        for name in RAW["parent_names"].values():
            assert not re.search(r"\d", str(name)), f"{name!r} carries a digit"
