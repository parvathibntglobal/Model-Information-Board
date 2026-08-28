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
