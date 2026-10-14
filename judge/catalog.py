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


def catalog_view(conn) -> dict[str, Any]:
    from judge import publication

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

    # WHICH CATALOGUE MODELS HAVE REPORTS A READER CAN OPEN: rows in our
    # registry with a board entry from a source the public view shows.
    registry = {r[0] for r in conn.execute("SELECT canonical_id FROM model_version")}
    reported_rows = conn.execute(
        "SELECT DISTINCT v.canonical_id, d.source FROM board_entry be "
        "JOIN document d ON d.id = be.document_id "
        "JOIN model_version v "
        "  ON v.id = be.model_version_id OR v.canonical_id = be.model_version_id "
        "WHERE be.ruling IS DISTINCT FROM 'declined'"
    ).fetchall()
    reported = {cid for cid, source in reported_rows if not publication.withheld_publicly(source)}

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
                "types": sorted(
                    {t for m in models if m["provider"] in ids for t in m["types"]}, key=TYPES.index
                ),
            }
        )
    providers.sort(key=lambda p: (-p["models"], p["name"].lower()))
    types = {t: sum(1 for m in models if t in m["types"]) for t in TYPES}
    dated = sorted(
        (m for m in models if m["listed_at"]), key=lambda m: m["listed_at"], reverse=True
    )
    return {
        "models": models,
        "providers": providers,
        "types": types,
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
