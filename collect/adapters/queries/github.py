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
    sieve_terms = entry.terms.substitute(alias, alias_b)
    query_terms = entry.terms.substitute(github_alias_form(alias), alias_b)

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
