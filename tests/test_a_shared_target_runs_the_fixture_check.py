"""A shared database gets the fixture check whatever ENVIRONMENT says.

`judge/writeguard.check()` refuses one pairing, ENVIRONMENT=development against a
remote database, and returns early on every other ENVIRONMENT. Both write
scripts read that early return as if a fixture check had run:
`fetch_model.py`'s seeded-model check and `run_extraction_batched.py`'s
fixture-exposure check ran ONLY under `--development-write`. So a container on
ENVIRONMENT=production wrote claims to the shared database with no fixture check
at all, and six container hostnames did, 2026-09-14 to 09-16
(`docs/ops-extract-on-railway.md`).

Now the condition is the TARGET: `fixture_check_required` says the check runs
whenever the database is not this machine, and under the flag as before.
"""

from __future__ import annotations

import pathlib

import pytest
from psycopg.types.json import Json

from judge.writeguard import fixture_check_required
from tests.conftest import assert_disposable, assert_safe_target

ROOT = pathlib.Path(__file__).resolve().parents[1]
REMOTE = "postgresql://example_user:x@203.0.113.5:5432/modelboard"
LOCAL = "postgresql://postgres:postgres@localhost:5433/modelboard_test"


class TestTheDecision:
    @pytest.mark.parametrize("environment", ["development", "staging", "production", ""])
    def test_a_shared_target_always_requires_it(self, monkeypatch, environment):
        monkeypatch.setenv("ENVIRONMENT", environment)
        assert fixture_check_required(REMOTE, development_write=False)
        assert fixture_check_required(REMOTE, development_write=True)

    @pytest.mark.parametrize("environment", ["development", "production"])
    def test_a_local_target_requires_it_only_under_the_flag(self, monkeypatch, environment):
        monkeypatch.setenv("ENVIRONMENT", environment)
        assert fixture_check_required(LOCAL, development_write=False) is None
        assert fixture_check_required(LOCAL, development_write=True)

    def test_no_target_is_the_callers_error_not_this_ones(self):
        assert fixture_check_required(None, development_write=False) is None

    def test_the_reason_says_which_of_the_two_it_was(self):
        flag = fixture_check_required(REMOTE, development_write=True)
        shared = fixture_check_required(REMOTE, development_write=False)
        assert "--development-write" in flag
        assert "shared" in shared and "--development-write" not in shared


class TestBothScriptsAskIt:
    """The source-level half: each script's check is keyed on the decision,
    not on the flag alone. A revert to `if args.development_write` fails here."""

    def test_fetch_model_keys_the_seeded_check_on_it(self):
        src = (ROOT / "scripts" / "fetch_model.py").read_text(encoding="utf-8")
        assert "fixture_check_required(dsn, development_write=args.development_write)" in src
        assert 'if fixture_reason and provenance == "seed":' in src
        assert 'if args.development_write and provenance == "seed":' not in src

    def test_fetch_model_decides_before_anything_is_harvested(self):
        src = (ROOT / "scripts" / "fetch_model.py").read_text(encoding="utf-8")
        body = src[src.index("def main(argv"):]
        assert body.index("fixture_check_required(") < body.index("harvest_github(")

    def test_the_batch_keys_the_exposure_check_on_it(self):
        src = (ROOT / "scripts" / "run_extraction_batched.py").read_text(encoding="utf-8")
        assert ("fixture_check_required(\n        database_url, "
                "development_write=args.development_write)") in src
        block = src[src.index("THE FIXTURE-EXPOSURE CHECK"):]
        assert block.index("if fixture_reason:") < block.index("fixture_exposure(")
        assert "    if args.development_write:\n        from collect.surface_resolver" not in src


@pytest.fixture
def seeded_db(test_dsn):
    from collect.db import apply_schema, connect

    assert_safe_target(test_dsn)
    connection = connect(test_dsn)
    try:
        assert_disposable(connection, test_dsn)
        connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        apply_schema(connection)
        connection.execute(
            "INSERT INTO model_version (id, canonical_id, provider, family, display_name, "
            "lifecycle, provenance, sources) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            ("mv_seeded", "google/gemini-2.5-flash", "google", "gemini",
             "Gemini 2.5 Flash", "ga", "seed", Json({})),
        )
        connection.commit()
        yield test_dsn
    finally:
        connection.close()


class TestFetchModelOnAContainer:
    """The behaviour: ENVIRONMENT=production, no flag, a shared target, a seeded
    model. The local test database stands in for the shared one by making
    `is_local` answer False - which is the only input the decision reads."""

    def _run(self, monkeypatch, tmp_path, dsn, *, shared: bool):
        import judge.writeguard as writeguard
        import scripts.fetch_model as fetch_model

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DATABASE_URL", dsn)
        monkeypatch.setattr(fetch_model, "FETCH_DIR", tmp_path)
        monkeypatch.setattr(writeguard, "is_local", lambda url: not shared)
        # No network in either arm: with no variants the run ends at E1/E2
        # with "nothing to harvest", which is how the control is told apart.
        monkeypatch.setattr(fetch_model, "_variants_for", lambda *a, **k: [])
        return fetch_model.main(["mv_seeded"])

    def test_a_seeded_model_is_refused_on_a_shared_target(self, seeded_db, monkeypatch,
                                                          tmp_path, capsys):
        assert self._run(monkeypatch, tmp_path, seeded_db, shared=True) == 1
        assert "seeded (build-fixture) model_version" in capsys.readouterr().err

    def test_control_the_same_run_on_a_local_target_is_not_refused(self, seeded_db,
                                                                   monkeypatch, tmp_path):
        """Without this, a refusal from anywhere else would pass the test above."""
        assert self._run(monkeypatch, tmp_path, seeded_db, shared=False) == 0
