"""OpenRouter's whole model list - every output type - for the Models pages.

WHY A SECOND LIST, AND NOT MORE ROWS IN `model_version`

`model_version` is the registry the EVIDENCE pipeline reads: what is
`in_window` decides what the nightly chain plans searches for, and every row in
it is a model somebody may fetch reports about. `openrouter.py` reads the
feed's default listing, which is TEXT models only (462 of 667 on 2026-10-14).

The Models pages need the rest too - image, video, speech, audio,
transcription and decision models - because a reader browsing "what models
exist" is asking a different question from "which models do we collect
evidence on". Putting ~200 voice, video and classifier models into
`model_version` would answer the second question by accident, the same trap
`openrouter.py`'s docstring describes for the sweep. So the catalogue is its own
table, and nothing in the evidence pipeline reads it.

WHAT A TYPE IS. OpenRouter's own `architecture.output_modalities`, copied as
published - `text`, `image`, `video`, `speech`, `audio`, `transcription`,
`decisions`, and also `embeddings` and `rerank`. The board does not invent a
taxonomy: a model is an Image model because OpenRouter lists it producing
images (https://openrouter.ai/models?output_modalities=image).

`listed_at` IS WHEN OPENROUTER LISTED IT (`created`), NOT A VENDOR'S RELEASE
DATE. The two usually agree within days; where they do not, the page says
"listed", not "released".

NO CREDENTIAL, same as `openrouter.py`: the endpoint answers unauthenticated.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from psycopg.types.json import Jsonb

from collect.registry.openrouter import MODELS_URL, UnreadableFeed, _per_million

#: Every output type, not the default text-only listing.
CATALOG_URL = f"{MODELS_URL}?output_modalities=all"


def provider_of(model_id: str) -> str:
    """The vendor segment of an OpenRouter id. A leading `~` marks a "latest"
    alias (`~perplexity/pplx-decider-27b-latest`) and is not part of the name."""
    return model_id.lstrip("~").split("/", 1)[0]


def _listed_at(created: Any) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(created), tz=UTC)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _date_or_none(v: Any):
    """An ISO date from the feed, or None. A malformed value is None - never
    a guessed date (rule 6)."""
    from datetime import date

    try:
        return date.fromisoformat(str(v)[:10]) if v else None
    except ValueError:
        return None


def _int_or_none(v: Any) -> int | None:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def parse_catalog(payload: Any) -> list[dict[str, Any]]:
    """The feed's entries as catalogue rows. RAISES on a payload it cannot read
    and on one that holds no models: a feed that parses to nothing is a feed we
    could not read, not a world with no models (the registry stage learned this
    by reporting `OK models=0` for its whole life)."""
    data = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(data, list):
        raise UnreadableFeed(f"the catalogue feed is a {type(payload).__name__}, not a model list")
    rows: list[dict[str, Any]] = []
    for entry in data:
        if not isinstance(entry, dict) or not entry.get("id"):
            continue
        arch = entry.get("architecture") or {}
        pricing = entry.get("pricing") or {}
        rows.append(
            {
                "canonical_id": str(entry["id"]),
                "provider": provider_of(str(entry["id"])),
                "name": str(entry.get("name") or entry["id"]),
                "description": entry.get("description") or None,
                "listed_at": _listed_at(entry.get("created")),
                "input_modalities": [str(m) for m in arch.get("input_modalities") or []],
                "output_modalities": [str(m) for m in arch.get("output_modalities") or []],
                "context_length": entry.get("context_length")
                if isinstance(entry.get("context_length"), int)
                else None,
                # PER TOKEN WHERE THE FEED PRICES PER TOKEN, ELSE NULL. A voice or
                # video model is priced per character, per second or per image -
                # `pricing` keeps that as published, and a NULL here means "not a
                # per-token price", never "free" (rule 6).
                "price_in": _per_million(pricing.get("prompt")),
                "price_out": _per_million(pricing.get("completion")),
                "price_cached_read": _per_million(pricing.get("input_cache_read")),
                "max_output_tokens": _int_or_none(
                    (entry.get("top_provider") or {}).get("max_completion_tokens")
                ),
                "supported_parameters": [str(x) for x in entry.get("supported_parameters") or []],
                "expiration_date": _date_or_none(entry.get("expiration_date")),
                "knowledge_cutoff": _date_or_none(entry.get("knowledge_cutoff")),
                "pricing": pricing,
            }
        )
    if not rows:
        raise UnreadableFeed(f"the catalogue feed parsed to 0 models from {len(data)} entries")
    return rows


def write_catalog(
    conn, rows: list[dict[str, Any]], *, seen_at: datetime | None = None
) -> dict[str, int]:
    """Upsert every row and stamp `last_seen_at`. A model that leaves the feed
    keeps its row with an older `last_seen_at`, so the page can show only what
    the latest poll listed without the table forgetting what it once held."""
    seen_at = seen_at or datetime.now(UTC)
    added = 0
    for r in rows:
        cur = conn.execute(
            "INSERT INTO model_catalog (canonical_id, provider, name, description, listed_at, "
            " input_modalities, output_modalities, context_length, price_in, price_out, "
            " price_cached_read, pricing, max_output_tokens, supported_parameters, "
            " expiration_date, knowledge_cutoff, last_seen_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (canonical_id) DO UPDATE SET provider = EXCLUDED.provider, "
            " name = EXCLUDED.name, description = EXCLUDED.description, "
            " listed_at = EXCLUDED.listed_at, input_modalities = EXCLUDED.input_modalities, "
            " output_modalities = EXCLUDED.output_modalities, "
            " context_length = EXCLUDED.context_length, price_in = EXCLUDED.price_in, "
            " price_out = EXCLUDED.price_out, price_cached_read = EXCLUDED.price_cached_read, "
            " pricing = EXCLUDED.pricing, max_output_tokens = EXCLUDED.max_output_tokens, "
            " supported_parameters = EXCLUDED.supported_parameters, "
            " expiration_date = EXCLUDED.expiration_date, "
            " knowledge_cutoff = EXCLUDED.knowledge_cutoff, "
            " last_seen_at = EXCLUDED.last_seen_at "
            "RETURNING (xmax = 0)",
            (
                r["canonical_id"],
                r["provider"],
                r["name"],
                r["description"],
                r["listed_at"],
                r["input_modalities"],
                r["output_modalities"],
                r["context_length"],
                r["price_in"],
                r["price_out"],
                r["price_cached_read"],
                Jsonb(r["pricing"]),
                r["max_output_tokens"],
                r["supported_parameters"],
                r["expiration_date"],
                r["knowledge_cutoff"],
                seen_at,
            ),
        ).fetchone()
        added += bool(cur and cur[0])
    return {"listed": len(rows), "added": added, "updated": len(rows) - added}


def poll_catalog(conn, client) -> tuple[dict[str, int], tuple[str, ...]]:
    """GET the whole list and write it: `(counts, "id: columns" not written)`.
    Raises when the feed cannot be read.

    A row with a value its column cannot hold is left out and named rather than
    allowed to overflow the whole write (`openrouter.unstorable`); its existing
    row keeps its old price and an older `last_seen_at`, so the caller must say so.
    """
    from collect.registry.openrouter import unstorable

    response = client.get(CATALOG_URL)
    if response.status_code != 200:
        raise UnreadableFeed(f"HTTP {response.status_code} from {CATALOG_URL}")
    rows, dropped = [], []
    for row in parse_catalog(response.json()):
        columns = unstorable(row)
        if columns:
            dropped.append(f"{row['canonical_id']}: {', '.join(columns)}")
        else:
            rows.append(row)
    return write_catalog(conn, rows), tuple(sorted(dropped))
