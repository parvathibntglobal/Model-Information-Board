"""The pre-LLM screen: deterministic hard gates run BEFORE the extractor reads.

The LLM must read only clean, on-topic text. Everything here is code — no model
— so a document dropped here never costs a token, and every drop carries a named
trigger: a caused absence is recorded, never silent (rule 4 on our own
machinery).

IT REUSES THE VET RULES RATHER THAN RESTATING THEM. The same
affiliate/sponsored/discount checks in `judge/vet/reject.py` that used to run
AFTER extraction (`judge/pipeline.py`, on `document.text` — which was never
populated, so they had never actually run: #190) run here instead, before the
model. Moving them earlier is the funnel change; the rules are unchanged, so
there is one description of "promotional", not two.

WHAT RUNS HERE — text only, needs nothing the LLM produces:

    platform placeholder        [removed]/[deleted]      judge/extract/placeholder.py
    minimum signal              too short to carry a claim   here
    bot self-identification     "I am a bot" / "beep boop"   here
    language                    not English (heuristic)      here
    affiliate / tracking link   provider link + params   reject.py rule 1
    sponsored disclosure        paid-placement wording   reject.py rule 2
    discount code               code for the product      reject.py rule 3

The language and bot checks are DELIBERATELY conservative — a false drop removes
a real voice, so both err toward keeping: language fires only on decisively
non-English text, and bot only on an explicit self-identification (the account
flags and karma heuristics need author metadata from harvest, and heuristics are
weights, not drops).

WHAT DOES NOT RUN HERE YET — named rather than skipped, because an absent check
must not read as a passed one:

    release-date sanity   reject.py rule 5. On the model-name fetch the model IS
                          known, so this runs in the fetch (not here) against the
                          fetched model's release date
    syndication           reject.py rule 4, needs the E3 dedup cluster (no writer)
    8★ behaviour          needs a signal vocabulary derived from near-misses; a
                          hand-written one would silently empty the corpus (rule 8)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from judge.extract.placeholder import is_placeholder_body
from judge.vet.reject import check as reject_check

#: A URL, loosely: enough to hand `reject.check` the links it inspects for
#: provider + tracking parameters. Not a validator — a false positive here only
#: gives the rule a string that will not match a provider domain.
_URL = re.compile(r"https?://[^\s)>\]}\"']+")

#: Below this, a document has no room to carry a claim with its condition. A
#: floor, not a judgement about content — the LLM's time is better spent on text
#: that could say something.
MIN_SIGNAL_CHARS = 40

#: Common English function words. Their near-total absence in Latin-script text
#: of any length is a strong signal it is not English.
_ENGLISH_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "be", "been",
    "to", "of", "in", "on", "at", "for", "with", "that", "this", "it", "its", "you",
    "i", "we", "they", "he", "she", "as", "by", "from", "not", "no", "have", "has",
    "had", "do", "does", "did", "will", "would", "can", "could", "should", "there",
    "their", "what", "when",
})

#: Internal markers E3 adds, stripped before language detection so "[root by …]"
#: and "[upside_down_face]" are not counted as the author's words.
_BRACKET_TAG = re.compile(r"\[[^\]]*\]")

#: Explicit bot self-identification. Reddit bots are usually required to say so,
#: which makes this high precision. NOT an attempt to enumerate bots — the flags
#: and account heuristics live at harvest, and heuristics are weights not drops.
_BOT_SELFID = [
    re.compile(p, re.I)
    for p in (
        r"\bi[' ]?a?m a bot\b",
        r"\bbeep[ -]?boop\b",
        r"\bthis action was performed automatically\b",
        r"\baction was performed automatically\b",
    )
]


def _is_bot_selfid(text: str) -> bool:
    return any(p.search(text) for p in _BOT_SELFID)


def _looks_non_english(text: str) -> bool:
    """Conservative: True only when the text is decisively not English.

    A false drop removes a real voice, so this errs hard toward KEEPING. Two
    decisive cases: majority non-Latin script, and Latin-script text of real
    length carrying not one common English function word (Spanish, French, …).
    Thin or code-shaped text is left alone.
    """
    body = _BRACKET_TAG.sub(" ", text)
    letters = [c for c in body if c.isalpha()]
    if len(letters) < 30:
        return False  # too little to judge; never drop on thin evidence
    non_ascii = sum(1 for c in letters if not c.isascii())
    if non_ascii / len(letters) > 0.5:
        return True  # majority non-Latin script (Cyrillic, CJK, Arabic, …)
    # Latin script, real length, and not one English function word.
    words = re.findall(r"[a-z]{2,}", body.lower())
    return len(words) >= 20 and not any(w in _ENGLISH_STOPWORDS for w in words)


@dataclass(frozen=True)
class ScreenVerdict:
    """Whether the text may reach the model, and why not when it may not."""

    dropped: bool
    trigger: str | None = None
    detail: str = ""


def links_in(text: str) -> list[str]:
    return _URL.findall(text)


def screen(*, text: str) -> ScreenVerdict:
    """Run the pre-LLM hard gates on one piece of text. No model, no cost.

    First trigger wins, cheapest first. A `ScreenVerdict(dropped=False)` means
    the text passed every gate that can run pre-LLM — NOT that it passed every
    rule (see the module docstring for what is deferred).
    """
    stripped = text.strip()

    # Cheapest and most decisive first. A tombstone quotes as itself and means
    # nothing; a too-short document cannot carry a claim.
    if is_placeholder_body(stripped):
        return ScreenVerdict(True, "placeholder", "platform tombstone, nothing to quote")
    if len(stripped) < MIN_SIGNAL_CHARS:
        return ScreenVerdict(
            True, "too_short", f"under {MIN_SIGNAL_CHARS} chars — no room for a claim"
        )
    if _is_bot_selfid(text):
        return ScreenVerdict(True, "bot_selfid", "author self-identifies as a bot")
    if _looks_non_english(text):
        return ScreenVerdict(
            True, "non_english", "text is not English by the conservative heuristic"
        )

    # The promotional rules, from the one place they are defined. Only the
    # text-only rules can fire: rule 4 needs a dedup cluster and rule 5 needs
    # resolved mentions, and passing neither leaves them inert rather than wrong.
    verdict = reject_check(
        text=text,
        links=links_in(text),
        published_at=None,
        model_release_dates={},
        mentioned_models=[],
    )
    if verdict.rejected:
        trigger = verdict.trigger.value if verdict.trigger is not None else "rejected"
        return ScreenVerdict(True, trigger, verdict.detail)

    return ScreenVerdict(False, None, "passed the pre-LLM screen")
