"""PROPOSAL 2026-10-14: every JOB (best_for) leaf -> keep under a heading, merge
into a kept job, decline, or leave unfiled. One reader's judgement over names and
definitions on the local copy (341 leaves, internal view); a person approves
before anything is ruled (rule 10).

CLUSTERS: target -> (heading, [slugs merged into it]). The target is kept.
DECLINE:  slug -> reason. Rows kept, ruled `declined`.
UNFILED:  slug -> reason. Left under no heading on purpose - shown in the
          "not yet under a heading" box until somebody rules on them.

TWO THINGS THIS DOES NOT DO, ON PURPOSE
  - It merges NOTHING into `coding-agent` except its exact twin
    `coding-agents`. That leaf holds rows that do not belong to it (#412, #415
    open); folding more in would bury more of them.
  - It does not rule on capabilities filed as jobs (`instruction-following`,
    `constraint-adherence`, ...). Whether those are declined or moved is
    concern 10, a separate decision; they are UNFILED here.
"""

SECTION = "best_for"

PARENTS = {
    "agentic-automation": "Coding agents and automation",
    "review-and-security": "Code review and security",
    "software-development": "Software development",
    "documents-and-research": "Documents, data and research",
    "reasoning-and-science": "Reasoning, maths and science",
    "writing-and-content": "Writing and content",
    "chat-and-assistants": "Chat, roleplay and everyday use",
    "media-generation": "Images, video and audio",
    "cost-volume-local": "Cost, volume and local use",
}

AG, RV, SD, DR, RS, WC, CA, MG, CV = PARENTS

CLUSTERS = {
    # ── Coding agents and automation ───────────────────────────────────────
    "coding-agent": (AG, ["coding-agents"]),
    "agentic-coding": (
        AG,
        ["agentic-development", "agentic-development-worker", "code-and-agents"],
    ),
    "terminal-agent": (AG, ["terminal-agents", "terminal-work", "execution", "builder"]),
    "agentic-tasks": (
        AG,
        [
            "agentic-work",
            "agentic-workloads",
            "agents",
            "ai-agents",
            "agentic-systems",
            "automation",
            "complex-multi-step-workflows",
            "complex-workflows",
            "multi-agent-reasoning",
            "agentic-tool-use",
            "tool-calling",
            "multi-tool-agents",
            "production-agentic-workflows",
            "business-workflow-agents",
            "agentic-cowork",
            "business-simulation",
            "agent-safety",
            "skill-optimization",
        ],
    ),
    "long-horizon-agent": (
        AG,
        [
            "long-running-agents",
            "long-horizon-tasks",
            "long-horizon-software-engineering",
            "agent-memory",
            "memory-audit",
        ],
    ),
    "orchestration": (
        AG,
        [
            "orchestrator",
            "main-agent",
            "planning-orchestration",
            "long-running-orchestration",
            "internal-ai-backbone",
            "agent-handoff",
            "multi-session-feedback-loop",
            "routing",
            "model-selection",
        ],
    ),
    "computer-use": (
        AG,
        ["browser-control", "browser-operation", "browsing-tasks", "desktop-automation"],
    ),
    "trading-agent": (AG, []),
    "driving": (AG, []),
    # ── Code review and security ───────────────────────────────────────────
    "code-review": (
        RV,
        [
            "code-critique",
            "code-audit",
            "code-audit-and-fix",
            "codebase-audit",
            "adversarial-review",
        ],
    ),
    "reviewing-plans": (
        RV,
        ["project-plan-review", "verification", "evaluation-agents", "data-consistency-checking"],
    ),
    "security-review": (RV, ["security-audit"]),
    "cybersecurity": (
        RV,
        ["cybersecurity-agent", "cyber-defense", "ad-pentesting", "red-teaming", "ctf"],
    ),
    "vulnerability-discovery": (RV, ["vulnerability-detection", "exploit-verification"]),
    "reverse-engineering": (RV, []),
    "surgery": (RV, []),
    # ── Software development ───────────────────────────────────────────────
    "coding": (
        SD,
        [
            "programming",
            "coding-tasks",
            "coding-assistance",
            "coding-assistants",
            "coding-workhorse",
            "general-development",
            "general-purpose-coding",
            "daily-development",
            "development-work",
            "engineering-dev-work",
            "code-heavy-workloads",
            "software-engineering",
            "vibe-coding",
            "complex-coding",
            "face-blurring",
        ],
    ),
    "code-generation": (
        SD,
        [
            "implementation",
            "terraform-code-generation",
            "simulation-code",
            "proof-based-programming",
        ],
    ),
    "code-migration": (
        SD,
        [
            "code-porting",
            "code-refactoring",
            "code-translation",
            "legacy-code-revival",
            "multi-file-refactoring",
            "app-rebuilding",
        ],
    ),
    "large-codebases": (
        SD,
        [
            "large-repository",
            "large-project-development",
            "codebase-exploration",
            "code-analysis",
            "deep-investigation",
            "long-context-coding",
            "code-editing",
        ],
    ),
    "debugging": (SD, ["bug-fixes", "bug-fixing", "diagnosis"]),
    "code-optimization": (SD, []),
    "web-development": (
        SD,
        [
            "web-app-building",
            "website-creation",
            "web-design",
            "web-and-mobile-development",
            "mobile-app-creation",
            "image-to-web-development",
            "ui-code",
            "ui-prototyping",
            "companion-app-development",
            "business-software-development",
        ],
    ),
    "prototyping": (SD, ["rapid-prototyping"]),
    "game-development": (SD, []),
    "frontend-testing": (SD, ["agentic-testing"]),
    "planning": (SD, ["project-planning", "long-horizon-planning", "architecture", "design-work"]),
    "sql-generation": (SD, ["sql"]),
    "compiler-development": (SD, []),
    "chip-design": (SD, []),
    "buildroot-system-setup": (SD, []),
    # ── Documents, data and research ───────────────────────────────────────
    "rag": (DR, ["grounded-qa"]),
    "extraction": (
        DR,
        ["classification-extraction", "form-filling", "tax-preparation", "sentence-extraction"],
    ),
    "ocr": (DR, ["chinese-ocr", "text-image-extraction"]),
    "classification": (DR, ["policy-classification"]),
    "summarization": (DR, ["meeting-summarization", "document-workflows"]),
    "document-analysis": (
        DR,
        [
            "document-processing",
            "heavy-document-processing",
            "long-document",
            "long-context",
            "long-context-reasoning",
            "contradiction-resolution",
            "legal",
            "legal-work",
            "literary-criticism",
            "talking-and-document-work",
            "spreadsheet",
            "bi-dashboard",
            "incident-analysis",
            "finance",
            "market-analysis",
        ],
    ),
    "research": (
        DR,
        [
            "research-assistant",
            "agentic-knowledge-work",
            "exploration",
            "exploration-and-research",
            "search-agent",
            "knowledge-work",
            "knowledge-work-tasks",
            "sales-call-prep",
            "shopping",
            "librarian",
            "knowledge-management",
        ],
    ),
    # ── Reasoning, maths and science ───────────────────────────────────────
    "reasoning": (
        RS,
        [
            "reasoning-intensive-tasks",
            "think-hard",
            "complex-reasoning",
            "complex-problem-solving",
            "difficult-reasoning",
            "very-specific-logic",
            "critical-thinking",
        ],
    ),
    "math": (RS, ["math-reasoning", "stem"]),
    "scientific-reasoning": (
        RS,
        [
            "biology",
            "clinical-reasoning",
            "computational-biology",
            "electrical-engineering",
            "automated-science-lab",
            "scientific-research",
            "experimental-research",
            "neural-architecture-search",
        ],
    ),
    "proof-generation": (RS, []),
    "ds-judgment": (RS, ["ds-judgment-open"]),
    "teaching-from-examples": (RS, []),
    "timezone-conversion": (RS, []),
    "knowledge": (RS, ["compliance"]),
    # ── Writing and content ────────────────────────────────────────────────
    "creative-writing": (WC, ["fiction-writing", "narrative-writing"]),
    "content-writing": (
        WC,
        [
            "content-rewriting",
            "marketing-copy",
            "outreach-drafting",
            "writing",
            "writing-assistance",
        ],
    ),
    "translation": (WC, ["multi-lingual-inference", "chinese-language", "chinese-language-work"]),
    "documentation": (WC, ["technical-writing"]),
    "presentation-generation": (WC, ["presentation-creation", "ppt-generation"]),
    "brainstorming": (WC, ["debate"]),
    # ── Chat, roleplay and everyday use ────────────────────────────────────
    "roleplay": (
        CA,
        [
            "roleplaying",
            "quick-roleplay",
            "budget-roleplay",
            "extreme-content-roleplay",
            "companion-project",
            "personal-chatbot",
        ],
    ),
    "nsfw-content": (CA, ["nsfw-roleplay"]),
    "chat": (
        CA,
        [
            "chatting",
            "chatbots",
            "chatbot",
            "general-chat",
            "general-conversation",
            "general-purpose-chat",
            "conversational-ui",
        ],
    ),
    "general-purpose": (
        CA,
        [
            "general-assistant",
            "general-llm-use",
            "general-task",
            "general-tasks",
            "general-usage",
            "general-use",
            "general-workloads",
            "any-task",
            "daily-driver",
            "daily-tasks",
            "everyday-work",
            "non-coding-tasks",
            "professional-tasks",
            "professional-work",
            "tech-how-to",
            "maximum-quality",
        ],
    ),
    "customer-service": (CA, ["support-triage", "slack-triage"]),
    "daily-planning": (CA, []),
    # ── Images, video and audio ────────────────────────────────────────────
    "image-generation": (
        MG,
        ["creative-visual-generation", "product-photography", "visual-exploration", "design"],
    ),
    "3d-modeling": (
        MG,
        [
            "3d-art",
            "3d-asset-generation",
            "3d-scene-construction",
            "3d-scene-editing",
            "cad-design",
        ],
    ),
    "2d-sprite-generation": (MG, ["sprite-generation", "pixel-art-generation"]),
    "svg-generation": (MG, []),
    "video-generation": (MG, ["explainer-videos", "product-launch-video"]),
    "video-editing": (MG, []),
    "video-indexing": (MG, ["video-processing"]),
    "vision": (MG, ["carb-counting", "hazard-spotting"]),
    "voice-pipeline": (MG, ["voice-agent", "voice-input-tool"]),
    # ── Cost, volume and local use ─────────────────────────────────────────
    "local-inference": (
        CV,
        [
            "local-ai",
            "local-deployment",
            "local-inference-mac",
            "local-model",
            "offline-use",
            "one-workstation",
        ],
    ),
    "high-volume-workloads": (
        CV,
        [
            "high-volume",
            "high-volume-low-cost",
            "high-volume-agentic-workloads",
            "offline-batch-processing",
            "batch-processing",
            "non-interactive-work",
            "nightly-experimentation",
            "ai-pipelines",
            "small-medium-tasks",
            "simple-tasks",
            "heartbeat-checking",
            "git-operations",
            "internal-tools",
            "application-use",
            "quick-one-shot-work",
        ],
    ),
    "value-for-price": (
        CV,
        [
            "api-rate-viability",
            "subscription-independence",
            "api-usage",
            "free-tier",
            "cache-pricing",
            "price-comparison",
            "fallback-model",
        ],
    ),
}

#: Not a job at all: a benchmark result, a product feature, or a sentence
#: about suitability with no task in it.
DECLINE = {
    "the-nature-of-the-work": "names no task: 'being the right tool for a particular kind of work'",
    "top-capability": "a benchmark ranking, not a task somebody runs",
    "benchmark": "a benchmark score, not a task somebody runs",
    "visible-chain-of-thought": "a product feature, not a task",
    "vision-routing": "a product feature, not a task",
    "building-contract-tests": "what a model upgrade breaks in an app, not a task run with it",
}

#: Capabilities filed as jobs (concern 10). Left unfiled for that ruling.
UNFILED = {
    "instruction-following": "a capability filed as a job",
    "constraint-adherence": "a capability filed as a job",
    "constrained-tasks": "a capability filed as a job",
    "vague-prompt-following": "a capability filed as a job",
    "adversarial-strategic-play": "a capability filed as a job",
}
