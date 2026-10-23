"""What code checks in a paraphrase or a summary before it is stored.

AN LLM MAY PROPOSE, IT MAY NEVER DECIDE (rule 2). These checks are the part
that decides, and they decide only SHAPE - they cannot tell whether a
paraphrase is faithful, and a model checking a model is what rule 1 refuses.
What they can tell, mechanically:

    copied run      the longest run of consecutive words shared with the
                    excerpts. Over the contract's limit the "paraphrase" is a
                    quote in disguise, which for Reddit and X is exactly what
                    the embed-only terms forbid. A word is a run of letters
                    or digits in any script; Chinese, Japanese and Korean text
                    has no spaces, so each of those characters is one word.
    numbers         every number written in digits must appear, exactly, in
                    what it was written from ("4" does not match "4.1"). A
                    number from the model's own name is allowed only where it
                    follows the same word as in the name ("GLM 5", not "costs
                    5"). An integer whose decimal form is in the source
                    ("4.1") is allowed only after a word the source also puts
                    before that integer, which catches "4.1" turned into "4".
                    Number words two..ninety, hundred, thousand, million,
                    billion, dozen(s) and percent must be in the source as a
                    word or as the digits.
    identity        no URL, bare domain (`huggingface.co`), `@`/`u/`/`r/`
                    handle, or embed-only platform name - the source is cited
                    beside the text by code, never inside it by a model.
    length          bounded, non-empty.

WHAT THESE DO NOT CATCH, said so nobody assumes they do: "one", "half",
"twice" and other words for numbers outside that list; a bare "X" (it is also
a letter); a community named without `r/`; a domain on a top-level name not
in `_TLD`; and faithfulness - a number that IS in the source but attached to
the wrong thing passes. Faithfulness is left to the reader, which is why every
item carries its source one click away, and to a person for the summary,
which is reviewed.
"""

from __future__ import annotations

import re

# Scripts written without spaces: each character counts as one word, or a
# copied Chinese sentence would be one "word" and pass any limit.
_CJK = "぀-ヿ㐀-䶿一-鿿豈-﫿가-힯"
_WORD = re.compile(rf"[{_CJK}]|[^\W_{_CJK}]+(?:['.][^\W_{_CJK}]+)*")
# A number as written: 4, 4.1, 97.1, 1,000, 0.25. The sign, unit and % are
# separate tokens so "$0.25/MTok" and "0.25" compare equal.
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_TLD = r"(?:com|org|net|io|ai|dev|to|it|co|me|app|gg|so|sh|xyz|tv|news|blog)"
_URL = re.compile(r"https?://|www\.", re.I)
# A bare domain, slash or not: "via huggingface.co" is a link in all but markup.
_DOMAIN = re.compile(rf"\b[a-z0-9][\w-]*(?:\.[\w-]+)*\.{_TLD}\b", re.I)
_SPELLED = re.compile(
    r"\b(two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
    r"fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|"
    r"eighty|ninety|hundreds?|thousands?|millions?|billions?|dozens?|percent|per cent)\b"
    r"(?!\.\w)",  # not a name that starts with one: "three.js"
    re.I,
)
_SPELLED_DIGITS = {
    "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8",
    "nine": "9", "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
    "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17", "eighteen": "18",
    "nineteen": "19", "twenty": "20", "thirty": "30", "forty": "40", "fifty": "50",
    "sixty": "60", "seventy": "70", "eighty": "80", "ninety": "90",
}
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


def _normal(n: str) -> str:
    # A comma between digit groups of three is a separator; otherwise
    # (`4,5` as a decimal) it is kept, and must then match as written.
    return n.replace(",", "") if re.fullmatch(r"\d{1,3}(?:,\d{3})+", n) else n


def numbers(text: str) -> set[str]:
    """Numbers as written, thousands separators dropped: `1,000` -> `1000`."""
    return {_normal(n) for n in _NUMBER.findall(text or "")}


def number_spans(text: str) -> list[tuple[str, str]]:
    """Each number with the word written just before it: `("5", "glm")`."""
    text = text or ""
    out = []
    for m in _NUMBER.finditer(text):
        before = words(text[: m.start()])
        out.append((_normal(m.group(0)), before[-1] if before else ""))
    return out


def number_problem(text: str, sources: list[str], model_label: str) -> str | None:
    """Why the numbers in `text` are refused, or None (module docstring).

    ⚠ A SHORTENED DECIMAL IS CAUGHT ONLY WHEN THE SHORT FORM IS IN THE SOURCE
      NOWHERE ELSE. "4.1" written as "4" passes when the source also says "4"
      (e.g. "GLM 4"). A word-before rule that tried to tell those apart was
      measured 2026-10-23 on the 4,102 stored paraphrases (local copy): it
      refused 75 that passed before, among them "79" for a source's "79.0" -
      the same value - so it was not kept (rule 8).
    """
    allowed = set()
    for s in sources:
        allowed |= {n for n, _ in number_spans(s)}
    name = set(number_spans(model_label))
    extra = sorted({n for n, before in number_spans(text)
                    if (n, before) not in name and n not in allowed})
    if extra:
        return f"adds a number not in the excerpts ({', '.join(extra)})"
    source_words = {w for s in sources for w in words(s)}
    for m in _SPELLED.finditer(text):
        word = m.group(0).lower()
        if word in ("percent", "per cent"):
            ok = any("%" in s or re.search(r"\bper ?cent\b", s, re.I) for s in sources)
        elif word not in _SPELLED_DIGITS and not word.startswith("dozen"):
            # A multiplier after "per" or after a sourced number is a unit or a
            # scale ("$0.15 per million tokens", "2 million"), not a count of
            # its own: 99 of the 181 first-draft refusals were "per million".
            before = words(text[: m.start()])
            ok = word in source_words or bool(before and (before[-1] == "per"
                                                          or before[-1] in allowed))
        else:
            ok = word in source_words or _SPELLED_DIGITS.get(word) in allowed
        if not ok:
            return f"writes a number the excerpts do not have (“{m.group(0)}”)"
    return None


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


def identity_problem(text: str, model_label: str = "") -> str | None:
    """A domain in the model's own label ("Z.ai: GLM 5") is a vendor's name, and
    may be written; any other domain is a link."""
    if _URL.search(text):
        return "contains a link"
    own = {d.lower() for d in _DOMAIN.findall(model_label or "")}
    for m in _DOMAIN.finditer(text):
        if m.group(0).lower() not in own:
            return f"contains a link ({m.group(0)})"
    if _HANDLE.search(text):
        return "contains a handle or community name"
    m = _PLATFORM.search(text)
    if m:
        return f"names a platform ({m.group(0)})"
    return None


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
    problem = identity_problem(text, model_label) or number_problem(
        text, [*excerpts, *topics], model_label)
    if problem:
        return problem
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
        problem = identity_problem(text, model_label)
        if problem:
            return f"paragraph {i} {problem}", []
        cited_texts = [t for c in cites for t in sources[c]]
        problem = number_problem(text, cited_texts, model_label)
        if problem:
            return f"paragraph {i}: {problem.replace('the excerpts', 'its cited reports')}", []
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
