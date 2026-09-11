"""Canonical URLs. FR-16's first step, and the one that was missing.

WHY A URL NEEDS CANONICALISING AT ALL. The same article arrives as

    https://www.example.com/post?utm_source=reddit&utm_medium=social
    https://example.com/post/
    http://example.com/post#section

Four spellings, one page. Left alone they are four links in `document.url`,
four different "sources" to a reader following them, and four rows that no
url-based check can recognise as one.

IT IS PURE, AND THAT IS DELIBERATE. No network. Resolving redirects and
shorteners is in the spec and is NOT done here: it needs a request per URL, and
a function that sometimes makes an HTTP call is one nobody can safely put in a
loop over 7,000 documents. `expand_shortener` is named below as the seam where
that belongs, unimplemented rather than half-done.

WHAT IT DOES NOT TOUCH, BECAUSE STRIPPING TOO MUCH IS THE WORSE ERROR:

    the path         `/post/` and `/post` are the same page on almost every
                     host and NOT on all of them, so only a trailing slash goes.
    the query        only KNOWN tracking keys are dropped. A blanket "remove
                     the query" would destroy `?id=49610874`, which IS the
                     document on Hacker News.
    the fragment     dropped - `#section` is a position in one page, never a
                     different page. Except on a host that routes with it,
                     which is why `#!` is kept.

Under-canonicalising leaves two spellings of one page. Over-canonicalising
merges two genuinely different pages, and that destroys evidence rather than
tidying it — the same asymmetry `dedupe.py` reasons from.
"""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

#: Keys that identify a CAMPAIGN, never a document. Dropped.
#:
#: A closed list rather than a prefix rule: `utm_*` would be easy to match with
#: a wildcard, but `fbclid`, `gclid` and `igshid` share no prefix, and a
#: wildcard broad enough to catch a future one is broad enough to eat an id.
TRACKING_KEYS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_name", "utm_cid", "utm_reader", "utm_referrer", "utm_social",
    "utm_brand", "utm_id", "utm_swu",
    "fbclid", "gclid", "dclid", "gclsrc", "msclkid", "twclid", "igshid",
    "mc_cid", "mc_eid", "ref_src", "ref_url", "s_kwcid", "yclid", "_hsenc",
    "_hsmi", "mkt_tok", "trk", "trkCampaign", "sc_channel", "sc_campaign",
    # Reddit and Hacker News append these to shared links; neither changes the
    # page, and `share_id` in particular differs per person who shared it.
    "share_id", "utm_hsm", "rdt", "correlation_id", "post_fullname",
})

#: Hosts where `www.` is cosmetic. Collapsing it everywhere is wrong — some
#: hosts genuinely serve different content — but the rule holds for the
#: ordinary case, and a host that breaks it can be excluded here by name.
_KEEP_WWW: frozenset[str] = frozenset()


def expand_shortener(url: str) -> str:
    """NOT IMPLEMENTED, and named so the gap is visible rather than forgotten.

    Resolving `bit.ly/x` needs a network round trip per URL. That belongs in
    the harvest, where a request is already being made and its failure is
    already reported, not in a pure normaliser called in a loop. Returning the
    input unchanged is the honest behaviour: the URL is not expanded, and
    nothing pretends it was.
    """
    return url


def canonical_url(url: str | None) -> str | None:
    """One spelling of a page. `None` in, `None` out; unparseable in, unchanged out.

    Never raises. A URL this cannot read is returned as it arrived, because a
    link that still works is worth more than a tidy one that does not.
    """
    if not url or not url.strip():
        return url
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return url
    if not parts.scheme or not parts.netloc:
        # A relative or malformed reference. Canonicalising it would invent a
        # host, which is the one thing a normaliser must never do.
        return url

    scheme = parts.scheme.lower()
    # http -> https is NOT done. It looks harmless and is a guess about what
    # the host serves; a host that does not answer on 443 would get a dead link.

    host = parts.netloc.lower()
    if host.startswith("www.") and host[4:] not in _KEEP_WWW:
        host = host[4:]
    # A default port is noise; a non-default one is part of the address.
    for default in (":80", ":443"):
        if host.endswith(default) and (
            (default == ":80" and scheme == "http") or (default == ":443" and scheme == "https")
        ):
            host = host[: -len(default)]

    query = urlencode(
        [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
         if k.lower() not in TRACKING_KEYS]
    )

    path = parts.path
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/") or "/"

    # `#!` was a routing convention and still addresses a page on old hosts.
    fragment = parts.fragment if parts.fragment.startswith("!") else ""

    return urlunsplit((scheme, host, path, query, fragment))


def same_page(a: str | None, b: str | None) -> bool:
    """Whether two URLs address one page, after canonicalisation.

    Deliberately not `canonical_url(a) == canonical_url(b)` at the call site:
    naming the question stops the comparison being written four ways in four
    places, each subtly different.
    """
    if a is None or b is None:
        return False
    return canonical_url(a) == canonical_url(b)
