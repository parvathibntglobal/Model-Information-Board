"""The seating check: an entry seated without attestation that the corpus now attests.

WHY THIS IS NOT A STALENESS CHECK, which was the first proposal. "Is this entry
still provisional" fires on every launch-window entry forever, including the ones
that are *legitimately* provisional — a model nobody has written a sentence about
is correctly seated by its release date and there is nothing to do about it. A
check that fires on a correct state gets muted, and a muted check is worse than no
check because it looks like coverage.

`seated_by: launch-window` AND `mentions > 0` is a state that is **wrong and
fixable by looking**. The entry was seated because nothing was observed; something
has since been observed; so the seat was made on an assumption the corpus has
disproved, and the surfaces under it are derivations where an attested form now
exists.

**WHY IT LANDS BEFORE THE SEATS, NOT AFTER.** Engineer 2's argument and it decides
the order: 18 primaries are about to be guessed for models nobody has discussed.
A wrong seat with no flag is invisible. A wrong seat with a flag that fires on the
first mention is a to-do item.

**WHY IT IS A TEST AND NOT A NIGHTLY REPORT.** Same reason the CI ordering finding
established: a report is read when somebody chooses to read it, and the thing that
makes a check load-bearing is that it runs whether or not anyone remembered. It
needs no database and no network — it reads one file in the tree.

`provisional` DOES NOT EXIST AS A FIELD, and this file is where that is written
down so nobody has to infer it from reading the YAML. `to_yaml` emits
`seated_by: attested | launch-window`; `launch-window` IS the provisional state,
and its own generated comment says so — "no attested surface, so every form below
is derived". The check keys on `seated_by`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ARTIFACT = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "proposals"
    / "alias-surfaces-tracked-set.yaml"
)

#: `to_yaml` writes mentions into a trailing COMMENT, not a key, so the count is
#: not reachable by `yaml.safe_load`. Parsing prose is the shape that has burned
#: this repo repeatedly, so every parse below is SIZED: if the generator's format
#: changes, the counts drop to zero and `test_the_parse_still_finds_its_inputs`
#: fails rather than this check passing over an empty set (habit 4).
#:
#: The durable fix is a `mentions:` key in `to_yaml`. That is a change to the
#: artifact Engineer 2 is reviewing, so it is proposed rather than taken.
_MENTIONS = re.compile(r"^\s+(?:surface:|- )\s*(.+?)\s+# attested (\d+) mentions", re.M)
_SEATED_BY = re.compile(r"seated_by:\s*(\S+)")

PROVISIONAL = "launch-window"
ATTESTED = "attested"


def _entries() -> list[tuple[str, str | None, list[tuple[str, int]]]]:
    """One tuple per proposal: canonical id, `seated_by`, attested (surface, count)."""
    text = ARTIFACT.read_text(encoding="utf-8")
    out = []
    for block in re.split(r"\n  - canonical_id: ", text)[1:]:
        canonical_id = block.split("\n")[0].strip()
        seat = _SEATED_BY.search(block)
        mentions = [(s.strip(), int(n)) for s, n in _MENTIONS.findall(block)]
        out.append((canonical_id, seat.group(1) if seat else None, mentions))
    return out


@pytest.fixture(scope="module")
def entries():
    if not ARTIFACT.exists():
        pytest.fail(
            f"{ARTIFACT.name} is not in the tree. It was committed to a branch with "
            "no upstream once already, which is why Engineer 2 could not read it for "
            "two weeks — so its absence fails rather than skips."
        )
    return _entries()


def test_the_parse_still_finds_its_inputs(entries):
    """The guard on every other test in this file.

    A regex over generated prose stops matching silently, and a check over an
    empty set passes. So the population is asserted before anything is concluded
    from it: entries exist, both seating grounds are represented, and mentions
    were actually read off the comments.
    """
    assert len(entries) >= 40, f"only {len(entries)} entries parsed — format changed?"

    grounds = {seat for _, seat, _ in entries}
    assert PROVISIONAL in grounds, f"no {PROVISIONAL!r} entries parsed; got {grounds}"
    assert ATTESTED in grounds, f"no {ATTESTED!r} entries parsed; got {grounds}"
    assert None not in grounds, "an entry parsed with no seated_by at all"

    with_mentions = sum(1 for _, _, m in entries if m)
    assert with_mentions >= 20, (
        f"only {with_mentions} entries had a parseable mention count. The comment "
        "format in to_yaml has probably changed — fix this parse before trusting "
        "the seating check, which would otherwise pass over nothing."
    )


def test_no_provisional_entry_has_been_attested_since(entries):
    """`seated_by: launch-window` AND mentions > 0 — seated blind, observed since.

    The message names THE SURFACE AND THE COUNT, not the model. Engineer 2's
    refinement and the reason is repair: "gemini 3.6 flash is provisional and now
    has 13 mentions" tells someone what to do. "3 entries are stale" sends them to
    find out which, and that is a second task rather than a finding.
    """
    caught = [
        (canonical_id, surface, count)
        for canonical_id, seat, mentions in entries
        if seat == PROVISIONAL
        for surface, count in mentions
    ]
    if caught:
        lines = "\n".join(
            f"    {surface!r} is provisional and now has {count} mentions "
            f"({canonical_id})"
            for canonical_id, surface, count in sorted(
                caught, key=lambda row: -row[2]
            )
        )
        pytest.fail(
            f"{len(caught)} provisional surface(s) the corpus now attests. Each was "
            f"seated by its release date because nothing had been observed, and "
            f"something has been:\n{lines}\n"
            "Reseat as attested, or record why the mentions do not attribute."
        )


def test_an_attested_seat_is_never_also_provisional(entries):
    """The two grounds are exclusive, so one entry cannot claim both."""
    for canonical_id, seat, _ in entries:
        assert seat in (ATTESTED, PROVISIONAL), (
            f"{canonical_id} has seated_by={seat!r}, which is neither "
            f"{ATTESTED!r} nor {PROVISIONAL!r} — a third ground was added without "
            "deciding what the seating check does with it"
        )


def test_the_check_would_notice_a_new_mention(entries):
    """Break-it-on-purpose, in the file, so the condition is known to fire.

    Habit 3. A check that has never been seen to fail is a check nobody has
    tested, and this one gates 18 guessed primaries.
    """
    fabricated = [("vendor/model-x", PROVISIONAL, [("model x", 1)])]
    caught = [
        (cid, s, c)
        for cid, seat, mentions in fabricated
        if seat == PROVISIONAL
        for s, c in mentions
    ]
    assert caught == [("vendor/model-x", "model x", 1)]

    unseen = [("vendor/model-y", PROVISIONAL, [])]
    assert not [
        (cid, s, c)
        for cid, seat, mentions in unseen
        if seat == PROVISIONAL
        for s, c in mentions
    ], "a provisional entry with no mentions must NOT fire — that is the muting case"
