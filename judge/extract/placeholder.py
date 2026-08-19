"""Bodies that are a platform's tombstone rather than a person's writing.

Rule 1 holds perfectly here and means nothing. `[removed]` is nine characters
of real text: a quote of it is a verbatim substring of what the extractor was
given, it resolves through the offset map to the right document and the right
author, and it says nothing at all. Verification cannot see the difference,
because there is no difference to see - the guarantee is about FIDELITY and
this is a failure of CONTENT.

Measured rather than assumed, by E1: a `[removed]` body scores
`has_error_strings = True` today, because the pattern matches on `[` and `]`
and does not care what is between them, and its 9 characters clear the
8-character floor. So it passes triage and reaches extraction. Six of 4,153
documents in the corpus - small, and the direction is the point.

WHERE THE SKIP BELONGS, AND WHY IT IS HERE

Before the model call. Cheaper than verifying afterwards, it saves a call that
can only produce something worthless, and it cannot be bypassed by a later
caller the way a verification-time check can.

THE WEAKER TEST, AND IT IS WEAKER ON PURPOSE

`collect/` marks these at parse time, because Reddit setting a body to exactly
`[removed]` is a fact about the PLATFORM and a person typing those nine
characters is a coincidence. That mark is the right signal and this lane
cannot read it yet: `document.status`'s CHECK permits `kept | filtered |
rejected | tombstoned` and nothing else, so `'removed'` cannot currently be
written. Demonstrated against Postgres rather than inferred.

So this matches on the text, which cannot tell the platform's placeholder from
a person quoting one. That is a real false positive and the cost is bounded:
the worst case is skipping a document whose entire body is the nine characters
`[removed]`, which has nothing to quote either way.

**When the vocabulary permits the mark, `is_placeholder_status` becomes the
test and this becomes the fallback.** Written that way round now so the upgrade
is deleting a branch rather than rewriting a rule.
"""

from __future__ import annotations

#: Exactly what the platform writes. Compared after stripping, and NOT a
#: substring test: a comment that merely mentions `[removed]` while discussing
#: moderation is somebody's writing and belongs in the corpus.
PLACEHOLDER_BODIES = frozenset({"[removed]", "[deleted]"})

#: What `collect/` sets once `document_status_ck` permits it. Kept here so the
#: upgrade is a one-line change in one place.
PLACEHOLDER_STATUS = "removed"


def is_placeholder_body(text: str) -> bool:
    """Whether this body is a tombstone rather than writing.

    Exact match after stripping. A substring test would drop any comment
    discussing removal, which is a real conversation about moderation and
    exactly the sort of thing this board should carry.
    """
    return text.strip() in PLACEHOLDER_BODIES


def is_placeholder_status(status: str | None) -> bool:
    """The strong test, for when `collect/`'s mark is readable.

    Preferred over the text match wherever a status is available, because it
    distinguishes the platform writing the placeholder from a person typing
    it - knowledge that exists only at parse time.
    """
    return status == PLACEHOLDER_STATUS


def readable_documents(
    raw_text_of: dict[str, str], status_of: dict[str, str] | None = None
) -> dict[str, str]:
    """The documents worth sending to a model.

    `status_of` wins where present. Where it is absent - which is everywhere
    today - the text match stands in.
    """
    statuses = status_of or {}
    return {
        doc_id: text
        for doc_id, text in raw_text_of.items()
        if not is_placeholder_status(statuses.get(doc_id)) and not is_placeholder_body(text)
    }


def has_nothing_to_extract(
    raw_text_of: dict[str, str], status_of: dict[str, str] | None = None
) -> bool:
    """True when there ARE documents and every one is a placeholder.

    The whole point of the skip: a thread of nothing but tombstones costs a
    model call and can only produce a verbatim quote of `[removed]`.

    AN EMPTY `raw_text_of` RETURNS FALSE, and the first version of this
    returned True on the argument that there was equally nothing to extract.
    That was wrong, and it broke a security check: the forged-marker test
    supplies `raw_text_of={}` with text that forges a block marker, so the
    early return fired and `wrap_untrusted` never ran. An ATTACK came back as
    "no claims found" - which is precisely the distinction that test exists to
    protect, and the one this skip must not blur.

    An empty mapping is a thread whose documents were not supplied. That is a
    malformed input, not a tombstoned one, and the two need opposite handling:
    a tombstone is skipped, a malformed thread must still reach every check
    downstream of here.
    """
    if not raw_text_of:
        return False
    return not readable_documents(raw_text_of, status_of)
