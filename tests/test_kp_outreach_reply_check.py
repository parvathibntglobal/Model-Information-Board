"""The outreach REPLY CHECK (reply_check.py). Pure functions: no database, no
network. Each rule has a passing and a refused example, against the real
config files, so a config edit that breaks a rule fails here."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

OUTREACH = Path(__file__).resolve().parent.parent / "web" / "src" / "kitepulse" / "outreach"
if str(OUTREACH) not in sys.path:
    sys.path.insert(0, str(OUTREACH))

import reply_check  # noqa: E402
from reply_check import check  # noqa: E402

RULES = reply_check.load_rules()
DISCLOSURE = "Disclosure: I work on Kite Pulse"
HEADROOM = ("Kite Pulse shows who on a team is close to a Claude Code plan limit: the "
            "5-hour window, the weekly window and each model's weekly window.")
THREAD = {"source": "hackernews", "url": "https://news.ycombinator.com/item?id=50334110",
          "title": "Claude Code usage limit hit after 2 hours",
          "body": "We are a team of 12 and keep hitting the limit."}

GOOD = f"""The 5-hour window starts at your first message, not on the hour, so heavy
morning use can lock you out until early afternoon. With 12 people it helps to
see who is close before they hit it.

{HEADROOM}

{DISCLOSURE}"""


def codes(result):
    return [f.code for f in result.failures]


def test_a_reply_that_helps_first_and_uses_an_approved_sentence_passes():
    r = check(GOOD, THREAD, RULES)
    assert r.passed, r.failures
    assert r.claims_used == ("plan-headroom",)
    assert r.not_checked, "a pass must always say what it did not check"


def test_the_pitchy_example_fails_on_every_rule_it_breaks():
    bad = ("Kite Pulse is the best way to fix this! It tracks cost for every tool and "
           "is SOC 2 certified, and Kite Pulse is free.\n\n" + DISCLOSURE)
    got = codes(check(bad, THREAD, RULES))
    for code in ("pitch_first", "unapproved_claim", "refused_phrase", "too_many_mentions"):
        assert code in got, got


# --- disclosure --------------------------------------------------------------

@pytest.mark.parametrize("line", [DISCLOSURE, DISCLOSURE + ".",
                                  "  disclosure: i work on  kite pulse!"])
def test_the_disclosure_line_is_found_with_punctuation_case_and_spacing(line):
    assert "no_disclosure" not in codes(check(GOOD.replace(DISCLOSURE, line), THREAD, RULES))


def test_a_missing_or_buried_disclosure_fails():
    assert "no_disclosure" in codes(check(GOOD.replace(DISCLOSURE, ""), THREAD, RULES))
    buried = GOOD.replace(f"\n\n{DISCLOSURE}", f" {DISCLOSURE}")
    assert "no_disclosure" in codes(check(buried, THREAD, RULES))


# --- mentions and claims -----------------------------------------------------

def test_a_reply_that_never_names_kite_pulse_passes_without_a_claim():
    r = check("Use /status to see the window.\n\n" + DISCLOSURE, THREAD, RULES)
    assert r.passed and r.claims_used == ()


def test_an_approved_sentence_reworded_is_unapproved():
    reworded = GOOD.replace("is close to", "is near")
    assert "unapproved_claim" in codes(check(reworded, THREAD, RULES))


def test_curly_quotes_and_line_wraps_do_not_break_an_approved_sentence():
    wrapped = GOOD.replace("model's", "model’s").replace(": the 5-hour", ":\nthe 5-hour")
    assert check(wrapped, THREAD, RULES).passed


@pytest.mark.parametrize("spelling", ["KitePulse", "kite-pulse", "KITE PULSE"])
def test_every_spelling_of_the_name_counts_as_a_mention(spelling):
    assert "unapproved_claim" in codes(check(
        f"Fix: wait.\n\nTry {spelling} for this.\n\n{DISCLOSURE}", THREAD, RULES))


def test_two_approved_sentences_are_two_mentions():
    two = GOOD.replace(HEADROOM, HEADROOM + " Kite Pulse shows token use per developer, "
                       "tool, model, project and day.")
    assert "too_many_mentions" in codes(check(two, THREAD, RULES))


# --- refused phrases, help first --------------------------------------------

def test_a_refused_phrase_anywhere_fails_and_whole_words_only():
    assert "refused_phrase" in codes(check(GOOD + "\nWe support single sign-on.", THREAD, RULES))
    assert "refused_phrase" not in codes(check(GOOD.replace("early", "macro"), THREAD, RULES))


def test_naming_kite_pulse_in_the_first_paragraph_is_pitch_first():
    first = f"{HEADROOM}\n\nThe window resets at your first message.\n\n{DISCLOSURE}"
    assert "pitch_first" in codes(check(first, THREAD, RULES))


# --- links -------------------------------------------------------------------

def test_vendor_docs_and_the_threads_own_site_are_allowed():
    text = (GOOD + "\nSee https://docs.anthropic.com/en/docs/limits and "
            "news.ycombinator.com/item?id=1")
    assert "link_not_allowed" not in codes(check(text, THREAD, RULES))


def test_any_other_link_and_any_kite_pulse_link_is_refused_while_no_site_is_live():
    assert RULES.kite_pulse_link_domains == frozenset()
    got = check(GOOD + "\nhttps://example.com/x https://kitepulse.io/pricing", THREAD, RULES)
    details = [f.detail for f in got.failures if f.code == "link_not_allowed"]
    assert any("example.com" in d for d in details)
    assert any("no public site" in d for d in details)


def test_at_most_one_kite_pulse_link_once_the_site_is_listed():
    live = replace(RULES, kite_pulse_link_domains=frozenset({"kitepulse.io"}))
    one = GOOD + "\nhttps://kitepulse.io/a"
    assert "too_many_kp_links" not in codes(check(one, THREAD, live))
    assert "too_many_kp_links" in codes(check(one + " https://kitepulse.io/b", THREAD, live))


# --- numbers, length ---------------------------------------------------------

def test_a_number_from_nowhere_fails_and_names_the_number():
    got = check(GOOD.replace("12 people", "40% of teams"), THREAD, RULES)
    fail = [f for f in got.failures if f.code == "number_not_in_sources"]
    assert fail and "40" in fail[0].detail


def test_numbers_inside_a_link_are_not_figures():
    text = GOOD + "\nhttps://github.com/anthropics/claude-code/issues/9999"
    assert "number_not_in_sources" not in codes(check(text, THREAD, RULES))


def test_length_is_per_source():
    long = GOOD + "\n" + "x" * 1500
    assert "too_long" in codes(check(long, THREAD, RULES))
    assert "too_long" not in codes(check(long, {**THREAD, "source": "github",
                                                "url": "https://github.com/a/b/discussions/1"},
                                         RULES))


# --- refusals and config -----------------------------------------------------

def test_empty_text_is_refused_not_passed():
    with pytest.raises(reply_check.Refused):
        check("   ", THREAD, RULES)


def test_a_source_with_no_length_rule_is_a_config_error_not_a_pass():
    # x: a source with no Finder yet, so no length rule (reddit had none until 2026-11-10)
    with pytest.raises(reply_check.RulesError, match="'x'"):
        check(GOOD, {**THREAD, "source": "x"}, RULES)


def test_an_unreviewed_claims_file_is_said_on_every_result():
    assert RULES.claims_reviewed_by is None
    assert any("not been reviewed" in w for w in check(GOOD, THREAD, RULES).warnings)


def test_every_finder_source_has_a_length():
    assert set(RULES.max_reply_chars) == {"hackernews", "devto", "discourse", "github", "reddit"}
