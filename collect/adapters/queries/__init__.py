"""The rendering half of `contract/queries.yaml`.

Engineer 2's file carries what a query must MEAN. This package carries what an
adapter sends and what it keeps, and the split between those two is the whole
design:

    RETRIEVAL   broad and cheap, whatever an index honours. Its only job is to
                produce candidate documents. Precision here is not worth paying
                for, because the index cannot deliver it.

    SIEVE       local, exact, identical on all three platforms. This is where
                the terms do their actual work.

One sieve, three platforms. Blogs skip retrieval entirely — RSS is a fetch of a
known URL, so the same terms are a post-fetch relevance filter there. GitHub
issues one cheap request per entry and lets the sieve do the narrowing, because
issue #4 and issue #5 measured that its index cannot express any-of, cannot
honour a phrase, discards grouping and wildcards, and matches a trailing numeral
against the issue number.

    contract.py   load queries.yaml into typed entries; substitute {alias}
    sieve.py      the shared local filter — exact phrases, bounded stems
    github.py     GitHub retrieval, and a refusal where retrieval cannot work
"""

from collect.adapters.queries.contract import (
    QueryEntry,
    QuerySet,
    RenderedTerms,
    TermSet,
    load_queries,
)
from collect.adapters.queries.github import (
    FORBIDDEN_SYNTAX,
    SearchPlan,
    SearchRequest,
    Unrenderable,
    github_alias_form,
    plan_searches,
    render_search,
)
from collect.adapters.queries.sieve import SieveVerdict, matches, sieve, sieve_any

__all__ = [
    "FORBIDDEN_SYNTAX",
    "QueryEntry",
    "QuerySet",
    "RenderedTerms",
    "SearchPlan",
    "SearchRequest",
    "SieveVerdict",
    "TermSet",
    "Unrenderable",
    "github_alias_form",
    "load_queries",
    "matches",
    "plan_searches",
    "render_search",
    "sieve",
    "sieve_any",
]
