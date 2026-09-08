"""Prose out of a platform payload. The assembly half of the `content_hash` ruling.

WHY EXTRACTION LIVES HERE AND NOT IN THE WRITER

`docs/engineer-1/ruling-what-content-hash-identifies.md`:

    content_hash   the hash of the bytes the platform gave us, unmodified
    text_ref       the location of those same bytes
    prose          derived at ASSEMBLY, never stored in place of the payload

Storing prose in place of the payload is what broke 1,517 reddit rows: it left
the fetched artifact unreferenced (`document` has one ref column, no `raw_ref`)
and unidentified, so a tombstone hash fingerprinted a string we assembled and
MOVED whenever our extractor changed - NFR-6 and NFR-4 both.

The writer also runs before anyone knows the assembly SHAPE. `issue_body_only`,
`post_body_only` and `specificity_x_log_engagement@observed` want different prose
from the same bytes - a thread wants each comment's body separately so the offset
map can attribute spans, a post wants title plus selftext joined. A writer that
picks the prose is picking for a shape not yet chosen.

**Blog already worked this way** and is the only platform with claims on the
board: `text_ref` -> raw HTML, `content_hash` -> that HTML's hash,
`extract_article_text` (trafilatura) at assembly. This module is the same
arrangement for the two platforms that lacked it.

WHY IT REFUSES RATHER THAN FALLING BACK TO THE INPUT

A payload that will not parse is not prose. Passing the raw string through would
reproduce the original defect exactly - `assemble_issue` flattening
`{"url":"https://api.github.com/...` verbatim, and a quote then verifying against
a FIELD VALUE while `quote_verified` reported true. Rule 1 returning true for the
wrong reason.

So `NotAPayload` is raised and named, and the caller counts it. 246 reddit rows
still point at pre-extracted prose whose payload was never stored, and they will
refuse here. That is correct: they are real text with broken provenance, and a
caller that wants them must say so deliberately rather than have this function
guess.
"""

from __future__ import annotations

import json

#: The join between a title and a body. MUST NOT CHANGE without re-flattening
#: every affected thread_context: `scripts/repoint_reddit_text_refs.py` used
#: exactly `title + "\n\n" + selftext`, so the 1,512 contexts built from it hold
#: text with these two newlines in it. A different separator shifts every offset
#: in every offset_map, and offsets are the one thing that cannot be recovered
#: later (`collect/CLAUDE.md`, first rule).
TITLE_SEPARATOR = "\n\n"


class NotAPayload(ValueError):
    """The bytes are not a payload this extractor recognises. Named, not guessed."""


def _loaded(blob: str, *, what: str) -> dict:
    if not blob or not blob.strip():
        raise NotAPayload(f"{what}: empty input")
    try:
        payload = json.loads(blob)
    except ValueError as exc:
        # A REFUSAL, NOT A FALLBACK. Returning `blob` here is the original
        # defect with the direction reversed: prose that is really an envelope
        # got flattened, and an envelope that is really prose would get stored
        # as a document whose provenance nothing can check.
        raise NotAPayload(f"{what}: not JSON ({exc})") from exc
    if not isinstance(payload, dict):
        raise NotAPayload(f"{what}: JSON is {type(payload).__name__}, not an object")
    return payload


def reddit_prose(blob: str) -> str:
    """A Reddit post or comment payload -> the text a human wrote.

    A POST is `title` plus `selftext`; a COMMENT is `body`. Both are checked
    because one sweep stores posts and another stores comments, and a function
    that handled only posts would refuse every comment with a message about
    missing fields rather than about the shape.
    """
    payload = _loaded(blob, what="reddit payload")

    if "selftext" in payload or "title" in payload:
        title = payload.get("title") or ""
        selftext = payload.get("selftext") or ""
        text = f"{title}{TITLE_SEPARATOR}{selftext}"
    elif "body" in payload:
        text = payload.get("body") or ""
    else:
        raise NotAPayload(
            "reddit payload: no `selftext`, `title` or `body`. A listing page "
            "has `data` or `posts` at its top level and is not one document."
        )

    if not text.strip():
        # DISTINGUISHED from a parse failure. A post with an empty title and an
        # empty selftext is a real post that says nothing, and assembling it
        # would build a context every quote fails against - which reads as a
        # fabricating extractor rather than as an empty document.
        raise NotAPayload("reddit payload: parsed, and every text field is empty")
    return text


def github_issue_prose(blob: str) -> str:
    """A GitHub issue payload -> title plus body.

    THIS IS THE FIX FOR THE DEFECT NOBODY HAD LOOKED FOR. `github.py:583` sets
    `text_ref = issue.ref`, correctly - that is the payload, and `content_hash`
    identifies one document because of it. `assemble_issue` then flattened the
    payload VERBATIM, so all 80 github thread_contexts hold
    `{"url":"https://api.github.com/repos/...`. The prose is present inside the
    JSON as `"body": "..."`, so a quote of it verifies by substring and reports
    clean.
    """
    payload = _loaded(blob, what="github issue payload")
    if "body" not in payload and "title" not in payload:
        raise NotAPayload(
            "github issue payload: no `title` or `body`. A search response "
            "carries `items` and covers a hundred issues."
        )
    title = payload.get("title") or ""
    body = payload.get("body") or ""
    text = f"{title}{TITLE_SEPARATOR}{body}"
    if not text.strip():
        raise NotAPayload("github issue payload: parsed, and title and body are empty")
    return text


# ── the five platforms added 2026-09-07 ──────────────────────────────────
#
# Same arrangement, one function per payload shape. These exist because the
# adapters store CONTAINERS by ruling, so without a prose function a stored
# payload can never become text - and the failure would be silent in the worst
# direction: `assemble_*` would flatten the container, a quote would verify
# against a FIELD VALUE by substring, and `quote_verified` would report true.
# That is rule 1 returning true for the wrong reason, which this module exists
# to prevent, and it has already happened twice on two platforms.
#
# WHY ONE FUNCTION PER SHAPE RATHER THAN ONE THAT SNIFFS THE KEYS. A sniffer
# would have to guess, and a guess that lands on the wrong branch produces prose
# rather than a refusal - so the failure would be text nobody can attribute
# instead of a `NotAPayload` somebody counts. `reddit_prose` already carries two
# shapes and says why: one sweep stores posts and another stores comments, and
# both are `source = 'reddit'`. The same is true here for Hacker News (a comment
# or its story) and Hugging Face (a discussion or one of its comment events), so
# those two functions handle both of their own shapes and nothing else.


def arxiv_paper_prose(blob: str) -> str:
    """An arXiv single-entry Atom feed -> title plus abstract.

    XML, not JSON, so `_loaded` does not apply - and the refusal has to be
    explicit for the same reason it is there: passing the raw feed through would
    flatten markup into the extractor's input and let a quote verify against a
    tag.

    A MULTI-ENTRY FEED IS REFUSED RATHER THAN SLICED. A caller reaching here
    with a search page has the wrong `text_ref`, which is the artifact-choice
    defect the content_hash ruling exists to catch - not something to paper over
    by taking the first entry.
    """
    from xml.etree import ElementTree

    if not blob or not blob.strip():
        raise NotAPayload("arxiv payload: empty input")
    try:
        feed = ElementTree.fromstring(blob)
    except ElementTree.ParseError as exc:
        raise NotAPayload(f"arxiv payload: not XML ({exc})") from exc

    atom = "{http://www.w3.org/2005/Atom}"
    entries = feed.findall(f"{atom}entry")
    if not entries:
        raise NotAPayload(
            "arxiv payload: no <entry>. A query that matched nothing returns a "
            "feed with none, and that is not a document."
        )
    if len(entries) > 1:
        raise NotAPayload(
            f"arxiv payload: {len(entries)} entries. `text_ref` must name a "
            "single-entry id_list response, not a search page - one search "
            "response covers a hundred papers and cannot identify one document."
        )
    entry = entries[0]
    title = " ".join((entry.findtext(f"{atom}title") or "").split())
    summary = (entry.findtext(f"{atom}summary") or "").strip()
    text = f"{title}{TITLE_SEPARATOR}{summary}"
    if not text.strip():
        raise NotAPayload("arxiv payload: parsed, and title and summary are empty")
    return text


def devto_article_prose(blob: str) -> str:
    """A dev.to article payload -> title plus `body_markdown`.

    `body_markdown` AND NOT `body_html`, because the extractor is shown prose
    and markdown is the closer of the two - and not `description`, which is a
    truncated blurb: an article assembled from its description would be a
    150-character teaser that extraction reports on normally.
    """
    payload = _loaded(blob, what="devto article payload")
    if "body_markdown" not in payload and "title" not in payload:
        raise NotAPayload(
            "devto article payload: no `title` or `body_markdown`. A search "
            "response is a LIST and carries neither - `body_markdown` appears "
            "only on the single-article response."
        )
    title = payload.get("title") or ""
    body = payload.get("body_markdown") or ""
    if not body.strip() and payload.get("body_html"):
        # NAMED RATHER THAN SUBSTITUTED. An article with HTML and no markdown is
        # a real dev.to state (a crosspost), and falling back silently would mix
        # two text sources in one column with nothing recording which is which.
        raise NotAPayload(
            "devto article payload: `body_markdown` is empty and `body_html` is "
            "not. That is a crosspost, and choosing between the two is a "
            "decision for whoever needs it, not a fallback."
        )
    text = f"{title}{TITLE_SEPARATOR}{body}"
    if not text.strip():
        raise NotAPayload("devto article payload: parsed, and every text field is empty")
    return text


def hackernews_prose(blob: str) -> str:
    """A Hacker News item payload -> the text a human wrote.

    A COMMENT is `text`; a STORY is `title` plus `text`, where `text` is the
    self-post body and is absent for a link submission. Both shapes are handled
    for the reason `reddit_prose` handles two: this adapter writes comments as
    evidence AND their stories as subject anchors, and both are
    `source = 'hackernews'`.

    HTML ENTITIES AND `<p>` TAGS ARE UNESCAPED HERE, AT ASSEMBLY, AND NOWHERE
    ELSE. The API returns the text HTML-escaped with `<p>` between paragraphs,
    so a quote of what a reader can see would fail verification against the raw
    field while the text plainly contains it - rule 1 failing for the wrong
    reason, the mirror of the defect this module was built for.

    It happens here rather than in the fetcher because a transformation before
    the hash would put derived bytes under `content_hash`.
    """
    import html as html_module
    import re as re_module

    payload = _loaded(blob, what="hackernews payload")
    if "text" not in payload and "title" not in payload:
        raise NotAPayload(
            "hackernews payload: no `title` or `text`. A search response carries "
            "`hits` and covers many items."
        )
    title = payload.get("title") or ""
    body = payload.get("text") or ""
    text = f"{title}{TITLE_SEPARATOR}{body}" if title else body

    # HN's paragraph separator has no closing tag. Turned into two newlines
    # BEFORE tags are stripped, so paragraphs do not run together into one line
    # - which would change where a quote's whitespace falls.
    text = re_module.sub(r"<p>\s*", "\n\n", text)
    text = re_module.sub(r"<[^>]+>", "", text)
    text = html_module.unescape(text)

    if not text.strip():
        raise NotAPayload(
            "hackernews payload: parsed, and there is no text. A dead or flagged "
            "comment keeps its record and loses its text, which is a real state - "
            "the adapter stores those as status='filtered'."
        )
    return text


def huggingface_prose(blob: str) -> str:
    """A Hugging Face discussion or comment-event payload -> the markdown written.

    TWO SHAPES, one function, for the reason `reddit_prose` has two:

        a comment event   the `data.latest.raw` markdown one person wrote
        a discussion      the THREAD ROOT, whose own text is its title plus its
                          FIRST comment, because that is what the person who
                          opened it wrote

    `data.latest.raw` and not the rendered HTML: the raw markdown is what the
    author typed, and `latest` rather than an earlier revision because an edited
    comment's current text is the text that is public.
    """
    payload = _loaded(blob, what="huggingface payload")

    if payload.get("type") == "comment" or "data" in payload:
        raw = ((payload.get("data") or {}).get("latest") or {}).get("raw")
        if not raw or not str(raw).strip():
            raise NotAPayload(
                "huggingface comment event: `data.latest.raw` is empty. A hidden "
                "comment keeps its event and loses its text; the adapter stores "
                "those as status='filtered'."
            )
        return str(raw)

    if "events" in payload or "title" in payload:
        title = payload.get("title") or ""
        first = ""
        for event in payload.get("events") or ():
            if isinstance(event, dict) and event.get("type") == "comment":
                first = ((event.get("data") or {}).get("latest") or {}).get("raw") or ""
                break
        text = f"{title}{TITLE_SEPARATOR}{first}"
        if not text.strip():
            raise NotAPayload(
                "huggingface discussion: no title and no first comment text"
            )
        return text

    raise NotAPayload(
        "huggingface payload: neither a comment event nor a discussion. A "
        "discussions LIST has `discussions` at its top level and is not one "
        "document."
    )


def x_post_prose(blob: str) -> str:
    """An X post payload -> its text. THREE PLACES IT CAN BE, in one order.

    ⚠  THIS FUNCTION WAS WRONG UNTIL 2026-09-08 AND NOTHING COULD HAVE TOLD US.
       It read a top-level `text` key, which the twitter241 payload does not
       have: the real shape is a GraphQL `Tweet` whose text is under `legacy`.
       So it raised `NotAPayload` on **50 of 50** stored X documents the first
       time a real corpus existed - the whole platform produced no prose.

       IT WAS UNTESTABLE BEFORE THAT, because no X request had ever been made
       from the pipeline path, and the fixtures were built to the same
       assumption as the code. `collect/adapters/x.py:_post_of` read `legacy`
       CORRECTLY the whole time, which is the part worth recording: two readers
       of one payload, one right and one wrong, and only the wrong one was on
       the path that turns bytes into text. `has_artifact` records what two
       definitions of one concept cost; this is that shape across two modules.

    THE ORDER MATTERS AND IS NOT A PREFERENCE:

        note_tweet…result.text   THE COMPLETE TEXT of a long post. Measured
                                 2026-09-08: 21 of 50 payloads carry one, and
                                 on those `legacy.full_text` is TRUNCATED -
                                 250 characters against 190 on the first. Read
                                 first, or a long post's evidence is cut off
                                 mid-sentence and a quote of the missing half
                                 fails rule 1's substring check while the
                                 reader can plainly see it.
        legacy.full_text         the post's text. Present on 50 of 50.
        text                     a top-level field, for a provider shape that
                                 offers one. Kept last rather than deleted
                                 because `SCRAPER_PROVIDER` is swappable and
                                 the ruling pins only which provider was
                                 reviewed, not what its envelope looks like.

    The refusal is still the value: a caller handed a search PAGE gets
    `NotAPayload` rather than a silently flattened envelope whose text fields
    would let a quote verify by substring against the wrong document.
    """
    payload = _loaded(blob, what="x post payload")

    note = (
        (payload.get("note_tweet") or {}).get("note_tweet_results") or {}
    ).get("result") or {}
    legacy = payload.get("legacy") or {}
    for candidate in (note.get("text"), legacy.get("full_text"), payload.get("text")):
        if candidate and str(candidate).strip():
            return str(candidate)

    raise NotAPayload(
        "x post payload: no text in `note_tweet.note_tweet_results.result.text`, "
        "`legacy.full_text` or a top-level `text`. A search response carries its "
        "posts under `data` as a LIST and covers many documents; a single post "
        "carries `legacy`."
    )
