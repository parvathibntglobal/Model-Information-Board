"""The code-counted has_repro_steps — the rule-2-clean replacement for the
extractor's boolean. Detects reproduction artifacts; makes no judgement."""

from __future__ import annotations

from judge.vet.repro import has_repro_steps


class TestPresent:
    def test_a_code_fence(self):
        assert has_repro_steps("here is what I ran:\n```\nmodel.generate(x)\n```")

    def test_a_shell_prompt(self):
        assert has_repro_steps("reproduce with\n$ pip install foo && python run.py")

    def test_a_stack_trace(self):
        assert has_repro_steps("Traceback (most recent call last):\n  File ...")

    def test_an_error_string(self):
        assert has_repro_steps("it crashed with TypeError: cannot read property")

    def test_the_words_steps_to_reproduce(self):
        assert has_repro_steps("Steps to reproduce: send a 6-tool schema and watch")

    def test_numbered_steps(self):
        assert has_repro_steps("1. call the tool\n2. pass 6 args\n3. it fails")


class TestAbsent:
    def test_a_bare_opinion(self):
        assert has_repro_steps("gemini is great for bulk summarisation, very reliable") is False

    def test_praise_with_a_number_but_no_repro(self):
        # has_numbers is a different signal; a figure alone is not a repro step.
        assert has_repro_steps("it handled 50k tokens fine and stayed accurate") is False
