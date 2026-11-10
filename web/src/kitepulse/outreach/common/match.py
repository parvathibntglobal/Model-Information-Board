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


def span(phrase: str, text: str) -> int | None:
    """The fewest consecutive words of `text` that hold every word of `phrase`.

    1 word for a one-word phrase, 2 for "agent stuck" written as "agent stuck",
    and so on. None when some word of the phrase is not in the text at all.
    Same word rule as `matches` (whole word, one plain ending).

    Used by the Shortlister to tell "my claude code is stuck" from a long
    comment that says "Claude Code" in one paragraph and "stuck" in another.
    """
    pats = _patterns(phrase)
    tokens = [m.group() for m in _WORD.finditer(text)]
    events = sorted((i, k) for k, p in enumerate(pats)
                    for i, tok in enumerate(tokens) if p.fullmatch(tok))
    need = len(pats)
    if len({k for _, k in events}) < need:
        return None
    have: dict[int, int] = {}
    best, left = None, 0
    for pos, k in events:
        have[k] = have.get(k, 0) + 1
        while len(have) == need:
            width = pos - events[left][0] + 1
            best = width if best is None else min(best, width)
            lk = events[left][1]
            have[lk] -= 1
            if not have[lk]:
                del have[lk]
            left += 1
    return best
