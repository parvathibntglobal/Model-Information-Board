"""What code checks in a paraphrase or a summary before it is stored.

AN LLM MAY PROPOSE, IT MAY NEVER DECIDE (rule 2). These checks are the part
that decides, and they decide only SHAPE - they cannot tell whether a
paraphrase is faithful, and a model checking a model is what rule 1 refuses.
What they can tell, mechanically:

    copied run      the longest run of consecutive words shared with the
                    excerpts. Over the contract's limit the "paraphrase" is a
                    quote in disguise, which for Reddit and X is exactly what
                    the embed-only terms forbid.
    numbers         every number written must appear in what it was written
                    from. A model that adds "40%" has synthesised a figure
                    (rule 3); one that turns "4.1" into "4" has changed a model.
    identity        no URL, handle, subreddit or platform name - the source is
                    cited beside the text by code, never inside it by a model.
    length          bounded, non-empty.

Faithfulness is left to the reader, which is why every item carries its
source one click away, and to a person for the summary, which is reviewed.
"""

from __future__ import annotations

import re

_WORD = re.compile(r"[a-z0-9]+(?:['.][a-z0-9]+)*")
# A number as written: 4, 4.1, 97.1, 1,000, 0.25. The sign, unit and % are
# separate tokens so "$0.25/MTok" and "0.25" compare equal.
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_URL = re.compile(r"https?://|www\.|\b[\w-]+\.(?:com|org|net|io|ai|dev|to|it)\b/", re.I)
_HANDLE = re.compile(r"(?<![\w/])@\w|(?<![\w])/?\b[ur]/\w", re.I)
# A measured figure: a price, or a number with a unit. A bare version number
# ("4.6", "V4") is a name, not a measurement, and is not matched.
_FIGURE = re.compile(
    r"[$€£]\s?\d[\d,.]*|\d[\d,.]*\s?(?:%|percent\b|ms\b|milliseconds?\b|seconds?\b|"
    r"tokens?(?: per second|/s)?\b|tok/s\b|t/s\b|[kKmMbB]\b|GiB\b|GB\b|TB\b|x\b|times\b)",
)
# The EMBED-ONLY platforms. Those are cited only by their own embed, so our
# prose must not name them; GitHub or Hugging Face can be what a report is
# ABOUT ("ran it in GitHub Actions") and are not refused.
_PLATFORM = re.compile(r"\b(?:reddit|subreddit|redditor|twitter|tweet(?:ed|s)?|x\.com)\b", re.I)


def words(text: str) -> list[str]:
    return _WORD.findall((text or "").lower())


def numbers(text: str) -> set[str]:
    """Numbers as written, thousands separators dropped: `1,000` -> `1000`."""
    out = set()
    for n in _NUMBER.findall(text or ""):
        # A comma between digit groups of three is a separator; otherwise
        # (`4,5` as a decimal) it is kept, and must then match as written.
        out.add(n.replace(",", "") if re.fullmatch(r"\d{1,3}(?:,\d{3})+", n) else n)
    return out


def longest_shared_run(text: str, excerpts: list[str]) -> int:
    """The longest run of consecutive words `text` shares with any excerpt."""
    return len(longest_shared_phrase(text, excerpts).split())


def longest_shared_phrase(text: str, excerpts: list[str]) -> str:
    """That run itself, as words - what a retry is told not to reuse. Saying
    only "copies 7 words" left the model to guess which seven, and it often
    wrote them again (2026-10-21: 1,433 of 3,884 reports needed a retry and
    562 were still refused for copying after it)."""
    a = words(text)
    best, end = 0, 0
    for excerpt in excerpts:
        b = words(excerpt)
        if not a or not b:
            continue
        # Longest common substring over word lists, O(len(a) * len(b)). A
        # paraphrase is <= ~60 words and a report's excerpts a few hundred.
        prev = [0] * (len(b) + 1)
        for i, x in enumerate(a, 1):
            cur = [0] * (len(b) + 1)
            for j, y in enumerate(b, 1):
                if x == y:
                    cur[j] = prev[j - 1] + 1
                    if cur[j] > best:
                        best, end = cur[j], i
            prev = cur
    return " ".join(a[end - best:end])


def identity_problem(text: str) -> str | None:
    if _URL.search(text):
        return "contains a link"
    if _HANDLE.search(text):
        return "contains a handle or community name"
    m = _PLATFORM.search(text)
    if m:
        return f"names a platform ({m.group(0)})"
    return None


def unsourced_numbers(text: str, sources: list[str]) -> list[str]:
    allowed: set[str] = set()
    for s in sources:
        allowed |= numbers(s)
    return sorted(numbers(text) - allowed)


def paraphrase_problem(
    text: str, excerpts: list[str], model_label: str, *, max_chars: int, max_copied_words: int,
    topics: list[str] = (),
) -> str | None:
    """Why a paraphrase is refused, or None. The model's own name is allowed
    to carry its version number, and nothing else may add one.

    `topics` are the names the report's entries are filed under ("3D
    modeling"), which the prompt shows and the page shows as tags. A number in
    one may be repeated (2026-10-21: the last two unparaphrased reports were
    refused for the "3" of their own topic, "3D modeling", while their excerpts
    read "Fable 5.1 one shotted this"). Copying is still checked against the
    excerpts alone - a topic name is ours, not the author's words."""
    text = (text or "").strip()
    if not text:
        return "empty"
    if len(text) > max_chars:
        return f"longer than {max_chars} characters (it was {len(text)})"
    problem = identity_problem(text)
    if problem:
        return problem
    extra = unsourced_numbers(text, [*excerpts, *topics, model_label])
    if extra:
        return f"adds a number not in the excerpts ({', '.join(extra)})"
    phrase = longest_shared_phrase(text, excerpts)
    run = len(phrase.split())
    if run > max_copied_words:
        return (f"copies {run} consecutive words from the source (limit {max_copied_words}): "
                f"“{phrase}”")
    return None


def summary_problems(
    paragraphs: list[dict],
    sources: dict[str, list[str]],
    model_label: str,
    *,
    excerpts: dict[str, list[str]],
    max_words: int,
    max_paragraphs: int,
    max_copied_words: int,
    quantity_words: list[str],
) -> tuple[str | None, list[dict]]:
    """`(why the draft is refused, or None; flags for the reviewer)`.

    `sources` maps each citable report id to what the summary was written from
    (its paraphrase); `excerpts` to the source's own words, which the summary
    must not copy - reusing OUR paraphrase's wording is fine, copying the
    author's is not. A paragraph must cite at least one report, may cite only
    reports it was given, and may carry only numbers found in what it cites -
    so no count can be invented, and a version number cannot drift. Quantity
    words ("most engineers") are FLAGGED, not refused (rule 8): consensus is
    code's to state from counts, and the reviewer decides whether a flagged
    sentence stays.
    """
    if not paragraphs:
        return "no paragraphs", []
    if len(paragraphs) > max_paragraphs:
        return f"more than {max_paragraphs} paragraphs", []
    total = 0
    flags: list[dict] = []
    quantity = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in quantity_words) + r")\b", re.I)
    for i, p in enumerate(paragraphs, 1):
        text = (p.get("text") or "").strip() if isinstance(p, dict) else ""
        cites = p.get("cites") if isinstance(p, dict) else None
        if not text:
            return f"paragraph {i} is empty", []
        if not isinstance(cites, list) or not cites:
            return f"paragraph {i} cites no report", []
        unknown = [c for c in cites if c not in sources]
        if unknown:
            return (
                f"paragraph {i} cites reports it was not given "
                f"({', '.join(map(str, unknown[:5]))})",
                [],
            )
        problem = identity_problem(text)
        if problem:
            return f"paragraph {i} {problem}", []
        cited_texts = [t for c in cites for t in sources[c]]
        extra = unsourced_numbers(text, [*cited_texts, model_label])
        if extra:
            return f"paragraph {i} has a number its cited reports do not ({', '.join(extra)})", []
        run = longest_shared_run(text, [t for c in cites for t in excerpts.get(c, [])])
        if run > max_copied_words:
            return f"paragraph {i} copies {run} consecutive words from a source", []
        total += len(words(text))
        for m in quantity.finditer(text):
            flags.append(
                {
                    "check": "quantity word",
                    "paragraph": i,
                    "detail": f"“{m.group(0)}” claims how many reported it",
                }
            )
        # A FIGURE IS FLAGGED, NOT REFUSED: the prompt asks for none, the
        # number check has already tied it to its citations, and whether one
        # belongs on the page is the reviewer's call (rule 8).
        for m in _FIGURE.finditer(text):
            flags.append(
                {
                    "check": "measured figure",
                    "paragraph": i,
                    "detail": f"“{m.group(0).strip()}” - the page is meant to carry no figures",
                }
            )
    if total > max_words:
        return f"{total} words, over the {max_words}-word page", []
    return None, flags
