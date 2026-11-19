"""The topic recommender: what to post about on one platform, from board data.

Coded, no model. For each topic kind a platform uses, it reads one board
source through the board's own functions (the same ones its pages use) and
lists items a person could write about, each with its evidence and links:

  launches       judge.updates.build, kind 'launch'
  price_moves    judge.updates.build, price kinds
  price_cuts     judge.updates.build, kind 'price_cut'
  verdicts       judge.updates.build launches, then judge.verdict.verdict
                 per model: posts and people by polarity per window
  news           judge.news.news_view, sponsored items left out
  week_summary   counts of the three above over 7 days
  workspace_drafts  this workspace's own drafts for another platform
  evergreen      no board data: the kind's angle and a link to a board page

It reads and never writes. Nothing is scored: items are newest first within
their kind, and the page says so. A source that cannot be read is reported
as unreadable, never as "nothing to suggest" (rule 4).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any
from urllib.parse import quote

from judge.content_workspace import recipes

ORDER_NOTE = ("Within each kind, newest first. Nothing is scored or ranked; "
              "a person picks.")
PRICE_KINDS = ("price_cut", "price_rise", "price_change")


def _n(count: int, one: str, many: str | None = None) -> str:
    return f"{count} {one if count == 1 else (many or one + 's')}"


def _model_path(paths: dict[str, str], model_id: str) -> str:
    parts = (quote(p, safe="") for p in model_id.split("/"))
    return paths["model"].format(model_path="/".join(parts))


MODEL_SQL = ("SELECT canonical_id, display_name, provider, release_date, price_in, price_out"
             " FROM model_version WHERE canonical_id = %s")
PRICE_NOT_LISTED = "Its price is not listed on the board."
FIND_SQL = ("SELECT canonical_id, display_name, release_date FROM model_version"
            " WHERE display_name ILIKE %s OR canonical_id ILIKE %s"
            " ORDER BY release_date DESC NULLS LAST, canonical_id LIMIT %s")


def _model(conn, model_id: str) -> dict | None:
    from judge.updates import launch_pricing

    row = conn.execute(MODEL_SQL, (model_id,)).fetchone()
    if row is None:
        return None
    # The board's own price sentence; a price not listed stays not listed
    # (rule 6: a NULL price is not free).
    return {"id": row[0], "name": row[1] or row[0], "provider": row[2],
            "release_date": row[3].isoformat() if row[3] else None,
            "price": launch_pricing(row[4], row[5]) or PRICE_NOT_LISTED}


def default_readers() -> dict[str, Callable[..., Any]]:
    from judge import news, updates, verdict

    return {
        "updates": lambda conn, days, now: updates.build(conn, days=days, now=now)["updates"],
        "news": lambda conn, days, now: news.news_view(conn, days=days, now=now)["items"],
        "verdict": lambda conn, model_id, today: verdict.verdict(conn, model_id, today=today),
        "week": lambda conn, model_id, start, today: verdict.week(conn, model_id, start,
                                                                  today=today),
        "model": _model,
        "split": _split_rows,
        "people": _model_people,
        "themes": _theme_rows,
    }


def _theme_rows(conn, model_id: str, start: date, end: date, sections: list[str],
                themes: dict[str, list[str]]) -> dict[str, dict[str, int]]:
    """Per pain theme, the model's counted people across ALL its slugs, each
    person once (a person reporting under two slugs of one theme is one person),
    and people per side. Counted as _split_rows counts."""
    from judge import publication
    from judge.verdict import COUNTED, POST_DAY

    out = {t: {"people": 0, "for": 0, "against": 0, "neutral": 0} for t in themes}
    row = conn.execute("SELECT id FROM model_version WHERE canonical_id = %s",
                       (model_id,)).fetchone()
    pairs = [(k, t) for t, keys in themes.items() for k in keys]
    if row is None or not pairs:
        return out
    clause, params = publication.sql_counted_document("be.document_id")
    join = ("JOIN (SELECT unnest(%s::text[]) AS k, unnest(%s::text[]) AS theme) m "
            "ON m.k = be.section || ':' || be.slug")
    where = (f"be.model_version_id = %s AND {COUNTED} AND {POST_DAY} BETWEEN %s AND %s "
             f"{clause}")
    args = ([k for k, _ in pairs], [t for _, t in pairs], row[0], sections, start, end, *params)
    base = f"FROM board_entry be JOIN document d ON d.id = be.document_id {join} WHERE {where}"
    for theme, n in conn.execute(
            f"SELECT m.theme, count(DISTINCT d.author_id) {base} GROUP BY 1", args).fetchall():
        out[theme]["people"] = n
    for theme, pol, n in conn.execute(
            f"SELECT m.theme, be.polarity, count(DISTINCT d.author_id) {base} GROUP BY 1, 2",
            args).fetchall():
        out[theme][{"positive": "for", "negative": "against"}.get(pol, "neutral")] += n
    return out


def _model_people(conn, model_id: str, start: date, end: date) -> dict[str, int]:
    """One model's counted reports from `start` to `end`: people (distinct
    authors) and posts, and people on each side. Counted as the model page
    counts them (judge/verdict.py COUNTED, POST_DAY and its sections,
    publication.sql_counted_document). A person can be on more than one side."""
    from judge import publication
    from judge.verdict import COUNTED, POST_DAY, counted_sections

    row = conn.execute("SELECT id FROM model_version WHERE canonical_id = %s",
                       (model_id,)).fetchone()
    out = {"people": 0, "posts": 0, "for": 0, "against": 0, "neutral": 0, "known": row is not None}
    if row is None:
        return out
    clause, params = publication.sql_counted_document("be.document_id")
    where = (f"be.model_version_id = %s AND {COUNTED} AND {POST_DAY} BETWEEN %s AND %s "
             f"{clause}")
    args = (row[0], counted_sections(), start, end, *params)
    out["people"], out["posts"] = conn.execute(
        f"SELECT count(DISTINCT d.author_id), count(DISTINCT d.id) FROM board_entry be "
        f"JOIN document d ON d.id = be.document_id WHERE {where}", args).fetchone()
    for pol, n in conn.execute(
            f"SELECT be.polarity, count(DISTINCT d.author_id) FROM board_entry be "
            f"JOIN document d ON d.id = be.document_id WHERE {where} GROUP BY 1", args).fetchall():
        out[{"positive": "for", "negative": "against"}.get(pol, "neutral")] += n
    return out


def _split_rows(conn, model_id: str, start: date, end: date,
                sections: list[str]) -> dict[str, Any]:
    """A model's counted reports from `start` to `end`, by capability or job and
    polarity: distinct authors (people) and posts. Counted as public counts are
    (judge/verdict.py COUNTED and POST_DAY, publication.sql_counted_document)."""
    from judge import publication
    from judge.verdict import COUNTED, POST_DAY

    row = conn.execute("SELECT id FROM model_version WHERE canonical_id = %s",
                       (model_id,)).fetchone()
    if row is None:
        return {"rows": [], "people": 0, "posts": 0, "people_by_name": {}}
    mv = row[0]
    clause, params = publication.sql_counted_document("be.document_id")
    where = (f"be.model_version_id = %s AND {COUNTED} AND {POST_DAY} BETWEEN %s AND %s "
             f"{clause}")
    args = (mv, sections, start, end, *params)
    # Grouped on the board's identifier (section and slug), not on the display
    # name: two spellings of one name are one capability only if the board says
    # so (rule 10). The name shown is the most common spelling's first.
    key = "be.section || ':' || be.slug"
    rows = conn.execute(
        f"SELECT {key}, min(be.name), min(be.section), be.polarity, "
        f"       count(DISTINCT d.author_id), count(DISTINCT d.id) "
        f"FROM board_entry be JOIN document d ON d.id = be.document_id WHERE {where} "
        f"GROUP BY 1, 4", args).fetchall()
    by_name = dict(conn.execute(
        f"SELECT {key}, count(DISTINCT d.author_id) "
        f"FROM board_entry be JOIN document d ON d.id = be.document_id WHERE {where} "
        f"GROUP BY 1", args).fetchall())
    people, posts = conn.execute(
        f"SELECT count(DISTINCT d.author_id), count(DISTINCT d.id) "
        f"FROM board_entry be JOIN document d ON d.id = be.document_id WHERE {where}",
        args).fetchone()
    return {"rows": [{"key": r[0], "name": r[1], "section": r[2], "polarity": r[3],
                      "people": r[4], "posts": r[5]} for r in rows],
            "people": people, "posts": posts, "people_by_name": by_name}


PRICE_UNREADABLE = "Its price could not be read."


def _price(board: _Board, model_id: str) -> str:
    """The model's listed price sentence. Supporting detail: a failed lookup
    says so on the item instead of making the whole kind unreadable."""
    try:
        return (board.read("model", model_id) or {}).get("price") or PRICE_UNREADABLE
    except BoardUnreadable:
        return PRICE_UNREADABLE


def _counts_line(label: str, w: dict[str, Any]) -> str:
    """One period's counts in words. by_polarity counts posts with at least one
    report of that polarity, so one post can be in two: say so rather than let
    the three read as a split of the total (rule 7)."""
    bp = w.get("by_polarity") or {}
    return (f"{label}: {_n(w.get('posts', 0), 'post')} from "
            f"{_n(w.get('people', 0), 'person', 'people')}; posts with a positive report "
            f"{bp.get('positive', {}).get('posts', 0)}, negative "
            f"{bp.get('negative', {}).get('posts', 0)}, neutral "
            f"{bp.get('neutral', {}).get('posts', 0)} (a post can carry more than one)")


def sample(largest_period_people: int, s: dict[str, Any]) -> dict[str, Any]:
    """The sample-size label: the busiest single period's people (never a sum
    across periods) against `recommender.small_sample_people`."""
    limit = s["recommender"]["small_sample_people"]
    small = 0 < largest_period_people < limit
    return {"largest_period_people": largest_period_people, "small": small,
            "note": (f"Small sample: at most {_n(largest_period_people, 'person', 'people')} "
                     "reported in any one period. Say so in the post." if small else None)}


def _proof(said: dict | None, per_side: int, period: str) -> list[dict[str, Any]]:
    """The board's paraphrased reports as proof. Each is the evidence feed's
    paraphrase (code-checked; never the user's own words). Its source LINK is
    dropped on purpose: a post links to the model page, never to the post
    (anooj, 2026-11-17); only the platform's name is kept."""
    out = []
    for side in ("positive", "negative"):
        for r in ((said or {}).get(side) or [])[:per_side]:
            src = r.get("source") if isinstance(r.get("source"), dict) else {}
            out.append({"side": side, "text": r["text"], "on": list(r.get("on") or []),
                        "date": (r.get("at") or "")[:10] or None,
                        "platform": src.get("platform"), "period": period})
    return out


class _Board:
    """Reads each board source once per request, and remembers a failure."""

    def __init__(self, conn: Any, readers: dict[str, Callable[..., Any]], now: datetime,
                 error: str | None = None):
        self.conn, self.readers, self.now, self.error = conn, readers, now, error
        self.cache: dict[tuple, Any] = {}

    def read(self, name: str, *args: Any) -> Any:
        if self.conn is None:
            raise BoardUnreadable(self.error or "the board database is not connected")
        key = (name, *args)
        if key not in self.cache:
            try:
                self.cache[key] = ("ok", self.readers[name](self.conn, *args))
            except Exception as e:  # noqa: BLE001 - reported per kind, never as "nothing"
                rollback = getattr(self.conn, "rollback", None)
                if rollback:
                    rollback()
                self.cache[key] = ("error", f"{type(e).__name__}: {e}")
        state, value = self.cache[key]
        if state == "error":
            raise BoardUnreadable(value)
        return value


class BoardUnreadable(RuntimeError):
    pass


def _story_item(u: dict[str, Any], paths: dict[str, str], extra_link: tuple | None) -> dict:
    style = (u.get("styles") or [{}])[0]
    links = [{"label": "Model page", "path": _model_path(paths, m)} for m in u["models"][:3]]
    if extra_link:
        links.append({"label": extra_link[0], "path": paths[extra_link[1]]})
    return {
        "id": f"update:{u['key']}",
        "headline": style.get("headline") or u.get("label"),
        "detail": style.get("detail"),
        "date": u["date"],
        "evidence": [f"{u.get('label', u['kind'])} on {u['date']}"]
                    + ([u["why"]] if u.get("why") else []),
        "links": links,
        "models": u["models"],
        "ready": True,
    }


def _launches(board: _Board, s: dict, paths: dict) -> list[dict]:
    rows = board.read("updates", s["window_days"]["launches"], board.now)
    return [_story_item(u, paths, ("Updates", "updates")) for u in rows if u["kind"] == "launch"]


def _prices(board: _Board, s: dict, paths: dict, kinds: tuple[str, ...]) -> list[dict]:
    rows = board.read("updates", s["window_days"]["price_moves"], board.now)
    return [_story_item(u, paths, ("Price changelog", "price_changes"))
            for u in rows if u["kind"] in kinds]


def _retirements(board: _Board, s: dict, paths: dict) -> list[dict]:
    rows = board.read("updates", s["window_days"]["retirements"], board.now)
    return [_story_item(u, paths, ("Updates", "updates")) for u in rows if u["kind"] == "retiring"]


#: Signals whose items are calendar events, joined to the board's evidence.
EVENT_SIGNALS = ("launches", "price_moves", "price_cuts", "retirements")


def _add_evidence(board: _Board, item: dict[str, Any], s: dict, signal: str) -> None:
    """Join a calendar item (topic selection B) to the board's evidence on its
    models: people in the `evidence_days` to today, and since the event. An
    event nobody reported on stays listed and SAYS so (rule 4, rule 8): it is a
    calendar item only, never silently a story. A read that fails says that,
    not "nobody" (rule 6)."""
    today = board.now.date()
    days = s["evidence_days"]
    since = date.fromisoformat(item["date"]) if item.get("date") else None
    window_start = today - timedelta(days=days - 1)
    lines, total, unreadable = [], 0, False
    for m in item["models"][:3]:
        try:
            ev = board.read("people", m, window_start, today)
            after = (board.read("people", m, since, today)
                     if since and since <= today else None)
            name = (board.read("model", m) or {}).get("name") or m
        except BoardUnreadable as e:
            unreadable = True
            lines.append(f"Board, {m}: its reports could not be read ({e}).")
            continue
        if not ev["known"]:
            lines.append(f"Board, {m}: not in the board's registry, so no reports are counted.")
            continue
        total += ev["people"]
        if not ev["people"]:
            lines.append(f"Board, {name}: nobody reported on it in the {days} days to {today}.")
            continue
        line = (f"Board, {name}: {ev['people']} people in the {days} days to {today} "
                f"({ev['for']} for, {ev['against']} against, {ev['neutral']} neutral; one "
                f"person can be on more than one side)")
        if after is not None:
            line += f"; {after['people']} of them since {since}"
        lines.append(line + ".")
    item["evidence"] = list(item["evidence"]) + lines
    if not total and not unreadable and item["models"]:
        item["no_reports"] = (
            f"No reports on the board yet since the launch on {item['date']}."
            if signal == "launches" else
            f"No reports on the board for this model in the last {days} days: a calendar "
            f"item only. Say so, or skip it.")


def _verdicts(board: _Board, s: dict, paths: dict) -> list[dict]:
    today = board.now.date()
    rows = board.read("updates", s["window_days"]["verdicts"], board.now)
    seen: dict[str, str] = {}
    for u in rows:
        if u["kind"] != "launch":
            continue
        for m in u["models"]:
            seen.setdefault(m, u["date"])
    young = [m for m, d in seen.items()
             if (today - date.fromisoformat(d)).days >= s["verdict_min_days"]]
    young.sort(key=lambda m: seen[m], reverse=True)
    out = []
    for m in young[: s["verdict_max_models"]]:
        v = board.read("verdict", m, today)
        if not v.get("model"):
            continue
        windows = [w for w in (v.get("windows") or []) if w.get("state") != "not_yet"]
        evidence, people, proof = [], 0, []
        for w in windows:
            people = max(people, w.get("people") or 0)
            evidence.append(_counts_line(f"{w['label']} ({w['from']} to {w['to']})", w))
            proof += _proof(w.get("said"), s["proof_per_window_per_side"], w["label"])
        name = v["model"]["name"]
        item = {
            "id": f"verdict:{m}",
            "headline": f"{name}: what engineers reported since release",
            "detail": f"Released {v['model'].get('release_date')}; "
                      f"{v.get('days_since_release')} days ago.",
            "date": seen[m],
            "evidence": evidence or ["No window has started yet."],
            "links": [{"label": "Model page", "path": _model_path(paths, m)}],
            "models": [m],
            "proof": proof,
            "price": _price(board, m),
            "sample": sample(people, {"recommender": s}),
            "ready": people > 0,
        }
        if people == 0:
            item["why_not_ready"] = ("Nobody has reported on it yet. Wait, or say that "
                                     "nobody has reported yet: silence is not praise.")
        out.append(item)
    return out


def _news(board: _Board, s: dict, paths: dict) -> list[dict]:
    rows = board.read("news", s["window_days"]["news"], board.now)
    out = []
    for n in rows:
        if n.get("sponsored"):
            continue
        summary = " ".join((n.get("summary") or "").split())
        out.append({
            "id": f"news:{n['id']}",
            "headline": n["title"],
            "detail": summary[:280] + ("…" if len(summary) > 280 else ""),
            "date": (n.get("published_at") or n["first_seen_at"])[:10],
            "evidence": [f"From {n['source_key']}"
                         + (f", {n['daily_count']} stories from it that day"
                            if n.get("daily_count") else "")],
            "links": [{"label": "Source", "url": n["url"]},
                      {"label": "On the board", "path": paths["news"].format(id=n["id"])}],
            "models": [],
            "ready": True,
        })
    return out


def _week(board: _Board, s: dict, paths: dict) -> list[dict]:
    rows = board.read("updates", 7, board.now)
    news_rows = board.read("news", 7, board.now)
    launches = sum(u["kind"] == "launch" for u in rows)
    prices = sum(u["kind"] in PRICE_KINDS for u in rows)
    news_n = sum(not n.get("sponsored") for n in news_rows)
    return [{
        "id": f"week:{board.now.date().isoformat()}",
        "headline": f"The week to {board.now.date().isoformat()}",
        "detail": "Pick the 5-10 that matter from these.",
        "date": board.now.date().isoformat(),
        "evidence": [f"{launches} launch updates, {prices} price updates "
                     f"(the board's Updates list, 7 days)",
                     f"{news_n} news items, sponsored ones left out (7 days)"],
        "links": [{"label": "Updates", "path": paths["updates"]},
                  {"label": "Price changelog", "path": paths["price_changes"]}],
        "models": [],
        "ready": launches + prices + news_n > 0,
    }]


def _workspace(drafts: list[dict], kind: dict) -> list[dict]:
    out = []
    for d in drafts:
        if d["platform_key"] != kind["from_platform"] or d["status"] not in ("ready", "posted"):
            continue
        first = (d.get("title") or (d.get("body") or "").strip().split("\n")[0])[:120]
        out.append({
            "id": f"draft:{d['id']}",
            "headline": first or f"Draft {d['id']}",
            "detail": f"{d['status'].capitalize()} on {kind['from_platform']}, format "
                      f"{d['format']}.",
            "date": (d.get("posted_at") or d["updated_at"])[:10],
            "evidence": [f"Workspace draft {d['id']}"],
            "links": ([{"label": "Posted", "url": d["posted_url"]}] if d.get("posted_url")
                      else []),
            "models": [],
            "ready": True,
            "from_draft": d["id"],
        })
    return out


def _evergreen(kind_key: str, kind: dict, paths: dict) -> list[dict]:
    link = kind.get("link")
    return [{
        "id": f"evergreen:{kind_key}",
        "headline": kind["label"],
        "detail": kind["angle"].strip(),
        "date": None,
        "evidence": ["Not tied to today's board data."],
        "links": [{"label": "Board page", "path": paths[link]}] if link else [],
        "models": [],
        "ready": True,
    }]


def suggestions(board_conn: Any, p: dict[str, Any], settings: dict[str, Any], *,
                workspace_drafts: list[dict] | None = None, now: datetime | None = None,
                readers: dict[str, Callable[..., Any]] | None = None,
                board_error: str | None = None) -> dict[str, Any]:
    """Suggestions for platform `p`, one block per topic kind it uses.
    `board_conn` None (with `board_error` saying why) marks every board-backed
    kind unreadable; kinds that need no board data still show."""
    now = now or datetime.now(UTC)
    s = settings["recommender"]
    paths = settings["site"]["paths"]
    kinds = settings["topic_kinds"]
    board = _Board(board_conn, readers or default_readers(), now, board_error)
    blocks = []
    for key in p["topic_kinds"]:
        kind = kinds.get(key)
        if kind is None:
            blocks.append({"kind": key, "label": key, "items": [], "unreadable": True,
                           "note": f"{key!r} is not defined in workspace.yaml topic_kinds"})
            continue
        block = {"kind": key, "label": kind["label"], "signal": kind["signal"],
                 "angle": " ".join(kind["angle"].split()), "items": [],
                 "recipe": recipes.for_block(settings, p["key"], key)}
        try:
            sig = kind["signal"]
            if sig == "launches":
                items = _launches(board, s, paths)
            elif sig == "price_moves":
                items = _prices(board, s, paths, PRICE_KINDS)
            elif sig == "price_cuts":
                items = _prices(board, s, paths, ("price_cut",))
            elif sig == "retirements":
                items = _retirements(board, s, paths)
            elif sig == "verdicts":
                items = _verdicts(board, s, paths)
            elif sig == "news":
                items = _news(board, s, paths)
            elif sig == "week_summary":
                items = _week(board, s, paths)
            elif sig == "workspace_drafts":
                items = _workspace(workspace_drafts or [], kind)
            elif sig == "evergreen":
                items = _evergreen(key, kind, paths)
            elif sig == "trajectory":
                # Built on request for the model a person picks
                # (`trajectory` below, GET /admin/content/trajectory), which
                # needs the board: without it, say so rather than offer a
                # picker that cannot work.
                if board.conn is None:
                    raise BoardUnreadable(board.error or "the board database is not connected")
                items = []
            else:
                raise BoardUnreadable(f"unknown signal {sig!r}")
            block["items"] = items[: s["max_per_kind"]]
            block["more"] = max(0, len(items) - s["max_per_kind"])
            if sig in EVENT_SIGNALS:
                for it in block["items"]:
                    _add_evidence(board, it, s, sig)
            if not items:
                block["note"] = _empty_note(sig, s)
        except BoardUnreadable as e:
            block["unreadable"] = True
            block["note"] = f"The board data for this could not be read: {e}"
        blocks.append(block)
    return {"platform": p["key"], "generated_at": now.isoformat(), "order": ORDER_NOTE,
            "kinds": blocks}


def _empty_note(signal: str, s: dict) -> str:
    w = s["window_days"]
    return {
        "launches": f"No launches on the board in the last {w['launches']} days.",
        "price_moves": f"No price updates in the last {w['price_moves']} days.",
        "price_cuts": f"No price cuts in the last {w['price_moves']} days.",
        "retirements": (f"No retirement among the board's updates for the last "
                        f"{w['retirements']} days."),
        "verdicts": (f"No launch in the last {w['verdicts']} days is at least "
                     f"{s['verdict_min_days']} days old."),
        "news": f"No unsponsored news in the last {w['news']} days.",
        "workspace_drafts": "No ready or posted draft to re-use yet.",
        "trajectory": "Pick a model to see it week by week.",
    }.get(signal, "Nothing to suggest.")


# ── a model's trajectory ─────────────────────────────────────────────────────


def find_models(board_conn: Any, q: str, settings: dict[str, Any]) -> list[dict[str, Any]]:
    q = (q or "").strip()
    if len(q) < 2:
        return []
    like = f"%{q}%"
    rows = board_conn.execute(
        FIND_SQL, (like, like, settings["trajectory"]["model_search_limit"])).fetchall()
    return [{"id": r[0], "name": r[1] or r[0],
             "release_date": r[2].isoformat() if r[2] else None} for r in rows]


class TrajectoryRequestError(ValueError):
    pass


def trajectory(board_conn: Any, model_id: str, settings: dict[str, Any], *,
               start: date | None = None, weeks: int | None = None,
               today: date | None = None,
               readers: dict[str, Callable[..., Any]] | None = None) -> dict[str, Any]:
    """One suggestion item: `model_id` week by week from `start` (its release
    date unless given), with each week's counts, most-named topics and
    paraphrased proof. A week with no reports says so (rule 4)."""
    t = settings["trajectory"]
    paths = settings["site"]["paths"]
    readers = readers or default_readers()
    today = today or datetime.now(UTC).date()
    weeks = t["weeks"] if weeks is None else int(weeks)
    if not 1 <= weeks <= t["max_weeks"]:
        raise TrajectoryRequestError(f"weeks must be between 1 and {t['max_weeks']}")
    m = readers["model"](board_conn, model_id.strip())
    if m is None:
        raise TrajectoryRequestError(f"no model {model_id!r} on the board")
    if start is None:
        if not m["release_date"]:
            raise TrajectoryRequestError(
                f"{m['name']} has no recorded release date; give a start date")
        start = date.fromisoformat(m["release_date"])
    if start > today:
        raise TrajectoryRequestError("the start date is in the future")

    evidence, proof, people_any, shown, busiest = [], [], 0, 0, 0
    for i in range(weeks):
        s = start + timedelta(days=7 * i)
        if s > today:
            break
        w = readers["week"](board_conn, m["id"], s, today)
        e = min(s + timedelta(days=6), today)
        label = f"Week {i + 1} ({s.isoformat()} to {e.isoformat()})"
        shown += 1
        if not w.get("people"):
            evidence.append(f"{label}: nobody reported on it.")
            continue
        people_any += w["people"]
        busiest = max(busiest, w["people"])
        line = _counts_line(label, w)
        tops = [tp for tp in (w.get("topics") or [])][: t["top_topics_per_week"]]
        if tops:
            line += ". Most named: " + "; ".join(
                f"{tp['name']} ({tp['positive']} positive, {tp['negative']} negative)"
                for tp in tops)
        evidence.append(line)
        proof += _proof(w.get("said"), t["proof_per_week_per_side"], f"Week {i + 1}")
    end = min(start + timedelta(days=7 * shown - 1), today)
    since_release = m["release_date"] and start.isoformat() == m["release_date"]
    item = {
        "id": f"trajectory:{m['id']}:{start.isoformat()}:{shown}",
        "headline": (f"{m['name']}: its first {_n(shown, 'week')} after release"
                     if since_release else
                     f"{m['name']}: {start.isoformat()} to {end.isoformat()}"),
        "detail": (f"Released {m['release_date'] or 'on an unrecorded date'}. "
                   f"{_n(shown, 'week')} of reports, {start.isoformat()} to {end.isoformat()}."
                   + (" The last week is still running." if end < start + timedelta(
                       days=7 * shown - 1) else "")),
        "date": start.isoformat(),
        "evidence": evidence,
        "links": [{"label": "Model page", "path": _model_path(paths, m["id"])}],
        "models": [m["id"]],
        "proof": proof,
        "price": m.get("price"),
        "sample": sample(busiest, settings),
        "ready": people_any > 0,
    }
    if not people_any:
        item["why_not_ready"] = ("Nobody reported on it in these weeks. Say so, or pick "
                                 "other weeks: silence is not praise.")
    return item


# ── a model's reports split by capability (topic selection A) ────────────────


def split_label(pos: int, neg: int) -> str:
    """The capability's label in words, from the people on each side. Never a
    score, and it hides nothing: the counts sit beside it (rule 3, rule 8).

    The two thresholds are the board's own, from E7 (judge/curate/gate.py), so
    "mixed" here means what "Mixed reports" means on a model page: under 3
    people taking a side is not yet corroborated, and a majority side under 70%
    of them is mixed. It is NOT the board's published consensus, which also
    weights evidence and needs two platforms; the page says so."""
    from judge.curate.gate import GENERALLY_PRAISED_VOICES, CellCounts, classify

    sided = pos + neg
    if sided == 0:
        return "discussed, no side taken"
    if sided < GENERALLY_PRAISED_VOICES:
        return "too few to say"
    agreement = CellCounts(positive=pos, negative=neg).agreement
    if agreement < classify.__kwdefaults__["dissent_threshold"]:
        return "mixed reports"
    return "mostly for" if pos > neg else "mostly against"


def capability_split(board_conn: Any, model_id: str, settings: dict[str, Any], *,
                     start: date | None = None, days: int | None = None,
                     today: date | None = None,
                     readers: dict[str, Callable[..., Any]] | None = None) -> dict[str, Any]:
    """`model_id`'s reports from `start` (its release date unless given) over
    `days`, by capability and job: people for, against and neutral on each,
    ordered by how many people reported on it. Reads only."""
    c = settings["capability_split"]
    paths = settings["site"]["paths"]
    readers = readers or default_readers()
    today = today or datetime.now(UTC).date()
    days = c["days"] if days is None else int(days)
    if not 1 <= days <= c["max_days"]:
        raise TrajectoryRequestError(f"days must be between 1 and {c['max_days']}")
    m = readers["model"](board_conn, model_id.strip())
    if m is None:
        raise TrajectoryRequestError(f"no model {model_id!r} on the board")
    if start is None:
        if not m["release_date"]:
            raise TrajectoryRequestError(
                f"{m['name']} has no recorded release date; give a start date")
        start = date.fromisoformat(m["release_date"])
    if start > today:
        raise TrajectoryRequestError("the start date is in the future")
    end = min(start + timedelta(days=days - 1), today)
    got = readers["split"](board_conn, m["id"], start, end, list(c["sections"]))

    caps: dict[str, dict[str, Any]] = {}
    for r in got["rows"]:
        # People per side only. Posts are not summed across sides: a post with a
        # positive and a negative report would count twice.
        cap = caps.setdefault(r["key"], {"name": r["name"], "section": r["section"],
                                         "for": 0, "against": 0, "neutral": 0})
        side = {"positive": "for", "negative": "against"}.get(r["polarity"], "neutral")
        cap[side] += r["people"]
    listed = []
    for key, cap in caps.items():
        cap["people"] = int(got["people_by_name"].get(key, 0))
        cap["label"] = split_label(cap["for"], cap["against"])
        listed.append(cap)
    listed.sort(key=lambda x: (-x["people"], x["name"].lower()))
    shown = listed[: c["top"]]

    # PAIN ANGLES (topic selection C): each theme's people on this model, in
    # this span, with its label from the same thresholds. A theme nobody
    # reported on is listed as such, never dropped (rule 4).
    angles_cfg = settings["pain_angles"]
    themes = readers["themes"](board_conn, m["id"], start, end, list(c["sections"]),
                               {a["key"]: list(a["slugs"]) for a in angles_cfg})
    angles = []
    for a in angles_cfg:
        n = themes[a["key"]]
        angles.append({"key": a["key"], "label": a["label"], "says": a["says"], "fit": a["fit"],
                       "people": n["people"], "for": n["for"], "against": n["against"],
                       "neutral": n["neutral"],
                       "in_words": ("nobody reported on it" if not n["people"]
                                    else split_label(n["for"], n["against"]))})
    angles.sort(key=lambda x: (-x["people"], x["label"].lower()))
    return {
        "model": m["id"], "name": m["name"],
        "start": start.isoformat(), "end": end.isoformat(),
        "still_running": end < start + timedelta(days=days - 1),
        "people": got["people"], "posts": got["posts"],
        "capabilities": shown, "more": len(listed) - len(shown),
        "order": ("Ordered by how many people reported on each capability or job. A person "
                  "can be on both sides of one, and can report on several, so the sides do "
                  "not add up to the people, and the rows do not add up to the total. The "
                  "labels use the board's thresholds (3 people taking a side; mixed below "
                  "70%) but are not its published consensus, which also weights the "
                  "evidence and needs two platforms."),
        "links": [{"label": "Model page", "path": _model_path(paths, m["id"])}],
        "empty": None if listed else ("Nobody reported on a capability or job of this model "
                                      "in this span. Silence is not praise."),
        "pain_angles": angles,
        "pain_not_counted": list(settings["pain_not_counted"]),
        "pain_note": ("Angles from the team's pain research, counted on the board: each theme "
                      "counts a person once across its capabilities. A theme's 'fit' says "
                      "whether the board counts the whole pain or part of it. The pains "
                      "listed as not counted have no board capability yet; their absence "
                      "here is not their absence."),
    }
