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
        # Two people on dev.to (one posting twice, under two capabilities) and
        # one on Reddit, which the public view withholds.
        for author, source in (("au1", "devto"), ("au2", "devto"), ("au3", "reddit")):
            connection.execute(
                "INSERT INTO author (id, source, external_id) VALUES (%s, %s, %s)",
                (author, source, author),
            )
        for doc, source, mv, author in (
            ("d1", "devto", "mv_a", "au1"),
            ("d3", "devto", "mv_a", "au1"),
            ("d4", "devto", "mv_a", "au2"),
            ("d2", "reddit", "mv_r", "au3"),
        ):
            connection.execute(
                "INSERT INTO document "
                "(id, source, external_id, url, text_ref, content_hash, status, author_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, 'kept', %s)",
                (doc, source, doc, f"https://example.test/{doc}", f"r{doc}", f"h{doc}", author),
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
                    {
                        **entry("acme/text-r", ["text"], created=1_790_100_000),
                        "expiration_date": "2026-11-11",
                        "knowledge_cutoff": "2026-02-16",
                    },
                    entry("acme/text-r:batch", ["text"], created=1_790_200_000),
                    entry("acme/image-late", ["image"], created=1_790_200_000),
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
            # image-i and image-late; text-a, text-r, text-r:batch, text-x:free, m1, m2
            view["types"]["video"] == 1
            and view["types"]["image"] == 2
            and view["types"]["text"] == 6
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


class TestVoicesOrderTheList:
    def test_voices_are_distinct_people_on_the_public_view(self, view):
        """au1 posted twice: one voice, two reports. au3 is on Reddit only."""
        m = model(view, "acme/text-a")
        assert (m["voices"], m["reports"]) == (2, 3)
        assert model(view, "acme/text-r")["voices"] == 0

    def test_a_type_with_no_voiced_model_stays_empty(self, view):
        assert view["types_voiced"]["text"] == 1
        assert view["types_voiced"]["video"] == 0 and view["types"]["video"] == 1
        assert view["voiced"] == 1


class TestOneModelsPage:
    def test_every_listed_model_has_a_page_voiced_or_not(self, conn):
        from judge.catalog import catalog_model

        assert catalog_model(conn, "acme/video-v")["voices"] == 0
        assert catalog_model(conn, "acme/text-a")["voices"] == 2

    def test_a_model_not_listed_has_no_page(self, conn):
        from judge.catalog import catalog_model

        assert catalog_model(conn, "acme/nothing") is None

    def test_a_feature_the_feed_does_not_list_is_not_stated_not_no(self, conn):
        """`entry()` lists no supported parameters: tool calling is unknown, not absent."""
        from judge.catalog import catalog_model

        f = catalog_model(conn, "acme/text-a")["features"]
        assert f["tools"] is None and f["structured_output"] is None
        assert f["vision_input"] is False

    def test_registry_facts_come_through_for_a_tracked_model(self, conn):
        from judge.catalog import catalog_model

        assert catalog_model(conn, "acme/text-a")["in_registry"] is True
        assert catalog_model(conn, "acme/video-v")["registry"] is None


def test_the_personas_say_they_are_illustrative():
    """Rule 7: numbers nobody measured are shown as starting points, never as
    what a workload costs."""
    js = (ROOT / "web" / "src" / "tokens" / "PersonaPicker.jsx").read_text(encoding="utf-8")
    assert "Illustrative starting points, not measurements" in js
    personas = (ROOT / "web" / "src" / "tokens" / "personas.js").read_text(encoding="utf-8")
    names = re.findall(r"name: '([^']+)'", personas)
    assert len(names) == len(set(names)) >= 5


class TestLifecycle:
    def test_the_feeds_dates_are_parsed(self):
        [row] = parse_catalog(
            {
                "data": [
                    {
                        **entry("acme/t", ["text"]),
                        "expiration_date": "2026-11-11",
                        "knowledge_cutoff": "not a date",
                    }
                ]
            }
        )
        assert str(row["expiration_date"]) == "2026-11-11"
        assert row["knowledge_cutoff"] is None, "a malformed date is no date, never a guess"

    def test_a_retirement_is_shown_with_its_source(self, conn):
        from judge.catalog import catalog_model

        lc = catalog_model(conn, "acme/text-r")["lifecycle"]
        assert lc["retirements"] == [{"date": "2026-11-11", "source": "OpenRouter"}]
        assert (
            lc["knowledge_cutoff"] == "2026-02-16" and lc["knowledge_cutoff_source"] == "OpenRouter"
        )

    def test_two_readings_of_one_date_are_one_date(self, conn):
        """The registry's retirement_date is OpenRouter's expiration_date read
        by an earlier poll - one source, so an agreeing date shows once."""
        from judge.catalog import catalog_model

        conn.execute("UPDATE model_version SET retirement_date = '2026-11-11' WHERE id = 'mv_r'")
        assert len(catalog_model(conn, "acme/text-r")["lifecycle"]["retirements"]) == 1
        conn.execute("UPDATE model_version SET retirement_date = '2026-10-31' WHERE id = 'mv_r'")
        sources = [
            r["source"] for r in catalog_model(conn, "acme/text-r")["lifecycle"]["retirements"]
        ]
        assert sources == ["OpenRouter", "OpenRouter, an earlier reading"]

    def test_no_date_is_none_announced_not_a_promise(self, conn):
        from judge.catalog import catalog_model

        assert catalog_model(conn, "acme/text-a")["lifecycle"]["retirements"] == []

    def test_newer_from_provider_is_the_same_kind_and_no_variant(self, conn):
        """`text-r:batch` is a variant and `image-late` writes images: neither
        is a newer text model from this provider."""
        from judge.catalog import catalog_model

        newer = [
            n["id"] for n in catalog_model(conn, "acme/text-a")["lifecycle"]["newer_from_provider"]
        ]
        assert newer == ["acme/text-r"]


def test_the_cache_drawer_lists_models_without_a_rate_apart_and_says_it_is_an_upper_bound():
    js = (ROOT / "web" / "src" / "tokens" / "CacheSavings.jsx").read_text(encoding="utf-8")
    assert "if (m.price_cached_read == null) { noRate.push" in js
    assert "An upper bound" in js


def test_the_modality_finder_lists_unpriced_models_apart():
    js = (ROOT / "web" / "src" / "finder" / "ModalityFinder.jsx").read_text(encoding="utf-8")
    assert "unpriced.push(m)" in js and "not priced per token" in js
