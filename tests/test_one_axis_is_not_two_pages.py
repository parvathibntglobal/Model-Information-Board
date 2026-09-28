"""Stopping a benchmark becoming two axis pages, and the two ways it happened.

A reader found this on the metrics tab:

    AIME         Score on the AIME math competition benchmark.      1 model
    AIME 2026    Performance on the AIME 2026 mathematics benchmark. 1 model

Same model, same 97.1%, same benchmark, two pages. And the cause was not two
writers disagreeing - it was the extractor copying to different depths:

    slug 'aime'       quote: "97.1% on AIME 2026 math"    <- the full name is there
    slug 'aime-2026'  quote: "97.1% on AIME 2026"

Both copies really are in their quotes, so `metric_refusal`'s substring check
passes either. A substring test cannot tell a complete name from a prefix.

⚠ THERE ARE THREE KINDS AND ONLY ONE IS A PROMPT PROBLEM. Measured over the
  314 published figures and 104 axes on 2026-09-21:

    TRUNCATION      'aime' vs 'aime-2026'          -> the extractor is asked
    SPELLING        'exploitbench' vs 'exploit-bench' -> code, here
    REAL VERSIONS   'osworld' vs 'osworld-2'       -> must NOT merge, ever

⚠ AND THE MECHANICAL FIX FOR TRUNCATION IS A TRAP. `axis_specificity` already
  detects a name that continues. On the same 314 figures it fired five times,
  and THREE of the five continuations were the score rather than the name:

      'CyberGym'     -> 'CyberGym 84.5'      (84.5% is the result)
      'ExploitBench' -> 'ExploitBench 54.4'  (54.4% is the result)
      'AIME'         -> 'AIME 2026'          (a year, genuinely the name)

  Extending the copy automatically would invent three axes named after
  measurements to repair two. Telling a year from a score is a reading task,
  so it is asked of the extractor and reported here as a weight (rule 8).
"""

from __future__ import annotations

import pathlib

from judge.store.board_entries import normalise_slug, spelling_key

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "judge" / "extract" / "schema.py"


class TestSeparatorsAreNotMeaning:
    """`spelling_key` - the half no prompt can do."""

    def test_a_hyphen_does_not_make_a_second_benchmark(self):
        assert spelling_key("exploit-bench") == spelling_key("exploitbench")
        assert spelling_key("exploit-gym") == spelling_key("exploitgym")
        assert spelling_key("over-thinking") == spelling_key("overthinking")

    def test_a_version_number_absolutely_does(self):
        """⚠ THE ONE THING THIS MUST NEVER DO. `osworld` and `osworld-2` are
        different versions of a benchmark, and folding them would be #368's
        defect with the sign flipped - a figure filed under a benchmark it was
        not measured on."""
        assert spelling_key("osworld") != spelling_key("osworld-2")
        assert spelling_key("arc-agi") != spelling_key("arc-agi-3")
        assert spelling_key("aime") != spelling_key("aime-2026")
        assert spelling_key("posttrainbench") != spelling_key("posttrainbench-plus")

    def test_it_resolves_no_synonyms(self):
        """`normalise_slug` refuses to fold `tool-calling` into
        `function-calling` because that is a judgement about MEANING. This
        folds separators, which is a judgement about nothing - and it must
        not quietly grow into the other thing."""
        assert spelling_key("tool-calling") != spelling_key("function-calling")
        assert spelling_key("swe-bench") != spelling_key("swebench-verified")

    def test_it_agrees_with_normalise_slug_on_what_a_separator_is(self):
        assert spelling_key(normalise_slug("Exploit Bench")) == spelling_key("exploitbench")
        assert spelling_key(normalise_slug("Exploit_Bench")) == spelling_key("exploitbench")


class TestThePageSaysWhichSpellingsItStandsFor:
    def test_the_shown_slug_is_the_one_most_writers_used(self):
        # Not whichever row the ORDER BY put first: this is the URL as well as
        # the title, and an address that changes when a fourth report arrives
        # breaks every link to the page.
        src = (ROOT / "judge" / "store" / "board_entries.py").read_text(encoding="utf-8")
        assert 'min(spellings.items(), key=lambda kv: (-kv[1], kv[0]))[0]' in src

    def test_the_alternatives_are_reported_rather_than_swallowed(self):
        src = (ROOT / "judge" / "store" / "board_entries.py").read_text(encoding="utf-8")
        assert 'item["spelled_also"] = sorted' in src
        js = (ROOT / "web" / "src" / "board" / "views.js").read_text(encoding="utf-8")
        assert "Also written" in js, (
            "a page standing for two spellings without saying so is making a "
            "claim the reader cannot check (rule 4)"
        )


class TestTheExtractorIsAskedForTheWholeName:
    """The half code cannot do, because it needs a year told from a score."""

    def test_it_is_asked_to_include_a_version_or_year(self):
        text = SCHEMA.read_text(encoding="utf-8")
        assert "COPY THE WHOLE NAME, INCLUDING A VERSION OR YEAR THAT IS PART OF" in text
        assert "'AIME 2026', not 'AIME'" in text.replace('\\"', '"').replace("\\'", "'")

    def test_it_is_told_where_the_name_stops(self):
        """Without this the instruction above turns `CyberGym 84.5%` into an
        axis called after its own result."""
        text = SCHEMA.read_text(encoding="utf-8")
        assert "BUT STOP AT THE NAME" in text
        assert "CyberGym" in text and "ExploitBench" in text

    def test_it_still_says_empty_is_correct(self):
        # The instruction to copy MORE must not become pressure to fill the
        # field in. A run whose description said "REQUIRED" and "leave this
        # empty" in one paragraph returned 0 absent and 19 unsupported of 22.
        text = SCHEMA.read_text(encoding="utf-8")
        assert "OPTIONAL, and empty is a correct answer" in text
        assert "If you cannot tell which you are looking" in text, (
            "the tie-break must send an unsure extractor to the SHORTER name, "
            "or the new instruction becomes a licence to guess"
        )
