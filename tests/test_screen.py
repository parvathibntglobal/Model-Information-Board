"""The pre-LLM screen — the hard gates that run before the extractor reads.

The property: text a rule would reject never reaches the model, and every drop
names its trigger. The rules themselves are judge/vet/reject.py's and tested
there; these check the SCREEN wires them (and the cheap placeholder/length
gates) correctly, in cheapest-first order.
"""

from __future__ import annotations

from judge.screen import MIN_SIGNAL_CHARS, links_in, screen

_CLEAN = "gemini 2.5 flash stayed accurate well past 50k tokens in our summariser"


class TestPreLLMScreen:
    def test_clean_on_topic_text_passes(self):
        assert screen(text=_CLEAN).dropped is False

    def test_a_platform_placeholder_is_dropped(self):
        v = screen(text="[removed]")
        assert v.dropped and v.trigger == "placeholder"

    def test_too_short_is_dropped_and_is_the_cheapest_gate(self):
        assert len("too short to say anything") < MIN_SIGNAL_CHARS
        v = screen(text="too short to say anything")
        assert v.dropped and v.trigger == "too_short"

    def test_a_sponsored_disclosure_is_dropped(self):
        v = screen(text="This entire write-up is sponsored by Acme, who paid me for it.")
        assert v.dropped and v.trigger == "sponsored_disclosure"

    def test_a_discount_code_is_dropped(self):
        v = screen(text="Solid model, and you can use code SAVE20 at their checkout page.")
        assert v.dropped and v.trigger == "discount_code"

    def test_the_deferred_rules_do_not_fire_falsely(self):
        # release-date (rule 5) and syndication (rule 4) need inputs the screen
        # deliberately does not pass, so a long clean thread must PASS, not trip
        # a rule running on empty mentions / no cluster.
        v = screen(text="A long, careful thread about gemini 2.5 flash and its "
                        "long-context recall in practice.")
        assert v.dropped is False

    def test_links_are_extracted_for_the_affiliate_rule(self):
        got = links_in("see https://example.com/x?ref=1 and http://foo.bar/y here")
        assert "https://example.com/x?ref=1" in got
        assert "http://foo.bar/y" in got


class TestBotSelfIdentification:
    def test_an_explicit_bot_is_dropped(self):
        v = screen(text="I am a bot, and this action was performed automatically by me.")
        assert v.dropped and v.trigger == "bot_selfid"

    def test_beep_boop_is_dropped(self):
        v = screen(text="Beep boop! Here is the summary you asked for, from your friendly helper.")
        assert v.dropped and v.trigger == "bot_selfid"

    def test_a_human_mentioning_bots_is_not_dropped(self):
        # Discussing bots is not being one — the pattern is a self-identification.
        v = screen(text="gemini handled the bot-detection task well and did not overthink it")
        assert v.dropped is False


class TestLanguage:
    def test_clean_english_passes(self):
        assert screen(text=_CLEAN).dropped is False

    def test_non_latin_script_is_dropped(self):
        # Chinese — decisively non-Latin, so the script ratio fires. Long enough
        # to clear the too_short floor and reach the language check.
        v = screen(text=(
            "这个模型对于大型任务非常有效并且每次都能可靠地处理长文本内容"
            "表现优秀稳定可靠值得推荐给所有需要它的团队在生产环境中使用"
        ))
        assert v.dropped and v.trigger == "non_english"

    def test_latin_text_with_no_english_function_words_is_dropped(self):
        # Long Latin-script text carrying not one common English word.
        v = screen(text=(
            "zzt qmx lorplk vwenta brklm frtsun glomph vrenzik tolmaq brundel "
            "wexlo praften murgle snelvok trundish greblik omphal wextra brommel snargle"
        ))
        assert v.dropped and v.trigger == "non_english"

    def test_thin_text_is_never_dropped_on_language(self):
        # Under the letter floor: judged too little to call, so kept (but caught
        # by too_short first here — the point is language does not fire on it).
        assert screen(text="mañana").trigger != "non_english"

    def test_code_shaped_english_is_kept(self):
        # Error strings / identifiers with English function words present must pass.
        v = screen(text="the call failed with TypeError: cannot read property of "
                        "undefined in the loop")
        assert v.dropped is False
