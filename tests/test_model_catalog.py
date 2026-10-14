"""The Models pages' catalogue: OpenRouter's whole list, by provider and type.

What these keep true:
  - a type is OpenRouter's own output modality, copied - the board invents none;
  - nothing in the evidence pipeline reads the catalogue (it is its own table);
  - no price is invented: an all-zero listing is "not published", not free;
  - a "latest" alias is not a second model, and one company is one bubble;
  - a model links to reports only when the PUBLIC view holds some;
  - the menu and the page offer the same seven types.
"""

from __future__ import annotations

import json
import pathlib
import re
from datetime import UTC, datetime

import psycopg
import pytest

from collect.registry.catalog import CATALOG_URL, parse_catalog, provider_of, write_catalog
from collect.registry.openrouter import UnreadableFeed
from judge import publication

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "contract" / "tables.sql"


def entry(
    model_id,
    outs,
    *,
    name=None,
    created=1_790_000_000,
    prompt="0.000001",
    completion="0.000002",
    **pricing,
):
    return {
        "id": model_id,
        "name": name or f"Acme: {model_id}",
        "created": created,
        "context_length": 128000,
        "architecture": {"input_modalities": ["text"], "output_modalities": outs},
        "pricing": {"prompt": prompt, "completion": completion, **pricing},
    }


class TestParsing:
    def test_it_reads_every_output_type_not_the_text_only_default(self):
        assert CATALOG_URL.endswith("?output_modalities=all")

    def test_a_type_is_the_feeds_own_output_modality(self):
        [row] = parse_catalog({"data": [entry("acme/v", ["video"])]})
        assert row["output_modalities"] == ["video"]

    def test_a_latest_alias_keeps_its_id_and_loses_the_tilde_in_its_provider(self):
        assert provider_of("~perplexity/pplx-decider-27b-latest") == "perplexity"

    def test_a_negative_sentinel_price_stays_unknown(self):
        [row] = parse_catalog(
            {"data": [entry("openrouter/auto", ["text"], prompt="-1", completion="-1")]}
        )
        assert row["price_in"] is None and row["price_out"] is None

    def test_a_feed_with_no_models_is_unreadable_not_empty(self):
        with pytest.raises(UnreadableFeed):
            parse_catalog({"data": []})
        with pytest.raises(UnreadableFeed):
            parse_catalog("not a list")


@pytest.fixture(autouse=True)
def _public_view(monkeypatch):
    publication.withheld_sources.cache_clear()
    monkeypatch.delenv("PUBLICATION_VIEW", raising=False)
    yield
    publication.withheld_sources.cache_clear()


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as connection:
        connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
        connection.execute("CREATE SCHEMA public")
        connection.execute(SCHEMA.read_text(encoding="utf-8"))
        # Two registry models: one with a public report, one reported only on Reddit.
        for mv, cid in (("mv_a", "acme/text-a"), ("mv_r", "acme/text-r")):
            connection.execute(
                "INSERT INTO model_version (id, canonical_id, provider, sources, provenance) "
                "VALUES (%s, %s, 'acme', '{}', 'polled')",
                (mv, cid),
            )
        for doc, source, mv in (("d1", "devto", "mv_a"), ("d2", "reddit", "mv_r")):
            connection.execute(
                "INSERT INTO document "
                "(id, source, external_id, url, text_ref, content_hash, status) "
                "VALUES (%s, %s, %s, %s, %s, %s, 'kept')",
                (doc, source, doc, f"https://example.test/{doc}", f"r{doc}", f"h{doc}"),
            )
            connection.execute(
                "INSERT INTO board_entry (id, section, slug, name, definition, model_version_id, "
                "document_id, quote, quote_verified, polarity, proposer_model, pipeline_version) "
                "VALUES (%s, 'capability', 'tool-use', 'Tool use', 'Def.', %s, %s, 'q', true, "
                "'positive', 'm', 'v1')",
                (f"be_{doc}", mv, doc),
            )
        rows = parse_catalog(
            {
                "data": [
                    entry("acme/text-a", ["text"], created=1_790_000_000),
                    entry("acme/text-r", ["text"], created=1_790_100_000),
                    entry("acme/text-x:free", ["text"], prompt="0", completion="0"),
                    entry("acme/video-v", ["video"], prompt="0", completion="0"),
                    entry(
                        "acme/image-i",
                        ["image"],
                        prompt="0",
                        completion="0",
                        image_output="0.0000024",
                    ),
                    entry("~acme/text-latest", ["text"]),
                    entry("meta/m1", ["text"], name="Meta: One"),
                    entry("meta-llama/m2", ["text"], name="Meta: Two"),
                ]
            }
        )
        write_catalog(connection, rows, seen_at=datetime(2026, 10, 14, tzinfo=UTC))
        connection.commit()
        yield connection


@pytest.fixture
def view(conn):
    from judge.catalog import catalog_view

    return catalog_view(conn)


def model(view, mid):
    return next(m for m in view["models"] if m["id"] == mid)


class TestTheView:
    def test_a_latest_alias_is_left_out_and_counted(self, view):
        assert "~acme/text-latest" not in {m["id"] for m in view["models"]}
        assert view["aliases_left_out"] == 1

    def test_one_company_is_one_bubble(self, view):
        [meta] = [p for p in view["providers"] if p["name"] == "Meta"]
        assert sorted(meta["ids"]) == ["meta", "meta-llama"] and meta["models"] == 2

    def test_an_all_zero_listing_is_not_published_not_free(self, view):
        assert model(view, "acme/video-v")["price_state"] == "not_published"
        assert model(view, "acme/text-x:free")["price_state"] == "free"

    def test_an_image_model_shows_the_price_it_is_charged_by(self, view):
        tp = model(view, "acme/image-i")["type_price"]
        assert tp["label"] == "Image output" and tp["usd_per_million"] == pytest.approx(2.4)

    def test_types_are_counted_from_the_feed(self, view):
        assert (
            view["types"]["video"] == 1
            and view["types"]["image"] == 1
            and view["types"]["text"] == 5
        )

    def test_new_releases_are_newest_listed_first(self, view):
        order = view["new_releases"]
        assert order.index("acme/text-r") < order.index("acme/text-a")

    def test_reports_link_only_where_the_public_view_holds_some(self, view):
        """`text-r` is reported only on Reddit, which the public view withholds -
        its link would open an empty page."""
        assert model(view, "acme/text-a")["reported"] is True
        assert model(view, "acme/text-r")["reported"] is False
        assert model(view, "acme/text-r")["in_registry"] is True
        assert model(view, "acme/video-v")["in_registry"] is False

    def test_a_model_the_latest_poll_did_not_list_is_not_shown(self, conn):
        from judge.catalog import catalog_view

        write_catalog(
            conn,
            parse_catalog({"data": [entry("acme/text-a", ["text"])]}),
            seen_at=datetime(2026, 10, 15, tzinfo=UTC),
        )
        assert [m["id"] for m in catalog_view(conn)["models"]] == ["acme/text-a"]


class TestTheEvidencePipelineNeverReadsIt:
    def test_only_the_catalogue_modules_name_the_table(self):
        users = {
            p.relative_to(ROOT).as_posix()
            for p in (ROOT / "collect").rglob("*.py")
            if "model_catalog" in p.read_text(encoding="utf-8")
        }
        users |= {
            p.relative_to(ROOT).as_posix()
            for p in (ROOT / "judge").rglob("*.py")
            if "model_catalog" in p.read_text(encoding="utf-8")
        }
        assert users == {
            "collect/registry/catalog.py",
            "collect/cli.py",
            "collect/ops/chain.py",
            "judge/catalog.py",
            "judge/app.py",
        }

    def test_the_nightly_chain_polls_it_without_depending_on_it(self):
        src = (ROOT / "collect" / "ops" / "chain.py").read_text(encoding="utf-8")
        assert 'Stage("poll-catalog", run=_poll_catalog_stage, needs=("preflight",))' in src
        assert 'needs=("poll-catalog"' not in src


def test_the_menu_and_the_page_offer_the_same_seven_types():
    from judge.catalog import TYPES

    js = (ROOT / "web" / "src" / "catalog" / "types.js").read_text(encoding="utf-8")
    assert tuple(re.findall(r"\{ key: '([a-z]+)'", js)) == TYPES


def test_the_view_is_json():
    """The route returns it as-is; a date or Decimal left in would 500."""
    from judge.catalog import _type_price

    json.dumps(_type_price({"image_output": "0.0000024"}))
