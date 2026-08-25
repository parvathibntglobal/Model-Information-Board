"""The wiring that makes `judge extract` store anything — checked without a DB.

The pipeline verified quotes and stored nothing for weeks because one piece was
disconnected: the extractor proposes a SURFACE, and nothing mapped it to a model.
These tests guard the CONNECTION, not the behaviour — behaviour needs a database
(and is covered in `test_pipeline_db.py`), but the connection is where the bug
lived, so a no-DB test that goes red the moment it is dropped is worth having.

No database, local or shared: imports, a source check, and an in-memory
population.
"""

from __future__ import annotations

import inspect

from collect.surface_resolver import RegistrySurfaceResolver
from collect.triage.entity import build_population
from judge.pipeline import SurfaceResolver


class TestTheResolverSatisfiesWhatTheLaneNames:
    """`collect/` provides what `judge/` named, without either importing the other."""

    def _resolver(self):
        population = build_population([("anthropic/claude-sonnet-4", "Claude Sonnet 4")])
        return RegistrySurfaceResolver(population, {"anthropic/claude-sonnet-4": "mv_x"})

    def test_it_is_a_SurfaceResolver(self):
        assert isinstance(self._resolver(), SurfaceResolver)

    def test_a_written_surface_resolves_to_a_model_id(self):
        assert self._resolver()("sonnet 4") == "mv_x"

    def test_an_unknown_surface_returns_none_not_a_guess(self):
        assert self._resolver()("some model we do not carry") is None


class TestTheCliForwardsTheResolver:
    """`run()` gets `resolve_surface`, and it comes from the composition root."""

    def test_extract_from_export_forwards_resolve_surface_to_run_all(self):
        from judge import cli

        src = inspect.getsource(cli._extract_from_export)
        assert "resolve_surface" in inspect.signature(cli._extract_from_export).parameters
        assert "resolve_surface=resolve_surface" in src, (
            "the resolver must reach run_all, or every claim is skipped again"
        )

    def test_cmd_extract_accepts_a_resolver_factory(self):
        from judge import cli

        assert "resolver_factory" in inspect.signature(cli._cmd_extract).parameters


class TestTheCompositionRootWiresBothLanes:
    """`scripts/run_extraction.py` is the one place both lanes meet."""

    def _source(self) -> str:
        from pathlib import Path

        return Path("scripts/run_extraction.py").read_text(encoding="utf-8")

    def test_it_supplies_the_registry_resolver_as_the_factory(self):
        src = self._source()
        assert "RegistrySurfaceResolver.from_connection" in src
        assert "resolver_factory=" in src

    def test_it_imports_both_lanes_which_neither_lane_may_do(self):
        src = self._source()
        assert "from collect.surface_resolver import" in src
        assert "from judge.cli import" in src
