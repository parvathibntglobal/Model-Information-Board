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
