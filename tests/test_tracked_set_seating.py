"""The seating check: an entry seated without attestation that the corpus now attests.

WHY THIS IS NOT A STALENESS CHECK, which was the first proposal. "Is this entry
still provisional" fires on every launch-window entry forever, including the ones
that are *legitimately* provisional — a model nobody has written a sentence about
is correctly seated by its release date and there is nothing to do about it. A
check that fires on a correct state gets muted, and a muted check is worse than no
check because it looks like coverage.

**THE FIRST VERSION OF THIS CONDITION WAS WRONG, AND IT WAS WRONG IN EXACTLY THE
WAY THE PARAGRAPH ABOVE WARNS ABOUT.** It read `launch-window AND mentions > 0`,
on the belief that `launch-window` meant "nothing was observed". It does not.
`cli.py` sets it whenever `BY_MENTIONS` is absent, and `BY_MENTIONS` requires
`mentions >= mention_floor` — so a model with 13 mentions against a floor of 20 is
seated by the window, is attested, and is seated **exactly as the policy
intends**. The condition fired on 5 of the launch-window entries, all correct, and
a check that fires on a correct state is the one that gets muted.

The condition that names a real error is `launch-window` AND
`mentions >= mention_floor`: the entry qualifies BY COUNT and was not credited for
it. That is unambiguous, and today it finds nothing, which is the honest result
rather than a disappointing one.

What the wrong version did surface was a genuine defect one layer over — the
generated annotation on those 5 rows read "no attested surface, so every form
below is derived" while the next line read `attested 13 mentions`. Rule 4: an
absence claimed where evidence exists. Fixed in `to_yaml`, and the floor now
travels in the file's `policy:` header, because without it neither a reader nor
this check can tell "below the floor" from "never observed".

**WHY IT LANDS BEFORE THE SEATS, NOT AFTER.** Engineer 2's argument and it decides
the order: **17** primaries are about to be guessed for models nobody has
discussed. A wrong seat with no flag is invisible — the model never resolves, and
that reads as nobody discussing it, which is rule 4 at the point where nobody is
looking. A wrong seat with a flag that fires on the first mention is a to-do item.

(17, not 18: `~deepseek/deepseek-v4-flash-latest` was removed from the artifact on
2026-08-19. A routing pointer cannot be seated correctly at all - it names
whatever resolves this week and has no capability to report on.)

**WHY IT IS A TEST AND NOT A NIGHTLY REPORT.** Same reason the CI ordering finding
established: a report is read when somebody chooses to read it, and the thing that
makes a check load-bearing is that it runs whether or not anyone remembered. It
needs no database and no network — it reads one file in the tree.

`provisional` DOES NOT EXIST AS A FIELD, and this file is where that is written
down so nobody has to infer it from reading the YAML. `to_yaml` emits
`seated_by: attested | launch-window`, and `launch-window` IS the provisional
state — but it means "did not clear the mention floor", not "unobserved". The
check keys on `seated_by` and on the floor beside it.
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
_MENTIONS = re.compile(
    r"^\s+(?:surface:|- )\s*(.+?)\s+# attested (\d+) mentions(?: \[([^\]]*)\])?", re.M
)
_SPLIT_PART = re.compile(r"([a-z-]+)\s+(\d+)")
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
        mentions = []
        for surface, count, split in _MENTIONS.findall(block):
            by_source = {k: int(v) for k, v in _SPLIT_PART.findall(split or "")}
            mentions.append((surface.strip(), int(count), by_source))
        out.append((canonical_id, seat.group(1) if seat else None, mentions))
    return out


@pytest.fixture(scope="module")
def floor() -> int:
    """The mention floor, read from the artifact's own `policy:` header.

    **Not a constant in this file.** A threshold copied into the checker is a
    second place for it to be wrong, and the whole reason the first version of
    this check misfired is that the floor was nowhere near the seats it explains.
    So it travels in the file (rule 7) and is read from there; if the header goes
    missing this fails rather than falling back to a guess (rule 6).
    """
    text = ARTIFACT.read_text(encoding="utf-8")
    match = re.search(r"^\s+mention_floor:\s*(\d+)", text, re.M)
    assert match, (
        "no `policy: mention_floor:` in the artifact. `seated_by: launch-window` "
        "cannot be checked without it — it means 'below the floor', and which "
        "floor is the whole question."
    )
    return int(match.group(1))


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


def test_no_provisional_entry_already_qualifies_by_count(entries, floor):
    """`launch-window` AND mentions >= floor — qualifies by count, not credited.

    The message names THE SURFACE AND THE COUNT, not the model. Engineer 2's
    refinement, and the reason is repair: "gemini 3.6 flash is provisional and now
    has 38 mentions" tells someone what to do; "3 entries are stale" sends them to
    find out which, which is a second task rather than a finding.

    Totals per entry, not per surface: the floor is compared against a model's
    attested mentions, and one model's forms are not separate evidence.
    """
    caught = []
    for canonical_id, seat, mentions in entries:
        if seat != PROVISIONAL or not mentions or _total(mentions) < floor:
            continue
        top = max(mentions, key=lambda row: row[1])[0]
        caught.append((canonical_id, top, _total(mentions), _slice_share(mentions)))

    if caught:
        lines = "\n".join(
            f"    {surface!r} is provisional and now has {count} mentions "
            f"({canonical_id}) — {_describe_population(share)}"
            for canonical_id, surface, count, share in sorted(
                caught, key=lambda row: -row[2]
            )
        )
        pytest.fail(
            f"{len(caught)} provisional entry/entries already clear the floor of "
            f"{floor}. Each qualifies BY COUNT and was seated by its release date "
            f"anyway, so `seated_by` understates the evidence:\n{lines}\n"
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


def _total(mentions) -> int:
    return sum(row[1] for row in mentions)


def _slice_share(mentions) -> float | None:
    """Fraction of the total that came from `substitution-slice`, or None.

    None when no surface carried a split - absent, not 0.0, because 0.0 would
    read as "measured, none from the slice" (rule 6).
    """
    agg: dict[str, int] = {}
    for _surface, _count, by_source in mentions:
        for name, value in by_source.items():
            agg[name] = agg.get(name, 0) + value
    total = sum(agg.values())
    if not total:
        return None
    return agg.get("slice", 0) / total


def _describe_population(share: float | None) -> str:
    """What to DO about a firing, which differs by where the mentions came from.

    Slice-dominated and below-floor are disjoint concerns needing different
    responses, so the message says which one this is instead of leaving the reader
    to go and look.
    """
    if share is None:
        return "source split unrecorded — check the population before reseating"
    if share > 0.5:
        return (
            f"{share:.0%} substitution-slice: a TARGETED sweep for migration "
            "language, so re-measure against the general sweep before crediting it"
        )
    return f"{share:.0%} substitution-slice: mostly general sweep, reseat"


def _fires(rows, floor):
    """The condition itself, so the test and the check cannot drift apart.

    **KEYED ON THE TOTAL, DELIBERATELY, AND THE SPLIT IS REPORTED INSTEAD.**
    `select()` seats by comparing a model's TOTAL attested mentions to the floor,
    so a check keyed on anything else is checking a rule the code does not
    implement. Conditioning on non-slice mentions would find "errors" that are
    correct under the policy, which is the mistake the first version of this check
    already made once.

    But slice-contamination and below-floor are DISJOINT concerns needing
    different responses - reseat versus re-measure against a wider sweep - so the
    failure message carries the split. The condition does not conflate them
    because it does not judge them; it names both facts and lets the reader act.
    """
    return [
        cid
        for cid, seat, mentions in rows
        if seat == PROVISIONAL and mentions and _total(mentions) >= floor
    ]


def test_the_condition_fires_on_a_real_error_and_not_on_a_correct_seat(floor):
    """Break-it-on-purpose, and pin BOTH sides of the boundary.

    Habit 3, and the second assertion is the one this check earned the hard way.
    The first version had no case for "correctly seated below the floor", so
    nothing stopped it firing on 5 rows that were right — which is the muting
    failure it was written to avoid, reintroduced by the condition itself.
    """
    over = [("vendor/model-x", PROVISIONAL, [("model x", floor, {"sweep": floor})])]
    assert _fires(over, floor) == ["vendor/model-x"], (
        "an entry at or above the floor and still seated by the window is a real "
        "error and must fire"
    )

    under = [("vendor/model-y", PROVISIONAL, [("model y", floor - 1, {"sweep": floor - 1})])]
    assert not _fires(under, floor), (
        "BELOW the floor and inside the window is what the policy intends. This "
        "is the case the first version got wrong on 5 of 23 entries."
    )

    unseen = [("vendor/model-z", PROVISIONAL, [])]
    assert not _fires(unseen, floor), (
        "a provisional entry nobody has discussed must never fire — it stays "
        "legitimately provisional forever, and that is the mute to avoid"
    )

    seated = [("vendor/model-w", ATTESTED, [("model w", floor * 10, {"sweep": floor * 10})])]
    assert not _fires(seated, floor), "an already-attested seat is not an error"


def test_the_live_artifact_agrees_with_the_condition(entries, floor):
    """The same condition over the real file, so the two cannot diverge."""
    assert _fires(entries, floor) == [], (
        "the artifact has a provisional entry clearing the floor — "
        "test_no_provisional_entry_already_qualifies_by_count names it"
    )


def test_slice_contamination_and_below_floor_are_kept_apart(floor):
    """Two disjoint concerns, and a condition keyed on a total would merge them.

    Below-floor and slice-dominated need DIFFERENT responses — reseat versus
    re-measure against a wider sweep — and today they are disjoint sets: the five
    below-floor entries are mostly sweep-sourced (`gemini 3.6 flash` is
    [sweep 10, slice 3], `qwen3.8-max` is [sweep 7]), while the slice-dominated
    ones are all already `attested`.

    **The condition still keys on the total, deliberately.** `select()` seats by
    comparing total mentions to the floor, so conditioning on anything else checks
    a rule the code does not implement — the mistake the first version made. The
    split is separated in the MESSAGE, not the condition.
    """
    sweep_sourced = [("v/sweep", PROVISIONAL, [("s", floor, {"sweep": floor})])]
    slice_sourced = [("v/slice", PROVISIONAL, [("s", floor, {"slice": floor})])]

    # Both fire: both qualify by count, which is what the policy measures.
    assert _fires(sweep_sourced, floor) == ["v/sweep"]
    assert _fires(slice_sourced, floor) == ["v/slice"]

    # And they are distinguishable, which is what makes the responses different.
    assert _slice_share(sweep_sourced[0][2]) == 0.0
    assert _slice_share(slice_sourced[0][2]) == 1.0


def test_a_missing_split_is_absent_rather_than_zero(floor):
    """Rule 6. 0.0 would read as "measured, none from the slice"."""
    assert _slice_share([("s", 5, {})]) is None


def test_the_below_floor_population_and_its_slice_share_are_pinned(entries):
    """The two concerns OVERLAP, by one entry, and the number is the point.

    **CORRECTION.** I told Engineer 2 the five below-floor entries were "mostly
    sweep-sourced, so slice contamination and below-floor are disjoint sets", on
    the strength of two of them. Counted, they are not disjoint:

        google/gemini-3.6-flash          14   21% slice
        qwen/qwen3.8-max                  8    0%
        qwen/qwen3.7-flash                5    0%
        deepseek/deepseek-v4-flash-0731   3  100% slice   <- the overlap
        deepseek/deepseek-v4-pro-0813     1    0%

    4 of 5 sweep-dominated, 1 of 5 slice-only. Generalising from two instances
    without counting is the risk form of rule 7, and it is the second time this
    week - so the population is pinned here rather than described.

    **THIS DOES NOT FAIL ON THE OVERLAP, deliberately.** A below-floor entry whose
    few mentions are all from the migration sweep is seated CORRECTLY: it is under
    the floor either way. Failing the build on it would be firing on a correct
    state, which is the exact mistake the first version of this check made. What
    fails is the distribution CHANGING, because that means a reviewer's assumption
    about which entries need re-measurement has gone stale.
    """
    below = [
        (cid, _total(m), _slice_share(m))
        for cid, seat, m in entries
        if seat == PROVISIONAL and m
    ]
    assert below, "no below-floor provisional entries parsed — format changed?"

    slice_dominated = sorted(
        cid for cid, _total_, share in below if share is not None and share > 0.5
    )
    assert len(below) == 5, f"the below-floor population changed: {len(below)} entries"
    assert slice_dominated == ["deepseek/deepseek-v4-flash-0731"], (
        f"the slice-dominated below-floor set changed: {slice_dominated}. Re-check "
        "which entries need re-measuring against the general sweep before "
        "confirming their seats — the two concerns overlap and the overlap moved."
    )


def test_every_below_floor_entry_is_actually_below_the_floor(entries, floor):
    """The seating itself, independent of where the mentions came from.

    Guards the claim the docstring above rests on: these entries are correctly
    seated. If one crosses the floor it is no longer a correct state and
    `test_no_provisional_entry_already_qualifies_by_count` is the one that fires.
    """
    for cid, seat, mentions in entries:
        if seat == PROVISIONAL and mentions:
            assert _total(mentions) < floor, f"{cid} clears the floor of {floor}"
