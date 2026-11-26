"""The Industry AI agent's rules, as pure functions over one item's text.

No network, no database, no language model. Everything tunable comes from
contract/industry_ai.yaml (`config.Config`); this module only applies it. The
same functions run on a fresh harvest and on `--relabel` over stored items, so a
rule change re-labels the whole collection without a request.

STAGE ORDER, as the pipeline calls them (docs/industry-ai-agent.md §3): window, sieve, [dedupe, in
pipeline.py, across items], filter, label. Every drop names its reason.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from collect.industry_ai.config import DEFAULT_TYPE, Config, Domain, Terms

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
    #: When this lane first stored it (`iai_item.first_seen_at`); None for an item
    #: from this run's harvest, not yet stored. The watch window is measured from it.
    first_seen_at: datetime | None = None
    #: What media the post carries (collect/industry_ai/media.py MEDIA_KINDS), from
    #: the provider's own fields; None = not recorded, never "none" (rule 6).
    media_kind: str | None = None
    #: Words the provider sent WITH the post that are not the author's own - alt
    #: text, a quoted post, a crosspost's original (media.MEDIA_TEXT_KINDS, #679
    #: step 1) - and which kinds they are. None / () = none found or not read.
    media_text: str | None = None
    media_text_from: tuple[str, ...] = ()

    @property
    def text(self) -> str:
        """The AUTHOR'S words only: what the filters, the type label, the duplicate
        keys and the pages use. See `judged_text` for what the term matching reads."""
        return f"{self.title}\n{self.body}".strip()


def judged_text(item: Item) -> str:
    """The author's words plus the text that came with the media (#679 step 1).

    Read by the AI-term and industry-term matching (`sieve`) and by
    `too_little_to_read`, and by nothing else: a spam or promo filter judges what
    the author wrote, and two people quoting one viral post must not look like
    copies of each other to the duplicate check."""
    return f"{item.text}\n{item.media_text}".strip() if item.media_text else item.text


#: On a kept post whose AI term, or every industry term it needed, was found only
#: in the text that came with its media - so the page and the PR can count what
#: `media_text` changed (rule 8).
MEDIA_TEXT_FLAG = "terms_from_media_text"


@dataclass
class Verdict:
    """What the rules made of one item. `reason` is set exactly when dropped."""

    kept: bool
    reason: str | None = None
    flags: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
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
#: not declare a language (docs/industry-ai-agent.md §3 stage 4, rule 8 - checked in the §7 sample).
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


def ai_terms_found(text: str, cfg: Config) -> list[str]:
    """The AI terms an item names, after the global exclusions are removed. Every
    term matches as a whole word in any case (`has_term`), so the bare word counts
    only because the contract lists `ai`, which matches "AI" and "ai" alike. ".ai"
    (a file type or a web domain) never counts: `global_exclude_phrases` removes it
    before any term is matched. Until 2026-11-24 (#660) a capitals-only "AI" was
    added here when nothing else matched; with `ai` in the list that could never
    add anything, so it is gone."""
    clean = remove(text, cfg.global_exclude)
    return [t for t in cfg.all_ai_terms if has_term(clean, t)]


def _near(words: list[str], i: int, context: tuple[str, ...], window: int) -> bool:
    span = " ".join(words[max(0, i - window) : i + window + 1])
    return any(has_term(span, c) for c in context)


def _found(clean: str, terms: Terms, cfg: Config) -> list[str]:
    """`terms`' words in already-cleaned text. An ambiguous term counts only with
    one of its context words nearby."""
    found = [t for t in terms.domain_terms if has_term(clean, t)]
    if terms.ambiguous_terms:
        words = clean.split()
        window = int(cfg.run["context_window_words"])
        for term, context in terms.ambiguous_terms.items():
            pat = term_pattern(term)
            for i, w in enumerate(words):
                if pat.fullmatch(w.strip(".,;:!?()[]\"'")) and _near(words, i, context, window):
                    found.append(term)
                    break
    return found


def domain_match(text: str, domain: Domain, cfg: Config) -> dict | None:
    """What of one domain the item names: `{"terms": [...], "groups": {g: [...]}}`,
    or None when nothing. The domain's exclusions apply to all of its terms; a
    group's exclusions only to that group's own (#644 review, point 4)."""
    clean = remove(remove(text, cfg.global_exclude), domain.terms.exclude_phrases)
    terms = _found(clean, domain.terms, cfg)
    groups = {}
    for gkey, g in domain.groups.items():
        hit = _found(remove(clean, g.terms.exclude_phrases), g.terms, cfg)
        if hit:
            groups[gkey] = hit
    if not terms and not groups:
        return None
    return {"terms": terms, "groups": groups}


def domain_terms_found(text: str, domain: Domain, cfg: Config) -> list[str]:
    """Every term of the domain and its groups the item names (flattened)."""
    m = domain_match(text, domain, cfg)
    if m is None:
        return []
    return m["terms"] + [t for g in m["groups"].values() for t in g]


# ── the stages ───────────────────────────────────────────────────────────────


def outside_window(item: Item, since: datetime) -> bool:
    """Posted before the window. An undated item is NOT outside it (rule 6):
    it is kept and stays undated."""
    return item.created_at is not None and item.created_at < since


#: Query keys of the observer's watch lists start with this (`watch:<platform>:<source>`).
WATCH_KEY_PREFIX = "watch:"


def is_watched(item: Item) -> bool:
    """Found by a watch list (a community, an account, a list) - not only by keyword."""
    return any(k.startswith(WATCH_KEY_PREFIX) for k in item.query_keys)


#: An X post's page names its author: `https://x.com/<handle>/status/<id>`. A post whose
#: URL is the anonymous `/i/status/` form names nobody and links to no person.
_X_STATUS_URL = re.compile(r"^https://(?:x|twitter)\.com/([A-Za-z0-9_]{1,15})/status/")
_BLUESKY_WATCH = "watch:bluesky:from:"
_INSTAGRAM_WATCH = "watch:instagram:ig:"


def handle_of(item: Item) -> str | None:
    """The watched-account handle that posted `item`, lower-cased, or None.

    Each platform says it differently, and none is guessed (rule 6):
      x           the handle in the post's URL (`author_id` is a numeric account id);
      bluesky     the `from:<handle>` watch query that found it (`author_id` is a DID;
                  `person_of` reads the DID itself where the map holds one);
      hackernews  `author_id`, which is the username;
      instagram   the `ig:<handle>` watch query that found it (`author_id` is the
                  numeric account id; Instagram is read only by watching)."""
    if item.platform == "instagram":
        found = sorted(k[len(_INSTAGRAM_WATCH):].lower() for k in item.query_keys
                       if k.startswith(_INSTAGRAM_WATCH))
        return found[0] if len(found) == 1 else None
    if item.platform == "x":
        m = _X_STATUS_URL.match(item.url or "")
        # `/i/status/` is X's anonymous form, not an account called "i".
        return m.group(1).lower() if m and m.group(1).lower() != "i" else None
    if item.platform == "bluesky":
        found = sorted(k[len(_BLUESKY_WATCH):].lower() for k in item.query_keys
                       if k.startswith(_BLUESKY_WATCH))
        return found[0] if len(found) == 1 else None
    if item.platform == "hackernews":
        return (item.author_id or "").lower() or None
    return None


#: The flag naming a mapped person (`person:simon_willison`). READ BY pipeline.counts
#: and judge/industry_ai/view.py, which count a person as one author.
PERSON_FLAG = "person:"


def person_of(item: Item, cfg: Config,
              people: dict[tuple[str, str], str] | None = None,
              dids: dict[str, str] | None = None) -> str | None:
    """The person in `watch.people` who posted `item`, or None. Only a person written
    in the contract links two handles; nothing here infers one. `people` and `dids`
    are `cfg.person_by_handle()` and `cfg.person_by_did()`, passed in by a caller that
    asks for many items.

    BLUESKY, THE DID DECIDES (2026-11-24, #653 review). A post's `author_id` is its
    author's DID, so:
      * a DID in the map links its person, however the post was found - a keyword
        query included, which the handle alone could not do;
      * a post found by `from:<handle>` whose author DID is NOT the DID written for
        that handle's person links no one: the handle has passed to another account,
        and linking it would count a stranger as the person (rule 6)."""
    people = people if people is not None else cfg.person_by_handle()
    dids = dids if dids is not None else cfg.person_by_did()
    if item.platform == "bluesky" and item.author_id in dids:
        return dids[item.author_id]
    handle = handle_of(item)
    if not handle:
        return None
    person = people.get((item.platform, handle))
    if item.platform == "bluesky" and person in dids.values():
        return None  # the person has a DID, and this post's author is not it
    return person


_MENTION_OR_TAG = re.compile(r"[@#]\w[\w.]*")
#: Below this many characters a person's two posts are not folded as one: the floor the
#: 2026-11-20 measurement used. Over-merging is the worse failure (collect/CLAUDE.md
#: rule 3), and two short posts ("thanks!") match by chance.
CROSS_POST_MIN_CHARS = 20


#: The drop reasons a post with media and too few words is spared from: both say
#: "nothing here to judge", which of a picture or a video is not a finding.
UNREAD_INSTEAD_OF = frozenset({"no_ai_term", "too_short"})
#: The stage and reason it is stored with instead (`iai_item.drop_stage`, `drop_reason`).
UNREAD_STAGE, UNREAD_REASON = "unread", "media_unread"


def too_little_to_read(item: Item, cfg: Config) -> bool:
    """A picture, gallery or video with fewer than `run.unread_media_max_chars` of words
    once links, @handles and #tags are taken out (2026-11-25).

    Its content is in the media, which this lane does not read, so its few words cannot
    say whether it is about AI. It is counted as NOT READABLE (stage `unread`), apart
    from what the filters dropped - never as "no AI term" (rules 4 and 6). A post with
    no recorded media (`media_kind` None) is judged on its text as before: an unknown is
    not taken to be a picture either."""
    from collect.industry_ai.media import VISUAL

    if item.media_kind not in VISUAL:
        return False
    # The words that came WITH the media count too (#679 step 1): a picture with an
    # alt text, or a quote of a post, has something to read.
    words = _MENTION_OR_TAG.sub(" ", strip_links(judged_text(item)))
    return len(" ".join(words.split())) < int(cfg.run["unread_media_max_chars"])


def cross_post_text(text: str) -> str | None:
    """`normalized_text` without @mentions and #tags, which a person spells per
    platform (`@simonw` on X, `@simonwillison.net` on Bluesky); None when too short to
    say two posts are one."""
    key = normalized_text(_MENTION_OR_TAG.sub(" ", strip_links(text)))
    return key if len(key) >= CROSS_POST_MIN_CHARS else None


def is_watch_only(item: Item) -> bool:
    """Found by watch lists and by NO keyword query. Only these get the observer's own
    rules (the watch window, option A); a post a keyword query also found keeps the
    keyword agent's (#650 review)."""
    return bool(item.query_keys) and all(k.startswith(WATCH_KEY_PREFIX) for k in item.query_keys)


def sieve(item: Item, cfg: Config) -> tuple[str | None, dict[str, dict], list[str]]:
    """(drop reason or None, domain -> what matched, AI terms found). Needs an AI
    term and a term of ANY domain or group; which domain it is gets decided in
    `label`. The matched terms are KEPT (#644 review, point 2): they are what a
    keyword's count is counted from, and a post can count for several.

    A WATCHED item needs the AI term only (anooj, 2026-11-20): a post from a watched
    account or community that names no industry is general AI news or opinion, kept
    as "General AI" by `label`, not dropped as `no_domain_term`.

    The terms are matched on `judged_text`: the post's own words and the text that
    came with its media (#679 step 1). `needed_media_text` says whether that mattered."""
    text = judged_text(item)
    ai = ai_terms_found(text, cfg)
    if not ai:
        return "no_ai_term", {}, []
    matched = {k: m for k, d in cfg.domains.items() if (m := domain_match(text, d, cfg))}
    if not matched and not is_watched(item):
        return "no_domain_term", {}, ai
    return None, matched, ai


def needed_media_text(item: Item, cfg: Config) -> bool:
    """True when `item` passes `sieve` only because of its `media_text`: on its own
    words alone it would have been dropped. False when it has none."""
    if not item.media_text:
        return False
    import dataclasses

    own, _, _ = sieve(dataclasses.replace(item, media_text=None), cfg)
    return own is not None


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


def _any_naming_ai(patterns, text: str, cfg: Config) -> re.Pattern | None:
    """`_any` for type patterns: a pattern with a named group `ai` counts only at a
    match where that group's words name an AI term (contract `type_patterns`, since
    2026-11-24) - "I use it for my journal" is not an AI use case, "I used Claude to"
    is. Every match is tried, not only the first. A pattern without the group counts
    as `_any` does."""
    for p in patterns:
        if "ai" not in p.groupindex:
            if p.search(text):
                return p
            continue
        if any(ai_terms_found(m.group("ai") or "", cfg) for m in p.finditer(text)):
            return p
    return None


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
        # A PURE LINK POST IS NOT DROPPED OUTRIGHT when it shares an article: it
        # is kept and deduped onto the article by its link
        # (docs/industry-ai-agent.md §3 stage 4).
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


def label(item: Item, matched: dict[str, dict], cfg: Config) -> Verdict:
    """Domain(s), group(s), content type and stage, for an item every filter kept.

    DOMAIN: the domains whose queries found the item, confirmed by their own
    terms. None confirmed means `domains` is empty - the "domain unconfirmed"
    bucket, never a guess; another domain whose terms matched is recorded as a
    flag only. GROUPS: within a confirmed domain, every group whose own terms
    matched, as "<domain>/<group>".
    """
    confirmed = {d for d in item.domain_hints if d in matched}
    if is_watch_only(item):
        # A post ONLY watch lists found has no finding query to say its domain
        # (option A, anooj, 2026-11-20): it is filed under EVERY domain whose own
        # terms it names, flagged so those can be counted or filtered apart.
        domains = sorted(matched)
        flags = [f"domain_from_terms:{d}" for d in domains]
    else:
        # A keyword query found it (and maybe a watch list too): the keyword agent's
        # rule, the same label whether or not a watch list also found it (#650 review).
        domains = sorted(confirmed)
        flags = [f"also_matches:{d}" for d in sorted(matched) if d not in item.domain_hints]
    if not matched and is_watched(item):
        # Naming no industry at all, it is General AI - kept only because a watch list
        # found it - a different absence from "domain unconfirmed" (rule 4).
        flags.append("general_ai")
    groups = sorted(f"{d}/{g}" for d in domains for g in matched[d]["groups"])
    text = item.text

    content_type, why = None, None
    for t in cfg.type_order:
        hit = _any_naming_ai(cfg.type_patterns[t], text, cfg)
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
        groups=groups,
        content_type=content_type,
        matched_pattern=why,
        stage_guess=stage,
    )
