"""contract/industry_ai.yaml, read strictly.

Every key the lane uses is required and checked here, once, before a request is
made (rule 12): a missing key, an UNKNOWN key, an unknown platform, a domain with
no terms, an X query too long for the platform or a pattern that is not a valid
regular expression stops the run with a message naming it. Nothing is defaulted,
and nothing unimplemented is silently accepted: a block the code does not read
(say `x: {accounts: [...]}` before the observer arm exists) is refused, because
a reader of the file would believe it is being watched (#644 review, point 8).

STRUCTURE (#644 review, point 3): a domain is an industry or a function
(`kind`), is `active` or not, and may hold `groups`, each with its own terms,
exclusions and queries. Terms and queries at the domain level apply to the
whole domain; a group's apply to that group, and its exclusions only to its own
terms.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from collect.adapters.x import MAX_QUERY_CHARS

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contract" / "industry_ai.yaml"

#: The platforms this lane harvests. `feeds` is the blog/RSS arm.
PLATFORMS = ("reddit", "x", "github", "hackernews", "devto", "bluesky", "feeds")
#: The content types, in no particular order; `type_order` sets precedence.
CONTENT_TYPES = ("use_case", "how_to", "tool_or_product", "research", "news", "discussion")
STAGES = ("deployed", "pilot", "first_hand")
KINDS = ("industry", "function")
#: The fallback type, said by the contract's own `type_order`, never invented.
DEFAULT_TYPE = "discussion"

TOP_KEYS = {
    "version",
    "pipeline_version",
    "run",
    "query_suffix",
    "ai_terms",
    "global_exclude_phrases",
    "spam_patterns",
    "ad_patterns",
    "teach_patterns",
    "hiring_patterns",
    "promo_patterns",
    "type_order",
    "type_patterns",
    "stage_patterns",
    "domains",
    "watch",
    "retention",
    # What each pipeline_version changed, one line each, for the Info view
    # (judge/industry_ai/view.py reads it; the rules never do). #668, 2026-11-25.
    "versions",
}
#: `retention:` (anooj, 2026-11-24): when a stored item's TEXT is cleared. Rows are
#: never deleted - the page's counts need them.
RETENTION_KEYS = {"clear_text_after_days", "dropped", "kept_domains"}

# ── THE OBSERVER (watch lists; anooj, 2026-11-20) ────────────────────────────
#: The platforms whose watch lists the code READS today. A list for any other
#: platform (dev.to tags, GitHub repos, feeds) is refused as an unknown key
#: until its runner exists - a refused list cannot be mistaken for a watched one.
WATCH_PLATFORMS = ("reddit", "x", "bluesky", "hackernews", "instagram")
WATCH_KEYS = {"enabled", "lookback_days", "max_requests", "x_pages", "x_club_max", "x_suffix",
              "people", "cross_post_hours", *WATCH_PLATFORMS}
#: The platforms whose watched ACCOUNTS a person can be mapped across (Reddit watches
#: communities, not people).
PEOPLE_PLATFORMS = ("x", "bluesky", "hackernews")
_PERSON_KEY = re.compile(r"^[a-z0-9_]{2,40}$")
#: A Bluesky account's permanent id. `did:plc:` is 24 base32 characters; `did:web:`
#: names a domain. A handle can change hands; a DID does not.
_BLUESKY_DID = re.compile(r"^did:(plc:[a-z2-7]{24}|web:[a-z0-9.-]+)$")
HN_WATCH_KEYS = {"lists", "authors"}
#: Algolia's own tags for Hacker News lists.
HN_LISTS = ("show_hn", "ask_hn", "front_page")
_REDDIT_SUB = re.compile(r"^[A-Za-z0-9_]{2,21}$")
_X_HANDLE = re.compile(r"^[A-Za-z0-9_]{1,15}$")
_BSKY_HANDLE = re.compile(r"^[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$")
_HN_USER = re.compile(r"^[A-Za-z0-9_-]{2,15}$")
#: Instagram usernames: letters, digits, `.` and `_`, at most 30 (2026-11-25).
_IG_HANDLE = re.compile(r"^[A-Za-z0-9._]{1,30}$")
#: An Instagram account's numeric id (the provider's `user_id`): the account,
#: where the handle is only its current name.
_IG_ID = re.compile(r"^[0-9]{3,25}$")
#: The longest `since:` an X watch query carries ("since:2026-11-20").
_SINCE_CHARS = len(" since:2026-11-20")
RUN_KEYS = {
    "enabled",
    "cadence",
    "window_days",
    "max_requests",
    "pages_per_query",
    "x_clubbed_min_keywords",
    "min_text_chars",
    "context_window_words",
    "low_engagement_max",
    "rotation",
}
#: The two rotation groups (`run.rotation.groups`), and how a scheduled run picks one.
ROTATION_GROUPS = ("a", "b")
ROTATION_BY = {"utc_day_parity"}
PAGE_KEYS = {"reddit", "x", "x_clubbed"}
DOMAIN_KEYS = {
    "name",
    "kind",
    "active",
    "definition",
    "domain_terms",
    "ambiguous_terms",
    "exclude_phrases",
    "queries",
    "groups",
}
GROUP_KEYS = {"name", "definition", "domain_terms", "ambiguous_terms", "exclude_phrases", "queries"}
QUERY_KEYS = {
    "reddit": {"subreddits", "search"},
    **{p: {"search"} for p in PLATFORMS if p not in ("reddit", "feeds")},
}

_QUOTED = re.compile(r'"[^"]+"')


class IndustryAIConfigError(ValueError):
    """contract/industry_ai.yaml is missing a key, holds an unknown one, or a wrong value."""


@dataclass(frozen=True)
class Terms:
    """What a domain or one of its groups matches, and how it is searched."""

    domain_terms: tuple[str, ...]
    ambiguous_terms: dict[str, tuple[str, ...]]
    exclude_phrases: tuple[re.Pattern, ...]
    queries: dict[str, Any]

    @property
    def any_terms(self) -> bool:
        return bool(self.domain_terms or self.ambiguous_terms)


@dataclass(frozen=True)
class Group:
    key: str
    name: str
    definition: str | None
    terms: Terms


@dataclass(frozen=True)
class Domain:
    key: str
    name: str
    kind: str
    active: bool
    definition: str
    terms: Terms
    groups: dict[str, Group] = field(default_factory=dict)

    # Kept for the domain-level terms, which most domains use alone.
    @property
    def domain_terms(self) -> tuple[str, ...]:
        return self.terms.domain_terms

    @property
    def exclude_phrases(self) -> tuple[re.Pattern, ...]:
        return self.terms.exclude_phrases


@dataclass(frozen=True)
class Config:
    pipeline_version: str
    run: dict[str, Any]
    query_suffix: dict[str, str]
    ai_terms: tuple[str, ...]
    global_exclude: tuple[re.Pattern, ...]
    spam: tuple[re.Pattern, ...]
    ads: tuple[re.Pattern, ...]
    teach: tuple[re.Pattern, ...]
    hiring: tuple[re.Pattern, ...]
    promo: tuple[re.Pattern, ...]
    type_order: tuple[str, ...]
    type_patterns: dict[str, tuple[re.Pattern, ...]]
    stage_patterns: dict[str, tuple[re.Pattern, ...]]
    domains: dict[str, Domain]
    #: The observer's watch lists, parsed (`_watch`).
    watch: dict[str, Any] = field(default_factory=dict)
    #: `retention:`, parsed (`_retention`): clear_text_after_days, dropped, kept_domains.
    retention: dict[str, Any] = field(default_factory=dict)
    #: Registry model names, added to `ai_terms` at run time (read-only).
    extra_ai_terms: tuple[str, ...] = field(default=())

    @property
    def all_ai_terms(self) -> tuple[str, ...]:
        return self.ai_terms + self.extra_ai_terms

    @property
    def active_domains(self) -> list[str]:
        return [k for k, d in self.domains.items() if d.active]

    def group_for(self, day: date) -> str:
        """The rotation group a scheduled run on `day` (UTC) harvests: `a` on an
        even proleptic ordinal, `b` on an odd one. The ordinal, not the day of the
        year, so the groups alternate across a year end (365 is odd)."""
        return ROTATION_GROUPS[day.toordinal() % 2]

    def group_domains(self, group: str) -> list[str]:
        """The group's domains, in the contract's order."""
        if group not in ROTATION_GROUPS:
            raise IndustryAIConfigError(
                f"no rotation group {group!r}; the groups are {ROTATION_GROUPS}")
        members = set(self.run["rotation"]["groups"][group])
        return [k for k in self.domains if k in members]

    def x_pages(self, query: str) -> int:
        """Pages for one X query: `x_clubbed` when it clubs at least
        `x_clubbed_min_keywords` quoted keywords, else `x` (#644 review, point 10:
        one page of 20 cannot hold six keywords' worth of posts). A WATCH query
        (`from:` accounts) gets `watch.x_pages`: one prolific account fills a page,
        so the window is paged rather than its first page read (probe 2026-11-20:
        swyx 16 of 20 posts on one page over five accounts)."""
        if is_watch_x(query):
            return int(self.watch["x_pages"])
        pages = self.run["pages_per_query"]
        clubbed = len(_QUOTED.findall(query)) >= int(self.run["x_clubbed_min_keywords"])
        return int(pages["x_clubbed"] if clubbed else pages["x"])

    def person_by_handle(self) -> dict[tuple[str, str], str]:
        """(platform, handle lower-cased) -> person, from `watch.people`."""
        return {(p, h.lower()): person
                for person, hs in self.watch.get("people", {}).items()
                for p, h in hs.items() if p in PEOPLE_PLATFORMS}

    def person_by_did(self) -> dict[str, str]:
        """Bluesky DID -> person, for the people whose `bluesky_did` is written."""
        return {hs["bluesky_did"]: person
                for person, hs in self.watch.get("people", {}).items() if "bluesky_did" in hs}

    def watch_queries(self) -> list[tuple[str, str]]:
        """Every (platform, query) the observer asks, in file order. No network.

        Reddit: `r/<sub>` (a listing, newest first). X: accounts clubbed with OR as
        `(from:a OR from:b ...)`; harvest adds `since:` and the suffix. Bluesky:
        `from:<handle>`. Hacker News: `hn:list:<tag>` or `hn:author:<name>`.
        Instagram: `ig:<handle>` (one feed request; the id is in `instagram_ids`)."""
        w = self.watch
        out = [("reddit", f"r/{s}") for s in w["reddit"]]
        accts, n = list(w["x"]), int(w["x_club_max"])
        out += [("x", "(" + " OR ".join(f"from:{a}" for a in accts[i:i + n]) + ")")
                for i in range(0, len(accts), n)]
        out += [("bluesky", f"from:{h}") for h in w["bluesky"]]
        out += [("hackernews", f"hn:list:{t}") for t in w["hackernews"]["lists"]]
        out += [("hackernews", f"hn:author:{a}") for a in w["hackernews"]["authors"]]
        out += [("instagram", f"ig:{h}") for h, _ in w["instagram"]]
        return out

    def instagram_ids(self) -> dict[str, str]:
        """Watched Instagram handle -> the account's numeric id, as the contract holds it."""
        return dict(self.watch["instagram"])


def is_watch_x(query: str) -> bool:
    """An X watch query names accounts with `from:`; a keyword query never does."""
    return query.startswith("(from:")


def _need(block: dict, key: str, where: str) -> Any:
    if not isinstance(block, dict) or key not in block:
        raise IndustryAIConfigError(f"{where}: `{key}` is required")
    return block[key]


def _known(block: Any, allowed: set[str], where: str) -> None:
    """Refuse a key the code does not read (rule 12)."""
    if not isinstance(block, dict):
        raise IndustryAIConfigError(f"{where} must be a mapping")
    extra = sorted(set(block) - allowed)
    if extra:
        raise IndustryAIConfigError(
            f"{where}: unknown key(s) {extra} - not implemented, so refused rather than ignored; "
            f"allowed: {sorted(allowed)}"
        )


def _whole(value: Any, where: str, *, positive: bool = True) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < (1 if positive else 0):
        raise IndustryAIConfigError(
            f"{where} must be a whole number {'> 0' if positive else '>= 0'}"
        )
    return value


def _strings(value: Any, where: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        raise IndustryAIConfigError(f"{where} must be a list of non-empty strings")
    if not value and not allow_empty:
        raise IndustryAIConfigError(f"{where} must not be empty")
    return tuple(v.strip() for v in value)


def _patterns(value: Any, where: str) -> tuple[re.Pattern, ...]:
    out = []
    for i, p in enumerate(_strings(value, where)):
        try:
            out.append(re.compile(p, re.IGNORECASE))
        except re.error as e:
            raise IndustryAIConfigError(f"{where}[{i}] is not a valid pattern ({e}): {p!r}") from e
    return tuple(out)


def _queries(q: Any, where: str, suffix: dict[str, str]) -> dict[str, Any]:
    _known(q, set(PLATFORMS), where)
    if set(q) != set(PLATFORMS):
        raise IndustryAIConfigError(f"{where} must name exactly {sorted(PLATFORMS)}")
    for p in PLATFORMS:
        if p == "feeds":
            _strings(q[p], f"{where}.feeds")
            continue
        _known(q[p], QUERY_KEYS[p], f"{where}.{p}")
        for k in sorted(QUERY_KEYS[p]):
            _strings(_need(q[p], k, f"{where}.{p}"), f"{where}.{p}.{k}")
    # X CUTS OFF A LONG QUERY RATHER THAN REFUSING IT (#644 review, point 10), so
    # the keywords at the end would silently go unsearched. Refused here instead.
    for s in q["x"]["search"]:
        full = f"{s} {suffix.get('x', '')}".strip()
        if len(full) > MAX_QUERY_CHARS:
            raise IndustryAIConfigError(
                f"{where}.x.search: {len(full)} characters with the suffix, over X's "
                f"{MAX_QUERY_CHARS}: {s[:60]!r}..."
            )
    return q


def _terms(block: dict, where: str, suffix: dict[str, str]) -> Terms:
    amb = _need(block, "ambiguous_terms", where)
    if not isinstance(amb, dict):
        raise IndustryAIConfigError(f"{where}.ambiguous_terms must be a mapping")
    return Terms(
        domain_terms=_strings(_need(block, "domain_terms", where), f"{where}.domain_terms"),
        ambiguous_terms={
            t: _strings(c, f"{where}.ambiguous_terms.{t}", allow_empty=False)
            for t, c in amb.items()
        },
        exclude_phrases=_patterns(
            _need(block, "exclude_phrases", where), f"{where}.exclude_phrases"
        ),
        queries=_queries(_need(block, "queries", where), f"{where}.queries", suffix),
    )


def _handles(value: Any, pattern: re.Pattern, where: str) -> tuple[str, ...]:
    """A watch list: strings in the platform's own handle format, no repeats."""
    out = _strings(value, where)
    bad = [h for h in out if not pattern.match(h)]
    if bad:
        raise IndustryAIConfigError(f"{where}: not a valid name {bad}")
    dupes = sorted({h for h in out if out.count(h) > 1})
    if dupes:
        raise IndustryAIConfigError(f"{where}: listed twice {dupes}")
    return out


def _instagram(value: Any) -> tuple[tuple[str, str], ...]:
    """`watch.instagram`: `[handle, "id"]` pairs (2026-11-25). A list rather than a
    mapping because YAML lets a repeated mapping key silently replace the first
    (rule 12); here a repeat - of a handle or of an id - is refused."""
    where = "watch.instagram"
    if not isinstance(value, list):
        raise IndustryAIConfigError(f"{where} must be a list of [handle, id] pairs")
    out = []
    for i, pair in enumerate(value):
        if (not isinstance(pair, list) or len(pair) != 2
                or not all(isinstance(x, str) for x in pair)):
            raise IndustryAIConfigError(
                f"{where}[{i}]: {pair!r} is not a [handle, \"id\"] pair of two strings")
        handle, uid = pair
        if not _IG_HANDLE.match(handle):
            raise IndustryAIConfigError(f"{where}[{i}]: not a valid name {handle!r}")
        if not _IG_ID.match(uid):
            raise IndustryAIConfigError(f"{where}[{i}]: {uid!r} is not a numeric account id")
        out.append((handle, uid))
    for k, label in ((0, "handle"), (1, "id")):
        seen = [p[k].lower() for p in out]
        dupes = sorted({s for s in seen if seen.count(s) > 1})
        if dupes:
            raise IndustryAIConfigError(f"{where}: {label} listed twice {dupes}")
    return tuple(out)


def _watch(raw: Any, suffix: dict[str, str]) -> dict[str, Any]:
    """The observer's `watch:` block, every key required (rule 12)."""
    where = "watch"
    _known(raw, WATCH_KEYS, where)
    for key in sorted(WATCH_KEYS):
        _need(raw, key, where)
    if not isinstance(raw["enabled"], bool):
        raise IndustryAIConfigError("watch.enabled must be true or false")
    for key in ("lookback_days", "x_pages", "x_club_max", "cross_post_hours"):
        _whole(raw[key], f"watch.{key}")
    caps = raw["max_requests"]
    _known(caps, set(WATCH_PLATFORMS), "watch.max_requests")
    if set(caps) != set(WATCH_PLATFORMS):
        raise IndustryAIConfigError(
            f"watch.max_requests must name exactly {sorted(WATCH_PLATFORMS)}"
        )
    for p, n in caps.items():
        _whole(n, f"watch.max_requests.{p}", positive=False)
    if not isinstance(raw["x_suffix"], str):
        raise IndustryAIConfigError("watch.x_suffix must be a string (may be empty)")
    hn = raw["hackernews"]
    _known(hn, HN_WATCH_KEYS, "watch.hackernews")
    lists = _strings(_need(hn, "lists", "watch.hackernews"), "watch.hackernews.lists")
    unknown = [t for t in lists if t not in HN_LISTS]
    if unknown:
        raise IndustryAIConfigError(
            f"watch.hackernews.lists: unknown {unknown}; known {list(HN_LISTS)}"
        )
    out = {
        "enabled": raw["enabled"],
        "lookback_days": int(raw["lookback_days"]),
        "max_requests": {p: int(caps[p]) for p in WATCH_PLATFORMS},
        "x_pages": int(raw["x_pages"]),
        "x_club_max": int(raw["x_club_max"]),
        "x_suffix": raw["x_suffix"].strip(),
        "cross_post_hours": int(raw["cross_post_hours"]),
        "reddit": _handles(raw["reddit"], _REDDIT_SUB, "watch.reddit"),
        "x": _handles(raw["x"], _X_HANDLE, "watch.x"),
        "bluesky": _handles(raw["bluesky"], _BSKY_HANDLE, "watch.bluesky"),
        "hackernews": {
            "lists": lists,
            "authors": _handles(_need(hn, "authors", "watch.hackernews"), _HN_USER,
                                "watch.hackernews.authors"),
        },
        "instagram": _instagram(raw["instagram"]),
    }
    # X CUTS OFF A LONG QUERY RATHER THAN REFUSING IT, so a clubbed account list
    # plus `since:` and both suffixes must fit (the keyword queries' guard, #644).
    accts, n = list(out["x"]), out["x_club_max"]
    for i in range(0, len(accts), n):
        q = "(" + " OR ".join(f"from:{a}" for a in accts[i:i + n]) + ")"
        full = " ".join(s for s in (q, suffix.get("x", ""), out["x_suffix"]) if s)
        if len(full) + _SINCE_CHARS > MAX_QUERY_CHARS:
            raise IndustryAIConfigError(
                f"watch.x: {len(full) + _SINCE_CHARS} characters with since: and the suffixes, "
                f"over X's {MAX_QUERY_CHARS}; lower watch.x_club_max"
            )
    out["people"] = _people(raw["people"], out)
    return out


def _people(raw: Any, watch: dict[str, Any]) -> dict[str, dict[str, str]]:
    """`watch.people`: one person, their handles on several platforms (2026-11-20).

    Lets the pipeline count a person ONCE as an author, and fold their same post on two
    platforms into one item. Strict, so the map cannot drift from the lists: every
    handle must be one the watch list for that platform already holds, and no handle
    may belong to two people. We never GUESS that two handles are one person - only
    a person written here is linked.

    `bluesky_did` (optional, 2026-11-24, #653 review): the Bluesky account's DID,
    resolved once by hand from its handle. A Bluesky post's author field IS the DID,
    so a post found by a keyword query - not by the `from:` watch query - links too,
    and a handle that has passed to another account links no one (rules.person_of)."""
    if not isinstance(raw, dict):
        raise IndustryAIConfigError("watch.people must be a mapping of person -> handles")
    listed = {"x": set(watch["x"]), "bluesky": set(watch["bluesky"]),
              "hackernews": set(watch["hackernews"]["authors"])}
    out, owner, dids = {}, {}, {}
    for person, entry in raw.items():
        where = f"watch.people.{person}"
        if not isinstance(person, str) or not _PERSON_KEY.match(person):
            raise IndustryAIConfigError(f"{where}: a person key is lower-case letters, digits, _")
        _known(entry, {*PEOPLE_PLATFORMS, "bluesky_did"}, where)
        handles = {p: h for p, h in entry.items() if p in PEOPLE_PLATFORMS}
        if len(handles) < 2:
            raise IndustryAIConfigError(f"{where}: map a person on at least two platforms")
        did = entry.get("bluesky_did")
        if did is not None:
            if "bluesky" not in handles:
                raise IndustryAIConfigError(f"{where}.bluesky_did: needs a bluesky handle")
            if not isinstance(did, str) or not _BLUESKY_DID.match(did):
                raise IndustryAIConfigError(f"{where}.bluesky_did: {did!r} is not a Bluesky DID")
            if did in dids:
                raise IndustryAIConfigError(f"{where}.bluesky_did: already belongs to {dids[did]}")
            dids[did] = person
        for platform, h in handles.items():
            if not isinstance(h, str) or h not in listed[platform]:
                raise IndustryAIConfigError(
                    f"{where}.{platform}: {h!r} is not in the {platform} watch list")
            key = (platform, h.lower())
            if key in owner:
                raise IndustryAIConfigError(
                    f"{where}.{platform}: {h!r} already belongs to {owner[key]}")
            owner[key] = person
        out[person] = {p: str(h) for p, h in handles.items()}
        if did is not None:
            out[person]["bluesky_did"] = did
    return out


def parse(raw: dict) -> Config:
    if not isinstance(raw, dict):
        raise IndustryAIConfigError("contract/industry_ai.yaml is not a mapping")
    _known(raw, TOP_KEYS, "top level")
    run = _need(raw, "run", "top level")
    _known(run, RUN_KEYS, "run")
    for key in sorted(RUN_KEYS):
        _need(run, key, "run")
    if not isinstance(run["enabled"], bool):
        raise IndustryAIConfigError("run.enabled must be true or false")
    caps = run["max_requests"]
    _known(caps, set(PLATFORMS), "run.max_requests")
    if set(caps) != set(PLATFORMS):
        raise IndustryAIConfigError(f"run.max_requests must name exactly {sorted(PLATFORMS)}")
    for p, n in caps.items():
        _whole(n, f"run.max_requests.{p}", positive=False)
    pages = run["pages_per_query"]
    _known(pages, PAGE_KEYS, "run.pages_per_query")
    for k in sorted(PAGE_KEYS):
        _whole(_need(pages, k, "run.pages_per_query"), f"run.pages_per_query.{k}")
    for key in ("window_days", "min_text_chars", "context_window_words", "x_clubbed_min_keywords"):
        _whole(run[key], f"run.{key}")
    _whole(run["low_engagement_max"], "run.low_engagement_max", positive=False)

    suffix = raw.get("query_suffix") or {}
    _known(suffix, set(PLATFORMS), "query_suffix")
    suffix = {str(k): str(v) for k, v in suffix.items()}

    type_order = _strings(_need(raw, "type_order", "top level"), "type_order", allow_empty=False)
    if set(type_order) != set(CONTENT_TYPES) or len(type_order) != len(CONTENT_TYPES):
        raise IndustryAIConfigError(f"type_order must list each of {sorted(CONTENT_TYPES)} once")
    tp = _need(raw, "type_patterns", "top level")
    _known(tp, set(CONTENT_TYPES), "type_patterns")
    if set(tp) != set(CONTENT_TYPES):
        raise IndustryAIConfigError(f"type_patterns must name exactly {sorted(CONTENT_TYPES)}")
    sp = _need(raw, "stage_patterns", "top level")
    _known(sp, set(STAGES), "stage_patterns")
    if set(sp) != set(STAGES):
        raise IndustryAIConfigError(f"stage_patterns must name exactly {sorted(STAGES)}")

    raw_domains = _need(raw, "domains", "top level")
    if not isinstance(raw_domains, dict) or not raw_domains:
        raise IndustryAIConfigError("domains must be a non-empty mapping")
    domains = {}
    for key, d in raw_domains.items():
        where = f"domains.{key}"
        _known(d, DOMAIN_KEYS, where)
        kind = _need(d, "kind", where)
        if kind not in KINDS:
            raise IndustryAIConfigError(f"{where}.kind must be one of {list(KINDS)}, not {kind!r}")
        active = _need(d, "active", where)
        if not isinstance(active, bool):
            raise IndustryAIConfigError(f"{where}.active must be true or false")
        groups = {}
        for gkey, g in (d.get("groups") or {}).items():
            gwhere = f"{where}.groups.{gkey}"
            _known(g, GROUP_KEYS, gwhere)
            groups[gkey] = Group(
                key=gkey,
                name=str(_need(g, "name", gwhere)),
                definition=g.get("definition"),
                terms=_terms(g, gwhere, suffix),
            )
            if not groups[gkey].terms.any_terms:
                raise IndustryAIConfigError(f"{gwhere} has no terms")
        terms = _terms(d, where, suffix)
        if not terms.any_terms and not groups:
            raise IndustryAIConfigError(f"{where} has no terms and no groups")
        domains[key] = Domain(
            key=key,
            name=str(_need(d, "name", where)),
            kind=kind,
            active=active,
            definition=str(_need(d, "definition", where)),
            terms=terms,
            groups=groups,
        )
    if not any(d.active for d in domains.values()):
        raise IndustryAIConfigError("no domain is `active: true`; nothing would be harvested")
    _rotation(run["rotation"], domains)

    return Config(
        pipeline_version=str(_need(raw, "pipeline_version", "top level")),
        run=run,
        query_suffix=suffix,
        ai_terms=_strings(_need(raw, "ai_terms", "top level"), "ai_terms", allow_empty=False),
        global_exclude=_patterns(
            _need(raw, "global_exclude_phrases", "top level"), "global_exclude_phrases"
        ),
        spam=_patterns(_need(raw, "spam_patterns", "top level"), "spam_patterns"),
        ads=_patterns(_need(raw, "ad_patterns", "top level"), "ad_patterns"),
        teach=_patterns(_need(raw, "teach_patterns", "top level"), "teach_patterns"),
        hiring=_patterns(_need(raw, "hiring_patterns", "top level"), "hiring_patterns"),
        promo=_patterns(_need(raw, "promo_patterns", "top level"), "promo_patterns"),
        type_order=type_order,
        type_patterns={t: _patterns(tp[t], f"type_patterns.{t}") for t in CONTENT_TYPES},
        # The contract's own order: the first stage whose pattern matches wins.
        stage_patterns={s: _patterns(sp[s], f"stage_patterns.{s}") for s in sp},
        domains=domains,
        watch=_watch(_need(raw, "watch", "top level"), suffix),
        retention=_retention(_need(raw, "retention", "top level"), domains),
    )


def _rotation(raw: Any, domains: dict[str, Domain]) -> None:
    """`run.rotation` (2026-11-25): the domains in two groups a scheduled run
    alternates between. EVERY DOMAIN IN EXACTLY ONE GROUP: a domain in neither
    would never be harvested on a schedule, and one in both would be harvested
    twice as often - both silently, so both are refused (rule 12)."""
    where = "run.rotation"
    if not isinstance(raw, dict):
        raise IndustryAIConfigError(f"{where} must be a mapping")
    _known(raw, {"by", "groups"}, where)
    by = _need(raw, "by", where)
    if by not in ROTATION_BY:
        raise IndustryAIConfigError(f"{where}.by must be one of {sorted(ROTATION_BY)}, not {by!r}")
    groups = _need(raw, "groups", where)
    if not isinstance(groups, dict) or set(groups) != set(ROTATION_GROUPS):
        raise IndustryAIConfigError(f"{where}.groups must name exactly {list(ROTATION_GROUPS)}")
    seen: dict[str, str] = {}
    for g in ROTATION_GROUPS:
        members = _strings(groups[g], f"{where}.groups.{g}", allow_empty=False)
        for k in members:
            if k not in domains:
                raise IndustryAIConfigError(f"{where}.groups.{g}: no domain {k!r}")
            if k in seen:
                raise IndustryAIConfigError(
                    f"{where}: {k!r} is in group {seen[k]!r} and group {g!r}; one only")
            seen[k] = g
    missing = [k for k in domains if k not in seen]
    if missing:
        raise IndustryAIConfigError(
            f"{where}: {missing} in no group, so never harvested on a schedule")


def _retention(raw: Any, domains: dict[str, Domain]) -> dict[str, Any]:
    """`retention:`, every key required (rule 12). `kept_domains` must name domains
    the contract has: a misspelt key would silently keep that domain's text."""
    where = "retention"
    _known(raw, RETENTION_KEYS, where)
    for key in sorted(RETENTION_KEYS):
        _need(raw, key, where)
    _whole(raw["clear_text_after_days"], "retention.clear_text_after_days")
    if not isinstance(raw["dropped"], bool):
        raise IndustryAIConfigError("retention.dropped must be true or false")
    kept = _strings(raw["kept_domains"], "retention.kept_domains")
    unknown = sorted(set(kept) - set(domains))
    if unknown:
        raise IndustryAIConfigError(f"retention.kept_domains: unknown domain(s) {unknown}")
    return {"clear_text_after_days": int(raw["clear_text_after_days"]),
            "dropped": raw["dropped"], "kept_domains": tuple(kept)}


def load(path: Path | None = None) -> Config:
    return parse(yaml.safe_load((path or CONTRACT).read_text(encoding="utf-8")))
