"""The category score on Compare: CLAUDE.md rule 3's second exception.

ONE FORMULA, FROM contract/category_scores.yaml AND NOWHERE ELSE: for one model
in one category,

    positive   reports with a positive entry in a scored section
    negative   reports with a negative entry in a scored section
    both       reports that are both
    neutral    the rest: no side taken, or only metric rows (a metric's
               polarity is never scored - the contract says why)
    sided      positive + negative - both
    score      round(100 x Wilson lower bound of positive / sided), at the
               board's own wilson_z - and None below min_sided_reports

A REPORT IS A DOCUMENT, counted once per (model, category) however many
entries it filed there: the unit `_split` uses (judge/store/board_entries.py).

A leaf reaches a category through its parent heading: contract/slug_parents.yaml
first, then the extractor's `parent_proposed` when it names a real heading of
that section, exactly as judge/board_grouping.py files it. A leaf filed nowhere
counts nowhere.

THREE STATES, NEVER TWO (rules 4 and 6): `scored`; `too_few` - reports exist
but fewer than the minimum took a side, so there is no score, not a low one;
`none` - nobody reported on this model in this category.
"""

from __future__ import annotations

from collections import defaultdict

from judge.config import board_ordering_z, category_scores, slug_parents
from judge.store.board_entries import _wilson_lower


def score_categories(rows, cfg: dict, leaf_parent: dict, z: float) -> list[dict]:
    """rows: (section, slug, parent_proposed, document_id, polarity) for ONE model."""
    headings = {s: set(m.values()) for s, m in leaf_parent.items()}
    owner = cfg["parent_to_category"]
    docs: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for section, slug, proposed, doc, polarity in rows:
        parent = leaf_parent.get(section, {}).get((slug or "").strip().lower())
        if parent is None and proposed in headings.get(section, set()):
            parent = proposed
        key = owner.get((section, parent)) if parent else None
        if key is None:
            continue
        scored = section in cfg["scored_sections"] and polarity in ("positive", "negative")
        docs[key][doc].add(polarity if scored else "neutral")
    out = []
    for cat in cfg["categories"]:
        d = docs.get(cat["key"], {})
        positive = sum(1 for s in d.values() if "positive" in s)
        negative = sum(1 for s in d.values() if "negative" in s)
        both = sum(1 for s in d.values() if {"positive", "negative"} <= s)
        neutral = sum(1 for s in d.values() if not {"positive", "negative"} & s)
        sided = positive + negative - both
        if not d:
            state, score = "none", None
        elif sided < cfg["min_sided_reports"]:
            state, score = "too_few", None
        else:
            state, score = "scored", round(100 * _wilson_lower(positive, sided, z))
        out.append(
            {
                "key": cat["key"],
                "name": cat["name"],
                "state": state,
                "score": score,
                "reports": len(d),
                "positive": positive,
                "negative": negative,
                "both": both,
                "neutral": neutral,
                "sided": sided,
            }
        )
    return out


def scores_for(conn, model_ids: list[str]) -> list[dict]:
    """The eight categories for one model, from its board entries.

    `model_ids` is every spelling the model is stored under - the registry key
    and the canonical id - because `board_entry.model_version_id` holds both
    (see board_sections). Counted documents only (judge/publication.py): the
    same population as every other count on Compare.
    """
    from judge import publication

    pub_sql, pub_args = publication.sql_counted_document("board_entry.document_id")
    rows = conn.execute(
        "SELECT section, COALESCE(ruling_target, slug), parent_proposed, document_id, polarity "
        "FROM board_entry "
        "WHERE model_version_id = ANY(%s) AND ruling IS DISTINCT FROM 'declined' " + pub_sql,
        ([i for i in model_ids if i], *pub_args),
    ).fetchall()
    return score_categories(rows, category_scores(), slug_parents(), board_ordering_z())


def method() -> dict:
    """What the page says about the score, from the contract, never typed twice."""
    cfg = category_scores()
    return {
        "min_sided_reports": cfg["min_sided_reports"],
        "wilson_z": board_ordering_z(),
        "scored_sections": sorted(cfg["scored_sections"]),
    }
