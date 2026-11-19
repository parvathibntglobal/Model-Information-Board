"""Content workspace: small-sample label, saved ticks, results overview per
platform, and media files per draft (2026-11-17)."""

from __future__ import annotations

import contextlib
import io
from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter

from judge import gate
from judge.app import app
from judge.content_workspace import db, media, recommend, results, settings, store

S = settings.load()


def _png(w=1080, h=1350) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (12, 12, 14)).save(buf, "PNG")
    return buf.getvalue()


def _pdf(pages=3) -> bytes:
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=810, height=1012.5)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


class TestSmallSample:
    def test_the_busiest_period_decides_and_nothing_is_summed(self):
        limit = S["recommender"]["small_sample_people"]
        assert recommend.sample(limit - 1, S)["small"] is True
        assert "Small sample" in recommend.sample(1, S)["note"]
        assert recommend.sample(limit, S) == {"largest_period_people": limit, "small": False,
                                              "note": None}

    def test_nobody_is_not_a_small_sample(self):
        # No reports is its own state (silence is not praise), not "small".
        assert recommend.sample(0, S)["small"] is False

    def test_a_trajectory_carries_the_label(self):
        week = {"posts": 2, "people": 1, "by_polarity": {}, "topics": [], "said": {}}
        readers = {"model": lambda c, mid: {"id": mid, "name": "M", "provider": "p",
                                            "release_date": "2026-11-01", "price": None},
                   "week": lambda c, mid, start, today: week}
        item = recommend.trajectory(None, "a/m", S, today=datetime(2026, 11, 17).date(),
                                    readers=readers)
        assert item["sample"]["small"] and item["ready"]


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as c:
        c.execute("DROP SCHEMA IF EXISTS public CASCADE")
        c.execute("CREATE SCHEMA public")
        c.commit()
        db.migrate(c)
        store.load_seed(c)
        yield c


def _manual_rule(conn, platform="linkedin"):
    return next(n for n in store.notes(conn, platform)["rule"] if n["check_id"] == "manual")


class TestTicks:
    def test_a_tick_is_saved_and_survives_a_reload(self, conn):
        d = store.create_draft(conn, "linkedin", {"format": "post", "body": "hello"}, None)
        rule = _manual_rule(conn)
        store.set_tick(conn, d["id"], rule["id"], True, "anooj")
        again = store.draft(conn, d["id"])
        t = again["ticks"][str(rule["id"])]
        assert t["ticked"] and t["by"] == "anooj" and t["content_sha"] == again["content_sha"]

    def test_an_edit_after_the_tick_shows_it_was_for_other_text(self, conn):
        d = store.create_draft(conn, "linkedin", {"format": "post", "body": "hello"}, None)
        rule = _manual_rule(conn)
        store.set_tick(conn, d["id"], rule["id"], True, None)
        store.update_draft(conn, d["id"], {"body": "hello, edited"}, None)
        after = store.draft(conn, d["id"])
        assert after["ticks"][str(rule["id"])]["content_sha"] != after["content_sha"]

    def test_unticking_is_kept_as_a_later_row(self, conn):
        d = store.create_draft(conn, "linkedin", {"format": "post"}, None)
        rule = _manual_rule(conn)
        store.set_tick(conn, d["id"], rule["id"], True, None)
        store.set_tick(conn, d["id"], rule["id"], False, None)
        assert store.draft(conn, d["id"])["ticks"][str(rule["id"])]["ticked"] is False
        n = conn.execute("SELECT count(*) FROM cw_tick WHERE draft_id = %s",
                         (d["id"],)).fetchone()[0]
        assert n == 2

    def test_only_a_hand_checked_rule_can_be_ticked(self, conn):
        d = store.create_draft(conn, "linkedin", {"format": "post"}, None)
        coded = next(n for n in store.notes(conn, "linkedin")["rule"] if n["check_id"] == "length")
        with pytest.raises(store.WorkspaceRequestError, match="by hand"):
            store.set_tick(conn, d["id"], coded["id"], True, None)
        other = _manual_rule(conn, "reddit")
        if other["platform_key"] == "reddit":
            with pytest.raises(store.WorkspaceRequestError, match="another platform"):
                store.set_tick(conn, d["id"], other["id"], True, None)


def _posted(conn, platform, when):
    d = store.create_draft(conn, platform, {"format": "post", "title": f"post {when}"}, None)
    store.update_draft(conn, d["id"], {"status": "posted", "posted_url": "https://x.com/i/1"},
                       None)
    conn.execute("UPDATE cw_draft SET posted_at = %s WHERE id = %s", (when, d["id"]))
    return d


class TestResultsOverview:
    def test_posts_newest_first_with_their_latest_reading(self, conn):
        t = datetime.now(UTC) - timedelta(days=3)
        old = _posted(conn, "x", t)
        new = _posted(conn, "x", t + timedelta(days=1))
        store.create_draft(conn, "x", {"format": "post"}, None)   # not posted: not listed
        for v, dt in ((100, 0), (250, 1)):
            results.add(conn, old["id"], metric="impressions", value=v, source="X analytics",
                        observed_at=t + timedelta(hours=dt), note=None, by=None, s=S)
        o = results.overview(conn, "x", S)
        assert [p["draft_id"] for p in o["posts"]] == [new["id"], old["id"]]
        assert o["posts"][1]["latest"]["impressions"]["value"] == 250
        assert o["posts"][0]["latest"] == {} and o["counts"] == {"posted": 2,
                                                                  "with_any_reading": 1}
        assert o["site_visits"]["measured"] is False
        assert "not ranked" in o["order"]


class TestMedia:
    def test_a_png_and_a_pdf_are_read_from_their_contents(self, conn):
        d = store.create_draft(conn, "linkedin", {"format": "document_carousel_text"}, None)
        card = media.add(conn, d["id"], data=_png(1200, 675), filename="card.png",
                         kind="card_png", made_with="test", note=None, by=None, s=S)
        assert (card["width"], card["height"], card["pages"]) == (1200, 675, None)
        deck = media.add(conn, d["id"], data=_pdf(3), filename='deck "v1".pdf',
                         kind="carousel_pdf", made_with="test", note=None, by=None, s=S)
        assert deck["pages"] == 3 and deck["width"] == 1080 and '"' not in deck["filename"]
        data, ctype, _ = media.fetch(conn, deck["id"])
        assert ctype == "application/pdf" and data.startswith(b"%PDF-")

    @pytest.mark.parametrize("data,kind,why", [
        (b"not an image at all", "card_png", "PNG or a PDF"),
        (_pdf(1), "card_png", "is a PNG"),
        (_png(), "carousel_pdf", "is a PDF"),
    ])
    def test_refusals(self, conn, data, kind, why):
        d = store.create_draft(conn, "x", {"format": "post"}, None)
        with pytest.raises(store.WorkspaceRequestError, match=why):
            media.add(conn, d["id"], data=data, filename="f.png", kind=kind, made_with="t",
                      note=None, by=None, s=S)

    def test_too_big_and_unnamed_tools_are_refused(self, conn):
        d = store.create_draft(conn, "x", {"format": "post"}, None)
        small = {**S, "media": {"max_bytes": 100}}
        with pytest.raises(store.WorkspaceRequestError, match="over 100"):
            media.add(conn, d["id"], data=_png(), filename="c.png", kind="card_png",
                      made_with="t", note=None, by=None, s=small)
        with pytest.raises(store.WorkspaceRequestError, match="made_with"):
            media.add(conn, d["id"], data=_png(), filename="c.png", kind="card_png",
                      made_with=" ", note=None, by=None, s=S)

    def test_a_file_made_before_an_edit_shows_as_out_of_date(self, conn):
        d = store.create_draft(conn, "x", {"format": "post", "body": "a"}, None)
        media.add(conn, d["id"], data=_png(), filename="c.png", kind="card_png",
                  made_with="t", note=None, by=None, s=S)
        assert media.listing(conn, d["id"])[0]["out_of_date"] is False
        store.update_draft(conn, d["id"], {"body": "b"}, None)
        assert media.listing(conn, d["id"])[0]["out_of_date"] is True


class TestEndpoints:
    @pytest.fixture
    def client(self, conn, monkeypatch):
        monkeypatch.setattr(db, "connect", lambda *a, **k: contextlib.nullcontext(conn))
        return TestClient(app)

    def test_media_file_is_served_privately(self, client, conn):
        d = store.create_draft(conn, "x", {"format": "post"}, None)
        m = media.add(conn, d["id"], data=_png(), filename="c.png", kind="card_png",
                      made_with="t", note=None, by=None, s=S)
        r = client.get(f"/admin/content/media/{m['id']}")
        assert r.status_code == 200 and r.headers["content-type"] == "image/png"
        assert "no-store" in r.headers["cache-control"]
        listed = client.get(f"/admin/content/drafts/{d['id']}/media").json()["media"]
        assert listed[0]["id"] == m["id"]

    def test_the_workspace_stays_behind_the_login(self):
        """anooj, 2026-11-17: always inside the login, even once approved."""
        from starlette.requests import Request

        for path in ("/admin/content/media/1", "/admin/content/platforms/x/results",
                     "/admin/content/drafts/1/media", "/admin/content/platforms"):
            req = Request({"type": "http", "method": "GET", "path": path, "query_string": b"",
                           "headers": []})
            assert not gate.is_public_read(req), path

    def test_a_tick_through_the_api(self, client, conn):
        d = store.create_draft(conn, "linkedin", {"format": "post"}, None)
        rule = _manual_rule(conn)
        r = client.post(f"/admin/content/drafts/{d['id']}/ticks",
                        json={"note_id": rule["id"], "ticked": True})
        assert r.status_code == 200 and r.json()["ticks"][str(rule["id"])]["ticked"]
