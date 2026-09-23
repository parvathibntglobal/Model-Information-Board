"""Group a board section's leaves under parent headings, at read time. #410.

WHAT THIS IS, IN ONE SENTENCE FROM THE REVIEW THAT SETTLED IT:

    A parent groups for reading and never implies the leaves are the same
    measurement.

That is why a wrong member list is cheap — it costs a reader one click rather
than costing the board a wrong number — and it is the property to check any
change here against.

WHY A PURE FUNCTION OVER `board_sections()` AND NOT A SECOND QUERY

`board_sections()` already resolves what a leaf IS: it excludes `declined`
rows, counts `merged` rows under their target, and folds spellings so
`exploitbench` and `exploit-bench` are one bucket. By the time a section list
reaches here, `slug` is the RESOLVED slug — post-merge, post-spelling.

Re-deriving any of that from `board_entry` would give two answers to "what is a
leaf" and they would drift. So this takes the output and regroups it, and the
grouping is the only thing it knows how to do.

⚠ A PARENT IS NOT A MERGE, AND THE DIFFERENCE IS THE WHOLE DESIGN. `merged`
  COLLAPSES a leaf into another leaf: the rows move and one heading survives. A
  parent does not collapse anything — every leaf stays visible underneath with
  its own name, count and quotes. That is what lets a wrong member list be
  undone by editing one line of YAML, and it is why `normalise_slug`'s refusal
  to fold `tool-calling` into `function-calling` is untouched by any of this.

⚠ AND A PARENT CARRIES A COUNT OF LEAVES, NEVER A COUNT OF VOICES. Summing the
  leaves' `reports` is wrong twice over, not merely against a rule:

    1. It DOUBLE-COUNTS documents. One document can produce entries under
       several slugs of one parent. Measured on `coding`, 2026-09-23: the
       leaves' distinct-document counts sum to 55 against a true union of 51,
       7.8% over, from 3 documents appearing under two leaves each.
    2. It SUMS FLOORS. `reports` is already ">= N" because an open vocabulary
       fragments a section until somebody merges it. A sum of floors is a
       floor whose error compounds, presented as a total.

  So `leaves` is the only count this module emits, and it is exact.
"""

from __future__ import annotations

from typing import Any

from judge.config import parent_heading, slug_parents

#: A leaf with no parent renders at the top level, beside the parents rather
#: than beneath a residual heading. There is deliberately no `other` bucket:
#: 19 capability slugs and 20 metric slugs are ungrouped on purpose, including
#: the two largest capability slugs, and a taxonomy that covers everything has
#: forced something.
UNGROUPED = None


def group_section(items: list[dict], *, section: str) -> list[dict]:
    """Regroup one section's leaves under their parents, order preserved.

    Args:
        items: `board_sections()[section]`, each a resolved leaf.
        section: which section these are, to pick the map.

    Returns a list of rows in the section's existing order, where each row is
    either a leaf (unchanged, with `parent: None`) or a parent heading carrying
    its leaves. A parent appears at the position of its highest-ranked leaf, so
    the section's ordering — by report count, which is a count — is not
    disturbed by grouping.

    ⚠ ORDERING IS INHERITED, NEVER RECOMPUTED. Ranking parents by anything of
      their own would need a parent-level figure, and the only honest one is
      `leaves`, which would sort a heading with 29 thin leaves above one with
      3 well-evidenced ones. Inheriting the caller's order keeps whatever it
      ranked by, and this module stays unable to rank.

    A section with no entry in the map (today: `best_for`) comes back as leaves
    with `parent: None`, which is the same shape and renders as it does now.
    """
    mapping = slug_parents().get(section, {})
    if not mapping:
        return [_leaf(item) for item in items]

    out: list[dict] = []
    at: dict[str, int] = {}
    for item in items:
        parent = mapping.get((item.get("slug") or "").strip().lower(), UNGROUPED)
        if parent is UNGROUPED:
            out.append(_leaf(item))
            continue
        if parent not in at:
            at[parent] = len(out)
            out.append(
                {
                    "kind": "parent",
                    "parent": parent,
                    # THE HEADING, beside the slug rather than instead of it.
                    # A leaf carries both `slug` and `name`; a parent that
                    # carried only one would be the one row on the page a
                    # reader cannot look up. Falls back to the slug (#416).
                    "name": parent_heading(parent),
                    # A COUNT OF LEAVES. Never a sum of `reports` — see the
                    # module docstring for the two reasons that is wrong
                    # arithmetic and not only a rule.
                    "leaves": 0,
                    "children": [],
                }
            )
        row = out[at[parent]]
        row["children"].append(_leaf(item, parent=parent))
        row["leaves"] = len(row["children"])
    return out


def _leaf(item: dict, *, parent: str | None = None) -> dict:
    """One leaf, unchanged except for the heading it is filed under.

    The item is passed through rather than projected, so a field added to
    `board_sections()` reaches the page without a change here. Copied rather
    than mutated because the caller's list is reused by other readers.
    """
    return {**item, "kind": "leaf", "parent": parent}


def group_sections(sections: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """`group_section` over every section a board payload carries."""
    return {name: group_section(items, section=name) for name, items in sections.items()}


def parent_of(slug: str, *, section: str) -> str | None:
    """The heading one leaf sits under, or None when it is ungrouped.

    ABSENCE IS THE DEFAULT AND IS NOT AN ERROR (rule 6). An unmapped slug is a
    leaf nobody has filed yet, which is a different thing from a leaf that has
    been ruled to belong nowhere — and this file has no way to express the
    second, deliberately.
    """
    return slug_parents().get(section, {}).get((slug or "").strip().lower())


def coverage(items: list[dict], *, section: str) -> dict[str, Any]:
    """How much of a section the map actually covers, computed not recorded.

    Rule 11: the numbers this would otherwise be written down as move with
    every extraction run — the proposal behind this file went stale three times
    in 47 minutes. So the file carries no counts and this recomputes them.
    """
    mapping = slug_parents().get(section, {})
    grouped = [i for i in items if (i.get("slug") or "").lower() in mapping]
    return {
        "leaves": len(items),
        "grouped": len(grouped),
        "ungrouped": len(items) - len(grouped),
        "parents": len({mapping[(i["slug"] or "").lower()] for i in grouped}),
    }
