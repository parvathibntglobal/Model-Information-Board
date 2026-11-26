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

from collect.industry_ai import media
from collect.industry_ai.config import PLATFORMS, WATCH_PLATFORMS, Config
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
    # Every platform a run can spend on, watch-only ones (Instagram) included.
    requests: dict[str, int] = field(
        default_factory=lambda: dict.fromkeys((*PLATFORMS, *WATCH_PLATFORMS), 0))
    notes: list[str] = field(default_factory=list)
    quota: dict[str, Any] = field(default_factory=dict)

    def add(self, item: Item, *, domain: str | None, key: str) -> None:
        """One item per id, however many queries found it; every finding
        domain becomes a hint, every finding query a key. A watch source has no
        domain (`None`): its items are filed by their own terms in `label`."""
        have = self.items.get(item.id)
        if have is None:
            self.items[item.id] = item
            have = item
        if domain:
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
    """Every (scope, platform, query) a run would ask, in file order. `scope` is
    the domain, or "<domain>/<group>" for a group's own queries. No network."""
    out = []
    for d in domains:
        dom = cfg.domains[d]
        scopes = [(d, dom.terms.queries)] + [
            (f"{d}/{g}", grp.terms.queries) for g, grp in dom.groups.items()
        ]
        for scope, q in scopes:
            for p in platforms:
                if p == "reddit":
                    out += [(scope, p, f"r/{s}") for s in q["reddit"]["subreddits"]]
                    out += [(scope, p, s) for s in q["reddit"]["search"]]
                elif p == "feeds":
                    out += [(scope, p, f) for f in q["feeds"]]
                else:
                    out += [(scope, p, s) for s in q[p]["search"]]
    return out


def round_robin(wanted: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """One platform's (scope, query) list, taken a domain at a time in turn.

    FAIR UNDER THE CAP (#644 review, point 7): walked in file order, one budget
    per platform starved whichever domains were listed last, and the log read as
    "those domains had nothing". In turn, every domain gets its first query
    before any gets its second."""
    by_domain: dict[str, list[tuple[str, str]]] = {}
    for scope, q in wanted:
        by_domain.setdefault(scope.split("/", 1)[0], []).append((scope, q))
    lists = list(by_domain.values())
    out = []
    for i in range(max((len(x) for x in lists), default=0)):
        out += [x[i] for x in lists if i < len(x)]
    return out


# ── item builders, one per platform ──────────────────────────────────────────


def _with_media_text(found: tuple[str | None, list[str]]) -> dict:
    """`Item` fields for the text that came with a post's media (#679 step 1)."""
    text, kinds = found
    return {"media_text": plain(text) if text else None, "media_text_from": tuple(kinds)}


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
        media_kind=media.reddit(raw),
        **_with_media_text(media.reddit_text(raw)),
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
        media_kind=media.x(getattr(post, "payload", None)),
        **_with_media_text(media.x_text(getattr(post, "payload", None))),
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
        # A comment (a watched author's) has no title: its text is the body, and
        # the story it sits under is not this item's title - never borrowed.
        title=plain(h.get("title")),
        body=plain(h.get("story_text") or h.get("comment_text")),
        created_at=when(h.get("created_at")),
        author_id=h.get("author"),
        engagement={"points": h.get("points"), "comments": h.get("num_comments")},
        link=h.get("url"),
        media_kind=media.hackernews(h),
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
        media_kind=media.bluesky(getattr(hit, "raw", None) or {}),
        **_with_media_text(media.bluesky_text(getattr(hit, "raw", None) or {})),
    )


def _instagram_item(node: dict) -> Item:
    """One post node of an Instagram account feed (collect/adapters/instagram.py).
    `taken_at_timestamp` is epoch seconds; absent stays absent (rule 6)."""
    from collect.adapters.instagram import caption_of

    code = str(node.get("shortcode") or node.get("id") or "")
    ts = node.get("taken_at_timestamp")
    owner = node.get("owner") or {}
    text = caption_of(node)
    likes = (node.get("edge_media_preview_like") or {}).get("count")
    comments = (node.get("edge_media_to_comment") or {}).get("count")
    return Item(
        id=f"instagram:{code}",
        platform="instagram",
        external_id=code,
        url=f"https://www.instagram.com/p/{code}/",
        title="",
        body=plain(text),
        created_at=datetime.fromtimestamp(ts, UTC) if isinstance(ts, int) else None,
        author_id=str(owner["id"]) if owner.get("id") else None,
        engagement={"likes": likes, "comments": comments},
        link=first_link(text),
        media_kind=media.instagram(node),
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
    watch_since: datetime | None = None,
) -> Harvest:
    """Run every planned query within its platform's cap. Returns all items.

    With `watch_since`, the observer's watch lists run too, after the keyword
    queries, under their OWN caps (`watch.max_requests`), reading back to
    `watch_since`."""
    out = Harvest()
    # KEYWORD QUERIES RUN ONLY ON THE KEYWORD PLATFORMS. A watch-only platform
    # (Instagram, 2026-11-25) has no keyword queries and no `run.max_requests`;
    # it is passed through to the watch lists below.
    kw_platforms = [p for p in platforms if p in PLATFORMS]
    budget = Budget({p: int(cfg.run["max_requests"][p]) for p in kw_platforms})
    rows = {p.get("id"): p for p in contract.platforms}
    by_platform: dict[str, list[tuple[str, str]]] = {}
    for scope, p, q in plan(cfg, domains=domains, platforms=kw_platforms):
        by_platform.setdefault(p, []).append((scope, q))

    for platform in kw_platforms:
        wanted = round_robin(by_platform.get(platform, []))
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
                    out.add(it, domain=d.split("/", 1)[0], key=stat.key)
                stat.items, stat.detail = len(seen_feed[q]), "same feed as another domain"
                continue
            items = _run_query(
                runner, q, stat, budget, out, platform,
                cap_note=f"{platform} request cap reached ({cfg.run['max_requests'][platform]})",
            )
            if items is None:
                continue
            if platform == "feeds":
                seen_feed[q] = items
            for it in items:
                out.add(it, domain=d.split("/", 1)[0], key=stat.key)
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
    if watch_since is not None:
        _harvest_watch(cfg, out, platforms, rows, contract, store, client_factory, watch_since, log)
    return out


def _run_query(runner, q, stat, budget, out, platform, *, cap_note) -> list[Item] | None:
    """One query, under its budget: the steps BOTH the keyword loop and the watch loop
    take, in one place so they cannot drift apart (#650 review, point 2). Returns the
    items, or None when the query was not run (capped) or raised.

    The runner returns (items, used, detail, failure), unpacked strictly, so a runner
    that leaves `failure` out raises and its query is marked `error`, never read as
    "nothing failed" (rule 12; #648). A FAILED SEARCH MUST NOT READ AS "FOUND
    NOTHING" (rule 4; the first dry run, #646: GitHub's 401s and dev.to's 429s showed
    as ok, 0 items): its query is `error`, and items from the pages that did answer
    are still kept."""
    cost = runner.cost(q)
    if not budget.allows(platform, cost):
        stat.status = "capped"
        stat.detail = f"not run: {cap_note}"
        return None
    try:
        items, used, detail, failure = runner.run(q)
    except Exception as e:  # noqa: BLE001 - one failed query must not stop the platform
        stat.status, stat.detail = "error", f"{type(e).__name__}: {str(e)[:160]}"
        budget.spend(platform, cost)
        out.requests[platform] += cost
        return None
    budget.spend(platform, used)
    out.requests[platform] += used
    stat.requests, stat.items, stat.detail = used, len(items), detail
    if failure:
        stat.status = "error"
        stat.detail = "; ".join(x for x in (failure, detail) if x)
    return items


def _harvest_watch(cfg, out, platforms, rows, contract, store, client_factory, since, log) -> None:
    """The observer's watch lists: one query key per source, `watch:<platform>:<source>`,
    each with its own yield; no domain hint. Own caps, so watching never spends the
    keyword queries' budget (anooj, 2026-11-20)."""
    caps = cfg.watch["max_requests"]
    budget = Budget({p: caps[p] for p in WATCH_PLATFORMS if p in platforms})
    by_platform: dict[str, list[str]] = {}
    for p, q in cfg.watch_queries():
        if p in platforms:
            by_platform.setdefault(p, []).append(q)
    for platform, wanted in by_platform.items():
        try:
            runner = _RUNNERS[platform](cfg, rows, contract, store, client_factory, since)
        except Exception as e:  # noqa: BLE001 - one refused platform must not stop the rest
            reason = str(e).splitlines()[0][:180] if str(e) else type(e).__name__
            out.notes.append(f"watch {platform}: skipped - {reason}")
            out.queries += [QueryStat(f"watch:{platform}:{q}", "watch", platform, q,
                                      status="skipped", detail=reason) for q in wanted]
            continue
        before = out.requests[platform]
        for q in wanted:
            stat = QueryStat(f"watch:{platform}:{q}", "watch", platform, q)
            out.queries.append(stat)
            items = _run_query(
                runner, q, stat, budget, out, platform,
                cap_note=f"watch {platform} request cap reached ({caps[platform]})",
            )
            for it in items or []:
                out.add(it, domain=None, key=stat.key)
        quota = getattr(runner, "quota", None)
        if quota:
            out.quota[platform] = quota
        close = getattr(runner, "close", None)
        if close:
            close()
        log(
            f"  watch {platform}: {out.requests[platform] - before} request(s), "
            f"{sum(s.items for s in out.queries if s.platform == platform and s.domain == 'watch')}"
            " item(s)"
        )
    out.notes += quiet_people(cfg, out)
    out.notes += passed_handles(cfg, out)


def quiet_people(cfg: Config, out: Harvest) -> list[str]:
    """A note for each mapped person's handle whose watch query ANSWERED and found
    nothing (#653 review). Quiet for a week is ordinary; a handle that changed is not,
    and nothing else would show it - the map and the watch list go stale together and
    the strict loader cannot see it. A note, never a gate: nothing is dropped.

    Only an `ok` query counts: a skipped, capped or failed one says nothing about the
    handle. X clubs accounts into one query, so its handles are checked against the
    posts that query returned (`handle_of`).

    "QUIET" MEANS THE ACCOUNT POSTED NOTHING, counted BEFORE the sieve (#655 review):
    every harvested post is counted, kept or not. Do not tighten it to "nothing
    passed the sieve" - a person posting about cooking all week is not a stale handle."""
    from collect.industry_ai.rules import handle_of

    stats = {s.key: s for s in out.queries if s.domain == "watch"}
    # The X query that names each account: `(from:a OR from:b ...)`.
    x_query = {a.lower(): s for s in stats.values() if s.platform == "x"
               for a in re.findall(r"from:([A-Za-z0-9_]+)", s.query)}
    x_seen = {handle_of(it) for it in out.items.values()
              if it.platform == "x" and any(k.startswith("watch:x:") for k in it.query_keys)}
    days = cfg.watch["lookback_days"]
    notes = []
    for person, entry in cfg.watch.get("people", {}).items():
        for platform, handle in entry.items():
            if platform == "x":
                s = x_query.get(handle.lower())
                quiet = s is not None and s.status == "ok" and handle.lower() not in x_seen
            elif platform in ("bluesky", "hackernews"):
                q = f"from:{handle}" if platform == "bluesky" else f"hn:author:{handle}"
                s = stats.get(f"watch:{platform}:{q}")
                quiet = s is not None and s.status == "ok" and s.items == 0
            else:
                continue  # `bluesky_did` is an id, not a handle that is queried
            if quiet:
                notes.append(f"watch {platform}: {handle} ({person}) returned no posts in "
                             f"{days} days - quiet, or the handle changed; check it still "
                             "names this person")
    return notes


def passed_handles(cfg: Config, out: Harvest) -> list[str]:
    """A note for each mapped Bluesky handle whose `from:` query returned posts by
    ANOTHER account than the DID written for its person (#655 review).

    `rules.person_of` already links such posts to no one - right for the count - but
    it is the strongest sign the map can get that the handle changed hands, stronger
    than "quiet", and while it lasts the watch list harvests a stranger's posts. A
    post with no author DID says nothing either way and is not counted. A note, never
    a gate."""
    notes = []
    for person, entry in cfg.watch.get("people", {}).items():
        did = entry.get("bluesky_did")
        if not did or "bluesky" not in entry:
            continue
        key = f"watch:bluesky:from:{entry['bluesky']}"
        others = sum(1 for it in out.items.values()
                     if key in it.query_keys and it.author_id and it.author_id != did)
        if others:
            notes.append(f"watch bluesky: {entry['bluesky']} ({person}) returned {others} "
                         "post(s) by another account - the handle may have passed to "
                         "someone else; re-resolve the DID")
    return notes


class _Runner:
    """One platform's harvester, built once per run through its gate."""

    quota: dict | None = None

    def cost(self, query: str) -> int:
        return 1

    def run(self, query: str) -> tuple[list[Item], int, str, str | None]:
        """(items, requests used, detail, failure). `failure` is None unless the
        adapter recorded a failed request - see `failure_of`."""
        raise NotImplementedError


def failure_of(run) -> str | None:
    """What an adapter's run object recorded as failed, or None.

    THE ADAPTERS RECORD FAILURES; THIS READS THEM. Each adapter swallows a failed
    request into its run record (`http_errors`, and per platform `failures`,
    `rate_limited`, `empty_response`) and hands back what it has, so an empty
    result can mean "nothing found" or "not answered". Only the record tells
    them apart (rule 4).

    `http_errors` is read directly: every adapter's run record has it, and a
    record without it raises rather than reading as "nothing failed" (rule 12).
    The other fields are per platform and read when present.

    `recovered` (X, since 2026-11-24) counts failed attempts a retry recovered
    from. Those are not failures of the query, so they are subtracted - else a
    query that answered on its second try would be marked `error`.
    """
    parts = []
    n = int(run.http_errors or 0) - int(getattr(run, "recovered", 0) or 0)
    if n:
        kinds = sorted({str(f) for f in (getattr(run, "failures", None) or [])})
        parts.append(f"{n} request(s) failed" + (f" ({', '.join(kinds)})" if kinds else ""))
    if getattr(run, "rate_limited", False):
        parts.append("rate-limited")
    empty = int(getattr(run, "empty_response", 0) or 0)
    if empty:
        parts.append(f"{empty} page(s) came back empty after retries")
    return "; ".join(parts) or None


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
            failure_of(run),
        )

    def close(self):
        self.client.close()


class _X(_Runner):
    """X, with a page count PER QUERY: a query clubbing at least
    `x_clubbed_min_keywords` keywords gets `x_clubbed` pages (Config.x_pages,
    #644 review, point 10). One harvester per page count, built on first use."""

    def __init__(self, cfg, rows, contract, store, client_factory, since):
        from collect.adapters import x

        self.cfg = cfg
        self.since = since
        self.client = client_factory(timeout=30.0)
        self.suffix = cfg.query_suffix.get("x", "")
        self._build = lambda pages: _gated(
            rows,
            contract,
            "x",
            x.harvester_for_source,
            client=self.client,
            store=store,
            max_pages=pages,
        )
        self._by_pages: dict[int, Any] = {}
        self._build(int(cfg.run["pages_per_query"]["x"]))  # the gate, before any query

    def _full(self, query: str) -> str:
        from collect.industry_ai.config import is_watch_x

        if is_watch_x(query):
            # A watch query reads the accounts' posts back to the window's start,
            # paged (`watch.x_pages`), with the watch suffix (replies excluded in
            # the first test runs). The config refuses one that would pass 480.
            parts = [query, f"since:{self.since:%Y-%m-%d}", self.suffix,
                     self.cfg.watch.get("x_suffix", "")]
            return " ".join(p for p in parts if p)
        return f"{query} {self.suffix}".strip()

    def cost(self, query):
        return self.cfg.x_pages(query)

    def run(self, query):
        pages = self.cfg.x_pages(query)
        if pages not in self._by_pages:
            self._by_pages[pages] = self._build(pages)
        run = self._by_pages[pages].search(self._full(query), search_type="Latest")
        if run.quota_limit is not None:
            self.quota = {"quota_limit": run.quota_limit, "quota_remaining": run.quota_remaining}
        detail = f"{pages} page(s)" + ("; quota exhausted" if run.quota_exhausted else "")
        return [_x_item(p) for p in run.posts], max(run.search_calls, 1), detail, failure_of(run)

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
        self.since = since

    def run(self, query):
        from collect.adapters.github import QueryRun
        from collect.adapters.queries.github import SearchRequest

        # ONLY ISSUES OPENED INSIDE THE RUN WINDOW (2026-11-25, the rotation PR).
        # GitHub's search orders by best match, so without a date a year-old issue
        # sits among this week's: 36 of the 132 GitHub posts the 2026-11-25 run
        # first stored were older than the 90-day window and were dropped after
        # being paid for in requests. `created:>=` IS APPLIED, not silently dropped
        # (the rule 6 shape GitHub search has shown before): measured 2026-11-25 on
        # "AI code review team is:issue", total_count 189,109 without it and 2,272
        # with `created:>=2026-11-22`, and 0 of 30 returned items older than that
        # date (20 of 30 without it).
        req = SearchRequest(
            query=f"{query} is:issue created:>={self.since:%Y-%m-%d}", entry_label="industry_ai",
            variants=(), narrowing_token=None,
        )
        run = QueryRun(request=req)
        hits = self.h.search(req, run)
        detail = f"truncated: {run.truncated_by}" if run.truncated_by else ""
        return ([_github_item(h) for h in hits], max(run.search_calls, 1), detail, failure_of(run))

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
        from collect.adapters.hackernews import HnRun

        # ITS OWN RUN RECORD, so a failed request is recorded and read (#648).
        run = HnRun(query=query, started_at=datetime.now(UTC))
        if query.startswith("hn:list:"):
            # A watch list: Algolia's own tag (show_hn, ask_hn, front_page), newest first.
            hits = self.h.search_stories("", since_ts=self.since, per_page=30, run=run,
                                         tags=query.split(":", 2)[2])
        elif query.startswith("hn:author:"):
            # A watched author: their stories AND comments - an author's comment is
            # where much first-hand AI work is reported.
            hits = self.h.search_stories("", since_ts=self.since, per_page=30, run=run,
                                         tags=f"(story,comment),author_{query.split(':', 2)[2]}")
        else:
            hits = self.h.search_stories(query, since_ts=self.since, per_page=30, run=run)
        items = [_hn_item(h) for h in hits
                 if h.get("objectID") and (h.get("title") or h.get("comment_text"))]
        return items, 1, "", failure_of(run)

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
        return [_devto_item(h) for h in run.hits if h.url and h.title], 1, "", failure_of(run)

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
        failure = failure_of(run) or (None if payload is not None else "no answer")
        return [_bluesky_item(h) for h in hits], max(run.search_calls, 1), "", failure

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
        # "error" and "robots-blocked" are not "an empty feed".
        failure = None
        if got.outcome in ("error", "robots-blocked"):
            failure = f"feed {got.outcome}" + (f": {got.detail}" if got.detail else "")
        return items, 1, str(got.outcome), failure

    def close(self):
        self.client.close()


class _Instagram(_Runner):
    """The observer's Instagram arm (2026-11-25): one feed request per watched
    account, by the numeric id the contract holds (`watch.instagram`), keeping the
    posts newer than the watch window's start. Watch lists only: no keyword search."""

    def __init__(self, cfg, rows, contract, store, client_factory, since):
        from collect.adapters import instagram

        self.since = since
        self.ids = cfg.instagram_ids()
        self.client = client_factory(timeout=45.0)
        self.h = _gated(
            rows, contract, "instagram", instagram.harvester_for_source,
            client=self.client, store=store,
        )

    def run(self, query):
        handle = query.removeprefix("ig:")
        uid = self.ids.get(handle)
        if uid is None:  # the loader pairs every handle with an id; this is a bug
            raise RuntimeError(f"instagram: no id for watched handle {handle!r}")
        run = self.h.user_feed(uid, query=query)
        if run.quota_limit is not None:
            self.quota = {"quota_limit": run.quota_limit, "quota_remaining": run.quota_remaining}
        # A POST WITH NO CAPTION IS LEFT OUT, NOT LABELLED: empty text would be
        # dropped as "no AI term", a judgement about text nobody received. A page
        # where EVERY post is uncaptioned is the provider fault of 9-17 Nov 2026,
        # so the query is marked failed rather than read as a quiet account (rule 4).
        from collect.adapters.instagram import caption_of

        captioned = [n for n in run.posts if caption_of(n).strip()]
        items = [_instagram_item(n) for n in captioned]
        # Undated posts are kept, never guessed into or out of the window (rule 6).
        items = [it for it in items if it.created_at is None or it.created_at >= self.since]
        notes = []
        if run.uncaptioned:
            notes.append(f"{run.uncaptioned} of {len(run.posts)} post(s) came back with "
                         "no caption and were left out")
        if run.quota_exhausted:
            notes.append("quota exhausted")
        # A FULL PAGE INSIDE THE WINDOW (#667 review, note 4): one request reads an
        # account's newest PER_PAGE posts, so when every dated one is inside the watch
        # window, older posts in the window were not read - said, as Reddit's 25-post
        # page is, never read as "that is all this account posted".
        from collect.adapters.instagram import PER_PAGE
        dated = [d for d in (_instagram_item(n).created_at for n in run.posts) if d is not None]
        if len(run.posts) >= PER_PAGE and dated and min(dated) >= self.since:
            notes.append(f"truncated: page-full ({len(run.posts)} posts, all inside the "
                         "watch window; older ones in it not read)")
        failure = failure_of(run)
        if run.posts and not captioned:
            failure = "; ".join(x for x in (failure, "no post carried a caption (provider "
                                            "fault, seen 9-17 Nov 2026)") if x)
        return items, max(run.calls, 1), "; ".join(notes), failure

    def close(self):
        self.client.close()


_RUNNERS = {
    "instagram": _Instagram,
    "reddit": _Reddit,
    "x": _X,
    "github": _GitHub,
    "hackernews": _HackerNews,
    "devto": _Devto,
    "bluesky": _Bluesky,
    "feeds": _Feeds,
}
