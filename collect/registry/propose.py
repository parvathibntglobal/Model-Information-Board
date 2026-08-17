"""Propose alias surfaces for review. Deterministic, and it never decides.

TWO INPUTS, NOT ONE
-------------------
    MECHANICAL   spacing, hyphenation and concatenation of the canonical id and
                 the feed's `name`. Derivable, so it is coverage.
    ATTESTED     surfaces observed in stored documents, with counts. Measured, so
                 it is recall.

`alias_rows` asks a human for the prose forms a model is discussed under —
`opus 5`, `opus5`, the bare `opus`. That was judgement supplied from imagination
because there was no corpus to check against. There is one now, and the two
inputs answer different questions: mechanical says what a machine can reach,
attested says what people actually type.

WHAT IS DELIBERATELY LEFT EMPTY, AND WHY THAT IS THE POINT
----------------------------------------------------------
Engineer 2's addition: **a generated list that looks complete is worse than a
short one known to be short.** Same argument as `phrase_present = None` versus 0.

So a slot with no evidence is marked `INCOMPLETE` rather than filled with a
plausible guess. A reviewer sees three things separately — what is derivable, what
is attested, and what is missing — and the third is the one that needs a person.

The family surface is the standing example. `opus` for `anthropic/claude-opus-5`
cannot be derived, because dropping the vendor word is judgement, and it cannot be
taken from the corpus either: 62% of family-word mentions carry no version at all,
so `opus` is attested constantly and attributable to no single model. It is
therefore always `INCOMPLETE` and never proposed.

MEASURED, SO THE DEFAULTS ARE NOT INVENTED
-------------------------------------------
Over 5,546 stored documents and the 340-model registry:

    distinct surfaces per discussed model   min 1, median 2, mean 2.01, max 4
    models reaching 3 surfaces              17 of 72
    models appearing under exactly one      18 of 72

The eleven hand-curated models carry **5.5 surfaces each**, written before there
was a corpus. That is about 2.75x what the corpus attests, and
`check_spelling_coverage`'s floor of three is unmet by 55 of the 72 models anyone
actually discusses. Both are flagged on #33 rather than changed here — the floor
is contract, and this module only proposes.

NO MODEL PARTICIPATES. String transformations and counted observations. A human
accepts or rejects per model. Propose, never decide.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

#: A slot with no evidence carries this rather than a guess.
INCOMPLETE = "INCOMPLETE"

#: Family words that name a line rather than a tier. Never proposed as a surface:
#: `classify_specificity` would rank them `family`, and a family-specificity claim
#: never counts as independent corroboration — so proposing one would add a
#: surface that can record a claim and cannot lift a cell.
FAMILY_WORDS = frozenset({
    "opus", "sonnet", "haiku", "claude", "gemini", "gpt", "chatgpt", "qwen",
    "llama", "mistral", "mixtral", "deepseek", "grok", "codex", "kimi", "glm",
    "nova", "phi", "command", "flash", "pro", "mini", "turbo", "air", "plus",
})

#: Shorter than this and a surface collides with ordinary words.
MIN_SURFACE_CHARS = 4


def _clean(text: str) -> str:
    """Casefold and regularise separators. A DISPLAY form, not a matching key.

    Neither existing normaliser fits, and both alternatives were tried:

    `sieve.normalize` is the right shape and importing it breaks FR-5's
    structural half — `tests/test_lane_boundary.py` refuses any import from
    `collect.adapters` into `collect/registry/`, because the registry must not be
    able to SEE harvest. That test caught this, and the boundary wins over
    sharing.

    `registry.aliases.normalize` is in-lane and strips every non-alphanumeric, so
    `gemini-3-pro` becomes `gemini3pro`. That is a matching key by design and it
    destroys the spacing this function exists to produce.

    So the operation is genuinely different from both rather than a third copy of
    either: lowercase, separators to spaces, whitespace collapsed, nothing removed.
    """
    lowered = text.casefold().replace("-", " ").replace("_", " ")
    return re.sub(r"\s+", " ", lowered).strip()


def mechanical_variants(canonical_id: str, display_name: str | None = None) -> list[str]:
    """Forms a machine can derive. No judgement, so no INCOMPLETE.

    Spacing, hyphenation and concatenation of the id's local part and of the
    feed's `name` with its vendor prefix removed — `Google: Gemini 3 Pro` gives
    `gemini 3 pro`, `gemini-3-pro`, `gemini3pro`.

    A bare family word is never returned even if the id is one: see FAMILY_WORDS.
    """
    seeds = {canonical_id.split("/", 1)[-1]}
    if display_name:
        seeds.add(display_name.split(":", 1)[-1])

    out: set[str] = set()
    for seed in seeds:
        spaced = _clean(seed)
        if not spaced:
            continue
        for form in (spaced, spaced.replace(" ", "-"), spaced.replace(" ", "")):
            if len(form) < MIN_SURFACE_CHARS:
                continue
            if form in FAMILY_WORDS:
                continue
            out.add(form)
    return sorted(out)


@dataclass(frozen=True)
class Attested:
    """One observed surface and how often it appeared."""

    surface: str
    mentions: int
    documents: int = 0


@dataclass
class AliasProposal:
    """One model's proposal, with the three categories kept apart.

    `surface` is the primary form. It is the most-mentioned ATTESTED surface where
    there is one, because that is what people actually type — and INCOMPLETE
    where there is not, rather than the first mechanical form dressed up as a
    choice.
    """

    canonical_id: str
    mechanical: list[str] = field(default_factory=list)
    attested: list[Attested] = field(default_factory=list)
    #: Slots a person has to fill. Named, so the gap is legible.
    incomplete: list[str] = field(default_factory=list)

    @property
    def surface(self) -> str:
        if self.attested:
            return self.attested[0].surface
        return INCOMPLETE

    @property
    def variants(self) -> list[str]:
        """Everything proposed, attested first, without the primary."""
        seen = {self.surface}
        out = []
        for a in self.attested:
            if a.surface not in seen:
                seen.add(a.surface)
                out.append(a.surface)
        for m in self.mechanical:
            if m not in seen:
                seen.add(m)
                out.append(m)
        return out

    @property
    def status(self) -> str:
        """What a reviewer needs to know before reading the row.

        `attested` — the corpus has seen this model named; the primary is real.
        `mechanical-only` — derivable forms only. Nobody in the corpus has been
        observed writing this model's name, so recall is unmeasured, not zero.
        """
        return "attested" if self.attested else "mechanical-only"

    @property
    def total_mentions(self) -> int:
        return sum(a.mentions for a in self.attested)


def propose(
    models,
    observed: dict[str, list[Attested]] | None = None,
) -> list[AliasProposal]:
    """One proposal per model. `models` is (canonical_id, display_name) pairs.

    `observed` maps canonical_id to attested surfaces. Absent means unmeasured,
    which is recorded as such — an empty attested list produces
    `mechanical-only`, never a claim that the model is undiscussed.
    """
    observed = observed or {}
    out = []
    for canonical_id, display_name in models:
        attested = sorted(
            observed.get(canonical_id, []), key=lambda a: (-a.mentions, a.surface)
        )
        mechanical = mechanical_variants(canonical_id, display_name)

        incomplete = ["family_surface"]  # always: see the module docstring
        if not attested:
            incomplete.append("attested_surfaces")
        if not mechanical:
            incomplete.append("mechanical_variants")

        out.append(AliasProposal(
            canonical_id=canonical_id,
            mechanical=mechanical,
            attested=attested,
            incomplete=incomplete,
        ))
    return sorted(out, key=lambda p: (-p.total_mentions, p.canonical_id))


def to_yaml(proposals) -> str:
    """A reviewable skeleton. NOT loadable as a finished alias list.

    Deliberately not valid input to `load_seed_file`: every proposal carries an
    `INCOMPLETE` marker for the family surface, so a reviewer has to touch each
    entry rather than piping this into the contract. A generated list that could
    be merged unread is the failure this format exists to prevent.
    """
    lines = [
        "# PROPOSED alias surfaces — review required, not loadable as-is.",
        "#",
        "# Two inputs, kept apart on purpose:",
        "#   attested    observed in stored documents, with mention counts. Recall.",
        "#   mechanical  derived from the canonical id and the feed's name. Coverage.",
        "#",
        "# Every entry has at least one INCOMPLETE slot. `family_surface` cannot be",
        "# derived (dropping the vendor word is judgement) and cannot be taken from",
        "# the corpus either: 62% of family-word mentions carry no version, so a bare",
        "# family word is attested constantly and attributable to no single model.",
        "#",
        "# Accept or reject per model. Nothing here decides anything.",
        "",
        "proposals:",
    ]
    for p in proposals:
        lines.append(f"  - canonical_id: {p.canonical_id}")
        lines.append(f"    status: {p.status}")
        if p.attested:
            lines.append(f"    surface: {p.surface}        # attested "
                         f"{p.attested[0].mentions} mentions")
        else:
            lines.append(f"    surface: {INCOMPLETE}   # no attested surface; "
                         "recall is unmeasured, not zero")
        lines.append("    variants:")
        for variant in p.variants:
            hit = next((a for a in p.attested if a.surface == variant), None)
            note = (f"# attested {hit.mentions} mentions" if hit
                    else "# mechanical, unattested")
            lines.append(f"      - {variant}".ljust(38) + note)
        if not p.variants:
            lines.append(f"      # {INCOMPLETE}: no variants derivable or attested")
        lines.append(f"    incomplete: [{', '.join(p.incomplete)}]")
        lines.append("")
    return "\n".join(lines)


def summarise(proposals) -> str:
    """Counts a reviewer sees before opening the file."""
    total = len(proposals)
    attested = sum(1 for p in proposals if p.status == "attested")
    sizes = sorted(len(p.attested) for p in proposals if p.attested)
    median = sizes[len(sizes) // 2] if sizes else 0
    return (
        f"{total} models: {attested} attested, {total - attested} mechanical-only. "
        f"Attested surfaces per discussed model: median {median}, "
        f"max {sizes[-1] if sizes else 0}. "
        f"Every entry has an INCOMPLETE family_surface slot."
    )
