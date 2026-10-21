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

from collections import Counter
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
            "model_type_min_models": int(raw["model_types"]["min_reported_models"]),
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise IndexingContractError(
            f"contract/indexing.yaml is missing or malformed at {exc}. Every threshold "
            "is required; a defaulted one would index pages on a number nobody chose."
        ) from exc
    for kind, n in out["min_voices"].items():
        if n < 1:
            raise IndexingContractError(f"`pages.{kind}.min_voices` must be at least 1, not {n}.")
    if out["model_type_min_models"] < 1:
        raise IndexingContractError(
            "`model_types.min_reported_models` must be at least 1, not "
            f"{out['model_type_min_models']}.")
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

    THE PUBLIC ADDRESSES (2026-10-20). The board's own pages (`/board/...`,
    `/models/...`) are signed-in since 2026-10-15 and noindex, so listing them
    told search engines about login walls while every public page fell to
    noindex - `noindexFor` keeps a page indexable only when its canonical is
    here. The same evidence now admits the public page that shows it:

        section           /reviews/{jobs|capabilities|metrics}/:slug, and for a
                          job also /best-ai-model/:slug (the picker on that job)
        model             /ai-models/:canonical and /reviews/models/:canonical, and
                          /alternatives/:name (the picker's alternatives to it)
        model_in_section  counted for the tally only - no public page shows one
                          model inside one section
        glossary_term     /glossary/:slug - every term in glossary.yaml, which is
                          reviewed copy, so no evidence threshold applies
        model_type        /ai-models/:type (2026-10-21) - one type's list (image,
                          video...), once it shows enough models engineers
                          reported on; an empty type page is not invited
    """
    from judge import blog_store, publication
    from judge.store.board_entries import board_sections, voices_by_model

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
    # Models with a job or capability entry: what the picker can find
    # alternatives for (it reads no metrics - web/src/routes/ModelPicker.jsx).
    in_picker: set[str] = set()
    for key, seg in SEGMENT.items():
        for item in sections.get(key) or []:
            v = int(item.get("voices") or 0)
            tallies["section"]["pages"] += 1
            if v >= need["section"]:
                tallies["section"]["indexable"] += 1
                # LASTMOD: when the newest entry on the page was added, over the
                # same public rows the page shows. Absent rather than invented.
                out.append({"path": f"/reviews/{seg}/{item['slug']}", "kind": "section",
                            "voices": v, "lastmod": item.get("updated_at")})
                # A JOB HAS A SECOND PUBLIC PAGE (2026-10-21): the picker's
                # /best-ai-model/<job>, the same evidence asked as "which model".
                if seg == "jobs":
                    out.append({"path": f"/best-ai-model/{item['slug']}", "kind": "section",
                                "voices": v, "lastmod": item.get("updated_at")})
            for m in item.get("models") or []:
                # THE READABLE ID IN THE ADDRESS (`anthropic/claude-opus-4.6`), the
                # same one the board links use; the internal key only as a fallback.
                mkey = m.get("model_canonical") or m.get("model_key") or m.get("model_version_id")
                if not mkey:
                    continue
                if key != "metric":
                    in_picker.add(mkey)
                mv = int(m.get("voices") or 0)
                # The model's newest entry across every section, for its own page.
                when = m.get("updated_at")
                if when and (mkey_lastmod.get(m.get("model_key")) or "") < when:
                    mkey_lastmod[m.get("model_key")] = when
                # Tallied, not listed: the drill-down lives only on the signed-in board.
                tallies["model_in_section"]["pages"] += 1
                if mv >= need["model_in_section"]:
                    tallies["model_in_section"]["indexable"] += 1

    # MODEL PAGES, by canonical id (SEO item 2: one URL per model). Only models
    # with any board entry can reach the threshold; the rest count as pages
    # with no evidence, so the tally's denominator is the whole registry.
    hidden = list(publication.withheld_sources())
    registry = conn.execute("SELECT id, canonical_id FROM model_version").fetchall()
    with_entries = {row[0] for row in conn.execute(
        "SELECT DISTINCT v.id FROM board_entry be JOIN model_version v "
        "  ON v.id = be.model_version_id OR v.canonical_id = be.model_version_id "
        "WHERE be.ruling IS DISTINCT FROM 'declined'").fetchall()}
    # A MODEL'S ALTERNATIVES PAGE is named by its own name (`gpt-6-astra`), or
    # `provider--model` when two registry models share that name - the rule the
    # picker writes its canonical by (web/src/routes/ModelPicker.jsx, altSlug).
    names = Counter(c.split("/", 1)[1] for _, c in registry if c and "/" in c)

    def alt_slug(canonical: str) -> str:
        name = canonical.split("/", 1)[1]
        return name if names[name] == 1 else canonical.replace("/", "--", 1)

    # A MODEL'S /ai-models PAGE EXISTS ONLY FOR WHAT THE CATALOGUE LISTS
    # (judge/catalog.py; anything else is a 404 there). A registry model with
    # reports but no listing keeps its reviews page. Read through the
    # catalogue's own view - only its modules name its table.
    from judge.catalog import catalog_view

    catalogue = catalog_view(conn)
    listed = {m["id"] for m in catalogue.get("models") or []}

    # ONE QUERY FOR EVERY MODEL'S VOICES (#552, item 12). This asked
    # `evidence_for_model` once per model - two queries each - which was most of
    # the ~13 s the list took. `voices_by_model` applies the same gates and is
    # held equal to it, model by model, in tests/test_seo_indexable_pages.py.
    voices = voices_by_model(conn, hidden=hidden)
    for mv_id, canonical in registry:
        tallies["model"]["pages"] += 1
        if mv_id not in with_entries or not canonical:
            continue
        v = voices.get(mv_id, 0)
        if v >= need["model"]:
            tallies["model"]["indexable"] += 1
            # Public pages that show one model: its catalogue page (price, specs,
            # voices) and its reviews page (what engineers report).
            paths = [f"/reviews/models/{canonical}"]
            if canonical in listed:
                paths.insert(0, f"/ai-models/{canonical}")
            # ...and its alternatives in the picker (2026-10-21), the same evidence
            # asked as "what else works where this one does".
            # Only where the picker has something to offer: a model reported on for
            # metrics alone has no alternatives page (it would read "not found").
            if "/" in canonical and canonical in in_picker:
                paths.append(f"/alternatives/{alt_slug(canonical)}")
            for path in paths:
                out.append({"path": path, "kind": "model", "voices": v,
                            "lastmod": mkey_lastmod.get(mv_id)})

    # MODEL TYPE PAGES (2026-10-21): /ai-models/image lists the image models
    # engineers reported on, and stays empty until one has a voice. Counted by
    # the page's own data (catalog_view's `types_voiced`, the number its type
    # chip shows), so the list and the page cannot disagree.
    voiced = catalogue.get("types_voiced") or {}
    for t, n in voiced.items():
        if n >= r["model_type_min_models"]:
            out.append({"path": f"/ai-models/{t}", "kind": "model_type", "voices": None})

    # Approved posts only. A store that cannot be read raises
    # (`blog_store.StoreUnreadable`), so a failure is not read as "no posts".
    for post in blog_store.published(conn):
        if post.get("slug"):
            out.append({"path": f"/blogs/{post['slug']}", "kind": "blog_post", "voices": None,
                        "lastmod": post.get("published_at")})

    # GLOSSARY TERMS (2026-10-20): reviewed copy in glossary.yaml, one page each.
    # A file that fails its checks raises (glossary.GlossaryError) instead of
    # silently listing no terms - the same rule as an unreadable blog store.
    from judge import glossary

    for term in glossary.load():
        out.append({"path": f"/glossary/{term['slug']}", "kind": "glossary_term", "voices": None})

    never = set(r["never"])
    paths = sorted((p for p in out if p["path"] not in never), key=lambda p: p["path"])
    return {"paths": paths, "tallies": tallies, "rules": r}
