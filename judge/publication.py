"""Which sources a public surface may show, and whether this deployment is public.

ONE PLACE, so the board, the model pages, /compare, /filtered, the document
source route and the blog generator cannot drift apart. The list itself is in
`contract/publication.yaml` (rule 5); this module only reads it.

THE VIEW IS PUBLIC UNLESS A DEPLOYMENT SAYS OTHERWISE. `PUBLICATION_VIEW` is
`public` or `internal`. Unset means `public`: a deployment that forgot to say
what it is withholds, which is the safe direction - an over-withheld page is
visible and arguable, an over-published quote cannot be taken back. Any other
value raises (rule 12): a typo must not pick a side.

`internal` is for the team's own board, where collected material is read but
not published. It is a statement about who can reach the deployment, and the
undertaking in `contract/sources.yaml` is what makes that statement checkable.
"""
from __future__ import annotations

import os
from functools import lru_cache

VIEWS = ("public", "internal")


class PublicationConfigError(RuntimeError):
    """`contract/publication.yaml` or `PUBLICATION_VIEW` is missing or malformed."""


@lru_cache(maxsize=1)
def withheld_sources() -> tuple[str, ...]:
    """`document.source` values that never appear on a public surface."""
    from judge.config import _read

    raw = _read("publication.yaml") or {}
    block = raw.get("withheld_from_public") or {}
    sources = block.get("sources")
    if not isinstance(sources, list) or not sources:
        raise PublicationConfigError(
            "contract/publication.yaml has no `withheld_from_public.sources` list. "
            "An empty or missing list would publish every source, so this refuses "
            "rather than reading the absence as permission (rule 6)."
        )
    return tuple(str(s).strip() for s in sources)


def view() -> str:
    raw = os.getenv("PUBLICATION_VIEW")
    if raw is None or not raw.strip():
        return "public"
    value = raw.strip()
    if value not in VIEWS:
        raise PublicationConfigError(
            f"PUBLICATION_VIEW={value!r} is not one of {VIEWS}. Refusing rather "
            "than guessing which side a typo meant."
        )
    return value


def is_public() -> bool:
    return view() == "public"


def hidden_here() -> tuple[str, ...]:
    """The sources THIS deployment withholds: the contract's list when public,
    none when internal."""
    return withheld_sources() if is_public() else ()


def withheld(source: str | None) -> bool:
    """True when a row from `source` must not be shown here.

    A row with NO known source is withheld on a public view: provenance we
    cannot name is not provenance we can publish (rule 6).
    """
    hidden = hidden_here()
    if not hidden:
        return False
    return source is None or source in hidden


def notice(count: int) -> dict:
    """What a payload carries when rows were withheld by source (rule 4).

    `count` is what this read dropped. The platforms are NOT named: public
    material never names a source platform (the team's standing rule, see
    `docs/proposals/public-surfaces-withhold-reddit-arxiv-x.md`), so the page
    can say that some sources are not shown and how many entries that cost,
    and nothing about which or about the rows themselves.
    """
    return {"view": view(), "sources_withheld": len(hidden_here()), "entries": count}


def sql_public_document(doc_col: str) -> tuple[str, tuple]:
    """An `AND ...` clause keeping only rows whose document may be shown here.

    `doc_col` names the column holding `document.id` (for example
    `board_entry.document_id`). On an internal view the clause is a no-op; on a
    public one a row survives only when its document has a KNOWN source outside
    the withheld list - unknown provenance is withheld, as in `withheld()`.
    Returns the SQL and its two parameters, in order.
    """
    hidden = list(hidden_here())
    clause = (
        " AND (cardinality(%s::text[]) = 0 OR EXISTS ("
        "SELECT 1 FROM document pub_d WHERE pub_d.id = " + doc_col +
        " AND pub_d.source IS NOT NULL AND NOT pub_d.source = ANY(%s::text[]))) "
    )
    return clause, (hidden, hidden)
