"""Propose alias surfaces for review. Deterministic, and it never decides.

THREE INPUTS, NOT ONE
---------------------
    MECHANICAL       spacing, hyphenation and concatenation of the canonical id
                     and the feed's `name`. Derivable, so it is coverage.
    ATTESTED         surfaces observed in stored documents, with counts.
                     Measured, so it is recall.
    ATTESTED-BY-RULE the vendor word dropped from the id, then rendered the three
                     mechanical ways: `claude-opus-5` -> `opus-5` -> `opus 5`.
                     Derived from a rule the corpus measured, so it is neither
                     observation nor judgement.

`alias_rows` asks a human for the prose forms a model is discussed under —
`opus 5`, `opus5`, the bare `opus`. That was judgement supplied from imagination
because there was no corpus to check against. There is one now, and the three
inputs answer different questions: mechanical says what a machine can reach,
attested says what people actually type, and by-rule says what follows from what
people were observed typing.

WHY THE THIRD IS NOT FOLDED INTO EITHER OF THE OTHER TWO
--------------------------------------------------------
`attested-gap` is the largest verdict by mentions in the surface extract — 4,556
mentions over 62 surfaces, models the registry already holds under forms no
derivation reached — and it is **one rule**: people drop the vendor word.
`opus 5`, not `claude opus 5`.

That was judgement while we were guessing at usage. The corpus makes it
mechanical, so it moves out of the reviewer's hands and into this module. It
still does not become ATTESTED: `opus 4.6` observed 398 times is a fact about
that model, and `fable-5` -> `fable 5` is a fact about the rule. Merging them
would let a derivation be read off a table as a measurement, which is the
mistake `status` and the INCOMPLETE slots exist to prevent. Kept apart, a
surface that is BOTH is the interesting row: it is the rule being corroborated
where the corpus can see it.

The rule fires narrowly, and where it does not fire that is a refusal to derive
rather than a claim that no such form exists — see `rule_variants`.

WHAT IS DELIBERATELY LEFT EMPTY, AND WHY THAT IS THE POINT
----------------------------------------------------------
Engineer 2's addition: **a generated list that looks complete is worse than a
short one known to be short.** Same argument as `phrase_present = None` versus 0.

So a slot with no evidence is marked `INCOMPLETE` rather than filled with a
plausible guess. A reviewer sees three things separately — what is derivable, what
is attested, and what is missing — and the third is the one that needs a person.

The family surface is the standing example, and the vendor-drop rule does NOT
reach it. `opus 5` keeps the version token; `opus` drops it. That is the whole
difference, and it is the difference between a surface that names a tier and one
that names a line: 62% of family-word mentions carry no version at all, so `opus`
is attested constantly and attributable to no single model. It is therefore always
`INCOMPLETE` and never proposed — by any of the three inputs.

MEASURED, SO THE DEFAULTS ARE NOT INVENTED
-------------------------------------------
Over 5,546 stored documents and the 340-model registry:

    distinct surfaces per discussed model   min 1, median 2, mean 2.01, max 4
    models reaching 3 surfaces              17 of 72
    models appearing under exactly one      18 of 72

The eleven hand-curated models carry **5.5 surfaces each**, written before there
was a corpus — about 2.75x what the corpus attests.

Read as a statement about usage, `check_spelling_coverage`'s floor of three looks
unmet by 55 of those 72 models. **#33 is ruled: the floor stays at three and it
keeps counting renderings, never attestations** — so that reading is not what the
gate measures, and a floor that did count attested surfaces would fail 55 models
whose only remedy is inventing spellings. The reasoning is with the check, in
`collect/registry/aliases.py`. What matters here is that nothing this module
proposes is required by that gate, and that the `family_surface` slot stays
INCOMPLETE-able rather than becoming a condition of load.

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
    "opus", "sonnet", "haiku", "fable", "claude", "gemini", "gpt", "chatgpt",
    "qwen", "llama", "mistral", "mixtral", "deepseek", "grok", "codex", "kimi",
    "glm", "nova", "phi", "command", "flash", "pro", "mini", "turbo", "air",
    "plus",
})

#: Shorter than this and a surface collides with ordinary words.
MIN_SURFACE_CHARS = 4

#: The name of the one transformation the corpus has supplied, carried into the
#: output so a reviewer reads a derivation and not an observation.
VENDOR_DROP = "vendor-drop"

_DIGIT = re.compile(r"\d")

#: Six or more consecutive digits is a date stamp, not a version. `opus 5` is a
#: form people write; `haiku 4 5 20251001` is not — 18 of 10,255 attested
#: mentions carry a date-shaped token at all, and one of those is Anthropic's
#: shape. So the rule stops at the snapshot id rather than deriving from it.
_DATE_STAMP = re.compile(r"\d{6,}")

#: A version-preserving token: letters, digits and the dot in `4.5`. Anything
#: else in a surface came from the feed's punctuation rather than from a name.
_PLAIN_TOKEN = re.compile(r"[0-9a-z.]+")


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
        if spaced:
            out.update(_renderings(spaced))
    return sorted(out)


def _renderings(spaced: str) -> list[str]:
    """One spaced form as the three renderings a search API cannot bridge."""
    return [
        form
        for form in (spaced, spaced.replace(" ", "-"), spaced.replace(" ", ""))
        if len(form) >= MIN_SURFACE_CHARS and form not in FAMILY_WORDS
    ]


def rule_variants(canonical_id: str, display_name: str | None = None) -> list[str]:
    """The vendor word dropped, then rendered three ways. Derived, not observed.

    `claude-opus-5` -> `opus-5` -> `opus 5`. The corpus measured that rule — the
    largest `attested-gap` surfaces are `opus 5` (1,445), `sonnet 4.5` (416),
    `opus 4.6` (398), `haiku 4.5` (83) — so applying it is arithmetic on an
    observation rather than a guess about usage.

    SIX GUARDS, AND EACH ONE IS A PLACE THE RULE STOPS BEING MECHANICAL:

    1. the dropped token is the vendor or family word — the id's namespace, or a
       member of FAMILY_WORDS. Dropping anything else is not this rule.
    2. what remains still OPENS with a family word. `gemini-2.5-flash` would leave
       `2.5 flash`, and the form people actually write is `flash 2.5` — a
       reordering, which is judgement and not a rendering.
    3. what remains still carries a version token. Without one the output is the
       bare family surface, which stays INCOMPLETE forever (see the module
       docstring) rather than arriving through a side door.
    4. no date-stamped remainder: see `_DATE_STAMP`.
    5. no OpenRouter route suffix. `anthropic/claude-opus-5:batch` would derive
       `opus 5:batch`, which nobody writes — and stripping the suffix instead would
       derive `opus 5` for two canonical ids with overlapping validity windows,
       which is exactly the ambiguity `AliasCollisionError` refuses at load. How a
       route gets aliased is a decision, so it stays with the reviewer.
       `mechanical_variants` keeps the suffix rather than refusing, and those forms
       cannot collide because they differ per route.
    6. every remaining token is alphanumeric. The feed's `name` is the other seed
       here, and `Anthropic: Claude Opus 5 (batch)` would otherwise slip a route
       suffix back in past guard 5 in different punctuation.

    Where a guard refuses, this returns nothing — and **nothing is not a claim
    that no vendor-dropped form exists.** `mistralai/mistral-large-3` almost
    certainly has one; `large` is not a family word, so deriving `large 3` here
    would be inventing the tier vocabulary the corpus has not supplied. The
    reviewer sees the same INCOMPLETE slots either way, which is the difference
    between a gap and a silence.
    """
    vendor = canonical_id.split("/", 1)[0].casefold() if "/" in canonical_id else ""
    local_part = canonical_id.split("/", 1)[-1]
    # Guard 5, applied to the MODEL and not to one seed: a routed id refuses
    # both seeds, or the display name would derive what the id was refused.
    if ":" in local_part:
        return []

    seeds = {local_part}
    if display_name:
        seeds.add(display_name.split(":", 1)[-1])

    out: set[str] = set()
    for seed in seeds:
        tokens = _clean(seed).split()
        # Two tokens leave one after the drop: a bare family word, or a bare
        # version. Neither is a surface.
        if len(tokens) < 3:
            continue
        head, rest = tokens[0], tokens[1:]
        if head not in FAMILY_WORDS and head != vendor:
            continue
        if rest[0] not in FAMILY_WORDS:
            continue
        if not all(_PLAIN_TOKEN.fullmatch(token) for token in rest):
            continue
        spaced = " ".join(rest)
        if not _DIGIT.search(spaced) or _DATE_STAMP.search(spaced):
            continue
        out.update(_renderings(spaced))
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
    choice. A by-rule surface never becomes the primary either: the rule says what
    follows from usage elsewhere, not that this model was seen written that way.
    """

    canonical_id: str
    mechanical: list[str] = field(default_factory=list)
    attested: list[Attested] = field(default_factory=list)
    #: Vendor-drop renderings. Derived from an observed rule, so they sit between
    #: the other two and are labelled as neither.
    by_rule: list[str] = field(default_factory=list)
    #: Slots a person has to fill. Named, so the gap is legible.
    incomplete: list[str] = field(default_factory=list)

    @property
    def surface(self) -> str:
        if self.attested:
            return self.attested[0].surface
        return INCOMPLETE

    @property
    def variants(self) -> list[str]:
        """Everything proposed, without the primary.

        Ordered observed, then derived-from-observed, then derivable — which is
        the order of how much the corpus has to say about each.
        """
        seen = {self.surface}
        out = []
        for candidate in (
            [a.surface for a in self.attested] + self.by_rule + self.mechanical
        ):
            if candidate not in seen:
                seen.add(candidate)
                out.append(candidate)
        return out

    @property
    def corroborated_by_rule(self) -> list[str]:
        """Surfaces the rule derives AND the corpus attests.

        The rule's own evidence, per model. `opus 5` is here for
        `anthropic/claude-opus-5`, at 1,445 mentions.
        """
        attested = {a.surface for a in self.attested}
        return [surface for surface in self.by_rule if surface in attested]

    @property
    def status(self) -> str:
        """What a reviewer needs to know before reading the row.

        `attested` — the corpus has seen this model named; the primary is real.
        `mechanical-only` — derivable forms only, whether by rendering or by rule.
        Nobody in the corpus has been observed writing this model's name, so recall
        is unmeasured, not zero.

        A by-rule surface deliberately does not move a model out of
        `mechanical-only`. Two derivations are still no observation, and a status
        that improved on one would be reporting the rule's confidence as the
        model's evidence.
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
        by_rule = rule_variants(canonical_id, display_name)

        incomplete = ["family_surface"]  # always: see the module docstring
        if not attested:
            incomplete.append("attested_surfaces")
        if not mechanical:
            incomplete.append("mechanical_variants")
        # A rule that did not fire is deliberately NOT a slot. `rule_variants`
        # refuses rather than guesses, and a reviewer given an empty
        # `vendor_drop` slot on every Google id would learn nothing from it that
        # `family_surface` does not already say.

        out.append(AliasProposal(
            canonical_id=canonical_id,
            mechanical=mechanical,
            attested=attested,
            by_rule=by_rule,
            incomplete=incomplete,
        ))
    return sorted(out, key=lambda p: (-p.total_mentions, p.canonical_id))


def to_yaml(proposals, seated_by: dict[str, str] | None = None) -> str:
    """A reviewable skeleton. NOT loadable as a finished alias list.

    Deliberately not valid input to `load_seed_file`: every proposal carries an
    `INCOMPLETE` marker for the family surface, so a reviewer has to touch each
    entry rather than piping this into the contract. A generated list that could
    be merged unread is the failure this format exists to prevent.

    `seated_by` maps a canonical id to why the tracked set holds it — `attested`
    or `launch-window` (`collect/registry/tracked.py`). Recorded per entry
    because it changes what a reviewer can do with the row: a model seated by
    the launch window has no attested surface to confirm, so every surface under
    it is a derivation, and the reviewer is supplying the judgement rather than
    checking one. Omitted where the proposal was not cut to a tracked set.
    """
    lines = [
        "# PROPOSED alias surfaces — review required, not loadable as-is.",
        "#",
        "# Three inputs, kept apart on purpose:",
        "#   attested     observed in stored documents, with mention counts. Recall.",
        "#   by rule      the vendor word dropped from the id, rendered three ways.",
        "#                Derived from a rule the corpus measured — `opus 5` over",
        "#                `claude opus 5`, 4,556 mentions of that shape — so it is",
        "#                not judgement, and it is not an observation of THIS model.",
        "#   mechanical   derived from the canonical id and the feed's name. Coverage.",
        "#",
        "# Every entry has at least one INCOMPLETE slot. `family_surface` cannot be",
        "# derived: the vendor-drop rule keeps the version token and a family surface",
        "# drops it. Nor can it be taken from the corpus — 62% of family-word mentions",
        "# carry no version, so a bare family word is attested constantly and",
        "# attributable to no single model.",
        "#",
        "# Accept or reject per model. Nothing here decides anything.",
        "",
        "proposals:",
    ]
    for p in proposals:
        lines.append(f"  - canonical_id: {p.canonical_id}")
        lines.append(f"    status: {p.status}")
        if seated_by and p.canonical_id in seated_by:
            ground = seated_by[p.canonical_id]
            note = (
                "# the corpus attests this model"
                if ground == "attested"
                else "# released inside the launch window; no attested surface, "
                "so every form below is derived"
            )
            lines.append(f"    seated_by: {ground}".ljust(38) + note)
        if p.attested:
            note = f"# attested {p.attested[0].mentions} mentions"
            if p.surface in p.by_rule:
                note += f"; also derived by {VENDOR_DROP}"
            lines.append(f"    surface: {p.surface}        {note}")
        else:
            lines.append(f"    surface: {INCOMPLETE}   # no attested surface; "
                         "recall is unmeasured, not zero")
        lines.append("    variants:")
        for variant in p.variants:
            hit = next((a for a in p.attested if a.surface == variant), None)
            if hit:
                note = f"# attested {hit.mentions} mentions"
                # An attested surface the rule also derives is the rule's own
                # evidence. Said on the line rather than in a summary, because
                # this is where a reviewer decides whether to trust it.
                if variant in p.by_rule:
                    note += f"; also derived by {VENDOR_DROP}"
            elif variant in p.by_rule:
                note = f"# by rule ({VENDOR_DROP}), unattested"
            else:
                note = "# mechanical, unattested"
            lines.append(f"      - {variant}".ljust(38) + note)
        if not p.variants:
            lines.append(f"      # {INCOMPLETE}: no variants derivable or attested")
        lines.append(f"    incomplete: [{', '.join(p.incomplete)}]")
        lines.append("")
    return "\n".join(lines)


def summarise(proposals) -> str:
    """Counts a reviewer sees before opening the file.

    Where nothing is attested the surface count is **not measured**, and it says
    so. `median 0, max 0` is the same table cell as a model measured at zero, and
    the two are not the same fact — the detector's blind spots (letter-prefixed
    versions like `deepseek r1`) live entirely inside the first one.
    """
    total = len(proposals)
    attested = sum(1 for p in proposals if p.status == "attested")
    by_rule = sum(1 for p in proposals if p.by_rule)
    corroborated = sum(1 for p in proposals if p.corroborated_by_rule)
    sizes = sorted(len(p.attested) for p in proposals if p.attested)
    spread = (
        f"median {sizes[len(sizes) // 2]}, max {sizes[-1]}" if sizes else "not measured"
    )
    return (
        f"{total} models: {attested} attested, {total - attested} mechanical-only. "
        f"Attested surfaces per discussed model: {spread}. "
        f"{by_rule} carry a {VENDOR_DROP} surface, {corroborated} of those "
        f"corroborated by attestation. "
        f"Every entry has an INCOMPLETE family_surface slot."
    )
