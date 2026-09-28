"""One API call, one ledger row.

⚠ THE LEDGER COUNTED ROWS, AND ROWS WERE NOT CALLS. Two places recorded every
  extraction: `judge/extract/client.py` beside the response, and
  `judge/pipeline.py` again once the thread had stored. One call, two rows, two
  dollar figures added to the same total.

  Measured 2026-09-28 over the shared ledger:

      rows                     3,288
      distinct calls           2,131
      DUPLICATED PAIRS         1,139       median 2.3s apart, p90 7.4s
      dollars as recorded     $7.1101
      dollars once collapsed  $5.1152
      spent on the key ever   $4.1570      <- the provider's own figure

  It is the expensive direction twice over. The admin page read a total higher
  than the key had ever been charged, and a cap enforced on that total stops a
  run that still had budget.

WHY NOT DEDUPLICATE IN `Call.id`. Because the id hashes the timestamp on
purpose, and the reason is written into it: *"two machines can make the same
call in the same microsecond with the same tokens; that is two real calls
costing two real amounts, and hashing content alone would record one of them
and lose the other's money."* That is right, and it means the two writes
milliseconds apart are two different ids BY DESIGN. A hash that collapsed them
would also collapse the real collision it was built for. The fix is one writer.

WHY THE CLIENT AND NOT THE PIPELINE. Three things the pipeline cannot do:

  - it sees the provider's `usage`, which carries the billed cost (#381)
  - it fires on truncated and abandoned calls, which are billed and never
    reach the pipeline's line - two of them on 2026-09-14, ~30,000 generated
    tokens each, invisible in our own figures
  - it covers every caller of the extractor, not only runs through `pipeline`

So these tests assert the pipeline does NOT write, which reads backwards until
you notice that "both write" is the state that costs money.
"""

from __future__ import annotations

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "judge" / "pipeline.py"
CLIENT = ROOT / "judge" / "extract" / "client.py"
ASK = ROOT / "judge" / "ask" / "spend.py"


def _record_calls(path: pathlib.Path) -> list[int]:
    """Line numbers of real `spend_ledger.record(...)` CALLS in `path`.

    ⚠ PARSED, NOT GREPPED, and that is the mention-versus-use trap this
      repository has walked into sixteen times. Both files below discuss
      `spend_ledger.record` at length in comments - one of them quotes the
      claim that justified the second writer - so a text search finds the
      writer that was removed and passes on the file that no longer has one.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Attribute) and fn.attr == "record":
            owner = fn.value
            if isinstance(owner, ast.Name) and owner.id == "spend_ledger":
                found.append(node.lineno)
    return sorted(found)


class TestExactlyOneWriterPerCall:
    def test_the_pipeline_does_not_write_a_second_row(self):
        """The 1,139 pairs, in one assertion."""
        assert _record_calls(PIPELINE) == [], (
            "judge/pipeline.py records the extraction call that "
            "judge/extract/client.py has already recorded. One call, two rows, "
            "and the dollar total is the sum of both."
        )

    def test_the_client_still_writes_one(self):
        """⚠ THE CONTROL. Without it, deleting BOTH writers passes the test
        above - and a ledger that records nothing is the one failure mode
        worse than double counting, because it reads as a quiet day."""
        assert len(_record_calls(CLIENT)) == 1, (
            "judge/extract/client.py must record each completion exactly once: "
            "it is the only place that sees the provider's usage, and the only "
            "one reached by a truncated call."
        )

    def test_the_ask_box_writes_its_own(self):
        """A different stage and a different call, so it is not a duplicate.
        Named here so that removing it reads as the deliberate act it would
        be - the $1/day cap is shared, and an unrecorded ask is spend the
        extractor is then allowed to make on top of."""
        assert len(_record_calls(ASK)) == 1


class TestThePipelineStillChargesTheBudget:
    """⚠ REMOVING THE LEDGER WRITE MUST NOT REMOVE THE CAP. `budget.charge()`
    is a different mechanism on the same line of defence - in-memory, per-run,
    what stops a single run overrunning $1 - and it lives a dozen lines above
    the row that was deleted. Deleting the wrong one is quiet: the run keeps
    working and stops respecting its ceiling."""

    def test_the_budget_is_still_charged_from_what_ran(self):
        tree = ast.parse(PIPELINE.read_text(encoding="utf-8"))
        charges = [
            n.lineno for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "charge"
        ]
        assert charges, "judge/pipeline.py no longer charges the run's budget"
