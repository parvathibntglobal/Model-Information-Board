"""Stages 2-5 over a set of items: sieve (window and terms), dedupe, filter, label.

PURE, apart from the near-duplicate clustering it reuses: items in, one
`Result` per item out, plus the counts the run log and the page read. The same
function runs on a fresh harvest and on `--relabel` over every stored item, so a
contract change re-labels the whole collection without a request.

RUN ORDER IS THE NUMBERED ORDER (docs/industry-ai-agent.md §2): an item dropped
at one stage is never looked at by a later one, and every drop names its stage
and reason.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

from collect.industry_ai.config import Config
from collect.industry_ai.rules import (
    Item,
    canonical_url,
    filter_reason,
    is_article_link,
    label,
    normalized_text,
    outside_window,
    sieve,
)


@dataclass
class Result:
    """What the rules made of one item: the row `iai_item`'s label columns hold."""

    verdict: str  # kept | dropped
    stage: str | None = None  # where it was dropped: window|sieve|dedupe|filter
    reason: str | None = None
    flags: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)  # "<domain>/<group>"
    #: What matched, KEPT (#644 review, point 2): domain -> {"terms", "groups"}.
    matched_terms: dict = field(default_factory=dict)
    ai_terms: list[str] = field(default_factory=list)
    content_type: str | None = None
    matched_pattern: str | None = None
    stage_guess: str | None = None
    canonical_of: str | None = None  # the item this one duplicates
    share_count: int = 0  # copies and shares deduped onto this one
    canonical_url: str | None = None


def _order(item: Item):
    """Earliest first; undated after dated; id breaks ties (stable, rule 6)."""
    return (item.created_at is None, item.created_at or datetime.max, item.id)


def _dedupe(items: list[Item], results: dict[str, Result]) -> None:
    """Stage 4 over the items the sieve kept. Three passes, each over what the
    previous left canonical: a shared article link, an author repeating
    themselves, and near-duplicate text."""
    live = sorted(items, key=_order)

    def fold(groups: dict, reason: str, flag: str | None = None) -> None:
        for members in groups.values():
            if len(members) < 2:
                continue
            head, *rest = sorted(members, key=_order)
            for m in rest:
                r = results[m.id]
                r.verdict, r.stage, r.reason, r.canonical_of = "dropped", "dedupe", reason, head.id
                results[head.id].share_count += 1 + r.share_count
            if flag and flag not in results[head.id].flags:
                results[head.id].flags.append(flag)

    # 1. THE SAME ARTICLE, SHARED ON SEVERAL PLATFORMS, IS ONE ITEM.
    by_link: dict[str, list[Item]] = {}
    for it in live:
        link = it.link if is_article_link(it.link) else None
        if it.platform == "feeds":
            link = it.url
        key = canonical_url(link) if link else None
        results[it.id].canonical_url = key
        if key:
            by_link.setdefault(key, []).append(it)
    fold(by_link, "shared_link")

    # 2. ONE AUTHOR POSTING THE SAME TEXT AGAIN: keep one, flag the author.
    by_author: dict[tuple, list[Item]] = {}
    for it in live:
        if results[it.id].verdict == "kept" and it.author_id and normalized_text(it.text):
            by_author.setdefault((it.platform, it.author_id, normalized_text(it.text)), []).append(
                it
            )
    fold(by_author, "repeat_post", flag="repeat_author")

    # 3. NEAR-DUPLICATE TEXT, by the corpus's own MinHash clustering. Below its
    #    token floor a text gets no signature and is never merged by this pass
    #    (over-merging is the worse failure: collect/CLAUDE.md rule 3).
    rest = [it for it in live if results[it.id].verdict == "kept"]
    if len(rest) > 1:
        from collect.assemble.dedupe import DedupeInput, cluster

        found = cluster(
            [DedupeInput(external_id=it.id, text=it.text, created_at=it.created_at) for it in rest]
        )
        by_id = {it.id: it for it in rest}
        groups = {c.canonical_id: [by_id[m] for m in c.member_ids] for c in found.merged_clusters}
        fold(groups, "near_duplicate")


def evaluate(
    items: list[Item], cfg: Config, *, since: datetime, is_bot=lambda item: False
) -> tuple[dict[str, Result], dict]:
    """Every item's Result, and the counts by stage. Nothing is deleted."""
    results: dict[str, Result] = {it.id: Result(verdict="kept") for it in items}
    matched: dict[str, dict] = {}
    passed: list[Item] = []

    for it in items:  # stages 1-2
        r = results[it.id]
        if outside_window(it, since):
            r.verdict, r.stage, r.reason = "dropped", "window", "outside_window"
            continue
        why, terms, ai = sieve(it, cfg)
        r.ai_terms, r.matched_terms = ai, terms
        if why:
            r.verdict, r.stage, r.reason = "dropped", "sieve", why
            continue
        matched[it.id] = terms
        passed.append(it)

    _dedupe(passed, results)  # stage 4

    for it in passed:  # stages 5-6
        r = results[it.id]
        if r.verdict != "kept":
            continue
        why, flags = filter_reason(it, cfg, is_bot=is_bot)
        r.flags = sorted(set(r.flags) | set(flags))
        if why:
            r.verdict, r.stage, r.reason = "dropped", "filter", why
            continue
        v = label(it, matched[it.id], cfg)
        r.domains, r.groups, r.content_type = v.domains, v.groups, v.content_type
        r.matched_pattern, r.stage_guess = v.matched_pattern, v.stage_guess
        r.flags = sorted(set(r.flags) | set(v.flags))

    return results, counts(items, results)


def counts(items: list[Item], results: dict[str, Result]) -> dict:
    """The run log's and the page's numbers, from the Results alone."""
    by_id = {it.id: it for it in items}
    kept = [i for i, r in results.items() if r.verdict == "kept"]
    dropped = Counter(f"{r.stage}:{r.reason}" for r in results.values() if r.verdict == "dropped")
    per_domain: dict[str, dict] = {}
    for i in kept:
        r, it = results[i], by_id[i]
        for d in r.domains or ["unconfirmed"]:
            c = per_domain.setdefault(
                d,
                {
                    "kept": 0,
                    "by_type": Counter(),
                    "by_platform": Counter(),
                    "by_stage": Counter(),
                    "by_group": Counter(),
                    "reach": 0,
                    "authors": set(),
                },
            )
            c["kept"] += 1
            c["by_type"][r.content_type] += 1
            c["by_platform"][it.platform] += 1
            if r.stage_guess:
                c["by_stage"][r.stage_guess] += 1
            for g in r.groups:
                if g.startswith(f"{d}/"):
                    c["by_group"][g.split("/", 1)[1]] += 1
            c["reach"] += r.share_count
            if it.author_id:
                c["authors"].add((it.platform, it.author_id))
    return {
        "items": len(items),
        "kept": len(kept),
        "dropped": dict(sorted(dropped.items())),
        "domains": {
            d: {
                **{k: v for k, v in c.items() if k != "authors"},
                "by_type": dict(c["by_type"]),
                "by_platform": dict(c["by_platform"]),
                "by_stage": dict(c["by_stage"]),
                "by_group": dict(c["by_group"]),
                "authors": len(c["authors"]),
            }
            for d, c in sorted(per_domain.items())
        },
    }
