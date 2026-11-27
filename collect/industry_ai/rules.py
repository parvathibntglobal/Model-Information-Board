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
from functools import cache, lru_cache
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
    #: THE FIRST PICTURE'S LINK, from the provider's own response (media.*_picture,
    #: #679 step 3). For this run's picture-text reader only; NEVER STORED.
    picture_url: str | None = None
    #: TEXT READ FROM THE FIRST PICTURE (collect/industry_ai/ocr.py), in SHADOW MODE:
    #: it decides no label (`ocr.affects_labels: false`), it only sets the flags of
    #: `picture_text_flags`. `ocr_text` is every word Tesseract returned, space
    #: separated, and `ocr_confidence` each word's confidence (0-100) in the same
    #: order, so `ocr.min_confidence` can be set from the shadow week's hand-check
    #: without fetching a picture again. `ocr_status`: None = not tried (rule 6).
    ocr_text: str | None = None
    ocr_confidence: tuple[int, ...] = ()
    ocr_status: str | None = None

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


#: On a post whose outcome the text that came with its media changed, so it can be
#: counted and read before anyone relies on it (rule 8). Two cases, one flag:
#:   LET THROUGH  its AI term, or every industry term it needed, was found only in
#:                `media_text` (`needed_media_text`, set at the sieve);
#:   FILED ELSEWHERE  it passes on its own words, but `media_text` changed its
#:                domains or groups (`media_text_changed_filing`, set at the label;
#:                #680 review, 2026-11-26).
#: AI Watch shows a flagged post's `media_text_from`, so a kept post whose own words
#: show no AI term is not left unexplained.
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


#: UNBOUNDED (2026-11-27): the terms are a finite list from the contract and the
#: registry. At 4,096 the AI terms (773 since the expansion), every domain's terms
#: and the registry's names could outgrow it, and an evicted pattern is recompiled
#: on every post - a slowdown nothing would report.
@cache
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


#: What `run.match_strip` can take out before terms are matched (iai-7). An @handle
#: needs no word character before it, so an email address ("a@b.com") is not one.
_HANDLE = re.compile(r"(?<![\w@])@\w[\w.]*")
_HASHTAG = re.compile(r"(?<![\w#])#\w[\w.]*")
_STRIP = {"links": _URL, "handles": _HANDLE, "hashtags": _HASHTAG}


def match_text(text: str, cfg: Config) -> str:
    """The text a post's AI and industry words are matched in: its title and body with
    `run.match_strip` taken out (iai-7, the 2026-11-26 kept-post review). A word inside
    a link or an @handle is not the author writing about it; hashtags stay unless the
    contract lists them, being the author's own topic label."""
    return remove(text, [_STRIP[k] for k in cfg.run["match_strip"]])


@lru_cache(maxsize=8)
def _any_ai_pattern(terms: tuple[str, ...]) -> re.Pattern:
    """Every AI term as one alternation: "names ANY of them" in one search, the same
    answer as asking each `term_pattern` in turn."""
    return re.compile("|".join(term_pattern(t).pattern for t in terms), re.IGNORECASE)


def ai_near_industry(text: str, terms: list[str], cfg: Config) -> bool:
    """Whether any of `terms` (a kept post's filed industry words) has an AI term within
    `run.ai_near_industry_words` words of it (iai-7: flag `ai_far_from_industry` when
    not). Read on the author's own words (`text`).

    NO EVIDENCE OF FAR IS NOT EVIDENCE OF FAR (rule 6), and this only ever adds a flag,
    so the answer is "near" when the distance cannot be measured:
      * a term that cannot be found again (an ambiguous term's spelling);
      * NO AI TERM IN THE AUTHOR'S OWN WORDS (#685 review, point 1): the post's AI term
        was in the text that came with its media (#680: alt text, a quoted post), which
        the sieve reads and this does not. Such a post is already flagged
        `terms_from_media_text`."""
    clean = remove(match_text(text, cfg), cfg.global_exclude)
    any_ai = _any_ai_pattern(cfg.all_ai_terms)
    if not any_ai.search(clean):
        return True
    words = clean.split()
    window = int(cfg.run["ai_near_industry_words"])
    located = False
    for term in terms:
        for m in term_pattern(term).finditer(clean):
            located = True
            i = len(clean[: m.start()].split())
            span = " ".join(words[max(0, i - window): i + len(term.split()) + window])
            if any_ai.search(span):
                return True
    return not located


def ai_terms_found(text: str, cfg: Config) -> list[str]:
    """The AI terms an item names, after the global exclusions are removed. Every
    term matches as a whole word in any case (`has_term`), so the bare word counts
    only because the contract lists `ai`, which matches "AI" and "ai" alike. ".ai"
    (a file type or a web domain) never counts: `global_exclude_phrases` removes it
    before any term is matched. Until 2026-11-24 (#660) a capitals-only "AI" was
    added here when nothing else matched; with `ai` in the list that could never
    add anything, so it is gone.

    ONLY TERMS WHOSE FIRST WORD IS IN THE TEXT ARE ASKED (2026-11-27): with 773 AI
    terms, asking every one of every post took 2.7x as long (24.3 s against 9.1 s for
    2,000 stored posts). A term can only match where its first word stands as a word,
    so the others cannot match and are skipped. Same answer, same order - pinned
    against the full loop by tests/test_industry_ai_ai_terms.py."""
    clean = remove(text, cfg.global_exclude)
    by_first, always = _ai_terms_by_first_word(cfg.all_ai_terms)
    present = {w.lower() for w in _ALNUM.findall(clean)}
    asked = set(always).union(*(by_first[w] for w in present if w in by_first))
    return [t for t in cfg.all_ai_terms if t in asked and has_term(clean, t)]


#: A run of letters or digits: the unit `term_pattern`'s words begin with.
_ALNUM = re.compile(r"[^\W_]+")


@lru_cache(maxsize=8)
def _ai_terms_by_first_word(terms: tuple[str, ...]) -> tuple[dict[str, frozenset], tuple]:
    """Terms keyed by their first word's first letters-and-digits run, lower case, as
    `term_pattern` splits a term (on spaces, hyphens, underscores). A term with no such
    run is always asked (`always`)."""
    by: dict[str, set[str]] = {}
    always = []
    for t in terms:
        first = re.split(r"[\s\-_]+", t.strip())[0]
        m = _ALNUM.search(first)
        if m:
            by.setdefault(m.group(0).lower(), set()).add(t)
        else:
            always.append(t)
    return {k: frozenset(v) for k, v in by.items()}, tuple(always)


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


def copy_text(text: str) -> str | None:
    """The text two accounts' posts on ONE platform are compared on (iai-7, dedupe pass
    2b): links and @handles out (each copy carries its own t.co link and tags), then
    `normalized_text`. None below `CROSS_POST_MIN_CHARS`, as for a cross-post: two short
    posts ("great thread!") match by chance."""
    key = normalized_text(remove(text, [_HANDLE]))
    return key if len(key) >= CROSS_POST_MIN_CHARS else None


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
    came with its media (#679 step 1). `needed_media_text` says whether that mattered.
    Links and @handles are taken out first (`match_text`, iai-7: `run.match_strip`)."""
    text = match_text(judged_text(item), cfg)
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


# ── TEXT IN THE PICTURE, SHADOW MODE (#679 step 3, anooj, 2026-11-26) ───────────
#
#: On a "not readable" post whose picture text, at `ocr.min_confidence`, would have
#: let it through: its caption plus that text pass the sieve and are no longer too
#: little to read. Its label is unchanged (shadow mode); this is what the shadow
#: week counts and hand-checks before `ocr.affects_labels` may be set (rule 8).
PICTURE_TEXT_FLAG = "picture_text_would_pass"
#: ...and the ONLY AI term the picture text added is `ai` (Parvathi, #683 review):
#: the case most exposed to stray letters read from a photo or art.
PICTURE_TEXT_AI_ONLY_FLAG = "picture_text_only_ai"
#: Statuses of one picture read (`iai_item.ocr_status`); NULL = not tried.
OCR_STATUSES = ("ok", "no_text", "failed", "too_large", "over_cap", "refused")


def picture_words(item: Item, min_confidence: int) -> str:
    """The words of `ocr_text` whose confidence is at least `min_confidence`."""
    words = (item.ocr_text or "").split()
    if len(words) != len(item.ocr_confidence):
        # A text and its confidences that disagree are not guessed at (rule 12).
        raise ValueError(f"{item.id}: {len(words)} picture word(s) but "
                         f"{len(item.ocr_confidence)} confidence(s)")
    return " ".join(w for w, c in zip(words, item.ocr_confidence, strict=True)
                    if c >= min_confidence)


def picture_text_flags(item: Item, cfg: Config) -> list[str]:
    """The shadow flags for a "not readable" post with picture text, or []."""
    if not item.ocr_text:
        return []
    import dataclasses

    words = picture_words(item, int(cfg.ocr["min_confidence"]))
    if not words:
        return []
    seen = dataclasses.replace(
        item, media_text="\n".join(t for t in (item.media_text, words) if t))
    why, _, ai = sieve(seen, cfg)
    if why is not None or too_little_to_read(seen, cfg):
        return []
    added = set(ai) - set(ai_terms_found(judged_text(item), cfg))
    return [PICTURE_TEXT_FLAG] + ([PICTURE_TEXT_AI_ONLY_FLAG] if added == {"ai"} else [])


def media_text_changed_filing(item: Item, matched: dict[str, dict], cfg: Config) -> bool:
    """True when the text that came with the media changed WHERE a kept post is filed:
    `label` on the post's own words gives other domains or groups than on its words plus
    `media_text` (#680 review, point 1). A post that would have passed on its own words
    but picks up a domain only the quoted post names is filed elsewhere, not let
    through, and `needed_media_text` cannot see it. False when it has no media text."""
    if not item.media_text:
        return False
    import dataclasses

    own_item = dataclasses.replace(item, media_text=None)
    why, own_matched, _ = sieve(own_item, cfg)
    if why is not None:
        return True  # through only on the media text: `needed_media_text`'s case
    mine, theirs = label(own_item, own_matched, cfg), label(item, matched, cfg)
    return (mine.domains, mine.groups) != (theirs.domains, theirs.groups)


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


#: How far `sentence_of` reads either side of a match, at most (iai-7).
SENTENCE_CHARS = 120
_SENTENCE_END = ".!?\n"


def sentence_of(text: str, start: int, end: int) -> str:
    """The sentence around text[start:end]: back to the previous . ! ? or line break and
    on to the next one, at most `SENTENCE_CHARS` either side (iai-7). Found by scanning
    from the match, not by a pattern that tries 120 characters at every position - that
    form cost a full relabel minutes (measured 2026-11-26, 2,000 stored posts)."""
    a = max(start - SENTENCE_CHARS, 0)
    for c in _SENTENCE_END:
        a = max(a, text.rfind(c, a, start) + 1)
    b = min(end + SENTENCE_CHARS, len(text))
    for c in _SENTENCE_END:
        i = text.find(c, end, b)
        if i != -1:
            b = i
    return text[a:b]


def names_ai(text: str, cfg: Config) -> bool:
    """Whether `text` names any AI term: `ai_terms_found`'s answer, in one search."""
    return _any_ai_pattern(cfg.all_ai_terms).search(remove(text, cfg.global_exclude)) is not None


def _any_naming_ai(patterns, text: str, cfg: Config) -> re.Pattern | None:
    """`_any` for type patterns, where AI must be what the phrase is about (contract
    `type_patterns`). A pattern with a named group
      * `ai` counts only at a match where that group's words name an AI term (since
        2026-11-24) - "I use it for my journal" is not an AI use case, "I used Claude
        to" is;
      * `sentence` counts only at a match whose SENTENCE (`sentence_of`) names an AI
        term (iai-7) - "$120K revenue since February" is not a use case, "our AI
        agent has run in production since March" is.
    Every match is tried, not only the first. A pattern with neither counts as `_any`."""
    for p in patterns:
        if "sentence" in p.groupindex:
            if any(names_ai(sentence_of(text, m.start("sentence"), m.end("sentence")), cfg)
                   for m in p.finditer(text)):
                return p
        elif "ai" in p.groupindex:
            if any(names_ai(m.group("ai") or "", cfg) for m in p.finditer(text)):
                return p
        elif p.search(text):
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
    flags.extend(review_flags(item, cfg))
    return None, flags


def review_flags(item: Item, cfg: Config) -> list[str]:
    """THE iai-7 FLAGS A POST CAN CARRY ON ITS OWN (the 2026-11-26 kept-post review,
    agreed with the team). Flags, never drops (rule 8): each is counted and its hits
    hand-checked before it could become one.
      * `flag_patterns`: github_tracking, market_chatter, for_sale, each on its platforms;
      * reply_fragment: an X reply (its text starts with an @handle) with fewer than
        `run.reply_min_own_words` words once @handles and links are out.
    `ai_far_from_industry` needs the filed industries (`label`) and `heavy_poster` the
    whole collection (pipeline.evaluate)."""
    text = item.text
    out = [name for name, (plats, pats) in cfg.flag_patterns.items()
           if (plats is None or item.platform in plats) and _any(pats, text)]
    if item.platform == "x" and text.lstrip().startswith("@"):
        own = remove(text, [_URL, _HANDLE]).split()
        if len(own) < int(cfg.run["reply_min_own_words"]):
            out.append("reply_fragment")
    return out


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
    # FLAG, NEVER A DROP (iai-7): no filed industry word has an AI term near it, so the
    # two may be about different things in a long post.
    filed = [t for d in domains for t in
             [*matched[d]["terms"], *(x for g in matched[d]["groups"].values() for x in g)]]
    if filed and not ai_near_industry(text, filed, cfg):
        flags.append("ai_far_from_industry")

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
