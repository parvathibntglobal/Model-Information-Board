"""The Industry AI agent's rules, as pure functions over one item's text.

No network, no database, no language model. Everything tunable comes from
contract/industry_ai.yaml (`config.Config`); this module only applies it. The
same functions run on a fresh harvest and on `--relabel` over stored items, so a
rule change re-labels the whole collection without a request.

STAGE ORDER, as the pipeline calls them (plan §3): window, sieve, [dedupe, in
pipeline.py, across items], filter, label. Every drop names its reason.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from collect.industry_ai.config import DEFAULT_TYPE, Config, Domain

# ── the item ─────────────────────────────────────────────────────────────────


@dataclass
class Item:
    """One harvested post or article: only the ROOT's title and body are read."""

    id: str  # "<platform>:<external_id>"
    platform: str
    external_id: str
    url: str
    title: str
    body: str
    created_at: datetime | None
    author_id: str | None = None
    lang: str | None = None
    engagement: dict = field(default_factory=dict)
    #: The article a post links to, when it links to one (a Reddit link post,
    #: a Hacker News story, a URL in a tweet). Used for cross-platform dedupe.
    link: str | None = None
    discovery_ref: str | None = None
    domain_hints: set[str] = field(default_factory=set)
    query_keys: set[str] = field(default_factory=set)

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.body}".strip()


@dataclass
class Verdict:
    """What the rules made of one item. `reason` is set exactly when dropped."""

    kept: bool
    reason: str | None = None
    flags: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    content_type: str | None = None
    matched_pattern: str | None = None
    stage_guess: str | None = None


# ── text helpers ─────────────────────────────────────────────────────────────

_URL = re.compile(r"https?://\S+", re.IGNORECASE)
_WORD = re.compile(r"[A-Za-z']+")

#: Query parameters that track a click and never change what a page is.
TRACKING_PARAMS = re.compile(
    r"^(utm_\w+|ref|ref_src|ref_url|fbclid|gclid|dclid|msclkid|mc_cid|mc_eid|igshid|"
    r"si|s|t|cmpid|_hsenc|_hsmi|source|share)$",
    re.IGNORECASE,
)

#: Hosts whose pages are posts, not articles: a link to one is not an article
#: share, so it is not used for cross-platform dedupe.
SOCIAL_HOSTS = (
    "reddit.com",
    "redd.it",
    "x.com",
    "twitter.com",
    "t.co",
    "bsky.app",
    "news.ycombinator.com",
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "youtube.com",
    "youtu.be",
    "tiktok.com",
)

#: A small set of English function words for the language check. Measured
#: nothing yet: a weight-like heuristic, applied only where the platform did
#: not declare a language (plan §3 stage 5, rule 8 - checked in the §7 sample).
_EN_STOPWORDS = frozenset(
    [
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "of",
        "to",
        "in",
        "on",
        "for",
        "with",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "it",
        "this",
        "that",
        "we",
        "our",
        "you",
        "your",
        "they",
        "their",
        "i",
        "my",
        "as",
        "at",
        "by",
        "from",
        "not",
        "have",
        "has",
        "had",
        "will",
        "can",
        "do",
        "does",
        "about",
        "how",
        "what",
        "which",
        "who",
        "when",
    ]
)


def strip_links(text: str) -> str:
    return _URL.sub(" ", text or "")


def first_link(text: str) -> str | None:
    m = _URL.search(text or "")
    return m.group(0).rstrip(").,;'\"]") if m else None


def canonical_url(url: str | None) -> str | None:
    """The same page, however it was linked: no tracking parameters, lower-case
    host without `www.`, no fragment, no trailing slash. None for no URL."""
    if not url:
        return None
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    query = urlencode(
        [
            (k, v)
            for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if not TRACKING_PARAMS.match(k)
        ]
    )
    path = parts.path.rstrip("/") or ""
    return urlunsplit(("https", host, path, query, ""))


def is_article_link(url: str | None) -> bool:
    c = canonical_url(url)
    if not c:
        return False
    host = urlsplit(c).netloc
    return not any(host == h or host.endswith("." + h) for h in SOCIAL_HOSTS)


def normalized_text(text: str) -> str:
    """For exact-repeat detection: links and punctuation out, case folded."""
    return " ".join(_WORD.findall(strip_links(text).lower()))


# ── term matching ────────────────────────────────────────────────────────────


@lru_cache(maxsize=4096)
def term_pattern(term: str) -> re.Pattern:
    """A term as whole words; a space, hyphen or underscore inside it matches any
    of the three. Case-insensitive."""
    words = [re.escape(w) for w in re.split(r"[\s\-_]+", term.strip()) if w]
    return re.compile(r"(?<![\w])" + r"[\s\-_]+".join(words) + r"(?![\w])", re.IGNORECASE)


def has_term(text: str, term: str) -> bool:
    return term_pattern(term).search(text) is not None


def remove(text: str, patterns) -> str:
    for p in patterns:
        text = p.sub(" ", text)
    return text


_BARE_AI = re.compile(r"(?<![\w.])AI(?![\w])")  # upper-case only, not ".ai"


def ai_terms_found(text: str, cfg: Config) -> list[str]:
    """The AI terms an item names, after the global exclusions are removed. The
    bare word "AI" counts in capitals only, as a whole word: lower-case "ai"
    and ".ai" (a file type or a web domain) never do."""
    clean = remove(text, cfg.global_exclude)
    found = [t for t in cfg.all_ai_terms if has_term(clean, t)]
    if not found and _BARE_AI.search(clean):
        found.append("AI")
    return found


def _near(words: list[str], i: int, context: tuple[str, ...], window: int) -> bool:
    span = " ".join(words[max(0, i - window) : i + window + 1])
    return any(has_term(span, c) for c in context)


def domain_terms_found(text: str, domain: Domain, cfg: Config) -> list[str]:
    """The domain's terms in the item, outside every excluded phrase. An
    ambiguous term counts only with one of its context words nearby."""
    clean = remove(remove(text, cfg.global_exclude), domain.exclude_phrases)
    found = [t for t in domain.domain_terms if has_term(clean, t)]
    if domain.ambiguous_terms:
        words = clean.split()
        window = int(cfg.run["context_window_words"])
        for term, context in domain.ambiguous_terms.items():
            pat = term_pattern(term)
            for i, w in enumerate(words):
                if pat.fullmatch(w.strip(".,;:!?()[]\"'")) and _near(words, i, context, window):
                    found.append(term)
                    break
    return found


# ── the stages ───────────────────────────────────────────────────────────────


def outside_window(item: Item, since: datetime) -> bool:
    """Posted before the window. An undated item is NOT outside it (rule 6):
    it is kept and stays undated."""
    return item.created_at is not None and item.created_at < since


def sieve(item: Item, cfg: Config) -> tuple[str | None, dict[str, list[str]]]:
    """(drop reason or None, domain -> matched terms). Needs an AI term and a
    domain term from ANY domain; which domain it is gets decided in `label`."""
    text = item.text
    if not ai_terms_found(text, cfg):
        return "no_ai_term", {}
    matched = {k: t for k, d in cfg.domains.items() if (t := domain_terms_found(text, d, cfg))}
    if not matched:
        return "no_domain_term", {}
    return None, matched


def _english(item: Item) -> bool:
    if item.lang:
        return item.lang.lower().startswith("en")
    words = _WORD.findall(strip_links(item.text).lower())
    if len(words) < 8:
        return True  # too little text to judge; not a drop
    letters = [c for c in item.text if c.isalpha()]
    if letters and sum(1 for c in letters if not c.isascii()) / len(letters) > 0.3:
        return False
    return sum(1 for w in words if w in _EN_STOPWORDS) / len(words) >= 0.04


def _any(patterns, text: str) -> re.Pattern | None:
    return next((p for p in patterns if p.search(text)), None)


def filter_reason(
    item: Item, cfg: Config, *, is_bot=lambda item: False
) -> tuple[str | None, list[str]]:
    """(drop reason or None, flags). Run order: short, bot, language, spam,
    promo, hiring, sign-up ad (unless it teaches), then the pure-link case."""
    flags: list[str] = []
    text = item.text
    bare = strip_links(text).strip()
    min_chars = int(cfg.run["min_text_chars"])

    if len(bare) < min_chars:
        # A PURE LINK POST IS NOT DROPPED OUTRIGHT when it shares an article:
        # it is kept and deduped onto the article by its link (plan §3 stage 5).
        if is_article_link(item.link or first_link(text)):
            flags.append("link_share")
        else:
            return "too_short", flags
    if is_bot(item):
        return "bot", flags
    if not _english(item):
        return "non_english", flags
    if _any(cfg.spam, text):
        return "spam", flags
    if _any(cfg.promo, text):
        return "promo", flags
    if _any(cfg.hiring, text):
        return "hiring", flags
    if _any(cfg.ads, text) and not _any(cfg.teach, text):
        return "signup_ad", flags

    floor = cfg.run["low_engagement_max"]
    signal = [
        v
        for k, v in (item.engagement or {}).items()
        if k in ("score", "likes", "reactions", "points") and isinstance(v, int)
    ]
    if signal and max(signal) <= floor:
        flags.append("low_engagement")
    return None, flags


def label(item: Item, matched: dict[str, list[str]], cfg: Config) -> Verdict:
    """Domain(s), content type and stage, for an item every filter kept.

    DOMAIN: the domains whose queries found the item, confirmed by their own
    terms. None confirmed means `domains` is empty - the "domain unconfirmed"
    bucket, never a guess; another domain whose terms matched is recorded as a
    flag only.
    """
    domains = sorted(d for d in item.domain_hints if d in matched)
    flags = [f"also_matches:{d}" for d in sorted(matched) if d not in item.domain_hints]
    text = item.text

    content_type, why = None, None
    for t in cfg.type_order:
        hit = _any(cfg.type_patterns[t], text)
        if hit:
            content_type, why = t, hit.pattern
            break
    # GitHub items are tools and code by default; only a stated use overrides.
    if item.platform == "github" and content_type != "use_case":
        content_type, why = "tool_or_product", "platform:github"
    if content_type is None:
        content_type = DEFAULT_TYPE

    stage = None
    if content_type == "use_case":
        stage = next((s for s, pats in cfg.stage_patterns.items() if _any(pats, text)), None)
    return Verdict(
        kept=True,
        flags=flags,
        domains=domains,
        content_type=content_type,
        matched_pattern=why,
        stage_guess=stage,
    )
