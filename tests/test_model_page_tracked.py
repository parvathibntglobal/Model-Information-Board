"""#33 Q2: an untracked model is a THIRD silence, not "no evidence".

`last_swept_at IS NULL` means never swept — "we have not looked at this model",
which is a different claim from "nobody has discussed it". Rule 4 says the two
must render differently, and this is where the model page draws that line.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest
from psycopg.types.json import Json

from judge.pages.model import CapabilityView, ModelPage, ModelPageReader
from judge.store.claims import CONNECT_TIMEOUT_SECONDS

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "contract" / "tables.sql"


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=CONNECT_TIMEOUT_SECONDS) as c:
        c.execute("DROP SCHEMA IF EXISTS public CASCADE")
        c.execute("CREATE SCHEMA public")
        c.execute(SCHEMA.read_text(encoding="utf-8"))
        c.commit()
        yield c


def _seed_model(conn, model_id, *, swept):
    conn.execute(
        "INSERT INTO model_version (id, canonical_id, provider, family, display_name,"
        " lifecycle, provenance, sources, last_swept_at) VALUES"
        " (%s,%s,'x','x',%s,'ga','seed',%s,%s)",
        (model_id, f"x/{model_id}", model_id, Json({}),
         datetime(2026, 8, 20, tzinfo=UTC) if swept else None),
    )
    conn.commit()


class TestTheModelPageReadsWhetherWeLooked:
    def test_a_never_swept_model_is_not_tracked(self, conn):
        _seed_model(conn, "mv_never", swept=False)
        page = ModelPageReader(conn).build("mv_never")
        assert page.tracked is False
        assert page.swept_at is None

    def test_a_swept_model_is_tracked(self, conn):
        _seed_model(conn, "mv_swept", swept=True)
        page = ModelPageReader(conn).build("mv_swept")
        assert page.tracked is True
        assert page.swept_at is not None

    def test_a_model_absent_from_the_registry_is_not_tracked_not_invented(self, conn):
        # No row at all is treated the same as never-swept: not looked at, rather
        # than defaulted to swept (rule 6).
        page = ModelPageReader(conn).build("mv_unknown")
        assert page.tracked is False


class TestTheThreeSilencesRenderDifferently:
    """Unit — no DB. The summary is where rule 4 lands at the model level."""

    def _page(self, *, swept):
        caps = tuple(
            CapabilityView(key=f"c.{i}", failure_mode="loud", slices=()) for i in range(12)
        )
        return ModelPage(
            "mv", "M", capabilities=caps,
            swept_at=datetime(2026, 8, 20, tzinfo=UTC) if swept else None,
        )

    def test_untracked_summary_says_we_have_not_looked(self):
        s = self._page(swept=False).summary
        assert "NOT been swept" in s
        assert "have not asked" in s
        # It must NOT read as "we looked and found nothing".
        assert "have any reports" not in s

    def test_tracked_empty_summary_says_nobody_reported(self):
        s = self._page(swept=True).summary
        assert "have any reports at all" in s
        assert "NOT been swept" not in s

    def test_the_two_summaries_are_not_the_same_string(self):
        assert self._page(swept=False).summary != self._page(swept=True).summary
