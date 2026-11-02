"""The three body blocks a guide carries, defined once (Guides phase B, 2026-10-30).

A blog post's `body` is a list of `[type, value]` blocks that
`web/src/board/views.js` `essayBlock` renders. A developer guide, a tutorial and
an error fix add three, and this module is the ONE place their shape is written
down: `generate_sample_blogs.export_post` builds them with the functions below,
`judge/blog_posts._problem` refuses a stored post whose block does not match
them, and `tests/test_guide_packs.py` renders what these builders produce through
the real `views.js`, so the page and the writer cannot drift apart.

    ["official_code", {"label", "lang", "code", "source": SOURCE}]
        One step's code, COPIED from an official source - never written by the
        post's writer (generate_sample_blogs.guide_violations checks it). The
        page draws it with a copy button and the source's name and link.
        ITS OWN TYPE NAME, not `code`: the older illustrative block is `code`
        with a string `source`, and telling the two apart by the shape of one
        field would let a malformed official block render as illustrative.

    ["code_tabs", {"label", "tabs": [{"lang", "code", "source": SOURCE}, ...]}]
        The same step in more than one language, one tab each; 2 to MAX_TABS
        tabs, no language twice.

    SOURCE = {"label", "repo", "path", "url", "ref"}
        label  what the page calls it (the official file's title)
        repo   owner/name on GitHub
        path   the file's path in the repository
        url    the file on github.com (https only)
        ref    the git ref the text was verified against: a blob sha (7+ hex)
               for a file, a release tag for a release note

    ["video", {"title", "speakers", "event", "date", "url", "thumbnail", "host", "duration"}]
        A TITLE CARD for a recorded talk from PyVideo's index (video_ref):
        metadata only, never a summary of what was said. `thumbnail` may be
        null - the page then draws a styled card with the title, never a broken
        image. `date` (YYYY-MM-DD) and `duration` (whole seconds) may be null
        and are then left off the card, never shown as zero (rule 6).

    ["sources_stamp", {"items": [ITEM, ...]}]
        ITEM = {"label", "repo", "ref", "url", "read_at", "licence", "basis"}
        The official files a guide rests on, near the top. `basis` is "copied"
        (code was copied from it and matched character for character) or
        "cited" (the text refers to it; nothing was copied), and the page words
        the two apart (#595 review).
        `read_at` is the date the harvest last read that repository with the
        file still at that ref (YYYY-MM-DD); `licence` is the repository's SPDX
        id as the harvest recorded it.

Nothing here touches a database or the raw store (judge/ never imports collect/).
"""

from __future__ import annotations

import re
from typing import Any

#: The block types this module defines.
GUIDE_BLOCK_TYPES = ("official_code", "code_tabs", "video", "sources_stamp")

SOURCE_KEYS = ("label", "repo", "path", "url", "ref")
VIDEO_KEYS = ("title", "speakers", "event", "date", "url", "thumbnail", "host", "duration")
STAMP_KEYS = ("label", "repo", "ref", "url", "read_at", "licence", "basis")
STAMP_BASES = ("copied", "cited")
#: The most tabs one `code_tabs` block may carry: the page's tabs are CSS only,
#: and web/src/styles/board.css switches exactly this many panes
#: (`:nth-of-type(1)` to `(6)`). A seventh would show its label and no code.
MAX_TABS = 6

_HTTPS = re.compile(r"^https://[^\s\"'<>]+$")
_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_LANG = re.compile(r"^[a-z0-9+#.-]{1,20}$")


class BlockError(ValueError):
    """A guide block that does not match its shape. Raised by the builders, so
    a malformed block never reaches a stored post (rule 12)."""


def _text(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def source_problem(s: Any) -> str | None:
    if not isinstance(s, dict) or set(s) != set(SOURCE_KEYS):
        return f"a code source needs exactly {', '.join(SOURCE_KEYS)}"
    if not all(_text(s[k]) for k in SOURCE_KEYS):
        return "a code source has an empty field"
    if not _REPO.match(s["repo"]):
        return f"a code source's repo {s['repo']!r} is not owner/name"
    if not _HTTPS.match(s["url"]):
        return "a code source's url is not https"
    return None


def _code_problem(v: Any, *, with_label: bool) -> str | None:
    keys = {"lang", "code", "source"} | ({"label"} if with_label else set())
    if not isinstance(v, dict) or set(v) != keys:
        return f"needs exactly {', '.join(sorted(keys))}"
    if not _text(v["code"]):
        return "has no code"
    if not (isinstance(v["lang"], str) and _LANG.match(v["lang"])):
        return f"has a language {v['lang']!r} that is not a short lower-case name"
    if with_label and not _text(v["label"]):
        return "has no label"
    return source_problem(v["source"])


def code_block(label: str, lang: str, code: str, source: dict) -> list:
    v = {"label": label, "lang": lang, "code": code, "source": dict(source)}
    if why := _code_problem(v, with_label=True):
        raise BlockError(f"code block {why}")
    return ["official_code", v]


def code_tabs_block(label: str, tabs: list[dict]) -> list:
    v = {"label": label, "tabs": [dict(t) for t in tabs]}
    if why := problem(["code_tabs", v]):
        raise BlockError(why)
    return ["code_tabs", v]


def video_block(**fields: Any) -> list:
    v = {k: fields.get(k) for k in VIDEO_KEYS}
    if set(fields) - set(VIDEO_KEYS):
        raise BlockError(f"video block has unknown fields {sorted(set(fields) - set(VIDEO_KEYS))}")
    if why := problem(["video", v]):
        raise BlockError(why)
    return ["video", v]


def sources_stamp_block(items: list[dict]) -> list:
    v = {"items": [dict(x) for x in items]}
    if why := problem(["sources_stamp", v]):
        raise BlockError(why)
    return ["sources_stamp", v]


def problem(block: Any) -> str | None:
    """Why `block` is not a well-formed guide block, or None. A block of
    another type - the illustrative `code` among them - is not this module's
    to judge."""
    if not (isinstance(block, list) and len(block) == 2):
        return None
    t, v = block
    if t == "official_code":
        why = _code_problem(v, with_label=True)
        return f"code block {why}" if why else None
    if t == "code_tabs":
        if not isinstance(v, dict) or set(v) != {"label", "tabs"} or not _text(v.get("label")):
            return "code_tabs needs a label and tabs"
        tabs = v["tabs"]
        if not isinstance(tabs, list) or not 2 <= len(tabs) <= MAX_TABS:
            return f"code_tabs needs 2 to {MAX_TABS} tabs"
        for i, tab in enumerate(tabs):
            if why := _code_problem(tab, with_label=False):
                return f"code_tabs tab {i} {why}"
        langs = [tab["lang"] for tab in tabs]
        if len(set(langs)) != len(langs):
            return "code_tabs gives one language twice"
        return None
    if t == "video":
        if not isinstance(v, dict) or set(v) != set(VIDEO_KEYS):
            return f"video needs exactly {', '.join(VIDEO_KEYS)}"
        if not _text(v["title"]):
            return "video has no title"
        if not (isinstance(v["url"], str) and _HTTPS.match(v["url"])):
            return "video url is not https"
        if v["thumbnail"] is not None and not (
            isinstance(v["thumbnail"], str) and _HTTPS.match(v["thumbnail"])
        ):
            return "video thumbnail is neither null nor an https url"
        if not (isinstance(v["speakers"], list) and all(_text(s) for s in v["speakers"])):
            return "video speakers must be a list of names (it may be empty)"
        if v["date"] is not None and not (isinstance(v["date"], str) and _DATE.match(v["date"])):
            return "video date is neither null nor YYYY-MM-DD"
        d = v["duration"]
        if d is not None and not (isinstance(d, int) and not isinstance(d, bool) and d >= 0):
            return "video duration is neither null nor whole seconds"
        if not (_text(v["event"]) and _text(v["host"])):
            return "video needs its event and host"
        return None
    if t == "sources_stamp":
        if (
            not isinstance(v, dict)
            or set(v) != {"items"}
            or not isinstance(v["items"], list)
            or not v["items"]
        ):
            return "sources_stamp needs a list of items"
        for i, it in enumerate(v["items"]):
            if not isinstance(it, dict) or set(it) != set(STAMP_KEYS):
                return f"sources_stamp item {i} needs exactly {', '.join(STAMP_KEYS)}"
            if not all(_text(it[k]) for k in STAMP_KEYS):
                return f"sources_stamp item {i} has an empty field"
            if it["basis"] not in STAMP_BASES:
                return f"sources_stamp item {i}'s basis is neither copied nor cited"
            if (
                not _REPO.match(it["repo"])
                or not _HTTPS.match(it["url"])
                or not _DATE.match(it["read_at"])
            ):
                return (f"sources_stamp item {i} needs owner/name, an https url "
                        "and a YYYY-MM-DD read date")
        return None
    return None
