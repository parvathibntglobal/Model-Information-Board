"""Build Engineer 2's labelling pools. Re-sieve over local corpora, no fetch.

    py -3 scripts/labelling_pools.py --out fixtures/golden

Three files. `entity-pool-candidates` and `filter-pool-candidates` come from
`_substitution_slice/`; `entity-pool-control-negatives` comes from
`_control_sweep/` and cannot come from anywhere else - see the last stratum.

CANDIDATE POOLS, NOT FINISHED SETS. She drafts them and hands ~50 back for
cross-labelling, so nothing here carries a label and nothing here is an answer
key. Every row is a question with its evidence attached, and since 2026-08-21
every row carries the question itself and the unit it is about - a shared
assumption about what a row means, held in a comment, is held nowhere.

WHY THE ENTITY POOL IS STRATIFIED AND NOT RANDOM
-------------------------------------------------
Her reason, and it is right: a random 200 mentions from this corpus is mostly
`opus 5` and `gemini 2.5 flash` matching one surface each, and an accuracy figure
over that measures the easy case. The strata are the places resolution is
actually decided:

    family-bare       a bare `sonnet` or `haiku` with no version token adjacent.
                      62% of family-word mentions are like this. The resolver
                      must NOT resolve them to a tier - `opus` is attested 968
                      times bare and attributable to no single model - so these
                      are the rows whose expected answer is `names-a-family-only`.

                      **THAT EXPECTATION IS ABOUT THE STRING AND THE LABEL IS
                      ABOUT THE DOCUMENT, AND BOTH CAN BE RIGHT.** `opus` in
                      "Claude 3 Opus & Sonnet" names a version to any reader, and
                      the population still excludes the bare word. The stratum
                      keeps its name - it is accurate about what it selected -
                      but the question now says "read the document" so the two
                      readings stop being silently swapped.
    spacing-variant   `gpt-5` against `gpt 5` against `gpt5`. Same model, three
                      surfaces, and the normaliser is what makes them one.
    ambiguous-in-context
                      a surface several registry models could be MEANT BY, where
                      READING THE DOCUMENT DOES NOT SETTLE IT. `qwen3` spans 25
                      registry ids, `gpt 5.6` spans 6, `claude 4.5` spans 3.

                      **WAS `ambiguous-owner`, AND THE OLD NAME CAUSED THE
                      DISAGREEMENT IT WAS BLAMED FOR.** Its note said attribution
                      "cannot be decided from the string alone", which invited a
                      reader to decide it from the string alone; `resolve()` reads
                      the normalised DOCUMENT. Nine of ten rows in a hand-labelled
                      draw were marked as resolving, by a person who read the
                      document, and they were right. The question now hands over
                      the document and says the answer may still be that it cannot
                      be decided.

                      `mistral 3` is the case worth holding: the registry has
                      `mistral-medium-3`, `-3-5` and `-3.1`, derives the surface
                      from none of them, and the document says *"Mistral just went
                      nuclear with their Mistral 3 release ... They released FOUR
                      models at once"*. Reading makes it worse, not better. That
                      example is in `LABEL_OPTIONS` where a labeller will see it.

                      SOURCED FROM THE EXTRACT, NOT FROM DERIVATION, and that is
                      a correction worth recording: the first version of this
                      stratum looked for surfaces that several canonical ids
                      DERIVE, and found zero. Derivation is injective - each id
                      renders its own local part, so two ids cannot produce one
                      string. Measured since, over 1,297 posts: surface
                      occurrences with more than one owner, **0**. Ambiguity is a
                      fact about what a human meant, not about what a machine
                      emits, and only the 49 `attested-gap-ambiguous` surfaces in
                      `fixtures/openrouter/observed-surfaces.json` measure it.
                      48 of those 49 are reachable by no derivation at all - so
                      `resolve()` returns nothing for them, and "we cannot
                      identify it" rather than "it is not a model" is the answer
                      the option set has to be able to express.
    matched-no-owner  a surface the population CONTAINS and no registry model
                      derives - the 23 declared-only surfaces from
                      `seed_models.yaml` that survive `_admissible`. `resolve()`
                      finds them, `RegistrySurfaceResolver` returns None, and
                      that is rule 6 working rather than failing: the owner is
                      absent and stays absent.

                      This is what the retired `unresolvable` name sounded like
                      it meant, and it had no bucket at all. `elif len(owners) ==
                      1` dropped it, and the sibling test above it paired two
                      ownerless surfaces because `() == ()` - so five reached the
                      pool mislabelled `spacing-variant`, under an expectation of
                      "resolves". Measured: 1,103 occurrences over 22 distinct
                      surfaces, `claude opus` 274 and `claude sonnet` 193.
    single-clear      one surface, one owner. The control. Without it there is
                      no baseline to say the hard strata are hard.

AND ONE STRATUM THAT IS NOT IN `STRATA`, BECAUSE IT IS NOT IN THIS CORPUS
--------------------------------------------------------------------------
    control-names-nothing
                      a document naming no model at all. **Real negatives**,
                      without which precision cannot be computed and the set
                      measures only recall. Document unit: no string is
                      highlighted, because there is none.

                      **`unresolvable` tried to draw these from the slice and
                      could not, and that is why it is retired rather than
                      repaired.** Every post in `_substitution_slice/` was
                      retrieved by a query containing model names. A sampler that
                      only reaches documents the query thought named a model
                      cannot produce a document where nothing does; what it
                      produces instead is documents where the query and the
                      population disagree, which is a real measurement of a
                      different thing. 40 such rows shipped with `surface: ""`
                      and were labelled.

                      Drawn instead by `build_control_negatives` from
                      `_control_sweep/`, the only documents here chosen for having
                      nothing to do with models. **748 of 750 qualify** - 448 of
                      450 Tier 1 and 300 of 300 Tier 2 - so the constraint is the
                      target and not the corpus. Tier 2 at exactly 300/300 is the
                      same instrument control passing that `control-and-reshape.md`
                      reports at 0.0% survival.

                      Written to its own file. The control manifests carry
                      `delete_after: 2026-11-16` and a snippet copied into a
                      committed fixture outlives its source unless the obligation
                      is copied too, so it is on every row and the file can be
                      dropped whole.

WHAT THE POOLS ARE DRAWN FROM, AND WHAT THAT FORBIDS
------------------------------------------------------
`_substitution_slice/` - 1,297 distinct Reddit posts recovered from 120 raw
payloads, retrieved 2026-08-17 by the substitution sweep.

**Every post was retrieved by a query containing model names.** So this corpus
is pre-filtered for exactly what the entity gate tests. Consequences, both of
which belong in whatever these pools are used to argue:

  * the FILTER pool's mix is not the mix of a real sweep. A survival rate
    measured on it is an upper bound and calibrates nothing.
  * the ENTITY pool's `unresolvable` stratum is scarcer here than in the wild,
    so a precision figure from it is optimistic.

Reddit only, and short-form only. GitHub config lines and blog prose name models
differently, and neither is represented.

PUBLISHED CONTENT IS QUOTE + ATTRIBUTION + LINK, NEVER FULL TEXT. Rows carry a
bounded snippet and the permalink, so the pools stay inside the same rule the
board publishes under.

NO MODEL PARTICIPATES.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collect.registry.propose import FAMILY_WORDS  # noqa: E402
from collect.registry.seed import load_seed_file  # noqa: E402
from collect.triage.entity import (  # noqa: E402
    SurfacePopulation,
    build_population,
    normalize,
    normalize_with_boundaries,
    resolve,
)
from collect.triage.gates import Document, triage  # noqa: E402

DEFAULT_SLICE = Path(__file__).resolve().parents[1] / "_substitution_slice"

#: Characters either side of a matched surface. Enough for a human to judge the
#: mention, far short of the document.
SNIPPET_RADIUS = 140

#: Targets. Approximate on purpose - a stratum the corpus cannot fill is
#: reported short rather than padded from an easier one.
ENTITY_TARGET = 200
FILTER_TARGET = 200

FAMILY_BARE = "family-bare"
SPACING_VARIANT = "spacing-variant"
#: WAS `ambiguous-owner`, renamed 2026-08-21. The old name said the ambiguity was
#: about which owner a STRING has, which invited "decide it from the string" and
#: got exactly that: the note read "attribution cannot be decided from the string
#: alone", nine rows were labelled `resolves` by a person reading the document,
#: and the disagreement looked like a labelling problem. It was a naming problem.
#: `resolve()` reads the normalised DOCUMENT. Ambiguity that survives the document
#: is the fact this stratum holds, and the name now says so.
AMBIGUOUS_IN_CONTEXT = "ambiguous-in-context"
MATCHED_NO_OWNER = "matched-no-owner"
SINGLE_CLEAR = "single-clear"
#: Document-unit negatives, and they do NOT come from `_substitution_slice/`.
#: See `build_control_negatives`.
CONTROL_NAMES_NOTHING = "control-names-nothing"

#: RETIRED 2026-08-21, and retired rather than repaired.
#:
#: `unresolvable` sampled documents in `_substitution_slice/` where `resolve()`
#: matched nothing, and emitted them with `surface: ""` because there is no
#: surface to name. 40 rows, every one asking a labeller whether the empty string
#: refers to a model.
#:
#: THE UNIT MISMATCH WAS THE SYMPTOM. The reason it cannot be fixed in place is
#: the corpus: every post in `_substitution_slice/` was retrieved by a query
#: containing model names, so a document there that matches nothing is not a
#: document about something else - it is a document the retrieval thought named a
#: model and the population disagreed. That is a measurement of the gap between
#: query and population, which is worth having and is not the negative class.
#: Rebuilding the branch would draw from the same 1,297 posts and produce the
#: same 40 blanks with better field names.
#:
#: The population lives in the control corpora, which is what they are for.
RETIRED_UNRESOLVABLE = "unresolvable"

STRATA = (
    FAMILY_BARE,
    SPACING_VARIANT,
    AMBIGUOUS_IN_CONTEXT,
    MATCHED_NO_OWNER,
    SINGLE_CLEAR,
)

#: What a row's label is a statement ABOUT. The first version of this pool had no
#: such field and every row was rendered as "does the highlighted surface refer to
#: a model", including the 40 whose surface was `""` by construction. A stratum
#: whose fact is about a document cannot answer a question about a string, and the
#: only durable fix is for the row to carry its own unit and its own question
#: rather than letting the tool assume one.
SURFACE = "surface"
DOCUMENT = "document"

#: How many of ENTITY_TARGET each stratum should contribute. The hard strata are
#: over-weighted relative to their frequency, which is the point of stratifying.
QUOTA = {
    FAMILY_BARE: 45,
    SPACING_VARIANT: 40,
    AMBIGUOUS_IN_CONTEXT: 40,
    MATCHED_NO_OWNER: 40,
    SINGLE_CLEAR: 35,
}

#: The document-unit negatives, drawn from the control corpora rather than from
#: the slice. Separate target because they are a separate file with a separate
#: retention date - see `build_control_negatives`.
CONTROL_TARGET = 40

#: WHAT A LABELLER MAY ANSWER, AND WHAT THE ANSWER IS ABOUT.
#:
#: Carried in the pool's `_meta` so the tool renders these and holds no list of
#: its own.
#:
#: THREE OPTIONS, RULED 2026-08-21, AND THE RULING IS ABOUT WHAT A LABEL IS FOR.
#: A label records **what the text names**. It is not a prediction of what
#: `resolve()` can return, and it must not be trimmed to match the resolver's
#: outcomes - that would make the golden set unable to disagree with the thing it
#: exists to measure.
#:
#: Two labellers arrived at the same conclusion from opposite ends. Yathu never
#: used the middle option at all; anooj used it for bare product lines like
#: `chatgpt` where no version is stated. **"Someone discussed a product line" is
#: not "someone typed a word that isn't a model"**, and that distinction is worth
#: a label even though no resolver can produce it: the first is evidence about a
#: line and the second is noise. Losing it would fold a real reading of the text
#: into the bucket for coincidences of spelling, and rule 4 is about exactly that
#: confusion at display time.
#:
#: SCORING IS SEPARATE, AND BINARY. `RegistrySurfaceResolver` returns
#: `str | None` - one model id or nothing. So a comparison collapses
#: `names-a-line-not-a-version` and `not-a-model` together and asks only whether
#: the resolver returned an id. The middle option is never scored on its own; it
#: is recorded for the reader and for any later ruling on family-specificity
#: claims, which is where it becomes load-bearing.
#:
#: The previous four-option set split the middle in two - a family word versus a
#: model we cannot pin down - and that split cannot be scored either, so it bought
#: precision the comparison could not use. Three, and the middle one honest about
#: covering both.
LABEL_OPTIONS = {
    "names-one-model": {
        "means": (
            "Reading this document, the highlighted string names exactly one "
            "specific model version you could file a claim against."
        ),
        "help": (
            "The document is yours to use. `mini` in \"Why GPT-4o mini beats "
            "Claude 3.5 Sonnet\" is this: the bare word names nothing, and in "
            "this document it is unmistakably GPT-4o mini."
        ),
        "scored_as": "expects the resolver to return a model id",
    },
    "names-a-line-not-a-version": {
        "means": (
            "The text names a model line, a product, or a release - but not one "
            "version you could attach a claim to. Someone IS discussing a model; "
            "you cannot say which one."
        ),
        "help": (
            "This is the option that records a reading rather than a lookup, so "
            "pick it from the text and never from what you think the code can "
            "do. "
            "Bare product lines: `chatgpt` in \"I unsubbed from ChatGPT plus\", "
            "`opus` in \"which Opus should I use\". A line is named, no version "
            "is. "
            "Releases that name several versions at once: `mistral 3`. The "
            "registry holds `mistral-medium-3`, `mistral-medium-3-5` and "
            "`mistral-medium-3.1`, and derives the surface from none of them. "
            "Reading the document does not settle it and makes it worse - the "
            "post says \"Mistral just went nuclear with their Mistral 3 release "
            "... They released FOUR models at once\". Four in the document, "
            "three in the registry, no way to pick. Choose this AFTER reading, "
            "not instead of reading. "
            "NOT this: `opus` in \"Claude 3 Opus & Sonnet\", which names a "
            "version - that is `names-one-model` even though the resolver "
            "cannot reach it."
        ),
        "scored_as": (
            "collapsed with not-a-model: expects the resolver to return nothing. "
            "The distinction from not-a-model is recorded, never scored - see the "
            "ruling above."
        ),
    },
    "not-a-model": {
        "means": (
            "Not a model reference at all - prose, a URL parameter, a person's "
            "name, a coincidence of spelling. Nobody is discussing a model here."
        ),
        "help": (
            "`auto` inside `&auto=webp` in an image URL is this. So is `free` "
            "inside \"freeze\", and `air` in \"a breath of fresh air\"."
        ),
        "scored_as": "collapsed with names-a-line-not-a-version",
    },
}

#: How the three options fold onto what the resolver can actually answer.
#: `RegistrySurfaceResolver` returns one model id or None, so scoring is binary
#: and the middle option has no column of its own.
SCORING = {
    "names-one-model": "resolved",
    "names-a-line-not-a-version": "not-resolved",
    "not-a-model": "not-resolved",
}

#: The question a labeller is shown, per stratum. Held here rather than in the
#: labelling tool so that a stratum and its question cannot drift apart: the tool
#: renders `row.question` and has no template of its own.
#:
#: EVERY QUESTION NAMES THE DOCUMENT, because `resolve()` reads the normalised
#: document and the strata used to assume the string alone. Where a question used
#: to say "the string alone cannot decide this", it now says the document is
#: available and the answer may still be that it cannot be decided.
QUESTION = {
    FAMILY_BARE: (
        "Read the document. Does the highlighted word name one specific model "
        "version here - or only a family?"
    ),
    SPACING_VARIANT: (
        "Read the document. Is the highlighted string a spelling of the same "
        "model as the others listed beside it?"
    ),
    AMBIGUOUS_IN_CONTEXT: (
        "Read the document, then say which ONE model the highlighted string "
        "means. If the document does not narrow it to one, say so - the "
        "registry holds several candidates and derives the string from none of "
        "them, and the document is allowed to leave that unresolved."
    ),
    MATCHED_NO_OWNER: (
        "The highlighted string IS in our surface list, and the registry holds "
        "no model that derives it. Reading the document, does it name a model "
        "we should be able to identify?"
    ),
    SINGLE_CLEAR: (
        "Read the document. Does the highlighted string, as used here, name the "
        "model listed beside it?"
    ),
    CONTROL_NAMES_NOTHING: (
        "NO STRING IS HIGHLIGHTED - this row is about the whole document. Does "
        "this document name any AI model at all?"
    ),
}

_VERSION_NEAR = re.compile(r"\b\d")


@dataclass
class Post:
    external_id: str
    url: str
    subreddit: str | None
    created_at: str | None
    author: str | None
    is_self: bool | None
    title: str
    body: str

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.body}".strip()


def load_corpus(slice_dir: Path) -> list[Post]:
    """Every distinct post in the raw payloads. Richer than posts.jsonl."""
    posts: dict[str, Post] = {}
    for f in (slice_dir / "raw").rglob("*"):
        if not f.is_file():
            continue
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for entry in payload.get("data", {}).get("posts", []) or []:
            d = entry.get("data") or {}
            if not d.get("id"):
                continue
            ts = d.get("created_utc")
            posts[d["id"]] = Post(
                external_id=d["id"],
                url="https://www.reddit.com" + (d.get("permalink") or ""),
                subreddit=d.get("subreddit"),
                created_at=(
                    datetime.fromtimestamp(ts, tz=UTC).date().isoformat()
                    if ts
                    else None
                ),
                author=d.get("author"),
                is_self=d.get("is_self"),
                title=d.get("title") or "",
                body=d.get("selftext") or "",
            )
    return sorted(posts.values(), key=lambda p: p.external_id)


def snippet_around(text: str, surface: str) -> tuple[str, int] | None:
    """A bounded window around the first occurrence, and where it started.

    Matched on the NORMALISED string and mapped back, because the document spells
    the surface however the writer did - `GPT 5`, `gpt-5` - and a raw `find` on
    the surface misses every one of those.

    **WORD BOUNDARIES ON BOTH ENDS, AND THIS FILE IS WHY THE RULE EXISTS TWICE.**
    A plain `.find()` on the space-stripped text reported 43 candidates for the
    two-surface stratum where a bounded match reports 2, and 40 of the 41 dropped
    were `pro` inside "problem" and "process". A stratum of 43 rows where 41 are
    noise is worse than an empty one: an empty stratum sends you elsewhere, and a
    full one gets labelled.

    Second instance of the defect `normalize_with_boundaries` was written for -
    the first was `resolve()` hitting `free` inside "freeze" on a movie corpus.
    So this REUSES that function rather than re-deriving the rule: two
    implementations of one question is how the first fix failed to reach the
    second caller.

    The current seated surfaces all carry a digit and so cannot hide inside an
    English word. That is a property of today's data and not of this code, which
    is exactly why the check belongs here.
    """
    norm_surface = normalize(surface)
    if not norm_surface:
        return None
    norm_text, starts, ends = normalize_with_boundaries(text)

    pos = norm_text.find(norm_surface)
    while pos >= 0 and not (starts[pos] and ends[pos + len(norm_surface) - 1]):
        pos = norm_text.find(norm_surface, pos + 1)
    if pos < 0:
        return None

    # Map the normalised offset back by walking the raw text and counting the
    # characters that survive normalisation.
    raw_start = raw_end = None
    seen = 0
    for i, ch in enumerate(text):
        if raw_start is None and seen == pos:
            raw_start = i
        if seen == pos + len(norm_surface):
            raw_end = i
            break
        if normalize(ch):
            seen += 1
    if raw_start is None:
        return None
    if raw_end is None:
        raw_end = len(text)

    lo = max(0, raw_start - SNIPPET_RADIUS)
    hi = min(len(text), raw_end + SNIPPET_RADIUS)
    prefix = "..." if lo > 0 else ""
    suffix = "..." if hi < len(text) else ""
    return f"{prefix}{text[lo:hi].strip()}{suffix}", raw_start


def occurs_bounded(text: str, surface: str) -> bool:
    """Does `surface` occur in `text` on word boundaries?

    THE AMBIGUOUS-OWNER STRATUM USED A RAW `in` AND THIS IS THE THIRD SITE OF THE
    SAME DEFECT. `snippet_around` bounds its match and `resolve` bounds its match;
    the ambiguous branch tested `normalize(surface) in normalize(text)` and so
    could seat a row on `gpt 3.5` found inside `gpt 3.5 turbo`, or on any surface
    hiding in a longer one. Same question, third implementation, so this one is a
    thin wrapper over the shared boundary map rather than a fourth rule.
    """
    return snippet_around(text, surface) is not None


def bare_family_hits(text: str) -> list[str]:
    """Family words appearing with NO digit within 20 characters.

    Deliberately crude and stated as such: it is a candidate finder for a human,
    not a classifier. `alias-surfaces.md` §4 measured the same shape and put 62%
    of family mentions in this bucket.
    """
    found = []
    lowered = text.casefold()
    for word in sorted(FAMILY_WORDS):
        for m in re.finditer(rf"\b{re.escape(word)}\b", lowered):
            window = lowered[m.end() : m.end() + 20]
            if not _VERSION_NEAR.search(window):
                found.append(word)
                break
    return found


@dataclass
class EntityRow:
    stratum: str
    surface: str
    snippet: str
    source_url: str
    subreddit: str | None
    external_id: str
    created_at: str | None
    #: What this row's label is a statement about - `surface` or `document`.
    #: The `unresolvable` stratum is the only document-unit one, and it is the
    #: reason this field exists: it carries no surface, so a tool that assumes
    #: every row is about a string asks 40 people about the empty string.
    unit: str = SURFACE
    #: The exact question to put to the labeller. Travels with the row so the
    #: tool cannot invent one that the stratum does not support.
    question: str = ""
    #: Registry ids that derive this surface. EMPTY IS TWO DIFFERENT FACTS:
    #: a declared-only surface has no owner recorded, and an unresolvable row has
    #: no surface at all. `stratum` is what separates them - and since the
    #: `matched-no-owner` stratum exists, the first of the two has a name.
    candidate_models: list[str] = field(default_factory=list)
    #: Every surface the population matched in this document, for context.
    all_surfaces_in_document: list[str] = field(default_factory=list)
    #: Set only on rows copied from a corpus that carries a retention date. The
    #: obligation travels with the copy or it does not exist: a snippet in a
    #: committed fixture outlives the corpus it came from by default.
    delete_after: str | None = None
    label: None = None
    note: str = ""


def load_ambiguous(path: Path) -> dict[str, list[str]]:
    """Surfaces the extract found several registry models could be meant by.

    Returns surface -> candidate ids. Not `population.owners`: see the
    `ambiguous-owner` note in the module docstring for why derivation cannot
    produce this and the corpus is the only source of it.
    """
    if not path.is_file():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {
        r["surface"]: list(r["models"])
        for r in rows
        if r.get("verdict") == "attested-gap-ambiguous" and len(r.get("models", [])) > 1
    }


def build_entity_pool(
    posts,
    population: SurfacePopulation,
    ambiguous: dict[str, list[str]] | None = None,
) -> tuple[list[EntityRow], dict]:
    buckets: dict[str, list[EntityRow]] = defaultdict(list)
    ambiguous = ambiguous or {}
    # Longest first, so `gemini 3.1 pro` is preferred over `gemini 3` in a
    # document containing both - the more specific mention is the harder label.
    ambiguous_order = sorted(ambiguous, key=lambda s: (-len(s), s))

    for post in posts:
        text = post.text
        matched = resolve(text, population)
        # `haystack = normalize(text)` lived here and became dead when the
        # unbounded `normalize(surface) in haystack` check was replaced by
        # `occurs_bounded`, which normalises internally. Removed rather than
        # silenced: a leftover from a boundary fix is the last thing to keep
        # around, since it is the shape the fix removed.

        def row(
            stratum: str,
            surface: str,
            note: str = "",
            candidates: list[str] | None = None,
            *,
            _post=post,
            _text=text,
            _matched=matched,
        ) -> EntityRow | None:
            # The three underscore parameters bind this iteration's values at
            # definition time. Without them the closure reads whatever the loop
            # holds when it is CALLED, which is the same iteration today and a
            # silent cross-document mix-up the moment anyone defers a call.
            got = snippet_around(_text, surface) if surface else (_text[:280], 0)
            if got is None:
                return None
            return EntityRow(
                stratum=stratum,
                surface=surface,
                unit=DOCUMENT if not surface else SURFACE,
                question=QUESTION[stratum],
                snippet=got[0],
                source_url=_post.url,
                subreddit=_post.subreddit,
                external_id=_post.external_id,
                created_at=_post.created_at,
                candidate_models=(
                    candidates
                    if candidates is not None
                    else list(population.owners.get(surface, ()))
                ),
                all_surfaces_in_document=list(_matched[:6]),
                note=note,
            )

        for surface in ambiguous_order:
            if normalize(surface) and occurs_bounded(text, surface):
                models = ambiguous[surface]
                r = row(
                    AMBIGUOUS_IN_CONTEXT,
                    surface,
                    f"the corpus extract found {len(models)} registry models this "
                    "surface could be meant by; attribution cannot be decided from "
                    "the string alone",
                    candidates=models,
                )
                if r:
                    buckets[AMBIGUOUS_IN_CONTEXT].append(r)
                break

        if not matched:
            # NO ROW, AND THE BRANCH IS KEPT EMPTY ON PURPOSE so the next person
            # to notice this pool has no negatives finds the reason here rather
            # than re-adding one.
            #
            # `unresolvable` lived here and is retired. A document in THIS corpus
            # that matches nothing is not a document about something else - every
            # post here was retrieved by a query naming a model. It is a document
            # the retrieval thought named one and the population disagreed, which
            # measures the gap between query and population. Worth measuring, and
            # not the negative class. Rebuilding it here draws from the same
            # 1,297 posts and produces the same 40 blanks with better field names.
            #
            # The negatives come from `build_control_negatives`.
            continue

        for word in bare_family_hits(text):
            r = row(
                FAMILY_BARE,
                word,
                "family word with no adjacent version; excluded from the "
                "population on purpose - the expected answer is 'cannot resolve'",
            )
            if r:
                buckets[FAMILY_BARE].append(r)

        for surface in matched:
            owners = population.owners.get(surface, ())
            if not owners:
                # MATCHED, AND RESOLVES TO NOTHING. A declared surface from
                # `seed_models.yaml` that no registry id derives: `build_population`
                # records no owner for it (rule 6 - it will not guess which model a
                # human meant), so `resolve()` finds it and `RegistrySurfaceResolver`
                # returns None. That is a real and distinct answer and it had no
                # stratum: the old `elif len(owners) == 1` dropped these on the
                # floor, except where two of them collided in the sibling test
                # below - `() == ()` reads as "same owner" - and five landed in
                # `spacing-variant` under an expectation of "resolves".
                r = row(
                    MATCHED_NO_OWNER,
                    surface,
                    "in the surface population but no registry model derives it "
                    "(declared-only); resolution returns None rather than a guess",
                )
                if r:
                    buckets[MATCHED_NO_OWNER].append(r)
                continue
            siblings = [
                s
                for s in matched
                if s != surface
                and population.owners.get(s, ()) == owners
                and normalize(s) != normalize(surface)
            ]
            if siblings:
                r = row(
                    SPACING_VARIANT,
                    surface,
                    f"same owner as {siblings[:2]} - one model, several spellings",
                )
                if r:
                    buckets[SPACING_VARIANT].append(r)
            elif len(owners) == 1:
                r = row(SINGLE_CLEAR, surface, "one surface, one owner")
                if r:
                    buckets[SINGLE_CLEAR].append(r)

    # Spread each stratum across SURFACES first and documents second. Taking the
    # first N by document id filled `family-bare` with `chatgpt` and `pro` and
    # reached no `haiku` at all, though the corpus holds 106 bare ones - the
    # quota was exhausted before the rarer words were reached. Round-robin over
    # the surface fixes that, and it is the surface the label is about.
    out: list[EntityRow] = []
    shortfall = {}
    for stratum in STRATA:
        rows = buckets[stratum]
        by_surface: dict[str, list[EntityRow]] = defaultdict(list)
        for r in rows:
            by_surface[r.surface].append(r)
        # Within one surface, spread across documents the same way.
        for surface, group in by_surface.items():
            by_doc: dict[str, list[EntityRow]] = defaultdict(list)
            for r in group:
                by_doc[r.external_id].append(r)
            spread: list[EntityRow] = []
            i = 0
            while len(spread) < len(group):
                added = False
                for d in sorted(by_doc):
                    if i < len(by_doc[d]):
                        spread.append(by_doc[d][i])
                        added = True
                if not added:
                    break
                i += 1
            by_surface[surface] = spread

        interleaved: list[EntityRow] = []
        surfaces = sorted(by_surface)
        i = 0
        while len(interleaved) < len(rows):
            added = False
            for s in surfaces:
                if i < len(by_surface[s]):
                    interleaved.append(by_surface[s][i])
                    added = True
            if not added:
                break
            i += 1
        want = QUOTA[stratum]
        take = interleaved[:want]
        out.extend(take)
        if len(take) < want:
            shortfall[stratum] = {"wanted": want, "available": len(take)}

    stats = {
        "available_per_stratum": {s: len(buckets[s]) for s in STRATA},
        "taken_per_stratum": {
            s: sum(1 for r in out if r.stratum == s) for s in STRATA
        },
        "shortfall": shortfall,
    }
    return out, stats


DEFAULT_CONTROL = Path(__file__).resolve().parents[1] / "_control_sweep"


def load_control(control_dir: Path) -> tuple[list[tuple[str, Post]], dict]:
    """The Tier 1 and Tier 2 control posts, tagged with their tier and manifest.

    Flat `posts.jsonl` rather than raw payloads, because the control sweep wrote
    one and because these documents are deliberately NOT in `raw/` - the manifest
    says so, and says why: they carry a deletion date that an immutable
    content-addressed store cannot express.
    """
    out: list[tuple[str, Post]] = []
    manifests: dict = {}
    for tier in ("tier1", "tier2"):
        posts_path = control_dir / tier / "posts.jsonl"
        manifest_path = control_dir / tier / "manifest.json"
        if not posts_path.is_file():
            continue
        manifests[tier] = json.loads(manifest_path.read_text(encoding="utf-8"))
        for line in posts_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            out.append(
                (
                    tier,
                    Post(
                        external_id=d["external_id"],
                        url=d.get("url") or "",
                        subreddit=d.get("subreddit"),
                        created_at=d.get("created_at"),
                        author=d.get("author"),
                        is_self=(str(d.get("is_self")).casefold() == "true"),
                        title=d.get("title") or "",
                        body=d.get("selftext") or "",
                    ),
                )
            )
    return out, manifests


def build_control_negatives(
    control: list[tuple[str, Post]],
    population: SurfacePopulation,
    manifests: dict,
) -> tuple[list[EntityRow], dict]:
    """The document-unit negative class, from documents the sweep did not retrieve.

    WHY HERE AND NOT IN `build_entity_pool`. A negative is a document about
    something else that our population correctly declines to match. Every post in
    `_substitution_slice/` was retrieved by a query containing model names, so the
    slice cannot contain one - a sampler that only reaches documents the query
    thought named a model cannot produce a document where nothing does. The old
    `unresolvable` stratum sampled the slice anyway and got 40 rows that were
    something else entirely, and rebuilding it in place would have produced the
    same 40.

    The control corpora ARE the population: 450 Tier 1 posts (programming, webdev,
    devops, rust, golang, sysadmin) and 300 Tier 2 (AskReddit, todayilearned,
    movies, cooking), collected 2026-08-18 to calibrate triage survival. They are
    the only documents in this repository chosen for having nothing to do with
    models, and `control-and-reshape.md` already used them for exactly this
    question - the `saba`-inside-"was a bad" defect is a false positive on this
    corpus, which is a mislabelled negative.

    COUNT BEFORE DRAWING. `qualifying` is reported whether or not it fills the
    target: a stratum of 12 is a stratum of 12, not a shortfall against 40.

    THE DELETION DATE TRAVELS. The manifests carry `delete_after: 2026-11-16`,
    because Data API Terms 3.2 is unresolved against the immutable store. A
    snippet copied into a committed fixture outlives that date unless the
    obligation is copied with it, so it is on every row and in the header, and
    these rows are written to their own file so they can be dropped whole.
    """
    by_tier: dict[str, list[Post]] = defaultdict(list)
    considered: dict[str, int] = defaultdict(int)
    for tier, post in control:
        considered[tier] += 1
        if not resolve(post.text, population):
            by_tier[tier].append(post)

    qualifying = {t: len(v) for t, v in by_tier.items()}
    delete_after = sorted(
        {m.get("delete_after") for m in manifests.values() if m.get("delete_after")}
    )

    # EQUAL DRAW ACROSS TIERS, not proportional. The two tiers measure different
    # things - Tier 1 is the bias control and Tier 2 the instrument control - and
    # a proportional draw would let the larger tier set the character of the
    # stratum.
    per_tier = CONTROL_TARGET // max(1, len(by_tier))
    out: list[EntityRow] = []
    for tier in sorted(by_tier):
        posts = sorted(by_tier[tier], key=lambda p: p.external_id)
        want = min(per_tier, len(posts))
        stride = max(1, len(posts) // want) if want else 1
        for post in posts[::stride][:want]:
            text = post.text
            out.append(
                EntityRow(
                    stratum=CONTROL_NAMES_NOTHING,
                    surface="",
                    unit=DOCUMENT,
                    question=QUESTION[CONTROL_NAMES_NOTHING],
                    snippet=text[:280] + ("..." if len(text) > 280 else ""),
                    source_url=post.url,
                    subreddit=post.subreddit,
                    external_id=post.external_id,
                    created_at=post.created_at,
                    candidate_models=[],
                    all_surfaces_in_document=[],
                    delete_after=(delete_after[0] if delete_after else None),
                    note=(
                        f"control corpus {tier}, r/{post.subreddit} - retrieved "
                        "for having nothing to do with models, not by a query "
                        "naming one. No population surface appears in it."
                    ),
                )
            )

    # A title-only link post is a weaker negative than prose, and the split is
    # reported rather than engineered: selecting for body text would pick the
    # corpus's chattier half and quietly change what the stratum measures.
    with_body = sum(1 for r in out if len(r.snippet.strip()) > 80)
    stats = {
        "considered_per_tier": dict(considered),
        "qualifying_per_tier": qualifying,
        "qualifying_total": sum(qualifying.values()),
        "target": CONTROL_TARGET,
        "taken_per_tier": {
            t: sum(1 for r in out if f"control corpus {t}," in r.note)
            for t in sorted(by_tier)
        },
        "taken_total": len(out),
        "rows_longer_than_80_chars": with_body,
        "delete_after": delete_after,
        "subreddits": {t: m.get("subreddits") for t, m in manifests.items()},
    }
    return out, stats


@dataclass
class FilterRow:
    external_id: str
    source_url: str
    subreddit: str | None
    created_at: str | None
    snippet: str
    token_count: int
    is_link_post: bool | None
    has_own_commentary: bool
    #: What the gates decided, so she is labelling AGAINST a verdict rather than
    #: from scratch. Disagreement is the signal the set exists to produce.
    gate_verdict: str = ""
    gate_reasons: list[str] = field(default_factory=list)
    gates_that_did_not_run: list[str] = field(default_factory=list)
    matched_surfaces: list[str] = field(default_factory=list)
    label: None = None
    note: str = ""


def build_filter_pool(posts, population: SurfacePopulation) -> tuple[list[FilterRow], dict]:
    """~200 documents, whatever mix the corpus holds - proportional, not balanced.

    Deliberately NOT stratified, unlike the entity pool. She asked for the mix
    the corpus holds, and the filter set's job is to check the gates against
    ordinary traffic. Sampled by a stable stride so the draw is reproducible and
    is not the first 200 by id.
    """
    rows: list[FilterRow] = []
    stride = max(1, len(posts) // FILTER_TARGET)
    for post in posts[::stride][:FILTER_TARGET]:
        doc = Document(
            text=post.text,
            author=post.author,
            is_self_post=post.is_self,
            body=post.body,
        )
        result = triage(doc, population=population)
        rows.append(
            FilterRow(
                external_id=post.external_id,
                source_url=post.url,
                subreddit=post.subreddit,
                created_at=post.created_at,
                snippet=post.text[:400] + ("..." if len(post.text) > 400 else ""),
                token_count=len(post.text.split()),
                is_link_post=(None if post.is_self is None else not post.is_self),
                has_own_commentary=bool(post.body.strip()),
                gate_verdict=str(result.verdict),
                gate_reasons=list(result.reasons),
                # BOTH kinds: this field means "said nothing", and the pool
                # labels documents rather than diagnosing the build. The split
                # lives on `TriageResult` for the reader who needs it.
                gates_that_did_not_run=list(result.no_verdict),
                matched_surfaces=list(result.matched_surfaces[:6]),
            )
        )
    kept = sum(1 for r in rows if r.gate_verdict == "kept")
    return rows, {
        "sampled": len(rows),
        "of_corpus": len(posts),
        "stride": stride,
        "gate_kept": kept,
        "gate_dropped": len(rows) - kept,
    }


HEADER = {
    "purpose": "CANDIDATE POOL for Engineer 2 to draft from. Not a labelled set.",
    "labels": "every row has label: null. Nothing here is an answer key.",
    "corpus": (
        "_substitution_slice/ - 1,297 distinct Reddit posts, retrieved 2026-08-17 "
        "by the substitution sweep"
    ),
    "caveat": (
        "EVERY POST WAS RETRIEVED BY A QUERY CONTAINING MODEL NAMES. The corpus is "
        "pre-filtered for what the entity gate tests: the filter pool's mix is not a "
        "real sweep's mix, and the unresolvable stratum is scarcer here than in the "
        "wild, so precision measured on it is optimistic. Reddit and short-form only."
    ),
    "content_rule": "bounded snippet plus permalink, never full text",
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slice", type=Path, default=DEFAULT_SLICE)
    ap.add_argument("--control", type=Path, default=DEFAULT_CONTROL)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    if not (args.slice / "raw").is_dir():
        print(
            f"no corpus at {args.slice}/raw. This script does not fetch: run "
            "scripts/substitution_slice.py retrieve first.",
            file=sys.stderr,
        )
        return 2

    posts = load_corpus(args.slice)
    print(f"corpus: {len(posts)} distinct posts")

    seed = load_seed_file()
    declared: list[str] = []
    for m in seed.models:
        declared.append(m.aliases.surface)
        declared.extend(m.aliases.variants)

    from collect.db import connect

    conn = connect()
    try:
        models = conn.execute(
            "SELECT canonical_id, display_name FROM model_version ORDER BY canonical_id"
        ).fetchall()
    finally:
        conn.close()

    population = build_population(models, declared)
    print(f"population: {population.basis}")

    args.out.mkdir(parents=True, exist_ok=True)

    ambiguous = load_ambiguous(
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "openrouter"
        / "observed-surfaces.json"
    )
    print(f"ambiguous surfaces from the extract: {len(ambiguous)}")

    entity_rows, entity_stats = build_entity_pool(posts, population, ambiguous)
    filter_rows, filter_stats = build_filter_pool(posts, population)

    control, manifests = load_control(args.control)
    if not control:
        print(
            f"no control corpus at {args.control}. The document-unit negative "
            "class comes from there and nowhere else; the entity pool will have "
            "no negatives and precision cannot be computed from it.",
            file=sys.stderr,
        )
        control_rows, control_stats = [], {"qualifying_total": 0, "taken_total": 0}
    else:
        control_rows, control_stats = build_control_negatives(
            control, population, manifests
        )
        # COUNTED BEFORE DRAWN, and printed that way round.
        print(
            f"control negatives: {control_stats['qualifying_total']} of "
            f"{sum(control_stats['considered_per_tier'].values())} control posts "
            f"qualify; took {control_stats['taken_total']}"
        )

    for name, rows, stats in (
        ("entity-pool-candidates", entity_rows, entity_stats),
        ("entity-pool-control-negatives", control_rows, control_stats),
        ("filter-pool-candidates", filter_rows, filter_stats),
    ):
        path = args.out / f"{name}.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            meta = {
                **HEADER,
                "pool": name,
                "population_fingerprint": population.fingerprint,
                "population_basis": population.basis,
                "rows": len(rows),
                "stats": stats,
            }
            if name.startswith("entity-pool"):
                # The tool renders these and keeps no list of its own, so a
                # renamed option cannot survive in one place and not the other.
                meta["label_options"] = LABEL_OPTIONS
            if name == "entity-pool-control-negatives":
                meta["corpus"] = (
                    "_control_sweep/ - 450 Tier 1 (programming, webdev, devops, "
                    "rust, golang, sysadmin) and 300 Tier 2 (AskReddit, "
                    "todayilearned, movies, cooking) posts, collected 2026-08-18"
                )
                meta["caveat"] = (
                    "NOT the substitution slice. These documents were retrieved "
                    "for having nothing to do with models, which is the only "
                    "way to get a real negative: every post in the slice was "
                    "retrieved by a query naming a model, so a slice document "
                    "that matches nothing is a query/population gap and not a "
                    "negative."
                )
                meta["delete_after"] = stats.get("delete_after")
                meta["retention"] = (
                    "These rows copy snippets from a corpus carrying "
                    "delete_after. The obligation travels with the copy, and "
                    "this file is separate so it can be dropped whole on that "
                    "date without touching the rest of the pool."
                )
            fh.write(json.dumps({"_meta": meta}, ensure_ascii=False) + "\n")
            for r in rows:
                fh.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
        print(f"wrote {path}  ({len(rows)} rows)")
        print(f"      {json.dumps(stats, ensure_ascii=False)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
