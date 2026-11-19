"""Specs for the media generators, built from the board. READ-ONLY.

Each approved look (workspace.yaml `looks`) has a generator in tools/media/
that renders a JSON spec into a carousel; this module writes those specs from
the board's data, through `python -m judge.content_workspace media-spec <look>`:

  field-report    one model's first weeks: people and posts per week, posts for
                  and against, and up to two restated reports
  data-card       one board label (section + slug) across models over a window
  evidence-board  one model's registry price history, its people for / against
                  / with no side, and report cards

COUNTED AS THE PUBLIC PAGES COUNT. judge/verdict.py COUNTED (no declined entry,
only the sections contract/verdict.yaml names) and POST_DAY (a post's UTC day),
with judge/publication.py `sql_counted_document` for totals. People are distinct
`document.author_id`; an entry with no author is an entry, not a person.

WITHHELD SOURCES ARE NEVER SPLIT OUT. A per-platform number shows a source, so
the data card's platform rows use `publication.sql_shown_document`: the people
who posted only on a withheld platform (contract/publication.yaml
`withheld_from_public`) are one "not named" row.

CARDS ARE THE EVIDENCE FEED'S PARAPHRASES (contract/publication.yaml
`evidence_feed`, proposed in #558): our stored restatement, never a post's
text; no link, handle or subreddit; a held source (`publication.feed_hides`)
is never carded. Whether such cards may appear on outward media is the #558
decision; a person looks at every card before any use.

Every limit a generator enforces is refused HERE first, with the reason, and a
person's words (headlines, notes) are never defaulted (rule 12). The database
reads are separate from the arithmetic so the tests need no database.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any

LOOKS = ("field-report", "data-card", "evidence-board")

PLATFORM_NAMES = {"x": "X", "reddit": "Reddit", "hackernews": "Hacker News", "bluesky": "Bluesky",
                  "devto": "dev.to", "github": "GitHub", "huggingface": "Hugging Face",
                  "forum": "Forum", "arxiv": "arXiv", "blog": "Blog"}


class MediaSpecError(ValueError):
    """A spec the generator would refuse, or one that would say something untrue."""


def platform_name(key: str | None) -> str:
    """The platform as a reader knows it. An unknown key refuses rather than
    printing a database id on a card (rule 12)."""
    try:
        return PLATFORM_NAMES[str(key).casefold()]
    except KeyError:
        raise MediaSpecError(f"no display name for platform {key!r}; add it to "
                             f"media_specs.PLATFORM_NAMES") from None


def display_name(registry_name: str) -> str:
    """'Anthropic: Claude Opus 5.5' -> 'Claude Opus 5.5'."""
    return re.sub(r"^[^:]+:\s*", "", registry_name).strip()


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9.]+", "-", text.lower()).strip("-")


# ── field report ────────────────────────────────────────────────────────────

FIELD_REPORT_WEEKS_MAX = 4


def field_report(conn: Any, model_id: str, settings: dict[str, Any], *, weeks: int = 4,
                 start: date | None = None, today: date | None = None,
                 readers: dict[str, Callable[..., Any]] | None = None) -> dict[str, Any]:
    """One model's complete weeks from its release (or `start`), through the
    workspace's own week reader, so the figures are the ones the workspace's
    trajectory suggestion shows."""
    from judge.content_workspace import recommend

    if not 1 <= weeks <= FIELD_REPORT_WEEKS_MAX:
        raise MediaSpecError(f"a field-report carousel shows 1 to {FIELD_REPORT_WEEKS_MAX} "
                             f"weeks, not {weeks}")
    readers = readers or recommend.default_readers()
    today = today or datetime.now(UTC).date()
    m = readers["model"](conn, model_id)
    if m is None:
        raise MediaSpecError(f"no model {model_id!r} on the board")
    if start is None and not m["release_date"]:
        raise MediaSpecError(f"{m['name']} has no recorded release date; give a start date")
    start = start or date.fromisoformat(m["release_date"])

    out_weeks, said_by_week = [], []
    for i in range(weeks):
        ws = start + timedelta(days=7 * i)
        we = ws + timedelta(days=6)
        if we > today:
            raise MediaSpecError(f"week {i + 1} ({ws} to {we}) is still running on {today}; "
                                 f"ask for {i} week(s) so every week shown is complete")
        w = readers["week"](conn, m["id"], ws, today)
        bp = w.get("by_polarity") or {}
        out_weeks.append({"from": ws.isoformat(), "to": we.isoformat(),
                          "people": int(w.get("people") or 0), "posts": int(w.get("posts") or 0),
                          "pos": int(bp.get("positive", {}).get("posts", 0)),
                          "neg": int(bp.get("negative", {}).get("posts", 0))})
        said_by_week.append(recommend._proof(w.get("said"), 1, f"Week {i + 1}"))

    # Page III: the first positive and the first negative restated report, by week.
    proofs = []
    for side in ("positive", "negative"):
        for i, items in enumerate(said_by_week):
            hit = next((p for p in items if p["side"] == side and p["date"] and p["platform"]),
                       None)
            if hit:
                proofs.append({"side": side, "week": i + 1,
                               "platform": platform_name(hit["platform"]),
                               "date": hit["date"], "text": hit["text"]})
                break
    proofs.sort(key=lambda p: p["week"])

    name = display_name(m["name"])
    return {
        "topic": "model_trajectory",
        "file_slug": name,
        "source": f"board database, read-only; workspace week reader; read {today.isoformat()}",
        "title": name,
        "subtitle": "in the hands of engineers, week by week",
        "path": recommend._model_path(settings["site"]["paths"], m["id"]),
        "release_date": m["release_date"] or start.isoformat(),
        "start": start.isoformat(),
        "read_on": today.isoformat(),
        "weeks": out_weeks,
        "proofs": proofs,
    }


# ── data card ───────────────────────────────────────────────────────────────

DATA_CARD_ROWS_MAX, DATA_CARD_SOURCES_MAX = 8, 8
DATA_CARD_TEXT_KEYS = ("headline", "sides", "page2_head", "page2_note", "not_a_measurement",
                       "path")


def data_card_window(days: int, to: date | None, today: date,
                     allow_running: bool = False) -> tuple[date, date, bool]:
    """(from, to, running). `to` is the last day counted, by default yesterday
    (UTC). A window not over yet is refused unless `allow_running`, which only
    exists to reproduce a spec read on its own last day, and says so."""
    if days < 1:
        raise MediaSpecError("days must be at least 1")
    to = to or today - timedelta(days=1)
    frm = to - timedelta(days=days)
    running = to >= today
    if running and not allow_running:
        raise MediaSpecError(f"the window {frm} to {to} is still running on {today}: its counts "
                             f"can still grow. Use a last day of {today - timedelta(days=1)} "
                             f"or earlier")
    return frm, to, running


def data_card_rows(conn: Any, section: str, slug: str, frm: date, to: date) -> dict[str, Any]:
    """The rows a data card counts, read as public pages read them."""
    from judge import publication, verdict

    sections = verdict.counted_sections()
    read_at = conn.execute("SELECT now()").fetchone()[0]
    names = conn.execute(
        "SELECT be.name, count(*) FROM board_entry be WHERE be.section = %s AND be.slug = %s "
        "GROUP BY 1 ORDER BY 2 DESC", (section, slug)).fetchall()
    counted, cparams = publication.sql_counted_document("be.document_id")
    shown, sparams = publication.sql_shown_document("be.document_id")
    where = (f"WHERE {verdict.COUNTED} AND be.section = %s AND be.slug = %s "
             f"AND {verdict.POST_DAY} BETWEEN %s AND %s")
    base = [sections, section, slug, frm, to]
    rows = conn.execute(
        f"""SELECT mv.id, mv.display_name, be.polarity, d.author_id, d.source
              FROM board_entry be JOIN document d ON d.id = be.document_id
              JOIN model_version mv ON mv.id = be.model_version_id {where} {counted}""",
        [*base, *cparams]).fetchall()
    shown_rows = conn.execute(
        f"""SELECT d.source, d.author_id
              FROM board_entry be JOIN document d ON d.id = be.document_id
            {where} {shown}""", [*base, *sparams]).fetchall()
    return {"names": names, "rows": rows, "shown_rows": shown_rows, "read_at": read_at}


def data_card_from_rows(slug: str, section: str, text: dict[str, Any], frm: date, to: date,
                        today: date, got: dict[str, Any]) -> dict[str, Any]:
    """The data card spec from `data_card_rows`' output. No database."""
    missing = [k for k in DATA_CARD_TEXT_KEYS if k not in text]
    if missing:
        raise MediaSpecError(f"the text is missing {missing}: a person writes these; there is no "
                             f"default (rule 12)")
    names, rows, shown_rows = got["names"], got["rows"], got["shown_rows"]
    if not names:
        raise MediaSpecError(f"no board entry is filed under {section}/{slug}: the label is "
                             f"spelled whole (rule 10)")

    people = {au for *_, au, _s in rows if au}
    side = {p: {au for _i, _n, pol, au, _s in rows if au and pol == p}
            for p in ("negative", "positive")}
    per: dict[Any, dict[str, Any]] = {}
    for mid, name, pol, au, _src in rows:
        m = per.setdefault(mid, {"name": display_name(name), "people": set(),
                                 "negative": set(), "positive": set()})
        if au:
            m["people"].add(au)
            if pol in ("negative", "positive"):
                m[pol].add(au)
    # A model whose entries all lack an author has no person, so no row.
    models = [m for m in per.values() if m["people"]]
    # Most people first; ties by name (a count orders, nothing else does).
    models.sort(key=lambda m: (-len(m["people"]), m["name"].casefold()))
    row_out = [{"model": m["name"], "people": len(m["people"]), "negative": len(m["negative"]),
                "positive": len(m["positive"])} for m in models[:DATA_CARD_ROWS_MAX]]
    rest = models[DATA_CARD_ROWS_MAX:]
    rest_out = {"models": len(rest),
                "people_min": min((len(m["people"]) for m in rest), default=0),
                "people_max": max((len(m["people"]) for m in rest), default=0),
                "negative": sum(len(m["negative"]) for m in rest),
                "positive": sum(len(m["positive"]) for m in rest),
                "neither": sum(len(m["people"] - m["negative"] - m["positive"]) for m in rest)}

    shown_people: dict[str, set] = {}
    for src, au in shown_rows:
        if au:
            shown_people.setdefault(src, set()).add(au)
    sources = sorted(({"platform": platform_name(s), "people": len(v)}
                      for s, v in shown_people.items()),
                     key=lambda x: (-x["people"], x["platform"].casefold()))
    seen = set().union(*shown_people.values()) if shown_people else set()
    not_named_people = people - seen
    not_named_platforms = {s for *_, au, s in rows if au in not_named_people and s}
    nn = {"people": len(not_named_people), "platforms": len(not_named_platforms)}
    if len(sources) + (1 if nn["people"] else 0) > DATA_CARD_SOURCES_MAX:
        raise MediaSpecError(f"{len(sources)} named platforms plus a not-named row: page 3 "
                             f"holds {DATA_CARD_SOURCES_MAX}")

    topic = text.get("topic") or names[0][0]
    read_at = got["read_at"]
    return {
        "slug": slug,
        "topic": topic,
        "filed_under": text.get("filed_under") or topic.lower(),
        "path": text["path"],
        "window": {"from": frm.isoformat(), "to": to.isoformat()},
        "read_on": today.isoformat(),
        "population": (f"board_entry {section}/{slug} (board name {names[0][0]!r}), counted as "
                       f"public pages count (judge.verdict COUNTED + POST_DAY, "
                       f"publication.sql_counted_document), posts dated {frm} to {to} UTC; "
                       f"people = distinct document.author_id; per-platform people via "
                       f"publication.sql_shown_document. Read {read_at:%Y-%m-%d %H:%MZ}"),
        "headline": text["headline"],
        "sides": text["sides"],
        "totals": {"people": len(people), "negative": len(side["negative"]),
                   "positive": len(side["positive"]), "models": len(models),
                   "entries": len(rows), "no_author_entries": sum(1 for r in rows if not r[3])},
        "rows": row_out,
        "rest": rest_out,
        "sources": sources,
        "sources_not_named": nn,
        "page2_head": text["page2_head"],
        "page2_note": text["page2_note"],
        "page3_head": text.get("page3_head") or ["{platforms_word} platforms,", "one subject"],
        "not_a_measurement": text["not_a_measurement"],
    }


def data_card(conn: Any, slug: str, text: dict[str, Any], *, section: str = "capability",
              days: int = 30, to: date | None = None, allow_running: bool = False,
              today: date | None = None) -> dict[str, Any]:
    from judge import verdict

    today = today or datetime.now(UTC).date()
    sections = verdict.counted_sections()
    if section not in sections:
        raise MediaSpecError(f"section {section!r} is not counted on public pages "
                             f"(contract/verdict.yaml: {sections})")
    frm, to, _running = data_card_window(days, to, today, allow_running)
    return data_card_from_rows(slug, section, text, frm, to, today,
                               data_card_rows(conn, section, slug, frm, to))


# ── evidence board ──────────────────────────────────────────────────────────

EB_CARDS_MAX, EB_CARD_CHARS, EB_PRICES_MAX, EB_PINS_MAX = 6, 160, 5, 40
EB_CARD_CAPTION = "Listed price per 1M tokens, as the board's registry recorded it"
EB_TEXT_KEYS = {"kicker", "note", "cards_head", "page3_head", "card_documents"}
_WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
_MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _day(d: date) -> str:
    return f"{d.day} {_MON[d.month - 1]}"


def evidence_board_rows(conn: Any, model_id: str) -> dict[str, Any]:
    """The rows an evidence board counts, read as public pages read them."""
    from judge import publication, verdict

    read_at = conn.execute("SELECT now()").fetchone()[0]
    mv = conn.execute("SELECT id, display_name FROM model_version WHERE canonical_id = %s",
                      (model_id,)).fetchone()
    if mv is None:
        return {"model": None, "read_at": read_at}
    counted, cparams = publication.sql_counted_document("be.document_id")
    sections = verdict.counted_sections()
    prices = conn.execute(
        "SELECT occurred_at, payload FROM model_event WHERE model_version_id = %s "
        "AND type = 'price-change' ORDER BY occurred_at", (mv[0],)).fetchall()
    people = conn.execute(
        f"""SELECT be.polarity, d.author_id, {verdict.POST_DAY}
              FROM board_entry be JOIN document d ON d.id = be.document_id
             WHERE be.model_version_id = %s AND {verdict.COUNTED} {counted}""",
        [mv[0], sections, *cparams]).fetchall()
    cards = conn.execute(
        f"""SELECT fp.document_id, fp.text, d.source, {verdict.POST_DAY},
                   array_agg(DISTINCT be.polarity || '|' || be.slug)
              FROM feed_paraphrase fp JOIN document d ON d.id = fp.document_id
              JOIN board_entry be ON be.document_id = fp.document_id
                                 AND be.model_version_id = fp.model_version_id
             WHERE fp.model_version_id = %s AND {verdict.COUNTED}
               AND be.polarity IN ('positive', 'negative') {counted}
             GROUP BY 1, 2, 3, 4""", [mv[0], sections, *cparams]).fetchall()
    return {"model": mv, "prices": prices, "people": people, "cards": cards, "read_at": read_at}


def _label_in_text(label: str, txt: str) -> bool:
    """Whether a label's words appear in the text: a word of 4+ letters, or its
    first five letters (quantization ~ quantize). A heuristic, said as one: a
    person checks every card."""
    low = txt.casefold()
    return any(w in low or (len(w) > 5 and w[:5] in low) for w in label.split() if len(w) >= 4)


def evidence_board_from_rows(model_id: str, got: dict[str, Any], settings: dict[str, Any], *,
                             cards: int = 6, text: dict[str, Any] | None = None) -> dict[str, Any]:
    """The evidence board spec from `evidence_board_rows`' output. No database."""
    from judge import publication
    from judge.content_workspace import recommend

    if not 1 <= cards <= EB_CARDS_MAX:
        raise MediaSpecError(f"cards is 1 to {EB_CARDS_MAX}: page 2 holds {EB_CARDS_MAX}")
    text = text or {}
    unknown = set(text) - EB_TEXT_KEYS
    if unknown:
        raise MediaSpecError(f"the text has keys the builder does not read: {sorted(unknown)}")
    if got["model"] is None:
        raise MediaSpecError(f"no model {model_id!r} on the board")
    mv_id, name = got["model"][0], display_name(got["model"][1])
    read_at = got["read_at"]
    today = read_at.astimezone(UTC).date()

    prices = []
    for occurred, payload in got["prices"]:
        f, t = payload.get("from") or {}, payload.get("to") or {}
        try:
            prices.append({"date": occurred.astimezone(UTC).date().isoformat(),
                           "input_from": round(float(f["price_in"]), 6),
                           "input_to": round(float(t["price_in"]), 6),
                           "output_from": round(float(f["price_out"]), 6),
                           "output_to": round(float(t["price_out"]), 6)})
        except (KeyError, TypeError, ValueError):
            raise MediaSpecError(f"the price event of {occurred} lacks an input or output price; "
                                 f"a missing price is not 0 (rule 6)") from None
    if not prices:
        raise MediaSpecError(f"{name} has no price change in the registry: the evidence board's "
                             f"case card is a price history")
    if len(prices) > EB_PRICES_MAX:
        raise MediaSpecError(f"{name} has {len(prices)} price changes; the case card holds "
                             f"{EB_PRICES_MAX}")
    for i in range(1, len(prices)):
        p, q = prices[i - 1], prices[i]
        if (q["input_from"], q["output_from"]) != (p["input_to"], p["output_to"]):
            raise MediaSpecError(f"the {q['date']} change does not start where the {p['date']} "
                                 f"one ended: a change is missing from the registry, and the "
                                 f"table would show a jump")

    def direction(p: dict[str, Any]) -> str:
        a_, b_ = ((p["input_from"], p["input_to"]) if p["input_from"] != p["input_to"]
                  else (p["output_from"], p["output_to"]))
        return "cut" if b_ < a_ else "rise" if b_ > a_ else "change"

    rows = got["people"]
    if not rows:
        raise MediaSpecError(f"{name} has no counted report on the board")
    authors = {au for _p, au, _d in rows if au}
    by = {k: {au for p, au, _d in rows if au and p == k}
          for k in ("positive", "negative", "neutral")}
    for k, label in (("positive", "for"), ("negative", "against"), ("neutral", "neither")):
        if len(by[k]) > EB_PINS_MAX:
            raise MediaSpecError(f"{len(by[k])} people {label}: a pin row holds {EB_PINS_MAX}")
    first_post, last_post = min(d for *_, d in rows), max(d for *_, d in rows)
    last_change = date.fromisoformat(prices[-1]["date"])
    since = {au for _p, au, d in rows if au and d >= last_change}
    word = direction(prices[-1])
    span_days = (last_change - date.fromisoformat(prices[0]["date"])).days
    weeks = round(span_days / 7)
    if len(prices) == 1:
        changes_label = "price change the registry recorded"
    elif weeks >= 1:
        n = _WORDS[weeks] if weeks < len(_WORDS) else weeks
        changes_label = f"price changes the registry recorded in {n} weeks"
    else:
        changes_label = f"price changes the registry recorded in {span_days} days"

    skipped = {"held": 0, "arxiv": 0, "long": 0, "unmatched": 0}
    pool = []
    for did, txt, src, d, ents in got["cards"]:
        if publication.feed_hides(src):
            skipped["held"] += 1
            continue
        if src == "arxiv":
            skipped["arxiv"] += 1
            continue
        if len(txt) > EB_CARD_CHARS:
            skipped["long"] += 1
            continue
        labels = [(e.split("|", 1)[0], e.split("|", 1)[1].replace("-", " ")) for e in ents]
        hit = next(((pol, lab) for pol, lab in labels if _label_in_text(lab, txt)), None)
        pool.append({"id": did, "text": txt, "source": src, "date": d, "hit": hit,
                     "labels": labels})

    pinned = text.get("card_documents")
    chosen: list[tuple[str, str, dict[str, Any]]] = []
    if pinned:
        by_id = {c["id"]: c for c in pool}
        for did in pinned:
            c = by_id.get(did)
            if c is None:
                raise MediaSpecError(
                    f"card document {did} is not a cardable stored paraphrase of {name} (held, "
                    f"arXiv, over {EB_CARD_CHARS} characters, or no counted positive or negative "
                    f"entry)")
            pol, lab = c["hit"] or c["labels"][0]
            chosen.append((pol, lab, c))
        why = f"{len(chosen)} card(s) chosen by a person (card_documents)"
    else:
        sides: dict[str, list[dict[str, Any]]] = {}
        for c in sorted((c for c in pool if c["hit"]), key=lambda c: (c["date"], c["id"]),
                        reverse=True):
            sides.setdefault(c["hit"][0], []).append(c)
        skipped["unmatched"] = sum(1 for c in pool if not c["hit"])
        half = cards // 2
        take = {"positive": sides.get("positive", [])[:cards - half],
                "negative": sides.get("negative", [])[:half]}
        # A short side gives its room to the other, up to what that side has.
        for k, o in (("positive", "negative"), ("negative", "positive")):
            room = cards - len(take[k]) - len(take[o])
            if room > 0:
                take[o] = sides.get(o, [])[:len(take[o]) + room]
        order = []
        for i in range(cards):
            for k in ("positive", "negative"):
                if i < len(take[k]):
                    order.append((k, take[k][i]["hit"][1], take[k][i]))
        chosen = order[:cards]
        why = (f"{len(chosen)} of {cards} card(s) asked: "
               f"{sum(1 for c in chosen if c[0] == 'positive')} for, "
               f"{sum(1 for c in chosen if c[0] == 'negative')} against, from {len(pool)} "
               f"cardable paraphrase(s) ({skipped['unmatched']} whose label is not in their "
               f"text left out)")
    if not chosen:
        raise MediaSpecError(f"no cardable paraphrase for {name}: {skipped}; the board would "
                             f"have no page 2")
    for pol, _lab, _c in chosen:
        if (pol == "positive" and not by["positive"]) or (pol == "negative" and not by["negative"]):
            raise MediaSpecError("a card's side has no counted person; the card and the pins "
                                 "would disagree")

    note = text.get("note", f"nobody has reported on it since the {_day(last_change)} {word}"
                    if not since else None)
    if len({direction(p) for p in prices}) > 1 and len(prices) > 1:
        default_kicker = "Case file · a price that kept moving"
    elif len(prices) > 1:
        default_kicker = f"Case file · a price that kept {'falling' if word == 'cut' else 'rising'}"
    else:
        default_kicker = f"Case file · a price {word}"
    return {
        "slug": model_id.split("/", 1)[-1],
        "model": name,
        "path": recommend._model_path(settings["site"]["paths"], model_id),
        "read_on": today.isoformat(),
        "population": (f"board_entry rows for {model_id} ({mv_id}), all time, counted as public "
                       f"pages count (judge.verdict COUNTED + POST_DAY, "
                       f"publication.sql_counted_document); people = distinct "
                       f"document.author_id; prices = model_event price-change rows; cards = "
                       f"stored feed_paraphrase rows under the evidence feed's terms ({why}; "
                       f"skipped: {skipped}). Read {read_at:%Y-%m-%d %H:%MZ}"),
        "kicker": text.get("kicker") or default_kicker,
        "card_caption": EB_CARD_CAPTION,
        "prices": prices,
        "people": {"all": len(authors), "for": len(by["positive"]),
                   "against": len(by["negative"]), "neither": len(by["neutral"]),
                   "entries": len(rows),
                   "no_author_entries": sum(1 for _p, au, _d in rows if not au)},
        "first_post": first_post.isoformat(),
        "last_post": last_post.isoformat(),
        "note": note,
        "cards_head": text.get("cards_head", "For and against, side by side"),
        "cards": [{"side": "for" if pol == "positive" else "against", "what": lab,
                   "source": platform_name(c["source"]), "date": c["date"].isoformat(),
                   "text": c["text"]} for pol, lab, c in chosen],
        "page3_head": text.get("page3_head") or (
            ["Every report predates", f"the latest {word}"] if not since
            else [f"{len(since)} people posted", f"after the latest {word}"]),
        "extra_stats": [
            {"value": len(since), "label": f"people posting since the {_day(last_change)} "
                                           f"price {word}",
             "counts": "people_since", "since": last_change.isoformat()},
            {"value": len(prices), "label": changes_label, "counts": "price_changes"},
        ],
    }


def evidence_board(conn: Any, model_id: str, settings: dict[str, Any], *, cards: int = 6,
                   text: dict[str, Any] | None = None) -> dict[str, Any]:
    return evidence_board_from_rows(model_id, evidence_board_rows(conn, model_id), settings,
                                    cards=cards, text=text)


def default_name(look: str, spec: dict[str, Any]) -> str:
    """A file name for a spec, from what it is about."""
    if look == "field-report":
        return f"{_slug(spec['title'])}-{spec['read_on']}.json"
    if look == "data-card":
        return f"{spec['slug']}-{spec['window']['to']}.json"
    return f"{spec['slug']}-{spec['read_on']}.json"
