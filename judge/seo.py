"""Which pages are worth indexing - SEO item 5 (proposed 2026-10-09).

One function, `indexable_pages`, answers it from the database and
`contract/indexing.yaml`. The frontend reads its answer through
`GET /seo/indexable` and marks every other page `noindex`; a sitemap
generator (SEO item 8) can read the same list, so the two cannot disagree.

NOTHING HERE MAKES THE SITE INDEXABLE. `web/index.html` carries
`noindex, nofollow` and a page can only make robots stricter. This decides
which pages stay out of search engines once that tag is lifted.

COUNTED ON THE PUBLIC VIEW, whatever view this server runs. A page's evidence
is what a public visitor would see, so withheld sources
(`contract/publication.yaml`) are not counted even on the team's internal
deployment - otherwise a page that looks substantial internally would be
indexed as a one-comment page publicly.

THE BOARD'S OWN COUNTING, NOT A SECOND ONE. Section pages and drill-downs are
counted by `board_sections` and model pages by `evidence_for_model` - the same
functions the pages render from - with the public withholding passed in. A
second count written here would be a second implementation that could drift
from what the page shows.

NO MODEL PARTICIPATES (rule 2). Thresholds live in the contract (rule 5) and a
missing one raises (rule 12).
"""

from __future__ import annotations

from typing import Any

#: board section key -> the URL segment the frontend routes on.
SEGMENT = {"best_for": "jobs", "capability": "capabilities", "metric": "metrics"}
PAGE_KINDS = ("section", "model_in_section", "model")


class IndexingContractError(RuntimeError):
    """`contract/indexing.yaml` is missing something this refuses to default."""


def rules() -> dict:
    """The contract, validated. Every key required; nothing defaulted."""
    from judge.config import _read

    raw = _read("indexing.yaml") or {}
    try:
        pages = raw["pages"]
        out = {
            "min_voices": {k: int(pages[k]["min_voices"]) for k in PAGE_KINDS},
            "always": [str(p) for p in raw["always"]],
            "never": [str(p) for p in raw["never"]],
            "blog_posts": str(raw["blog_posts"]),
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise IndexingContractError(
            f"contract/indexing.yaml is missing or malformed at {exc}. Every threshold "
            "is required; a defaulted one would index pages on a number nobody chose."
        ) from exc
    for kind, n in out["min_voices"].items():
        if n < 1:
            raise IndexingContractError(f"`pages.{kind}.min_voices` must be at least 1, not {n}.")
    if out["blog_posts"] != "approved_only":
        raise IndexingContractError(
            f"`blog_posts: {out['blog_posts']}` is not a known policy (only `approved_only`).")
    return out


def indexable_pages(conn: Any) -> dict:
    """Every path worth indexing, with what admitted it, and per-kind tallies.

    Returns {"paths": [{"path", "kind", "voices"}...], "tallies": {kind:
    {"pages", "indexable"}}, "rules": {...}}. `voices` is None for kinds with
    no evidence threshold. Paths are the canonical paths the frontend writes
    (web/src/seo/pages.js), so a page can test its own canonical against them.
    """
    from judge import blog_store, publication
    from judge.store.board_entries import board_sections, evidence_for_model

    r = rules()
    need = r["min_voices"]
    out: list[dict] = [{"path": p, "kind": "always", "voices": None} for p in r["always"]]
    tallies = {k: {"pages": 0, "indexable": 0} for k in PAGE_KINDS}

    # WHICH PAGES ARE WORTH INDEXING IS DECIDED BY WHAT THEY CAN SHOW. Totals on
    # a page count every source since 2026-10-15, but a page whose voices come
    # mostly from sources it may not quote is thin to a search engine - so the
    # threshold counts the quotable (public) voices only, as before.
    sections = board_sections(conn, hide_source=publication.withheld_publicly)
    mkey_lastmod: dict[str, str] = {}
    for key, seg in SEGMENT.items():
        for item in sections.get(key) or []:
            v = int(item.get("voices") or 0)
            tallies["section"]["pages"] += 1
            if v >= need["section"]:
                tallies["section"]["indexable"] += 1
                # LASTMOD: when the newest entry on the page was added, over the
                # same public rows the page shows. Absent rather than invented.
                out.append({"path": f"/board/{seg}/{item['slug']}", "kind": "section", "voices": v,
                            "lastmod": item.get("updated_at")})
            for m in item.get("models") or []:
                # THE READABLE ID IN THE ADDRESS (`anthropic/claude-opus-4.6`), the
                # same one the board links use; the internal key only as a fallback.
                mkey = m.get("model_canonical") or m.get("model_key") or m.get("model_version_id")
                if not mkey:
                    continue
                mv = int(m.get("voices") or 0)
                # The model's newest entry across every section, for its own page.
                when = m.get("updated_at")
                if when and (mkey_lastmod.get(m.get("model_key")) or "") < when:
                    mkey_lastmod[m.get("model_key")] = when
                tallies["model_in_section"]["pages"] += 1
                if mv >= need["model_in_section"]:
                    tallies["model_in_section"]["indexable"] += 1
                    out.append({"path": f"/board/{seg}/{item['slug']}/{mkey}",
                                "kind": "model_in_section", "voices": mv,
                                "lastmod": m.get("updated_at")})

    # MODEL PAGES, by canonical id (SEO item 2: one URL per model). Only models
    # with any board entry can reach the threshold; the rest count as pages
    # with no evidence, so the tally's denominator is the whole registry.
    hidden = list(publication.withheld_sources())
    registry = conn.execute("SELECT id, canonical_id FROM model_version").fetchall()
    with_entries = {row[0] for row in conn.execute(
        "SELECT DISTINCT v.id FROM board_entry be JOIN model_version v "
        "  ON v.id = be.model_version_id OR v.canonical_id = be.model_version_id "
        "WHERE be.ruling IS DISTINCT FROM 'declined'").fetchall()}
    for mv_id, canonical in registry:
        tallies["model"]["pages"] += 1
        if mv_id not in with_entries or not canonical:
            continue
        v = evidence_for_model(conn, mv_id, hidden=hidden, with_voices=True)["voices"]
        if v >= need["model"]:
            tallies["model"]["indexable"] += 1
            out.append({"path": f"/models/{canonical}", "kind": "model", "voices": v,
                        "lastmod": mkey_lastmod.get(mv_id)})

    # Approved posts only. A store that cannot be read raises
    # (`blog_store.StoreUnreadable`), so a failure is not read as "no posts".
    for post in blog_store.published(conn):
        if post.get("slug"):
            out.append({"path": f"/blogs/{post['slug']}", "kind": "blog_post", "voices": None,
                        "lastmod": post.get("published_at")})

    never = set(r["never"])
    paths = sorted((p for p in out if p["path"] not in never), key=lambda p: p["path"])
    return {"paths": paths, "tallies": tallies, "rules": r}
