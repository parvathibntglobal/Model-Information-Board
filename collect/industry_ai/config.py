"""contract/industry_ai.yaml, read strictly.

Every key the lane uses is required and checked here, once, before a request is
made (rule 12): a missing key, an unknown platform, a domain with no terms or a
pattern that is not a valid regular expression stops the run with a message
naming it. Nothing is defaulted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contract" / "industry_ai.yaml"

#: The platforms this lane harvests. `feeds` is the blog/RSS arm.
PLATFORMS = ("reddit", "x", "github", "hackernews", "devto", "bluesky", "feeds")
#: The content types, in no particular order; `type_order` sets precedence.
CONTENT_TYPES = ("use_case", "how_to", "tool_or_product", "research", "news", "discussion")
STAGES = ("deployed", "pilot", "first_hand")
#: The fallback type, said by the contract's own `type_order`, never invented.
DEFAULT_TYPE = "discussion"


class IndustryAIConfigError(ValueError):
    """contract/industry_ai.yaml is missing a key or holds a wrong value."""


@dataclass(frozen=True)
class Domain:
    key: str
    name: str
    definition: str
    domain_terms: tuple[str, ...]
    ambiguous_terms: dict[str, tuple[str, ...]]
    exclude_phrases: tuple[re.Pattern, ...]
    queries: dict[str, Any]
    feeds: tuple[str, ...]


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


def _need(block: dict, key: str, where: str) -> Any:
    if not isinstance(block, dict) or key not in block:
        raise IndustryAIConfigError(f"{where}: `{key}` is required")
    return block[key]


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


def parse(raw: dict) -> Config:
    if not isinstance(raw, dict):
        raise IndustryAIConfigError("contract/industry_ai.yaml is not a mapping")
    run = _need(raw, "run", "top level")
    for key in (
        "enabled",
        "window_days",
        "max_requests",
        "pages_per_query",
        "min_text_chars",
        "context_window_words",
        "low_engagement_max",
    ):
        _need(run, key, "run")
    if not isinstance(run["enabled"], bool):
        raise IndustryAIConfigError("run.enabled must be true or false")
    caps = run["max_requests"]
    if not isinstance(caps, dict) or set(caps) != set(PLATFORMS):
        raise IndustryAIConfigError(f"run.max_requests must name exactly {sorted(PLATFORMS)}")
    for p, n in caps.items():
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            raise IndustryAIConfigError(f"run.max_requests.{p} must be a whole number >= 0")
    for key in ("window_days", "min_text_chars", "context_window_words"):
        if isinstance(run[key], bool) or not isinstance(run[key], int) or run[key] <= 0:
            raise IndustryAIConfigError(f"run.{key} must be a positive whole number")

    type_order = _strings(_need(raw, "type_order", "top level"), "type_order", allow_empty=False)
    if set(type_order) != set(CONTENT_TYPES) or len(type_order) != len(CONTENT_TYPES):
        raise IndustryAIConfigError(f"type_order must list each of {sorted(CONTENT_TYPES)} once")
    tp = _need(raw, "type_patterns", "top level")
    if not isinstance(tp, dict) or set(tp) != set(CONTENT_TYPES):
        raise IndustryAIConfigError(f"type_patterns must name exactly {sorted(CONTENT_TYPES)}")
    sp = _need(raw, "stage_patterns", "top level")
    if not isinstance(sp, dict) or set(sp) != set(STAGES):
        raise IndustryAIConfigError(f"stage_patterns must name exactly {sorted(STAGES)}")

    raw_domains = _need(raw, "domains", "top level")
    if not isinstance(raw_domains, dict) or not raw_domains:
        raise IndustryAIConfigError("domains must be a non-empty mapping")
    domains = {}
    for key, d in raw_domains.items():
        where = f"domains.{key}"
        for k in (
            "name",
            "definition",
            "domain_terms",
            "ambiguous_terms",
            "exclude_phrases",
            "queries",
        ):
            _need(d, k, where)
        amb = d["ambiguous_terms"]
        if not isinstance(amb, dict):
            raise IndustryAIConfigError(f"{where}.ambiguous_terms must be a mapping")
        queries = d["queries"]
        if not isinstance(queries, dict) or set(queries) != set(PLATFORMS):
            raise IndustryAIConfigError(f"{where}.queries must name exactly {sorted(PLATFORMS)}")
        for p in PLATFORMS:
            q = queries[p]
            if p == "feeds":
                _strings(q, f"{where}.queries.feeds")
            elif p == "reddit":
                _need(q, "subreddits", f"{where}.queries.reddit")
                _need(q, "search", f"{where}.queries.reddit")
                _strings(q["subreddits"], f"{where}.queries.reddit.subreddits")
                _strings(q["search"], f"{where}.queries.reddit.search")
            else:
                _strings(_need(q, "search", f"{where}.queries.{p}"), f"{where}.queries.{p}.search")
        domains[key] = Domain(
            key=key,
            name=str(d["name"]),
            definition=str(d["definition"]),
            domain_terms=_strings(d["domain_terms"], f"{where}.domain_terms", allow_empty=False),
            ambiguous_terms={
                t: _strings(c, f"{where}.ambiguous_terms.{t}", allow_empty=False)
                for t, c in amb.items()
            },
            exclude_phrases=_patterns(d["exclude_phrases"], f"{where}.exclude_phrases"),
            queries=queries,
            feeds=tuple(queries["feeds"]),
        )

    return Config(
        pipeline_version=str(_need(raw, "pipeline_version", "top level")),
        run=run,
        query_suffix={str(k): str(v) for k, v in (raw.get("query_suffix") or {}).items()},
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
