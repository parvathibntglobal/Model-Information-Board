"""GET /local-models: what the local VRAM tool ("Can I run it?") needs.

docs/proposals/can-i-run-it.md. Per model: the measured GGUF file size per
quantization (the figure the page shows, rule 3), the repo and commit it was
measured at, the KV-cache shape read from the file's header, and the API price
where OpenRouter lists the model. Plus the hardware list and every constant the
page's arithmetic uses, from contract/ (rule 5) - the page computes the
estimate in the browser so changing hardware is instant, and has no constant of
its own.

THE CACHE IS RETURNED AS A SHAPE, NOT A SIZE. A model's cache grows with the
context a reader picks, so this returns elements per token - for the layers
that cache every token (`full_elements`), and per sliding window for the ones
that cache only the last N (`windowed`). The page multiplies by bytes per
element and by tokens.

WHAT THE HEADER STATES IS USED EXACTLY; WHAT IT DOES NOT IS AN UPPER BOUND.
`basis` says which, and `why` says what was not modelled:
    exact        every caching layer and its head size are stated
    upper_bound  sliding-window layers with no stated pattern, latent attention,
                 or state-space layers the header does not place - computed as
                 full attention, which can only make a model look bigger
    unknown      the header was not read, or lacks a field the arithmetic
                 needs; the page says "context memory unknown" (rule 6)
Head size, where the header omits `key_length`, is embedding length / head
count - llama.cpp's own rule when it loads that file, so it is what the file
will actually cost. A file whose header is wrong is replaced in
contract/local_models.yaml, never corrected here.

NOT MODELLED, AND SMALL: a state-space layer's recurrent state is a fixed few
megabytes per layer, not per token; the runtime overhead absorbs it.
"""

from __future__ import annotations

from typing import Any

from judge.config import _read


class LocalModelsContractError(ValueError):
    """A local_* contract file is missing a key the tool needs."""


def inference_settings() -> dict[str, Any]:
    """contract/local_inference.yaml, validated. Every key required."""
    raw = _read("local_inference.yaml") or {}
    try:
        out = {
            "quants": [str(q) for q in raw["quants"]],
            "contexts": [int(c) for c in raw["contexts"]],
            "kv_cache_bytes": {str(k): float(v) for k, v in raw["kv_cache_bytes"].items()},
            "runtime_overhead_gib": float(raw["runtime_overhead_gib"]),
            "overhead_per_card": bool(raw["overhead_per_card"]),
            "apple_gpu_share": float(raw["apple_gpu_share"]),
            "fits_at_most": float(raw["bands"]["fits_at_most"]),
        }
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise LocalModelsContractError(
            f"contract/local_inference.yaml is missing or malformed at {exc}. Every constant "
            "is required; a defaulted one would tell a reader a model fits on a number "
            "nobody chose.") from exc
    if not out["quants"] or not out["contexts"] or not out["kv_cache_bytes"]:
        raise LocalModelsContractError("local_inference.yaml: quants, contexts and "
                                       "kv_cache_bytes must each be non-empty.")
    if not 0 < out["apple_gpu_share"] <= 1 or not 0 < out["fits_at_most"] <= 1:
        raise LocalModelsContractError("local_inference.yaml: apple_gpu_share and "
                                       "bands.fits_at_most must be in (0, 1].")
    if out["runtime_overhead_gib"] < 0:
        raise LocalModelsContractError("local_inference.yaml: runtime_overhead_gib < 0.")
    return out


def hardware() -> list[dict[str, Any]]:
    """contract/local_hardware.yaml, validated, grouped in the sources' order."""
    raw = _read("local_hardware.yaml") or {}
    try:
        sources = {str(k): {"label": str(v["label"]), "url": str(v["url"])}
                   for k, v in raw["sources"].items()}
        order = list(sources)
        devices = [{"id": str(d["id"]), "name": str(d["name"]), "kind": str(d["kind"]),
                    "memory_gib": float(d["memory_gib"]),
                    "group": sources[str(d["source"])]["label"],
                    "source": sources[str(d["source"])]["url"],
                    "_order": order.index(str(d["source"]))}
                   for d in raw["devices"]]
        devices.sort(key=lambda d: d.pop("_order"))
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise LocalModelsContractError(
            f"contract/local_hardware.yaml is missing or malformed at {exc}.") from exc
    bad = [d["id"] for d in devices if d["kind"] not in ("discrete", "unified")
           or d["memory_gib"] <= 0]
    ids = [d["id"] for d in devices]
    if bad or len(set(ids)) != len(ids):
        raise LocalModelsContractError(
            f"local_hardware.yaml: bad kind/memory {bad}, or duplicate ids.")
    return devices


def listed_models() -> list[dict[str, Any]]:
    """contract/local_models.yaml's entries, in file order."""
    raw = _read("local_models.yaml") or {}
    try:
        return [{"id": str(m["id"]), "name": str(m["name"]), "family": str(m["family"]),
                 "original": m["original"], "openrouter": m["openrouter"],
                 "gguf_repo": str(m["gguf_repo"])} for m in raw["models"]]
    except (KeyError, TypeError) as exc:
        raise LocalModelsContractError(
            f"contract/local_models.yaml is missing or malformed at {exc}.") from exc


def _per_layer(value: Any, layers: int) -> list | None:
    if isinstance(value, list):
        return value if len(value) == layers else None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [value] * layers
    return None


def cache_shape(header: dict | None) -> dict[str, Any]:
    """The KV cache's elements per token, from a GGUF header (module docstring)."""
    unknown = {"basis": "unknown", "why": None, "full_elements": None, "windowed": [],
               "max_context": None}
    if not header:
        return {**unknown, "why": "the file's header was not read"}
    layers = header.get("block_count")
    max_context = header.get("context_length")
    max_context = max_context if isinstance(max_context, int) and max_context > 0 else None
    if not isinstance(layers, int) or layers < 1:
        return {**unknown, "why": "the header states no layer count", "max_context": max_context}
    kv_heads = _per_layer(header.get("attention.head_count_kv"), layers)
    heads = _per_layer(header.get("attention.head_count"), layers)
    embedding = header.get("embedding_length")
    if kv_heads is None:
        return {**unknown, "why": "the header states no KV-head count", "max_context": max_context}

    def length(key: str, i: int) -> int | None:
        stated = header.get(key)
        if isinstance(stated, int) and stated > 0:
            return stated
        if isinstance(embedding, int) and heads and heads[i]:
            return embedding // int(heads[i])  # llama.cpp's rule for an unstated head size
        return None

    reasons: list[str] = []
    window = header.get("attention.sliding_window")
    windowed_active = (isinstance(window, int) and window > 0
                       and (max_context is None or window < max_context))
    pattern = _per_layer(header.get("attention.sliding_window_pattern"), layers)
    if windowed_active and pattern is None:
        reasons.append("sliding-window layers whose pattern the header does not state")
        windowed_active = False
    if header.get("attention.kv_lora_rank"):
        reasons.append("latent attention")
    interval = header.get("full_attention_interval")
    interval = interval if isinstance(interval, int) and interval > 0 else None
    has_ssm = any(k.startswith("ssm.") for k in header)
    if has_ssm and interval is None and not isinstance(header.get("attention.head_count_kv"), list):
        reasons.append("state-space layers the header does not place")
    shared = header.get("attention.shared_kv_layers")
    sharing = isinstance(shared, int) and 0 < shared < layers
    own_cache_layers = layers - shared if sharing else layers

    full, windowed = 0, 0
    for i in range(layers):
        if i >= own_cache_layers or not kv_heads[i]:
            continue
        if interval is not None and (i + 1) % interval != 0:
            continue  # a state-space layer: llama.cpp caches only every interval-th layer
        is_windowed = bool(windowed_active and pattern[i])
        k = length("attention.key_length_swa" if is_windowed else "attention.key_length", i)
        if is_windowed and k is None:
            k = length("attention.key_length", i)
        v = header.get("attention.value_length_swa" if is_windowed else "attention.value_length")
        v = v if isinstance(v, int) and v > 0 else k
        if k is None:
            return {**unknown, "why": "the header states no head size", "max_context": max_context}
        elements = int(kv_heads[i]) * (k + v)
        if is_windowed:
            windowed += elements
        else:
            full += elements
    return {
        "basis": "upper_bound" if reasons else "exact",
        "why": "; ".join(reasons) or None,
        "full_elements": full,
        "windowed": [{"window": window, "elements": windowed}] if windowed else [],
        "max_context": max_context,
    }


ROWS_SQL = """
SELECT model_id, quant, gguf_repo, files, bytes, missing_files, header, header_note,
       repo_sha, measured_at
  FROM local_model_file
 WHERE model_id = ANY(%s)
"""

PRICES_SQL = """
SELECT canonical_id, price_in, price_out FROM model_catalog WHERE canonical_id = ANY(%s)
"""


def _price(value) -> float | None:
    return float(value) if value is not None else None


def local_models_view(conn) -> dict[str, Any]:
    """The tool's whole payload. A listed model with no measurement yet is
    listed under `not_measured`, never left out (rule 4)."""
    constants = inference_settings()
    listed = listed_models()
    rows = conn.execute(ROWS_SQL, ([m["id"] for m in listed],)).fetchall()
    by_model: dict[str, dict[str, tuple]] = {}
    for r in rows:
        by_model.setdefault(r[0], {})[r[1]] = r
    catalog = {r[0]: r for r in conn.execute(
        PRICES_SQL, ([m["openrouter"] for m in listed if m["openrouter"]],)).fetchall()}

    models, not_measured = [], []
    for m in listed:
        measured = by_model.get(m["id"])
        if not measured:
            not_measured.append(m["id"])
            continue
        first = measured.get(constants["quants"][0]) or next(iter(measured.values()))
        header, header_note = first[6], first[7]
        shape = cache_shape(header)
        if header is None and header_note:
            shape["why"] = header_note
        listed_on_catalog = catalog.get(m["openrouter"]) if m["openrouter"] else None
        models.append({
            **m,
            "architecture": (header or {}).get("architecture"),
            "on_catalog": listed_on_catalog is not None,
            "price_in": _price(listed_on_catalog[1]) if listed_on_catalog else None,
            "price_out": _price(listed_on_catalog[2]) if listed_on_catalog else None,
            "quants": {
                q: {"bytes": r[4], "files": list(r[3]), "missing_files": list(r[5]),
                    "repo_sha": r[8], "measured_at": r[9].isoformat()}
                for q, r in measured.items() if q in constants["quants"]
            },
            "cache": shape,
        })
    newest = max((q["measured_at"] for m in models for q in m["quants"].values()), default=None)
    return {
        "constants": constants,
        "hardware": hardware(),
        "models": models,
        "not_measured": not_measured,
        "measured_at": newest,
    }
