"""The compare page links each shared axis to its board page, and only where one exists.

The ranking already lives on the board — every Jobs and Capabilities page is
ordered by the rule in `contract/board_ordering.yaml` — so compare does not rank
anything a second time. It links instead: the axis name opens that axis's board
page, and each cell opens that model's reports there, which is where the quotes
already are. Compare stays counts, the board stays order, one click apart.

⚠ A LINK IS ONLY HONEST IF THE PAGE RENDERS, AND IT DOES NOT ALWAYS.
  Measured 2026-09-28 over the 15 models with the most entries: of 572 (model,
  axis) pairs `evidence_for_model` returns, 4 have no board page at all.

  All four for one reason: the board and this reader name the same axis
  differently.

    metric/exploitgym, capability/overthinking   rows merged both ways, so the
        two readers land on opposite ends of the cycle
    metric/exploit-bench                         a spelling fold: the board lists
        it as `exploitbench`, the row keeps `exploit-bench`

  (An earlier draft blamed a metric validity gate for `exploit-bench`. The
  gates are applied to both reads; the row is not withheld, it is renamed.)

  So the backend asks `board_sections` - the function that IS what the board
  renders - and a path is None exactly where the board has no page. A second
  implementation of "is this on the board" would drift the next time a gate
  changed.

⚠ AND THIS FILE EXISTS PARTLY BECAUSE OF A BUG IN WRITING IT. The helper that
  builds the paths was inserted between `@app.get("/compare")` and
  `compare_page`, so the ROUTE decorated the helper. Calling `compare_page()`
  from Python worked perfectly and timed at 4.1s; the HTTP route would have
  served a function expecting three positional arguments it never gets. Only
  the contract gate noticed, because the route suddenly "returned a Name".
  The first test below checks the route, not the function.
"""

from __future__ import annotations

import ast
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "judge" / "app.py"
PAGE = ROOT / "web" / "src" / "routes" / "Compare.jsx"


def _tree() -> ast.Module:
    return ast.parse(APP.read_text(encoding="utf-8"))


def _decorated_by(route: str) -> list[str]:
    """Every function the `@app.get(route)` decorator is actually attached to."""
    out = []
    for node in _tree().body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            if (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)
                    and dec.func.attr == "get" and dec.args
                    and isinstance(dec.args[0], ast.Constant)
                    and dec.args[0].value == route):
                out.append(node.name)
    return out


def _jsx() -> str:
    text = PAGE.read_text(encoding="utf-8")
    text = re.sub(r"/\*[\s\S]*?\*/", " ", text)
    return re.sub(r"//[^\n]*", " ", text)


class TestTheRouteServesTheRightFunction:
    def test_compare_is_decorated_on_compare_page(self):
        """⚠ THE BUG THIS FILE WAS WRITTEN AFTER. A helper inserted between a
        decorator and its function takes the decorator, and nothing about the
        helper - or about calling the real function directly - says so."""
        assert _decorated_by("/compare") == ["compare_page"], (
            f"@app.get('/compare') decorates {_decorated_by('/compare')}. A "
            f"helper placed between the decorator and compare_page captures "
            f"the route."
        )

    def test_the_helper_is_not_a_route(self):
        for node in _tree().body:
            if isinstance(node, ast.FunctionDef) and node.name == "_with_board_paths":
                assert not node.decorator_list, (
                    "_with_board_paths is decorated; it is a helper, not an endpoint"
                )
                return
        raise AssertionError("_with_board_paths is gone")


class TestAPathExistsOnlyWhereTheBoardHasThePage:
    def test_membership_comes_from_the_boards_own_function(self):
        src = ast.unparse(next(
            n for n in _tree().body
            if isinstance(n, ast.FunctionDef) and n.name == "compare_page"))
        assert "board_sections(conn)" in src, (
            "compare no longer asks board_sections which pages exist, so a link "
            "can point at an axis the board merged away or withheld"
        )

    def test_a_missing_page_is_none_not_a_guessed_path(self):
        src = ast.unparse(next(
            n for n in _tree().body
            if isinstance(n, ast.FunctionDef) and n.name == "_with_board_paths"))
        assert "if models is not None else None" in src, (
            "board_path is built without checking the board has the axis"
        )
        assert "if models is not None and key else None" in src, (
            "board_model_path is built without checking the model is on that page"
        )

    def test_the_model_key_is_the_boards_not_ours(self):
        """They are the same string on most rows and not all - the board's own
        route comment records `model_version.id` holding a canonical id for 166
        of 1,249 rows - so the key the board routes on is read off the board."""
        src = APP.read_text(encoding="utf-8")
        assert 'r.get("model_key")' in src

    def test_the_shared_evidence_is_copied_not_mutated(self):
        """`evidence_for_model` also feeds the model page; writing link fields
        into its dicts in place would put them on a payload nothing there reads."""
        src = ast.unparse(next(
            n for n in _tree().body
            if isinstance(n, ast.FunctionDef) and n.name == "_with_board_paths"))
        assert "**item" in src


class TestThePageNeverRendersADeadLink:
    def test_the_axis_name_links_only_when_a_path_exists(self):
        jsx = _jsx()
        assert "axisPath\n" in jsx or "axisPath ?" in jsx.replace("\n", " ").replace("  ", " ") \
            or re.search(r"\{axisPath\s*\?", jsx), (
            "the axis name is no longer conditional on a board path"
        )
        assert "to={`/board/${axisPath}`}" in jsx

    def test_the_cell_links_only_when_a_path_exists(self):
        jsx = _jsx()
        assert re.search(r"\{it\.board_model_path\s*\?", jsx), (
            "the cell link is no longer conditional; a cell for a model the board "
            "does not list on this axis would open an empty page"
        )
        assert "to={`/board/${it.board_model_path}`}" in jsx

    def test_the_ranking_is_not_reproduced_here(self):
        """⚠ THE DESIGN DECISION, pinned. The board already orders these pages;
        a position shown on compare would be a second copy that can disagree."""
        jsx = _jsx()
        assert "wilson" not in jsx.lower()
        assert not re.search(r"#\$\{[^}]*\}\s*of", jsx), (
            "a '#N of M' position is rendered on compare; the ranking lives on "
            "the board and is linked, not copied"
        )
