"""A named AI agent or assistant PRODUCT is the subject of a claim (2026-11-17).

The extractor's rule 1 asked for "a MODEL, named specifically enough to
identify", and it read product names as not models: on the 2026-11-15 agent
run it dropped first-hand ChatGPT Work reports ("ChatGPT is a product, not a
model") and, replayed, Claude Code threads too ("'claude code' is a
product/tool name, not a model name"). Every tracked agent (contract/
tracked_agents.yaml) is a product, so the agent fetch could lose any of its
reports this way. The rule now says a named agent or assistant product counts.

These tests pin the wording, not the model's behaviour: whether the extractor
follows it is measured on the runner (PR body).
"""

from __future__ import annotations

from judge.extract import prompt


def test_rule_one_counts_a_named_agent_or_assistant_product():
    flat = " ".join(prompt.SYSTEM_PROMPT.replace("\\\n", " ").split())
    assert "A named AI AGENT OR ASSISTANT PRODUCT counts as the model of a claim" in flat
    assert "Do not drop a first-hand report because the name is a product" in flat


def test_the_specificity_bar_stays():
    # Widened to products, not loosened: an unidentifiable reference is still not a model.
    assert '"the cheap Anthropic one"' in prompt.SYSTEM_PROMPT


def test_the_examples_are_not_from_the_threads_it_was_written_against():
    # The 2026-11-15 threads that showed the defect were ChatGPT Work and Claude
    # Code reports; an example quoting them would bias any measurement on them.
    flat = " ".join(prompt.SYSTEM_PROMPT.split()).lower()
    assert "chatgpt work" not in flat
    assert "froze" not in flat


def test_the_legacy_free_prompt_still_builds():
    # _LEGACY_PASSAGES asserts its passages are present; rule 1 is not one of
    # them, so the edit must leave both prompt forms buildable.
    assert "A named AI AGENT OR ASSISTANT PRODUCT" in " ".join(
        prompt.build_system_prompt([], legacy=False).replace("\\\n", " ").split())
