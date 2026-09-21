"""The only module in this lane that imports feedparser or trafilatura.

WHY IT IS THE ONLY ONE
----------------------
Both libraries ship their own HTTP layer, and both bypass
`collect.http.build_client` if used the obvious way:

    feedparser.parse("https://example.invalid/feed.xml")
        fetches, via urllib.request, sending
        `feedparser/6.0.14 +https://github.com/kurtmckee/feedparser/`

    trafilatura.fetch_url / fetch_response / trafilatura.downloads
    trafilatura.spider / .sitemaps / .feeds
        fetch, via urllib3 (pycurl if installed)

feedparser's default User-Agent is the sharper of the two. It names software
*and* gives a contact URL, so it passes every heuristic
`assert_identifying_user_agent` applies while giving whoever is deciding
whether to rate-limit us nobody at this project to reach. It is the placeholder
failure in the one form the placeholder check cannot see.

So the rule is **bytes in, never a URL and never a path**, and it is enforced
three ways rather than documented once:

  1. the signatures here take `bytes`, and reject `str` — the argument through
     which a URL could arrive does not accept one;
  2. `tests/test_lane_boundary.py` asserts no other file in `collect/` imports
     either library, and that nothing anywhere imports their download surfaces;
  3. `tests/test_blog_no_network.py` makes `urllib.request.urlopen`, `socket`
     and urllib3's `PoolManager` raise, then runs the whole fetch path against
     recorded fixtures. That is the one that catches a regression the AST test
     has no name for.

WHAT IS METADATA AND WHAT IS THE ARTIFACT
-----------------------------------------
feedparser sanitises HTML and resolves relative URIs, so the values it returns
are **not** the bytes that arrived. That is fine, and it is why the fetch path
stores the response bytes in `raw/` before anything here runs: the artifact is
immutable and re-parseable, and these dataclasses are a convenience derived
from it.

AN ID SHARED BY TWO ENTRIES IS NOT AN ID
----------------------------------------
`parse_feed` drops entries whose `entry_id` is not unique within the feed and
counts them as `ambiguous`. One of the nine seeded feeds does this today, on 8
of 20 entries, with the site root as both guid and link — so it is a live
defect rather than a prospective one, and every consequence of keeping them is
silent. The reasoning is at the check.

RULE 6, IN THE SMALL
--------------------
Every absent field stays absent. No `published_at` defaulting to now, no
feed-level author standing in for a missing entry author, no `updated` read as
`published`. A guessed author is worse than an unknown one: it attributes an
engineer's words to somebody who did not write them.
"""

from __future__ import annotations

import calendar
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import feedparser  # type: ignore[import-untyped]  # ships no py.typed marker
import trafilatura

from collect.adapters.blog.options import DEFAULT_EXTRACTION, ExtractionOptions, extraction_version

#: Reported in `extraction_version`, so a library upgrade is visible in the
#: version string rather than inferred from a date.
TRAFILATURA_VERSION: str = getattr(trafilatura, "__version__", "unknown")
FEEDPARSER_VERSION: str = getattr(feedparser, "__version__", "unknown")


class NotBytesError(TypeError):
    """A parser was handed something that could trigger I/O.

    `feedparser.parse` accepts a URL string, a file path or a stream and will
    happily fetch. Refusing `str` at the boundary is what makes that
    unreachable rather than merely discouraged.
    """


@dataclass(frozen=True)
class FeedEntry:
    """One feed entry's metadata. Not a document — a document needs the article.

    `entry_id` is what `document.external_id` gets, so it has to be the
    publisher's own identity for the post: a guid, or the link when no guid is
    given. It is never derived from the content, because an edited post would
    then become a second document and count as a second voice.
    """

    entry_id: str
    url: str | None
    title: str | None
    author: str | None
    published_at: datetime | None
    summary_html: str | None
    content_html: str | None

    @property
    def fetchable_url(self) -> str | None:
        return self.url


@dataclass(frozen=True)
class ParsedFeed:
    """What one feed payload yielded, including what it failed to yield."""

    feed_url: str | None
    feed_title: str | None
    entries: list[FeedEntry]

    #: feedparser's `bozo` flag: the payload was malformed in some way. It is
    #: not fatal on its own — a feed with one bad character still yields its
    #: entries — so it is recorded rather than raised, and `entries` says
    #: whether anything survived.
    malformed: bool = False
    malformed_detail: str | None = None

    #: Entries dropped for having neither a guid nor a link. They cannot be
    #: identified, so they cannot become documents; counting them is what stops
    #: the drop being silent (rule 6).
    unidentifiable: int = 0

    #: Entries dropped because two or more SHARED an id. Distinct from
    #: `unidentifiable`, which is identity absent; this is identity present and
    #: not unique, which is the worse of the two because it looks like an answer.
    #: 8 of hamel.dev's 20 entries, measured 2026-08-19. See `parse_feed`.
    ambiguous: int = 0

    #: Version of the code that parsed it, for the same reason every derived
    #: row carries `pipeline_version`.
    parser_version: str = field(default_factory=lambda: f"feedparser-{FEEDPARSER_VERSION}")


def _require_bytes(payload: object, *, what: str) -> bytes:
    if isinstance(payload, bytes | bytearray):
        return bytes(payload)
    raise NotBytesError(
        f"{what} takes the response bytes, not {type(payload).__name__}. "
        "A string here can be a URL or a file path, and feedparser would fetch "
        "it with its own HTTP layer and its own User-Agent, bypassing "
        "collect.http.build_client and NFR-5's identifying-User-Agent gate. "
        "Fetch through the adapter and pass what came back."
    )


def _text_or_none(value: Any) -> str | None:
    """Empty string is absence in a feed, and absence must stay absent."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _timestamp_or_none(struct_time: Any) -> datetime | None:
    """feedparser's UTC struct_time to an aware datetime, or None.

    `published_parsed` only. `updated_parsed` is a different fact — when the
    author last edited — and reading it as the publication date would misdate
    every corrected post, which matters because FR-4 resolves aliases against
    the date a claim was made.

    ⚠ `OSError` IS IN THE TUPLE AND IT IS NOT DEFENSIVE PADDING. It was
    missing, and `lilianweng.github.io` crashed the whole harvest on its 53rd
    entry - the feed's `/faq/` page, which Hugo dates `Mon, 01 Jan 0001
    00:00:00 +0000` because the page carries no date at all. That is
    `timegm` -> -62135596800, and on Windows/CPython 3.11
    `datetime.fromtimestamp` raises **OSError [Errno 22]** for it rather than
    the `ValueError` the original tuple expected.

    Two things make it worth this much comment. A ZERO DATE IS HUGO'S NORMAL
    OUTPUT for an undated page, so any Hugo feed with one reaches here - it is
    a shape, not a corrupt feed. And the exception TYPE IS PLATFORM-DEPENDENT:
    the tuple as written may well be sufficient on Linux, where CI runs, so a
    green suite says nothing about whether this line holds on the machine the
    harvest is actually run from. That is the same class as the ruff and
    pytest scoping entries in CLAUDE.md - a check answering a narrower
    question than the one being asked of it.

    An unrepresentable date returns None, the same as an absent one, and the
    caller keeps `published_at` NULL. That is rule 6 holding: the date is
    missing and stays missing, rather than becoming 1970 or today.
    """
    if not struct_time:
        return None
    try:
        return datetime.fromtimestamp(calendar.timegm(struct_time), tz=UTC)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _entry_content_html(entry: Any) -> str | None:
    """The richest body the feed offered, or None.

    A full-content feed puts the whole post in `content`; most put a teaser in
    `summary`. Both are kept separately rather than merged, because a teaser
    read as a full post would make a truncated article look complete.
    """
    contents = entry.get("content") or []
    for item in contents:
        value = _text_or_none(item.get("value"))
        if value:
            return value
    return None


#: feedparser sets `bozo` with this exception when it cannot see an XML
#: content-type in the response headers. Handing it bytes means *we* supply the
#: headers, so when we have no content-type to give, the flag is a statement
#: about our synthesised headers rather than about the payload — and reporting
#: it as malformedness would mark every well-formed feed malformed, which
#: retires the signal by crying wolf. When the caller *does* supply a
#: content-type and feedparser still objects, that is a real finding: the
#: publisher is serving a feed as something else.
_HEADER_ONLY_BOZO = "NonXMLContentType"


#: The elements whose CDATA carries a whole post. `content:encoded` is RSS's
#: full-text element; Atom spells it `content`.
_BODY_ELEMENTS = frozenset({"encoded", "content"})


def content_spans(payload: bytes) -> list[tuple[int, int, int]]:
    """`(entry_index, start, end)` byte ranges of each entry's full-text body.

    VERBATIM, AND THAT IS THE WHOLE POINT. `payload[start:end]` is a slice of
    the bytes the server sent - the publisher's own HTML, not anything this
    code composed. That is what lets a per-entry blob sit in `raw/` on the same
    footing as the feed blob it came from: NFR-4's rebuild reads original bytes
    at both levels.

    ⚠ WE CARVE `content:encoded`, NOT `<item>`, AND THE REASON IS MEASURED.
      The obvious carve is the whole `<item>` element, and it does not work.
      An item uses `content:`, `dc:` and `atom:` prefixes that the ROOT element
      declares, so a carved `<item>` is not parseable on its own:

          spans that re-parse standalone   0 of 20   (both Medium feeds, 10 each)
          unbound prefixes                 atom, content, dc

      Making it parseable means injecting the root's namespace declarations -
      at which point the bytes are composed rather than verbatim, and the
      argument for carving at all (that `raw/` holds what the server sent) is
      gone. `content:encoded`'s CDATA has no such dependency: it is
      self-contained HTML, byte-identical to what arrived, and exactly what
      `extract_article_text` already consumes on the article path. One
      function, two sources of bytes.

    ENTRY INDEX RATHER THAN A GUID, because the caller already has the guids.
    An earlier version read `<guid>` here and got the CHANNEL's `<link>`
    instead - the feed's own URL, before any item had opened - so every span
    carried the wrong identity and none matched a parsed entry. Counting item
    opens cannot make that mistake, and `parse_feed` returns entries in
    document order, so `entries[index]` is the entry this body belongs to.

    EXPAT RATHER THAN A REGEX, because `</item>` and `]]>` both appear inside
    real post bodies and only a parser knows which occurrence closes what.
    `xml.parsers.expat` is stdlib and exposes `CurrentByteIndex`, which is the
    one thing `feedparser` cannot give us - it returns parsed values and throws
    the offsets away. Same shape as `offset_map`: cheap while you are already
    walking the bytes, impossible to reconstruct afterwards.

    Returns `[]` for a feed carrying no full-text bodies, and for a payload
    that will not parse - a malformed feed is a gap, not an exception for every
    call site to handle.
    """
    import xml.parsers.expat

    spans: list[tuple[int, int, int]] = []
    index = -1
    in_body = False
    body_start: int | None = None
    parser = xml.parsers.expat.ParserCreate()

    def _local(name: str) -> str:
        return name.split("}")[-1].split(":")[-1]

    def _start(name, _attrs):
        nonlocal index, in_body, body_start
        local = _local(name)
        if local in ("item", "entry"):
            index += 1
        elif local in _BODY_ELEMENTS and index >= 0:
            in_body, body_start = True, None

    def _cdata():
        nonlocal body_start
        if in_body and body_start is None:
            body_start = parser.CurrentByteIndex + len(b"<![CDATA[")

    def _end(name):
        nonlocal in_body, body_start
        if _local(name) in _BODY_ELEMENTS and in_body:
            in_body = False
            if body_start is not None:
                close = payload.rindex(b"]]>", body_start, parser.CurrentByteIndex)
                # WHITESPACE-ONLY IS ABSENT. `<content:encoded><![CDATA[   ]]>`
                # is what a feed looks like the day a publisher switches it to
                # titles-only, and FR-10 has to see that as nothing delivered.
                # An empty body is not the same shape as an absent one and both
                # must count as zero - `fixtures/blog/feed_rss_no_bodies.xml`
                # carries one of each on purpose.
                if payload[body_start:close].strip():
                    spans.append((index, body_start, close))
            body_start = None

    parser.StartElementHandler = _start
    parser.EndElementHandler = _end
    parser.StartCdataSectionHandler = _cdata
    try:
        parser.Parse(payload, True)
    except Exception:  # noqa: BLE001 - a malformed feed yields no spans, not a raise
        return []
    # ONE BODY PER ENTRY, THE FIRST. A feed repeating `content:encoded` inside
    # one item is not a shape we have seen; keeping the first is a decision
    # rather than an accident, and a second would otherwise silently become a
    # second document for one post.
    seen: set[int] = set()
    first: list[tuple[int, int, int]] = []
    for idx, a, b in spans:
        if idx not in seen:
            seen.add(idx)
            first.append((idx, a, b))
    return first


def parse_feed(
    payload: bytes,
    *,
    feed_url: str | None = None,
    content_type: str | None = None,
) -> ParsedFeed:
    """Parse feed bytes. Never fetches — see the module docstring.

    `feed_url` is passed to feedparser as a `Content-Location` response header,
    which is how it resolves relative entry links without being given a URL to
    fetch. Without it, a feed whose links are relative yields relative
    `entry.url` values and every article fetch fails on a URL that is not one.

    `content_type` is the response's own header, passed through for the same
    reason: feedparser uses it to decide how to treat the body, and it is the
    difference between "this feed is malformed" and "we did not tell feedparser
    what this is".
    """
    data = _require_bytes(payload, what="parse_feed")

    response_headers: dict[str, str] = {}
    if feed_url:
        response_headers["content-location"] = feed_url
    if content_type:
        response_headers["content-type"] = content_type
    parsed = feedparser.parse(data, response_headers=response_headers or None)

    candidates: list[FeedEntry] = []
    unidentifiable = 0
    for raw in parsed.entries:
        url = _text_or_none(raw.get("link"))
        entry_id = _text_or_none(raw.get("id")) or url
        if not entry_id:
            unidentifiable += 1
            continue
        candidates.append(
            FeedEntry(
                entry_id=entry_id,
                url=url,
                title=_text_or_none(raw.get("title")),
                # Entry-level author only. A feed-level author standing in here
                # would attribute a guest post to the site owner.
                author=_text_or_none(raw.get("author")),
                published_at=_timestamp_or_none(raw.get("published_parsed")),
                summary_html=_text_or_none(raw.get("summary")),
                content_html=_entry_content_html(raw),
            )
        )

    # AN ID SHARED BY TWO ENTRIES IS NOT AN ID. Measured on the nine seeded
    # feeds 2026-08-19: `hamel.dev` publishes `https://hamel.dev/` as BOTH the
    # guid and the link of 8 of its 20 entries — eight distinct articles whose
    # only identity is the site root.
    #
    # This is the same defect as an entry with no guid and no link, wearing a
    # value. It is separated from `unidentifiable` because the causes differ and
    # a reader needs to tell them apart: one feed omits identity, the other
    # publishes a placeholder.
    #
    # WHAT IT WOULD HAVE COST, HAD THEY BEEN KEPT. All three failures are silent:
    #
    #   the fetch     `fetchable_url` is the site root, so the harvester fetches
    #                 a HOME PAGE eight times and stores it as an article.
    #   the document  `ON CONFLICT (source, external_id) DO NOTHING` keeps the
    #                 first and counts seven as `already_present` — "a re-fetch
    #                 of an unchanged article, not a failure".
    #   the context   `assemble_article` derives the thread_context id from the
    #                 document id, so all eight mint the SAME id and seven
    #                 flattenings are discarded under `DO NOTHING`.
    #
    # The surviving row would then carry the home page's text, attributed to the
    # author of whichever entry happened to be first, and read as an article.
    seen: dict[str, int] = {}
    for entry in candidates:
        seen[entry.entry_id] = seen.get(entry.entry_id, 0) + 1
    shared = {key for key, n in seen.items() if n > 1}
    entries = [e for e in candidates if e.entry_id not in shared]
    ambiguous = len(candidates) - len(entries)

    exception = parsed.get("bozo_exception")
    malformed = bool(parsed.get("bozo"))
    if malformed and content_type is None and type(exception).__name__ == _HEADER_ONLY_BOZO:
        malformed = False
        exception = None

    return ParsedFeed(
        feed_url=feed_url,
        feed_title=_text_or_none((parsed.feed or {}).get("title")),
        entries=entries,
        malformed=malformed,
        malformed_detail=f"{type(exception).__name__}: {exception}" if exception else None,
        unidentifiable=unidentifiable,
        ambiguous=ambiguous,
    )


def extract_article_text(
    payload: bytes,
    *,
    url: str | None = None,
    options: ExtractionOptions | None = None,
    template_block: str | Iterable[str] | TemplateBlockRule | None = None,
) -> str | None:
    """Article HTML bytes to the plain text the extractor will read.

    **E3's to call, not the fetch path's.** The result is derived and
    regenerable, so it belongs in the `flattened/` namespace behind
    `thread_context.flattened_text_ref`, which is assemble's artifact. Harvest
    stores the article bytes in `raw/` and stops there; this lives here because
    it is the other half of the trafilatura boundary and must not be imported
    from two places.

    Returns None when trafilatura finds no article body — a navigation page, a
    paywall stub, a JS shell. None means *nothing was extracted*, and the
    caller must not turn that into an empty document.

    The bytes are handed over undecoded on purpose: trafilatura's charset
    detection is better than a guess made here, and a mis-decoded article would
    produce mojibake that verifies as a quote.
    """
    data = _require_bytes(payload, what="extract_article_text")
    options = options or DEFAULT_EXTRACTION
    # Spelled out rather than `**options.as_kwargs()`: trafilatura is typed, and
    # unpacking a `dict[str, object]` into it erases every parameter type, so a
    # renamed or mistyped option would arrive silently. Drift between this call
    # and the dataclass is caught by
    # `test_blog_parse.py::test_every_option_reaches_trafilatura`.
    text = trafilatura.extract(
        data,
        url=url,
        include_comments=options.include_comments,
        include_formatting=options.include_formatting,
        include_tables=options.include_tables,
        include_links=options.include_links,
        deduplicate=options.deduplicate,
        favor_precision=options.favor_precision,
        favor_recall=options.favor_recall,
        output_format=options.output_format,
    )
    if text and template_block is not None:
        if isinstance(template_block, TemplateBlockRule):
            # An unverified or clean rule strips nothing, and says so
            # rather than silently behaving like an absent argument.
            template_block = template_block.headings
        text = strip_template_block(text, template_block)
    return text or None


@dataclass(frozen=True)
class TemplateBlockRule:
    """What `contract/sources.yaml` says about one feed's boilerplate tail.

    THREE STATES, NOT TWO, and the third is the reason this is a dataclass
    rather than a `str | None`:

        verified + headings    strip from the first heading that matches
        verified + no headings LOOKED AND FOUND NOTHING. A real result.
        unverified             NOBODY HAS LOOKED. Not a result (rule 6).

    A `str | None` return collapses the last two into `None`, and then a rule
    that fires on two feeds and does nothing on seven is indistinguishable from
    a rule that correctly found nothing to do. `inert_reason` is what makes the
    inaction visible to a caller that wants to count it.
    """

    source_id: str
    status: str
    headings: tuple[str, ...] = ()
    pages_examined: int = 0
    checked_on: object | None = None

    @property
    def verified(self) -> bool:
        return self.status == "verified"

    @property
    def strips(self) -> bool:
        """Whether this rule removes anything."""
        return self.verified and bool(self.headings)

    @property
    def inert_reason(self) -> str | None:
        """Why this rule will do nothing, or None if it will do something.

        The string is for a report, not for control flow — a caller branching on
        it is asking the wrong question and should read `strips`.
        """
        if self.strips:
            return None
        if not self.verified:
            return f"unverified: no page of {self.source_id} has been examined"
        return f"verified clean over {self.pages_examined} pages: no template block"


#: Feeds that are not blogs have no template rule and are not an omission.
_UNVERIFIED = "unverified"


def template_block_for(source_id: str | None) -> TemplateBlockRule:
    """This feed's template-block rule, read from the contract.

    **The rule lives in `contract/sources.yaml`, not here** (rule 5). It was a
    dict in this module for one commit, which put a per-source content rule in
    code where the other eight feeds were invisible; the contract holds one
    entry per feed, so an unexamined feed is a row somebody can count rather
    than a key that is missing.

    An unknown or absent `source_id` is `unverified` — never "clean".
    """
    from collect.registry.sources import load_sources

    if not source_id:
        return TemplateBlockRule(source_id="", status=_UNVERIFIED)
    for feed in load_sources().feeds:
        if feed.get("id") != source_id:
            continue
        block = feed.get("template_block") or {}
        return TemplateBlockRule(
            source_id=source_id,
            status=str(block.get("status", _UNVERIFIED)),
            headings=tuple(block.get("headings") or ()),
            pages_examined=int(block.get("pages_examined") or 0),
            checked_on=block.get("checked_on"),
        )
    return TemplateBlockRule(source_id=source_id, status=_UNVERIFIED)


def strip_template_block(text: str, heading: str | Iterable[str]) -> str:
    """Drop everything from a markdown heading line onwards.

    ANCHORED ON THE HEADING LINE, not on the words. `## Recent articles` at the
    start of a line is the block; the same phrase inside a sentence is somebody
    writing about recent articles and stays. A substring match here would be the
    boundary defect this project has already recorded twice.

    Everything AFTER the heading goes, because the block is terminal in every
    template measured so far — it is the page footer. A rule that tried to find
    the end of the block would need to know what follows it, which is more site
    knowledge for no gain while the block is last.

    SEVERAL HEADINGS, AND THE EARLIEST MATCH WINS. One feed needed two spellings
    (`Recent articles` on 57 pages, `More recent articles` on 4), and a
    single-string rule kept the block on those 4 while looking applied. Earliest
    rather than first-listed, so the order of the list in the contract cannot
    change how much text is removed.
    """
    headings = (heading,) if isinstance(heading, str) else tuple(heading)
    starts = [
        match.start()
        for h in headings
        if (
            match := re.compile(
                rf"^\s{{0,3}}#{{1,6}}\s+{re.escape(h)}\s*$", re.MULTILINE
            ).search(text)
        )
        is not None
    ]
    return text[: min(starts)].rstrip() if starts else text


def current_extraction_version(options: ExtractionOptions | None = None) -> str:
    """What to stamp on anything derived by `extract_article_text`."""
    return extraction_version(TRAFILATURA_VERSION, options)
