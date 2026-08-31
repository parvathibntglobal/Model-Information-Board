"""Does a document carry reproduction artifacts? Counted in code, not judged by a model.

`has_repro_steps` feeds the evidence tier, which is WEIGHTING — and rule 2
forbids a model participating in weighting. Today it is read from
`claim.has_repro_steps` (the extractor's opinion), the same rule-2 shape that
`has_numbers` was already moved off the claim to fix. This is the code-counted
replacement: a deterministic scan for the artifacts that make a report
reproducible — a code fence, a command line, a stack trace, an error string,
numbered steps, or the words "steps to reproduce".

Conservative and observable, not a judgement: it answers "are the artifacts of
reproducibility present in the text", which is a fact, not "is this good
evidence", which would be the weighting decision code is allowed to make FROM
this fact but a model is not.
"""

from __future__ import annotations

import re

_REPRO = [
    re.compile(p, re.IGNORECASE | re.MULTILINE)
    for p in (
        r"```",                                    # a fenced code block
        r"^\s*(?:\$|>>>|#|>)\s",                    # a shell / REPL prompt at line start
        r"\bsteps?\s+to\s+reproduce\b",
        r"\bto\s+reproduce\b",
        r"\btraceback \(most recent call last\)",  # a Python stack trace
        r"\b\w+(?:Error|Exception)\b\s*[:(]",       # TypeError: / SomeException(
        r"^\s*\d+\.\s+\S",                          # a numbered step
        r"\b(?:pip install|npm install|npm run|git clone|docker run|curl)\b",
    )
]


def has_repro_steps(text: str) -> bool:
    """True when the text carries a reproduction artifact. No model involved."""
    return any(pattern.search(text) for pattern in _REPRO)
