"""PROPOSAL 2026-10-14: every capability leaf -> keep under a parent, merge into a
target, or decline. One reader's judgement over names + definitions; a person
approves before anything is ruled (CLAUDE.md rule 10: a fold of meaning belongs
to a person through `ruling`).

CLUSTERS: target -> (parent, [slugs merged into it]). The target is kept.
          Ten members come from the map reviewed on #410 and are not in the
          local database this was read from (vulnerability-exploitation,
          proof-of-concept-generation, multi-host-red-team, letter-counting,
          over-thinking, public-figure-identification, speech-to-text,
          multi-turn-dialogue, editorial-craft, deceptive-behavior): they are
          filed so the map keeps them, and a ruling on them changes no row
          where they have none.
DECLINE:  slug -> reason. Rows are kept and ruled `declined` (nothing deleted).
"""

from pathlib import Path

PARENTS = {
    "software-engineering": "Coding and security",
    "agentic": "Agents and tool use",
    "reasoning-and-math": "Reasoning, knowledge and accuracy",
    "instruction-and-reliability": "Instruction following and reliability",
    "writing-language": "Writing, tone and language",
    "vision-media": "Vision, images and media",
    "long-context-and-memory": "Long context, documents and memory",
    "safety-and-honesty": "Safety, refusals and honesty",
    "performance-cost": "Speed, cost and efficiency",
    "api-behaviour": "API and platform behaviour",
}

SE, AG, RE, IR, WR, VI, LC, SA, PC, API = PARENTS

CLUSTERS = {
    # ── Coding and security ────────────────────────────────────────────────
    "code-generation": (
        SE,
        [
            "code-implementation",
            "single-shot-code-generation",
            "math-code-generation",
            "game-code-generation",
            "strategy-implementation",
            "plumbing-implementation",
            "nnue-implementation",
            "gui-application-generation",
            "programming",
            "one-shot-generation",
        ],
    ),
    "coding": (SE, ["coding-evaluation", "complex-coding", "software-engineering-benchmarks"]),
    "code-quality": (
        SE,
        [
            "coding-quality",
            "coding-reliability",
            "comparative-coding-quality",
            "concurrency-awareness",
            "data-loading-efficiency",
            "current-api-following",
            "knowledge-vs-generation",
            "code-pattern-reproduction",
            "code-convention-adherence",
            "code-completeness",
            "conflict-handling",
        ],
    ),
    "code-review": (
        SE,
        [
            "code-audit",
            "review-accuracy",
            "cross-agent-critique",
            "design-review",
            "n-plus-one-detection",
            "issue-prioritization",
            "adversarial-review",
        ],
    ),
    "bug-detection": (SE, ["bug-finding", "wrong-reason", "memorisation-gap"]),
    "false-positive-control": (SE, ["falsification", "problem-invention", "false-alarm-rate"]),
    "debugging": (
        SE,
        [
            "bug-fixing",
            "code-fixing",
            "fixing-broken-projects",
            "build-troubleshooting",
            "gui-component-repair",
            "cross-layer-awareness",
        ],
    ),
    "large-scale-refactoring": (SE, ["long-refactors"]),
    "surgical-fixes": (SE, ["targeted-editing", "code-editing-diff-fidelity"]),
    "regression-avoidance": (SE, ["code-regression"]),
    "repository-level-coding": (
        SE,
        [
            "repository-level-editing",
            "code-navigation",
            "enterprise-code-resolution",
            "integration",
            "investigation-depth",
            "investigation-breadth",
        ],
    ),
    "software-architecture": (SE, ["architectural-reasoning"]),
    "planning": (
        SE,
        ["design-planning", "code-happiness", "stating-the-problem", "execution-vs-planning"],
    ),
    "test-generation": (SE, []),
    "performance-optimization": (SE, ["optimization", "code-optimization"]),
    "sql-generation": (SE, []),
    "code-translation": (SE, []),
    "assembly-reading": (SE, []),
    "haskell-knowledge": (SE, ["template-haskell"]),
    "java-knowledge": (SE, []),
    "commit-message-generation": (SE, []),
    "chip-design": (SE, ["schematic-building", "schematic-editing", "flow-orchestration"]),
    "gpu-compiler-writing": (SE, []),
    "web-design": (
        SE,
        [
            "frontend",
            "frontend-code-generation",
            "ui-generation",
            "ui-rendering",
            "frontend-motion-design",
            "ui-design",
        ],
    ),
    "overcomplication": (SE, ["overengineering-restraint"]),
    "api-discovery": (SE, ["self-directed-learning"]),
    "no-code-generation": (SE, []),
    "development-speed": (SE, []),
    "cybersecurity": (
        SE,
        [
            "cyber-capability",
            "offensive-security",
            "cybersecurity-reasoning",
            "cyber-defense",
            "penetration-testing",
            "long-horizon-cyber",
            "multi-host-red-team",
        ],
    ),
    "exploit-development": (
        SE,
        [
            "cyber-exploit-development",
            "cyber-exploitation",
            "exploit-chaining",
            "exploit-reasoning",
            "exploitation",
            "autonomous-exploit-generation",
            "smart-contract-exploitation",
            "exploit-verification",
            "vulnerability-exploitation",
            "proof-of-concept-generation",
        ],
    ),
    "vulnerability-discovery": (SE, []),
    "vulnerability-detection": (SE, ["security-auditing", "security-bug-finding"]),
    "automated-patching": (SE, ["security-patching"]),
    "internet-connected-code-execution": (SE, []),
    # ── Agents and tool use ────────────────────────────────────────────────
    "agentic-tool-use": (
        AG,
        [
            "agentic-capabilities",
            "agentic-performance",
            "agentic-workload-performance",
            "agentic-real-world-tasks",
            "autonomous-agent",
            "multi-step-execution",
            "task-automation",
            "tool-use",
            "tool-calling-decision-quality",
            "tool-calling-recognition",
            "tool-selection-accuracy",
            "routing",
            "long-tool-chains",
        ],
    ),
    "function-calling": (AG, ["tool-calling"]),
    "agentic-coding": (
        AG,
        [
            "coding-agent",
            "agentic-code-generation",
            "terminal-coding",
            "coding-autonomous-planning",
            "agent-development",
            "voice-driven-development",
            "agentic-workflow",
        ],
    ),
    "computer-use": (AG, ["agentic-saas"]),
    "physical-task-execution": (AG, ["real-world-driving", "continuous-balance"]),
    "long-horizon-tasks": (
        AG,
        [
            "long-running-tasks",
            "long-unattended-work",
            "long-horizon-construction",
            "autonomous-execution",
            "autonomous-task-completion",
            "restart-resume",
            "long-horizon-reasoning",
        ],
    ),
    "orchestration": (
        AG,
        ["subagent-orchestration", "long-running-orchestration", "subagent-polling"],
    ),
    "task-completion": (AG, ["agentic-testing"]),
    "task-persistence": (
        AG,
        ["persistence", "persistent-reasoning", "crash-handling", "agentic-behaviour"],
    ),
    "premature-completion": (AG, ["accepting-local-evidence", "lazy-convergence"]),
    "self-verification": (
        AG,
        ["verification", "empirical-auditing", "independent-audit", "self-audit", "step-audit"],
    ),
    "self-correction": (AG, ["local-surgery"]),
    "scope-adherence": (AG, ["goal-alignment"]),
    "judgment": (AG, ["cautiousness", "asking-clarifications"]),
    "initiative": (AG, ["creative-autonomy", "curiosity", "exploration", "open-ended-exploration"]),
    "search": (AG, ["web-search", "retrieval", "scientific-agentic-search"]),
    "triage": (AG, []),
    # ── Reasoning, knowledge and accuracy ──────────────────────────────────
    "reasoning": (
        RE,
        [
            "complex-understanding",
            "complex-problem-solving",
            "critical-thinking",
            "inference-quality",
            "difficult-tasks",
            "hard-task-performance",
            "automatic-deduction",
            "problem-solving-efficiency",
            "creative-problem-solving",
            "nuance",
            "common-sense",
            "cipher-solving",
            "prediction-accuracy",
            "letter-counting",
        ],
    ),
    "no-cot-reasoning": (RE, ["latent-reasoning"]),
    "quality": (
        RE,
        [
            "overall-quality",
            "overall-capability",
            "overall-performance",
            "general-capability",
            "general-performance",
            "performance",
            "performance-quality",
            "capability",
            "answer-quality",
            "response-quality",
            "generation-quality",
            "real-world-quality",
            "real-world-usability",
            "usability",
            "functional-accuracy",
            "superficial-flash",
            "day-to-day-improvement",
            "frontier",
            "opus-class-performance",
            "intelligence",
            "for-needs",
            "sufficient-for-light-tasks",
            "sufficient-for-most-needs",
            "weird-scenarios",
            "open-weight-performance",
            "first-attempt-accuracy",
            "one-shot-accuracy",
        ],
    ),
    "comparative-quality": (
        RE,
        [
            "comparison",
            "general-capability-parity",
            "close-to-opus-4-8",
            "sonnet-5-quality",
            "retention",
        ],
    ),
    "benchmark-performance": (
        RE,
        ["benchmark-ranking", "scientific-reasoning", "pass-rate", "pass-at-k", "correctness"],
    ),
    "mathematical-reasoning": (RE, ["mathematical-verification"]),
    "proof-writing": (RE, ["proof-generation"]),
    "serial-arithmetic": (RE, []),
    "spatial-reasoning": (RE, ["spatial-index-bias"]),
    "temporal-reasoning": (RE, ["timezone-reasoning", "time-awareness", "stale-fact-detection"]),
    "world-knowledge": (
        RE,
        [
            "factual-recall",
            "medical-knowledge",
            "earnings-memory",
            "knowledge-of-standard-status",
            "accuracy-on-real-standards",
            "incident-recognition",
            "german-domain-terminology",
            "compliance",
            "physical-advice",
            "local-recommendations",
            "current-events-knowledge",
            "carb-overestimation-bias",
        ],
    ),
    "hallucination": (
        RE,
        [
            "hallucination-rate",
            "hallucination-in-apis",
            "factuality",
            "factual-accuracy",
            "factual-reliability",
            "fact-consistency",
            "mistake-rate",
            "confabulation-reduction",
            "accuracy",
        ],
    ),
    "abstention": (
        RE,
        [
            "abstention-on-unanswerable",
            "knowing-when-to-say-no",
            "overconfidence-on-unsolvable-items",
        ],
    ),
    "judging-accuracy": (
        RE,
        [
            "ai-grading",
            "judgment-call-recognition",
            "open-ended-judgment",
            "open-ended-judgment-drop",
            "claim-verification",
        ],
    ),
    "classification": (
        RE,
        ["tag-accuracy", "prompt-classification", "syntactic-classification", "lead-scoring"],
    ),
    "game-play": (
        RE,
        [
            "chess-play",
            "gameplay-behaviour",
            "strategy",
            "game-economy-management",
            "discovery-in-games",
            "agentic-game-play",
            "adversarial-resilience",
        ],
    ),
    "scientific-discovery": (
        RE,
        [
            "agentic-discovery",
            "automated-lab-work",
            "scientific-replication",
            "autonomous-problem-selection",
            "research-idea-generation",
            "automated-ai-rd",
        ],
    ),
    "research-taste": (RE, ["experimental-research-taste"]),
    "research": (RE, ["complex-research", "market-research-analysis", "agentic-knowledge-work"]),
    "learning-from-examples": (
        RE,
        [
            "teaching-efficiency",
            "reading-efficiency",
            "note-conciseness",
            "self-consistency-in-note-writing",
        ],
    ),
    "cot-controllability": (RE, []),
    # ── Instruction following and reliability ──────────────────────────────
    "instruction-following": (
        IR,
        [
            "requirement-following",
            "business-rule-following",
            "task-adherence",
            "constraint-adherence",
            "multi-task-handling",
            "policy-application",
            "default-substitution",
            "dog-petting",
            "controllability",
        ],
    ),
    "structured-output": (IR, ["format-compliance", "output-completeness"]),
    "context-awareness": (
        IR,
        ["contextual-awareness", "task-inference", "vague-prompt-following", "context-sensitivity"],
    ),
    "consistency": (
        IR,
        [
            "output-consistency",
            "paraphrase-stability",
            "within-image-reproducibility",
            "bit-reproducibility",
            "token-predictability",
            "cross-harness-consistency",
            "precision",
            "batch-processing",
        ],
    ),
    "reliability": (IR, ["production-reliability", "stability-reliability"]),
    "model-drift": (IR, ["performance-over-time", "median-thinking", "harness-regression"]),
    "empty-response": (IR, ["empty-responses", "response-emptiness", "response-completeness"]),
    "thinking-stalling": (
        IR,
        ["thinking-loops", "retry-loop", "convergence", "loop-until-dry", "thinking-effort-bug"],
    ),
    "overthinking": (IR, ["reasoning-verbosity", "reasoning-focus", "over-thinking"]),
    "citation-accuracy": (IR, ["evidence-quality", "evidence-recording"]),
    # ── Writing, tone and language ─────────────────────────────────────────
    "communication-clarity": (
        WR,
        [
            "output-clarity",
            "explainability",
            "jargon-reduction",
            "goal-oriented-output",
            "language-output",
        ],
    ),
    "writing-quality": (
        WR,
        [
            "writing",
            "language-quality",
            "natural-language",
            "human-like-writing",
            "authenticity",
            "spelling-accuracy",
            "output-quality",
            "claudelish",
            "editorial-craft",
        ],
    ),
    "writing-style": (WR, ["verbal-style"]),
    "style-mimicry": (WR, ["voice-matching", "writing-style-adaptation"]),
    "communication-style": (
        WR,
        [
            "tone",
            "tone-and-style",
            "persona-warmth",
            "warmth-and-listening",
            "sarcasm",
            "crudeness",
            "hedging",
        ],
    ),
    "conversational-quality": (
        WR,
        [
            "chat-quality",
            "enjoyability",
            "personality",
            "voice-personality",
            "text-chat",
            "assistant-behavior",
            "customer-service",
            "multi-turn-dialogue",
        ],
    ),
    "persona-contrarian": (WR, ["contrarian-behavior", "condescending-tone"]),
    "creative-writing": (
        WR,
        [
            "creativity",
            "story-writing",
            "creative-output",
            "creative-process-support",
            "narrative-coherence",
            "narrative-balance",
            "plot-direction",
            "interiority",
            "over-explaining",
        ],
    ),
    "dialogue": (WR, ["dialogue-quality"]),
    "emotional-intelligence": (WR, ["theory-of-mind"]),
    "roleplay-consistency": (
        WR,
        [
            "roleplay",
            "roleplay-quality",
            "roleplay-writing",
            "roleplaying",
            "character-consistency",
        ],
    ),
    "verbosity": (WR, ["output-verbosity", "conciseness"]),
    "repetitive-output": (WR, ["repetition-loops", "output-pattern-detection", "style-diversity"]),
    "chinese-language": (WR, ["chinese-language-output", "chinese-quality"]),
    "multilingual": (
        WR,
        [
            "multi-lingual-quality",
            "multilingual-translation",
            "english-language",
            "english-quality",
        ],
    ),
    "summarization": (WR, ["detail-retention", "surface-summarization"]),
    "email-writing": (WR, ["outreach-drafting"]),
    "document-generation": (
        WR,
        ["technical-writing", "setup-guidance", "information-architecture"],
    ),
    "long-form-consistency": (WR, []),
    # ── Vision, images and media ───────────────────────────────────────────
    "vision": (
        VI,
        ["intuitive-visual-reasoning", "content-analysis", "public-figure-identification"],
    ),
    "ocr": (VI, []),
    "multimodal": (VI, ["modalities"]),
    "image-generation": (VI, ["image-quality", "image-detail", "image-design", "visual-quality"]),
    "image-editing": (VI, ["style-transfer"]),
    "text-in-image": (VI, []),
    "visual-design": (
        VI,
        [
            "design-quality",
            "copy-fidelity",
            "color-fidelity",
            "typeface-fidelity",
            "layout-consistency",
        ],
    ),
    "3d-modeling": (VI, ["3d-generation", "3d-rendering", "3d-topology", "scene-control"]),
    "svg-generation": (
        VI,
        ["svg-quality", "svg-animation-generation", "visual-coherence", "pixel-art-animation"],
    ),
    "text-to-video": (VI, ["motion-design", "animation-quality"]),
    "video-editing": (VI, []),
    "text-to-speech": (
        VI,
        ["text-to-speech-japanese", "custom-voice", "multi-character-conversation"],
    ),
    "audio-understanding": (VI, ["speech-to-text"]),
    "music-generation": (VI, []),
    # ── Long context, documents and memory ─────────────────────────────────
    "long-context": (LC, ["long-context-recall", "context-handling", "big-messy-context"]),
    "context-window": (LC, []),
    "coherence": (
        LC,
        [
            "durability",
            "long-session-consistency",
            "context-retention",
            "context-continuity",
            "voice-chat-context",
        ],
    ),
    "compaction": (LC, ["compaction-loss"]),
    "memory-recall": (LC, ["memory-quality"]),
    "document-reasoning": (
        LC,
        [
            "long-document-understanding",
            "investigation",
            "information-reconciliation",
            "synthesis",
            "incident-analysis",
        ],
    ),
    "sentence-extraction": (LC, ["term-extraction", "tokenization", "reading-from-html"]),
    # ── Safety, refusals and honesty ───────────────────────────────────────
    "censorship": (
        SA,
        [
            "censorship-transfer",
            "content-filtering",
            "safety-filters",
            "safety-restrictions",
            "uncensored-output",
            "uncensored-writing",
            "moderation",
            "drug-content",
        ],
    ),
    "over-refusal": (
        SA,
        [
            "safety-guardrails",
            "safety-filtering",
            "security-filters",
            "refusals",
            "refusal",
            "refusal-behavior",
            "biology-classification",
            "biology-discussion",
            "purpose-based-refusal",
            "security-refusal",
            "security-pauses",
            "refusal-configuration",
            "safety-seeking",
        ],
    ),
    "nsfw-content": (SA, ["nsfw", "nsfw-moderation"]),
    "safety": (
        SA,
        [
            "safety-alignment",
            "alignment-safety",
            "safety-call",
            "analysis-bias",
            "obligation-identification",
        ],
    ),
    "jailbreak-resistance": (SA, ["jailbreak-susceptibility"]),
    "injection-resistance": (
        SA,
        [
            "prompt-injection-defense",
            "prompt-injection-resistance",
            "prompt-injection-robustness",
            "authority-following",
            "reasoning-trace-injection",
        ],
    ),
    "reward-hacking": (SA, ["benchmark-cheating", "benchmark-gaming", "eval-gaming"]),
    "sandbagging": (SA, ["sabotage"]),
    "chain-of-thought-monitorability": (
        SA,
        ["chain-of-thought-monitoring", "reasoning-trace-security"],
    ),
    "situational-awareness": (SA, ["self-awareness", "self-identification"]),
    "sycophancy": (
        SA,
        [
            "pressure-susceptibility",
            "pressure-resistance",
            "resistance-to-pushback",
            "reasoning-stability",
            "ego-malleability",
            "honesty-critique",
        ],
    ),
    "honesty": (
        SA,
        [
            "honesty-truthfulness",
            "verification-honesty",
            "verification-degradation",
            "gotcha-question-handling",
            "deceptive-behavior",
        ],
    ),
    "safety-boundary-adherence": (
        SA,
        [
            "bypass-attempts",
            "mislabeling",
            "split-payment",
            "record-tampering",
            "sandbox-compliance",
            "scope-control",
            "agentic-behavior",
        ],
    ),
    # ── Speed, cost and efficiency ─────────────────────────────────────────
    "speed": (
        PC,
        [
            "generation-speed",
            "execution-speed",
            "inference-speed",
            "fast-execution",
            "speed-of-delivery",
            "frames-per-second",
            "host-sensitivity",
        ],
    ),
    "throughput": (PC, ["tokens-per-second", "decode-speed", "output-speed", "moe-decode"]),
    "latency": (PC, ["responsiveness", "task-duration"]),
    "time-to-first-token": (PC, ["time-to-first-response"]),
    "prefill-speed": (PC, ["batched-prefill", "long-context-speed", "long-context-slowness"]),
    "local-inference": (
        PC,
        [
            "local-deployment",
            "local-hardware-compatibility",
            "local-performance",
            "local-inference-speed",
            "resource-requirements",
            "memory-requirement",
            "local-hardware-cost",
        ],
    ),
    "quantization-quality": (PC, ["quantization-fidelity", "precision-accuracy-loss"]),
    "mtp": (PC, ["multi-token-prediction", "speculative-decoding"]),
    "parameter-activation": (PC, []),
    "size-efficiency": (PC, ["per-size"]),
    "cost-efficiency": (
        PC,
        [
            "cost-effectiveness",
            "cost-performance",
            "cost-vs-quality",
            "performance-vs-cost",
            "accuracy-vs-cost",
            "value",
            "economical",
            "competitive-pricing",
            "api-rate-viability",
            "cost-level",
            "relative-cost",
            "older-revision-pricing",
            "cost-control",
        ],
    ),
    "token-efficiency": (
        PC,
        [
            "token-consumption",
            "token-usage",
            "efficiency",
            "task-efficiency",
            "reasoning-efficiency",
            "context-efficiency",
            "consumption-intensity",
            "context-compression",
        ],
    ),
    "usage-limits": (PC, ["usage-quota", "generous-limits", "session-token-burn-rate"]),
    "reasoning-effort": (
        PC,
        [
            "reasoning-effort-auto",
            "adaptive-thinking",
            "reasoning-effort-sensitivity",
            "reasoning-effort-cost-tradeoff",
            "recall-precision-tradeoff",
            "thinking-knob-honesty",
            "non-reasoning-mode",
        ],
    ),
    # ── API and platform behaviour ─────────────────────────────────────────
    "thinking-mode": (
        API,
        [
            "thinking",
            "thinking-mode-locked",
            "thinking-parameter",
            "extended-thinking",
            "visible-chain-of-thought",
            "thinking-block-placement",
            "progress-text",
        ],
    ),
    "reasoning-content-passback": (
        API,
        [
            "reasoning-content-preservation",
            "reasoning-content-roundtrip",
            "reasoning-content-streaming",
            "thinking-transfer",
        ],
    ),
    "parameter-support": (
        API,
        [
            "parameter-compatibility",
            "parameter-forwarding",
            "temperature-control",
            "sampling-parameter-handling",
            "tool-choice",
            "message-role-alternation",
            "computer-use-tool",
        ],
    ),
    "api-compatibility": (
        API,
        [
            "upgrade-compatibility",
            "breaking-changes",
            "api-migration",
            "cli-tool-compatibility",
            "openclaw-compatibility",
            "ease-of-integration",
            "switching-cost",
        ],
    ),
    "availability": (
        API,
        ["free-tier-availability", "shutdown-notice", "shutdown-enforcement", "api-reliability"],
    ),
    "model-version-fidelity": (
        API,
        ["model-downgrade", "silent-rerouting", "model-selection-adherence", "vision-routing"],
    ),
    "prompt-caching": (
        API,
        [
            "prefix-cache",
            "prefix-caching",
            "multi-turn-prefix-cache",
            "input-caching",
            "prompt-cache-floor",
        ],
    ),
    "streaming": (API, []),
    "token-counting": (API, ["token-accounting", "tokenizer"]),
    "license-clarity": (API, []),
    "watermarking": (API, []),
    "fine-tuning": (API, []),
    "system-configuration": (API, ["toolchain-assumption-error"]),
}

#: Not a behaviour of the model: a product feature, a vendor's process, or one
#: test prompt's detail. Rows kept; ruled `declined` so the Board stops listing them.
DECLINE = {
    "coding-instructions-removal": "a setting in one tool's output-style config, not the model",
    "diff-visualization": "a feature of the editor UI, not the model",
    "staged-edits": "a feature of the editor UI, not the model",
    "honesty-in-release-notes": "about the vendor's release notes, not the model",
    "pricing-aggregation": "about how a price listing is compiled, not the model",
    "usage-volume": "how much a model is used in production, not something it can do",
    "post-training": "about how the vendor trained it, not something it does",
    "safety-evaluation": "about the vendor's pre-release evaluation process, not the model",
}


# ── writing it out ───────────────────────────────────────────────────────────


def parent_map() -> dict[str, list[str]]:
    """{parent: [every slug filed under it]} - each kept capability followed by
    the slugs proposed to merge into it. Merged slugs are listed too, so a row
    that has not been ruled yet still groups where its target does."""
    out: dict[str, list[str]] = {p: [] for p in PARENTS}
    for target, (parent, merged) in CLUSTERS.items():
        out[parent] += [target, *merged]
    return out


def write_parents(path: str = "contract/slug_parents.yaml") -> None:
    """Replace the `capability:` block of the contract and nothing else."""
    from pathlib import Path

    p = Path(path)
    text = p.read_text(encoding="utf-8")
    start = text.index("\n  capability:\n") + 1
    end = text.index("\n  metric:\n", start) + 1
    lines = ["  capability:"]
    for parent, slugs in parent_map().items():
        lines.append(f"    {parent}:")
        lines += [f"      - {s}" for s in slugs]
    p.write_text(text[:start] + "\n".join(lines) + "\n" + text[end:], encoding="utf-8")


VOCABULARY_HEADER = """\
# THE CAPABILITY VOCABULARY THE EXTRACTOR IS SHOWN. Generated 2026-10-14 from
# `docs/proposals/capability_curation_2026_10_14.py` (`--write-vocabulary`):
# every capability that proposal KEEPS, under the heading it is filed under in
# `slug_parents.yaml`, with the name the board renders. Names merged into one of
# these are not listed - offering them would invite the duplicates the merge
# removes. Edit the proposal and regenerate; do not edit by hand.
#
# WHAT THIS IS AND IS NOT. It is a REUSE-FIRST list, not a closed one. The
# extractor is told to reuse a listed slug whenever one names what the quote
# reports, and when none does, to name a new capability and file it under one
# of the headings below (`parent`). Code never refuses a new slug: a membership
# check here would be the closed vocabulary `judge/config.py:board_exemplars`
# warns against, which forces a quote into the nearest wrong name.
#
# NO COUNTS (rule 11). How many reports each holds is the board's to compute.
"""


def write_vocabulary(path: str = "contract/board_vocabulary.yaml") -> None:
    """Every KEPT capability with its display name, under its heading.

    The name is the one the board renders today: the commonest `name` among
    the slug's rows. A kept slug with no rows (none today) gets its slug
    title-cased, said so in a comment rather than silently.
    """
    import os

    import psycopg
    import yaml

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        names = dict(conn.execute(
            "SELECT slug, mode() WITHIN GROUP (ORDER BY name) FROM board_entry "
            "WHERE section = 'capability' GROUP BY slug").fetchall())
    body: dict[str, list[dict[str, str]]] = {p: [] for p in PARENTS}
    unnamed = []
    for target, (parent, _merged) in CLUSTERS.items():
        name = names.get(target)
        if not name:
            unnamed.append(target)
            name = target.replace("-", " ").capitalize()
        body[parent].append({"slug": target, "name": name})
    text = VOCABULARY_HEADER
    if unnamed:
        text += f"# Named from the slug, no rows on the database read: {', '.join(unnamed)}\n"
    text += "\n" + yaml.safe_dump({"capability": body}, sort_keys=False, allow_unicode=True)
    Path(path).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    import sys

    if "--write-parents" in sys.argv:
        write_parents()
        print("wrote the capability block of contract/slug_parents.yaml")
    if "--write-vocabulary" in sys.argv:
        write_vocabulary()
        print("wrote contract/board_vocabulary.yaml")
