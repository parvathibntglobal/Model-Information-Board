"""GitHub retrieval: one cheap request per entry, and a refusal where it cannot work.

WHAT THE INDEX ACTUALLY DOES, MEASURED
--------------------------------------
Every rule here comes from a measurement in issue #4 or issue #5, not from the
documentation:

    (a OR b)        silently discarded. The query returns what remains
    wildcard*       silently discarded
    "a phrase"      does not bind. Reversing the words changes 540 to 545, and
                    of 8 results for one phrase query, 7 contained the phrase
                    nowhere. Quoting changes the RANKING, not the membership
    a trailing 5    matched against the ISSUE NUMBER. `"claude sonnet"` 77 →
                    `"claude sonnet 5"` 123 → `"claude sonnet 7"` 96. A version
                    numeral widens a query rather than narrowing it
    repo: org:      work, and repeated qualifiers UNION: `org:langchain-ai` 475
                    + `org:run-llama` 56, both together exactly 531
    stemming        none. `truncate` 2,136, `truncates` 180, `truncated` 1,334

So the only things worth spending a request on are the alias, at most one
narrowing token, and the scope. Everything else the contract carries is for the
sieve, which is the arrangement `contract/queries.yaml` itself describes.

WHY NOT ONE REQUEST PER topic × signal PAIR
-------------------------------------------
Because it was costed: 830 pairs per alias × 59 alias strings is 48,616 search
requests, 30.9 hours at GitHub's 30/min, 79× BUILD-PLAN's budget — before the
REST fetch half, which issue #4 measured as the real cost. And it buys nothing:
the extra terms are token conjunctions the index cannot combine as intended.
One request per (entry, alias) is ~944, and the sieve recovers the precision.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace

from collect.adapters.queries.contract import QueryEntry, RenderedTerms

#: Syntax this renderer must never emit, because the index discards it without
#: erroring — which is how twelve templates collapsed to their alias and nobody
#: could see it. Asserted on every rendered query rather than trusted.
FORBIDDEN_SYNTAX: tuple[str, ...] = (" OR ", "(", ")", "*")

#: A term with a space cannot narrow: the index would require its tokens
#: separately and honour neither adjacency nor order. Multi-word terms are the
#: sieve's.
_MULTI_WORD = re.compile(r"\s")

#: A surface whose last token is a bare number collides with the issue number.
_TRAILING_NUMERAL = re.compile(r"\s\d+(\.\d+)?$")

#: Words too common to narrow anything. Deliberately short: the point is to
#: skip tokens that cost a request and return the corpus, not to curate.
_WEAK_TOKENS = frozenset(
    {"the", "a", "an", "code", "json", "context", "agent", "model", "slow", "told"}
)


class UnrenderableError(RuntimeError):
    """The query cannot be expressed on this index without changing its meaning."""


@dataclass(frozen=True)
class Unrenderable:
    """A refusal, carrying why. Not an error — an outcome to record.

    Returned rather than raised because "this platform cannot ask this
    question" is a fact about coverage that belongs on the coverage page, not
    an exception to swallow at a call site.
    """

    entry_label: str
    reason: str
    platform: str = "github"


@dataclass(frozen=True)
class SearchRequest:
    """One GitHub search, and every sieve term set its results should be read with.

    `variants` carries **every spelling of the model**, not only the spelling that
    produced this query. Which spelling *found* a document says nothing about how
    the document *names* the model: a post retrieved by `gemini flash` may say
    `gemini-2.5-flash` in its body, and a sieve given one spelling rejects it on
    subject.

    Measured on the first live run: checking only the retrieving spelling put the
    subject-miss rate at 88.6%; checking all six of one model's forms put it at
    66.9% over the same corpus. Twenty-eight documents of 136 recovered for zero
    extra requests.

    It also does the job it was first built for — `claude opus 5` and
    `claude-opus-5` render to the same query, since the numeral rule hyphenates
    the first, so issuing both would buy the same documents twice.

    Retrieve once, sieve against every form.
    """

    query: str
    entry_label: str
    variants: tuple[RenderedTerms, ...]
    narrowing_token: str | None
    scope: tuple[str, ...] = ()

    @property
    def terms(self) -> RenderedTerms:
        """The first spelling. Use `variants` when reading documents."""
        return self.variants[0]

    @property
    def alias(self) -> str:
        return self.variants[0].alias

    @property
    def aliases(self) -> tuple[str, ...]:
        return tuple(v.alias for v in self.variants)

    @property
    def query_key(self) -> str:
        """Stable key for `watermark` and `harvest_run`. The query as issued."""
        return self.query

    def sieve(self, text: str):
        """Read one retrieved document against every spelling this request covers."""
        from collect.adapters.queries.sieve import sieve_any

        return sieve_any(self.variants, text)


@dataclass(frozen=True)
class SearchPlan:
    """What a sweep would issue, before it issues anything.

    The count is the point: issue #4's central failure was a budget nobody
    computed until an adapter was about to run.
    """

    requests: tuple[SearchRequest, ...]
    refusals: tuple[Unrenderable, ...]

    @property
    def request_count(self) -> int:
        return len(self.requests)

    @property
    def distinct_queries(self) -> int:
        """How many unique query strings the requests contain.

        Below `request_count` where two entries narrow on the same token. The
        gap is what a shared-retrieval arrangement would save, and it is
        reported rather than taken, because taking it costs the second entry's
        sieve terms.
        """
        return len({r.query for r in self.requests})

    def minutes_at(self, per_minute: int = 30) -> float:
        """Search time only. The REST fetch half is the larger cost."""
        return self.request_count / per_minute


def github_alias_form(surface: str) -> str:
    """Render an alias so its version numeral cannot match an issue number.

    `claude sonnet 5` → `claude-sonnet-5`. Measured: the spaced form's trailing
    numeral collects issue #5 from unrelated repositories — 89 of 123 results at
    one scope, every one of them issue #5, none mentioning the model. The
    hyphenated form returned the same corpus minus that noise.

    Only a trailing numeral triggers it. `gpt-4.1 mini` keeps its shape, because
    the numeral is not the last token and nothing collides.
    """
    surface = surface.strip()
    if _TRAILING_NUMERAL.search(surface):
        return "-".join(surface.split())
    return surface


#: Emission order for one alias on GitHub. Ranked by MEASURED yield per request
#: over 1,019 harvest runs and 44,848 candidates, not by taste:
#:
#:     hyphenated                 551 runs  40,909 fetched  173 kept  74.2/run
#:     concatenated-with-numeral  436 runs   2,439 fetched    8 kept   5.6/run
#:     spaced                      32 runs   1,500 fetched    0 kept
#:
#: `docs/measurements/what-github-needs-before-a-sweep.md`.
ALIAS_FORMS: tuple[str, ...] = ("hyphenated", "concatenated")


def github_alias_forms(surface: str) -> tuple[str, ...]:
    """Every form worth issuing for one alias, MOST PRODUCTIVE FIRST.

    WHY THIS RETURNS A LIST AND `github_alias_form` RETURNS ONE STRING. The two
    forms retrieve **disjoint sets**. Measured per document rather than per
    request:

        found ONLY by concatenated     4
        found by both                  0
        found ONLY by hyphenated      48

    Zero overlap. So the concatenated form is not a worse way of finding the same
    issues - it finds different ones, and dropping it discards a measured 7.7% of
    the corpus.

    **EXPENSIVE AND USELESS ARE DIFFERENT STATES, and the second is the easy
    read.** 5.6 fetched per run against 74.2 looks like noise until you ask what
    it uniquely produced; then it is 109 requests per unique document against
    hyphenated's 11.5. A 9.5x cost difference is a PRIORITY, not a filter -
    which is rule 8's shape with the measurement already in hand: the error rate
    is known, so this ships as a weight with a number rather than a gate on a
    guess.

    So: emit hyphenated always, concatenated last and only when the search
    budget is not the binding constraint. The caller decides that; this function
    only orders them.

    WHY GITHUB WANTS THE OPPOSITE FORM TO REDDIT, WHICH IS THE THING THAT STOPS
    SOMEONE UNIFYING THESE LATER
    ---------------------------------------------------------------------------
    **GitHub's preference is about the INDEX. Reddit's is about CONVENTION.**

    GitHub Search tokenises on punctuation, so `claude-sonnet-4.5` becomes
    matchable terms - `claude`, `sonnet`, `4`, `5` - and an issue mentioning the
    model matches on them. `claudesonnet4.5` is a **single rare token** that
    appears nowhere, which is why it fetches 0 on run after run rather than
    fetching noise. The concatenated form does not retrieve badly; it barely
    retrieves at all, and the four documents it does find are ones where somebody
    literally typed it.

    Reddit has no such index in play - the sweep matches against titles - so the
    question there is *how does a human write this*, and the answer was the
    vendor's own marketing spelling: `qwen3.8-27b` hyphenated matched 116 of 175
    titles against 42 spaced, because that is how the announcement wrote it and
    how people copy it.

    **Same alias, two questions.** GitHub asks *how does this tokenise*; Reddit
    asks *how do humans write this*. A single renderer with a platform flag would
    have to answer both from one rule, and there is no rule that produces
    `claude-sonnet-4.5` for a tokeniser and `qwen3.8-27b` for a copy-paste
    convention except "look up the platform" - which is what having two arms
    already is, stated honestly.

    A trailing numeral is what makes hyphenation load-bearing rather than
    cosmetic: see `github_alias_form`, where the spaced form collected issue #5
    from unrelated repositories, 89 of 123 results.
    """
    surface = surface.strip()
    if not surface:
        return ()
    hyphenated = github_alias_form(surface)
    concatenated = "".join(surface.split())
    if concatenated.casefold() == hyphenated.casefold():
        # Nothing to add. A single-token alias has one form, and returning it
        # twice would double the request count for no candidates.
        return (hyphenated,)
    return (hyphenated, concatenated)


#: Query SHAPES, ranked by on-subject documents per request. Measured
#: 2026-08-28 over 18 requests and 1,451 candidates, three models:
#:
#:     shape    reqs  cands  on-subject  UNIQUE  on-subject/request
#:     title       3    300          93      79               31.0
#:     label       3    300          65      29               21.7
#:     repro       6    600          95      61               15.8
#:     signal      6    251          22      21                3.7
#:
#: `docs/measurements/what-github-needs-before-a-sweep.md`.
SHAPES: tuple[str, ...] = ("title", "topic", "repro")


def title_only_query(surface: str, *, item_type: str = "issue") -> str:
    """`"<alias>" in:title type:issue` — the highest-precision shape measured.

    **76 of 100 candidates on-subject on a single query**, and 93 of 300 across
    three models, against a pooled all-time keep rate of 0.404%. That is the
    largest retrieval improvement measured on this platform and nobody had
    issued it before 2026-08-28.

    WHY IT WORKS, and it is the tokeniser argument again. GitHub indexes title
    and body together by default, so `"claude-sonnet-4.5"` matches a changelog
    entry, a lockfile diff, a dependency bump - anything that merely CONTAINS the
    string. `in:title` restricts the match to the field a human chose to write,
    and a model named in a title is what the issue is ABOUT rather than something
    it happens to mention.

    WHAT IT DOES NOT FIX, stated because the number invites the wrong
    conclusion. Across all four shapes tested, **230 on-subject documents
    produced ZERO signal hits.** `in:title` moves the funnel's first stage from
    ~20% to 31% and changes nothing downstream. It is a better place to start
    failing, not a fix - signal is a sieve question, and no query shape reaches
    it.

    NEAR-DISJOINT WITH THE OTHER SHAPES, which is why the sweep should run
    several rather than pick this one:

        title n signal   0        repro n signal   0
        title n repro    9        repro n label   30
        title n label   10        signal n label   1

    79 of `title`'s 93 on-subject documents were found by no other shape.
    """
    return f'"{github_alias_form(surface)}" in:title type:{item_type}'


def repro_query(surface: str, word: str = "traceback", *, item_type: str = "issue") -> str:
    """Alias plus a repro artifact word. 61 unique on-subject documents in 6 requests.

    Kept as a shape despite producing 0 kept, because `unique` is the number
    that matters when shapes are disjoint: 61 of its 95 on-subject documents
    were found by nothing else, and it shares NOTHING with the signal shape.

    **The reading that motivated this arm is withdrawn.** It was chosen because
    the productive topic tokens (`SEARCH/REPLACE`, `json_schema`) are literal
    artifacts and the barren ones (`extraction`, `boilerplate`) are conceptual
    English - so a repro word should behave like the productive class.
    `traceback` produced zero signal hits, exactly like everything else. The
    topic-token measurement stands on its own numbers; this arm did not confirm
    the explanation for it, and the shape earns its place on uniqueness instead.
    """
    return f'"{github_alias_form(surface)}" {word} type:{item_type}'


# ══════════════════════════════════════════════════════════════════════════
# THE MULTI-SHAPE SWEEP
# ══════════════════════════════════════════════════════════════════════════
#
# ONE SHAPE IS THE WRONG NUMBER OF SHAPES, and the disjointness is why.
# `title` and `repro` share 9 documents of 188, so running both roughly doubles
# unique documents per model rather than adding a second look at the same ones.
# A sweep that picked the best shape would leave 61 of repro's 95 on-subject
# documents unreachable - the ones nothing else finds.
#
#     shape   on-subject/req   UNIQUE/req      issued here
#     title        31.0            26.3        yes, first
#     label        21.7             9.7        NO - see REFUSED_SHAPES
#     repro        15.8            10.2        yes, second
#     signal        3.7             3.5        no - last by a factor of four
#
# ORDERED BY THE RANKING so a run truncated by the search bucket has issued the
# most productive requests rather than an arbitrary prefix. `sweep_requests`
# emits shape-major within each surface batch for that reason.
#
# ⚠ UNIQUE/req IS THE NUMBER THAT DECIDES AN ARM, not on-subject/req. That is
#   the disjoint-sets lesson: `label` looks like a strong second arm at 21.7
#   on-subject per request and is a weak one at 9.7 unique, because 30 of its
#   documents are repro's and 10 are title's. A report that ranked arms by kept
#   documents would have bought `label` twice.

#: What a sweep issues, in the order it issues them.
SWEEP_SHAPES: tuple[str, ...] = ("title", "repro")

#: Shapes that exist, are renderable, and are deliberately not issued.
#: Keyed by shape, valued by the reason, because a refusal nobody can read is
#: indistinguishable from an oversight - and the next person to notice `label`
#: sitting at 21.7 on-subject per request will otherwise add it back.
REFUSED_SHAPES: dict[str, str] = {
    "label": (
        "label:bug measured 21.7 on-subject per request and only 9.7 UNIQUE - 30 "
        "of its documents are repro's and 10 are title's, so it buys a third of "
        "what its headline suggests. Two reasons beyond the arithmetic. (1) "
        "STRUCTURAL QUALIFIERS MEASURED AS DOING NOTHING at max_pages=1: "
        "`is:issue state:open` shrinks the reported corpus 3.65x and returns the "
        "IDENTICAL 100 ids in the same order, because the qualifier narrows the "
        "corpus and page 1 is all we ever read. `label:` is a different "
        "qualifier and is not strictly covered by that measurement, which is why "
        "this says 'most likely to reproduce a known null' rather than 'will'. "
        "(2) IT NARROWS TOWARD COMPLAINTS. label:bug retrieves issues somebody "
        "filed as a defect, which makes the POSITIVE half of the four "
        "silent-failure capabilities structurally unreachable - rule 4 arriving "
        "through the query rather than through the page. An arm that can only "
        "find criticism produces a board where absence of praise reads as "
        "absence of quality."
    ),
    "signal": (
        "3.7 on-subject per request, a factor of four below the next arm, and "
        "230 on-subject documents across all four shapes produced ZERO signal "
        "hits. Signal is a sieve question rather than a harvest one and no query "
        "shape reaches it; this sweep does not attempt it."
    ),
}


class RefusedShape(RuntimeError):
    """A shape was asked for that this sweep does not issue. Names the reason."""

    def __init__(self, shape: str) -> None:
        self.shape = shape
        super().__init__(
            f"refusing to issue shape {shape!r}: {REFUSED_SHAPES.get(shape, 'unknown shape')}"
        )


@dataclass(frozen=True)
class SweepRequest:
    """One query a sweep would issue, and what it is for."""

    shape: str
    surface: str
    query: str
    #: Where this sits in the ranked order, 0-based. Carried so a truncated run
    #: can say how far down the ranking it got rather than only how many
    #: requests it made.
    rank: int


def sweep_requests(
    surfaces: Sequence[str],
    *,
    shapes: Sequence[str] = SWEEP_SHAPES,
    item_type: str = "issue",
    repro_word: str = "traceback",
    budget: int | None = None,
) -> tuple[SweepRequest, ...]:
    """Every request a multi-shape sweep would issue, most productive first.

    SHAPE-MAJOR, NOT SURFACE-MAJOR. A run truncated at request 40 of 60 should
    have issued `title` for every model rather than `title` and `repro` for the
    first twenty - the first arrangement loses the weakest arm on every model,
    the second loses both arms on a third of them. Truncation is the expected
    case at 30 requests per minute, so the order is the design.

    `budget` truncates HERE rather than at the client, so the plan a caller
    prints is the plan that runs. A cap applied inside the fetch loop produces a
    report about requests that were never planned.

    Raises `RefusedShape` rather than filtering silently: asking for `label` is
    a decision somebody made, and dropping it quietly would let a sweep report
    coverage it did not attempt.
    """
    for shape in shapes:
        if shape in REFUSED_SHAPES:
            raise RefusedShape(shape)
        if shape not in _SHAPE_RENDERERS:
            raise ValueError(
                f"unknown shape {shape!r}. Known: {sorted(_SHAPE_RENDERERS)}; "
                f"refused: {sorted(REFUSED_SHAPES)}"
            )

    ordered = sorted(shapes, key=_shape_rank)
    planned: list[SweepRequest] = []
    seen: set[str] = set()
    rank = 0
    for shape in ordered:
        render = _SHAPE_RENDERERS[shape]
        for surface in surfaces:
            query = (
                render(surface, repro_word, item_type=item_type)
                if shape == "repro"
                else render(surface, item_type=item_type)
            )
            # Two surfaces can render to the same query - `github_alias_form`
            # collapses spacing - and issuing it twice spends a request from a
            # 30-per-minute bucket to fetch the same 100 candidates.
            if query in seen:
                continue
            seen.add(query)
            planned.append(SweepRequest(shape=shape, surface=surface, query=query, rank=rank))
            rank += 1
    if budget is not None:
        return tuple(planned[:budget])
    return tuple(planned)


def _shape_rank(shape: str) -> int:
    try:
        return SWEEP_SHAPES.index(shape)
    except ValueError:
        return len(SWEEP_SHAPES)


_SHAPE_RENDERERS = {
    "title": lambda surface, *, item_type="issue": title_only_query(
        surface, item_type=item_type
    ),
    "repro": lambda surface, word="traceback", *, item_type="issue": repro_query(
        surface, word, item_type=item_type
    ),
}


#: GitHub's authenticated search bucket, measured from `GET /rate_limit` and
#: recorded in `collect/adapters/github.py`. Core is 5,000/hour and separate,
#: which is why comment fetching does not compete with discovery.
SEARCH_REQUESTS_PER_MINUTE = 30


@dataclass(frozen=True)
class SweepCost:
    """What a sweep costs in requests and in minutes of the search bucket."""

    models: int
    shapes: tuple[str, ...]
    surfaces_per_model: float
    requests: int

    @property
    def minutes(self) -> float:
        return self.requests / SEARCH_REQUESTS_PER_MINUTE

    #: Documents this would ADD, at the measured unique-on-subject rate for the
    #: shapes issued. An ESTIMATE, and labelled one wherever it is printed: the
    #: rates come from three models and 18 requests, and per-model yield varies
    #: 76 / 8 / 9 on the title arm alone - a factor of nine on the same shape.
    @property
    def unique_on_subject_estimate(self) -> float:
        per_model = sum(UNIQUE_PER_REQUEST[s] for s in self.shapes)
        return per_model * self.models * self.surfaces_per_model


#: Measured 2026-08-28, 18 requests over three models. UNIQUE on-subject per
#: request - documents no other shape found - which is the rate that survives
#: running several arms.
UNIQUE_PER_REQUEST: dict[str, float] = {"title": 26.3, "repro": 10.2}

#: On-subject per request, for the same population. NOT the number that decides
#: an arm - see the block above - and carried only so a report can show both and
#: let the gap between them make the point.
ON_SUBJECT_PER_REQUEST: dict[str, float] = {"title": 31.0, "repro": 15.8}

#: PER-MODEL on-subject on the title arm, one entry per model in the sample:
#: claude-sonnet-4.5, gpt-5.2, qwen3.8-27b. 76, 8, 9.
#:
#: ⚠ THIS IS THE NUMBER THAT STOPS 26.3 BEING READ AS A RATE. A FACTOR OF NINE
#:   between the best and worst model on ONE shape, and the mean sits nowhere
#:   near the middle - 31.0 is above two of the three points. Multiplying it by
#:   342 models produces a five-figure projection from a sample whose spread
#:   covers an order of magnitude, which is a real number answering a question
#:   it was not asked. Any projection built on these rates must show the band.
PER_MODEL_TITLE_ON_SUBJECT: tuple[int, ...] = (76, 8, 9)


def sweep_cost(
    models: int,
    *,
    shapes: Sequence[str] = SWEEP_SHAPES,
    surfaces_per_model: float = 1.0,
) -> SweepCost:
    """Requests and search-bucket minutes for a sweep at a given scale.

    `surfaces_per_model` defaults to 1.0 - one alias per model. It is a float
    because it is an AVERAGE over a registry where some models carry two usable
    surfaces and some carry one, and rounding it to an int would understate the
    cost of exactly the models with the most aliases.
    """
    for shape in shapes:
        if shape in REFUSED_SHAPES:
            raise RefusedShape(shape)
    requests = round(models * surfaces_per_model * len(shapes))
    return SweepCost(
        models=models,
        shapes=tuple(shapes),
        surfaces_per_model=surfaces_per_model,
        requests=requests,
    )


def _narrowing_token(terms: RenderedTerms) -> str | None:
    """The single most selective single-word topic term, or None.

    One token, because a second costs another request and the index cannot OR
    them. Longest wins as a cheap proxy for selectivity: `summarization` narrows
    where `summary` does not.
    """
    candidates = [
        term
        for term in terms.topic
        if not _MULTI_WORD.search(term) and term.casefold() not in _WEAK_TOKENS
    ]
    if not candidates:
        return None
    return max(candidates, key=len)


def assert_renderable_syntax(query: str) -> None:
    """Refuse to issue anything the index would silently reinterpret."""
    found = [token for token in FORBIDDEN_SYNTAX if token in query]
    if found:
        raise UnrenderableError(
            f"refusing to issue {query!r}: it contains {found!r}, which GitHub Search "
            "discards without erroring. That is the defect issue #4 documents — the "
            "query returns what remains and the result reads as an answer."
        )


def render_search(
    entry: QueryEntry,
    alias: str,
    *,
    scope: tuple[str, ...] = (),
    alias_b: str | None = None,
    item_type: str = "issue",
) -> SearchRequest | Unrenderable:
    """One entry plus one alias to one request, or a refusal with a reason.

    Refuses `direction: decided_at_extraction` outright. `"replaced X with Y"`
    and `"replaced Y with X"` are the same query here — measured at 53 against
    52 — so the retrieved set cannot carry direction, and direction is the whole
    content of a substitution claim. Retrieval is still possible as a
    direction-blind superset; deciding to accept that is a coverage decision,
    not something to make silently inside a renderer.

    That reasoning predates the rename and needed no edit, which is the useful
    part: it never rested on an index being ABLE to bind phrases, only on this
    one not carrying direction. The old flag name asserted a cause; this text
    described the consequence, and the consequence is what turned out to be
    true. Only the name lagged.
    """
    if entry.direction_from_extraction:
        return Unrenderable(
            entry_label=entry.label,
            reason=(
                "entry declares direction: decided_at_extraction, and retrieval here "
                "cannot decide direction: "
                '"replaced claude with gpt" returns 53 and "replaced gpt with claude" 52, '
                "so the retrieved set is a direction-blind superset. Extraction reads "
                "direction from the quote; a renderer cannot. Accepting the superset is a "
                "coverage decision and belongs to whoever plans the sweep."
            ),
        )

    if entry.needs_second_model and alias_b is None:
        return Unrenderable(
            entry_label=entry.label,
            reason="entry needs a second model and none was supplied",
        )

    # Two renderings of the same entry, and they must not be the same object.
    #
    #   RETRIEVAL  uses `github_alias_form`, which hyphenates a trailing numeral
    #              so the query cannot collect issue #5 from unrelated repos.
    #   SIEVE      uses the alias EXACTLY as a human writes it, because that is
    #              what the document contains. Sieving with the hyphenated form
    #              would drop every post written in prose — most of them — and
    #              drop them silently.
    #
    # This is the search-versus-attribution split from issue #5, one layer down
    # and inside a single function.
    # `alias_b` gets the same treatment as `alias`, and it did not before.
    #
    # Latent while substitution is refused above, and it stopped being harmless
    # the moment `{alias_b}` moved into `subject`: `parts` is built from the
    # SUBJECT group, so a second model in that group goes into the query itself.
    # Hyphenating one alias and not the other would issue
    # `claude-sonnet-5 "claude opus 5"` and collect issue #5 from unrelated
    # repositories through the half that kept its trailing numeral — the exact
    # noise `github_alias_form` exists to remove, reintroduced through the second
    # argument.
    sieve_terms = entry.terms.substitute(alias, alias_b)
    query_terms = entry.terms.substitute(
        github_alias_form(alias),
        github_alias_form(alias_b) if alias_b is not None else None,
    )

    parts = [f'"{term}"' if _MULTI_WORD.search(term) else term for term in query_terms.subject]

    token = _narrowing_token(query_terms)
    if token:
        parts.append(token)

    parts.append(f"type:{item_type}")
    parts.extend(scope)

    query = " ".join(parts)
    assert_renderable_syntax(query)

    return SearchRequest(
        query=query,
        entry_label=entry.label,
        variants=(sieve_terms,),
        narrowing_token=token,
        scope=tuple(scope),
    )


def plan_searches(
    entries,
    aliases,
    *,
    scope: tuple[str, ...] = (),
    alias_b_by_alias=None,
    subject_forms=None,
) -> SearchPlan:
    """Every request a sweep would issue, and every entry it cannot ask.

    Refusals are returned rather than dropped. A capability that cannot be
    retrieved on a platform is a coverage gap, and a gap nobody can see reads as
    "we looked everywhere" when we did not.
    """
    # Keyed by (entry, query), NOT by query alone.
    #
    # Two entries can render to the same query — `context.effective_window`
    # negative and positive both narrow on `recall` — and deduplicating across
    # them would keep the first entry's sieve terms and discard the second's.
    # The loss would land precisely on the POSITIVE entries, which exist so the
    # four silent-failure capabilities can reach positive consensus at all. Six
    # saved requests is not worth a silent hole there.
    #
    # `distinct_queries` reports the overlap, so the cheaper arrangement stays
    # visible to whoever wants to build it properly.
    # Every spelling the sieve should read documents with. Defaults to the alias
    # list itself, which is one model's forms at every call site today; passed
    # explicitly when a caller sweeps several models at once, since mixing two
    # models' spellings into one subject check would let a post about one satisfy
    # a query about the other.
    forms = tuple(subject_forms) if subject_forms is not None else tuple(aliases)

    by_key: dict[tuple[str, str], SearchRequest] = {}
    refusals: list[Unrenderable] = []
    refused: set[str] = set()

    for entry in entries:
        for alias in aliases:
            alias_b = (alias_b_by_alias or {}).get(alias)
            rendered = render_search(entry, alias, scope=scope, alias_b=alias_b)
            if isinstance(rendered, Unrenderable):
                if rendered.entry_label not in refused:
                    refused.add(rendered.entry_label)
                    refusals.append(rendered)
                continue

            # Deduplicated on the query as issued, keeping every spelling for
            # the sieve. Two alias variants that hyphenate to the same string
            # are one request and two ways of reading its results.
            # Attach every spelling, not just the one that rendered this query.
            #
            # Not for a directional entry: there the terms carry `{alias_b}` as
            # well, and one alias's pairing is not another's, so expanding would
            # build term sets for model pairs nobody asked about.
            if not entry.needs_second_model:
                rendered = replace(
                    rendered,
                    variants=tuple(entry.terms.substitute(form) for form in forms),
                )

            key = (rendered.entry_label, rendered.query)
            if key not in by_key:
                by_key[key] = rendered

    return SearchPlan(requests=tuple(by_key.values()), refusals=tuple(refusals))
