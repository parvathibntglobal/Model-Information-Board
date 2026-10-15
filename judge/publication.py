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


@lru_cache(maxsize=1)
def totals_include_withheld() -> bool:
    """Whether a public TOTAL counts rows from the withheld sources
    (contract/publication.yaml `withheld_from_public.totals_include_withheld`).

    true since 2026-10-15: "20 voices" counts every source, and nothing on a
    page says how many came from which platform. Quotes, links, handles,
    platform names and per-platform counts stay withheld whatever this says.
    Must be a boolean; absent raises (rule 6) - a guess here would either hide
    real evidence or publish a split the contract forbids.
    """
    from judge.config import _read

    raw = _read("publication.yaml") or {}
    value = (raw.get("withheld_from_public") or {}).get("totals_include_withheld")
    if not isinstance(value, bool):
        raise PublicationConfigError(
            "contract/publication.yaml `withheld_from_public.totals_include_withheld` "
            f"must be true or false, not {value!r}. Refusing rather than guessing "
            "whether a public total may count the withheld sources."
        )
    return value


def hidden_from_counts() -> tuple[str, ...]:
    """The sources a public TOTAL leaves out: none when totals include every
    source, the withheld list otherwise. For counts only - a quote, a link, a
    handle or a platform name is filtered with `withheld_sources()` always."""
    return () if totals_include_withheld() else withheld_sources()


@lru_cache(maxsize=1)
def derived_posts_may_draw_on_withheld() -> bool:
    """Whether a blog draft may be written from a withheld source.

    `contract/publication.yaml` `derived_posts.may_draw_on_withheld`. Must be a
    boolean; absent or anything else raises (rule 6) - the generator must never
    infer permission from a missing key, nor refusal from a typo.
    """
    from judge.config import _read

    raw = (_read("publication.yaml") or {}).get("derived_posts") or {}
    value = raw.get("may_draw_on_withheld")
    if not isinstance(value, bool):
        raise PublicationConfigError(
            "contract/publication.yaml `derived_posts.may_draw_on_withheld` must be "
            f"true or false, not {value!r}. Refusing rather than guessing whether "
            "blog drafts may draw on withheld sources."
        )
    return value


@lru_cache(maxsize=1)
def derived_posts_embed_only() -> tuple[str, ...]:
    """Sources a published post may show ONLY as the platform's official embed.

    `contract/publication.yaml` `derived_posts.embed_only` (re-reviewed
    2026-10-13). Must be a list; absent raises (rule 6). An empty list is a
    definite "quote every source", so it is accepted - but only when written.
    """
    from judge.config import _read

    raw = (_read("publication.yaml") or {}).get("derived_posts") or {}
    if "embed_only" not in raw or not isinstance(raw["embed_only"], list):
        raise PublicationConfigError(
            "contract/publication.yaml `derived_posts.embed_only` must be a list of "
            f"sources, not {raw.get('embed_only')!r}. Refusing rather than guessing "
            "which sources a post may quote."
        )
    return tuple(str(s).strip() for s in raw["embed_only"])


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


def withheld_publicly(source: str | None) -> bool:
    """True when a row from `source` would be withheld on the PUBLIC view,
    whatever view this deployment runs.

    For decisions about public pages made by an internal deployment - which
    pages are worth indexing (`judge/seo.py`) - where counting with the
    deployment's own view would count sources the public page never shows.
    """
    return source is None or source in withheld_sources()


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
    return _sql_filter(doc_col, list(hidden_here()))


def sql_counted_document(doc_col: str) -> tuple[str, tuple]:
    """The same clause for a public TOTAL: keeps every row when totals include
    every source (`totals_include_withheld`), whatever view the deployment runs.
    Never use it for a quote, a link, a handle or a platform name."""
    return _sql_filter(doc_col, list(hidden_from_counts()))


def sql_shown_document(doc_col: str) -> tuple[str, tuple]:
    """The same clause for anything that SHOWS a source - a quote, a link, a
    platform name, a per-platform number - with the contract's withheld list
    applied whatever view the deployment runs."""
    return _sql_filter(doc_col, list(withheld_sources()))


def _sql_filter(doc_col: str, hidden: list[str]) -> tuple[str, tuple]:
    clause = (
        " AND (cardinality(%s::text[]) = 0 OR EXISTS ("
        "SELECT 1 FROM document pub_d WHERE pub_d.id = " + doc_col +
        " AND pub_d.source IS NOT NULL AND NOT pub_d.source = ANY(%s::text[]))) "
    )
    return clause, (hidden, hidden)
