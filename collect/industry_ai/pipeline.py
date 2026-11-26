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
from datetime import UTC, datetime, timedelta

from collect.industry_ai.config import Config
from collect.industry_ai.rules import (
    MEDIA_TEXT_FLAG,
    PERSON_FLAG,
    UNREAD_INSTEAD_OF,
    UNREAD_REASON,
    UNREAD_STAGE,
    Item,
    canonical_url,
    cross_post_text,
    filter_reason,
    is_article_link,
    is_watch_only,
    label,
    needed_media_text,
    normalized_text,
    outside_window,
    person_of,
    sieve,
    too_little_to_read,
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


def _dedupe(items: list[Item], results: dict[str, Result],
            persons: dict[str, str] | None = None, *, cross_post_hours: int) -> None:
    """Stage 4 over the items the sieve kept. Four passes, each over what the
    previous left canonical: a shared article link, an author repeating
    themselves, one PERSON posting the same text on two platforms (`persons`:
    item id -> person, from `watch.people`; within `cross_post_hours`, the
    contract's `watch.cross_post_hours`, required), and near-duplicate text."""
    persons = persons or {}
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

    # 3. ONE PERSON, THE SAME TEXT, TWO PLATFORMS (watch.people, 2026-11-20): a
    #    cross-post is one item and the copy a share. Pass 2 cannot see it - the
    #    two handles are two `author_id`s - and on 2026-11-20 pass 4 caught 1 of 3.
    #    Mentions and tags are left out of the comparison, being spelt per platform.
    #    NARROWER THAN "SAME PERSON, SAME TEXT" (#653 review): the copy must be on
    #    ANOTHER platform, within `cross_post_hours` of the earlier post, and - when
    #    both carry an article link - share it. Undated posts are never folded (rule
    #    6). So a template intro reused days later for another paper stays two posts,
    #    and a same-platform repeat is left to pass 2.
    by_person: dict[tuple, list[Item]] = {}
    for it in live:
        person = persons.get(it.id)
        key = cross_post_text(it.text) if person else None
        if results[it.id].verdict == "kept" and key and it.created_at is not None:
            by_person.setdefault((person, key), []).append(it)
    window = timedelta(hours=cross_post_hours)
    copies: dict[tuple, list[Item]] = {}
    for key, members in by_person.items():
        free = sorted(members, key=_order)
        while free:
            head, *rest = free
            link = results[head.id].canonical_url
            taken, platforms = [], {head.platform}
            for m in rest:
                other = results[m.id].canonical_url
                if (m.platform not in platforms
                        and m.created_at - head.created_at <= window
                        and (link is None or other is None or link == other)):
                    taken.append(m)
                    platforms.add(m.platform)
            if taken:
                copies[(key, head.id)] = [head, *taken]
            free = [m for m in rest if m not in taken]
    fold(copies, "cross_post", flag="cross_post")

    # 4. NEAR-DUPLICATE TEXT, by the corpus's own MinHash clustering. Below its
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
    items: list[Item],
    cfg: Config,
    *,
    since: datetime,
    is_bot=lambda item: False,
    now: datetime | None = None,
) -> tuple[dict[str, Result], dict]:
    """Every item's Result, and the counts by stage. Nothing is deleted.

    THE WATCH WINDOW (#650 review, point 1): a post found ONLY by watch lists is kept
    if it was posted within `watch.lookback_days` of when this lane first saw it
    (`first_seen_at`; `now` for this run's fresh items). Reddit's newest page and
    Bluesky's `from:` feed return posts of any age, so without this "the observer
    reads the last week" would really mean "the newest page, up to a year back".
    Measured from first sight, not from now, so a later `--relabel` never drops a
    watched post just because time has passed. A post a keyword query also found
    keeps the run window (`since`)."""
    now = now or datetime.now(UTC)
    lookback = timedelta(days=int(cfg.watch["lookback_days"]))
    results: dict[str, Result] = {it.id: Result(verdict="kept") for it in items}
    matched: dict[str, dict] = {}
    passed: list[Item] = []

    for it in items:  # stages 1-2
        r = results[it.id]
        if outside_window(it, since):
            r.verdict, r.stage, r.reason = "dropped", "window", "outside_window"
            continue
        if (is_watch_only(it) and it.created_at is not None
                and it.created_at < (it.first_seen_at or now) - lookback):
            # Its own reason, so the log says WHICH window dropped it.
            r.verdict, r.stage, r.reason = "dropped", "window", "outside_watch_window"
            continue
        why, terms, ai = sieve(it, cfg)
        r.ai_terms, r.matched_terms = ai, terms
        if why in UNREAD_INSTEAD_OF and too_little_to_read(it, cfg):
            # NOT READABLE, NOT FILTERED OUT (2026-11-25): its content is a picture or
            # a video and its few words cannot say what it is about (rules 4, 6).
            r.verdict, r.stage, r.reason = "dropped", UNREAD_STAGE, UNREAD_REASON
            continue
        if why:
            r.verdict, r.stage, r.reason = "dropped", "sieve", why
            continue
        if needed_media_text(it, cfg):
            # Through on the text that came with its media, not its own words (#679).
            r.flags = sorted(set(r.flags) | {MEDIA_TEXT_FLAG})
        matched[it.id] = terms
        passed.append(it)

    # ONE PERSON, ONE AUTHOR (watch.people): the person rides as a flag, which is
    # stored, so the page counts authors the way `counts` does.
    # Both maps built once per run, not per item (#653 review).
    people, dids = cfg.person_by_handle(), cfg.person_by_did()
    persons = {it.id: p for it in passed if (p := person_of(it, cfg, people, dids))}
    for item_id, p in persons.items():
        results[item_id].flags = sorted(set(results[item_id].flags) | {f"{PERSON_FLAG}{p}"})

    _dedupe(passed, results, persons,
            cross_post_hours=int(cfg.watch["cross_post_hours"]))  # stage 4

    for it in passed:  # stages 5-6
        r = results[it.id]
        if r.verdict != "kept":
            continue
        why, flags = filter_reason(it, cfg, is_bot=is_bot)
        r.flags = sorted(set(r.flags) | set(flags))
        if why in UNREAD_INSTEAD_OF and too_little_to_read(it, cfg):
            r.verdict, r.stage, r.reason = "dropped", UNREAD_STAGE, UNREAD_REASON
            continue
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
        # Two different absences, counted apart (rule 4): a keyword query's own
        # domain not confirmed ("unconfirmed"), and a watched post naming no
        # industry at all ("general").
        empty = "general" if "general_ai" in r.flags else "unconfirmed"
        for d in r.domains or [empty]:
            c = per_domain.setdefault(
                d,
                {
                    "kept": 0,
                    "from_watch": 0,
                    "by_type": Counter(),
                    "by_platform": Counter(),
                    "by_stage": Counter(),
                    "by_group": Counter(),
                    "reach": 0,
                    "authors": set(),
                },
            )
            if f"domain_from_terms:{d}" in r.flags:
                # A watch list filed it here by its terms (option A): counted APART,
                # never in the domain's own figures, which count what its keyword
                # queries found (anooj, 2026-11-20, option (a); the page does the same).
                c["from_watch"] += 1
                continue
            c["kept"] += 1
            c["by_type"][r.content_type] += 1
            c["by_platform"][it.platform] += 1
            if r.stage_guess:
                c["by_stage"][r.stage_guess] += 1
            for g in r.groups:
                if g.startswith(f"{d}/"):
                    c["by_group"][g.split("/", 1)[1]] += 1
            c["reach"] += r.share_count
            # A mapped person is ONE author on every platform; anyone else is one
            # per (platform, account). judge/industry_ai/view.py counts the same way
            # (`coalesce(person, platform || ':' || author_id)`): the set below holds
            # two kinds of key - a "person:<key>" string and a (platform, account)
            # tuple - which cannot collide, so the two counts are built to agree.
            person = next((f for f in r.flags if f.startswith(PERSON_FLAG)), None)
            if person:
                c["authors"].add(person)
            elif it.author_id:
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
