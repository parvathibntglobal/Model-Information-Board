"""E3 — flatten a thread into one string, and emit the `offset_map` beside it.

**THIS IS THE ONE PIECE WHERE A DEFECT IS EXPENSIVE RATHER THAN MERELY WRONG.**
`collect/CLAUDE.md`: the map is about ten lines while you are already walking the
tree and impossible to reconstruct afterwards. Every quote extracted without it,
or against a wrong one, has to be re-extracted — and extraction is the only paid
stage. So byte equality against a known-good map comes before anything else
touches this.

WHAT IT PRODUCES
----------------
    flattened_text   the string the extractor reads
    offset_map       one segment per contiguous run where flat and raw
                     correspond one-to-one, plus one per substitution

`contract/tables.sql` specifies that shape and `judge/extract/verify.py` consumes
it. A substitution segment has different flat and raw lengths and cannot be
sub-indexed: a span touching it takes the whole substitution, because there is no
meaningful position inside a rewrite.

TWO REWRITES, IN ONE ORDER, IN ONE WALK
----------------------------------------
**Entities are decoded before symbols are substituted.** Ruled 2026-08-18, and
the reason is that they are different KINDS of operation: an entity undoes how
the text arrived, a symbol substitution changes how it reads. Decoding first
means everything downstream operates on what the person typed. The other order
substitutes into a string still carrying `&gt;`, and the later decode then moves
offsets that symbol segments were already computed against.

Both happen in ONE left-to-right walk rather than two passes, which is what makes
the order structural instead of a convention somebody has to remember — and what
makes `unescape exactly once` a property of the algorithm rather than a check.
`&amp;gt;` is a literal somebody typed: the walk consumes `&amp;`, emits `&`,
and resumes AFTER it, so `gt;` is never re-examined. Decoding twice would turn
their text into markup they did not write.

WHAT IS TESTED SYNTHETICALLY, AND WHY IT HAS TO BE
---------------------------------------------------
Stated rather than left to inference, because "entities are handled" is not the
same claim as "double-decoding is prevented" and a reader cannot tell them apart
from the code.

**No real comment can supply a double-encoded entity.** Counted over the source
payload: 195 comment bodies, 6 carrying an entity, **0 doubled**. So
`&amp;gt;` staying `&gt;` is tested synthetically in
`tests/test_flatten.py::test_unescape_happens_exactly_once` and nowhere else,
and that is the correct place for it rather than a gap.

The layering is worth knowing, because the three checks catch different things:

    byte equality vs the fixture     catches NOTHING here. `&gt;` decoded once
                                     or twice both yield `>`, so the string is
                                     identical either way.
    segment equality vs the fixture  catches a single entity decoded in the
                                     wrong place — the substitution collapses
                                     into the identity run and `raw_end` moves
                                     from 4 to 167.
    the synthetic test               catches double-decoding, which no fixture
                                     built from this payload can reach.

Mutation-checked 2026-08-18: pre-unescaping the text before the walk — the
realistic form of the bug, reaching for `html.unescape` and then walking — fails
five tests in that file and passes byte equality. Confirmed by reverting.

REDDIT'S FIVE ENTITIES AND NO OTHERS
-------------------------------------
`&amp; &lt; &gt; &quot; &#39;` is what the API emits. A general HTML unescaper
would also rewrite `&copy;` and `&mdash;`, which a user may have typed literally
— and rewriting those is a change to authorship rather than to transport.

WHICH CHARACTERS ARE SUBSTITUTED, MEASURED RATHER THAN CHOSEN
--------------------------------------------------------------
Unicode general category **`So`** — Symbol, other. Read off
`fixtures/threads/thread-1u1b22l.json` rather than decided here: that fixture
substitutes `😄 😭 🤝 █` and keeps `’` (U+2019, category `Pf`). So the line is not
"emoji" — `█` FULL BLOCK is not an emoji and is substituted — it is `So`.

The tag is `unicodedata.name()`, lowercased, spaces to underscores:
`[loudly_crying_face]`, `[full_block]`.

NO MODEL PARTICIPATES.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class FlatteningRules:
    """Which rewrites apply, per platform. Ruled 2026-08-18.

    The rules in this module were global, which was true while there was one
    platform and stopped being true the moment blog text arrived.

    WHY `decode_entities` IS FALSE FOR BLOGS
    ----------------------------------------
    **trafilatura has already decoded, and it decodes TWICE.** Measured
    2026-08-18 by isolating it against bare lxml:

        html          'type &amp;gt; here'
        lxml alone    'type &gt; here'      <- one decode, correct
        trafilatura   'type > here'        <- a second decode

    An unknown entity (`&amp;unknown;`) survives as `&unknown;` through both, so
    the second pass is an entity unescape and not generic cleanup.

    So on blog text this module's entity pass is a no-op in the ordinary case —
    0 of the five entities survived into the flattener across 53 real articles,
    519,997 characters (`docs/measurements/blog-symbol-census.md`). Where it is
    NOT a no-op it is a THIRD decode: triple-encoded input reaches it as
    `&gt;` and leaves as `>`.

    **RULE 1 CANNOT CATCH THIS, WHICH IS WHY THE RULE IS OFF RATHER THAN
    MERELY UNUSED.** Verification is an exact substring match against the text
    the extractor was given, and `verify.py`'s display step resolves against
    the same trafilatura output. Both sides of the check sit downstream of the
    decode. An author who wrote `&gt;` for display gets quoted saying `>` —
    verified, attributed to the right person, and wrong. There is no counting,
    weighting or gating error to find; the corpus is simply not what they typed.

    `unescape exactly once` remains true of THE WALK and was never true of the
    PIPELINE for blog text. Leaving the pass on would encode the belief that
    blog text arrives encoded, and it does not.

    WHY `So` IS NOT PER-PLATFORM YET
    --------------------------------
    Deliberately absent. The `So` rule was read off one Reddit fixture and does
    not generalise, and the blog corpus refused BOTH candidate replacements —
    see the census. Narrowing it now would repeat the mistake in the other
    direction, from a corpus of 2 documents. It stays global and wrong-in-a-
    known-way until there is enough evidence to be right.
    """

    #: Reddit's API emits `&amp; &lt; &gt; &quot; &#39;` and the walk decodes
    #: them exactly once. trafilatura emits none of them; see above.
    decode_entities: bool

    #: Unicode `So`. True everywhere for now, and that is a known defect
    #: rather than a decision — see above.
    substitute_symbols: bool = True


#: Reddit: the API hands us encoded text, so the walk decodes it.
REDDIT_RULES = FlatteningRules(decode_entities=True)

#: Blogs: trafilatura already decoded, twice. A third pass is not a no-op.
BLOG_RULES = FlatteningRules(decode_entities=False)

#: What `flatten` uses when a caller says nothing. Reddit's, because Reddit is
#: what every existing caller and fixture is, and because a wrong default that
#: matches the tested path is easier to find than one that quietly differs.
DEFAULT_RULES = REDDIT_RULES


#: Between documents. Belongs to NO segment, deliberately: a quote spanning it
#: overlaps two documents, so `verify.py` returns SPAN_CROSSES_COMMENTS and
#: rejects it. An unattributable quote cannot be displayed or counted as a
#: voice, and leaving the joiner unmapped makes that automatic rather than a
#: check somebody has to write.
JOINER = "\n\n---\n\n"

#: What Reddit's API emits, and nothing else. Ordered longest-first so `&amp;`
#: is tried before any shorter prefix could match.
ENTITIES: tuple[tuple[str, str], ...] = (
    ("&quot;", '"'),
    ("&amp;", "&"),
    ("&#39;", "'"),
    ("&lt;", "<"),
    ("&gt;", ">"),
)

_MAX_ENTITY = max(len(e) for e, _ in ENTITIES)


@dataclass(frozen=True)
class Segment:
    """One run of the flattened string, mapped back to its source.

    `is_identity` is length equality rather than a flag, so a segment cannot
    claim to be one thing and measure as another.
    """

    flat_start: int
    flat_end: int
    document_id: str
    raw_start: int
    raw_end: int

    @property
    def is_identity(self) -> bool:
        return (self.flat_end - self.flat_start) == (self.raw_end - self.raw_start)

    def as_dict(self) -> dict[str, object]:
        return {
            "flat_start": self.flat_start,
            "flat_end": self.flat_end,
            "document_id": self.document_id,
            "raw_start": self.raw_start,
            "raw_end": self.raw_end,
        }


@dataclass(frozen=True)
class Flattened:
    """The string, its map, and the documents it was built from."""

    text: str
    segments: tuple[Segment, ...]
    member_document_ids: tuple[str, ...]

    def as_offset_map(self) -> list[dict[str, object]]:
        """The `thread_context.offset_map` payload."""
        return [s.as_dict() for s in self.segments]

    @property
    def substitutions(self) -> int:
        return sum(1 for s in self.segments if not s.is_identity)


def substitute(char: str) -> str | None:
    """The bracketed tag for a symbol, or None where the character is kept.

    Category `So` only. `’` is `Pf` and stays — an innocuous sentence followed
    by `[upside_down_face]` is frustration, and an apostrophe is an apostrophe.
    """
    if unicodedata.category(char) != "So":
        return None
    try:
        name = unicodedata.name(char)
    except ValueError:
        # Named by nothing. Substituting it would produce `[]`, which is worse
        # than leaving a character the extractor can at least see.
        return None
    return "[" + name.lower().replace(" ", "_") + "]"


def _entity_at(text: str, i: int) -> tuple[str, str] | None:
    """The entity starting at `i`, or None. Longest match wins."""
    if text[i] != "&":
        return None
    window = text[i : i + _MAX_ENTITY]
    for entity, decoded in ENTITIES:
        if window.startswith(entity):
            return entity, decoded
    return None


def flatten_document(
    text: str,
    document_id: str,
    flat_offset: int = 0,
    rules: FlatteningRules = DEFAULT_RULES,
) -> tuple[str, list[Segment]]:
    """Flatten one document. Returns its text and its segments.

    ONE WALK, LEFT TO RIGHT, so the rewrite order is structural. At each
    position: an entity is consumed whole and emits its decoded character; a
    `So` symbol emits its tag; anything else is copied.

    Identity characters accumulate into a run and are emitted as one segment
    when the run ends — which is what makes a 1,739-character post one segment
    rather than 1,739.
    """
    out: list[str] = []
    segments: list[Segment] = []
    flat = flat_offset
    raw = 0
    run_flat_start: int | None = None
    run_raw_start: int | None = None

    def close_run() -> None:
        nonlocal run_flat_start, run_raw_start
        if run_flat_start is not None:
            segments.append(
                Segment(run_flat_start, flat, document_id, run_raw_start, raw)
            )
            run_flat_start = run_raw_start = None

    while raw < len(text):
        entity = _entity_at(text, raw) if rules.decode_entities else None
        if entity is not None:
            # A SHRINKING substitution: 4-6 raw characters, one flat. Every
            # substitution in the reference fixture grows; this is the other
            # direction, and it is taken whole exactly the same way.
            source, decoded = entity
            close_run()
            out.append(decoded)
            segments.append(
                Segment(flat, flat + len(decoded), document_id, raw, raw + len(source))
            )
            flat += len(decoded)
            raw += len(source)
            continue

        tag = substitute(text[raw]) if rules.substitute_symbols else None
        if tag is not None:
            close_run()
            out.append(tag)
            segments.append(Segment(flat, flat + len(tag), document_id, raw, raw + 1))
            flat += len(tag)
            raw += 1
            continue

        if run_flat_start is None:
            run_flat_start, run_raw_start = flat, raw
        out.append(text[raw])
        flat += 1
        raw += 1

    close_run()
    return "".join(out), segments


def flatten(
    documents: Sequence[tuple[str, str]],
    rules: FlatteningRules = DEFAULT_RULES,
) -> Flattened:
    """Flatten an ORDERED list of `(document_id, raw_text)` into one string.

    Selection and ranking are not this function's job — it takes the documents
    it is given, in the order it is given them, so the flattening rules can be
    tested against a known map without a selection policy in the way.

    `rules` is per PLATFORM and applies to every document in the call, which is
    correct because a thread's members all come from one platform. If a mixed
    thread ever exists, this signature is the thing that has to change, and it
    will fail to compile rather than silently apply Reddit's rules to a blog.
    """
    parts: list[str] = []
    segments: list[Segment] = []
    ids: list[str] = []
    flat = 0

    for index, (document_id, raw_text) in enumerate(documents):
        if index:
            parts.append(JOINER)
            flat += len(JOINER)
        text, produced = flatten_document(
            raw_text, document_id, flat_offset=flat, rules=rules
        )
        parts.append(text)
        segments.extend(produced)
        ids.append(document_id)
        flat += len(text)

    return Flattened(
        text="".join(parts),
        segments=tuple(segments),
        member_document_ids=tuple(ids),
    )
