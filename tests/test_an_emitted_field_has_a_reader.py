"""#275: a produced value nothing would notice going wrong.

The declaration half, ruled by @anoojntglobal-sudo on 2026-09-24. The API emits
fields; this asks whether anything reads them, and nothing about whether the
values are right.

⚠ IT IS DELIBERATELY NOT AN AGREEMENT CHECK, and the #274/#279 sequence is why.
  `board_entry.quote` is a copy of `claim.quote`. Both held a JSON payload slice
  for weeks:

      before the repair      JSON | JSON      divergence 0    both wrong
      board repaired         prose | JSON     divergence 45   page LOOKS fixed
      claim repaired         prose | prose    divergence 0    correct

  An agreement check is green on the first row and on the third. It is blind to
  exactly the state the check exists for, and it was green for weeks while the
  board served envelopes. Agreement between a copy and its source says nothing
  about whether either is right — so this tests the DECLARATION.

⚠ AN UNANALYSABLE ROUTE IS WAIVED AND NEVER FAILS THE BUILD:

      "A check that blocks on what it cannot understand gets disabled, and a
       disabled check is worse than a permissive one with a visible waiver
       list. The waiver list is the output that matters: it is the set of
       routes nobody can vouch for, written down."

  So the waived set is printed on every run, not only on failure.

⚠ AND IT OVER-COUNTS READERS, WHICH IS THE SAFE DIRECTION. A generic field name
  matches an access to a different field of the same name, and a field reached
  through a spread is invisible. So `no_consumer` is a FLOOR and `consumed` is
  not proof — this check's silence is weaker than its statements, and saying so
  is what stops the contract being read as an endorsement.

Measured 2026-09-24:

    routes analysed    30
    routes waived      14
    fields emitted    138
      with a consumer  87
      NO CONSUMER      51
"""

from __future__ import annotations

import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_api_fields as audit  # noqa: E402

CONTRACT = ROOT / "contract" / "api_fields.yaml"


@pytest.fixture(scope="module")
def discovered():
    return audit.discover()


@pytest.fixture(scope="module")
def declared():
    return yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))["fields"]


class TestTheContractMatchesWhatTheCodeDoes:
    def test_every_emitted_field_is_declared(self, discovered, declared):
        """⚠ ANALYSABLE AND UNDECLARED IS A FAILURE. A new field that nobody
        has said anything about is the exact thing this check is for: it is
        emitted, it may have no reader, and until it is in the contract the
        silence about it is indistinguishable from approval."""
        missing = sorted(set(discovered["fields"]) - set(declared))
        assert not missing, (
            f"{len(missing)} emitted field(s) are not in contract/api_fields.yaml: "
            f"{missing[:12]}. Run `python scripts/audit_api_fields.py` and add "
            f"them, with `reviewed: false` if nobody has looked yet."
        )

    def test_no_declaration_names_a_field_that_is_gone(self, discovered, declared):
        """The other direction. A contract row for a field the API stopped
        emitting is a statement about nothing, and it makes the reviewed count
        flatter us."""
        stale = sorted(set(declared) - set(discovered["fields"]))
        assert not stale, (
            f"contract/api_fields.yaml declares {len(stale)} field(s) the API no "
            f"longer emits: {stale[:12]}"
        )

    def test_the_discovered_state_matches_the_declared_one(self, discovered, declared):
        """The gate. A field losing its last reader is a red test rather than a
        quiet change — which is the whole of rule 9 at this layer."""
        drifted = []
        for name, row in sorted(discovered["fields"].items()):
            want = declared.get(name, {}).get("state")
            if want and want != row["state"]:
                drifted.append(
                    f"{name}: declared {want!r}, discovered {row['state']!r}"
                    + (f" (read by {row['read_by'][0]})" if row["read_by"] else "")
                )
        assert not drifted, (
            f"{len(drifted)} field(s) are not in the state they declare:\n  "
            + "\n  ".join(drifted)
        )

    def test_a_reviewed_no_consumer_row_says_why(self, declared):
        """⚠ REVIEWED IS THE WORD THAT NEEDS THE REASON, NOT `no_consumer`. A
        field with no reader is rule 9's defect; a field with no reader that
        somebody LOOKED AT and left is a decision, and a decision with no
        recorded reason is indistinguishable from an oversight six weeks
        later."""
        silent = sorted(
            name for name, row in declared.items()
            if row.get("reviewed") and row.get("state") == audit.NO_CONSUMER
            and not row.get("why")
        )
        assert not silent, (
            f"reviewed `no_consumer` rows with no `why`: {silent}"
        )


class TestTheWaiverListIsTheOutput:
    def test_an_unanalysable_route_does_not_fail_anything(self, discovered):
        """The ruling, as a test. If this ever becomes an assertion that the
        waived set is empty, the check starts blocking on what it cannot
        understand — and then it gets disabled."""
        assert discovered["routes_waived"] > 0, (
            "every route became analysable, which is good news — but check that "
            "the waiver path still exists before deleting this test"
        )
        # No assertion about the size. That is the point.

    def test_every_waived_route_carries_its_reason(self, discovered):
        """A waiver with no reason is a list of route names, and nobody can act
        on it. `returns Call rather than a dict literal` tells a reader what
        would have to change."""
        for route, why in discovered["waived"].items():
            assert why and why.strip(), f"{route} is waived with no reason"

    def test_the_waiver_list_is_printed_rather_than_only_counted(self, capsys):
        """⚠ A LIST NOBODY SEES GROWS. It prints on every run, not only when
        something fails, because the failure path is the one case where the
        waived routes are NOT the interesting part."""
        audit.main(argv=[])
        printed = capsys.readouterr().out
        assert "WAIVED ROUTES" in printed
        for route in audit.discover()["waived"]:
            assert route in printed

    def test_a_route_can_be_both_analysed_and_waived(self, discovered):
        """A handler with one dict-literal return and one `return _x(...)` has
        fields this can check AND a shape it cannot. Recording only the first
        would present partial coverage as complete."""
        both = set(discovered["waived"]) & {
            route for row in discovered["fields"].values() for route in row["routes"]
        }
        assert both, (
            "no route is both — if that is now true the population changed, but "
            "check the audit did not start dropping one of the two facts"
        )


class TestItReportsHowMuchOfItselfIsUnreviewed:
    def test_the_snapshot_share_is_visible(self, declared, capsys):
        """Rule 11 and the reason `column_states.yaml` prints the same line: a
        contract that is 100% `reviewed: false` and a contract nobody has to
        look at again render identically."""
        unreviewed = [n for n, r in declared.items() if not r.get("reviewed")]
        share = 100 * len(unreviewed) / max(len(declared), 1)
        with capsys.disabled():
            print(
                f"\napi fields: {len(declared)} emitted, "
                f"{len(declared) - len(unreviewed)} reviewed, "
                f"{len(unreviewed)} still a snapshot ({share:.0f}% undeclared)"
            )
        assert declared, "the contract is empty"


class TestTheDetectorItself:
    def test_a_field_named_only_in_a_comment_is_not_a_reader(self):
        """⚠ THE TRAP THIS REPOSITORY KEEPS FALLING INTO, twelve times and
        counting. `_code_mask` is reused from the column audit rather than
        reimplemented, because two implementations of "is this an access or
        just the word" drift and both look right in isolation."""
        masked = audit._code_mask("// row.reach is not a read\nconst x = 1\n")
        text = "// row.reach is not a read\nconst x = 1\n"
        code = "".join(c if masked[i] else " " for i, c in enumerate(text))
        assert "reach" not in code

    def test_a_real_access_survives_the_mask(self):
        text = "const n = row.reach\n"
        masked = audit._code_mask(text)
        code = "".join(c if masked[i] else " " for i, c in enumerate(text))
        assert "row.reach" in code
