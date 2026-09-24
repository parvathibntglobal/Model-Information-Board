"""#302: the roster counted cells across every `pipeline_version`.

`CellStore.__init__` takes a `pipeline_version` and says why in its own
docstring:

    `claim_id_for` hashes `pipeline_version`, so a bump FORKS the table: after
    `judge reweight` the same quote exists twice, once at e5.1 and once at
    e5.2, with different weights and the same `author_id`. `count()` keeps one
    representative per voice AT ITS HIGHEST WEIGHT, so an unfiltered read would
    silently give every voice the better of its two tiers and report an `n_eff`
    that belongs to no version — worst on exactly the claims a re-tier moved,
    which are the ones being measured.

`judge/pages/roster.py` was the unfiltered read that docstring warns about, and
it was on the page as shipped. Measured 2026-09-15:

    cell rows by version        e5.1  86      e5.4  49
    models spanning >1 version  12 of 45, every one exactly two

    DeepSeek V4 Pro      "6 cells"  =  5 at e5.4 + 1 stale at e5.1
    Claude Opus 4.8      7 cells across two generations

The stale DeepSeek cell is `context.effective_window` holding *"permanent 75%
reduction in DeepSeek V4 Pro pricing"* — a price quote filed under context
window by the retired Gemini extractor, not recounted since 2026-08-31.

⚠ FILTERING ALONE WAS THE WRONG FIX, which is why this took a ruling rather
  than a patch. A model whose only cells are older would drop from
  `insufficient` to `unreported` — reading as *"nobody has discussed this"*
  when the truth is *"we have not recounted this since the extractor changed"*.
  Rule 4 exactly, and it would hit every model nobody has re-fetched.

  Ruled option B by @anoojntglobal-sudo on 2026-09-24: **filter to the current
  version, and say what was dropped.** More urgent than when it was proposed,
  because e5.5 produces no cells at all — so an unfiltered count shows e5.4
  numbers for a generation that has none, which is a missing generation
  silently answered by an older one.
"""

from __future__ import annotations

import pathlib
import re

from judge.pages.roster import SQL, RosterReader, _evidence
from judge.store.claims import PIPELINE_VERSION

ROOT = pathlib.Path(__file__).resolve().parents[1]


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0]


class _Conn:
    def __init__(self, rows):
        self._rows = rows
        self.params = []

    def execute(self, sql, params=None):
        self.params.append(params)
        if "pricing_history" in sql:
            return _Result([(None,)])
        return _Result(self._rows)


def _row(name, *, cells, published=0, stale=0, stale_versions=None, keys=None):
    return (
        f"mv_{name}", name, "vendor", f"vendor/{name}",
        1, 2, None, 128000, 4096, True, False, True, None, None,
        cells, published, stale, stale_versions, keys, 0, None,
    )


class TestTheQueryIsScopedToOneGeneration:
    def test_every_cell_subquery_names_the_version(self):
        """⚠ ALL FIVE. The count, the published count, the stale count, the
        stale-version aggregate and the capability-key aggregate all read
        `cell` — and I asserted four on the first run, having forgotten that
        the list of dropped versions is itself a read of the table it is
        reporting about. Scoping four of five would leave the capability chips
        describing a generation the counts beside them do not."""
        subqueries = re.findall(r"\(SELECT[^;]*?FROM cell c.*?\)\s+AS \w+", SQL, re.S)
        assert len(subqueries) == 5, f"the cell subqueries moved: {len(subqueries)}"
        for q in subqueries:
            assert "pipeline_version" in q, f"unscoped cell read:\n{q}"

    def test_the_version_arrives_as_a_parameter(self):
        """Not interpolated. The version is a value, and a value that reaches
        SQL by formatting is a value somebody will format from a request."""
        assert "%(pipeline_version)s" in SQL
        conn = _Conn([_row("a", cells=0)])
        RosterReader(conn).all()
        assert conn.params[0] == {"pipeline_version": PIPELINE_VERSION}

    def test_it_defaults_to_the_current_generation(self):
        conn = _Conn([_row("a", cells=0)])
        RosterReader(conn).all()
        assert conn.params[0]["pipeline_version"] == PIPELINE_VERSION

    def test_a_caller_can_ask_about_another_generation_explicitly(self):
        """Named rather than positional, so reading an older generation is
        something a caller says out loud."""
        conn = _Conn([_row("a", cells=0)])
        RosterReader(conn, pipeline_version="e5.1").all()
        assert conn.params[0]["pipeline_version"] == "e5.1"


class TestWhatWasDroppedIsCountedRatherThanHidden:
    def test_a_mixed_generation_model_reports_both_numbers(self):
        """DeepSeek's shape: five current, one not recounted since e5.1."""
        conn = _Conn([_row("deepseek", cells=5, stale=1, stale_versions=["e5.1"])])
        evidence = RosterReader(conn).all().models[0]["evidence"]
        assert evidence["cells"] == 5
        assert evidence["not_recounted"] == 1
        assert evidence["not_recounted_since"] == ["e5.1"]

    def test_the_count_excludes_the_stale_ones(self):
        """⚠ THE DEFECT ITSELF. `cells` must be the current generation alone —
        if the stale ones were added back for a friendlier total, the number
        would again belong to no version."""
        conn = _Conn([_row("deepseek", cells=5, stale=1, stale_versions=["e5.1"])])
        assert RosterReader(conn).all().models[0]["evidence"]["cells"] == 5

    def test_a_model_with_only_older_cells_is_unreported_and_says_why(self):
        """⚠ THE CASE THAT MADE FILTERING-ALONE WRONG. The state is honest —
        this generation has counted nothing — and on its own it would read as a
        fact about the model rather than about our coverage."""
        conn = _Conn([_row("stale", cells=0, stale=4, stale_versions=["e5.1", "e5.4"])])
        evidence = RosterReader(conn).all().models[0]["evidence"]
        assert evidence["state"] == "unreported"
        assert evidence["cells"] == 0
        assert evidence["not_recounted"] == 4
        assert evidence["not_recounted_since"] == ["e5.1", "e5.4"]

    def test_zero_is_a_measurement_and_the_key_is_always_present(self):
        """Rule 6 in the other direction: 0 says we looked at every other
        generation and found nothing. A missing key would say nobody asked."""
        evidence = _evidence(cells=3, published=0, capability_keys=["a"])
        assert evidence["not_recounted"] == 0
        assert evidence["not_recounted_since"] == []

    def test_it_is_carried_on_every_state(self):
        for cells, published, state in ((0, 0, "unreported"), (3, 0, "insufficient"),
                                        (3, 2, "published")):
            evidence = _evidence(
                cells=cells, published=published, capability_keys=[],
                stale=1, stale_versions=["e5.1"],
            )
            assert evidence["state"] == state
            assert evidence["not_recounted"] == 1, state


class TestTheVersionsTravelWithTheCount:
    def test_it_names_which_generation_rather_than_only_how_many(self):
        """*"1 not recounted"* is a fact. *"1 not recounted since e5.1"* is one
        somebody can act on — it says which extractor produced it, which is how
        the DeepSeek price-quote-under-context-window cell was identified."""
        conn = _Conn([_row("x", cells=5, stale=1, stale_versions=["e5.1"])])
        evidence = RosterReader(conn).all().models[0]["evidence"]
        assert evidence["not_recounted_since"] == ["e5.1"]

    def test_a_null_aggregate_becomes_an_empty_list(self):
        """`array_agg` over no rows is NULL, not an empty array — the same trap
        the capability keys already carry a comment about."""
        conn = _Conn([_row("x", cells=5, stale=0, stale_versions=None)])
        assert RosterReader(conn).all().models[0]["evidence"]["not_recounted_since"] == []
