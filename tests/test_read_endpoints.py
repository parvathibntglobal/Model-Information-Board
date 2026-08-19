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

        source = inspect.getsource(app_module._conn)
        # COMMENTS AND DOCSTRINGS STRIPPED FIRST. The first version asserted
        # `"localhost" not in source` and failed on this function's own comment
        # explaining why there is no localhost default - the third time in one
        # session I have written a substring check that caught my own prose,
        # after "complete" in "completeness" and "commit" in "never commits".
        code = re.sub(r"#.*", "", re.sub(r'"""[\s\S]*?"""', "", source))
        assert "localhost" not in code
        assert 'os.getenv("DATABASE_URL")' in code


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
