"""Persist what the classifier discovered, and serve the Board page from it.

The classifier NAMES a job, a capability or a metric; nothing here decides one.
Rows land in `board_entry` and the Board page groups them by slug. There is no
publication gate, deliberately — see the table comment. `cell` publishes a
verdict and is gated; these three sections are observations, and gating them
behind four agreeing voices would leave the board empty while the evidence sat
in the database.

WHAT THIS MODULE IS ACTUALLY FOR, beyond the INSERT
---------------------------------------------------
An open vocabulary trades gaps for DUPLICATES: "function calling" and "tool
calling" from two threads are one section under two names. Two things narrow
that, and neither is a model deciding anything.

  `normalise_slug`   mechanical only. Case, spacing, punctuation, a leading
                     `job.`/`metric.` prefix if the model emitted one. It cannot
                     tell that two different WORDS mean one thing, and it does
                     not try — guessing that would be the LLM's judgement moved
                     into code, which is the same mistake wearing a hat.

  `ruling`           a person folds one slug into another (`merged` +
                     `ruling_target`), through the same shape
                     `capability_candidate` already uses. That is the only place
                     a synonym is resolved.

IDEMPOTENT, and that is the report count's integrity. `id` is the content hash
of the natural key (document, section, slug, quote, pipeline_version), written
`ON CONFLICT DO NOTHING`, so re-classifying the same corpus cannot inflate the
number of reports the page shows.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from judge.store.claims import PIPELINE_VERSION

SECTIONS = ("best_for", "capability", "metric")

#: Anything that is not a letter, a digit or a hyphen becomes a hyphen.
_NON_SLUG = re.compile(r"[^a-z0-9]+")
#: A prefix the classifier is told not to emit but might: `job.rag` -> `rag`.
_PREFIX = re.compile(r"^(job|metric|capability|cap)[._-]")


def normalise_slug(raw: str) -> str:
    """Mechanical slug normalisation. NO synonym resolution.

    `Function Calling`, `function calling` and `function_calling` are one slug.
    `tool-calling` is NOT folded into `function-calling` here, however obvious
    that looks: a synonym table in code is a judgement about meaning, and the
    moment it is wrong it silently merges two genuinely different sections. That
    call belongs to a person, through `ruling`.
    """
    slug = _NON_SLUG.sub("-", raw.strip().casefold()).strip("-")
    slug = _PREFIX.sub("", slug)
    return slug.strip("-")


def entry_id(
    *, document_id: str, section: str, slug: str, quote: str, pipeline_version: str
) -> str:
    """Content hash of the natural key, so a re-run produces the same id."""
    digest = hashlib.sha256(
        "\x1f".join([document_id, section, slug, quote, pipeline_version]).encode("utf-8")
    ).hexdigest()
    return f"be_{digest[:24]}"


def store_entries(
    conn: Any,
    entries: list[dict],
    *,
    proposer_model: str,
    pipeline_version: str = PIPELINE_VERSION,
) -> dict[str, int]:
    """Append discovered entries. Returns {proposed, stored, skipped_unverified}.

    Each dict carries: section, slug, name, definition, document_id, quote,
    quote_verified, polarity, and optionally model_version_id, claim_id, and
    unit/value_verbatim/basis for a metric.

    AN UNVERIFIED QUOTE IS NOT STORED, and it is counted rather than dropped
    quietly. The table CHECKs `quote_verified = true`, so passing one would
    raise and take the whole batch with it; refusing it here keeps the rest of
    the batch and still reports that it happened. Rule 1 has no exception for a
    new table, and rule 4 says the refusal must be visible.
    """
    proposed = len(entries)
    stored = 0
    skipped = 0
    with conn.cursor() as cur:
        for e in entries:
            if not e.get("quote_verified"):
                skipped += 1
                continue
            section = e["section"]
            if section not in SECTIONS:
                raise ValueError(
                    f"unknown board section {section!r}: the three sections are "
                    f"{SECTIONS}. A new section is a product decision, not a "
                    "value the classifier may invent - unlike the slug, which it "
                    "may."
                )
            slug = normalise_slug(e["slug"])
            if not slug:
                skipped += 1
                continue
            cur.execute(
                "INSERT INTO board_entry "
                "(id, section, slug, name, definition, unit, value_verbatim, basis,"
                " model_version_id, document_id, claim_id, quote, quote_verified,"
                " polarity, proposer_model, pipeline_version) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (id) DO NOTHING",
                (
                    entry_id(
                        document_id=e["document_id"], section=section, slug=slug,
                        quote=e["quote"], pipeline_version=pipeline_version,
                    ),
                    section, slug, e["name"], e["definition"],
                    e.get("unit"), e.get("value_verbatim"), e.get("basis"),
                    e.get("model_version_id"), e["document_id"], e.get("claim_id"),
                    e["quote"], True, e["polarity"], proposer_model, pipeline_version,
                ),
            )
            stored += cur.rowcount  # 1 on insert, 0 on conflict
    return {"proposed": proposed, "stored": stored, "skipped_unverified": skipped}


# ── the Board page read ──────────────────────────────────────────────────────


def board_sections(conn: Any) -> dict[str, list[dict]]:
    """Everything the Board page renders, grouped by section then slug.

    Returns {"best_for": [...], "capability": [...], "metric": [...]}, each item
    a discovered section with its report count, the models named in it, and the
    quotes behind it.

    `declined` rows are excluded and `merged` rows are counted under their
    target, so a person's consolidation shows up here without rewriting history
    — the rows stay, the grouping changes.

    THE REPORT COUNT IS A FLOOR, and it is labelled that way wherever it is
    shown. An open vocabulary fragments one section across phrasings until
    somebody merges them, so `reports` is ">= N" rather than N. Saying so is
    rule 7: the figure travels with what it actually counted.
    """
    rows = conn.execute(
        "SELECT section,"
        "       COALESCE(ruling_target, slug) AS slug,"
        "       name, definition, unit, value_verbatim, basis,"
        "       model_version_id, document_id, quote, polarity, created_at "
        "FROM board_entry "
        "WHERE ruling IS DISTINCT FROM 'declined' "
        "ORDER BY section, COALESCE(ruling_target, slug), created_at DESC"
    ).fetchall()

    grouped: dict[str, dict[str, dict]] = {s: {} for s in SECTIONS}
    for (section, slug, name, definition, unit, value, basis,
         mv_id, doc_id, quote, polarity, _created_at) in rows:
        if section not in grouped:
            continue
        bucket = grouped[section].setdefault(
            slug,
            {
                "slug": slug, "name": name, "definition": definition,
                "unit": unit, "reports": 0, "models": {}, "quotes": [], "figures": [],
            },
        )
        bucket["reports"] += 1
        if mv_id:
            bucket["models"][mv_id] = bucket["models"].get(mv_id, 0) + 1
        # The quote list is the evidence, so it is capped for payload size rather
        # than sampled - newest first, and the count above is the honest total.
        if len(bucket["quotes"]) < 12:
            bucket["quotes"].append(
                {"quote": quote, "document_id": doc_id, "polarity": polarity,
                 "model_version_id": mv_id}
            )
        if section == "metric" and value is not None:
            bucket["figures"].append(
                {"value": value, "basis": basis, "unit": unit,
                 "model_version_id": mv_id, "document_id": doc_id}
            )

    out: dict[str, list[dict]] = {}
    for section, by_slug in grouped.items():
        items = []
        for item in by_slug.values():
            item["models"] = [
                {"model_version_id": m, "reports": n}
                for m, n in sorted(item["models"].items(), key=lambda kv: -kv[1])
            ]
            if section != "metric":
                item.pop("figures", None)
                item.pop("unit", None)
            items.append(item)
        # Most-reported first: the ordering is a COUNT, never a score.
        items.sort(key=lambda i: (-i["reports"], i["slug"]))
        out[section] = items
    return out


# ── the admin review surface ─────────────────────────────────────────────────
#
# An open vocabulary means DUPLICATES are the failure mode, not gaps: "function
# calling" and "tool calling" arriving from two threads are one board section
# under two names. Nothing in code can decide they are the same - that is a
# judgement about meaning, and a wrong synonym table silently merges two real
# sections. So a person rules, through the columns the table already has.
#
# A ruling is CONSOLIDATION, NOT PUBLICATION. There is no gate here: an unruled
# entry is already on the board. `declined` removes one, `merged` folds it into
# another slug, `adopted` marks it reviewed and changes nothing. That is the
# opposite of `capability_candidate`, where a ruling ADMITS a key - and the
# difference is deliberate, because holding these back until review would leave
# the board empty for exactly as long as nobody looked at it.

RULINGS = ("adopted", "declined", "merged")


def list_for_review(conn) -> list[dict]:
    """Discovered sections grouped by slug, newest evidence first.

    An admin rules on a SECTION, so this groups by (section, slug) rather than
    returning one row per quote: merging "tool-calling" into "function-calling"
    is one decision about a word, not nine about nine quotes. The document count
    behind it is the evidence for that decision, so it is shown.
    """
    rows = conn.execute(
        "SELECT section, slug, min(name) AS name, min(definition) AS definition,"
        "       count(*) AS entries, count(DISTINCT document_id) AS documents,"
        "       count(DISTINCT model_version_id) AS models,"
        "       max(created_at) AS newest,"
        "       max(ruling) AS ruling, max(ruling_target) AS ruling_target,"
        "       max(reviewed_at) AS reviewed_at "
        "FROM board_entry GROUP BY section, slug "
        "ORDER BY section, count(*) DESC, slug"
    ).fetchall()
    out = []
    for (section, slug, name, definition, entries, documents, models,
         newest, ruling, ruling_target, reviewed_at) in rows:
        quotes = conn.execute(
            "SELECT quote, polarity, model_version_id, document_id "
            "FROM board_entry WHERE section = %s AND slug = %s "
            "ORDER BY created_at DESC LIMIT 5",
            (section, slug),
        ).fetchall()
        out.append({
            "section": section, "slug": slug, "name": name, "definition": definition,
            "entries": entries, "documents": documents, "models": models,
            "newest": newest.isoformat() if newest else None,
            "ruling": ruling, "ruling_target": ruling_target,
            "reviewed_at": reviewed_at.isoformat() if reviewed_at else None,
            "quotes": [
                {"quote": q, "polarity": p, "model_version_id": m, "document_id": d}
                for q, p, m, d in quotes
            ],
        })
    return out


def rule_entries(conn, *, section: str, slug: str, ruling: str,
                 ruling_target: str | None = None) -> int:
    """Rule every entry under one slug. Returns rows ruled.

    `ruling_target` is NORMALISED like any other slug, so a reviewer typing
    "Function Calling" folds into the same bucket the classifier produced. The
    alternative - trusting free text - is how a merge silently creates a third
    section instead of removing one.

    Re-ruling is allowed and is not an error: a person changing their mind is
    the point of a review surface, and the row keeps its evidence either way.
    """
    if ruling not in RULINGS:
        raise ValueError(f"ruling must be one of {RULINGS}, not {ruling!r}")
    if ruling == "merged" and not (ruling_target or "").strip():
        raise ValueError(
            "a merge needs a ruling_target: the slug this one folds into. Without "
            "it the rows would be hidden rather than merged, which loses the "
            "evidence instead of consolidating it."
        )
    target = normalise_slug(ruling_target) if ruling_target else None
    if ruling == "merged" and target == normalise_slug(slug):
        raise ValueError("cannot merge a slug into itself")
    cur = conn.execute(
        "UPDATE board_entry SET ruling = %s, ruling_target = %s, reviewed_at = now() "
        "WHERE section = %s AND slug = %s",
        (ruling, target, section, slug),
    )
    return cur.rowcount


def unrule_entries(conn, *, section: str, slug: str) -> int:
    """Undo a ruling, putting the section back on the board.

    Present because `reviewed_at` and `ruling` are CHECKed to move together, so
    clearing one by hand would violate the constraint - and a review surface a
    person cannot back out of is one they will hesitate to use.
    """
    cur = conn.execute(
        "UPDATE board_entry SET ruling = NULL, ruling_target = NULL, reviewed_at = NULL "
        "WHERE section = %s AND slug = %s",
        (section, slug),
    )
    return cur.rowcount


def evidence_for_model(conn, model_version_id: str, *, limit: int = 200) -> dict:
    """Every discovered section this model was named in, with the quotes.

    THE MODEL PAGE'S HALF OF THE SAME CORPUS. The board groups by section and
    asks "who has been reported doing this"; a model page groups by model and
    asks "what has been said about it". One table, two questions, and neither is
    derived from the other — so this reads `board_entry` directly rather than
    filtering the board payload, which would make the model page depend on how
    the board happens to sort.

    `declined` rows are excluded and `merged` rows report under their target, so
    a reviewer consolidating two slugs changes what this returns without any
    evidence being rewritten.

    Quotes are the point of the page and are returned in full. They are already
    verified — the table CHECKs `quote_verified` — so what reaches the reader is
    what the engineer wrote, resolved back to the raw span.
    """
    rows = conn.execute(
        "SELECT section, COALESCE(ruling_target, slug) AS slug, name, definition,"
        "       unit, value_verbatim, basis, quote, polarity, document_id, created_at "
        "FROM board_entry "
        "WHERE model_version_id = %s AND ruling IS DISTINCT FROM 'declined' "
        "ORDER BY section, COALESCE(ruling_target, slug), created_at DESC "
        "LIMIT %s",
        (model_version_id, limit),
    ).fetchall()

    sections: dict[str, dict[str, dict]] = {s: {} for s in SECTIONS}
    for (section, slug, name, definition, unit, value, basis,
         quote, polarity, doc_id, _created) in rows:
        if section not in sections:
            continue
        bucket = sections[section].setdefault(slug, {
            "slug": slug, "name": name, "definition": definition,
            "unit": unit, "reports": 0, "quotes": [], "figures": [],
        })
        bucket["reports"] += 1
        bucket["quotes"].append(
            {"quote": quote, "polarity": polarity, "document_id": doc_id}
        )
        if section == "metric" and value is not None:
            # stated and reported stay side by side here too. A model page that
            # averaged an advertised ceiling with a measured figure would be
            # describing a number nobody produced.
            bucket["figures"].append({"value": value, "basis": basis, "unit": unit})

    out = {}
    for section, by_slug in sections.items():
        items = sorted(by_slug.values(), key=lambda i: (-i["reports"], i["slug"]))
        if section != "metric":
            for i in items:
                i.pop("figures", None)
                i.pop("unit", None)
        out[section] = items
    return {
        "model_version_id": model_version_id,
        "best_for": out["best_for"],
        "capabilities": out["capability"],
        "metrics": out["metric"],
        "totals": {
            "sections": sum(len(v) for v in out.values()),
            "quotes": sum(len(i["quotes"]) for v in out.values() for i in v),
        },
    }
