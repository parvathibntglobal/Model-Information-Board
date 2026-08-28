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
    affiliate / tracking link   provider link + params   reject.py rule 1
    sponsored disclosure        paid-placement wording   reject.py rule 2
    discount code               code for the product      reject.py rule 3
    minimum signal              too short to carry a claim   here

WHAT DOES NOT RUN HERE YET — named rather than skipped, because an absent check
must not read as a passed one:

    release-date sanity   reject.py rule 5, needs resolved model MENTIONS from a
                          deterministic resolver (not the extractor's)
    syndication           reject.py rule 4, needs the E3 dedup cluster
    language / bot        collect-side E4 triage, not judge's to run

So this is the promotional/placeholder/length subset of the funnel's step 6/2/3
— the part that needs only the document's text, which is exactly what a caller
has before the model call.
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
