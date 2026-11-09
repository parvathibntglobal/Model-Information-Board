"""Does a phrase match a topic? Code, not a model.

A phrase matches when EVERY word of it appears in the text as a whole word,
in any order, ignoring case. A word may carry one plain English ending
(s, es, d, ed, ing), so "limit" matches "limits" and "limited".

Deliberately narrow. Matching any word that merely STARTS with the phrase word
would let "ai" match "aim" and "cost" match "costume": a permissive pattern
that succeeds on the wrong input (CLAUDE.md rule 12). The cost is recall:
"hit" does not match "hitting". Tune the phrases, not the matcher.
"""

from __future__ import annotations

import re
from functools import cache

_WORD = re.compile(r"\w+")
_ENDINGS = r"(?:s|es|d|ed|ing)?"


@cache
def _patterns(phrase: str) -> tuple[re.Pattern[str], ...]:
    words = _WORD.findall(phrase.lower())
    if not words:
        raise ValueError(f"phrase has no words: {phrase!r}")
    return tuple(re.compile(rf"(?<!\w){re.escape(w)}{_ENDINGS}(?!\w)", re.I) for w in words)


def matches(phrase: str, text: str) -> bool:
    return all(p.search(text) for p in _patterns(phrase))
