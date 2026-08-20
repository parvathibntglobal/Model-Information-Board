"""Article-extraction options, pinned and fingerprinted.

These are not preferences. The string trafilatura returns **is** the byte
string the extractor sees and quotes are verified against, so an option change
moves every offset in every `offset_map` derived after it. Two of them are
correctness rather than tuning:

  include_comments=False   trafilatura's default is True. Blog comments are
                           other people's words; extracted into the article
                           body they are attributed to the post author. That
                           breaks rule 1 at the source — the quote would
                           verify by substring match against text the author
                           never wrote.

  deduplicate=False        trafilatura's deduplication silently drops repeated
                           segments. A quote that verified yesterday would
                           stop verifying after a library upgrade, with
                           nothing to say why.

**Rule 5 says these belong in `contract/`, and they are not there yet.** They
are config: they change what the pipeline produces without a code change being
conceptually necessary. Putting them in `contract/sources.yaml` is part of the
harvest-tables conversation, not something to do unilaterally in this lane. In
the meantime they live here, frozen, with a fingerprint so a change cannot
happen quietly.

TWO ROSTERS, ONE FINGERPRINT
----------------------------
`pipeline` is OURS. It is not a trafilatura option, it is never passed to
`trafilatura.extract`, and it is in the fingerprint because our own steps move
offsets exactly the way trafilatura's options do.

That gap was real and load-bearing. `extraction_version` read
`trafilatura-{version}+opts-{fingerprint}` and covered trafilatura's options
alone, so any pre-processing of ours could rewrite the byte string every offset
in every `offset_map` is measured against while the identifier stayed the same.
That is UNDER-identification, which is the direction that matters, and six lines
between the bytes arriving and the text being returned is all it takes. The gap
is small only because nobody has touched those lines yet.

So every field belongs to exactly one roster - `_TRAFILATURA_KEYS` or
`_PIPELINE_KEYS` - the fingerprint covers both, and only the first reaches the
library. **A field in neither raises.** A fingerprint whose whole job is to
change when its inputs change has to refuse an input it does not know rather
than silently fold it in; otherwise it is a hash of whatever happened to be in
the dict, and what it ranges over is whatever somebody last added.

WHAT `pipeline` DOES NOT COVER, SAID HERE RATHER THAN LEFT TO BE DISCOVERED
---------------------------------------------------------------------------
It is an integer somebody bumps. Editing a pre-processing step and not bumping
it leaves the identifier unchanged, which is the convention that already failed
once - `PIPELINE_VERSION` was not bumped when the scorer changed, and a
`thread_context` row kept a stale id
(`docs/measurements/first-thread-context.md` section 4).

The narrowing is the point rather than the cure: this convention names six lines
in one module instead of every change to `collect/`, which is small enough to
state and therefore small enough to check. The check itself is not here - it is
a fingerprint of the PRODUCED TEXT, one table over. A configuration identifier
selects work before it happens; only a content identifier can say what was
actually done. Neither replaces the other, and collapsing them is what makes a
re-fetch decision undecidable. `docs/measurements/README.md`.

`target_language` stays None on purpose. Language is *recorded* on the
document, never filtered on: a non-English post is translated with the
original retained, and an extractor that dropped it would produce an absence
nobody could see.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from collect.ids import content_hash

#: Trafilatura's surface. Fingerprinted AND passed to `trafilatura.extract`.
_TRAFILATURA_KEYS: frozenset[str] = frozenset(
    {
        "include_comments",
        "include_formatting",
        "include_tables",
        "include_links",
        "deduplicate",
        "favor_precision",
        "favor_recall",
        "output_format",
    }
)

#: Ours. Fingerprinted and NEVER passed. See the module docstring.
_PIPELINE_KEYS: frozenset[str] = frozenset({"pipeline"})


class UnrosteredOption(RuntimeError):
    """A field the rosters do not account for, in either direction.

    Raised rather than resolved by a default, because both defaults are wrong.
    Silently fingerprinting an unknown field makes the fingerprint a hash of
    whatever the dataclass currently holds; silently skipping it makes the
    fingerprint stop covering an input that moves offsets. Neither is visible
    afterwards.

    Adding an option is a two-line change - the field, and the roster it
    belongs to. This is what makes the second line non-optional.
    """


@dataclass(frozen=True)
class ExtractionOptions:
    """Everything that decides the byte string, in one place.

    Two kinds of member, and `as_kwargs` is the boundary: the eight in
    `_TRAFILATURA_KEYS` are passed to `trafilatura.extract`, and `pipeline` is
    ours and is not. Both are fingerprinted, because both move offsets.

    This class was documented as *"what gets passed to `trafilatura.extract`,
    and nothing else does"*, which was true of the fields and false of the
    identifier those fields produce - it left our own processing outside
    `extraction_version` entirely.
    """

    #: Rule 1. See the module docstring — this one is an attribution defect.
    include_comments: bool = False

    #: Code fences, error strings and numbers-with-units are the specificity
    #: signal triage ranks on and the extractor quotes. Dropping formatting
    #: would flatten a diff into prose.
    include_formatting: bool = True

    #: Tables carry pricing and benchmark figures in exactly the posts worth
    #: harvesting.
    include_tables: bool = True

    #: Link *text* is kept either way; this is about inlining URLs, which add
    #: bytes to every offset without adding a claim.
    include_links: bool = False

    #: See the module docstring. Byte stability beats tidiness.
    deduplicate: bool = False

    #: Balanced. Precision-vs-recall is a calibration to make against
    #: `fixtures/golden/extraction/`, not a guess to bake in now.
    favor_precision: bool = False
    favor_recall: bool = False

    #: Plain text. The extractor reads prose; XML/JSON output would put markup
    #: inside the byte string every quote offset is measured against.
    output_format: str = "txt"

    #: OURS, NOT TRAFILATURA'S, and never passed to `trafilatura.extract`.
    #:
    #: The generation of the processing this lane does AROUND the extraction
    #: call - today, everything in `extract_article_text` between the bytes
    #: arriving and the text being returned. Bump it when any of that changes.
    #:
    #: The footnote back-link finding is the one waiting on this. `↩` is
    #: chrome the renderer emitted, in 10 of 106 documents, and stripping it
    #: belongs at extraction rather than in the flattener where it would look
    #: solved (`docs/measurements/blog-symbol-census.md` section 5). That strip
    #: moves every offset after the first one in every article that has one,
    #: and before this field existed it would have done so under an unchanged
    #: `extraction_version`.
    #: BUMPED 1 -> 2 (2026-08-20): the recent-articles template strip in
    #: `extract_article_text`. The second change this field was made for, after
    #: the footnote back-link, and for the same reason - it belongs at extraction
    #: rather than in the flattener where it would look solved.
    #:
    #: NOTE THAT THIS CHANGES NOTHING OBSERVABLE TODAY. `extraction_version` is
    #: computed and persisted NOWHERE (`thread.py:38`), and the thread_context id
    #: carries `pipeline_version` instead - so a re-flatten under this bump has
    #: the same id and ON CONFLICT DO NOTHING drops it. The bump is correct and
    #: inert until #5 A4 lands.
    pipeline: int = 2

    def _rostered(self) -> dict[str, object]:
        """Every field, checked against the rosters in both directions.

        A field on the class and in neither roster is an input nobody decided
        about. A roster entry with no field behind it is a roster that lies
        about what the fingerprint covers - and that one is the quiet
        direction, because removing a field still changes the fingerprint, so
        the value looks healthy while its scope has narrowed.
        """
        fields = asdict(self)
        unclaimed = sorted(set(fields) - _TRAFILATURA_KEYS - _PIPELINE_KEYS)
        if unclaimed:
            raise UnrosteredOption(
                f"{', '.join(unclaimed)}: on ExtractionOptions and in neither "
                "roster. Add each to _TRAFILATURA_KEYS if trafilatura takes it, "
                "or to _PIPELINE_KEYS if it names something we do. Both are "
                "fingerprinted; only the first is passed to trafilatura.extract."
            )
        missing = sorted((_TRAFILATURA_KEYS | _PIPELINE_KEYS) - set(fields))
        if missing:
            raise UnrosteredOption(
                f"{', '.join(missing)}: rostered, with no field behind it. The "
                "fingerprint now covers less than the roster says it does."
            )
        return fields

    def as_kwargs(self) -> dict[str, object]:
        """Only what `trafilatura.extract` takes. `pipeline` is ours and is not."""
        return {
            key: value
            for key, value in self._rostered().items()
            if key in _TRAFILATURA_KEYS
        }

    def fingerprint(self) -> str:
        """A short hash of EVERY rostered option - trafilatura's and ours.

        Twelve hex characters of the sorted option list. Enough to make two
        runs with different options visibly different, short enough to sit in
        a version string a human reads.

        It covers `pipeline`, so this value moved when that field landed. Text
        produced before then carries the old fingerprint and cannot be told
        apart from text produced after it under an unchanged pipeline. That is
        the one thing a configuration identifier cannot fix retrospectively,
        and it is recorded rather than papered over - see
        `docs/measurements/README.md` and the stored-corpus note in
        `docs/measurements/blog-symbol-census.md`.
        """
        payload = ";".join(f"{key}={value}" for key, value in sorted(self._rostered().items()))
        return content_hash(payload)[:12]


#: The options every blog extraction uses. One instance, so "which options ran"
#: is never a question about a call site.
DEFAULT_EXTRACTION = ExtractionOptions()


def extraction_version(library_version: str, options: ExtractionOptions | None = None) -> str:
    """`trafilatura-2.2.0+pipeline-1+opts-ab12cd34ef56` — what produced a text.

    The library version belongs in here as much as the options do: trafilatura
    changing its boilerplate heuristics moves offsets exactly the way changing
    `include_formatting` would, and NFR-4 requires the difference be visible
    rather than inferred. The same argument is why `pipeline` is here, and it
    was the missing third term.

    The generation appears twice - legibly, and inside the fingerprint. That is
    one value shown two ways rather than two identifiers: both read the same
    field, so they cannot disagree. It is spelled out because "which generation
    produced this row" is a question somebody asks while reading a row, and
    twelve hex characters do not answer it.
    """
    options = options or DEFAULT_EXTRACTION
    return (
        f"trafilatura-{library_version}"
        f"+pipeline-{options.pipeline}"
        f"+opts-{options.fingerprint()}"
    )
