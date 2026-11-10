"""HTML from a platform's API as plain text, for a person to read."""

from __future__ import annotations

import html
import re

_PARAGRAPH = re.compile(r"<p>|<br\s*/?>", re.I)
_TAG = re.compile(r"<[^>]+>")


def plain_text(value: str | None) -> str | None:
    """`<p>`, `&#x27;`, links and other tags as plain text. Blank is None."""
    if not value or not value.strip():
        return None
    text = html.unescape(_TAG.sub("", _PARAGRAPH.sub("\n\n", value))).strip()
    return text or None
