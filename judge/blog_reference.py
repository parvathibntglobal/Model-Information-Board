"""The blog's reference formats - not articles (2026-10-15).

    glossary        what a job or capability IS, from the hand-written
                    descriptions in contract/, with what engineers report on it
    known issues    per model, the problems at least N engineers report: a
                    tracker, scanned and filtered, not read top to bottom
    answers         "Does <model> support <feature>?" - what the catalogue
                    advertises beside what engineers report

Code over the board and the catalogue, public sources only, no model call -
the same footing as judge/blog_live.py, whose helpers this reuses.

NOTHING HERE SAYS "FIXED", "BEST" OR "NO". An issue shows when it was LAST
reported, never a status, because a silence after a date is not a fix (rule
4). An unpublished feature reads "not published", never "no" (rule 6). Every
figure is a count of engineers or a published fact (rule 3).
"""

from __future__ import annotations

from typing import Any

from judge.blog_live import (
    _FROM,
    _SLUG,
    _VOICES,
    SECTIONS,
    SOURCE_LABEL,
    _hidden,
    _in_catalog,
    _iso,
    _model,
    _pair_rows,
    _topic_names,
    _withheld,
    catalog_entry,
)
from judge.config import (
    blog_reference_settings,
    board_vocabulary,
    capability_about,
    job_about,
    parent_heading,
    slug_parents,
)

_ABOUT = {"best_for": job_about, "capability": capability_about}


def _vocab_names() -> dict[tuple[str, str], str]:
    out = {}
    for section, heads in board_vocabulary().items():
        for items in (heads or {}).values():
            for it in items or []:
                out[(section, it["slug"])] = it["name"]
    return out


def _name(section: str, slug: str, vocab: dict, board: dict) -> str:
    return (
        vocab.get((section, slug)) or board.get((section, slug)) or slug.replace("-", " ").title()
    )


def _first_sentence(text: str) -> str:
    cut = text.find(". ")
    return text if cut == -1 else text[: cut + 1]


def _quotes(conn, hidden, where: str, params: dict, limit: int | None = None) -> list[dict]:
    rows = conn.execute(
        f"SELECT DISTINCT ON (be.document_id, be.quote) be.quote, d.url, d.source, d.created_at, "
        f"       be.polarity "
        f"{_FROM} {where} ORDER BY be.document_id, be.quote, d.created_at DESC",
        {"hidden": hidden, **params},
    ).fetchall()
    rows.sort(key=lambda r: r[3].isoformat() if r[3] else "", reverse=True)
    return [
        {
            "quote": q,
            "url": url,
            "source": SOURCE_LABEL.get(src, src),
            "written": _iso(at.date()) if at else None,
            "polarity": pol,
        }
        for q, url, src, at, pol in rows[:limit]
    ]


# ── the glossary ────────────────────────────────────────────────────────────


def glossary_index(conn) -> dict[str, Any]:
    """Every job and capability that has a hand-written description, with how
    many models and engineers the board has for it (public sources)."""
    hidden = _hidden()
    vocab, board = _vocab_names(), _topic_names(conn, hidden)
    parents = slug_parents()
    tally = {
        (s, slug): (m, a)
        for s, slug, m, a in conn.execute(
            f"SELECT be.section, {_SLUG}, count(DISTINCT v.canonical_id), "
            f"       count(DISTINCT d.author_id) "
            f"{_FROM} AND be.section = ANY(%(sections)s) GROUP BY 1, 2",
            {"hidden": hidden, "sections": list(SECTIONS)},
        ).fetchall()
    }
    entries = []
    for section in SECTIONS:
        for slug, text in _ABOUT[section]().items():
            heading = parents.get(section, {}).get(slug)
            models, engineers = tally.get((section, slug), (0, 0))
            entries.append(
                {
                    "section": section,
                    "slug": slug,
                    "name": _name(section, slug, vocab, board),
                    "summary": _first_sentence(text),
                    "heading": parent_heading(heading) if heading else None,
                    "models": models,
                    "engineers": engineers,
                }
            )
    entries.sort(key=lambda e: e["name"].lower())
    return {"entries": entries}


def glossary_entry(conn, section: str, slug: str) -> dict[str, Any] | None:
    """One concept: its description, the models engineers reported on for it,
    and its neighbours under the same heading. None without a description."""
    if section not in SECTIONS:
        return None
    text = _ABOUT[section]().get(slug)
    if not text:
        return None
    hidden = _hidden()
    vocab, board = _vocab_names(), _topic_names(conn, hidden)
    listed = _in_catalog(conn)
    p = {"section": section, "slug": slug}
    models = [
        {"model": _model(cid, name, listed), "working": wp, "problems": wn, "neutral": wz}
        for _s, _slug, cid, name, wp, wn, wz in _pair_rows(
            conn, hidden, f"AND be.section = %(section)s AND {_SLUG} = %(slug)s", p
        )
    ]
    models.sort(key=lambda r: (-(r["working"] + r["problems"] + r["neutral"]), r["model"]["name"]))
    engineers = conn.execute(
        f"SELECT count(DISTINCT d.author_id) {_FROM} "
        f"AND be.section = %(section)s AND {_SLUG} = %(slug)s",
        {"hidden": hidden, **p},
    ).fetchone()[0]
    heading = slug_parents().get(section, {}).get(slug)
    about = _ABOUT[section]()
    siblings = (
        sorted(
            (
                {"slug": s, "name": _name(section, s, vocab, board)}
                for s, h in slug_parents().get(section, {}).items()
                if h == heading and s != slug and s in about
            ),
            key=lambda x: x["name"].lower(),
        )[:12]
        if heading
        else []
    )
    return {
        "section": section,
        "slug": slug,
        "name": _name(section, slug, vocab, board),
        "about": text,
        "heading": parent_heading(heading) if heading else None,
        "engineers": engineers,
        "models": models,
        "siblings": siblings,
        "withheld_entries": _withheld(
            conn, f"AND be.section = %(section)s AND {_SLUG} = %(slug)s", {"hidden": hidden, **p}
        ),
    }


# ── known issues ────────────────────────────────────────────────────────────


def _issue_rows(conn, hidden, model_id: str | None = None) -> list[tuple]:
    """(canonical id, name, slug, engineers with problems, engineers it works
    for, first problem report, latest problem report) for capabilities."""
    n = blog_reference_settings()["min_engineers"]
    where = "AND v.canonical_id = %(model)s " if model_id else ""
    return conn.execute(
        f"SELECT v.canonical_id, v.display_name, {_SLUG}, "
        f"       count(DISTINCT d.author_id) FILTER (WHERE be.polarity = 'negative'), "
        f"       count(DISTINCT d.author_id) FILTER (WHERE be.polarity = 'positive'), "
        f"       min(d.created_at) FILTER (WHERE be.polarity = 'negative'), "
        f"       max(d.created_at) FILTER (WHERE be.polarity = 'negative') "
        f"{_FROM} AND be.section = 'capability' {where}"
        f"GROUP BY 1, 2, 3 "
        f"HAVING count(DISTINCT d.author_id) FILTER (WHERE be.polarity = 'negative') >= %(n)s",
        {"hidden": hidden, "model": model_id, "n": n},
    ).fetchall()


def issues_index(conn) -> dict[str, Any]:
    """Models with at least one known issue, most issues first - a count shown
    on every row, and the page says that is the order."""
    hidden = _hidden()
    listed = _in_catalog(conn)
    by_model: dict[str, dict] = {}
    for cid, name, _slug, _neg, _pos, _first, last in _issue_rows(conn, hidden):
        m = by_model.setdefault(
            cid, {"model": _model(cid, name, listed), "issues": 0, "latest": None}
        )
        m["issues"] += 1
        if last and (m["latest"] is None or last.date().isoformat() > m["latest"]):
            m["latest"] = last.date().isoformat()
    rows = sorted(by_model.values(), key=lambda r: (-r["issues"], r["model"]["name"]))
    return {"models": rows, "min_engineers": blog_reference_settings()["min_engineers"]}


def issues_for(conn, model_id: str) -> dict[str, Any] | None:
    """One model's known issues, each with the quotes behind it. None when the
    model has no public report at all (the route answers 404); an EMPTY list
    when it has reports but no issue reached the threshold - said in words."""
    hidden = _hidden()
    seen = conn.execute(
        f"SELECT v.display_name {_FROM} AND v.canonical_id = %(model)s LIMIT 1",
        {"hidden": hidden, "model": model_id},
    ).fetchone()
    if seen is None:
        return None
    vocab, board = _vocab_names(), _topic_names(conn, hidden)
    issues = []
    for _cid, _mname, slug, neg, pos, first, last in _issue_rows(conn, hidden, model_id):
        issues.append(
            {
                "slug": slug,
                "name": _name("capability", slug, vocab, board),
                "problems": neg,
                "working": pos,
                "first": _iso(first.date()) if first else None,
                "latest": _iso(last.date()) if last else None,
                "quotes": _quotes(
                    conn,
                    hidden,
                    f"AND be.section = 'capability' AND {_SLUG} = %(slug)s "
                    f"AND v.canonical_id = %(model)s AND be.polarity = 'negative'",
                    {"slug": slug, "model": model_id},
                    limit=6,
                ),
            }
        )
    issues.sort(key=lambda r: (-r["problems"], r["latest"] or "", r["name"]))
    return {
        "model": _model(model_id, seen[0], _in_catalog(conn)),
        "issues": issues,
        "min_engineers": blog_reference_settings()["min_engineers"],
    }


# ── answers ─────────────────────────────────────────────────────────────────


def answers_index(conn) -> dict[str, Any]:
    """Models a Q&A page exists for: those with at least one public report."""
    hidden = _hidden()
    listed = _in_catalog(conn)
    rows = conn.execute(
        f"SELECT v.canonical_id, v.display_name, count(DISTINCT d.author_id) {_FROM} "
        f"GROUP BY 1, 2 ORDER BY 2",
        {"hidden": hidden},
    ).fetchall()
    return {
        "models": [{"model": _model(cid, name, listed), "engineers": n} for cid, name, n in rows],
        "features": [f["label"] for f in blog_reference_settings()["features"]],
    }


def answers_for(conn, model_id: str) -> dict[str, Any] | None:
    """Each feature's question for one model: advertised, and reported."""
    hidden = _hidden()
    seen = conn.execute(
        f"SELECT v.display_name {_FROM} AND v.canonical_id = %(model)s LIMIT 1",
        {"hidden": hidden, "model": model_id},
    ).fetchone()
    cat = catalog_entry(conn, model_id)
    if seen is None and cat is None:
        return None
    name = (cat or {}).get("name") or seen[0]
    feats = (cat or {}).get("features") or {}
    vocab, board = _vocab_names(), _topic_names(conn, hidden)
    answers = []
    for f in blog_reference_settings()["features"]:
        slugs = f["board_slugs"]
        working = problems = neutral = 0
        topics, samples = [], {}
        if slugs:
            working, problems, neutral = conn.execute(
                f"SELECT {_VOICES} {_FROM} AND be.section = 'capability' "
                f"AND {_SLUG} = ANY(%(slugs)s) AND v.canonical_id = %(model)s",
                {"hidden": hidden, "slugs": slugs, "model": model_id},
            ).fetchone()
            topics = [
                {"slug": s, "name": _name("capability", s, vocab, board)}
                for (s,) in conn.execute(
                    f"SELECT DISTINCT {_SLUG} {_FROM} AND be.section = 'capability' "
                    f"AND {_SLUG} = ANY(%(slugs)s) AND v.canonical_id = %(model)s",
                    {"hidden": hidden, "slugs": slugs, "model": model_id},
                ).fetchall()
            ]
            for pol in ("positive", "negative"):
                q = _quotes(
                    conn,
                    hidden,
                    f"AND be.section = 'capability' AND {_SLUG} = ANY(%(slugs)s) "
                    f"AND v.canonical_id = %(model)s AND be.polarity = %(pol)s",
                    {"slugs": slugs, "model": model_id, "pol": pol},
                    limit=1,
                )
                samples[pol] = q[0] if q else None
        answers.append(
            {
                "key": f["key"],
                "label": f["label"],
                # True / False / None (not published), as the catalogue says.
                # None also when the model is not in today's catalogue.
                "advertised": feats.get(f["key"]) if cat else None,
                "in_catalogue": cat is not None,
                "mapped": bool(slugs),
                "working": working,
                "problems": problems,
                "neutral": neutral,
                "topics": topics,
                "sample_working": samples.get("positive"),
                "sample_problems": samples.get("negative"),
            }
        )
    return {"model": _model(model_id, name, _in_catalog(conn)), "answers": answers}
