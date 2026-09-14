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
from collections.abc import Iterable
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


def _scope_of(entry: dict, searched: frozenset[str]) -> str | None:
    """`searched` | `mentioned` | None, for one entry.

    None WHEN THE CALLER DID NOT SAY. A run that does not pass its own
    subject cannot have its rows labelled, and defaulting them to
    `mentioned` would assert a population nobody recorded - the same
    shape as reading an absent flag as `false` (rule 6). The column is
    nullable for exactly this.

    `searched` IS A SET OF IDS, NOT ONE, and that is load-bearing. The
    column it compares holds BOTH shapes for the same model - the
    canonical id when a run names its own subject, the internal `mv_`
    key when the entry was resolved out of the text through
    `model_alias`. Comparing against a single form would label the
    searched model's own rows `mentioned` whenever they happened to
    arrive by the other route, which is the failure this column exists
    to end rather than reproduce.

    An explicit `model_scope` on the entry wins, so a caller that
    already knows is never second-guessed.
    """
    given = entry.get("model_scope")
    if given in ("searched", "mentioned"):
        return given
    if not searched:
        return None
    mv = entry.get("model_version_id")
    if not mv:
        return None
    return "searched" if mv in searched else "mentioned"


def store_entries(
    conn: Any,
    entries: list[dict],
    *,
    proposer_model: str,
    searched_model_version_id: str | Iterable[str] | None = None,
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
    # ONE ID OR SEVERAL, normalised once. A caller knowing only the
    # canonical id may pass a string; one that has resolved both shapes
    # should pass both, and more forms can only make the match better.
    if searched_model_version_id is None:
        searched: frozenset[str] = frozenset()
    elif isinstance(searched_model_version_id, str):
        searched = frozenset({searched_model_version_id})
    else:
        searched = frozenset(x for x in searched_model_version_id if x)

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
                " polarity, proposer_model, model_scope, pipeline_version) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (id) DO NOTHING",
                (
                    entry_id(
                        document_id=e["document_id"], section=section, slug=slug,
                        quote=e["quote"], pipeline_version=pipeline_version,
                    ),
                    section, slug, e["name"], e["definition"],
                    e.get("unit"), e.get("value_verbatim"), e.get("basis"),
                    e.get("model_version_id"), e["document_id"], e.get("claim_id"),
                    e["quote"], True, e["polarity"], proposer_model,
                    _scope_of(e, searched),
                    pipeline_version,
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

    ⚠ ONE REPORT IS ONE SOURCE DOCUMENT. Until 2026-09-11 `reports` was
      incremented once per ROW, and a row is one quote — so the
      `ethical-reasoning` page said "3 reports · verified" about this:

          "it revived both men in 10 out of 20 rounds (50%)"
          "When people are watching, Fable 5.1 never shot, and it revived
           both men in 19 out of 20 rounds (95%)"
          "Fable 5.1 agent shot and killed the man with gold in 2 out of 20
           rounds (10%), and took his gold both times."

      Three figures from ONE Hacker News comment by ONE author. Nothing on this
      read path had ever looked at `document_id` or `author_id`, and the
      inflated count then flipped `evidenceState` past its `reports >= 2`
      threshold, so a single voice was labelled "verified" — the one word this
      board must not be wrong about.

      THE FLOOR ARGUMENT ABOVE DID NOT COVER IT, and that is worth saying
      plainly: fragmentation makes a count too LOW, which a ">= N" label
      handles honestly. Counting quotes as reports made it too HIGH, and no
      amount of "at least" saves a number that overstates corroboration.

      So three figures are now reported separately:

          reports      distinct source documents
          voices       distinct authors — what corroboration must be judged
                       on, because two comments by one person are one voice
          quote_count  rows, so a page can say "3 figures from 1 report"
                       rather than having to pick one of those numbers

    ⚠ A NEGATIVE QUOTE NEVER REACHES `best_for`. It reached it until
      2026-09-11, and the board said this:

          Board / Best for / Coding agents
          What engineers actually ran        01  claude-fable-5-1
          The quotes behind the ranking      "it has created 20+ bugs"

      One complaint, rendered as the top recommendation for the job. The
      pipeline was not wrong - it recorded `polarity: negative` correctly - the
      SURFACE was, because `best_for` means "evidence this model SUITS this
      job" and only a positive report can say that. A problem report names the
      job it happened on; it does not recommend it.

      `capability` and `metric` are NOT filtered, and the difference is the
      point. Those sections describe BEHAVIOUR and FIGURES, where a bad result
      is evidence of exactly the same standing as a good one - "it has failed
      to test the fixes" is a real finding about code-testing. Only "best for"
      makes a claim of suitability, so only "best for" needs the evidence to
      support one.

      THE ROWS ARE NOT DELETED AND NOT REFUSED AT WRITE TIME. They stay, and
      the model page still shows them with their polarity badge, because the
      finding is real and losing it would be the caused absence rule 4 forbids.
      What changes is that a surface promising suitability stops being filled
      by evidence of the opposite.

      This is a rule WE state, not one the classifier infers - the LLM only
      supplies the polarity label (rule 2: it may propose, it may never
      decide). `judge/extract/prompt.py` now also declines to propose these, so
      this filter is the second line rather than the only one.
    """
    rows = conn.execute(
        # LEFT JOIN, not JOIN. `document_id` is NOT NULL and references
        # `document`, so a row without one cannot exist - but an inner join
        # would still make the board's contents depend on the join succeeding,
        # and a quote whose document row was somehow missing would vanish from
        # the board rather than appear without a link. Absent stays absent.
        "SELECT be.section,"
        "       COALESCE(be.ruling_target, be.slug) AS slug,"
        "       be.name, be.definition, be.unit, be.value_verbatim, be.basis,"
        "       be.model_version_id, be.document_id, be.quote, be.polarity,"
        "       be.created_at, d.url, d.author_id,"
        # THE MODEL NAME, JOINED. `board_entry.model_version_id` holds TWO
        # shapes: a run names its own subject with the canonical id
        # (`anthropic/claude-fable-5-1`), while a model resolved out of a
        # thread through `model_alias` is stored as the internal key
        # (`mv_4247e801b…`). `web/src/board/db.js` shortens an id by
        # splitting on "/", so the first became `claude-fable-5-1` and the
        # second rendered raw where a model name belongs. Measured
        # 2026-09-11: 45 of 58 rows carried the internal key.
        #
        # Resolved HERE rather than in the frontend because this is the
        # layer that can see the registry, and matched on EITHER shape so
        # it does not depend on the two writers agreeing first.
        "       v.canonical_id, v.display_name "
        "FROM board_entry be LEFT JOIN document d ON d.id = be.document_id "
        "LEFT JOIN model_version v "
        "  ON v.id = be.model_version_id OR v.canonical_id = be.model_version_id "
        "WHERE be.ruling IS DISTINCT FROM 'declined' "
        # See the docstring. `best_for` claims suitability, so a negative
        # report cannot fill it. Written as NOT(...) rather than a polarity
        # allow-list on purpose: a row whose polarity is NULL or an unseen
        # value stays VISIBLE, because "we could not tell" must not silently
        # delete a finding (rule 6). Only an explicit `negative` is excluded,
        # and only from this one section.
        "  AND NOT (be.section = 'best_for' AND be.polarity = 'negative') "
        "ORDER BY be.section, COALESCE(be.ruling_target, be.slug), be.created_at DESC"
    ).fetchall()

    grouped: dict[str, dict[str, dict]] = {s: {} for s in SECTIONS}
    for (section, slug, name, definition, unit, value, basis,
         mv_id, doc_id, quote, polarity, _created_at, url, author_id,
         canonical, display) in rows:
        # Falls back to the raw id rather than to None: an id nobody can
        # resolve is still better than a blank where a model name belongs,
        # and it names the row to go and look at.
        label = display or canonical or mv_id
        if section not in grouped:
            continue
        bucket = grouped[section].setdefault(
            slug,
            {
                "slug": slug, "name": name, "definition": definition,
                "unit": unit, "quotes": [], "figures": [],
                # SETS, COUNTED AT THE END. `reports` used to be incremented
                # once per ROW, and a row is one quote - so three figures
                # stated in one comment by one person counted as three
                # reports, and `evidenceState` then labelled that "verified"
                # because it was >= 2. Nothing on this read path had ever
                # looked at `document_id` or `author_id` at all.
                "_docs": set(), "_voices": set(), "_models": {},
            },
        )
        bucket["_docs"].add(doc_id)
        if author_id:
            bucket["_voices"].add(author_id)
        if mv_id:
            # Per model, also DISTINCT DOCUMENTS rather than rows, or the
            # models list inherits exactly the same inflation.
            # Keyed by (id, label) so the list can carry BOTH. Keying by
            # the label alone would have emitted a name under the
            # `model_version_id` field, which is the kind of quiet
            # substitution this whole change exists to stop. Distinct
            # documents, as above.
            bucket["_models"].setdefault((mv_id, label), set()).add(doc_id)
        # The quote list is the evidence, so it is capped for payload size rather
        # than sampled - newest first, and the count above is the honest total.
        if len(bucket["quotes"]) < 12:
            bucket["quotes"].append(
                {"quote": quote, "document_id": doc_id, "url": url,
                 "polarity": polarity,
                 "model_version_id": mv_id, "model_label": label}
            )
        if section == "metric" and value is not None:
            # `url` TRAVELS WITH THE FIGURE, for the same reason it travels with
            # the quote directly above. A figure is the most checkable thing on
            # this board and it was the only evidence a reader could not open:
            # `document_id` was sent and `url` was not, so the metric table had
            # no link to render and every published figure was unverifiable.
            #
            # `document_id` is kept as well as the url, and it is the one that
            # matters for honesty rather than convenience: without it the table
            # cannot tell two figures from one article apart from two articles
            # agreeing, which is the `reports`-vs-`quote_count` inflation this
            # file's docstring already describes, arriving by a second route.
            bucket["figures"].append(
                {"value": value, "basis": basis, "unit": unit,
                 "model_version_id": mv_id, "model_label": label,
                 "document_id": doc_id, "url": url}
            )

    out: dict[str, list[dict]] = {}
    for section, by_slug in grouped.items():
        items = []
        for item in by_slug.values():
            # ONE REPORT IS ONE SOURCE DOCUMENT. `voices` is distinct authors,
            # and it is what corroboration has to be judged on: two comments by
            # one person are one voice, and "one voice is not corroboration" is
            # the board's own rule (see `evidenceState` in web/src/board/db.js).
            # `quote_count` stays separate so a page can say "3 figures from 1
            # report" instead of choosing which of those numbers to show.
            item["reports"] = len(item.pop("_docs"))
            item["voices"] = len(item.pop("_voices"))
            item["quote_count"] = len(item["quotes"])
            item["models"] = [
                {"model_version_id": mid, "model_label": lbl,
                 "reports": len(docs)}
                for (mid, lbl), docs in sorted(
                    item.pop("_models").items(), key=lambda kv: -len(kv[1])
                )
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
        "SELECT be.section, COALESCE(be.ruling_target, be.slug) AS slug, be.name,"
        "       be.definition, be.unit, be.value_verbatim, be.basis, be.quote,"
        "       be.polarity, be.document_id, be.created_at, d.url, d.author_id "
        "FROM board_entry be LEFT JOIN document d ON d.id = be.document_id "
        "LEFT JOIN model_version v "
        "  ON v.id = be.model_version_id OR v.canonical_id = be.model_version_id "
        # ⚠ MATCHED ON EITHER SHAPE, AND IT WAS NOT. This was an exact
        # match against a column holding TWO id shapes - the canonical id
        # when a run names its own subject, the internal `mv_` key when the
        # entry was resolved out of a thread. So a page asked for by
        # canonical id returned none of that model's `mv_` rows and
        # rendered "nobody has discussed this": an absence we CAUSED,
        # presented as one we found - rule 4 on the page the rule was
        # written for. Measured 2026-09-11: deepseek-v4-pro returned 0
        # quotes against 6 rows that existed.
        "WHERE (be.model_version_id = %s OR v.id = %s OR v.canonical_id = %s) "
        "  AND be.ruling IS DISTINCT FROM 'declined' "
        "ORDER BY be.section, COALESCE(be.ruling_target, be.slug), be.created_at DESC "
        "LIMIT %s",
        (model_version_id, model_version_id, model_version_id, limit),
    ).fetchall()

    sections: dict[str, dict[str, dict]] = {s: {} for s in SECTIONS}
    for (section, slug, name, definition, unit, value, basis,
         quote, polarity, doc_id, _created, url, author_id) in rows:
        if section not in sections:
            continue
        bucket = sections[section].setdefault(slug, {
            "slug": slug, "name": name, "definition": definition,
            "unit": unit, "quotes": [], "figures": [],
            # Same correction as `board_sections` - see its docstring. A model
            # page counting quotes as reports overstates its own evidence in
            # exactly the same way.
            "_docs": set(), "_voices": set(),
        })
        bucket["_docs"].add(doc_id)
        if author_id:
            bucket["_voices"].add(author_id)
        bucket["quotes"].append(
            {"quote": quote, "polarity": polarity, "document_id": doc_id, "url": url}
        )
        if section == "metric" and value is not None:
            # stated and reported stay side by side here too. A model page that
            # averaged an advertised ceiling with a measured figure would be
            # describing a number nobody produced.
            #
            # AND THE SOURCE COMES WITH THEM. This carried neither `document_id`
            # nor `url` - less than `board_sections` sent, so the model page's
            # figures were doubly unattributable: no link to open and no way to
            # see that two rows came from one article. Same three fields as the
            # quote above, because a figure is evidence on the same terms.
            bucket["figures"].append(
                {"value": value, "basis": basis, "unit": unit,
                 "document_id": doc_id, "url": url}
            )

    out = {}
    for section, by_slug in sections.items():
        for item in by_slug.values():
            item["reports"] = len(item.pop("_docs"))
            item["voices"] = len(item.pop("_voices"))
            item["quote_count"] = len(item["quotes"])
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
