"""`club_surfaces` — the OR query, and what it refuses to hide.

The OPERATOR itself is not tested here: whether twitter241 honours `OR` is a
fact about a third party, measured with real requests in
`docs/measurements/x-boolean-operator-probe.json` and not re-assertable from a
fixture. What is testable locally is that the query we build is the query we
say we built, which is the half that can silently rot.
"""
from __future__ import annotations

from collect.adapters.x import MAX_CLUBBED_SURFACES, club_surfaces


def test_surfaces_are_quoted_and_or_joined():
    c = club_surfaces(["opus 5", "opus5"])
    assert c.query == '"opus 5" OR "opus5"'
    assert c.used == ("opus 5", "opus5")
    assert c.dropped == ()


def test_a_multi_word_surface_is_quoted_so_it_cannot_split():
    """Unquoted, `claude opus` is two tokens the index may match apart."""
    assert club_surfaces(["claude opus"]).query == '"claude opus"'


def test_one_surface_is_still_a_valid_query_with_no_operator():
    c = club_surfaces(["opus 5"])
    assert c.query == '"opus 5"'
    assert " OR " not in c.query


def test_nothing_usable_gives_an_empty_query_rather_than_a_bare_or():
    """The caller skips on a falsy query. `'" OR "'` would be a real search."""
    c = club_surfaces(["", "   "])
    assert c.query == ""
    assert c.used == ()
    assert len(c.dropped) == 2


def test_surfaces_over_the_cap_are_reported_not_trimmed_quietly():
    surfaces = [f"s{i}" for i in range(MAX_CLUBBED_SURFACES + 3)]
    c = club_surfaces(surfaces)
    assert len(c.used) == MAX_CLUBBED_SURFACES
    assert len(c.dropped) == 3
    # The dropped ones are the ones absent from the query, not just counted.
    for surface in c.dropped:
        assert f'"{surface}"' not in c.query


def test_the_character_ceiling_drops_rather_than_truncates():
    """A truncated disjunction is a DIFFERENT query that looks like this one."""
    c = club_surfaces(["a" * 200, "b" * 200, "c" * 200], max_chars=480)
    assert len(c.used) == 2
    assert len(c.dropped) == 1
    assert c.query.endswith('"' + "b" * 200 + '"')


def test_a_surface_carrying_a_quote_is_dropped_and_named():
    """No documented escape inside an X quoted phrase, so it is not attempted."""
    c = club_surfaces(['opus 5', 'say "hi"'])
    assert c.used == ("opus 5",)
    assert c.dropped == ('say "hi"',)
    assert c.query == '"opus 5"'


def test_every_input_lands_in_exactly_one_of_used_or_dropped():
    """The accounting is the reason this returns a type rather than a string."""
    surfaces = ["opus 5", "", "claude opus", 'q"x', *[f"s{i}" for i in range(8)]]
    c = club_surfaces(surfaces)
    assert len(c.used) + len(c.dropped) == len(surfaces)
