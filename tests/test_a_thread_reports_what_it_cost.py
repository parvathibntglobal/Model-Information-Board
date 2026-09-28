"""Each thread's line carries that thread's own tokens and cost (#403 follow-up).

MEASURED ON A REAL RUN. ElevenLabs v3, 2026-09-23,
`var/fetch/mv_9a53a616c98d9f6b-54be7210.jsonl`. Every one of the twenty thread
lines read:

    tokens_in=0  tokens_out=0  usd=0.0

while the closing box was right:

    tokens_in 407396 · tokens_out 81238 · cost_usd 0.037854

⚠ THE CAUSE, AND IT IS NOT THE ORDERING. `on_result` took `budget.spent_usd`
  before the call and again after it and reported the difference - and
  `budget.charge()` sits THIRTY LINES BELOW the `on_result` call, so nothing
  had been added yet and the difference was exactly zero every time. The run
  total was right because it is read after the whole loop, by which point
  every charge has landed.

  Moving `on_result` below `charge` would have fixed this instance and left
  the trap armed: the real defect is asking a MUTABLE ACCUMULATOR a question
  whose answer depends on when you ask it. `result.extraction` already carries
  this thread's own totals - retries included, which is exactly what `charge`
  is handed - so the figures are now read off the thread and there is no order
  to get wrong.

⚠ AND IT IS RULE 6, NOT A COSMETIC ONE. `$0.000000` beside a thread is a
  definite statement that the thread was free. Nineteen of them under a total
  of $0.037854 says the money came from nowhere, and a reader looking for the
  expensive thread cannot find it.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "judge" / "pipeline.py"


def on_result_block() -> str:
    src = PIPELINE.read_text(encoding="utf-8")
    start = src.index("if on_result is not None:")
    return src[start:src.index("results.append(result)", start)]


class TestTheFiguresComeFromTheThread:
    def test_the_budget_baseline_is_gone(self):
        """⚠ MENTION VERSUS USE, EIGHTH TIME. The comment above the call
        explains what `before_usd` was and why it was wrong, so a plain search
        of the file finds the explanation and fails. Only code lines count."""
        lines = [
            ln for ln in PIPELINE.read_text(encoding="utf-8").splitlines()
            if not ln.strip().startswith("#")
        ]
        code = "\n".join(lines)
        for name in ("before_in", "before_out", "before_usd"):
            assert name not in code, f"{name} is back; the delta is zero again"

    def test_the_tokens_are_read_off_the_extraction(self):
        block = on_result_block()
        assert "result.extraction.input_tokens" in block
        assert "result.extraction.output_tokens" in block

    def test_no_figure_is_differenced_off_the_budget(self):
        """The shape that produced twenty zeroes. Any subtraction against a
        budget attribute here is the same bug wearing different names."""
        block = on_result_block()
        assert not re.search(r"budget\.\w+\s*-", block), (
            "a per-thread figure is being differenced off the accumulator again"
        )

    def test_the_cost_is_computed_with_a_pure_call(self):
        """`cost_of` is arithmetic over the pricing table and moves nothing, so
        it cannot be sensitive to when it is called."""
        block = on_result_block()
        assert "budget.cost_of(" in block
        assert "budget.charge(" not in block


class TestWithoutABudgetTheCostIsUnknownRatherThanZero:
    def test_it_passes_none_and_not_a_number(self):
        """Rule 6. There is no pricing table without a Budget, so the cost is
        not known - and `$0.00` is a definite statement that the call was
        free."""
        block = on_result_block()
        assert "if budget is not None else None" in block

    def test_the_tokens_survive_without_a_budget(self):
        """The token counts come from the response, not from the pricing, so a
        run with no Budget still reports them. Only the dollars are unknown."""
        block = on_result_block()
        tokens = block[block.index("tokens_in="):block.index("usd=")]
        assert "budget" not in tokens


class TestCostOfIsSafeToCallHere:
    def test_it_does_not_mutate_the_budget(self):
        """The whole fix rests on this: if `cost_of` charged, calling it per
        thread would double every bill."""
        from judge.extract.budget import Budget

        src = pathlib.Path(Budget.__module__.replace(".", "/") + ".py")
        text = (ROOT / src).read_text(encoding="utf-8")
        body = text[text.index("def cost_of("):]
        body = body[:body.index("\n    def ", 1)]
        assert "self." not in body.replace("self.pricing", ""), (
            "cost_of touches state other than the pricing table"
        )

    def test_it_agrees_with_what_charge_would_add(self):
        """The per-thread figures have to sum to the run total, or the closing
        box and the lines above it tell two different stories."""
        from judge.extract.budget import Budget, Pricing

        budget = Budget(limit_usd=None, pricing=Pricing(price_in=1e-6, price_out=2e-6))
        per_thread = [budget.cost_of(1000, 500) for _ in range(3)]

        class _C:
            raw_arguments = ""
            model = "x"

            def __init__(self, i, o):
                self.input_tokens, self.output_tokens = i, o

        for _ in range(3):
            budget.charge(_C(1000, 500))
        assert round(sum(per_thread), 9) == round(budget.spent_usd, 9)
