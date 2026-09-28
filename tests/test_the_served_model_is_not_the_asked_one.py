"""What the provider served and what we asked for are two facts, kept apart.

⚠ ONE LINE MADE ONE COLUMN MEAN TWO THINGS.

      model_name = model_name or self.model

  When the stream named a model, the ledger recorded the provider's answer.
  When it named none, the same column quietly recorded the id WE SENT, and
  nothing downstream could tell the two apart.

  @anoojntglobal-sudo measured what that costs (#481 → #381, 2026-09-28): all
  3,077 alias rows in the shared ledger read `deepseek-v4-flash` and not one
  reads `-0423`, so the column is echoing the id we sent rather than the build
  that ran. A `model_asked` column beside it — which is what #481 originally
  proposed — would have matched on every row by construction and measured
  nothing at all.

⚠ AND DROPPING THE FALLBACK ALONE WOULD HAVE BEEN EXPENSIVE IN THE DIRECTION
  THAT MATTERS. `record()` prices by looking the model up in `MODEL_PRICING`;
  an empty name has no rate; an unpriced row records `usd: 0.0`; and
  `spent_today()` reads those rows to enforce the $1/day cap. So every call the
  provider declined to name would have cost the cap nothing, and a run could
  quietly overspend — a silent failure, on real money, introduced by a fix for
  an honesty defect.

  The price is therefore passed explicitly, computed from the id we ASKED for.
  That is not a workaround: OpenRouter bills the alias we sent at the alias's
  rate whichever build it routes to, so the id on the invoice is the asked one.
  What served the call is provenance, and is recorded as provenance or not at
  all.

WHAT THIS FILE DOES NOT COVER. Carrying `generation_id` and `provider` onto the
ledger row is the other half, and it is @anoojntglobal-sudo's in #381 — one
schema change on a shared table rather than two. Until a generation is looked
up, which build served any of our calls remains unknown.
"""

from __future__ import annotations

import ast
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLIENT = ROOT / "judge" / "extract" / "client.py"
NAMES = ROOT / "web" / "src" / "modelNames.js"


def _source() -> str:
    return CLIENT.read_text(encoding="utf-8")


def _code() -> str:
    """The module with comments and docstrings stripped.

    ⚠ BOTH ARE REMOVED, NOT JUST COMMENTS. The removed fallback is QUOTED in
      the comment that replaced it and again in the corrected docstring, so a
      search over the raw file finds the defect's own epitaph and reports it as
      still present. That is the mention-versus-use trap, and this repository
      has walked into it sixteen times.
    """
    tree = ast.parse(_source())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef,
                             ast.AsyncFunctionDef, ast.ClassDef)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                node.body.pop(0)
    return ast.unparse(tree)


class TestTheFallbackIsGone:
    def test_the_asked_id_is_not_copied_into_the_served_name(self):
        code = _code()
        assert "model_name = model_name or self.model" not in code, (
            "the fallback is back: a call the provider did not name is being "
            "recorded under the id we asked for, and the two cases become "
            "indistinguishable again"
        )
        assert re.search(r"\bserved = model_name\b", code)
        assert re.search(r"\basked = self\.model\b", code)

    def test_the_ledger_records_the_served_name_or_nothing(self):
        code = _code()
        assert re.search(r"model=served or ''", code), (
            "the ledger row no longer records the provider's own answer"
        )

    def test_the_completion_carries_the_asked_id(self):
        """Its own docstring has always said so — "IT IS STILL WHAT WE ASKED
        FOR, NOT WHAT RAN" — while the value was the provider's on any call
        that named one. `Budget.spend_by_model` is keyed on this."""
        assert re.search(r"model=asked", _code())


class TestTheCapStillCounts:
    """⚠ THE LOAD-BEARING TEST. The honesty fix must not disarm the budget."""

    def test_the_price_is_passed_explicitly(self):
        code = _code()
        assert "pricing=pricing_for(asked)" in code, (
            "the ledger row is no longer priced from the asked id. An unnamed "
            "model has no rate, an unpriced row records $0.00, and "
            "`spent_today()` enforces the $1/day cap from those rows — so the "
            "call would cost the cap nothing and a run could overspend."
        )

    def test_the_import_is_local(self):
        """`judge.extract.budget` imports `Completion` from this module, so a
        top-level import closes the cycle. `spend_ledger.record` takes the
        same precaution."""
        tree = ast.parse(_source())
        top = {
            n.module for n in tree.body
            if isinstance(n, ast.ImportFrom) and n.module
        }
        assert "judge.extract.budget" not in top, (
            "budget is imported at module level; it imports Completion from "
            "here, so this is an import cycle"
        )
        assert "from judge.extract.budget import pricing_for" in _source()


class TestTheUnsupportedPinClaimIsCorrected:
    """⚠ QUOTED AS SETTLED IN AT LEAST TWO DECISIONS — CLAUDE.md documents two
    — and never tested. It was false when written rather than made false
    later."""

    def test_the_pinning_claim_is_not_asserted(self):
        source = _source()
        for claim in (
            "it is pinned there, so the vendor cannot move it",
            "pinned, not floating, because",
        ):
            assert claim not in source, (
                f"{claim!r} is asserted again. Nothing tests it and the ledger "
                f"cannot settle it: the provider's actual build appears in "
                f"none of the 3,077 rows."
            )

    def test_it_says_what_is_actually_known(self):
        source = _source()
        assert "NO EVIDENCE" in source.upper()
        assert "-0731" in source and "we send neither" in source, (
            "the correction dropped the part that IS true — the two dated ids "
            "exist and we send neither"
        )

    def test_the_replacement_is_not_a_quieter_version_of_the_claim(self):
        """⚠ THE CONTROL. Softening "pinned" to "resolves to 0423" would pass
        the test above while making the same unevidenced claim."""
        code = _code()
        assert "0423" not in code, (
            "a build number is named in executable code again; which build "
            "serves the alias is not known to this repository"
        )


class TestTheEmptyNameRendersAsAReading:
    def test_the_page_does_not_render_a_blank(self):
        """⚠ A BLANK CELL BESIDE REAL NAMES READS AS A LAYOUT FAULT, and the
        obvious fix for a layout fault is to put the asked id back."""
        js = NAMES.read_text(encoding="utf-8")
        assert "provider named none" in js
        assert re.search(r"String\(id\)\.trim\(\) === ''", js), (
            "the empty case is no longer detected, so a row the provider did "
            "not name renders with no label at all"
        )
