"""E3 — `author` rows. FR-17's precondition, and NOT FR-17.

WHAT THIS IS NOT
----------------
This does not cluster identities. FR-17 is *"cluster author identities across
platforms before counting voices — one engineer posting to GitHub and Reddit
would otherwise satisfy the two-platform rule alone"*, and there is **not one
observed instance** of that in anything stored: zero cross-kind duplicate groups
and zero cross-kind clusters over 4,153 documents.

A clustering rule with no observed case is a rule written from imagination, and
#38 measured what that costs — `alias_rows` asked a human for the prose forms a
model is written under, and the corpus turned out to disagree with 8 of 11 primary
surfaces. Three heuristics for identity matching would fail the same way, plausibly
and invisibly.

So: write the rows, measure the overlap, and let the measurement decide whether
FR-17 has anything to match. `collect/CLAUDE.md` already sanctions the outcome
where it has nothing — *"unresolved stays separate, so counts are an upper
bound"*, and an upper bound is the direction the publication gate survives.

THE TWO PLATFORMS ARE SYMMETRIC ON STABLE IDENTITY, WHICH I DID NOT EXPECT
--------------------------------------------------------------------------
    reddit   `author_fullname` — `t2_2ii4xgakc7`. Survives a rename.
    github   `user.id` — `45689065`. Survives a rename. `user.node_id` is
             `MDQ6VXNlcjQ1Njg5MDY1`, which decodes to `04:User45689065`, so the
             two are the same identity in two spellings.

The GitHub adapter was **discarding it**: `_hit_of` kept `user.login` and nothing
else, which is exactly the failure Reddit's canonicalisation exists to avoid — a
renamed account arriving as a new author, and a reused name merging two people.
Now captured as `SearchHit.author_external_id`.

So FR-17's matching problem is not made harder by asymmetry. Both platforms hand
over a permanent account id; what neither hands over is any link BETWEEN them,
which is the actual difficulty and is unchanged.

A MISSING EXTERNAL ID GETS NO ROW
---------------------------------
`author` is `UNIQUE (source, external_id)`, so a NULL or placeholder id would
either fail the constraint or — worse, if someone reached for a sentinel — give
every deleted account the SAME row. Three Reddit comments in the fixture thread
have no `author_fullname` because the account is gone; they must not collapse into
one voice, and FR-17 would then count that voice as corroborating itself.

They are counted and reported as `unattributable` rather than silently dropped.

`handle_hash` — WHAT IT DOES AND DOES NOT PROTECT
--------------------------------------------------
The handle is needed transiently to compute the hash and is retained nowhere: it
is not stored on `AuthorRow`, not in `as_row`, and `handle_hash` is derived at
construction from a parameter that goes out of scope. A test asserts the row
carries no field holding it.

**It is data minimisation, not secrecy.** A plain digest of a public username is
reversible by anyone with a list of usernames, which for GitHub is a public
dataset. What it buys is that the handle cannot be read out of a row, logged by
accident, or published by a query that forgot to exclude a column — which is what
*"hashed: we don't need the handle"* in the schema is asking for. If the intent is
resistance to a determined reversal it needs a keyed hash and a key, and that is a
contract decision rather than something to slip in here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from collect.ids import content_hash, stable_id

log = logging.getLogger(__name__)

GITHUB = "github"
REDDIT = "reddit"

#: Not handles. Reddit substitutes these where the account is gone, and hashing
#: one would give EVERY such author the same `handle_hash` — the shared-value
#: collision this module refuses for a missing handle, arriving by another door.
PLACEHOLDER_HANDLES = frozenset({"[deleted]", "[removed]", "[unavailable]"})


def hash_handle(handle: str | None) -> str | None:
    """A digest of the handle, or None. Casefolded, so a rename in case is one hash.

    None for a missing handle rather than a hash of the empty string — every
    handle-less author would otherwise share one value, which is the collision
    this whole module is careful about (rule 6).
    """
    if not handle or not handle.strip():
        return None
    cleaned = handle.strip().casefold()
    if cleaned in PLACEHOLDER_HANDLES:
        # A marker, not a name. Treated as absent for the same reason None is.
        return None
    return content_hash(cleaned)


@dataclass(frozen=True)
class AuthorRow:
    """One `author` row. Carries no handle — see the module docstring."""

    source: str
    external_id: str
    handle_hash: str | None
    account_created_at: datetime | None = None
    karma: int | None = None
    #: FR-17. Always None here: clustering has no observed case to be built from,
    #: and NULL means "not clustered", never "clustered alone".
    identity_cluster_id: str | None = None

    @property
    def id(self) -> str:
        return stable_id("au", self.source, self.external_id)

    def as_row(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "external_id": self.external_id,
            "handle_hash": self.handle_hash,
            "account_created_at": self.account_created_at,
            "karma": self.karma,
            "identity_cluster_id": self.identity_cluster_id,
        }


@dataclass
class AuthorExtraction:
    """Rows, plus what could not be attributed and why."""

    rows: list[AuthorRow] = field(default_factory=list)
    #: Documents whose author has no stable id. Counted, never given a shared row.
    unattributable: int = 0
    #: Distinct handles seen transiently. A COUNT, not the handles.
    distinct_handles: int = 0

    @property
    def distinct_authors(self) -> int:
        return len({(r.source, r.external_id) for r in self.rows})

    def describe(self) -> str:
        return (
            f"{self.distinct_authors} distinct authors from {len(self.rows)} "
            f"attributions; {self.unattributable} documents had no stable author id "
            "and got no row"
        )


def _dedupe(rows: list[AuthorRow]) -> list[AuthorRow]:
    """One row per (source, external_id). The table's own uniqueness, upheld here.

    Keeps the FIRST occurrence rather than merging: the fields are per-account and
    identical across appearances, so there is nothing to merge, and preferring the
    first keeps the result independent of iteration order.
    """
    seen: dict[tuple[str, str], AuthorRow] = {}
    for row in rows:
        seen.setdefault((row.source, row.external_id), row)
    return list(seen.values())


def from_github(hits) -> AuthorExtraction:
    """Author rows from GitHub search hits.

    `author_external_id` is `user.id`, the stable numeric account id. A hit
    without one comes from a deleted account and gets no row.
    """
    rows: list[AuthorRow] = []
    unattributable = 0
    handles: set[str] = set()
    for hit in hits:
        external_id = getattr(hit, "author_external_id", None)
        handle = getattr(hit, "author", None)
        if not external_id:
            unattributable += 1
            continue
        cleaned = handle.strip().casefold() if handle else ""
        if cleaned and cleaned not in PLACEHOLDER_HANDLES:
            handles.add(cleaned)
        rows.append(AuthorRow(
            source=GITHUB,
            external_id=str(external_id),
            handle_hash=hash_handle(handle),
        ))
    return AuthorExtraction(_dedupe(rows), unattributable, len(handles))


def from_reddit(items) -> AuthorExtraction:
    """Author rows from Reddit posts or comments.

    Accepts either, because both carry `author_fullname`, and canonicalises
    through `author_external_id` so `t2_abc` and `abc` are one author rather
    than two.
    """
    from collect.adapters.reddit import author_external_id

    rows: list[AuthorRow] = []
    unattributable = 0
    handles: set[str] = set()
    for item in items:
        external_id = author_external_id(getattr(item, "author_fullname", None))
        handle = getattr(item, "author", None)
        if not external_id:
            unattributable += 1
            continue
        cleaned = handle.strip().casefold() if handle else ""
        if cleaned and cleaned not in PLACEHOLDER_HANDLES:
            handles.add(cleaned)
        rows.append(AuthorRow(
            source=REDDIT,
            external_id=external_id,
            handle_hash=hash_handle(handle),
        ))
    return AuthorExtraction(_dedupe(rows), unattributable, len(handles))


def write_authors(conn, rows, *, batch: int = 500) -> dict[str, int]:
    """Insert authors. `ON CONFLICT DO NOTHING` on (source, external_id).

    BATCHED, BECAUSE THE ROUND TRIP DOMINATES. One statement per row took ten
    minutes for 4,391 authors against the remote instance — roughly 130ms of
    latency each and almost no work. `executemany` pipelines them, which is the
    difference between a nightly step and a nightly problem.

    Not an upsert: every field here is per-account and does not change between
    appearances, so a second sighting has nothing new to write, and
    `first_seen_at` keeps meaning what it says.

    `identity_cluster_id` is never written. FR-17 has no observed case, and NULL
    means not clustered rather than clustered alone.
    """
    rows = list(rows)
    statement = """
        INSERT INTO author (id, source, external_id, handle_hash,
                            account_created_at, karma)
        VALUES (%(id)s, %(source)s, %(external_id)s, %(handle_hash)s,
                %(account_created_at)s, %(karma)s)
        ON CONFLICT (source, external_id) DO NOTHING
    """
    inserted = 0
    with conn.cursor() as cur:
        for start in range(0, len(rows), batch):
            chunk = [r.as_row() for r in rows[start:start + batch]]
            cur.executemany(statement, chunk)
            # rowcount over an executemany is the total affected, and a conflict
            # affects nothing - so this counts real inserts rather than attempts.
            inserted += max(0, cur.rowcount)
    return {"inserted": inserted, "seen": len(rows)}


def overlap_by_handle(github_handles: set[str], reddit_handles: set[str]) -> set[str]:
    """Handles present on both platforms, casefolded. FR-17's only free signal.

    TRANSIENT BY CONSTRUCTION. Takes handle sets the caller holds before hashing,
    returns the intersection, and stores nothing. This is a MEASUREMENT of whether
    FR-17 has anything to match — not a matcher, and not evidence that a shared
    handle is one person. `jsmith` on both platforms is two people far more often
    than it is one, which is why the answer feeds a decision rather than a merge.
    """
    return {h for h in github_handles & reddit_handles if h}


def now() -> datetime:
    return datetime.now(UTC)
