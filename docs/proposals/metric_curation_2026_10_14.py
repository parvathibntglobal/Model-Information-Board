"""PROPOSAL 2026-10-14: every METRIC leaf -> keep under a heading, merge into a
kept axis, or decline. One reader's judgement; a person approves before anything
is ruled (rule 10).

MERGES ARE DELIBERATELY FEW, AND THE REASON IS RULE 10. A benchmark name and a
longer one (`aime` / `aime-2026`, `terminal-bench` / `terminal-bench-2-1`) are
the SAME only when the shorter row's own quote names the longer one - a per-row
question this file cannot answer by reading slugs, so NO benchmark version is
merged here. What is merged:

  - two wordings of one quantity in ONE unit: `api-price-input`, `input-price`
    and `cost-per-million-input-tokens` are all USD per 1M input tokens, which
    `cost-per-token` already records with input and output kept apart;
  - one benchmark under two spellings of its NAME - HLE is Humanity's Last
    Exam, AA is Artificial Analysis - never under two versions or settings.

A percentage and a dollar price never share an axis, even where the words agree
(`cache-read-cost` is a percent of the input price; `cache-input-price` is USD).

HEADINGS: the map reviewed on #410 where it covers a slug, else the keyword
rules below, else UNFILED (shown as not yet under a heading). `HEADING` is
generated - run with `--write-headings` - and is there to be corrected by hand.
"""

SECTION = "metric"

PARENTS = {
    "price": "Price and cost",
    "speed-latency": "Speed and latency",
    "capacity-spec": "Context, size and hardware",
    "token-volume": "Tokens and usage limits",
    "coding-benchmarks": "Coding benchmarks",
    "agent-benchmarks": "Agent and computer-use benchmarks",
    "security-benchmarks": "Security and safety benchmarks",
    "reasoning-benchmarks": "Reasoning, maths and knowledge benchmarks",
    "media-benchmarks": "Vision and audio benchmarks",
    "reliability-rate": "Accuracy, reliability and errors",
}

#: kept axis -> axes merged into it (same quantity, same unit).
MERGES = {
    # price, USD per 1M tokens (input and output stay separate rows inside it)
    "cost-per-token": [
        "api-price-input",
        "api-price-output",
        "input-price",
        "cost-per-million-input-tokens",
        "cost-per-million-output-tokens",
        "cost-per-million-tokens",
        "cost-per-thinking-token",
        "openrouter",
        "deepseek-v4-pro",
    ],
    "cache-input-price": ["cache-cost", "cache-rate"],  # USD per 1M cached tokens
    "cache-read-cost": ["cache-discount", "cache-read-pricing"],  # percent of the input price
    "cost-per-request": ["cost-per-call", "cost-per-reply", "cost-per-message"],
    "cost-per-task": [
        "cost-to-run",
        "patch-cost",
        "cost-per-proof",
        "cost-per-email",
        "cost-per-review",
    ],
    "cost-per-run": ["cost-per-benchmark", "cost-per-eval", "eval-cost", "evaluation-cost"],
    "cost-per-month": ["monthly-cost"],
    "cost-per-character": ["cost-per-million-characters"],
    # time
    "latency": ["inference-latency", "latency-per-call"],
    "task-duration": [
        "time-per-task",
        "time-to-complete",
        "wall-time",
        "completion-time",
        "time-to-completion",
        "execution-time",
        "total-duration",
    ],
    "generation-time": ["generation-duration"],
    "tokens-per-second": ["inference-speed", "decode-speed"],
    "prefill-speed": ["prompt-processing-speed"],
    # size
    "max-output-tokens": ["maximum-output-tokens"],
    "total-parameters": ["parameters", "model-parameters"],
    "memory-usage": ["vram-usage"],
    # tokens and limits
    "tokens-per-task": ["total-tokens"],
    "output-tokens-per-task": [
        "total-output-tokens-per-task",
        "output-tokens-per-intelligence-index-task",
    ],
    "reasoning-tokens": ["thinking-tokens"],
    "turns-per-task": ["turns-per-run"],
    "usage-consumption": [
        "usage-consumption-rate",
        "usage-limit-burn",
        "quota-consumption",
        "weekly-quota-consumption",
    ],
    "usage-quota": ["token-allowance", "message-limits", "request-rate-limit"],
    # errors and rates
    "http-error-rate": ["api-error-rate", "error-rate"],
    "error-status-code": ["error-code"],
    "tool-call-accuracy": ["tool-calling-accuracy"],
    "run-to-run-variation": ["run-instability"],
    "serial-arithmetic-steps": ["arithmetic-steps"],
    "pass-rate": ["success-rate", "task-completion-rate"],
    "constraint-adherence": ["constraint-adherence-score"],
    # one benchmark, two spellings of its name
    "artificial-analysis-intelligence-index": [
        "aa-intelligence-index",
        "artificial-analysis-index",
    ],
    "hle": ["humanity-s-last-exam"],
    "hle-with-tools": ["humanity-s-last-exam-with-tools"],
    "charxiv-rq-python": ["charxiv-rq-with-python"],
    "aa-briefcase": ["aa-briefcase-elo"],
}

#: Not an axis anybody measured.
DECLINE = {
    "other": "the slug is the word 'other' - a catch-all, not an axis",
    "fable-5": "a model's name filed as an axis",
}

#: First match wins, for kept axes the reviewed map does not cover.
RULES = [
    ("price", r"cost|price|pricing|usd|bill|spend|cache-input|per-million|fee"),
    (
        "speed-latency",
        r"speed|latency|tokens-per-second|time-to|ttft|duration|wall-time|time-per|prefill|"
        r"throughput|generation-time|frames|move-time|time-horizon|exploration-time|"
        r"acceptance-rate",
    ),
    (
        "capacity-spec",
        r"context-window|max-output|parameter|model-size|downloads|memory|ram-|vram|kv-|"
        r"hardware|training-data|licen|voice-library|provider-count|shutdown",
    ),
    (
        "token-volume",
        r"token|calls|requests|turns|lines-of-code|files-changed|chunks|queries|usage|quota|"
        r"consumption|allowance|credits|limit",
    ),
    (
        "coding-benchmarks",
        r"swe|terminal-bench|deepswe|livecode|cursor|programbench|program-bench|frontiercode|"
        r"humaneval|kernelbench|scicode|code-|bugs-found|real-swe",
    ),
    (
        "agent-benchmarks",
        r"osworld|mcp|browsecomp|tau-|agents-last|automationbench|agentic|gdpval|briefcase|"
        r"screenspot|tool-|routing|posttrain|mind2web|claweval|finance-agent|coding-agent-index",
    ),
    (
        "security-benchmarks",
        r"cyber|exploit|vulnerab|attack|strongreject|fortress|post-cutoff|sre-bench|"
        r"escape|cheating|forbidden|latchbio|compromise",
    ),
    (
        "reasoning-benchmarks",
        r"gpqa|hle|humanit|aime|amc|frontiermath|mmlu|arc-agi|index|aa-|intelligence|"
        r"simpleqa|omniscience|go-elo|chess|centipawn|dig-bench|vellum|ifbench|math|gsm8k|"
        r"critpt|healthbench|harvey|eebench|world-knowledge|scientific|mrcr|lcr|vals",
    ),
    (
        "media-benchmarks",
        r"mmmu|charxiv|mmau|voicebench|audio|vision|chart|dashboard|multi-panel|diagram|"
        r"voice|vqa|^v$|image",
    ),
    (
        "reliability-rate",
        r"error|uptime|reliab|failure|fail|hallucinat|confabul|consisten|regression|"
        r"success|status|accuracy|rate|precision|recall|score|pass|bluff|instabil|variation|"
        r"variance|kappa|agreement|f1|catch|false|hold|flipped|correct",
    ),
]


#: GENERATED by --write-headings, then corrected by hand. kept axis -> heading.
#: `None` is UNFILED: no reviewed placement and no rule matched.
HEADING = {
    "cost-per-token": "price",  # reviewed
    "context-window": "capacity-spec",  # reviewed
    "tokens-per-second": "speed-latency",  # reviewed
    "cost-per-task": "price",  # reviewed
    "time-to-first-token": "speed-latency",  # reviewed
    "task-duration": "speed-latency",  # reviewed
    "terminal-bench-4-0": "coding-benchmarks",  # rule
    "swe-bench-pro": "coding-benchmarks",  # rule
    "gpqa-diamond": "reasoning-benchmarks",  # rule
    "model-size": "capacity-spec",  # rule
    "tokens-per-task": "token-volume",  # reviewed
    "intelligence-index": "reasoning-benchmarks",  # rule
    "token-usage": "token-volume",  # reviewed
    "artificial-analysis-intelligence-index": "reasoning-benchmarks",  # rule
    "cost-per-run": "price",  # reviewed
    "output-tokens": "token-volume",  # reviewed
    "swe-bench": "coding-benchmarks",  # rule
    "terminal-bench": "coding-benchmarks",  # rule
    "terminal-bench-2-1": "coding-benchmarks",  # rule
    "active-parameters": "capacity-spec",  # rule
    "exploitbench": "security-benchmarks",  # rule
    "output-tokens-per-task": "token-volume",  # rule
    "swe-bench-verified": "coding-benchmarks",  # rule
    "total-parameters": "capacity-spec",  # rule
    "cybergym": "security-benchmarks",  # rule
    "deepswe": "coding-benchmarks",  # rule
    "accuracy": "reliability-rate",  # reviewed
    "arc-agi-3": "reasoning-benchmarks",  # rule
    "mcp-atlas": "agent-benchmarks",  # rule
    "aa-briefcase": "agent-benchmarks",  # rule
    "agents-last-exam": "agent-benchmarks",  # rule
    "automationbench-aa": "agent-benchmarks",  # rule
    "browsecomp": "agent-benchmarks",  # rule
    "cache-read-cost": "price",  # reviewed
    "cursorbench-4-0": "coding-benchmarks",  # rule
    "deepswe-v1-1": "coding-benchmarks",  # rule
    "exploit-gym": "security-benchmarks",  # rule
    "gdpval-aa": "agent-benchmarks",  # rule
    "gdpval-aa-v2": "agent-benchmarks",  # rule
    "hle": "reasoning-benchmarks",  # rule
    "max-output-tokens": "capacity-spec",  # rule
    "osworld-2-0": "agent-benchmarks",  # rule
    "pass-rate": "reliability-rate",  # reviewed
    "session-duration": "speed-latency",  # rule
    "terminal-bench-science-0-1": "coding-benchmarks",  # rule
    "usage-consumption": "token-volume",  # rule
    "aime-2026": "reasoning-benchmarks",  # rule
    "automationbench": "agent-benchmarks",  # rule
    "chess-tournament-score": "reasoning-benchmarks",  # rule
    "coding-agent-index": "agent-benchmarks",  # rule
    "constraint-adherence": "reliability-rate",  # hand
    "cost-per-image": "price",  # reviewed
    "cost-per-month": "price",  # rule
    "cot-controllability-rate": "reliability-rate",  # rule
    "cursor-bench": "coding-benchmarks",  # rule
    "false-alarm-rate": "reliability-rate",  # rule
    "false-positive-rate": "reliability-rate",  # reviewed
    "frontiermath-tier-4": "reasoning-benchmarks",  # rule
    "generation-time": "speed-latency",  # rule
    "ifbench": "reasoning-benchmarks",  # rule
    "input-tokens": "token-volume",  # rule
    "latency": "speed-latency",  # rule
    "mmmu-pro": "media-benchmarks",  # rule
    "osworld-2": "agent-benchmarks",  # rule
    "osworld-verified": "agent-benchmarks",  # rule
    "output-size": "token-volume",  # reviewed
    "posttrainbench": "agent-benchmarks",  # rule
    "prefill-speed": "speed-latency",  # rule
    "reasoning-tokens": "token-volume",  # rule
    "routing-accuracy": "agent-benchmarks",  # rule
    "score": "reliability-rate",  # reviewed
    "token-consumption": "token-volume",  # reviewed
    "aa-briefcase-v1-1": "agent-benchmarks",  # rule
    "aa-index": "reasoning-benchmarks",  # rule
    "aa-lcr": "reasoning-benchmarks",  # rule
    "aa-lcr-v1-1": "reasoning-benchmarks",  # rule
    "aa-omniscience": "reasoning-benchmarks",  # rule
    "accessibility-control-refusal": "security-benchmarks",  # hand
    "accuracy-by-phrasing": "reliability-rate",  # rule
    "accuracy-drop-from-anonymization": "reliability-rate",  # rule
    "accuracy-drop-from-plain-template": "reliability-rate",  # rule
    "accuracy-on-complex-questions": "reliability-rate",  # rule
    "accuracy-on-real-twins": "reliability-rate",  # rule
    "action-match": "reliability-rate",  # hand
    "added-latency": "speed-latency",  # reviewed
    "adversarial-pass-rate": "reliability-rate",  # rule
    "agent-budget": None,  # unfiled
    "agentic-index": "agent-benchmarks",  # rule
    "agreement": "reliability-rate",  # rule
    "aic-usage": "capacity-spec",  # reviewed
    "amc-2023": "reasoning-benchmarks",  # rule
    "attack-success-rate": "security-benchmarks",  # rule
    "audio-generation-time": "speed-latency",  # rule
    "audio-mc": "media-benchmarks",  # rule
    "average-test-balanced-accuracy-bacc": "reliability-rate",  # rule
    "believed-shipped-rate": "reliability-rate",  # rule
    "benches": None,  # unfiled
    "benchmark-rank": None,  # unfiled
    "benchmark-score": "reliability-rate",  # rule
    "blind-judge-score": "reliability-rate",  # rule
    "browsecomp-w-ctx": "agent-benchmarks",  # rule
    "bugs-found": "coding-benchmarks",  # rule
    "cache-hit-rate": "reliability-rate",  # rule
    "cache-input-price": "price",  # rule
    "cache-miss-rate": "reliability-rate",  # rule
    "cache-read-size": "token-volume",  # hand
    "cache-retention": "capacity-spec",  # hand
    "cache-write-size": "token-volume",  # hand
    "captcha-word-refusal": "security-benchmarks",  # hand
    "cases-correct": "reliability-rate",  # rule
    "catch-rate": "reliability-rate",  # rule
    "centipawn-loss": "reasoning-benchmarks",  # rule
    "chartography-no-tools": "media-benchmarks",  # rule
    "charxiv-rq": "media-benchmarks",  # rule
    "charxiv-rq-python": "media-benchmarks",  # rule
    "cheating-rate": "security-benchmarks",  # rule
    "cheating-trials": "security-benchmarks",  # rule
    "checker-pass-rate": "reliability-rate",  # rule
    "chip-design-time": "speed-latency",  # reviewed
    "classification-accuracy": "reliability-rate",  # rule
    "claweval-1-1": "agent-benchmarks",  # rule
    "code-exploration-time": "speed-latency",  # rule
    "code-reuse-rate": "coding-benchmarks",  # rule
    "cohens-kappa": "reliability-rate",  # rule
    "cold-start-cost": "price",  # rule
    "composite-benchmark": None,  # unfiled
    "confabulation-rate": "reliability-rate",  # rule
    "confidence-on-made-up-totals": "reliability-rate",  # hand
    "consistency-gap": "reliability-rate",  # rule
    "consistency-score": "reliability-rate",  # rule
    "context-sensitivity": "reliability-rate",  # hand
    "context-window-usage": "capacity-spec",  # rule
    "continuous-score": "reliability-rate",  # reviewed
    "control-accuracy": "reliability-rate",  # rule
    "cosine-similarity": "reliability-rate",  # hand
    "cost-per-character": "price",  # reviewed
    "cost-per-commit": "price",  # rule
    "cost-per-correct-answer": "price",  # rule
    "cost-per-day": "price",  # rule
    "cost-per-generation": "price",  # reviewed
    "cost-per-hour": "price",  # rule
    "cost-per-request": "price",  # rule
    "cost-per-session": "price",  # rule
    "cost-per-thousand-chats": "price",  # rule
    "cost-per-week": "price",  # rule
    "credits-per-week": "token-volume",  # rule
    "critpt": "reasoning-benchmarks",  # rule
    "cyber-gap-months": "security-benchmarks",  # rule
    "cybergym-vulnerability-detection": "security-benchmarks",  # rule
    "dashboard-reading-accuracy": "media-benchmarks",  # rule
    "diagram-generation-rate": "capacity-spec",  # rule
    "dig-bench-tier-7": "reasoning-benchmarks",  # rule
    "distorted-text-solve-rate": "reliability-rate",  # rule
    "downloads": "capacity-spec",  # rule
    "earnings-memory": "capacity-spec",  # rule
    "editorial-craft": None,  # unfiled
    "eebench": "reasoning-benchmarks",  # rule
    "effective-usage-ratio": "token-volume",  # rule
    "error-reduction-on-agent-decisions": "reliability-rate",  # rule
    "error-reduction-on-output": "reliability-rate",  # rule
    "error-status-code": "reliability-rate",  # reviewed
    "escape-attempts": "security-benchmarks",  # rule
    "estimate": None,  # unfiled
    "eval-score": "reliability-rate",  # rule
    "exact-reproduction-rate": "reliability-rate",  # rule
    "example-accuracy-in-note": "reliability-rate",  # rule
    "exploit-count": "security-benchmarks",  # rule
    "exploitbench-exploit-reasoning": "security-benchmarks",  # rule
    "f1-score": "reliability-rate",  # rule
    "factual-recall-score": "reliability-rate",  # rule
    "failed-call-rate": "reliability-rate",  # rule
    "failure-rate": "reliability-rate",  # reviewed
    "false-alarms": "reliability-rate",  # rule
    "files-changed": "token-volume",  # rule
    "finance-agent-v2": "agent-benchmarks",  # rule
    "first-attempt-rate": "reliability-rate",  # rule
    "fix-score": "reliability-rate",  # rule
    "flipped-under-pushback": "reliability-rate",  # rule
    "fortress-adversarial": "security-benchmarks",  # rule
    "fortress-benign": "security-benchmarks",  # rule
    "frontiercode-1-1-main-max": "coding-benchmarks",  # rule
    "frontiermath": "reasoning-benchmarks",  # rule
    "game-duration": "speed-latency",  # rule
    "gdp-pdf": "agent-benchmarks",  # hand
    "gdpval": "agent-benchmarks",  # rule
    "gdpval-aa-elo": "agent-benchmarks",  # rule
    "gdpval-aa-v2-1": "agent-benchmarks",  # rule
    "german-term-coverage": "reliability-rate",  # hand
    "global-mmlu-lite": "reasoning-benchmarks",  # rule
    "go-elo": "reasoning-benchmarks",  # rule
    "gsm8k": "reasoning-benchmarks",  # rule
    "hallucinated-functions": "reliability-rate",  # rule
    "hallucinated-packages": "reliability-rate",  # rule
    "hallucination-rate": "reliability-rate",  # reviewed
    "hard-reasoning-index": "reasoning-benchmarks",  # rule
    "hardware-requirements": "capacity-spec",  # rule
    "harvey": "reasoning-benchmarks",  # rule
    "harvey-s-legal-benchmark": "reasoning-benchmarks",  # rule
    "healthbench": "reasoning-benchmarks",  # rule
    "held-under-pushback": "reliability-rate",  # hand
    "hle-no-tools-text-only": "reasoning-benchmarks",  # rule
    "hle-text": "reasoning-benchmarks",  # rule
    "hle-text-only": "reasoning-benchmarks",  # rule
    "hle-verified": "reasoning-benchmarks",  # rule
    "hle-with-tools": "reasoning-benchmarks",  # rule
    "hold-rate-after-assertion": "reliability-rate",  # rule
    "hold-rate-after-doubt": "reliability-rate",  # rule
    "http-error-rate": "reliability-rate",  # reviewed
    "humaneval": "coding-benchmarks",  # rule
    "humanity-s-last-exam-without-tools": "reasoning-benchmarks",  # rule
    "illegal-move-rate": "reliability-rate",  # rule
    "incident-recognition-rate": "reliability-rate",  # rule
    "injection-resistance-rate": "reliability-rate",  # rule
    "input-token-reduction": "token-volume",  # rule
    "input-tokens-total": "token-volume",  # rule
    "instruction-following": "reliability-rate",  # hand
    "judge-accuracy": "reliability-rate",  # rule
    "judging-accuracy": "reliability-rate",  # rule
    "kernel-latency-reduction": "speed-latency",  # rule
    "kernelbench-hard": "coding-benchmarks",  # rule
    "know-score": "reliability-rate",  # rule
    "knowledge-action-gap-rate": "reliability-rate",  # rule
    "kv-cache-per-token": "capacity-spec",  # rule
    "kv-data-reduction": "capacity-spec",  # rule
    "latchbio": "security-benchmarks",  # rule
    "latency-p95": "speed-latency",  # rule
    "latency-tail": "speed-latency",  # rule
    "learning-accuracy": "reliability-rate",  # rule
    "licence": "capacity-spec",  # reviewed
    "lines-of-code": "token-volume",  # rule
    "livecodebench": "coding-benchmarks",  # rule
    "livecodebench-v6": "coding-benchmarks",  # rule
    "made-up-totals-rate": "reliability-rate",  # rule
    "math500": "reasoning-benchmarks",  # rule
    "mean-signed-error": "reliability-rate",  # rule
    "memorisation-gap": "reliability-rate",  # hand
    "memory-usage": "capacity-spec",  # rule
    "mmau": "media-benchmarks",  # rule
    "mmlu-pro": "reasoning-benchmarks",  # rule
    "mmmu-pro-standard-10": "media-benchmarks",  # rule
    "model-calls": "token-volume",  # rule
    "move-time-limit": "speed-latency",  # rule
    "mrcr-v2": "reasoning-benchmarks",  # rule
    "mrcr-v2-at-512k-1m": "reasoning-benchmarks",  # rule
    "multi-panel-incident-accuracy": "media-benchmarks",  # rule
    "neutral-solve-rate": "reliability-rate",  # rule
    "no-cot-math-time-horizon": "speed-latency",  # rule
    "note-word-count": "token-volume",  # hand
    "online-mind2web": "agent-benchmarks",  # rule
    "osworld-2-0-offline": "agent-benchmarks",  # rule
    "osworld-2-1-partial": "agent-benchmarks",  # rule
    "overall-score": "reliability-rate",  # rule
    "pass-at-1": "reliability-rate",  # rule
    "pass-at-k": "reliability-rate",  # rule
    "patch-reintroduces-known-bug": "security-benchmarks",  # hand
    "post-cutoff-exploit-count": "security-benchmarks",  # rule
    "posttrainbench-plus": "agent-benchmarks",  # rule
    "precision": "reliability-rate",  # reviewed
    "prediction-error": "reliability-rate",  # rule
    "profit-generated": "reliability-rate",  # rule
    "program-bench": "capacity-spec",  # rule
    "projects-scanned": None,  # unfiled
    "prompt-instability": "reliability-rate",  # rule
    "proofs-proved": "reasoning-benchmarks",  # hand
    "provider-count": "capacity-spec",  # rule
    "purpose-gap": "security-benchmarks",  # hand
    "quantization-performance-retention": "capacity-spec",  # hand
    "ram-usage": "capacity-spec",  # rule
    "raw-accuracy": "reliability-rate",  # rule
    "reading-efficiency": "reasoning-benchmarks",  # hand
    "real-swe": "coding-benchmarks",  # rule
    "reasoning-chunks": "token-volume",  # rule
    "reasoning-duration": "speed-latency",  # rule
    "recovery-rate": "reliability-rate",  # rule
    "regression-rate": "reliability-rate",  # reviewed
    "relative-gain": None,  # unfiled
    "reliability": "reliability-rate",  # rule
    "requests-per-month": "token-volume",  # rule
    "retired-names-written": "coding-benchmarks",  # hand
    "retrieval-latency": "speed-latency",  # rule
    "routing-latency": "speed-latency",  # rule
    "routing-rate": "agent-benchmarks",  # rule
    "run-to-run-variation": "reliability-rate",  # rule
    "scicode": "coding-benchmarks",  # rule
    "scientific-reasoning": "reasoning-benchmarks",  # rule
    "screenspot-pro": "agent-benchmarks",  # rule
    "serial-arithmetic-steps": "reasoning-benchmarks",  # hand
    "shutdown-date": "capacity-spec",  # rule
    "side-effect-reduction": "security-benchmarks",  # hand
    "silent-failure-rate": "reliability-rate",  # rule
    "simpleqa-verified": "reasoning-benchmarks",  # rule
    "simplevqa": "media-benchmarks",  # rule
    "speculative-decoding-acceptance-rate": "speed-latency",  # rule
    "sre-bench-reverse-engineering-tasks": "security-benchmarks",  # rule
    "stability-adjusted-accuracy": "reliability-rate",  # rule
    "stale-premise-accuracy": "reliability-rate",  # rule
    "strongreject": "security-benchmarks",  # rule
    "structured-output-benchmark": "reliability-rate",  # hand
    "swe-bench-verified-with-advisor-mode": "coding-benchmarks",  # rule
    "swe-fficiency": "coding-benchmarks",  # rule
    "swe-pro": "coding-benchmarks",  # rule
    "swebench-pro-public": "coding-benchmarks",  # rule
    "tag-accuracy": "reliability-rate",  # rule
    "tau-3-banking": "agent-benchmarks",  # rule
    "teaching-against-self": "reasoning-benchmarks",  # hand
    "teaching-efficiency": "reasoning-benchmarks",  # hand
    "temperature": None,  # unfiled
    "terminal-bench-2-0": "coding-benchmarks",  # rule
    "terminal-bench-2-1-best-harness": "coding-benchmarks",  # rule
    "terminal-bench-3-0": "coding-benchmarks",  # rule
    "terminal-bench-science": "coding-benchmarks",  # rule
    "thinking-token-reduction": "token-volume",  # rule
    "time-horizon": "speed-latency",  # reviewed
    "time-per-check": "speed-latency",  # rule
    "time-per-output-token": "speed-latency",  # rule
    "time-per-proof": "speed-latency",  # rule
    "time-to-full-compromise": "speed-latency",  # rule
    "token-count-accuracy": "token-volume",  # reviewed
    "token-efficiency": "token-volume",  # rule
    "token-usage-rate": "token-volume",  # rule
    "tokens-per-output": "token-volume",  # reviewed
    "tool-call-accuracy": "agent-benchmarks",  # rule
    "tool-call-loop-length": "agent-benchmarks",  # rule
    "tool-name-accuracy": "agent-benchmarks",  # rule
    "total-agent-requests": "token-volume",  # rule
    "total-bill-change": "price",  # rule
    "total-project-cost": "price",  # rule
    "total-queries": "token-volume",  # rule
    "training-data-efficiency": "capacity-spec",  # rule
    "training-data-size": "capacity-spec",  # rule
    "trajectories-with-forbidden-actions": "security-benchmarks",  # rule
    "trajectories-with-unfulfilled-obligations": "security-benchmarks",  # hand
    "trap-accuracy": "reliability-rate",  # rule
    "turns-per-task": "token-volume",  # rule
    "unsolvable-bluff-rate": "reliability-rate",  # rule
    "upgrade-regressions": "reliability-rate",  # rule
    "uptime": "reliability-rate",  # rule
    "usage-quota": "capacity-spec",  # reviewed
    "usage-volume": "token-volume",  # rule
    "v": "media-benchmarks",  # rule
    "vals-index": "reasoning-benchmarks",  # rule
    "variance": "reliability-rate",  # rule
    "vellum-leaderboard": "reasoning-benchmarks",  # rule
    "violation-fee": "price",  # rule
    "vision": "media-benchmarks",  # rule
    "voice-library-size": "capacity-spec",  # rule
    "voicebench": "media-benchmarks",  # rule
    "vulnerabilities-discovered": "security-benchmarks",  # rule
    "vulnerability-detection-rate": "security-benchmarks",  # rule
    "world-knowledge": "reasoning-benchmarks",  # rule
    "write-score": "reliability-rate",  # rule
    "cost-per-minute": "price",  # reviewed
    "cost-per-shot": "price",  # reviewed
    "cost-per-benchmark-point": "price",  # reviewed
    "token-cost": "price",  # reviewed
    "wall-clock-time": "speed-latency",  # reviewed
    "fast-mode": "speed-latency",  # reviewed
    "output-token-inflation": "token-volume",  # reviewed
    "tokenizer-efficiency": "token-volume",  # reviewed
    "task-completion": "reliability-rate",  # reviewed
    "osworld": "agent-benchmarks",  # rule
    "aime": "reasoning-benchmarks",  # rule
    "aime-2025": "reasoning-benchmarks",  # rule
    "arc-agi": "reasoning-benchmarks",  # rule
    "arc-agi-2": "reasoning-benchmarks",  # rule
    "mmmu": "media-benchmarks",  # rule
    "exploit-bench": "security-benchmarks",  # rule
    "exploitgym": "security-benchmarks",  # rule
    "medical-benchmark": "reasoning-benchmarks",  # hand
    "benchmark-performance": None,  # unfiled
    "chess-rating": "reasoning-benchmarks",  # rule
    "odds-ratio": None,  # unfiled
    "compiler-performance": "coding-benchmarks",  # hand
    "pretraining-efficiency": None,  # unfiled
    "pretraining-quality": None,  # unfiled
}

CLUSTERS = {t: (HEADING[t], MERGES.get(t, [])) for t in HEADING if HEADING[t]}
UNFILED = {t: "no heading matched" for t, h in HEADING.items() if h is None}
