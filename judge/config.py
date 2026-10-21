"""Read the shared contract.

`contract/` is the interface between two engineers. This module reads it and
never writes to it — changes there go through a PR (see CLAUDE.md).

Loaded once at import and cached. These files change perhaps five times in
eight weeks, so re-reading per request buys nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml

CONTRACT_DIR = Path(__file__).resolve().parent.parent / "contract"

FailureMode = Literal["silent", "loud"]


@dataclass(frozen=True)
class Capability:
    """One entry from contract/capabilities.yaml."""

    key: str
    failure_mode: FailureMode
    description: str
    sounds_like: tuple[str, ...]

    @property
    def fails_silently(self) -> bool:
        """Silent failures require POSITIVE consensus, not merely absence of criticism.

        Loud failures error in seconds and a validation retry is a real
        mitigation, so weaker evidence is acceptable. This distinction decides
        how much evidence the answer path demands, and it matters more than how
        difficult the task is.
        """
        return self.failure_mode == "silent"


@dataclass(frozen=True)
class ConditionDimension:
    """One entry from contract/conditions.yaml."""

    key: str
    bands: tuple[str, ...]
    description: str


@lru_cache(maxsize=1)
def capabilities() -> dict[str, Capability]:
    raw = _read("capabilities.yaml")
    out: dict[str, Capability] = {}
    for entry in raw["capabilities"]:
        cap = Capability(
            key=entry["key"],
            failure_mode=entry["failure_mode"],
            description=entry.get("description", "").strip(),
            sounds_like=tuple(entry.get("sounds_like", ())),
        )
        out[cap.key] = cap
    return out


@lru_cache(maxsize=1)
def board_vocabulary() -> dict[str, dict[str, list[dict[str, str]]]]:
    """`contract/board_vocabulary.yaml` -> {section: {heading: [{slug, name}]}}.

    THE NAMES THE EXTRACTOR IS ASKED TO REUSE (2026-10-14), capabilities only
    so far. REUSE-FIRST, NOT CLOSED: nothing in code checks a proposed slug
    against this, for the reason `board_exemplars` gives below - a membership
    check forces a quote into the nearest wrong name. A section the file does
    not carry comes back absent, and the prompt falls back to its exemplars.
    """
    raw = _read("board_vocabulary.yaml") or {}
    return {
        str(section): {str(h): list(items or ()) for h, items in (headings or {}).items()}
        for section, headings in raw.items()
    }


def section_headings(section: str) -> frozenset[str]:
    """The heading keys a leaf of `section` may be filed under: every parent in
    `contract/slug_parents.yaml` for that section. Empty when it has none."""
    return frozenset(slug_parents().get(section, {}).values())


@lru_cache(maxsize=1)
def board_exemplars() -> dict:
    """Calibration samples for the board's three sections — NOT a vocabulary.

    Returns `contract/board_surfaces.yaml` whole, so the caller sees the
    `question`, the `test` and the `exemplars` for each section.

    THERE IS DELIBERATELY NO `job_keys()` OR `metric_keys()` HERE. An earlier
    version of this file had both, as closed lists the classifier had to pick
    from, and that was the defect: the hand-designed board carries `vision`,
    `multimodal` and `function-calling`, none of which is in
    `capabilities.yaml`. A closed list would have dropped them or forced them
    into the nearest ratified key, which manufactures consensus.

    So the board's sections are discovered from the evidence and these entries
    only calibrate how broad a section should be. Anything that turns this back
    into a lookup — a `keys()` helper, a membership check on a proposed slug —
    reintroduces the cap. The consolidation problem it looks like it solves
    (two names for one section) is solved downstream instead, by normalising the
    slug in code and letting a person merge the rest through the candidate
    ruling that already exists.
    """
    return _read("board_surfaces.yaml")


#: How a platform id is written for a reader. Only the ones that need it: the
#: rest title-case correctly on their own.
_PLATFORM_LABELS = {
    "arxiv": "arXiv",
    "hackernews": "Hacker News",
    "devto": "dev.to",
    "huggingface": "Hugging Face",
    "github": "GitHub",
    "x": "X",
    "reddit": "Reddit",
    "blog": "engineering blogs",
}


@lru_cache(maxsize=1)
def evidence_platforms(exclude_ids: tuple[str, ...] = ()) -> tuple[str, ...]:
    """The platforms the board harvests, read from `contract/sources.yaml`.

    THE FAQ MUST NOT COUNT THESE ITSELF. The landing demo's answer said "ten
    public platforms" and listed TikTok, Instagram, Hashnode and WordPress —
    none of which has a terms ruling in the contract, so none of which is
    harvested. A number typed into copy is a coverage claim that nothing
    checks, and it was already wrong by four.

    Read from the contract instead, so the sentence changes when the sources
    change. `judge/` reads the shared contract file directly rather than
    importing `collect.registry.sources`: the lane boundary is about code
    flowing between the two halves, and `contract/` belongs to both.
    """
    rows = _read("sources.yaml").get("sources") or []
    seen: list[str] = []
    for row in rows:
        if row.get("id") in exclude_ids:
            continue  # withheld from this view (judge/publication.py)
        platform = row.get("platform")
        if platform and platform not in seen:
            seen.append(platform)
    return tuple(_PLATFORM_LABELS.get(p, p) for p in seen)


@lru_cache(maxsize=1)
def faq() -> dict:
    """`contract/faq.yaml` whole — the FAQ page's questions and answers.

    Returned unresolved on purpose. Three of the eleven entries carry no `a` at
    all: they hold `unestablished_answer` plus a `claims` list naming exactly
    what the demo's version asserted about models, and one holds an
    `a_template` whose platform count must come from `sources.yaml` rather than
    from a number typed here.

    Resolving that is `judge/app.py`'s job, because it is the layer with a
    database and a source contract to check against. This function's
    contribution is to keep the copy in one reviewable file (rule 5) and to
    keep the demo wording as `demo_answer` beside the served one, so the
    difference between "what the mock-up said" and "what the board can support"
    stays auditable instead of being lost in a rewrite.
    """
    return _read("faq.yaml")


@lru_cache(maxsize=1)
def conditions() -> dict[str, ConditionDimension]:
    raw = _read("conditions.yaml")
    return {
        entry["key"]: ConditionDimension(
            key=entry["key"],
            bands=tuple(entry["bands"]),
            description=entry.get("description", "").strip(),
        )
        for entry in raw["dimensions"]
    }


@lru_cache(maxsize=1)
def dominant_dimension() -> dict[str, str]:
    """Which condition dimension forms the bucket key for each capability.

    A 12-tool task looks up `tools:6-15`, never the model's flattering average.
    """
    return dict(_read("conditions.yaml")["dominant_dimension"])


#: Vendor spellings of the same tier, folded onto the bands in
#: contract/conditions.yaml. Extraction can only produce the band names
#: themselves (`Conditions.reasoning_effort` is a Literal), so this exists for
#: every other writer - seeds, backfills, and whatever a human types.
_EFFORT_ALIASES: dict[str, str] = {
    "off": "off", "none": "off", "minimal": "off", "no-thinking": "off",
    "low": "low",
    "medium": "medium", "med": "medium", "default": "medium",
    "high": "high",
    "max": "max", "xhigh": "max", "highest": "max", "maximum": "max",
    "auto": "auto", "dynamic": "auto", "router": "auto", "auto mode": "auto",
}


def band_for(dimension: str, value: int | bool | str | None) -> str:
    """Place a raw value into its fixed band.

    Bands are fixed rather than continuous because buckets must be countable —
    "fine under 5 tools, breaks above 10" only exists if the buckets are
    discrete. An unknown value is honest: it becomes `unknown` rather than
    being guessed into a band.
    """
    if value is None:
        return "unknown"

    if dimension == "tool_count":
        n = int(value)
        if n == 0:
            return "none"
        if n <= 5:
            return "1-5"
        if n <= 15:
            return "6-15"
        return "16+"

    if dimension == "context_size":
        n = int(value)
        if n < 8_000:
            return "<8k"
        if n < 32_000:
            return "8k-32k"
        if n < 128_000:
            return "32k-128k"
        return "128k+"

    if dimension == "schema_enforced":
        return "on" if value else "off"

    if dimension == "reasoning_effort":
        band = _EFFORT_ALIASES.get(str(value).strip().lower())
        if band is None:
            # DELIBERATELY LOUD. Mapping an unrecognised effort to `unknown`
            # would turn a value somebody actually reported into missing data,
            # which is rule 6 pointed the wrong way. `unknown` is what an
            # ABSENT value produces (the `value is None` branch above), and it
            # must stay the answer to one question only.
            raise ValueError(
                f"unrecognised reasoning_effort {value!r}. Add it to "
                f"_EFFORT_ALIASES, or to the bands in contract/conditions.yaml "
                f"if it is a new tier. Do not let it fall to 'unknown'."
            )
        return band

    raise ValueError(f"unknown condition dimension: {dimension!r}")


def bucket_for(capability_key: str, conditions_seen: dict[str, int | bool | None]) -> str:
    """Build the `condition_bucket` string for a capability.

    Format is `<dimension>:<band>` — e.g. `tool_count:6-15`.
    """
    dim = dominant_dimension()[capability_key]
    return f"{dim}:{band_for(dim, conditions_seen.get(dim))}"


@lru_cache(maxsize=1)
def job_about() -> dict[str, str]:
    """`contract/job_about.yaml`: slug -> what the job IS, hand-written.

    A slug with no entry has no lead line, and that is the intended state: the
    extractor's `definition` is a counting rule, not a description, and is never
    promoted into this role. The file itself must exist (`_read` raises), so a
    missing contract fails loudly instead of silently blanking every lead line.
    """
    return _about("job_about.yaml")


@lru_cache(maxsize=1)
def capability_about() -> dict[str, str]:
    """`contract/capability_about.yaml`: slug -> what the capability IS,
    hand-written, as `job_about` is for jobs.

    A slug with no entry keeps the extractor's `definition` as its page's
    definition - which for a capability is what it is meant to be - and simply
    has no longer description above it.
    """
    return _about("capability_about.yaml")


def _about(name: str) -> dict[str, str]:
    raw = _read(name) or {}
    about = raw.get("about") or {}
    if not isinstance(about, dict):
        raise ValueError(f"contract/{name}: `about` must map slug -> text")
    return {str(k).strip().lower(): " ".join(str(v).split()) for k, v in about.items() if v}


@lru_cache(maxsize=1)
def board_ordering_z() -> float:
    """`contract/board_ordering.yaml`'s `wilson_z`: the confidence level the
    board's first group is ordered by.

    NO DEFAULT. A missing or non-positive value raises rather than falling back
    to 1.96, because a fallback that succeeds would order every page by a
    number nobody chose and nothing on the page would say so (rule 12).
    """
    raw = _read("board_ordering.yaml")
    z = raw.get("wilson_z") if isinstance(raw, dict) else None
    if isinstance(z, bool) or not isinstance(z, (int, float)) or z <= 0:
        raise ValueError(
            f"contract/board_ordering.yaml: wilson_z must be a positive number, got {z!r}"
        )
    return float(z)


@lru_cache(maxsize=1)
def category_scores() -> dict:
    """`contract/category_scores.yaml`: the one visible score CLAUDE.md rule 3
    permits - its categories, which sections score, and the minimum.

    Returns {"min_sided_reports": int, "scored_sections": frozenset,
    "categories": [{"key", "name"}] in file order,
    "parent_to_category": {(section, parent): key}}.

    NO DEFAULTS, AND A PARENT IN TWO CATEGORIES IS REFUSED. A missing minimum
    would score one report as readily as fifty (rule 12); a parent filed twice
    would count one report in two categories and inflate both. A parent that is
    not a heading in contract/slug_parents.yaml is refused too: it would score
    nothing, silently, under a category that looks covered.
    """
    raw = _read("category_scores.yaml")
    if not isinstance(raw, dict):
        raise ValueError("contract/category_scores.yaml must be a mapping")
    minimum = raw.get("min_sided_reports")
    if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
        raise ValueError(
            "contract/category_scores.yaml: min_sided_reports must be a positive "
            f"integer, got {minimum!r}"
        )
    scored = raw.get("scored_sections")
    if not isinstance(scored, list) or not scored:
        raise ValueError("contract/category_scores.yaml: scored_sections must be a non-empty list")
    headings = {s: set(m.values()) for s, m in slug_parents().items()}
    cats, owner = [], {}
    for key, spec in (raw.get("categories") or {}).items():
        for section, names in ((spec or {}).get("parents") or {}).items():
            for p in names or []:
                if p not in headings.get(section, set()):
                    raise ValueError(
                        f"contract/category_scores.yaml: {key}: {p!r} is not a {section} "
                        "heading in contract/slug_parents.yaml"
                    )
                if (section, p) in owner:
                    raise ValueError(
                        f"contract/category_scores.yaml: {section}/{p} is in both "
                        f"{owner[(section, p)]!r} and {key!r}"
                    )
                owner[(section, p)] = str(key)
        cats.append({"key": str(key), "name": str((spec or {}).get("name") or key)})
    if not cats:
        raise ValueError("contract/category_scores.yaml: no categories")
    return {
        "min_sided_reports": minimum,
        "scored_sections": frozenset(scored),
        "categories": cats,
        "parent_to_category": owner,
    }


@lru_cache(maxsize=1)
def blog_live_settings() -> dict[str, dict[str, int]]:
    """`contract/blog_live.yaml`: the numbers the blog's live pages run on.

    NO DEFAULTS. Every key must be present and a positive whole number, or this
    raises - a quiz that quietly fell back to some length nobody chose would
    look exactly like one somebody did (rule 12)."""
    raw = _read("blog_live.yaml")
    need = {
        "quiz": ("general_per_day", "board_per_day", "options", "margin_percent", "gap_days"),
        "this_week": ("weeks_shown", "retiring_within_days", "models_listed"),
    }
    out: dict[str, dict[str, int]] = {}
    for part, keys in need.items():
        block = raw.get(part) if isinstance(raw, dict) else None
        if not isinstance(block, dict):
            raise ValueError(f"contract/blog_live.yaml: `{part}` is missing")
        out[part] = {}
        for key in keys:
            v = block.get(key)
            if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
                raise ValueError(
                    f"contract/blog_live.yaml: {part}.{key} must be a positive whole "
                    f"number, got {v!r}"
                )
            out[part][key] = v
    return out


@lru_cache(maxsize=1)
def quiz_drafter_settings() -> dict:
    """`contract/blog_live.yaml` `quiz_drafter`: which model drafts general quiz
    questions, how many per call, and on which topics. No defaults (rule 12)."""
    raw = _read("blog_live.yaml")
    block = raw.get("quiz_drafter") if isinstance(raw, dict) else None
    if not isinstance(block, dict):
        raise ValueError("contract/blog_live.yaml: `quiz_drafter` is missing")
    model, per_call, topics = block.get("model"), block.get("per_call"), block.get("topics")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("contract/blog_live.yaml: quiz_drafter.model must name a model")
    if isinstance(per_call, bool) or not isinstance(per_call, int) or not 1 <= per_call <= 20:
        raise ValueError("contract/blog_live.yaml: quiz_drafter.per_call must be 1 to 20")
    if (
        not isinstance(topics, list)
        or not topics
        or not all(isinstance(t, str) and t.strip() for t in topics)
    ):
        raise ValueError("contract/blog_live.yaml: quiz_drafter.topics must be a list of topics")
    return {"model": model.strip(), "per_call": per_call, "topics": [t.strip() for t in topics]}


def evidence_feed_settings() -> dict:
    """`contract/evidence_feed.yaml`: the feed's paraphraser, summariser and
    page size. Every key is required and checked; no defaults (rule 12)."""
    raw = _read("evidence_feed.yaml")
    if not isinstance(raw, dict):
        raise ValueError("contract/evidence_feed.yaml is not a mapping")

    def block(name: str) -> dict:
        b = raw.get(name)
        if not isinstance(b, dict):
            raise ValueError(f"contract/evidence_feed.yaml: `{name}` is missing")
        return b

    def text(b: dict, where: str, key: str) -> str:
        v = b.get(key)
        if not isinstance(v, str) or not v.strip():
            raise ValueError(
                f"contract/evidence_feed.yaml: {where}.{key} must be a non-empty string"
            )
        return v.strip()

    def count(b: dict, where: str, key: str, lo: int, hi: int) -> int:
        v = b.get(key)
        if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
            raise ValueError(f"contract/evidence_feed.yaml: {where}.{key} must be {lo} to {hi}")
        return v

    def effort(b: dict, where: str) -> str:
        v = text(b, where, "reasoning_effort").lower()
        if v not in ("none", "low", "medium", "high"):
            raise ValueError(f"contract/evidence_feed.yaml: {where}.reasoning_effort must be "
                             "none, low, medium or high")
        return v

    p, s, pg = block("paraphrase"), block("summary"), block("page")
    words = s.get("quantity_words")
    if not isinstance(words, list) or not all(isinstance(w, str) and w.strip() for w in words):
        raise ValueError(
            "contract/evidence_feed.yaml: summary.quantity_words must be a list of words"
        )
    return {
        "paraphrase": {
            "model": text(p, "paraphrase", "model"),
            "reasoning_effort": effort(p, "paraphrase"),
            "prompt_version": text(p, "paraphrase", "prompt_version"),
            "per_call": count(p, "paraphrase", "per_call", 1, 50),
            "max_chars": count(p, "paraphrase", "max_chars", 80, 1000),
            "max_copied_words": count(p, "paraphrase", "max_copied_words", 2, 20),
        },
        "summary": {
            "model": text(s, "summary", "model"),
            "reasoning_effort": effort(s, "summary"),
            "prompt_version": text(s, "summary", "prompt_version"),
            "max_reports": count(s, "summary", "max_reports", 5, 2000),
            "min_reports": count(s, "summary", "min_reports", 1, 100),
            "max_words": count(s, "summary", "max_words", 100, 2000),
            "max_paragraphs": count(s, "summary", "max_paragraphs", 1, 20),
            "attempts": count(s, "summary", "attempts", 1, 5),
            "max_copied_words": count(s, "summary", "max_copied_words", 2, 20),
            "quantity_words": [w.strip().lower() for w in words],
        },
        "page": {"per_page": count(pg, "page", "per_page", 5, 200)},
    }


@lru_cache(maxsize=1)
def blog_reference_settings() -> dict:
    """`contract/blog_live.yaml` `known_issues` and `answers`: the known-issues
    threshold and the person-ruled pairing of advertised features with board
    topics (rule 10). No defaults (rule 12)."""
    raw = _read("blog_live.yaml")
    issues = (raw or {}).get("known_issues") or {}
    n = issues.get("min_engineers")
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("contract/blog_live.yaml: known_issues.min_engineers must be 1 or more")
    feats = ((raw or {}).get("answers") or {}).get("features")
    if not isinstance(feats, list) or not feats:
        raise ValueError("contract/blog_live.yaml: answers.features must be a list")
    out = []
    for f in feats:
        key, label, slugs = f.get("key"), f.get("label"), f.get("board_slugs")
        if key not in ("tools", "structured_output", "reasoning", "vision_input", "prompt_caching"):
            raise ValueError(f"contract/blog_live.yaml: unknown feature {key!r}")
        if not isinstance(label, str) or not isinstance(slugs, list):
            raise ValueError(
                f"contract/blog_live.yaml: feature {key} needs a label and board_slugs"
            )
        out.append({"key": key, "label": label, "board_slugs": [str(x) for x in slugs]})
    return {"min_engineers": n, "features": out}


def _read(name: str) -> dict:
    path = CONTRACT_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"{path} is missing. contract/ is the shared interface — it should "
            "be present in every checkout."
        )
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def evidence_tier_rules() -> dict[str, str | dict[str, str]]:
    """`contract/harvest.yaml` -> the evidence-tier ladder.

    Two shapes, because two of the three `speaking` values have no rungs:

        {"relayed-from-elsewhere": "E"}                    a flat tier
        {"own-experience": {"repro_steps_and_numbers": "B",
                            "one_of_the_two": "C",
                            "neither": "D"}}               a sub-ladder

    Returns `{}` when the block is absent rather than raising, because the
    refusal belongs in `compute()` where the missing input can be named
    alongside anything else that is missing. A raise here would report one gap
    per round trip.

    RENAMED FROM `evidence_tier_by_speaking` 2026-08-30, and the name is the
    point: the old one described a key that was the whole defect. See the block
    in `harvest.yaml` - `speaking` answers WHOSE claim it is and `TIER_WEIGHT`
    grades HOW CHECKABLE it is, so keying one on the other put every first-hand
    report, harness or none, on the same rung.
    """
    block = _read("harvest.yaml").get("evidence_tier_rules") or {}
    return {
        key: value
        for key, value in block.items()
        if isinstance(value, (str, dict)) and not key.startswith("not_a_")
    }


@dataclass(frozen=True)
class TrackedModel:
    """One row of the registry page, and where its figures come from.

    `registry` is a `model_version.canonical_id` or None. NONE IS A
    MEASUREMENT, not a gap: the OpenRouter poll has run and this model is not in
    it. Six of these are image models, five video, four speech, and
    `model_version.price_in` is USD per 1M TOKENS - so there is no number that
    could fill those columns and be true. See the file's own header.
    """

    name: str
    registry: str | None
    kind: str
    absent_because: str | None = None
    #: True when the row came from `auto_track` (judge/tracked.py) rather than
    #: from a hand-written entry in `contract/tracked_models.yaml`.
    auto: bool = False


@lru_cache(maxsize=1)
def tracked_models() -> tuple[TrackedModel, ...]:
    """The models the registry PAGE shows, in the order it shows them.

    Distinct from what the registry HOLDS - `model_version` has 344 rows because
    a router carries 344 models, and a page that listed them all would answer
    "which models does this board have opinions about" with a catalogue.

    Ordered by the file, never sorted here: the first four are the ones a fetch
    has actually run against, and that is an editorial ordering the page should
    not silently rearrange.
    """
    raw = _read("tracked_models.yaml")
    return tuple(
        TrackedModel(
            name=e["name"],
            registry=e.get("registry") or None,
            kind=e.get("kind", "text"),
            absent_because=e.get("absent_because"),
        )
        for e in raw["models"]
    )


#: Keys a parent map may never carry. A parent that could express a voice count
#: would eventually publish one, and a count of voices under a heading nobody
#: wrote is a consensus about a category no writer named (#410, ruling 1).
@dataclass(frozen=True)
class AutoTrackRule:
    """`contract/tracked_models.yaml` `auto_track`. Read strictly (rule 12)."""

    enabled: bool
    released_within_days: int
    include_pro_tier: bool
    exclude_name_terms: tuple[str, ...]


class AutoTrackConfigError(RuntimeError):
    """`auto_track` is missing a key or carries a value of the wrong kind."""


@lru_cache(maxsize=1)
def auto_track_rule() -> AutoTrackRule:
    """The rule that admits new arrivals to the page. No default in code: a
    missing block or key raises, so the page never guesses what it admits."""
    raw = (_read("tracked_models.yaml") or {}).get("auto_track")
    if not isinstance(raw, dict):
        raise AutoTrackConfigError("contract/tracked_models.yaml has no `auto_track` block")

    def need(key, kind):
        v = raw.get(key)
        if not isinstance(v, kind) or (kind is int and isinstance(v, bool)):
            raise AutoTrackConfigError(
                f"contract/tracked_models.yaml `auto_track.{key}` must be "
                f"{kind.__name__}, not {v!r}")
        return v

    if raw.get("providers") != "from_tracked":
        raise AutoTrackConfigError(
            "`auto_track.providers` must be `from_tracked` - the only source of "
            f"providers this rule knows; got {raw.get('providers')!r}")
    days = need("released_within_days", int)
    if days < 1:
        raise AutoTrackConfigError("`auto_track.released_within_days` must be at least 1")
    terms = need("exclude_name_terms", list)
    return AutoTrackRule(
        enabled=need("enabled", bool),
        released_within_days=days,
        include_pro_tier=need("include_pro_tier", bool),
        exclude_name_terms=tuple(str(t).strip().lower() for t in terms),
    )


#: The ceiling on headings per board section (2026-10-14). Kept in code, not the
#: contract, because it is a limit ON the contract: a file that could raise its
#: own ceiling would not have one.
MAX_PARENTS_PER_SECTION = 10

_PARENT_FORBIDDEN_KEYS = ("voices", "n_eff", "weight", "score", "consensus")


@lru_cache(maxsize=1)
def parent_names() -> dict[str, str]:
    """`contract/slug_parents.yaml` -> {parent_slug: display heading}.

    A parent with no entry here is NOT an error: `parent_heading()` falls back
    to the slug so a newly added parent renders rather than crashing a page.
    The contract is expected to be complete and a test asserts it is — the code
    is permissive so a missing name is a cosmetic gap, not an outage.
    """
    return {
        str(k).strip().lower(): str(v)
        for k, v in (_read("slug_parents.yaml").get("parent_names") or {}).items()
    }


def parent_heading(parent: str) -> str:
    """The heading a reader sees, or the slug when nobody has written one.

    Every LEAF has a display name because the extractor is required to produce
    one. Parents are written by hand, so this is the one place a heading can be
    missing, and falling back to the slug keeps the page rendering.
    """
    return parent_names().get((parent or "").strip().lower()) or parent


@lru_cache(maxsize=1)
def slug_parents() -> dict[str, dict[str, str]]:
    """`contract/slug_parents.yaml` -> {section: {leaf_slug: parent}}.

    Inverted from the file's {section: {parent: [leaf, ...]}} because every
    reader asks "what is this leaf's heading", never "what is under this
    heading" — the second is a `groupby` over the first and inverting once here
    keeps one direction authoritative.

    ⚠ READ-TIME NAVIGATION ONLY. This is NOT `capabilities()`. That is the
      closed 12-key counting vocabulary: it keys `cell`, it drives `n_eff`, and
      `judge/pages/capability.py` refuses a key it does not contain. This keys
      nothing, and a leaf absent from it is UNGROUPED rather than invalid —
      absence is the default (rule 6), which is why this returns a mapping to
      look up rather than a list to validate against.

    `best_for` is deliberately absent from the file; this returns whatever
    sections it declares, so a caller must handle a section with no parents.
    """
    raw = _read("slug_parents.yaml")
    forbidden = {str(n).strip().lower() for n in raw.get("forbidden_parents") or ()}
    out: dict[str, dict[str, str]] = {}
    for section, parents in (raw.get("sections") or {}).items():
        mapping: dict[str, str] = {}
        for parent, leaves in (parents or {}).items():
            name = str(parent).strip().lower()
            if name in forbidden:
                raise ValueError(
                    f"slug_parents.yaml: {name!r} is in `forbidden_parents`. A "
                    "parent wide enough to take anything takes everything — "
                    "`extraction.faithfulness` absorbed 12 facial-recognition "
                    "claims without one candidate proposal."
                )
            for leaf in leaves or ():
                leaf = str(leaf).strip().lower()
                if leaf in mapping:
                    raise ValueError(
                        f"slug_parents.yaml: {leaf!r} is under both "
                        f"{mapping[leaf]!r} and {name!r} in {section!r}. A leaf "
                        "under two parents is counted twice by any reader that "
                        "walks the map."
                    )
                mapping[leaf] = name
        if len(set(mapping.values())) > MAX_PARENTS_PER_SECTION:
            raise ValueError(
                f"slug_parents.yaml: {section!r} has {len(set(mapping.values()))} "
                f"parents; the ceiling is {MAX_PARENTS_PER_SECTION}. The Board shows "
                "each heading as a box to choose from, and a page of boxes a reader "
                "cannot scan is the long list again."
            )
        out[str(section)] = mapping
    return out
