"""Text in a "not readable" post's first picture, shadow mode (#679 step 3; CLAUDE.md's
fourth fetch exception, #683).

These pin each condition of the exception where code can hold it:
  * only the first picture link the provider gave (media.*_picture), Instagram's kept so
    its refusal is counted;
  * robots.txt asked for every hop; a refusal is `refused`, no answer is `failed`;
  * at most `ocr.max_bytes`, an image only; the folder removed whatever happened;
  * at most `ocr.max_per_run`, in turn by platform, then account, newest first;
  * the text decides no label: it only sets `picture_text_would_pass` (and
    `picture_text_only_ai` when it added only `ai`), from words at `ocr.min_confidence`;
  * the contract ships it off, and `affects_labels: true` is refused;
  * the store keeps every word with its confidence, clears the text after
    `retention.clear_text_after_days` WHATEVER the label, and the upsert never touches it;
  * AI Watch counts the not-readable pictures by status, `not_tried` said as itself.
The store and page tests use the disposable test database.
"""

from __future__ import annotations

import copy
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from collect.industry_ai import config as iai_config
from collect.industry_ai import media, ocr
from collect.industry_ai.config import CONTRACT, IndustryAIConfigError
from collect.industry_ai.pipeline import evaluate
from collect.industry_ai.rules import (
    OCR_STATUSES,
    PICTURE_TEXT_AI_ONLY_FLAG,
    PICTURE_TEXT_FLAG,
    Item,
    picture_text_flags,
    picture_words,
)

NOW = datetime.now(UTC)
WATCH = "watch:reddit:r/ClaudeAI"  # in contract/industry_ai.yaml watch.reddit
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def raw():
    return yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cfg(raw):
    return iai_config.parse(raw)


# ── the first picture's link ─────────────────────────────────────────────────


def test_x_gives_its_first_photo_and_nothing_for_a_video():
    photo = {"legacy": {"extended_entities": {"media": [
        {"type": "photo", "media_url_https": "https://pbs.twimg.com/media/a.jpg"},
        {"type": "photo", "media_url_https": "https://pbs.twimg.com/media/b.jpg"}]}}}
    assert media.x_picture(json.dumps(photo)) == "https://pbs.twimg.com/media/a.jpg"
    assert media.x_picture({"tweet": photo}) == "https://pbs.twimg.com/media/a.jpg"
    video = {"legacy": {"extended_entities": {"media": [{"type": "video"}]}}}
    assert media.x_picture(video) is None
    assert media.x_picture("not json") is None
    assert media.x_picture({"legacy": {"full_text": "x"}}) is None


def test_reddit_gives_an_image_or_a_gallerys_first_in_its_own_order():
    assert media.reddit_picture({"post_hint": "image", "url": "https://i.redd.it/a.png"}) \
        == "https://i.redd.it/a.png"
    gallery = {"is_gallery": True,
               "gallery_data": {"items": [{"media_id": "two"}, {"media_id": "one"}]},
               "media_metadata": {"one": {"s": {"u": "https://preview.redd.it/1.jpg?a=1&amp;b=2"}},
                                  "two": {"s": {"u": "https://preview.redd.it/2.jpg?a=1&amp;b=2"}}}}
    assert media.reddit_picture(gallery) == "https://preview.redd.it/2.jpg?a=1&b=2"
    assert media.reddit_picture({"is_self": True}) is None
    assert media.reddit_picture({}) is None


def test_bluesky_gives_the_first_fullsize():
    post = {"embed": {"$type": "app.bsky.embed.images#view",
                      "images": [{"fullsize": "https://cdn.bsky.app/a", "thumb": "t"}, {}]}}
    assert media.bluesky_picture(post) == "https://cdn.bsky.app/a"
    quote = {"embed": {"$type": "app.bsky.embed.recordWithMedia#view",
                       "media": {"images": [{"thumb": "https://cdn.bsky.app/t"}]}}}
    assert media.bluesky_picture(quote) == "https://cdn.bsky.app/t"
    assert media.bluesky_picture({"embed": None}) is None


def test_instagram_gives_its_link_so_the_refusal_is_counted():
    node = {"__typename": "GraphImage", "display_url": "https://scontent.cdninstagram.com/a"}
    assert media.instagram_picture(node) == "https://scontent.cdninstagram.com/a"
    first_video = {"edge_sidecar_to_children": {"edges": [{"node": {"is_video": True}}]}}
    assert media.instagram_picture(first_video) is None


# ── the contract ─────────────────────────────────────────────────────────────


def test_the_contract_ships_it_off_and_in_shadow_mode(cfg):
    assert cfg.ocr["enabled"] is False and cfg.ocr["affects_labels"] is False
    assert cfg.ocr["max_per_run"] == 150  # #683


@pytest.mark.parametrize("mutate, says", [
    (lambda o: o.update(affects_labels=True), "not built"),
    (lambda o: o.pop("min_confidence"), "min_confidence"),
    (lambda o: o.update(min_confidence=101), "0-100"),
    (lambda o: o.update(max_per_run=0), "max_per_run"),
    (lambda o: o.update(enabled="yes"), "true or false"),
    (lambda o: o.update(colour="red"), "colour"),
])
def test_a_bad_ocr_block_is_refused(raw, mutate, says):
    bad = copy.deepcopy(raw)
    mutate(bad["ocr"])
    with pytest.raises(IndustryAIConfigError, match=says):
        iai_config.parse(bad)


def test_the_table_and_the_migration_accept_exactly_these_statuses():
    for path in (CONTRACT.parent / "tables.sql",
                 CONTRACT.parent / "migrations" / "20261126T1500_iai_item_picture_text.sql"):
        sql = path.read_text(encoding="utf-8")
        check = re.search(r"iai_item_ocr_status_ck\s+CHECK \(ocr_status IS NULL\s+"
                          r"OR ocr_status IN \(([^)]*)\)\)", sql)
        assert check, path.name
        assert tuple(re.findall(r"'([a-z_]+)'", check.group(1))) == OCR_STATUSES, path.name


def test_the_pages_have_words_for_both_flags():
    src = (ROOT / "web" / "src" / "industry-ai" / "posts.jsx").read_text(encoding="utf-8")
    for flag in (PICTURE_TEXT_FLAG, PICTURE_TEXT_AI_ONLY_FLAG):
        assert f"  {flag}: '" in src, flag


# ── what the text would decide, in shadow mode ───────────────────────────────

CAPTION = "New one up 🔥 #tech"
ABOUT_AI = ("Testing ChatGPT for invoice reconciliation at our accounting firm this "
            "quarter, results inside")
BARE_AI = "The new ai workflow for our weekly team planning meetings and the notes after them"


def picture_post(text=None, conf=None, *, iid="p1", status="ok", author="t2_a", hours=6):
    words = (text or "").split()
    conf = conf if conf is not None else [90] * len(words)
    return Item(id=f"reddit:{iid}", platform="reddit", external_id=iid,
                url=f"https://www.reddit.com/{iid}", title="", body=CAPTION,
                created_at=NOW - timedelta(hours=hours), author_id=author,
                engagement={"score": 5}, query_keys={WATCH}, media_kind="image",
                picture_url=f"https://i.redd.it/{iid}.png",
                ocr_text=text, ocr_confidence=tuple(conf),
                ocr_status=status if text else None)


def test_only_confident_words_count():
    it = picture_post("ChatGPT ok blurry", [95, 60, 12])
    assert picture_words(it, 60) == "ChatGPT ok"
    assert picture_words(it, 96) == ""
    with pytest.raises(ValueError, match="confidence"):
        picture_words(picture_post("two words", [90]), 60)


def test_a_picture_that_names_ai_sets_the_flag(cfg):
    assert picture_text_flags(picture_post(ABOUT_AI), cfg) == [PICTURE_TEXT_FLAG]


def test_bare_ai_alone_is_flagged_apart(cfg):
    """Parvathi, #683: the case most exposed to stray letters read from a photo."""
    assert picture_text_flags(picture_post(BARE_AI), cfg) == [PICTURE_TEXT_FLAG,
                                                               PICTURE_TEXT_AI_ONLY_FLAG]


def test_low_confidence_or_no_text_sets_nothing(cfg):
    words = ABOUT_AI.split()
    assert picture_text_flags(picture_post(ABOUT_AI, [10] * len(words)), cfg) == []
    assert picture_text_flags(picture_post(None), cfg) == []


def test_the_post_stays_not_readable_and_carries_the_flag(cfg):
    it = picture_post(ABOUT_AI)
    results, _ = evaluate([it], cfg, since=NOW - timedelta(days=90), now=NOW)
    r = results[it.id]
    assert (r.verdict, r.stage) == ("dropped", "unread"), "shadow mode: no label moves"
    assert PICTURE_TEXT_FLAG in r.flags


# ── which posts, in what order ───────────────────────────────────────────────


def test_only_this_runs_not_readable_pictures_with_a_link_and_no_final_answer(cfg):
    a, b = picture_post(None, iid="a"), picture_post(None, iid="b")
    c = picture_post(None, iid="c")
    c.picture_url = None
    results, _ = evaluate([a, b, c], cfg, since=NOW - timedelta(days=90), now=NOW)
    stored = {a.id: None, b.id: "no_text", c.id: None}
    cutoff = NOW - timedelta(days=30)
    kw = {"first_seen": {}, "not_before": cutoff}
    assert [it.id for it in ocr.candidates([a, b, c], results, stored, **kw)] == [a.id]
    assert [it.id for it in ocr.candidates([a], results, {a.id: "over_cap"}, **kw)] == [a.id]
    # #687 review: a post first stored before the retention cutoff would be read and
    # then cleared in the same run, so it is not a candidate; one seen since is.
    old = {"first_seen": {a.id: cutoff - timedelta(days=1)}, "not_before": cutoff}
    assert ocr.candidates([a], results, {a.id: "over_cap"}, **old) == []
    young = {"first_seen": {a.id: cutoff + timedelta(days=1)}, "not_before": cutoff}
    assert [it.id for it in ocr.candidates([a], results, {a.id: None}, **young)] == [a.id]


def test_platforms_then_accounts_take_turns_newest_first():
    def p(platform, author, hours):
        return Item(id=f"{platform}:{author}{hours}", platform=platform, external_id="1",
                    url="u", title="", body="", created_at=NOW - timedelta(hours=hours),
                    author_id=author)

    heavy = [p("x", "heavy", h) for h in (1, 2, 3, 4)]
    order = ocr.in_turn([*heavy, p("x", "other", 5), p("reddit", "r", 9), p("reddit", "r", 8)])
    assert [i.id for i in order] == ["reddit:r8", "x:heavy1", "reddit:r9", "x:other5",
                                     "x:heavy2", "x:heavy3", "x:heavy4"]


def test_over_the_cap_is_recorded_not_skipped(monkeypatch):
    posts = [picture_post(None, iid=f"c{i}", author=f"t2_{i}") for i in range(3)]
    monkeypatch.setattr(ocr.shutil, "which", lambda _: "/usr/bin/tesseract")
    monkeypatch.setattr(ocr, "read_one", lambda *a, **k: ocr.PictureRead("no_text"))
    reads = ocr.read_pictures(posts, {"max_per_run": 2, "max_bytes": 10, "timeout_seconds": 1},
                              client=None, gate=None)
    assert sorted(r.status for r in reads.values()) == ["no_text", "no_text", "over_cap"]


def test_a_missing_tesseract_refuses_before_any_download(monkeypatch):
    monkeypatch.setattr(ocr.shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError, match="not installed"):
        ocr.read_pictures([picture_post(None)], {"max_per_run": 5, "max_bytes": 10,
                                                 "timeout_seconds": 1}, client=None, gate=None)


# ── one picture: robots.txt, size, type, the folder ──────────────────────────

TSV = ("level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight"
       "\tconf\ttext\n"
       "1\t1\t0\t0\t0\t0\t0\t0\t10\t10\t-1\t\n"
       "5\t1\t1\t1\t1\t1\t0\t0\t5\t5\t96.4\tChatGPT\n"
       "5\t1\t1\t1\t1\t2\t0\t0\t5\t5\t-1\t\n"
       "5\t1\t1\t1\t1\t3\t0\t0\t5\t5\t41\tdrafts\n")


def test_tesseract_tsv_becomes_aligned_words_and_confidences():
    assert ocr.parse_tsv(TSV) == (["ChatGPT", "drafts"], [96, 41])
    assert ocr.parse_tsv("") == ([], [])
    with pytest.raises(ValueError, match="not Tesseract TSV"):
        ocr.parse_tsv("hello\tworld\n")


class _Resp:
    def __init__(self, status=200, ctype="image/png", body=b"x" * 50, to=None):
        self.status_code, self._body = status, body
        self.headers = {"content-type": ctype}
        self.is_redirect = to is not None
        self.next_request = SimpleNamespace(url=to)

    def iter_bytes(self):
        yield from (self._body[i:i + 10] for i in range(0, len(self._body), 10))

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Client:
    def __init__(self, *responses):
        self.responses, self.asked = list(responses), []

    def stream(self, method, url, headers=None):
        self.asked.append(url)
        return self.responses.pop(0)


class _Gate:
    def __init__(self, refuse=(), no_answer=()):
        self.refuse, self.no_answer, self.asked = refuse, no_answer, []

    def allows(self, url):
        self.asked.append(url)
        status = "no-answer" if url in self.no_answer else "ok"
        return SimpleNamespace(allowed=url not in self.refuse and url not in self.no_answer,
                               reason="Disallow: /", ruling=SimpleNamespace(status=status))


@pytest.fixture
def folders(monkeypatch, tmp_path):
    """Every temporary folder read_one makes, to check it is gone afterwards."""
    made = []
    real = ocr.tempfile.mkdtemp

    def mkdtemp(prefix=""):
        made.append(Path(real(prefix=prefix, dir=tmp_path)))
        return str(made[-1])

    monkeypatch.setattr(ocr.tempfile, "mkdtemp", mkdtemp)
    return made


def _read(url, client, gate, **kw):
    return ocr.read_one(url, client=client, gate=gate, max_bytes=kw.get("max_bytes", 1000),
                        timeout=5, tesseract="tesseract")


def test_a_read_picture_keeps_only_its_text_and_the_folder_goes(monkeypatch, folders):
    monkeypatch.setattr(ocr.subprocess, "run",
                        lambda *a, **k: SimpleNamespace(returncode=0, stdout=TSV))
    got = _read("https://i.redd.it/a.png", _Client(_Resp()), _Gate())
    assert (got.status, got.text, got.confidence) == ("ok", "ChatGPT drafts", (96, 41))
    assert folders and not any(f.exists() for f in folders)


def test_robots_txt_is_asked_for_every_hop(folders):
    gate = _Gate(refuse=("https://cdn.example/b.png",))
    client = _Client(_Resp(to="https://cdn.example/b.png"))
    got = _read("https://i.redd.it/a.png", client, gate)
    assert got.status == "refused"
    assert gate.asked == ["https://i.redd.it/a.png", "https://cdn.example/b.png"]
    assert not any(f.exists() for f in folders)


def test_no_answer_from_robots_txt_is_a_failure_not_a_refusal(folders):
    url = "https://i.redd.it/a.png"
    assert _read(url, _Client(), _Gate(no_answer=(url,))).status == "failed"


@pytest.mark.parametrize("resp, status", [
    (_Resp(body=b"x" * 2000), "too_large"),
    (_Resp(ctype="text/html"), "failed"),
    (_Resp(status=404), "failed"),
])
def test_size_type_and_status_are_checked(folders, resp, status):
    assert _read("https://i.redd.it/a.png", _Client(resp), _Gate()).status == status
    assert not any(f.exists() for f in folders)


def test_not_https_and_tesseract_failures_are_failed(monkeypatch, folders):
    assert _read("http://i.redd.it/a.png", _Client(), _Gate()).status == "failed"
    monkeypatch.setattr(ocr.subprocess, "run",
                        lambda *a, **k: SimpleNamespace(returncode=1, stdout=""))
    assert _read("https://i.redd.it/a.png", _Client(_Resp()), _Gate()).status == "failed"
    monkeypatch.setattr(ocr.subprocess, "run",
                        lambda *a, **k: SimpleNamespace(returncode=0, stdout=TSV.split("\n")[0]))
    assert _read("https://i.redd.it/a.png", _Client(_Resp()), _Gate()).status == "no_text"


# ── stored, cleared, counted ─────────────────────────────────────────────────


@pytest.fixture
def conn(test_dsn):
    from collect.db import apply_schema, connect
    from tests.conftest import assert_disposable, assert_safe_target

    assert_safe_target(test_dsn)
    connection = connect(test_dsn)
    try:
        assert_disposable(connection, test_dsn)
        connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        apply_schema(connection)
        connection.commit()
        yield connection
    finally:
        connection.rollback()
        connection.close()


def test_reads_are_stored_loaded_and_never_overwritten_by_a_reharvest(conn, cfg):
    from collect.industry_ai import store

    store.start_run(conn, "iai-o", mode="harvest", domains=[], platforms=["reddit"],
                    pipeline_version="test")
    a, b = picture_post(None, iid="a"), picture_post(None, iid="b")
    store.upsert_items(conn, [a, b], run_id="iai-o")
    store.write_picture_reads(conn, {
        a.id: ocr.PictureRead("ok", text=ABOUT_AI, confidence=tuple([90] * len(ABOUT_AI.split()))),
        b.id: ocr.PictureRead("over_cap")}, {a.id: [PICTURE_TEXT_FLAG]})
    conn.commit()
    assert store.ocr_status_of(conn, [a.id, b.id, "reddit:none"]) == {a.id: "ok", b.id: "over_cap"}
    loaded = {it.id: it for it in store.load_items(conn)}
    assert loaded[a.id].ocr_text == ABOUT_AI and len(loaded[a.id].ocr_confidence) == 13
    assert (loaded[b.id].ocr_text, loaded[b.id].ocr_status) == (None, "over_cap")
    assert PICTURE_TEXT_FLAG in conn.execute(
        "SELECT flags FROM iai_item WHERE id = %s", (a.id,)).fetchone()[0]
    store.upsert_items(conn, [a], run_id="iai-o")  # found again
    conn.commit()
    assert conn.execute("SELECT ocr_text FROM iai_item WHERE id = %s", (a.id,)).fetchone()[0] \
        == ABOUT_AI
    with pytest.raises(Exception, match="ocr_status"):
        conn.execute("UPDATE iai_item SET ocr_status = 'maybe'")


def test_picture_text_is_cleared_at_its_age_whatever_the_label(conn, cfg):
    from collect.industry_ai import store

    store.start_run(conn, "iai-o", mode="harvest", domains=[], platforms=["reddit"],
                    pipeline_version="test")
    old, young = picture_post(None, iid="old"), picture_post(None, iid="young")
    store.upsert_items(conn, [old, young], run_id="iai-o")
    reads = {i.id: ocr.PictureRead("ok", text="ChatGPT notes", confidence=(90, 90))
             for i in (old, young)}
    store.write_picture_reads(conn, reads, {})
    age = int(cfg.retention["clear_text_after_days"]) + 1
    # KEPT, which title/body retention would leave alone (not Personal): still cleared.
    conn.execute("UPDATE iai_item SET verdict = 'kept', drop_stage = NULL, drop_reason = NULL, "
                 "first_seen_at = now() - make_interval(days => %s) WHERE id = %s", (age, old.id))
    conn.commit()
    assert store.clear_picture_text(conn, cfg.retention) == 1
    conn.commit()
    rows = dict((r[0], (r[1], list(r[2] or []))) for r in conn.execute(
        "SELECT id, ocr_text, ocr_confidence FROM iai_item").fetchall())
    assert rows == {old.id: ("", []), young.id: ("ChatGPT notes", [90, 90])}
    assert store.clear_picture_text(conn, cfg.retention) == 0, "cleared once"
    assert next(i for i in store.load_items(conn) if i.id == old.id).ocr_text is None


def test_the_run_step_reads_this_runs_pictures_and_stores_flags(conn, cfg, monkeypatch):
    """scripts/run_industry_ai.py read_picture_text end to end on the database, the
    network faked: only this run's not-readable posts with a link are read, the reads
    and their shadow flags are stored, and the run says every status."""
    import collect.adapters.blog.robots as robots
    import collect.http as http
    import scripts.run_industry_ai as script
    from collect.industry_ai import store

    class _NoClient:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(http, "build_client", lambda **k: _NoClient())
    monkeypatch.setattr(robots, "RobotsGate", lambda client, user_agent: None)
    asked = []

    def read_pictures(items, ocr_cfg, *, client, gate):
        asked.extend(it.id for it in items)
        return {items[0].id: ocr.PictureRead("ok", text=ABOUT_AI,
                                             confidence=tuple([90] * len(ABOUT_AI.split()))),
                **{it.id: ocr.PictureRead("refused") for it in items[1:]}}

    monkeypatch.setattr(ocr, "read_pictures", read_pictures)
    store.start_run(conn, "iai-o", mode="harvest", domains=[], platforms=["reddit"],
                    pipeline_version="test")
    fresh = [picture_post(None, iid="a", hours=1), picture_post(None, iid="b", hours=2)]
    store.upsert_items(conn, fresh, run_id="iai-o")
    conn.commit()
    items = store.load_items(conn)
    results, _ = evaluate(items, cfg, since=NOW - timedelta(days=90), now=NOW)
    store.write_labels(conn, results, pipeline_version="test")
    conn.commit()
    said = []
    line = script.read_picture_text(conn, cfg, fresh, items, results, said.append)
    conn.commit()
    assert sorted(asked) == ["reddit:a", "reddit:b"]
    rows = dict((r[0], (r[1], PICTURE_TEXT_FLAG in r[2])) for r in conn.execute(
        "SELECT id, ocr_status, flags FROM iai_item").fetchall())
    assert rows == {"reddit:a": ("ok", True), "reddit:b": ("refused", False)}
    assert "ok 1, refused 1" in line and "would pass 1" in line
    assert any("6b Picture text" in s and "refused 1" in s for s in said)


def test_ai_watch_counts_the_not_readable_pictures_by_status(conn, cfg):
    from collect.industry_ai import store
    from judge.industry_ai.view import ai_watch_view

    store.start_run(conn, "iai-o", mode="harvest", domains=[], platforms=["reddit"],
                    pipeline_version="test")
    posts = [picture_post(None, iid=i) for i in ("r", "t", "n")]
    store.upsert_items(conn, posts, run_id="iai-o")
    conn.execute("UPDATE iai_item SET verdict = 'dropped', drop_stage = 'unread', "
                 "drop_reason = 'media_unread'")
    store.write_picture_reads(conn, {"reddit:r": ocr.PictureRead("refused"),
                                     "reddit:t": ocr.PictureRead("ok", text="ChatGPT",
                                                                 confidence=(90,))},
                              {"reddit:t": [PICTURE_TEXT_FLAG]})
    conn.commit()
    w = ai_watch_view(conn)
    assert w["unread_pictures_by_read"] == {"refused": 1, "ok": 1, "not_tried": 1}
    assert w["unread_pictures_would_pass"] == 1
