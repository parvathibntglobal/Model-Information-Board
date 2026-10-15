"""The Models pages: OpenRouter's whole list, grouped by provider and by type.

Read from `model_catalog` (collect/registry/catalog.py), never from the evidence
pipeline. What this adds is the link back to the evidence: each model says
whether it is in our registry and whether engineers' reports on it can be read
on the Models detail page (`/reports/models/<id>`) - over the PUBLIC view,
because that is the page the link opens (judge/reports.py).

WHAT IS LEFT OUT, AND SAID
  - `~` ids are OpenRouter's "latest" aliases (`~openai/gpt-sol-latest`), each a
    pointer to a model listed under its own id. Listing both would show one
    model twice and count it twice, so aliases are dropped and counted
    (`aliases_left_out`).
  - A model the latest poll did not list keeps its row but is not shown.

NO PRICE IS INVENTED (rule 6). The feed publishes `0` for every price key of a
video or voice model that is not priced per token - which means "not priced
this way", not free. So a model whose published prices are all zero is shown as
"price not published" unless OpenRouter marks it a free variant (`:free`).
"""

from __future__ import annotations

from collections import Counter
from typing import Any

#: The types the page offers, in its order - OpenRouter's own output modalities
#: (https://openrouter.ai/models?output_modalities=...). `embeddings` and
#: `rerank` exist in the feed too and are not offered as types; a model that
#: outputs only those still appears under its provider.
TYPES = ("text", "image", "video", "speech", "audio", "transcription", "decisions")

#: How many models New releases lists.
NEW_RELEASES = 40


def _price_state(model_id: str, price_in, price_out, pricing: dict) -> str:
    published = [v for v in (pricing or {}).values() if v not in (None, "", "0", 0, "-1", -1)]
    if published:
        return "priced"
    if model_id.endswith(":free"):
        return "free"
    return "not_published"


#: The per-token prices a non-text model is mostly charged by, beyond prompt
#: and completion, in the order the card prefers them, with how it names them.
#: An image model can publish prompt 0 and completion 0 and be priced entirely
#: by `image_output` - showing only the first two would read as free.
TYPE_PRICES = (
    ("image_output", "Image output"),
    ("audio_output", "Audio output"),
    ("image", "Image input"),
    ("audio", "Audio input"),
    ("image_token", "Image tokens"),
)


def _type_price(pricing: dict) -> dict | None:
    for key, label in TYPE_PRICES:
        try:
            v = float((pricing or {}).get(key) or 0)
        except (TypeError, ValueError):
            continue
        if v > 0:
            return {"label": label, "usd_per_million": round(v * 1_000_000, 6)}
    return None


def _provider_names(rows) -> dict[str, str]:
    """`openai` -> `OpenAI`: the commonest prefix of the feed's own names
    ("OpenAI: GPT-6 Sol"), so a provider is spelled the way OpenRouter spells
    it. Falls back to the id segment where no name carries a prefix."""
    seen: dict[str, Counter] = {}
    for r in rows:
        name = r["name"]
        if ":" in name:
            seen.setdefault(r["provider"], Counter())[name.split(":", 1)[0].strip()] += 1
    return {p: c.most_common(1)[0][0] for p, c in seen.items()}


def _engineer_voices(conn) -> tuple[dict[str, int], dict[str, int]]:
    """{canonical id: distinct voices}, {canonical id: distinct reports}, over
    the PUBLIC view - what the reports page a model links to can show.

    DISTINCT ACROSS THE WHOLE MODEL, not summed over its jobs and capabilities:
    one person posting about a model's coding and its price is one voice. A
    report whose author is unknown adds a report and no voice (concern 6)."""
    from judge import publication

    rows = conn.execute(
        "SELECT v.canonical_id, d.source, d.author_id, d.id FROM board_entry be "
        "JOIN document d ON d.id = be.document_id "
        "JOIN model_version v "
        "  ON v.id = be.model_version_id OR v.canonical_id = be.model_version_id "
        "WHERE be.ruling IS DISTINCT FROM 'declined'"
    ).fetchall()
    voices: dict[str, set] = {}
    docs: dict[str, set] = {}
    for cid, source, author, doc in rows:
        if publication.withheld_publicly(source):
            continue
        docs.setdefault(cid, set()).add(doc)
        if author is not None:
            voices.setdefault(cid, set()).add(author)
    return {k: len(v) for k, v in voices.items()}, {k: len(v) for k, v in docs.items()}


def _feature(params: list[str], *names: str) -> bool | None:
    """Whether OpenRouter lists any of `names` for the model. None - not
    stated - when it lists no parameters at all: an empty list is something
    the feed did not tell us, not a feature the model lacks (rule 6)."""
    if not params:
        return None
    return any(n in params for n in names)


def catalog_model(conn, model_id: str) -> dict[str, Any] | None:
    """One model's page: the catalogue row, its specs, the registry's own facts
    where it is tracked, and its engineer voices. None when it is not listed."""
    row = conn.execute(
        "SELECT canonical_id, provider, name, description, listed_at, input_modalities, "
        "       output_modalities, context_length, price_in, price_out, price_cached_read, "
        "       pricing, max_output_tokens, supported_parameters, expiration_date, "
        "       knowledge_cutoff "
        "FROM model_catalog WHERE canonical_id = %s",
        (model_id,),
    ).fetchone()
    if row is None:
        return None
    (
        cid,
        provider,
        name,
        desc,
        listed_at,
        ins,
        outs,
        ctx,
        p_in,
        p_out,
        p_cache,
        pricing,
        max_out,
        params,
        expires,
        feed_cutoff,
    ) = row
    registry = conn.execute(
        "SELECT id, release_date, knowledge_cutoff, lifecycle, deprecation_date, retirement_date "
        "FROM model_version WHERE canonical_id = %s",
        (cid,),
    ).fetchone()
    voices, reports = _engineer_voices(conn)
    params = list(params or [])
    num = lambda v: float(v) if v is not None else None  # noqa: E731
    provider_name = name.split(":", 1)[0].strip() if ":" in name else provider
    return {
        "id": cid,
        "name": name.split(":", 1)[1].strip() if ":" in name else name,
        "provider": provider,
        "provider_name": provider_name,
        "description": desc,
        "listed_at": listed_at.date().isoformat() if listed_at else None,
        "inputs": list(ins or []),
        "outputs": list(outs or []),
        "types": [t for t in (outs or []) if t in TYPES],
        "context": ctx,
        "max_output_tokens": max_out,
        "price_in": num(p_in),
        "price_out": num(p_out),
        "price_cached_read": num(p_cache),
        "price_state": _price_state(cid, p_in, p_out, pricing),
        "type_price": _type_price(pricing),
        # THREE STATES EACH: true, false, or None for "not stated" (rule 6).
        "features": {
            "tools": _feature(params, "tools", "tool_choice"),
            "structured_output": _feature(params, "structured_outputs", "response_format"),
            "reasoning": _feature(params, "reasoning", "include_reasoning"),
            "vision_input": "image" in (ins or []),
            "prompt_caching": True if p_cache is not None else None,
        },
        "in_registry": registry is not None,
        "registry": None
        if registry is None
        else {
            "release_date": registry[1].isoformat() if registry[1] else None,
            "knowledge_cutoff": registry[2].isoformat() if registry[2] else None,
            "lifecycle": registry[3],
            "deprecation_date": registry[4].isoformat() if registry[4] else None,
        },
        "voices": voices.get(cid, 0),
        "reports": reports.get(cid, 0),
        "source": f"https://openrouter.ai/{cid.lstrip('~')}",
        "lifecycle": _lifecycle(
            conn, cid, provider, listed_at, outs, expires, feed_cutoff, registry
        ),
    }


def _iso(d) -> str | None:
    return d.isoformat() if d else None


def _lifecycle(
    conn, cid, provider, listed_at, outs, expires, feed_cutoff, registry
) -> dict[str, Any]:
    """A model's dates, each with WHERE IT CAME FROM - two sources can disagree,
    and a reader deciding whether to build on a model should see which said what.

    RETIREMENT: OpenRouter's `expiration_date`, read twice - by this catalogue's
    poll and, earlier, by the registry poller (`openrouter.py`, which stores it
    as `retirement_date`). ONE SOURCE, NOT TWO: when the readings agree the date
    is shown once; when they differ both are shown, the registry's marked as an
    earlier reading. None anywhere means NONE ANNOUNCED, which the page says in
    those words - never "will not retire" (rule 6).

    `newer_from_provider` lists models the same provider listed later. It is a
    FACT ABOUT DATES, not a claim that any of them replaces this one: which
    model succeeds which is the vendor's to say, and no row here says it."""
    reg_retire = registry[5] if registry is not None else None
    retirements = []
    if expires:
        retirements.append({"date": _iso(expires), "source": "OpenRouter"})
    if reg_retire and reg_retire != expires:
        retirements.append({"date": _iso(reg_retire), "source": "OpenRouter, an earlier reading"})
    newer = []
    if listed_at is not None and outs:
        newer = [
            {
                "id": r[0],
                "name": r[1].split(":", 1)[1].strip() if ":" in r[1] else r[1],
                "listed_at": _iso(r[2].date()),
            }
            for r in conn.execute(
                "SELECT canonical_id, name, listed_at FROM model_catalog "
                # SAME KIND OF MODEL: sharing an output type, and not a
                # `:batch` / `:free` variant of another listing.
                "WHERE provider = %s AND listed_at > %s AND canonical_id NOT LIKE '~%%' "
                "AND canonical_id NOT LIKE '%%:%%' AND canonical_id <> %s "
                "AND output_modalities && %s "
                "AND last_seen_at = (SELECT max(last_seen_at) FROM model_catalog) "
                "ORDER BY listed_at DESC LIMIT 4",
                (provider, listed_at, cid, list(outs or [])),
            ).fetchall()
        ]
    reg_cutoff = registry[2] if registry is not None else None
    return {
        "released": _iso(registry[1]) if registry is not None else None,
        "listed": _iso(listed_at.date()) if listed_at else None,
        "knowledge_cutoff": _iso(reg_cutoff or feed_cutoff),
        "knowledge_cutoff_source": "registry"
        if reg_cutoff
        else "OpenRouter"
        if feed_cutoff
        else None,
        "deprecated": _iso(registry[4]) if registry is not None else None,
        "retirements": retirements,
        "newer_from_provider": newer,
    }


def catalog_view(conn) -> dict[str, Any]:

    try:
        rows = conn.execute(
            "SELECT canonical_id, provider, name, listed_at, input_modalities, output_modalities, "
            "       context_length, price_in, price_out, pricing "
            "FROM model_catalog "
            "WHERE last_seen_at = (SELECT max(last_seen_at) FROM model_catalog)"
        ).fetchall()
    except Exception as e:  # noqa: BLE001 - an unmigrated database is a state, not a crash
        conn.rollback()
        return {
            "models": [],
            "providers": [],
            "types": {},
            "new_releases": [],
            "reason": f"the model catalogue could not be read ({type(e).__name__}) - "
            "run `python -m collect.cli db migrate`, then "
            "`python -m collect.cli registry poll-catalog`",
        }
    if not rows:
        return {
            "models": [],
            "providers": [],
            "types": {},
            "new_releases": [],
            "reason": "the model catalogue is empty - run "
            "`python -m collect.cli registry poll-catalog`",
        }

    registry = {r[0] for r in conn.execute("SELECT canonical_id FROM model_version")}
    voices, reports = _engineer_voices(conn)
    reported = set(reports)

    keep = [r for r in rows if not r[0].startswith("~")]
    aliases = len(rows) - len(keep)
    as_dicts = [{"name": r[2], "provider": r[1]} for r in keep]
    names = _provider_names(as_dicts)

    models = []
    for cid, provider, name, listed_at, ins, outs, ctx, p_in, p_out, pricing in keep:
        models.append(
            {
                "id": cid,
                "name": name.split(":", 1)[1].strip() if ":" in name else name,
                "provider": provider,
                "listed_at": listed_at.date().isoformat() if listed_at else None,
                "inputs": list(ins or []),
                "types": [t for t in (outs or []) if t in TYPES],
                "outputs": list(outs or []),
                "context": ctx,
                "price_in": float(p_in) if p_in is not None else None,
                "price_out": float(p_out) if p_out is not None else None,
                "price_state": _price_state(cid, p_in, p_out, pricing),
                "type_price": _type_price(pricing),
                "in_registry": cid in registry,
                "reported": cid in reported,
                # COUNTED, NOT SCORED (rule 3): distinct people and distinct
                # posts, over the public view. They ORDER All models - most
                # voices first - and are shown on the card beside the order.
                "voices": voices.get(cid, 0),
                "reports": reports.get(cid, 0),
            }
        )
    models.sort(key=lambda m: (m["provider"], m["name"].lower()))

    # ONE BUBBLE PER PROVIDER NAME, not per id. OpenRouter files Meta's models
    # under both `meta` and `meta-llama` and names both "Meta"; two bubbles
    # reading "Meta" would make a reader open both to find one company. The
    # bubble keeps every id it stands for (`ids`), and its `id` is the one
    # holding most models, so an address names it stably.
    by_id = Counter(m["provider"] for m in models)
    grouped: dict[str, list[str]] = {}
    for pid in by_id:
        grouped.setdefault(names.get(pid, pid), []).append(pid)
    providers = []
    for name, ids in grouped.items():
        ids.sort(key=lambda i: (-by_id[i], i))
        providers.append(
            {
                "id": ids[0],
                "name": name,
                "ids": ids,
                "models": sum(by_id[i] for i in ids),
                # Models with at least one engineer voice - what All models lists.
                "voiced": sum(1 for m in models if m["provider"] in ids and m["voices"]),
                "types": sorted(
                    {t for m in models if m["provider"] in ids for t in m["types"]}, key=TYPES.index
                ),
            }
        )
    providers.sort(key=lambda p: (-p["models"], p["name"].lower()))
    types = {t: sum(1 for m in models if t in m["types"]) for t in TYPES}
    # A TYPE STAYS EMPTY UNTIL ONE OF ITS MODELS HAS A VOICE (2026-10-14): All
    # models lists voiced models only, so its type chips count those.
    types_voiced = {t: sum(1 for m in models if t in m["types"] and m["voices"]) for t in TYPES}
    dated = sorted(
        (m for m in models if m["listed_at"]), key=lambda m: m["listed_at"], reverse=True
    )
    return {
        "models": models,
        "providers": providers,
        "types": types,
        "types_voiced": types_voiced,
        "voiced": sum(1 for m in models if m["voices"]),
        "new_releases": [m["id"] for m in dated[:NEW_RELEASES]],
        # The denominators the page states (rule 7).
        "listed": len(models),
        "aliases_left_out": aliases,
        "undated": len(models) - len(dated),
        "polled_at": max(
            r[0] for r in conn.execute("SELECT max(last_seen_at) FROM model_catalog")
        ).isoformat(),
        "source": "https://openrouter.ai/api/v1/models?output_modalities=all",
    }
