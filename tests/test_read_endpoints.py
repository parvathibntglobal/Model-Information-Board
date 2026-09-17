"""The board's read surface — the handover to whoever builds the UI.

Five page modules existed with no endpoint and no caller, so nothing outside
this repository could reach one of them. These are the assertions that a
frontend has something to call, and that what it gets back cannot be rendered
into a lie by dropping a field.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from judge.app import app

client = TestClient(app, raise_server_exceptions=False)

PAGES = (
    "/models/mv1",
    "/models/google/gemini-2.5-flash",  # every real id contains a slash
    "/capabilities/summarization.fidelity",
    "/filtered",
    "/coverage",
    "/changelog",
)


class TestEveryPageIsReachable:
    def test_all_five_have_a_route(self):
        paths = {getattr(r, "path", "") for r in app.routes}
        for expected in (
            "/models/{model_version_id:path}",
            "/capabilities/{capability_key}",
            "/filtered",
            "/coverage",
            "/changelog",
        ):
            assert expected in paths, f"{expected} has no route; the UI cannot fetch it"


class TestNoDatabaseIsNotAnEmptyBoard:
    """503, not 500 and not an empty 200.

    A page that cannot be READ differs from a page with nothing ON it, and
    that is the same distinction every one of these modules is built around.
    Returning an empty 200 here would make an outage indistinguishable from a
    board that knows nothing - the exact confusion rule 4 exists to prevent,
    at the transport layer.
    """

    @pytest.fixture(autouse=True)
    def _no_database(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)

    @pytest.mark.parametrize("path", PAGES)
    def test_each_page_returns_503_rather_than_an_empty_page(self, path):
        response = client.get(path)

        assert response.status_code == 503, path
        assert "not the same as a board with nothing on it" in response.json()["detail"]

    @pytest.mark.parametrize("path", PAGES)
    def test_no_page_returns_a_misleading_200(self, path):
        assert client.get(path).status_code != 200


class TestTheCaveatCannotBeDroppedByAccident:
    """Every response carries its caveat in the SAME object.

    Not an API style choice. This board's whole claim is that it distinguishes
    "nobody looked" from "nobody complained", and a client that fetches a page
    and renders only the findings has removed the distinction. A separate call
    for the caveat would make dropping it the easy path.
    """

    def test_the_model_response_shape_carries_state_and_headline_per_capability(self):
        import inspect

        from judge.app import model_page

        source = inspect.getsource(model_page)
        for field in ('"state"', '"headline"', '"needs_positive_consensus"'):
            assert field in source, f"the model page omits {field}"

    def test_quote_ids_travel_beside_the_phrase_not_in_a_separate_map(self):
        """FR-26. A phrase whose evidence lives in a different object is a
        phrase somebody will render without it."""
        import inspect

        from judge.app import model_page

        source = inspect.getsource(model_page)
        conditions = source.split('"conditions"')[1].split("for s in c.slices")[0]
        assert '"quote_ids"' in conditions
        assert '"phrase"' in conditions

    def test_unbound_phrases_are_surfaced_to_the_client(self):
        """So a client can refuse to render rather than discover it visually."""
        import inspect

        from judge.app import model_page

        assert '"unbound_phrases"' in inspect.getsource(model_page)

    def test_every_page_returns_a_summary(self):
        import inspect

        from judge.app import capability_page, changelog_page, coverage_page, filtered_page

        for fn in (capability_page, changelog_page, coverage_page, filtered_page):
            assert '"summary"' in inspect.getsource(fn), fn.__name__


class TestTheReadSurfaceOnlyReads:
    def test_no_endpoint_writes(self):
        import inspect

        from judge.app import (
            capability_page,
            changelog_page,
            coverage_page,
            filtered_page,
            model_page,
        )

        for fn in (model_page, capability_page, filtered_page, coverage_page, changelog_page):
            source = inspect.getsource(fn)
            for write in ("INSERT", "UPDATE", "DELETE", ".commit()"):
                assert write not in source, f"{fn.__name__} contains {write}"

    def test_the_dsn_is_not_defaulted_to_localhost(self):
        """A default that quietly reaches localhost is how a read surface ends
        up serving a database nobody meant to expose."""
        import inspect
        import re

        import judge.app as app_module

        # EVERY FUNCTION ON THE WAY TO A SOCKET, not just the one the call sites
        # name. `_conn` was both the context manager and the dialler until the
        # connection pool split them on 2026-09-17; asserting on `_conn` alone
        # then passed while reading nothing, because the DSN had moved to
        # `_open_connection` and this test could no longer see it.
        readers = (app_module._conn, app_module._open_connection,
                   app_module._ConnectionPool.take)
        # COMMENTS AND DOCSTRINGS STRIPPED FIRST. The first version asserted
        # `"localhost" not in source` and failed on this function's own comment
        # explaining why there is no localhost default - the third time in one
        # session I have written a substring check that caught my own prose,
        # after "complete" in "completeness" and "commit" in "never commits".
        bodies = {
            fn.__name__: re.sub(
                r"#.*", "", re.sub(r'"""[\s\S]*?"""', "", inspect.getsource(fn))
            )
            for fn in readers
        }
        for name, code in bodies.items():
            assert "localhost" not in code, f"{name} can reach localhost"
        # The DSN is read in exactly one place and it comes from the environment.
        assert 'os.getenv("DATABASE_URL")' in bodies["_open_connection"]
        # ⚠ AND THE POOL TAKES IT AS AN ARGUMENT RATHER THAN READING ITS OWN. A
        #   pool that resolved the DSN separately could hand back a connection to
        #   a different database than the caller asked for, and nothing would say
        #   so - see `test_changing_the_dsn_empties_the_pool`.
        assert "getenv" not in bodies["take"]


class TestAnUnknownCapabilityIs404:
    def test_it_is_404_without_needing_a_database(self, monkeypatch):
        """An unknown key would read "nobody has reported on this", which is
        indistinguishable from a real capability nobody discussed.

        Checked before connecting, so a wrong key answers 404 rather than 503
        - telling the caller the board is down when their key is simply wrong
        is the wrong repair pointed at the wrong person.
        """
        monkeypatch.delenv("DATABASE_URL", raising=False)
        response = client.get("/capabilities/not.a.capability")

        assert response.status_code == 404
        assert "not a tracked capability" in response.json()["detail"]


class TestAModelIdContainsASlash:
    """Found by the first check against a real database, not by any test.

    Every model id is `vendor/name` - google/gemini-2.5-flash,
    anthropic/claude-opus-5. The route was `{model_version_id}`, which matches
    only up to the first separator, so EVERY REAL MODEL PAGE 404ed while the
    suite passed on `mv1`.

    The tests used a fixture id with no slash, so the whole endpoint was
    verified against the one shape production never produces. A variable the
    test supplies, again, and this time it was the URL.
    """

    def test_a_vendor_prefixed_id_routes(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        # 503 rather than 404: it reached the handler and failed on the
        # database, which is the proof that routing worked.
        assert client.get("/models/google/gemini-2.5-flash").status_code == 503

    def test_the_route_declares_a_path_parameter(self):
        paths = {getattr(r, "path", "") for r in app.routes}
        assert "/models/{model_version_id:path}" in paths


class TestAnUnknownModelIdIsRefusedRatherThanRendered:
    """FR-24 inverted, and the one place this API broke rule 4.

    ⚠ ADDED FROM THE OTHER LANE, on instruction, alongside the fix in
    `judge/app.py`. Flagged rather than quiet: see
    `docs/proposals/model-page-id-resolution.md`.

    `cell.model_version_id` is the internal `mv_…` id, so a canonical id matched
    no row — and nothing checked, so it rendered instead of refusing. Every one
    of these returned 200 with an identical page against a live registry:

        /models/mv_568e0eb3a95b5113          the real key
        /models/anthropic/claude-opus-5      what every caller holds
        /models/total-nonsense-not-a-model   not a model
        /models/                             the empty string

    all four saying *"0 of 12 tracked capabilities have any reports at all"*. A
    typo and a real model were the same page — which is the empty-page rule
    working correctly for a real model and fabricating for one that does not
    exist.

    These assert the SHAPE without a database, which is all that can be asserted
    here: the lookup needs one, so a no-database run answers 503 before it can
    404. The 404 itself is exercised in `tests/test_read_endpoints_db.py`'s
    absence by the live check recorded in the proposal — stated plainly rather
    than left to look like coverage it is not.
    """

    def test_the_handler_validates_before_building_a_page(self):
        """The lookup is the first thing after the connection.

        Asserted by AST rather than by response, because the ordering is the
        property: a page built before validation is a page that can be returned
        for an id that does not exist, which is exactly what happened.
        """
        import ast
        import inspect

        from judge.app import model_page

        tree = ast.parse(inspect.getsource(model_page).strip())

        # BY LINE NUMBER, NOT BY WALK ORDER. The first version of this asserted
        # `names.index("execute") < names.index("build")` over `ast.walk`, which
        # is BREADTH-FIRST: `conn.execute(...).fetchone()` visits `fetchone`
        # before its child `execute`, so the check compared traversal depth and
        # called it source order. It failed on correct code — habit 11 in a test
        # written about habit 11, which is the reason this comment exists rather
        # than a silent fix.
        at = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                at.setdefault(node.func.attr, node.lineno)

        assert "execute" in at, "no lookup: the id is not validated"
        assert "fetchone" in at
        assert at["execute"] < at["build"], (
            f"the page is built (line {at['build']}) before the id is validated "
            f"(line {at['execute']})"
        )

    def test_it_raises_a_404_and_not_an_empty_page(self):
        """The refusal exists in the source and names both accepted shapes."""
        import inspect

        from judge.app import model_page

        source = inspect.getsource(model_page)
        assert "status_code=404" in source
        assert "indistinguishable" in source, (
            "the refusal has to say WHY, the way /capabilities/{key} does — "
            "otherwise the next reader deletes it as defensive"
        )

    def test_both_id_shapes_are_accepted(self):
        """Accepting only one would move the defect rather than close it."""
        import inspect

        from judge.app import model_page

        source = inspect.getsource(model_page)
        assert "WHERE id = %s OR canonical_id = %s" in source
