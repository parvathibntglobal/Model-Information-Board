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
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import quote

ORDER_NOTE = ("Within each kind, newest first. Nothing is scored or ranked; "
              "a person picks.")
PRICE_KINDS = ("price_cut", "price_rise", "price_change")


def _n(count: int, one: str, many: str | None = None) -> str:
    return f"{count} {one if count == 1 else (many or one + 's')}"


def _model_path(paths: dict[str, str], model_id: str) -> str:
    parts = (quote(p, safe="") for p in model_id.split("/"))
    return paths["model"].format(model_path="/".join(parts))


def default_readers() -> dict[str, Callable[..., Any]]:
    from judge import news, updates, verdict

    return {
        "updates": lambda conn, days, now: updates.build(conn, days=days, now=now)["updates"],
        "news": lambda conn, days, now: news.news_view(conn, days=days, now=now)["items"],
        "verdict": lambda conn, model_id, today: verdict.verdict(conn, model_id, today=today),
    }


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
        evidence, people = [], 0
        for w in windows:
            bp = w.get("by_polarity") or {}
            people = max(people, w.get("people") or 0)
            # by_polarity counts posts with at least one report of that
            # polarity, so one post can be in two: say so rather than let the
            # three read as a split of the total (rule 7).
            evidence.append(
                f"{w['label']} ({w['from']} to {w['to']}): {_n(w.get('posts', 0), 'post')} "
                f"from {_n(w.get('people', 0), 'person', 'people')}; posts with a positive "
                f"report {bp.get('positive', {}).get('posts', 0)}, negative "
                f"{bp.get('negative', {}).get('posts', 0)}, neutral "
                f"{bp.get('neutral', {}).get('posts', 0)} (a post can carry more than one)")
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
                 "angle": " ".join(kind["angle"].split()), "items": []}
        try:
            sig = kind["signal"]
            if sig == "launches":
                items = _launches(board, s, paths)
            elif sig == "price_moves":
                items = _prices(board, s, paths, PRICE_KINDS)
            elif sig == "price_cuts":
                items = _prices(board, s, paths, ("price_cut",))
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
            else:
                raise BoardUnreadable(f"unknown signal {sig!r}")
            block["items"] = items[: s["max_per_kind"]]
            block["more"] = max(0, len(items) - s["max_per_kind"])
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
        "verdicts": (f"No launch in the last {w['verdicts']} days is at least "
                     f"{s['verdict_min_days']} days old."),
        "news": f"No unsponsored news in the last {w['news']} days.",
        "workspace_drafts": "No ready or posted draft to re-use yet.",
    }.get(signal, "Nothing to suggest.")
