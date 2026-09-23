"""Reproduces the slug/parent measurements in the parent-map proposal.

`docs/proposals/a-parent-map-for-the-board-sections.md`, 2026-09-23.

READ-ONLY. No write, no model call. Persisted rather than pasted into a
comment because the clustering enters an argument, and a measurement nobody
can re-run is a number nobody can dispute.

WHAT IS A MEASUREMENT HERE AND WHAT IS NOT. The distribution in section 1 and
the mechanical spelling folds in section 2 are measurements: run this and you
get them. `PARENTS` in section 3 is ONE READER'S JUDGEMENT over 292 slugs --
the counts it produces are reproducible, the clustering that produced them is
not. Section 9 of the proposal says so too; it is repeated here because a
script reads as authoritative in a way prose does not.

    .venv/Scripts/python.exe docs/measurements/slug-parent-clustering-2026-09-23.py
"""

from __future__ import annotations

import collections
import os
import re

import psycopg
from dotenv import load_dotenv

SECTIONS = ("capability", "metric", "best_for")

#: Parent -> member leaf slugs. A JUDGEMENT, not a measurement. Leaves absent
#: from every list are UNGROUPED and stay that way -- there is deliberately no
#: residual bucket, because a taxonomy that covers everything has forced
#: something.
PARENTS: dict[str, dict[str, list[str]]] = {
    "capability": {
        "coding": [
            "code-generation", "code-review", "code-quality", "coding",
            "code-fixing", "code-editing-diff-fidelity",
            "frontend-code-generation", "debugging", "test-generation",
            "code-completeness", "code-convention-adherence", "code-regression",
            "repository-level-coding", "repository-level-editing",
            "long-refactors", "surgical-fixes", "sql-generation",
            "ui-generation", "software-architecture", "design-planning",
            "design-review", "adversarial-review", "no-code-generation",
            "api-migration", "automated-patching", "n-plus-one-detection",
            "gpu-compiler-writing", "development-speed",
            "architectural-reasoning",
        ],
        "security": [
            "cybersecurity", "vulnerability-discovery", "vulnerability-detection",
            "vulnerability-exploitation", "exploit-development",
            "autonomous-exploit-generation", "smart-contract-exploitation",
            "jailbreak-resistance", "prompt-injection-resistance",
            "prompt-injection-robustness", "security-refusal", "security-pauses",
            "multi-host-red-team", "long-horizon-cyber", "cyber-capability",
            "proof-of-concept-generation", "reasoning-trace-injection",
            "reasoning-trace-security", "sandbox-compliance",
            "internet-connected-code-execution",
        ],
        "reasoning": [
            "reasoning", "mathematical-reasoning", "spatial-reasoning",
            "long-horizon-reasoning", "persistent-reasoning", "no-cot-reasoning",
            "cot-controllability", "reasoning-effort", "proof-writing",
            "serial-arithmetic", "letter-counting", "over-thinking",
            "overthinking", "overcomplication",
            "chain-of-thought-monitorability", "chain-of-thought-monitoring",
        ],
        "agentic": [
            "agentic-tool-use", "agentic-behavior", "agentic-testing",
            "agentic-workflow", "agentic-game-play", "computer-use",
            "function-calling", "tool-calling", "tool-use", "long-tool-chains",
            "flow-orchestration", "loop-until-dry", "long-unattended-work",
            "premature-completion", "scope-adherence", "routing", "triage",
        ],
        "vision-media": [
            "vision", "multimodal", "image-editing", "image-generation",
            "visual-design", "visual-quality", "visual-coherence",
            "3d-generation", "svg-quality", "text-in-image", "style-transfer",
            "style-diversity", "public-figure-identification",
            "schematic-building", "schematic-editing", "audio-understanding",
            "speech-to-text", "text-to-speech-japanese",
        ],
        "writing-language": [
            "creative-writing", "writing", "writing-quality",
            "uncensored-writing", "communication-clarity", "output-clarity",
            "output-verbosity", "output-completeness", "summarization",
            "dialogue", "multi-turn-dialogue", "condescending-tone",
            "warmth-and-listening", "language-quality", "english-language",
            "english-quality", "chinese-language", "chinese-quality",
            "chinese-language-output", "multilingual", "multi-lingual-quality",
            "long-form-consistency", "detail-retention", "document-generation",
            "editorial-craft",
        ],
        "reliability-safety": [
            "hallucination", "abstention", "citation-accuracy",
            "false-positive-control", "self-verification", "self-audit",
            "independent-audit", "evidence-quality", "consistency",
            "reliability", "production-reliability", "api-reliability",
            "crash-handling", "response-emptiness", "model-drift",
            "model-downgrade", "model-version-fidelity",
            "verification-degradation", "compaction-loss", "sandbagging",
            "reward-hacking", "deceptive-behavior", "sabotage",
            "shutdown-enforcement", "situational-awareness", "self-awareness",
            "alignment-safety", "safety-evaluation", "over-refusal",
            "refusal-configuration", "contrarian-behavior", "analysis-bias",
            "gotcha-question-handling",
        ],
        "performance-cost": [
            "latency", "speed", "execution-speed", "speed-of-delivery",
            "throughput", "streaming", "token-efficiency", "token-counting",
            "tokenizer", "cost-efficiency", "usage-limits", "local-deployment",
            "parameter-support", "parameter-forwarding",
            "sampling-parameter-handling", "toolchain-assumption-error",
            "system-configuration", "one-shot-accuracy", "quality",
            "output-quality", "generation-quality", "judgment",
        ],
    },
    "best_for": {
        "coding": [
            "coding-agent", "code-review", "code-generation", "code-audit",
            "code-porting", "coding-assistants", "multi-file-refactoring",
            "terminal-agent", "programming", "proof-based-programming",
            "compiler-development", "frontend-testing", "ui-prototyping",
            "web-and-mobile-development", "game-development", "sql",
            "sql-generation", "math-heavy-debugging", "prototyping",
            "security-review", "general-purpose-coding-and-content",
        ],
        "agents-automation": [
            "agentic-systems", "agentic-testing", "agentic-tool-use",
            "multi-tool-agents", "browser-control", "computer-use",
            "desktop-automation", "api-usage", "buildroot-system-setup",
            "support-triage", "incident-analysis",
        ],
        "text-knowledge": [
            "classification", "extraction", "rag", "summarization",
            "translation", "document-analysis", "content-rewriting",
            "meeting-summarization", "writing", "creative-writing",
            "roleplaying", "chat", "chatbots", "conversational-ui",
            "general-purpose-chat", "general-purpose", "quick-one-shot-work",
            "instruction-following", "reasoning", "math",
        ],
        "media": [
            "svg-generation", "3d-art", "3d-asset-generation",
            "sprite-generation", "product-photography", "presentation-creation",
            "video-editing", "video-processing", "voice-pipeline", "chinese-ocr",
        ],
        "domain": [
            "biology", "computational-biology", "finance", "tax-preparation",
            "cad-design", "chip-design", "cybersecurity",
            "vulnerability-discovery", "vulnerability-detection",
            "public-figure-identification", "sales-call-prep",
            "chinese-language", "chinese-language-work",
            "multi-lingual-inference", "local-inference",
        ],
    },
    "metric": {
        "price": [
            "cost-per-token", "cost-per-task", "cost-per-character",
            "cost-per-generation", "cost-per-review", "cost-per-run",
            "cost-per-image", "cost-per-million-characters", "cost-per-minute",
            "cost-per-shot", "cost-per-benchmark-point", "cache-read-cost",
            "eval-cost", "token-cost",
        ],
        "speed-latency": [
            "time-to-first-token", "tokens-per-second", "execution-time",
            "completion-time", "time-to-completion", "task-duration",
            "wall-clock-time", "added-latency", "chip-design-time", "fast-mode",
            "time-horizon",
        ],
        "token-usage": [
            "token-usage", "tokens-per-output", "output-tokens",
            "output-token-inflation", "output-size", "token-consumption",
            "tokens-per-task", "token-count-accuracy", "tokenizer-efficiency",
            "turns-per-run",
        ],
        "capacity-spec": [
            "context-window", "licence", "parameters", "usage-quota",
            "aic-usage",
        ],
        "reliability-rate": [
            "failure-rate", "http-error-rate", "error-status-code",
            "regression-rate", "pass-rate", "hallucination-rate",
            "false-positive-rate", "precision", "accuracy", "task-completion",
            "continuous-score", "score", "other",
        ],
        "benchmark": [
            "swe-bench", "swe-bench-pro", "swe-bench-verified", "terminal-bench",
            "terminal-bench-2-1", "osworld", "osworld-2", "osworld-2-0",
            "osworld-verified", "gpqa-diamond", "aime", "aime-2025", "aime-2026",
            "arc-agi", "arc-agi-2", "arc-agi-3", "mmlu-pro", "mmmu", "mmmu-pro",
            "hle-text", "hle-with-tools", "frontiermath", "livecodebench-v6",
            "ifbench", "browsecomp", "simpleqa-verified", "healthbench", "mmau",
            "voicebench", "global-mmlu-lite", "charxiv-rq", "charxiv-rq-python",
            "mrcr-v2", "posttrainbench", "posttrainbench-plus", "exploitbench",
            "exploit-bench", "exploitgym", "exploit-gym", "cybergym",
            "agents-last-exam", "mcp-atlas", "gdpval-aa-v2", "aa-omniscience",
            "tau-3-banking", "dig-bench-tier-7", "fortress-benign",
            "fortress-adversarial", "strongreject",
            "sre-bench-reverse-engineering-tasks", "audio-mc",
            "medical-benchmark", "benchmark-performance", "benchmark-rank",
            "intelligence-index", "artificial-analysis-intelligence-index",
            "agentic-index", "blind-judge-score", "chess-rating", "odds-ratio",
            "compiler-performance", "pretraining-efficiency",
            "pretraining-quality",
        ],
    },
}


def spelling_key(slug: str) -> str:
    """Rule 10's mechanical half: fold separators and nothing else."""
    return re.sub(r"[-_]", "", slug)


def main() -> int:
    load_dotenv()
    dsn = os.environ["DATABASE_URL"]
    with psycopg.connect(dsn, connect_timeout=25) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT section, slug, count(*), count(DISTINCT model_version_id) "
            "FROM board_entry GROUP BY 1, 2"
        )
        rows = cur.fetchall()

    entries = {(sec, slug): n for sec, slug, n, _ in rows}
    models = {(sec, slug): m for sec, slug, _, m in rows}

    print("== 1 - distribution, a measurement ==")
    print(f"{'section':12}{'entries':>9}{'slugs':>7}{'=1':>5}{'1 model':>9}")
    for sec in SECTIONS:
        mine = {s: n for (x, s), n in entries.items() if x == sec}
        one_model = sum(1 for s in mine if models[(sec, s)] == 1)
        print(
            f"{sec:12}{sum(mine.values()):>9}{len(mine):>7}"
            f"{sum(1 for n in mine.values() if n == 1):>5}{one_model:>9}"
        )

    print("\n== 2 - mechanical spelling folds, a measurement (rule 10) ==")
    folds = collections.defaultdict(list)
    for (sec, slug), n in entries.items():
        folds[(sec, spelling_key(slug))].append((slug, n))
    found = 0
    for (sec, _), members in sorted(folds.items()):
        if len(members) > 1:
            found += 1
            joined = " + ".join(f"{s}({n})" for s, n in sorted(members))
            print(f"  {sec:11} {joined}")
    print(f"  {found} collision(s) across the whole board")

    print("\n== 3 - proposed parents, A JUDGEMENT (see module docstring) ==")
    for sec in SECTIONS:
        mine = {s: n for (x, s), n in entries.items() if x == sec}
        groups = PARENTS.get(sec, {})
        claimed: set[str] = set()
        print(f"\n-- {sec}: {len(mine)} slugs / {sum(mine.values())} entries --")
        print(f"  {'parent':20}{'slugs':>7}{'entries':>9}{'singletons':>12}")
        for parent, members in groups.items():
            present = [m for m in members if m in mine]
            claimed.update(present)
            print(
                f"  {parent:20}{len(present):>7}{sum(mine[m] for m in present):>9}"
                f"{sum(1 for m in present if mine[m] == 1):>12}"
            )
        rest = sorted(s for s in mine if s not in claimed)
        print(
            f"  {'(ungrouped)':20}{len(rest):>7}{sum(mine[s] for s in rest):>9}"
            f"{sum(1 for s in rest if mine[s] == 1):>12}"
        )
        if rest:
            print(f"  ungrouped, and staying that way: {', '.join(rest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
