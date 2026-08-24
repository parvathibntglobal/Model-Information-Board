"""Which models get swept. A selection, and it states what it was drawn from.

340 models in the registry, 81.45 requests per model per night, ~900 requests
available: 11 models a night, so a full pass takes 31 days against a 30-day
half-life on `ops.latency_ttft`. The sweep loses to the decay curve. Something
has to be smaller than 340, and this module says by how much and on what
grounds - #33.

TWO GROUNDS, AND THE SECOND EXISTS BECAUSE THE FIRST CANNOT SEE A NEW MODEL
---------------------------------------------------------------------------
    BY COUNT    the corpus attests this model at or above a mention floor.
                Measured, so it is the primary ground.
    BY RULE     released inside a launch window, regardless of mentions. A model
                released last week has no discussion history for the corpus to
                carry, and the launch window is exactly when people post about
                it. Ranking on mentions alone would rank a four-day-old model
                last on the strength of its being four days old.

Engineer 2 already agreed the shape of the second: a model in its launch window
is swept nightly rather than rotated.

WHY THE RANKING IS BY MENTIONS AND NOT BY RELEASE DATE
-------------------------------------------------------
Recency and discussion are not the same measurement. The feed carries regional
variants, fine-tunes and routing entries - 11 of the 340 ids are
`~vendor/...-latest` routing pointers, whose `release_date` is when the pointer
moved rather than when anything launched. A date-sorted top 50 would seat
several of those and drop models from months ago that people still discuss
constantly: `anthropic/claude-sonnet-4.5` is **32 non-slice mentions** and
outside any recent window.

**THAT FIGURE WAS `426` AND IT WAS THE WRONG ONE TO QUOTE HERE.** 426 is real -
`sonnet 4.5` 416 plus `sonnet-4.5` 10 - but **394 of it is
`substitution-slice`**, 92%. The substitution slice is a *targeted* sweep for
migration language, so a model people are leaving gets counted there heavily by
construction. Quoting its total as evidence that "people still discuss this
model" made a slice measurement do duty as a corpus measurement, **inside the
argument for the ranking method itself** - which is the one place a
population error propagates into every seat.

**The conclusion survives, and on a smaller number.** 32 mentions from
`reddit-sweep` and `reddit-comments` is not zero, it is sixteen months after
release, and a date sort still drops it while seating routing pointers. So the
ranking stays by mentions. What changes is what this docstring claims: the
argument rests on `sonnet-4.5` being discussed *at all* long after release, not
on it being the second-most-discussed model in the corpus.

Rule 7, and the reason it took a fortnight to see: the extract has always
carried a `by_source` split and `to_yaml` printed only the total, so every seat
was reviewed against a figure whose population was invisible. The split is now
printed per surface in the artifact - `Attested.by_source` and
`propose.source_split`.

`mentions` IS `None` WHERE NOTHING WAS OBSERVED, NEVER 0
---------------------------------------------------------
Rule 6, and it is load-bearing here rather than decorative. 268 of the 340
registry models are absent from the surface extract. That is **recall
unmeasured**, not a measurement of zero - the detector needs a vendor or family
word followed by a version token, so it cannot see `deepseek r1` at all, and the
corpus is Reddit prose only.

So an unobserved model carries `mentions = None` and is **unrankable**. It can
enter the tracked set by the launch-window rule and by no other route. A `0`
here would let "we did not look" sort identically to "we looked and found
nothing", which is the whole class of defect rule 6 names.

WHAT THE MENTION COUNTS ARE DRAWN FROM
---------------------------------------
Rule 7: a figure travels with its denominator. `Selection.basis` carries it into
the artifact and into any argument made from it, because these counts answer a
narrower question than "how often is this model discussed":

  - 10,255 attested mentions over 449 surfaces, 5,546 Reddit documents, 2026-08-17.
  - Only `resolved` and `attested-gap` surfaces are attributable - 145 surfaces,
    7,202 mentions, each naming exactly one registry model.
  - `attested-gap-ambiguous` is EXCLUDED: 49 surfaces, 1,530 mentions that
    several registry models could be meant by. Excluded rather than split or
    assigned, because assigning them would invent an attribution the extract
    refuses. A model's count is therefore a LOWER BOUND.
  - `unknown-model` is excluded too: 255 surfaces, 1,523 mentions naming nothing
    the registry carries. That is a poller finding, not a mention of a tracked
    model.
  - Reddit only. A GitHub issue names a model in a config line, where the id
    spelling is likely the common form, and this corpus says id spellings are
    unattested. So these counts measure Reddit prose and not naming generally.

NO MODEL PARTICIPATES. Counted observations and a date comparison. This module
proposes a set; a person approves it.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date

from collect.registry.propose import Attested, is_route

#: Why a model is in the set. Kept as separate grounds rather than collapsed to a
#: boolean: the artifact says which one seated each model, and a model seated
#: only by the launch window is one nobody has written a sentence about yet.
BY_MENTIONS = "mentions"
BY_LAUNCH_WINDOW = "launch-window"

#: Surface verdicts that name exactly one registry model. Everything else is
#: excluded from attribution - see the module docstring.
ATTRIBUTABLE_VERDICTS = frozenset({"resolved", "attested-gap"})

#: The ground recorded when a route is refused a seat, so the exclusion is
#: COUNTED rather than silent. Not a seating ground - `selected` stays False -
#: but a reason `summarise` can state, because rule 6's display side is that a
#: thing dropped where it would have been used has to say so.
REFUSED_ROUTE = "route-not-model"

# THE RULING WAS NEVER PROSE, AND THAT IS A CORRECTION TO MY OWN FIRST FIX.
# `is_route` has existed in `collect/registry/propose.py` since 2026-08-18, it is
# ruled - "routes are not models" - and it is MEASURED: excluding the 17 route
# ids takes control-corpus survival from 1.3% to 0.0%. It also had a caller,
# `collect/triage/entity.py:218`, so a route has never been able to become an
# entity match.
#
# What it did not have was a call from HERE. `select()` seated
# `~deepseek/deepseek-v4-flash-latest` because the tracked set never consulted
# the ruling that the triage stage already enforced. So the defect was one
# missing call, not a missing rule - and my first attempt at this added a second
# `is_routing_pointer()` beside the first, which checked only the `~` prefix,
# missed the `openrouter/` namespace entirely and did not casefold. Two
# implementations of one ruling is the thing that drifts; there is now one.


@dataclass(frozen=True)
class TrackedSetPolicy:
    """The two thresholds. **Deliberately without defaults.**

    Rule 5 puts a selection rule in `contract/`, and this is the same class as
    the feed list and the subreddit list. `RegistryPolicy` carries proposed
    values as code defaults so the lane can be developed before the contract
    file exists; that pattern is documented there as a hazard rather than a
    convenience, and it is not repeated here because there is no signed-off
    value yet for a default to shadow. A caller must supply both, so nothing
    can pick up a threshold nobody agreed to.
    """

    #: Attested mentions at or above which a model qualifies by count.
    mention_floor: int

    #: Days since release inside which a model qualifies regardless of mentions.
    launch_window_days: int

    def __post_init__(self) -> None:
        if self.mention_floor < 1:
            raise ValueError(
                f"mention_floor must be at least 1, got {self.mention_floor}. "
                "A floor of 0 would seat every model in the registry by count, "
                "including the 268 the corpus has never observed - and it would "
                "record them as qualifying on evidence that does not exist."
            )
        if self.launch_window_days < 0:
            raise ValueError(
                "launch_window_days must not be negative, got "
                f"{self.launch_window_days}"
            )


@dataclass(frozen=True)
class TrackedModel:
    """One model and why it is in - or the counts that kept it out."""

    canonical_id: str
    display_name: str | None
    release_date: date | None
    #: Attributable mentions, or None where the corpus never observed this model.
    #: None is unmeasured. It is not zero. See the module docstring.
    mentions: int | None
    #: Distinct attested surfaces. None on the same terms as `mentions`.
    surfaces: int | None
    #: Every ground that seats it. Empty means not selected.
    grounds: tuple[str, ...] = ()

    @property
    def selected(self) -> bool:
        """Seated by at least one SEATING ground.

        `REFUSED_ROUTE` is in `grounds` and is not one of them, so this is not
        `bool(self.grounds)` any more. That line would have seated every pointer
        the moment the refusal was recorded — the refusal reading as its own
        justification, which is the shape rule 6 is about.
        """
        return bool(set(self.grounds) & {BY_MENTIONS, BY_LAUNCH_WINDOW})

    @property
    def refused_as_route(self) -> bool:
        """A route rather than a model. See `propose.is_route`."""
        return REFUSED_ROUTE in self.grounds

    @property
    def measured(self) -> bool:
        """Did the corpus observe this model at all?

        The one property that must not be spelled `mentions > 0`, because that
        reads None as false and an unmeasured model as an unmentioned one.
        """
        return self.mentions is not None


@dataclass(frozen=True)
class Selection:
    """The chosen set, the rejected rest, and where the numbers came from."""

    tracked: list[TrackedModel]
    rejected: list[TrackedModel]
    policy: TrackedSetPolicy
    as_of: date
    #: Rule 7. Carried into the artifact so a figure never travels alone.
    basis: dict[str, object] = field(default_factory=dict)

    @property
    def by_mentions(self) -> list[TrackedModel]:
        return [m for m in self.tracked if BY_MENTIONS in m.grounds]

    @property
    def by_launch_window(self) -> list[TrackedModel]:
        return [m for m in self.tracked if BY_LAUNCH_WINDOW in m.grounds]

    @property
    def launch_window_only(self) -> list[TrackedModel]:
        """Seated by the rule alone - nobody has written a sentence about these."""
        return [m for m in self.tracked if m.grounds == (BY_LAUNCH_WINDOW,)]

    @property
    def refused_routes(self) -> list[TrackedModel]:
        """Routes refused a seat. **Counted, so the exclusion is not silent.**

        Rule 6's display side. A pointer dropped without a number beside it makes
        the set look like it never contained one, which is exactly how the last
        one survived - the rule was in prose, nothing counted, and nobody had a
        figure to disagree with.
        """
        return [m for m in self.rejected if m.refused_as_route]

    @property
    def unmeasured(self) -> list[TrackedModel]:
        """Tracked models the corpus has never observed. Recall unmeasured."""
        return [m for m in self.tracked if not m.measured]

    @property
    def future_dated(self) -> list[TrackedModel]:
        """Registry rows dated ahead of `as_of`. Not in the launch window.

        A poller finding rather than a selection outcome, and listed rather than
        dropped: a mis-parsed date is invisible if the only effect it has is a
        model quietly missing from the sweep.
        """
        return [
            m
            for m in self.tracked + self.rejected
            if m.release_date is not None and m.release_date > self.as_of
        ]

    @property
    def surface_sizes(self) -> list[int]:
        """Distinct attested surfaces, measured models only.

        Unmeasured models are omitted rather than counted as 0: a median taken
        over 0s from models nobody looked at is a statement about coverage
        wearing the clothes of a statement about usage.
        """
        return sorted(m.surfaces for m in self.tracked if m.surfaces is not None)


def attributable(
    surface_rows: Iterable[Mapping[str, object]],
) -> dict[str, list[Attested]]:
    """Fold the surface extract into per-model attested surfaces.

    Only verdicts naming exactly one model. The cardinality is checked rather
    than assumed: `attested-gap-ambiguous` rows carry 2 to 25 models, and taking
    `models[0]` from one would assign 1,530 mentions to whichever id happened to
    sort first.
    """
    out: dict[str, list[Attested]] = {}
    for row in surface_rows:
        models = row.get("models") or []
        if row.get("verdict") not in ATTRIBUTABLE_VERDICTS or len(models) != 1:  # type: ignore[arg-type]
            continue
        out.setdefault(str(models[0]), []).append(  # type: ignore[index]
            Attested(
                surface=str(row["surface"]),
                mentions=int(row["mentions"]),  # type: ignore[call-overload]
                documents=int(row.get("documents", 0)),  # type: ignore[call-overload]
                # Carried, not dropped. The extract has always had this and the
                # artifact never showed it - see `Attested.by_source`.
                by_source={
                    str(k): int(v)
                    for k, v in (row.get("by_source") or {}).items()  # type: ignore[union-attr]
                },
            )
        )
    for surfaces in out.values():
        surfaces.sort(key=lambda a: (-a.mentions, a.surface))
    return out


def select(
    models: Sequence[tuple[str, str | None, date | None]],
    observed: Mapping[str, list[Attested]],
    *,
    policy: TrackedSetPolicy,
    as_of: date,
    basis: Mapping[str, object] | None = None,
) -> Selection:
    """Choose the tracked set. `models` is (canonical_id, display_name, release_date).

    Ranked by attributable mentions, descending, then by canonical_id so the
    order is stable across runs and two runs of the same inputs diff to nothing.
    Unmeasured models sort last and are never seated by count.
    """
    scored: list[TrackedModel] = []
    for canonical_id, display_name, release_date in models:
        surfaces = observed.get(canonical_id)
        mentions = sum(a.mentions for a in surfaces) if surfaces else None
        count = len(surfaces) if surfaces else None

        grounds: list[str] = []
        if is_route(canonical_id):
            # Refused before either rule is consulted, and UNCONDITIONALLY.
            # A pointer's mentions are about whatever it resolves to and its
            # release_date is when it last moved, so both seating grounds are
            # measuring something other than a model. Recorded rather than
            # dropped, so `Selection.refused_pointers` can count it.
            grounds.append(REFUSED_ROUTE)
        else:
            if mentions is not None and mentions >= policy.mention_floor:
                grounds.append(BY_MENTIONS)
            if release_date is not None and in_launch_window(
                release_date, as_of, policy.launch_window_days
            ):
                grounds.append(BY_LAUNCH_WINDOW)

        scored.append(
            TrackedModel(
                canonical_id=canonical_id,
                display_name=display_name,
                release_date=release_date,
                mentions=mentions,
                surfaces=count,
                grounds=tuple(grounds),
            )
        )

    scored.sort(key=lambda m: (-(m.mentions or 0), m.canonical_id))
    return Selection(
        tracked=[m for m in scored if m.selected],
        rejected=[m for m in scored if not m.selected],
        policy=policy,
        as_of=as_of,
        basis=dict(basis or {}),
    )


def age_days(release_date: date, as_of: date) -> int:
    """Days between release and today. Negative for a future-dated release."""
    return as_of.toordinal() - release_date.toordinal()


def in_launch_window(release_date: date, as_of: date, window_days: int) -> bool:
    """Has this model launched, and launched recently?

    BOUNDED AT BOTH ENDS, and the lower bound is the one worth explaining. A
    future-dated row has an age of `-40`, which is trivially "within 30 days" if
    the comparison is only `<= window`. So a feed that mis-parses a date, or a
    provider that pre-announces, would seat a model that does not exist yet and
    keep it seated — the further wrong the date, the longer it stays.

    A model that has not launched is not in its launch window. It is not dropped
    either: `Selection.future_dated` lists it, because a release date ahead of
    today is a poller finding somebody should look at, and the difference
    between "excluded" and "excluded and nobody mentioned it" is rule 6's whole
    subject.
    """
    return 0 <= age_days(release_date, as_of) <= window_days


def distribution(selection: Selection) -> str:
    """The shape of the mention curve, for a reviewer deciding the floor.

    The count is a contract decision, so this reports where the curve flattens
    rather than nominating a number.
    """
    measured = [m for m in selection.tracked + selection.rejected if m.measured]
    measured.sort(key=lambda m: (-(m.mentions or 0), m.canonical_id))
    total = sum(m.mentions or 0 for m in measured)
    if not total:
        return "no attributable mentions: the floor cannot be derived from this extract"

    lines = [
        f"{len(measured)} models carry {total} attributable mentions "
        f"({selection.basis.get('platform', 'platform unstated')}, "
        f"{selection.basis.get('documents', '?')} documents).",
        "",
        "  rank band   mentions added   share   fewest in band",
    ]
    bands = [(1, 10), (11, 20), (21, 30), (31, 40), (41, 50), (51, len(measured))]
    for lo, hi in bands:
        if lo > len(measured):
            break
        band = measured[lo - 1 : hi]
        added = sum(m.mentions or 0 for m in band)
        lines.append(
            f"  {lo:>3}-{min(hi, len(measured)):<3}     {added:>10}   "
            f"{100 * added / total:5.1f}%   {band[-1].mentions:>6}"
        )
    return "\n".join(lines)


def summarise(selection: Selection) -> str:
    """What a reviewer reads before opening the artifact."""
    sizes = selection.surface_sizes
    if sizes:
        spread = (
            f"median {sizes[len(sizes) // 2]}, mean {sum(sizes) / len(sizes):.2f}, "
            f"min {sizes[0]}, max {sizes[-1]}"
        )
    else:
        spread = "not measured"
    total = len(selection.tracked) + len(selection.rejected)
    return (
        f"{len(selection.tracked)} tracked of {total} registry models "
        f"(floor {selection.policy.mention_floor} mentions, launch window "
        f"{selection.policy.launch_window_days}d, as of {selection.as_of}).\n"
        f"  {len(selection.by_mentions)} by mentions, "
        f"{len(selection.by_launch_window)} by launch window, "
        f"{len(selection.launch_window_only)} by launch window alone.\n"
        f"  {len(selection.unmeasured)} tracked models the corpus never observed "
        f"- recall unmeasured, not zero.\n"
        f"  {len(selection.refused_routes)} routes refused a seat "
        f"- routes are not models, excluded before either ground was consulted.\n"
        f"  Attested surfaces per measured tracked model: {spread}."
    )
