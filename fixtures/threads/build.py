"""Build a `thread_context` fixture from a real harvested Reddit tree.

WHY THIS IS A SCRIPT AND NOT A HAND-WRITTEN FILE

The first offset map in this repo was hand-written and had an off-by-one: the
space before an emoji belongs to the identity run, not to the substitution.
Four tests failed and it took computing the spans to see it. A map that looks
right and resolves one character wrong is exactly the failure `verify.py`
exists to prevent, so writing one by hand to test it is circular.

So the map is computed here, from the same normalisation that produces the
flattened text, and the two cannot drift apart because one produces the other.

WHAT THIS IS NOT

**Not E3.** `collect/assemble/` is Engineer 1's and is authoritative. This is
fixture tooling that produces the same SHAPE so `judge/` can meet it before the
real assembler exists — the swap-rather-than-integration the plan asks for. If
the two disagree when E3 lands, E3 is right and this regenerates.

Two things it deliberately does not copy: child selection is by score alone,
where E3 ranks by `specificity_score x log(1 + engagement)`, because
`specificity_score` is computed at ingest and not present in a raw API payload.
And it takes the whole selected comment rather than a window.

SEGMENTS, NOT COMMENTS

`offset_map` carries one segment per contiguous run where flat and raw agree,
plus one per substitution. An emoji becoming `[loudly_crying_face]` is one
character becoming twenty, so a constant per-comment delta resolves past the
end of the document — which is how the bug presented the first time, silently,
against the wrong text rather than failing.

    python fixtures/threads/build.py
"""

from __future__ import annotations

import html
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE = ROOT / "fixtures" / "reddit" / "thread-1u1b22l-getPostComments.json"
OUTPUT = ROOT / "fixtures" / "threads" / "thread-1u1b22l.json"

#: Root plus six children. The plan says three to five; six is taken because
#: the selection is forced to include specific shapes rather than whatever
#: ranked highest - a deleted body, two emoji documents, a run of full
#: blocks, and an HTML entity. A fixture that happens not to contain them
#: tests less than it appears to.
CHILD_COUNT = 6

#: Length-CHANGING substitutions are the only ones that produce a segment
#: boundary. A no-break space becoming a space is one character for one and
#: leaves the map identical, so it is normalised and not recorded.
IDENTITY_LENGTH = {" ": " ", " ": " ", " ": " "}

#: HTML entities, and the case this fixture could not reach until now.
#:
#: Every symbol substitution above GROWS - one character into twelve or more -
#: so a sign error in the segment arithmetic is invisible against them. `&gt;`
#: SHRINKS, four raw characters to one flat, and it is the only direction that
#: exercises the other sign. Engineer 1 asked for it after writing an
#: independent flattener that matched this one byte for byte, which agreement
#: could not have covered a case neither implementation had ever seen.
#:
#: They also run the opposite way in MEANING. An emoji becoming
#: `[loudly_crying_face]` is internal representation replacing what was typed.
#: An entity becoming `>` is transport encoding removed to REVEAL what was
#: typed - the reader sees `>` because that is what the author wrote.
#:
#: UNESCAPE-EXACTLY-ONCE IS STRUCTURAL RATHER THAN A RULE TO REMEMBER. Both
#: rewrites happen in one left-to-right walk that advances past whatever it
#: consumed, so `&amp;gt;` emits `&`, resumes after it, and never re-examines
#: `gt;` - the text stays `&gt;`. Nothing has to track whether it already
#: decoded. This payload carries no double-encoded entity, so that property is
#: argued rather than tested.
_ENTITY = re.compile(r"&(?:#\d{1,7}|#[xX][0-9a-fA-F]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});")


@dataclass(frozen=True)
class Segment:
    """One entry in `offset_map`. Half-open on both sides."""

    flat_start: int
    flat_end: int
    document_id: str
    raw_start: int
    raw_end: int


def _is_substituted(ch: str) -> bool:
    """Emoji and pictographs get a bracketed name; nothing else does.

    Deliberately narrow. Typographic quotes and dashes are left alone: the
    sieve normalises those at match time, and substituting them here would put
    a rendering decision in the wrong stage.
    """
    return unicodedata.category(ch) == "So" or ord(ch) > 0x1F000


def _tag_for(ch: str) -> str:
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return f"[u{ord(ch):04x}]"
    return "[" + name.lower().replace(" ", "_").replace("-", "_") + "]"


def flatten(document_id: str, raw: str, flat_offset: int) -> tuple[str, list[Segment]]:
    """One document's contribution to the flattened text, plus its segments.

    Returns the flattened chunk and the segments mapping it back. Identity runs
    are coalesced, so a document with no substitutions yields exactly one
    segment rather than one per character.
    """
    out: list[str] = []
    segments: list[Segment] = []
    run_flat_start = flat_offset
    run_raw_start = 0
    flat = flat_offset

    def close_run(raw_pos: int) -> None:
        nonlocal run_flat_start, run_raw_start
        if flat > run_flat_start:
            segments.append(Segment(run_flat_start, flat, document_id, run_raw_start, raw_pos))
        run_flat_start = flat
        run_raw_start = raw_pos

    raw_pos = 0
    while raw_pos < len(raw):
        entity = _ENTITY.match(raw, raw_pos)
        if entity is not None:
            decoded = html.unescape(entity.group(0))
            if decoded != entity.group(0):
                close_run(raw_pos)
                out.append(decoded)
                segments.append(
                    Segment(
                        flat,
                        flat + len(decoded),
                        document_id,
                        raw_pos,
                        entity.end(),
                    )
                )
                flat += len(decoded)
                # Advance past the WHOLE entity. This is what makes
                # unescape-exactly-once a property of the walk: the character
                # just emitted is never looked at again.
                raw_pos = entity.end()
                run_flat_start = flat
                run_raw_start = raw_pos
                continue

        ch = raw[raw_pos]
        if ch in IDENTITY_LENGTH:
            out.append(IDENTITY_LENGTH[ch])
            flat += 1
            raw_pos += 1
            continue
        if _is_substituted(ch):
            close_run(raw_pos)
            tag = _tag_for(ch)
            out.append(tag)
            segments.append(Segment(flat, flat + len(tag), document_id, raw_pos, raw_pos + 1))
            flat += len(tag)
            raw_pos += 1
            run_flat_start = flat
            run_raw_start = raw_pos
            continue
        out.append(ch)
        flat += 1
        raw_pos += 1

    close_run(len(raw))
    return "".join(out), segments


def _walk(children: list[dict], out: list[dict]) -> None:
    for node in children:
        data = node.get("data", {})
        if "body" in data:
            out.append(data)
            replies = data.get("replies")
            if isinstance(replies, dict):
                _walk(replies.get("data", {}).get("children", []), out)


def document_id_for(thing: dict, expected_prefix: str) -> str:
    """The id `collect/` stores, which is the FULLNAME and never the bare id.

    `collect/adapters/reddit.py` documents it on the field itself - `external_id:
    str  # t3_... - the fullname, never the bare id` - and this builder used
    `thing["id"]` instead, producing `reddit:oqosfnq` against a document table
    holding `reddit:t1_oqosfnq`.

    `raw_text_of` is keyed by document_id, so every lookup would have missed and
    `verify.py` would have returned RAW_TEXT_MISSING for every quote in the
    thread - a naming failure presenting as a storage failure, on the one
    artefact that cannot be reconstructed after the fact.

    ENGINEER 1'S INDEPENDENT FLATTENER DID NOT CATCH THIS, and the reason is
    worth more than the fix. It reproduced this fixture byte for byte, 2,481
    characters and all 20 segments, first run. But `document_id` is an INPUT to
    a flattener, not an output: the test handed both implementations the same
    ids and compared text and offsets. An id-convention difference is invisible
    to that comparison by construction. It surfaced only by writing a row to
    Postgres and reading it back with `raw_text_of` rebuilt from `document`.

    So: a variable the test supplies is a variable the test cannot check. Where
    two components must agree about a value, round-trip it through the real
    carrier rather than handing it to both.

    Raising rather than falling back to `id` is the point. A silent fallback
    would restore exactly the defect being fixed, and it would do it on a
    payload shape nobody was looking at.
    """
    fullname = thing.get("name")
    if not isinstance(fullname, str) or not fullname.startswith(expected_prefix):
        raise ValueError(
            f"no {expected_prefix}... fullname on {thing.get('id')!r}: got "
            f"{fullname!r}. `collect/` keys `document` by the fullname, so a "
            f"bare id here is a fixture that cannot be read back."
        )
    return f"reddit:{fullname}"


def build() -> dict:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    post = payload["data"][0]["data"]["children"][0]["data"]
    comments: list[dict] = []
    _walk(payload["data"][1]["data"]["children"], comments)

    root_id = document_id_for(post, "t3_")
    root_text = f"{post['title']}\n\n{post.get('selftext', '')}".strip()

    ranked = sorted(comments, key=lambda c: c.get("score", 0), reverse=True)

    # Cases the assembler will meet on its first real thread, forced in rather
    # than hoped for. A fixture that happens not to contain them tests less
    # than it appears to, and the first attempt here selected six documents
    # with one substitution between them.
    def first(predicate, exclude: list[dict]) -> dict | None:
        return next(
            (c for c in comments if predicate(c) and not any(c is e for e in exclude)),
            None,
        )

    def has_emoji(c: dict) -> bool:
        return any(ord(ch) > 0x1F000 for ch in c["body"])

    forced: list[dict] = []
    for predicate in (
        # a body that is not there. A different offset problem from a body
        # with an emoji in it, and the assembler meets both
        # A deleted body: no text to quote, and an offset-map case nothing
        # else here reaches.
        #
        # ⚠ THIS DOCUMENT CANNOT CURRENTLY BE STORED. `collect/`'s
        # `write_documents` requires `author_id`, and `write_authors` correctly
        # skips authorless comments, so rebuilding this thread from staging
        # yields FOUR documents where this fixture has seven. E1 read that as
        # two correct rules producing an impossible state.
        #
        # It is one rule stricter than the contract. `document.author_id` is
        # NULLABLE - `author_id text REFERENCES author(id)` with no NOT NULL -
        # so the schema permits an authorless document and the writer does not.
        # Raised with E1 rather than worked around here; either answer is fine
        # for evidence, because a removed body has nothing to quote.
        #
        # Kept in the fixture regardless: this artefact is adversarial by
        # design, and an absent body is a different offset problem from a
        # substituted one whether or not a row for it exists.
        lambda c: c["body"] in ("[deleted]", "[removed]"),
        # one raw character becoming twenty flat ones
        has_emoji,
        # a SECOND emoji document, so substitutions appear in more than one
        # comment and a per-document delta cannot accidentally work
        has_emoji,
        # U+2588 FULL BLOCK: category So but not an emoji, seven of them in one
        # comment, so a single document carries a run of substitutions
        lambda c: "█" in c["body"],
        # AN HTML ENTITY, and the only SHRINKING substitution available. Every
        # symbol above grows one character into twelve or more; `&gt;` is four
        # raw characters becoming one flat. A sign error in the segment
        # arithmetic is invisible against growth alone, which is what this
        # fixture could not reach before. Engineer 1's request on the
        # independently-written flattener.
        lambda c: "&gt;" in c["body"] or "&lt;" in c["body"],
    ):
        found = first(predicate, forced)
        if found is not None:
            forced.append(found)

    selected = (forced + [c for c in ranked if not any(c is f for f in forced)])[:CHILD_COUNT]

    documents = [(root_id, root_text)] + [(document_id_for(c, "t1_"), c["body"]) for c in selected]

    parts: list[str] = []
    segments: list[Segment] = []
    raw_text_of: dict[str, str] = {}
    flat = 0
    separator = "\n\n---\n\n"

    for index, (doc_id, raw) in enumerate(documents):
        if index:
            parts.append(separator)
            flat += len(separator)
        chunk, doc_segments = flatten(doc_id, raw, flat)
        parts.append(chunk)
        segments.extend(doc_segments)
        raw_text_of[doc_id] = raw
        flat += len(chunk)

    return {
        "thread_context_id": f"tc:{post['id']}",
        "thread_root_id": root_id,
        "member_document_ids": [doc_id for doc_id, _ in documents],
        "flattened_text": "".join(parts),
        "offset_map": [asdict(s) for s in segments],
        "raw_text_of": raw_text_of,
        "provenance": {
            "source": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
            "built_by": "fixtures/threads/build.py",
            "note": (
                "Fixture tooling, not E3. collect/assemble/ is authoritative; "
                "if the two disagree, regenerate this from that."
            ),
            # The Reddit fetch path has never called assert_terms_reviewed, so
            # the payload this is derived from was gathered before any ruling
            # existed. Recorded rather than assumed: if the ruling goes against
            # us, this fixture goes with the payload, and reconstructing which
            # artefacts depend on it afterwards is far more expensive than one
            # line now.
            "terms_review": "pending - see the Reddit ruling; payload predates it",
        },
    }


def main() -> None:
    fixture = build()
    OUTPUT.write_text(json.dumps(fixture, indent=2, ensure_ascii=False), encoding="utf-8")
    substitutions = sum(
        1
        for s in fixture["offset_map"]
        if (s["flat_end"] - s["flat_start"]) != (s["raw_end"] - s["raw_start"])
    )
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    print(f"  documents      {len(fixture['member_document_ids'])}")
    print(f"  flattened      {len(fixture['flattened_text'])} chars")
    print(f"  segments       {len(fixture['offset_map'])}")
    print(f"  substitutions  {substitutions}")


if __name__ == "__main__":
    main()
