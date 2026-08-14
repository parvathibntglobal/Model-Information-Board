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

`target_language` stays None on purpose. Language is *recorded* on the
document, never filtered on: a non-English post is translated with the
original retained, and an extractor that dropped it would produce an absence
nobody could see.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from collect.ids import content_hash


@dataclass(frozen=True)
class ExtractionOptions:
    """What gets passed to `trafilatura.extract`, and nothing else does."""

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

    def as_kwargs(self) -> dict[str, object]:
        return asdict(self)

    def fingerprint(self) -> str:
        """A short hash of the options, for `pipeline_version`.

        Twelve hex characters of the sorted option list. Enough to make two
        runs with different options visibly different, short enough to sit in
        a version string a human reads.
        """
        payload = ";".join(f"{key}={value}" for key, value in sorted(asdict(self).items()))
        return content_hash(payload)[:12]


#: The options every blog extraction uses. One instance, so "which options ran"
#: is never a question about a call site.
DEFAULT_EXTRACTION = ExtractionOptions()


def extraction_version(library_version: str, options: ExtractionOptions | None = None) -> str:
    """`trafilatura-2.2.0+opts-ab12cd34ef56` — what produced a flattened text.

    The library version belongs in here as much as the options do: trafilatura
    changing its boilerplate heuristics moves offsets exactly the way changing
    `include_formatting` would, and NFR-4 requires the difference be visible
    rather than inferred.
    """
    options = options or DEFAULT_EXTRACTION
    return f"trafilatura-{library_version}+opts-{options.fingerprint()}"
