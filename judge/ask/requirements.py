"""Q3 — what does this role actually need?

Deterministic rules. The language model in Q1 turns free text into a structured
profile; from here on it is ordinary code, so the reasoning is auditable and the
same task always produces the same requirements.

Two things set how strong the evidence must be:

  (a) COMPLEXITY TIER, derived from the task's structure — not from how hard it
      sounds.

  (b) FAILURE MODE — and this matters MORE than difficulty. Loud failures error
      in seconds and a validation retry is a real mitigation. Silent failures
      put wrong data into your system looking correct, where it stays.

      This is why the advisor will happily move a strict-JSON role to a cheap
      model and refuse on an equally simple summariser. Not difficulty —
      whether you would find out.

And the rule people forget: EVERY REQUIREMENT YOU CAN HONESTLY DROP WIDENS THE
CHEAP END OF THE FIELD. Carrying a context requirement you do not have is the
most common way to overpay, so dropped constraints are named out loud.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from judge.ask.profile import (
    Assumption,
    CapabilityNeed,
    ErrorCost,
    HardConstraints,
    RoleRequirement,
)
from judge.config import bucket_for, capabilities

# ── verb and phrase triggers ─────────────────────────────────────────────
# Each entry: regex -> the capabilities it raises. Order does not matter;
# every match contributes.


@dataclass(frozen=True)
class Trigger:
    pattern: re.Pattern[str]
    capabilities: tuple[str, ...]
    note: str = ""


TRIGGERS: tuple[Trigger, ...] = (
    Trigger(
        re.compile(r"\b(summari[sz]\w*|condense|digest|tl;?dr|recap)\b", re.I),
        ("summarization.fidelity",),
    ),
    Trigger(
        re.compile(r"\b(extract\w*|parse|populate|pull out|scrape into|structure)\b", re.I),
        ("extraction.faithfulness", "instruction.adherence"),
    ),
    Trigger(
        re.compile(r"\b(classif\w*|categori[sz]\w*|route|label|tag|triage)\b", re.I),
        ("instruction.adherence",),
        note="the cheapest role there is — only instruction following is gated",
    ),
    Trigger(
        # The bare noun "tool" is NOT a trigger. "an internal tool" describes
        # the product, not a role that calls anything — and gating on tool
        # calling there would exclude models over a requirement the task does
        # not have, which is the exact overpayment the dropped-constraints rule
        # exists to prevent. So: only tool-CALLING contexts count.
        re.compile(
            r"\b(?:\d+\s+tools?"
            r"|tools?[- ]?(?:call\w*|us\w*|chain\w*)"
            r"|(?:call|invoke|use)s?\s+(?:a\s+|the\s+)?tools?"
            r"|function[- ]?call\w*"
            r"|calls?\s+the\s+api"
            r"|look[- ]?ups?"
            r"|quer(?:y|ies)\s+the)\b",
            re.I,
        ),
        ("tool_calling.schema_accuracy",),
    ),
    Trigger(
        re.compile(r"\b(edit|refactor|patch|modify|apply a? ?diff|fix the file)\b", re.I),
        ("code.editing_diff_fidelity",),
        note="code EDITING, not generation — cheap models write fine code and "
        "cannot emit a clean diff",
    ),
    Trigger(
        re.compile(r"\b(generate|write) (?:the )?code\b|\bwrite a (?:script|function)\b", re.I),
        ("code.generation",),
    ),
    Trigger(
        re.compile(r"\b(plan|orchestrat\w*|decide|coordinate|decompose|break down)\b", re.I),
        ("reasoning.multistep",),
    ),
    Trigger(
        re.compile(
            r"\b(reads? the whole|entire (?:document|codebase|repo|transcript)"
            r"|long document|full context)\b",
            re.I,
        ),
        ("context.effective_window",),
    ),
    Trigger(
        re.compile(r"\b(json|schema|structured output|valid (?:json|xml|yaml))\b", re.I),
        ("format.structured_output", "instruction.adherence"),
    ),
    Trigger(
        re.compile(r"\b(image|screenshot|photo|diagram|chart|pdf page|vision|ocr)\b", re.I),
        (),
        note="raises the vision hard constraint rather than a capability",
    ),
)

_VISION = re.compile(r"\b(image|screenshot|photo|diagram|chart|pdf page|vision|ocr)\b", re.I)
_TOOL_COUNT = re.compile(r"\b(\d{1,3})\s+(?:tools?|functions?)\b", re.I)
_REALTIME = re.compile(r"\b(real[- ]?time|interactive|while the user waits|chat|live)\b", re.I)
_BATCH = re.compile(r"\b(batch|nightly|offline|overnight|scheduled|cron)\b", re.I)

# ── error cost ───────────────────────────────────────────────────────────
# Derived from CONSEQUENCE OF ERROR, not from how important the task sounds.

_ERROR_COST_RULES: tuple[tuple[re.Pattern[str], ErrorCost, str], ...] = (
    (
        re.compile(
            r"\b(writes? to|updates? the (?:database|record)|sends? (?:the )?(?:email|message)"
            r"|places? (?:the )?order|charges?|pays?|deletes?|refunds?|posts? to)\b",
            re.I,
        ),
        "irreversible",
        "the task triggers a write, send, payment or deletion",
    ),
    (
        re.compile(
            r"\b(customer[- ]facing|sent to (?:users|customers)|published|shown to the user"
            r"|user[- ]facing|public)\b",
            re.I,
        ),
        "customer-facing",
        "output is seen by someone outside the org",
    ),
    (
        re.compile(
            r"\b(prototype|experiment\w*|proof of concept|draft|a human (?:reviews|checks))\b",
            re.I,
        ),
        "experimental",
        "a human reviews the output before it is used",
    ),
)

# ── complexity tier signals ──────────────────────────────────────────────

_OPEN_ENDED = re.compile(r"\b(write|draft|compose|essay|article|report|narrative)\b", re.I)
_FIXED_LABELS = re.compile(r"\b(classif\w*|label|tag|categori[sz]\w*|yes/no|boolean)\b", re.I)
_MULTI_HOP = re.compile(r"\b(multi[- ]step|chain|then|after that|plan|orchestrat\w*)\b", re.I)
_LONG_SESSION = re.compile(r"\b(conversation|multi[- ]turn|\d{2,}\s+turns?|session)\b", re.I)
_TASTE = re.compile(r"\b(tone|voice|style|nuance|judgement|judgment|tact|persuasi\w*)\b", re.I)
_SPECIALIST = re.compile(r"\b(legal|medical|clinical|financial|regulatory|compliance|tax)\b", re.I)


def infer(
    text: str,
    *,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    tool_count: int | None = None,
    regions: list[str] | None = None,
    structured_mode: bool | None = None,
) -> RoleRequirement:
    """Turn one role's description into a checkable requirement.

    Everything not stated is guessed, and every guess is returned as an
    Assumption so the interface can render it editable.
    """
    assumptions: list[Assumption] = []
    triggered: dict[str, str] = {}

    for trigger in TRIGGERS:
        if match := trigger.pattern.search(text):
            for cap in trigger.capabilities:
                triggered.setdefault(cap, match.group(0))

    # Tool count, if the user stated one, otherwise inferred from the mention.
    if tool_count is None and (m := _TOOL_COUNT.search(text)):
        tool_count = int(m.group(1))
        assumptions.append(
            Assumption(
                field="tool_count", value=tool_count, why=f"read from {m.group(0)!r}"
            )
        )
    needs_tools = bool(tool_count) or "tool_calling.schema_accuracy" in triggered

    # A long chain is a different capability from a single correct call.
    if needs_tools and (tool_count or 0) >= 6:
        triggered.setdefault(
            "tool_calling.long_chain_reliability", f"{tool_count} tools"
        )

    needs_structured = "format.structured_output" in triggered
    needs_vision = bool(_VISION.search(text))

    if input_tokens is None:
        input_tokens = 20_000
        assumptions.append(
            Assumption(
                field="input_tokens",
                value=input_tokens,
                why="not stated; assumed a typical medium document",
            )
        )
    if output_tokens is None:
        output_tokens = 1_000
        assumptions.append(
            Assumption(
                field="output_tokens", value=output_tokens, why="not stated; assumed short"
            )
        )

    latency_matters = bool(_REALTIME.search(text))
    cost_dominates = bool(_BATCH.search(text)) or not latency_matters

    error_cost, why = _error_cost(text)
    if why:
        assumptions.append(Assumption(field="error_cost", value=error_cost, why=why))

    hard = HardConstraints(
        needs_tools=needs_tools,
        tool_count=tool_count,
        needs_structured_output=needs_structured,
        needs_vision=needs_vision,
        min_context_tokens=_min_context(input_tokens, output_tokens),
        max_latency_ms=2_000 if latency_matters else None,
        regions=regions or [],
    )

    conditions_seen = {
        "tool_count": tool_count,
        "context_size": input_tokens,
        "structured_mode": structured_mode if structured_mode is not None else needs_structured,
    }

    known = capabilities()
    needs = [
        CapabilityNeed(
            key=key,
            triggered_by=phrase,
            failure_mode=known[key].failure_mode,
            condition_bucket=bucket_for(key, conditions_seen),
        )
        for key, phrase in sorted(triggered.items())
        if key in known
    ]

    return RoleRequirement(
        capabilities=needs,
        hard=hard,
        complexity_tier=complexity_tier(
            text, input_tokens=input_tokens, output_tokens=output_tokens, tool_count=tool_count
        ),
        error_cost=error_cost,
        cost_dominates=cost_dominates,
        dropped_constraints=_dropped(hard, latency_matters=latency_matters),
        assumptions=assumptions,
    )


def _error_cost(text: str) -> tuple[ErrorCost, str]:
    for pattern, cost, why in _ERROR_COST_RULES:
        if pattern.search(text):
            return cost, why
    return "internal", "not stated; assumed an internal tool where errors get noticed"


def _min_context(input_tokens: int, output_tokens: int) -> int:
    """Input + output + 30% headroom.

    Matched against REPORTED effective context, never the advertised window.
    Advertised figures overstate usable ones — often several-fold — and
    filtering on them recommends models that will fail at the user's real size.
    """
    return int((input_tokens + output_tokens) * 1.3)


def _dropped(hard: HardConstraints, *, latency_matters: bool) -> list[str]:
    """Name the requirements this task does NOT have.

    Each one widens the field at the cheap end. Small-context models are
    usually the cheapest available, and a task at 20k tokens has no business
    excluding them.
    """
    dropped: list[str] = []

    if hard.min_context_tokens and hard.min_context_tokens < 32_000:
        dropped.append(
            f"long context — this task needs ~{hard.min_context_tokens:,} tokens, "
            "which every candidate handles, so it is not a differentiator"
        )
    if not hard.needs_tools:
        dropped.append("tool calling — this role calls nothing")
    if not latency_matters:
        dropped.append("latency — this is not interactive, so cost dominates")
    if not hard.needs_vision:
        dropped.append("vision — text only")

    return dropped


def complexity_tier(
    text: str,
    *,
    input_tokens: int,
    output_tokens: int,
    tool_count: int | None,
) -> int:
    """1–5, derived from task STRUCTURE rather than from how hard it sounds.

    tier 1  almost anything qualifies; collapse quality, sort by price
    tier 2  many cheap models qualify
    tier 3  mid-tier and up
    tier 4  few models; cost is secondary
    tier 5  1–3 models, or "nothing does this reliably yet"
    """
    score = 0

    score += -1 if _FIXED_LABELS.search(text) else 1 if _OPEN_ENDED.search(text) else 0
    score += -1 if output_tokens < 50 else 1 if output_tokens > 1_000 else 0
    score += -1 if input_tokens < 2_000 else 1 if input_tokens > 100_000 else 0
    score += 1 if _MULTI_HOP.search(text) else 0
    score += 1 if (tool_count or 0) >= 6 else 0
    score += 1 if _LONG_SESSION.search(text) else 0
    score += 1 if _TASTE.search(text) else 0
    score += 1 if _SPECIALIST.search(text) else 0

    return max(1, min(5, 2 + score))
