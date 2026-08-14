"""E6 step 1 — hard rejection.

Binary, and rightly so. An affiliate link to the provider, or a claim dated
before the model existed, is not a weighting problem.

REJECTED IS NOT DELETED. Every rejected document is stored and appears on
/filtered with the trigger named, sorted by how close it came to passing.
A filter you cannot inspect cannot be trusted, and this audience will audit it —
being able to is the basis for trusting anything else on the page.

The four sophisticated paid-content tests — vendor phrase echo, embargo
clustering, never-negative author history, coordination graph — are NOT here.
Every one needs accumulated author or launch history that does not exist on day
one. They are the moat, they are deferred rather than dropped, and this stage's
job is to generate the history they need.

No language model participates in this file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from urllib.parse import parse_qs, urlparse


class RejectionTrigger(StrEnum):
    """Named on /filtered, so a reader can disagree with the specific rule."""

    AFFILIATE_LINK = "affiliate_link"
    SPONSORED_DISCLOSURE = "sponsored_disclosure"
    DISCOUNT_CODE = "discount_code"
    SYNDICATED_DUPLICATE = "syndicated_duplicate"
    PREDATES_MODEL = "predates_model"

    def explain(self) -> str:
        return _EXPLANATIONS[self]


_EXPLANATIONS = {
    RejectionTrigger.AFFILIATE_LINK: (
        "Links to a model provider carrying affiliate, referral or campaign "
        "tracking parameters. The author is paid on conversion."
    ),
    RejectionTrigger.SPONSORED_DISCLOSURE: (
        "The document states it is sponsored or a paid placement."
    ),
    RejectionTrigger.DISCOUNT_CODE: (
        "Carries a discount code for the product being reviewed."
    ),
    RejectionTrigger.SYNDICATED_DUPLICATE: (
        "Near-identical content already ingested from a different domain. "
        "The original is kept; this copy would inflate the voice count."
    ),
    RejectionTrigger.PREDATES_MODEL: (
        "Claims to describe a model that had not been released when this was "
        "published. Cheap to check, decisive, and it catches a surprising "
        "volume of fabrication."
    ),
}

# Affiliate and campaign markers. Presence alone is not damning — it must be on
# a link pointing at a model provider.
_TRACKING_PARAMS = frozenset(
    {"ref", "referral", "aff", "affiliate", "aff_id", "partner", "tag",
     "utm_source", "utm_campaign", "utm_medium", "fpr", "via", "irclickid"}
)

_PROVIDER_DOMAINS = frozenset(
    {"openai.com", "anthropic.com", "ai.google.dev", "deepmind.google",
     "mistral.ai", "deepseek.com", "cohere.com", "x.ai", "together.ai",
     "fireworks.ai", "groq.com", "replicate.com", "openrouter.ai"}
)

_SPONSORED_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"\bthis (?:post|article|video|review) is sponsored\b",
        r"\bsponsored by\b",
        r"\bpaid partnership\b",
        r"\bin partnership with\b.{0,40}\b(?:who|which) (?:paid|sponsored)\b",
        r"\b#(?:ad|sponsored|paidpartnership)\b",
        r"\bincludes paid promotion\b",
        r"\bi was paid to\b",
    )
]

_DISCOUNT_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"\buse (?:code|coupon)\s+[A-Z0-9]{3,}\b",
        r"\b(?:promo|discount|coupon) code\b",
        r"\b\d{1,2}%\s+off\s+with\b",
    )
]

# Deliberately NOT a trigger: "thanks to X for the API credits". That is not
# sponsorship, but it is not independence either. It is flagged and shown
# rather than filtered — see the weighted signals in the deferred register.
_CREDITS_PATTERN = re.compile(
    r"\bthanks to\b.{0,40}\bfor (?:the )?(?:api )?credits\b", re.I
)


@dataclass(frozen=True)
class RejectionVerdict:
    """The outcome of hard rejection for one document."""

    rejected: bool
    trigger: RejectionTrigger | None = None
    detail: str = ""
    flags: tuple[str, ...] = ()
    """Non-fatal observations, shown alongside the document rather than hiding it."""

    @property
    def status(self) -> str:
        return "rejected" if self.rejected else "kept"


def check(
    *,
    text: str,
    links: list[str],
    published_at: date | None,
    model_release_dates: dict[str, date],
    mentioned_models: list[str],
    dedup_cluster_id: str | None = None,
    is_canonical_in_cluster: bool = True,
    canonical_domain: str | None = None,
    own_domain: str | None = None,
) -> RejectionVerdict:
    """Run every hard-rejection rule. First trigger wins.

    Args:
        text: the normalised document text.
        links: every URL found in it.
        published_at: when the document was published (None if only inferred).
        model_release_dates: canonical_id -> release date, from the registry.
        mentioned_models: canonical ids resolved in this document.
        dedup_cluster_id: set if E3 clustered this with other documents.
        is_canonical_in_cluster: False means this is an amplification.
        canonical_domain / own_domain: used to confirm cross-domain syndication.
    """
    flags: list[str] = []

    if _CREDITS_PATTERN.search(text):
        flags.append("free_api_credits_acknowledged")

    # 1 — affiliate or referral link to a provider
    for url in links:
        if _is_tracked_provider_link(url):
            return RejectionVerdict(
                True,
                RejectionTrigger.AFFILIATE_LINK,
                f"tracked link to a model provider: {url}",
                tuple(flags),
            )

    # 2 — sponsored disclosure
    for pattern in _SPONSORED_PATTERNS:
        if m := pattern.search(text):
            return RejectionVerdict(
                True,
                RejectionTrigger.SPONSORED_DISCLOSURE,
                f"matched {m.group(0)!r}",
                tuple(flags),
            )

    # 3 — discount code
    for pattern in _DISCOUNT_PATTERNS:
        if m := pattern.search(text):
            return RejectionVerdict(
                True,
                RejectionTrigger.DISCOUNT_CODE,
                f"matched {m.group(0)!r}",
                tuple(flags),
            )

    # 4 — syndicated reprint. Only rejected when the original lives on a
    #     DIFFERENT domain: a site reposting its own article is one voice
    #     either way, but two domains would otherwise look like two sources.
    if (
        dedup_cluster_id
        and not is_canonical_in_cluster
        and canonical_domain
        and own_domain
        and canonical_domain != own_domain
    ):
        return RejectionVerdict(
            True,
            RejectionTrigger.SYNDICATED_DUPLICATE,
            f"reprint of content first published on {canonical_domain}",
            tuple(flags),
        )

    # 5 — claim predates the model. Only fires on a KNOWN publication date;
    #     an inferred date is not solid enough to reject on.
    if published_at is not None:
        for model_id in mentioned_models:
            released = model_release_dates.get(model_id)
            if released and published_at < released:
                return RejectionVerdict(
                    True,
                    RejectionTrigger.PREDATES_MODEL,
                    f"published {published_at.isoformat()} but {model_id} "
                    f"was released {released.isoformat()}",
                    tuple(flags),
                )

    return RejectionVerdict(False, flags=tuple(flags))


def _is_tracked_provider_link(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    host = (parsed.hostname or "").lower().removeprefix("www.")
    if not any(host == d or host.endswith("." + d) for d in _PROVIDER_DOMAINS):
        return False

    params = {k.lower() for k in parse_qs(parsed.query)}
    return bool(params & _TRACKING_PARAMS)
