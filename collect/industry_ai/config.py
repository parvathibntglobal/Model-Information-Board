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
}
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
}
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
    #: Registry model names, added to `ai_terms` at run time (read-only).
    extra_ai_terms: tuple[str, ...] = field(default=())

    @property
    def all_ai_terms(self) -> tuple[str, ...]:
        return self.ai_terms + self.extra_ai_terms

    @property
    def active_domains(self) -> list[str]:
        return [k for k, d in self.domains.items() if d.active]

    def x_pages(self, query: str) -> int:
        """Pages for one X query: `x_clubbed` when it clubs at least
        `x_clubbed_min_keywords` quoted keywords, else `x` (#644 review, point 10:
        one page of 20 cannot hold six keywords' worth of posts)."""
        pages = self.run["pages_per_query"]
        clubbed = len(_QUOTED.findall(query)) >= int(self.run["x_clubbed_min_keywords"])
        return int(pages["x_clubbed"] if clubbed else pages["x"])


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
    )


def load(path: Path | None = None) -> Config:
    return parse(yaml.safe_load((path or CONTRACT).read_text(encoding="utf-8")))
