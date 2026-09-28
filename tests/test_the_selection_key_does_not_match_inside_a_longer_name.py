"""#456: `fetch_model`'s selection key no longer matches inside a longer name.

The key orders the unread threads a fetch spends its cap on. It was a
normalised substring test over the whole thread, so `gemini25flash` matched
inside `gemini25flashlite` and put 302 threads first against 208 on a boundary
check (#441). Now: raw lowercased text, a boundary at both ends, and other
registry models' longer names subtracted.

⚠ THE FINDER IS DELIBERATELY UNCHANGED. #341's rule treats a WORD suffix as
naming the base model (`GPT-5.2-Codex` names `GPT-5.2`), and
`test_the_finder_does_not_match_inside_a_longer_name.py` pins that for
attribution. The subtraction here is for an ordering key only, so nothing is
dropped (rule 8).

Measured on the #456 population 2026-09-28:
`docs/measurements/selection-key-456-2026-09-28.json`.
"""

from __future__ import annotations

import pytest

import scripts.fetch_model as fm


def _key(*surfaces):
    return fm._compile_surfaces(surfaces)


class TestTheHeadlineCase:
    def test_flash_inside_flash_lite_is_not_flash(self):
        assert not fm.names_the_model("Gemini 2.5 Flash Lite was fast",
                                      _key("Gemini 2.5 Flash"), _key("Gemini 2.5 Flash Lite"))

    def test_hyphenated_and_joined_spellings_too(self):
        own, longer = _key("Gemini 2.5 Flash"), _key("Gemini 2.5 Flash Lite")
        assert not fm.names_the_model("gemini-2.5-flash-lite", own, longer)
        assert not fm.names_the_model("gemini25flashlite", own, longer)

    def test_a_thread_naming_both_names_the_shorter_one(self):
        assert fm.names_the_model("gemini-2.5-flash-lite vs gemini-2.5-flash",
                                  _key("Gemini 2.5 Flash"), _key("Gemini 2.5 Flash Lite"))


class TestTheIssuesTable:
    @pytest.mark.parametrize("text,own,longer", [
        ("Fable 5.1 is out", "Fable 5", "Fable 5.1"),
        ("GLM-5.3 Flash rocks", "GLM 5.3", "GLM 5.3 Flash"),
        ("GPT-5.6 Luna Pro handled it", "GPT-5.6 Luna", "GPT-5.6 Luna Pro"),
    ])
    def test_a_registered_longer_name_is_subtracted(self, text, own, longer):
        assert not fm.names_the_model(text, _key(own), _key(longer))

    def test_a_following_version_digit_is_refused_even_unregistered(self):
        assert not fm.names_the_model("Tried Opus 5.5 today", _key("Opus 5"), None)
        assert not fm.names_the_model("claude-fable-5-1", _key("Claude Fable 5"), None)

    def test_dot_zero_is_the_same_version(self):
        """The finder's `_SAME_VERSION`: "Opus 5.0" names Opus 5. Refusing it
        dropped 3 of 4 threads from Opus 5 on the first measurement."""
        assert fm.names_the_model("Opus 5.0 was fine", _key("Opus 5"), _key("Opus 5.5"))

    def test_the_normaliser_no_longer_joins_across_punctuation(self):
        """"Opus 5 / 5.5" normalised to `opus555`, which contains `opus55`."""
        assert not fm.names_the_model("Opus 5 / 5.5 comparison", _key("Opus 5.5"), None)
        assert not fm.names_the_model("...and fable.\n\n5t for opus", _key("Fable 5"), None)

    def test_the_short_name_on_its_own_still_counts(self):
        assert fm.names_the_model("GLM-5.3 rocks", _key("GLM 5.3"), _key("GLM 5.3 Flash"))
        assert fm.names_the_model("claude opus 5.", _key("Opus 5"), _key("Opus 5.5"))


class _Conn:
    """Answers the two queries `longer_registry_surfaces` makes."""

    def __init__(self, aliases, names):
        self.aliases, self.names = aliases, names

    def execute(self, sql, params=()):
        rows = self.aliases if "model_alias" in sql else [(n,) for n in self.names]
        return type("R", (), {"fetchall": lambda _self: rows})()


class TestTheLongerNames:
    def test_the_models_own_names_are_never_longer(self):
        """Measured 2026-09-28: another row also carried `claude fable 5`, and it
        subtracted Fable 5 from its own threads until this was excluded."""
        conn = _Conn([("claude fable 5", ["claude fable 5"]), ("Fable 5.1", ["fable 5.1"])], [])
        out = fm.longer_registry_surfaces(conn, "mv_fable5", ["fable 5", "claude fable 5"])
        assert "claude fable 5" not in out
        assert "Fable 5.1" in out and "fable 5.1" in out

    def test_a_display_name_counts_without_its_vendor_prefix(self):
        conn = _Conn([], ["Z.ai: GLM 5.3 Flash"])
        out = fm.longer_registry_surfaces(conn, "mv_glm53", ["glm 5.3"])
        assert "GLM 5.3 Flash" in out

    def test_a_name_that_does_not_contain_ours_is_left_out(self):
        conn = _Conn([("Gemini 3.8 Flash", ["gemini 3.8 flash"])], ["Google: Gemini 2.5 Pro"])
        assert fm.longer_registry_surfaces(conn, "mv", ["gemini 2.5 flash"]) == []


def test_the_finder_keeps_its_own_rule():
    """The subtraction must not have leaked into the finder: a word suffix
    still names the base model there."""
    import inspect

    from collect import surface_resolver

    assert "names_the_model" not in inspect.getsource(surface_resolver)
