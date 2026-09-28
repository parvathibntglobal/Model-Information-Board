"""The queue behind a removed panel does not keep filling.

`capability_candidate` fed the Capability candidates admin panel. The panel came
off on 2026-09-24, when capabilities stopped getting a review surface the other
board sections do not have. The queue kept filling for four more days.

    capability_candidate     223 rows, 0 EVER RULED ON       staging, 2026-09-24
    of e5.5's 53 keys         24 already exist as a board slug
                                 metric.osworld          beside  osworld
                                 capability.computer_use beside  computer-use

⚠ A WRITER OUTLIVING ITS READER IS NOT VISIBLE FROM EITHER END. The panel's
  removal looks complete — the component is gone, the client functions are gone,
  nothing renders. The writer looks correct — it stores what the extractor
  proposed, idempotently, exactly as designed. Only the pair is wrong, and no
  test that reads one file can see it.

⚠ THE ROWS ARE NOT DELETED AND THIS FILE DOES NOT ASK FOR THAT. 17 of the 28
  keys with no matching board slug came from a document that produced NO board
  entry, so those observations exist in exactly one place:

      safety.instruction-manipulation     alignment.concealment
      safety.unauthorized-data-exfiltration   code.bug_detection

  Stopping a writer and deleting a table's contents are different acts with
  different risks, and only the first was asked for.

WHAT THIS DOES NOT COVER. The extractor is still ASKED for
`proposed_capabilities` — the field is in the schema and the prompt — so the
tokens are still spent and the answer is now discarded rather than filed.
Removing the field changes what the model is asked to produce, which is a
prompt change and a provenance change. It stays on #434 and is deliberately
not asserted here: a test that failed until somebody edited the prompt would be
this file taking a decision that is not its to take.
"""

from __future__ import annotations

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FETCH = ROOT / "scripts" / "fetch_model.py"
STORE = ROOT / "judge" / "store" / "capability_candidates.py"


def _calls_named(path: pathlib.Path, name: str) -> list[int]:
    """Line numbers where `name(...)` is CALLED in `path`.

    ⚠ PARSED, NOT GREPPED. `fetch_model.py` now explains at length why it does
      not store proposals, naming the function in the prose — so a substring
      search finds the removal's own comment and reports the writer as still
      present. That is the mention-versus-use trap, which this repository has
      walked into sixteen times.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name) and fn.id == name:
                out.append(node.lineno)
            elif isinstance(fn, ast.Attribute) and fn.attr == name:
                out.append(node.lineno)
    return sorted(out)


class TestTheFetchNoLongerFilesProposals:
    def test_the_fetch_does_not_store_capability_proposals(self):
        assert _calls_named(FETCH, "store_proposals") == [], (
            "scripts/fetch_model.py is filing capability proposals again. The "
            "panel that ruled on them was removed on 2026-09-24 (#434); a row "
            "written now has no reader and never will."
        )

    def test_the_import_went_with_the_call(self):
        """A dangling import is how a removed call comes back: the next reader
        sees the symbol already imported and assumes it is used."""
        tree = ast.parse(FETCH.read_text(encoding="utf-8"))
        imported = [
            n.lineno for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom)
            and (n.module or "").endswith("capability_candidates")
        ]
        assert imported == [], (
            f"scripts/fetch_model.py still imports from capability_candidates "
            f"at line(s) {imported}, though nothing calls it"
        )


class TestTheStageStillReports:
    """⚠ RULE 4: A CAUSED ABSENCE SAYS IT WAS CAUSED. Deleting the E5b stage
    line would have been the tidier diff and the worse outcome — a stage that
    vanishes from a run log reads as a stage that found nothing, which is the
    reassuring one of the two available readings."""

    def test_e5b_is_still_emitted(self):
        source = FETCH.read_text(encoding="utf-8")
        assert '"E5b"' in source, "the E5b stage line was removed with the writer"

    def test_the_stage_says_the_proposals_were_not_stored(self):
        """The count alone would read as a count of what was filed."""
        source = FETCH.read_text(encoding="utf-8")
        assert "NOT STORED" in source


class TestTheRowsAreStillReachable:
    """The reader stays. 223 rows nobody can query is a worse state than 223
    rows nobody has ruled on, and 17 of those observations are recorded
    nowhere else."""

    def test_the_store_can_still_read_and_rule(self):
        source = STORE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        defined = {
            n.name for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for name in ("list_candidates", "rule_candidates"):
            assert name in defined, f"{name} is gone; the 223 rows are unreachable"

    def test_nothing_in_this_change_deletes_rows(self):
        """`delete_candidates` exists for an admin acting deliberately. What
        matters is that no automated path calls it — a cleanup that ran on a
        fetch would take the 17 unique observations with it."""
        assert _calls_named(FETCH, "delete_candidates") == []
