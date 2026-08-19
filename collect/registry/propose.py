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


#: Id namespaces that denote a ROUTE rather than a model.
#:
#: `openrouter/auto` picks whatever is cheapest at request time and
#: `~vendor/model-latest` points at whatever the vendor currently ships. Ruled
#: 2026-08-18: **routes are not models.**
#:
#: The reason is FR-4 rather than tidiness. A claim about `free` resolves to a
#: pointer, and the model that actually served the request is unknown — so the
#: mention is unattributable BY CONSTRUCTION, not merely unattributed. FR-4
#: exists so a mention resolves to what existed when it was written, and a
#: pointer has no such thing.
#:
#: It was also producing false entity matches: `openrouter/free` and
#: `openrouter/auto` derive the surfaces `free` and `auto`, which are ordinary
#: English words. Measured on a non-technical control, excluding these 17 ids
#: takes survival from 1.3% to 0.0%.
ROUTE_NAMESPACES = ("openrouter/",)
ROUTE_PREFIX = "~"


def is_route(canonical_id: str) -> bool:
    """Does this id denote a route rather than a model?

    Two shapes, both structural rather than a judgement about the name:
    the `~` prefix the feed uses for floating pointers, and the `openrouter/`
    namespace, whose entries are the router's own endpoints rather than models
    it routes to.
    """
    lowered = canonical_id.casefold()
    return lowered.startswith(ROUTE_PREFIX) or lowered.startswith(ROUTE_NAMESPACES)


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

    #: WHICH SWEEPS THE COUNT CAME FROM, and it is not decoration.
    #:
    #: `mentions` is a SUM across `substitution-slice`, `reddit-sweep` and
    #: `reddit-comments`, and the extract has always carried the split while the
    #: artifact printed only the total. That is rule 7 in the one file the seats
    #: are read from: `sonnet 4.5` at 416 is **393 slice, 21 sweep, 2 comments**,
    #: and a reviewer confirming that seat off `416` cannot see that it is
    #: overwhelmingly a slice measurement.
    #:
    #: Empty when the extract row carried no `by_source` key - absent, not zero
    #: (rule 6), and `to_yaml` says "split unrecorded" rather than printing a
    #: fabricated 100%.
    by_source: dict[str, int] = field(default_factory=dict)


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


#: The header block explaining the split, so a reader of the artifact does not
#: have to find this module to learn what `[slice 393, sweep 21]` means.
HEADER_SOURCE_SPLIT = """# EVERY MENTION COUNT IS A SUM, AND THE SPLIT IS NOW BESIDE IT.
#   [slice N, sweep N, comments N]  substitution-slice / reddit-sweep /
#                                   reddit-comments, descending
# Rule 7 in the file the seats are read from. The extract has always carried
# this split and this file used to print only the total, so a reviewer could not
# tell a corpus figure from a slice figure. `sonnet 4.5` reads 416 mentions and
# 393 of them are substitution-slice; `opus 5` reads 1445 and 1092 are the sweep.
# Those two seats are supported by different populations and looked identical.
# `split unrecorded` means the extract row had no by_source key - absent, not
# zero.
#"""


#: Short names for the sweeps, so the split fits on the line it annotates.
#: Spelled out here rather than abbreviated silently, because a reader who does
#: not know what `sl` is cannot check the figure.
_SOURCE_ABBREV = {
    "substitution-slice": "slice",
    "reddit-sweep": "sweep",
    "reddit-comments": "comments",
}


def source_split(attested: Attested) -> str:
    """`mentions` broken down by sweep, for the annotation on a surface line.

    **THIS IS RULE 7 IN THE FILE THE SEATS ARE READ FROM.** `mentions` is a sum
    across three sweeps and the artifact printed only the total, so a reviewer
    confirming a seat could not tell a corpus figure from a slice figure. The
    case that shows why: `sonnet 4.5` reads `416 mentions`, of which 393 are
    substitution-slice - 94% of that one surface, and 92% across the model's two
    attested forms.

    Absent rather than assumed when the extract carried no `by_source`: the
    string says so instead of implying the total came from one sweep (rule 6).
    """
    if not attested.by_source:
        return "split unrecorded"
    ordered = sorted(attested.by_source.items(), key=lambda kv: (-kv[1], kv[0]))
    parts = [f"{_SOURCE_ABBREV.get(name, name)} {count}" for name, count in ordered]
    rendered = ", ".join(parts)
    total = sum(attested.by_source.values())
    if total != attested.mentions:
        # The split must reconcile with the figure it explains, or it is a second
        # unverified number rather than a denominator.
        rendered += f" (!! sums to {total}, not {attested.mentions})"
    return rendered


def to_yaml(
    proposals,
    seated_by: dict[str, str] | None = None,
    policy: object | None = None,
) -> str:
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
        *HEADER_SOURCE_SPLIT.splitlines(),
        "# Accept or reject per model. Nothing here decides anything.",
        "",
    ]
    # RULE 7 AT THE TOP OF THE FILE. Without the floor, `seated_by:
    # launch-window` is unreadable: it could mean "nothing observed" or "observed
    # below the floor", and those need different actions. A reader could not tell
    # them apart, and neither could a check — the first version of the seating
    # check read every launch-window row with any mentions as an error, which is
    # 5 of 23 rows that are seated exactly as the policy intends.
    if policy is not None:
        lines += [
            "# THE THRESHOLDS THESE SEATS WERE CUT WITH. A seat is not readable"
            " without them.",
            "policy:",
            f"  mention_floor: {getattr(policy, 'mention_floor', 'unrecorded')}"
            "        # at or above this, a model is seated by count",
            f"  launch_window_days: {getattr(policy, 'launch_window_days', 'unrecorded')}"
            "   # inside this, seated regardless of count",
            "",
        ]
    lines += [
        "proposals:",
    ]
    for p in proposals:
        lines.append(f"  - canonical_id: {p.canonical_id}")
        lines.append(f"    status: {p.status}")
        if seated_by and p.canonical_id in seated_by:
            ground = seated_by[p.canonical_id]
            # THREE CASES, NOT TWO. `launch-window` means "did not clear the
            # mention floor" — `cli.py` sets it whenever `BY_MENTIONS` is absent
            # — and that is NOT the same as "nothing was observed". A model with
            # 13 mentions against a floor of 20 is seated by the window and is
            # attested, so the two-case version asserted "no attested surface"
            # on a row whose very next line read `attested 13 mentions`. False
            # on 5 of 23 launch-window entries, and rule 4 exactly: an absence
            # claimed where evidence exists.
            if ground == "attested":
                note = "# the corpus attests this model"
            elif p.attested:
                note = (
                    "# inside the launch window AND below the mention floor: "
                    "attested, but not by enough to seat it"
                )
            else:
                note = (
                    "# released inside the launch window; no attested surface, "
                    "so every form below is derived"
                )
            lines.append(f"    seated_by: {ground}".ljust(38) + note)
        if p.attested:
            note = (f"# attested {p.attested[0].mentions} mentions "
                    f"[{source_split(p.attested[0])}]")
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
                note = f"# attested {hit.mentions} mentions [{source_split(hit)}]"
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
