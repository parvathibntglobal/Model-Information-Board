"""Stage 1, harvest: the contract's queries, per domain and platform, as Items.

EVERY PLATFORM THROUGH ITS OWN GATED ENTRY POINT (`harvester_for_source`, or
`fetcher_for_source` for feeds), so the terms rulings, robots.txt, rate limits
and RapidAPI quota recording apply exactly as they do for the model fetch. A
refused or unconfigured platform is reported and skipped; the others still run.

EVERY RAW PAGE IS STORED BEFORE ANYTHING IS READ (the adapters do this), so a
later rule change can be re-applied without a request.

THE REQUEST CAP IS CHECKED BEFORE EACH QUERY. A query that would pass its
platform's `run.max_requests` is not run, and the run log names it - "capped"
must never read as "found nothing" (rule 4).

What this module returns is every item the searches returned, before any rule.
The sieve, dedupe, filters and labels are pipeline.py's.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from collect.industry_ai.config import PLATFORMS, Config
from collect.industry_ai.rules import Item, first_link

_TAG = re.compile(r"<[^>]+>")
BODY_MAX = 8000


def plain(text: str | None) -> str:
    if not text:
        return ""
    t = html.unescape(_TAG.sub(" ", text))
    return re.sub(r"\s+", " ", t).strip()[:BODY_MAX]


def when(value: Any) -> datetime | None:
    """A real timestamp or None - never the fetch time (rule 6)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value, tz=UTC)
    s = str(value).strip()
    for fmt in ("%a %b %d %H:%M:%S %z %Y",):  # X's created_at
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=UTC)
    except ValueError:
        return None


@dataclass
class QueryStat:
    """One query's yield, for the run log and the "prune?" flag."""

    key: str  # "iai:<domain>:<platform>:<query>"
    domain: str
    platform: str
    query: str
    requests: int = 0
    items: int = 0
    status: str = "ok"  # ok | capped | error | skipped
    detail: str = ""


@dataclass
class Harvest:
    items: dict[str, Item] = field(default_factory=dict)
    queries: list[QueryStat] = field(default_factory=list)
    requests: dict[str, int] = field(default_factory=lambda: dict.fromkeys(PLATFORMS, 0))
    notes: list[str] = field(default_factory=list)
    quota: dict[str, Any] = field(default_factory=dict)

    def add(self, item: Item, *, domain: str, key: str) -> None:
        """One item per id, however many queries found it; every finding
        domain becomes a hint, every finding query a key."""
        have = self.items.get(item.id)
        if have is None:
            self.items[item.id] = item
            have = item
        have.domain_hints.add(domain)
        have.query_keys.add(key)


class Budget:
    """Requests left per platform this run."""

    def __init__(self, caps: dict[str, int]):
        self.left = dict(caps)

    def allows(self, platform: str, cost: int) -> bool:
        return self.left.get(platform, 0) >= cost

    def spend(self, platform: str, n: int) -> None:
        self.left[platform] = self.left.get(platform, 0) - n


def plan(cfg: Config, *, domains: list[str], platforms: list[str]) -> list[tuple[str, str, str]]:
    """Every (domain, platform, query) a run would ask, in order. No network."""
    out = []
    for d in domains:
        q = cfg.domains[d].queries
        for p in platforms:
            if p == "reddit":
                out += [(d, p, f"r/{s}") for s in q["reddit"]["subreddits"]]
                out += [(d, p, s) for s in q["reddit"]["search"]]
            elif p == "feeds":
                out += [(d, p, f) for f in q["feeds"]]
            else:
                out += [(d, p, s) for s in q[p]["search"]]
    return out


# ── item builders, one per platform ──────────────────────────────────────────


def _reddit_item(post) -> Item:
    raw = post.raw or {}
    permalink = raw.get("permalink")
    url = f"https://www.reddit.com{permalink}" if permalink else post.url
    dest = raw.get("url_overridden_by_dest") or (post.url if post.url != url else None)
    return Item(
        id=f"reddit:{post.external_id}",
        platform="reddit",
        external_id=post.external_id,
        url=url,
        title=plain(post.title),
        body=plain(post.selftext),
        created_at=post.created_at,
        author_id=post.author_fullname,
        engagement=post.engagement,
        link=dest,
    )


def _x_item(post) -> Item:
    return Item(
        id=f"x:{post.post_id}",
        platform="x",
        external_id=post.post_id,
        url=post.url,
        title="",
        body=plain(post.text),
        created_at=when(post.created_at),
        author_id=post.author_external_id,
        lang=post.lang,
        engagement=post.engagement,
        link=first_link(post.text),
    )


def _github_item(hit) -> Item:
    return Item(
        id=f"github:{hit.external_id}",
        platform="github",
        external_id=hit.external_id,
        url=hit.html_url,
        title=plain(hit.title),
        body=plain(hit.body),
        created_at=when(hit.created_at),
        author_id=hit.author_external_id,
        engagement={"reactions": hit.reactions, "comments": hit.comment_count},
    )


def _hn_item(h: dict) -> Item:
    oid = str(h["objectID"])
    return Item(
        id=f"hackernews:{oid}",
        platform="hackernews",
        external_id=oid,
        url=f"https://news.ycombinator.com/item?id={oid}",
        title=plain(h.get("title")),
        body=plain(h.get("story_text")),
        created_at=when(h.get("created_at")),
        author_id=h.get("author"),
        engagement={"points": h.get("points"), "comments": h.get("num_comments")},
        link=h.get("url"),
    )


def _devto_item(hit) -> Item:
    body = " ".join([plain(hit.description), " ".join(f"#{t}" for t in hit.tags)]).strip()
    return Item(
        id=f"devto:{hit.article_id}",
        platform="devto",
        external_id=str(hit.article_id),
        url=hit.url,
        title=plain(hit.title),
        body=body,
        created_at=when(hit.published_at),
        author_id=hit.author_external_id,
        lang=hit.language,
        engagement={"reactions": hit.reactions, "comments": hit.comments},
    )


def _bluesky_item(hit) -> Item:
    return Item(
        id=f"bluesky:{hit.uri}",
        platform="bluesky",
        external_id=hit.uri,
        url=hit.url,
        title="",
        body=plain(hit.text),
        created_at=when(hit.created_at),
        author_id=hit.did,
        lang=hit.lang,
        engagement={"likes": hit.likes, "comments": hit.replies},
        link=first_link(hit.text),
    )


def _feed_item(fid: str, e) -> Item:
    return Item(
        id=f"feeds:{fid}|{e.entry_id}",
        platform="feeds",
        external_id=f"{fid}|{e.entry_id}",
        url=e.url,
        title=plain(e.title),
        body=plain(e.summary_html or e.content_html),
        created_at=when(e.published_at),
        author_id=e.author,
        link=e.url,
    )


# ── the harvest ──────────────────────────────────────────────────────────────


def harvest(
    cfg: Config,
    *,
    domains: list[str],
    platforms: list[str],
    contract,
    store,
    client_factory: Callable[..., Any],
    since: datetime,
    log: Callable[[str], None] = print,
) -> Harvest:
    """Run every planned query within its platform's cap. Returns all items."""
    out = Harvest()
    budget = Budget({p: int(cfg.run["max_requests"][p]) for p in platforms})
    rows = {p.get("id"): p for p in contract.platforms}
    by_platform: dict[str, list[tuple[str, str]]] = {}
    for d, p, q in plan(cfg, domains=domains, platforms=platforms):
        by_platform.setdefault(p, []).append((d, q))

    for platform in platforms:
        wanted = by_platform.get(platform, [])
        if not wanted:
            continue
        try:
            runner = _RUNNERS[platform](cfg, rows, contract, store, client_factory, since)
        except Exception as e:  # noqa: BLE001 - one refused platform must not stop the rest
            reason = str(e).splitlines()[0][:180] if str(e) else type(e).__name__
            out.notes.append(f"{platform}: skipped - {reason}")
            for d, q in wanted:
                out.queries.append(
                    QueryStat(
                        f"iai:{d}:{platform}:{q}", d, platform, q, status="skipped", detail=reason
                    )
                )
            continue
        seen_feed: dict[str, list[Item]] = {}
        for d, q in wanted:
            stat = QueryStat(f"iai:{d}:{platform}:{q}", d, platform, q)
            out.queries.append(stat)
            if platform == "feeds" and q in seen_feed:
                # ONE FEED, ONE REQUEST, whichever domains list it.
                for it in seen_feed[q]:
                    out.add(it, domain=d, key=stat.key)
                stat.items, stat.detail = len(seen_feed[q]), "same feed as another domain"
                continue
            cost = runner.cost(q)
            if not budget.allows(platform, cost):
                stat.status = "capped"
                stat.detail = (
                    f"not run: {platform} request cap reached ({cfg.run['max_requests'][platform]})"
                )
                continue
            try:
                items, used, detail = runner.run(q)
            except Exception as e:  # noqa: BLE001 - one failed query must not stop the platform
                stat.status, stat.detail = "error", f"{type(e).__name__}: {str(e)[:160]}"
                budget.spend(platform, cost)
                out.requests[platform] += cost
                continue
            budget.spend(platform, used)
            out.requests[platform] += used
            stat.requests, stat.items, stat.detail = used, len(items), detail
            if platform == "feeds":
                seen_feed[q] = items
            for it in items:
                out.add(it, domain=d, key=stat.key)
        quota = getattr(runner, "quota", None)
        if quota:
            out.quota[platform] = quota
        close = getattr(runner, "close", None)
        if close:
            close()
        log(
            f"  {platform}: {out.requests[platform]} request(s), "
            f"{sum(s.items for s in out.queries if s.platform == platform)} item(s)"
        )
    return out


class _Runner:
    """One platform's harvester, built once per run through its gate."""

    quota: dict | None = None

    def cost(self, query: str) -> int:
        return 1

    def run(self, query: str) -> tuple[list[Item], int, str]:
        raise NotImplementedError


def _gated(rows, contract, platform_id: str, factory, **kwargs):
    source = rows.get(platform_id)
    if source is None:
        raise RuntimeError(
            f"no `{platform_id}` source row in contract/sources.yaml: unassessed, not refused"
        )
    return factory(source, rulings=contract.rulings, **kwargs)


class _Reddit(_Runner):
    def __init__(self, cfg, rows, contract, store, client_factory, since):
        from collect.adapters import reddit

        self.client = reddit.build_client()
        self.pages = int(cfg.run["pages_per_query"]["reddit"])
        self.h = _gated(
            rows,
            contract,
            "reddit",
            reddit.harvester_for_source,
            client=self.client,
            store=store,
            max_pages=self.pages,
        )

    def cost(self, query):
        return self.pages

    def run(self, query):
        if query.startswith("r/"):
            run = self.h.list_subreddit(query[2:], pages=self.pages)
        else:
            run = self.h.search(query, pages=self.pages)
        q = {k: getattr(run, k, None) for k in ("quota_limit", "quota_remaining")}
        if any(v is not None for v in q.values()):
            self.quota = q
        return (
            [_reddit_item(p) for p in run.posts],
            max(run.pages_fetched, 1),
            (f"truncated: {run.truncated_by}" if run.truncated_by else ""),
        )

    def close(self):
        self.client.close()


class _X(_Runner):
    def __init__(self, cfg, rows, contract, store, client_factory, since):
        from collect.adapters import x

        self.client = client_factory(timeout=30.0)
        self.pages = int(cfg.run["pages_per_query"]["x"])
        self.suffix = cfg.query_suffix.get("x", "")
        self.h = _gated(
            rows,
            contract,
            "x",
            x.harvester_for_source,
            client=self.client,
            store=store,
            max_pages=self.pages,
        )

    def cost(self, query):
        return self.pages

    def run(self, query):
        run = self.h.search(f"{query} {self.suffix}".strip(), search_type="Latest")
        if run.quota_limit is not None:
            self.quota = {"quota_limit": run.quota_limit, "quota_remaining": run.quota_remaining}
        detail = "quota exhausted" if run.quota_exhausted else ""
        return [_x_item(p) for p in run.posts], max(run.search_calls, 1), detail

    def close(self):
        self.client.close()


class _GitHub(_Runner):
    def __init__(self, cfg, rows, contract, store, client_factory, since):
        from collect.adapters.github import GitHubHarvester
        from collect.config import settings
        from collect.registry.assertions import assert_terms_reviewed

        source = rows.get("github")
        if source is None:
            raise RuntimeError("no `github` source row in contract/sources.yaml")
        # The observation the model fetch passes for the same ruling.
        assert_terms_reviewed(
            [source],
            rulings=contract.rulings,
            observations={"github": {"access_path": "api"}},
            today=datetime.now(UTC).date(),
        )
        token = settings().github_token
        if not token:
            raise RuntimeError("GITHUB_TOKEN is not set")
        self.client = client_factory(
            timeout=30.0,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        self.h = GitHubHarvester(
            client=self.client, store=store, max_pages=1, max_fetch_per_query=0
        )

    def run(self, query):
        from collect.adapters.github import QueryRun
        from collect.adapters.queries.github import SearchRequest

        req = SearchRequest(
            query=f"{query} is:issue", entry_label="industry_ai", variants=(), narrowing_token=None
        )
        run = QueryRun(request=req)
        hits = self.h.search(req, run)
        detail = f"truncated: {run.truncated_by}" if run.truncated_by else ""
        return [_github_item(h) for h in hits], max(run.search_calls, 1), detail

    def close(self):
        self.client.close()


class _HackerNews(_Runner):
    def __init__(self, cfg, rows, contract, store, client_factory, since):
        from collect.adapters import hackernews

        self.client = client_factory()
        self.since = int(since.timestamp())
        self.h = _gated(
            rows,
            contract,
            "hackernews",
            hackernews.harvester_for_source,
            client=self.client,
            store=store,
        )

    def run(self, query):
        hits = self.h.search_stories(query, since_ts=self.since, per_page=30)
        return [_hn_item(h) for h in hits if h.get("objectID") and h.get("title")], 1, ""

    def close(self):
        self.client.close()


class _Devto(_Runner):
    def __init__(self, cfg, rows, contract, store, client_factory, since):
        from collect.adapters import devto

        self.client = client_factory()
        self.h = _gated(
            rows,
            contract,
            "devto",
            devto.harvester_for_source,
            client=self.client,
            store=store,
            max_pages=1,
            per_page=30,
        )

    def run(self, query):
        # dev.to answers HTTP 500 to a hyphenated query (harvest_topics.py, 2026-10-18).
        run = self.h.search(query.replace("-", " "))
        return [_devto_item(h) for h in run.hits if h.url and h.title], 1, ""

    def close(self):
        self.client.close()


class _Bluesky(_Runner):
    def __init__(self, cfg, rows, contract, store, client_factory, since):
        from collect.adapters import bluesky

        self.mod = bluesky
        self.client = client_factory()
        self.h = _gated(
            rows, contract, "bluesky", bluesky.harvester_for_source, client=self.client, store=store
        )

    def run(self, query):
        run = self.mod.BlueskyRun(query=query, started_at=datetime.now(UTC))
        payload = self.h.search(run)
        hits = []
        if payload is not None:
            hits = [h for h in (self.mod._hit_of(p) for p in payload.get("posts") or []) if h]
        detail = "" if payload is not None else "; ".join(run.failures) or "no answer"
        return [_bluesky_item(h) for h in hits], max(run.search_calls, 1), detail

    def close(self):
        self.client.close()


class _Feeds(_Runner):
    def __init__(self, cfg, rows, contract, store, client_factory, since):
        from collect.adapters.blog.fetch import fetcher_for_source
        from collect.adapters.blog.robots import RobotsGate
        from collect.config import settings

        self.client = client_factory()
        self.robots = RobotsGate(self.client, user_agent=settings().user_agent)
        self.factory, self.contract, self.store = fetcher_for_source, contract, store
        self.feeds = {f["id"]: f for f in contract.feeds}

    def run(self, fid):
        feed = self.feeds.get(fid)
        if feed is None:
            raise RuntimeError(f"feed `{fid}` is not in contract/sources.yaml `feeds:`")
        fetcher = self.factory(
            feed,
            robots=self.robots,
            rulings=self.contract.rulings,
            client=self.client,
            store=self.store,
        )
        got = fetcher.fetch_feed(feed["endpoint"])
        items = [_feed_item(fid, e) for e in got.entries if e.url and e.title]
        return items, 1, str(got.outcome)

    def close(self):
        self.client.close()


_RUNNERS = {
    "reddit": _Reddit,
    "x": _X,
    "github": _GitHub,
    "hackernews": _HackerNews,
    "devto": _Devto,
    "bluesky": _Bluesky,
    "feeds": _Feeds,
}
