"""GET /local-models: what the local VRAM tool ("Can I run it?") needs.

docs/proposals/can-i-run-it.md. Per model: the measured GGUF file size per
quantization (the ONE figure the page shows, rule 3), the repo and commit it was
measured at, the memory shape read from the file's header, and the API price
where OpenRouter lists the model. Plus the hardware list and the constants the
page's grouping uses, from contract/ (rule 5). The page groups in the browser
so changing hardware is instant, and shows no computed number.

THE CACHE IS RETURNED AS A SHAPE, NOT A SIZE. A model's cache grows with the
context a reader picks, so this returns elements per token - for the layers
that cache every token (`full_elements`), and per sliding window for the ones
that cache only the last N (`windowed`) - plus `fixed_bytes`, the recurrent
state of state-space layers, which does not grow. The page multiplies by bytes
per element and by tokens.

WHAT THE HEADER STATES IS USED EXACTLY; WHAT IT DOES NOT IS AN UPPER BOUND OR
UNKNOWN. `basis` says which, and `why` says what was not modelled:
    exact        every caching layer, its head size and every state-space layer
                 are stated
    upper_bound  a sliding window with no stated pattern, latent attention, an
                 architecture whose attention llama.cpp sets in code
                 (local_inference.yaml `attention_not_in_header`), or
                 state-space layers the header does not place - computed so the
                 figure can only be too big, never too small
    unknown      the header was not read, lacks a field the arithmetic needs,
                 has attention the arithmetic does not model at all, or states a
                 head size its own key projection contradicts; the page says
                 "can't tell" (rule 6)
Head size, where the header omits `key_length`, is embedding length / head
count - llama.cpp's own rule when it loads that file. It is then CHECKED against
the file's own key projection (`tensor.attn_k` / `tensor.attn_qkv`, read from
the tensor list by collect/local_models/gguf.py): unsloth's Mistral Nemo states
160 by that rule and its key projection says 128, and is "unknown" rather than
wrong (rule 12). A file whose header is wrong is replaced in
contract/local_models.yaml, never corrected here.
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
            "recurrent_state_bytes": float(raw["recurrent_state_bytes"]),
            "runtime_overhead_gib": float(raw["runtime_overhead_gib"]),
            "overhead_per_card": bool(raw["overhead_per_card"]),
            "apple_gpu_share": sorted(
                ({"from_gib": float(r["from_gib"]), "share": float(r["share"]),
                  "evidence": str(r["evidence"])} for r in raw["apple_gpu_share"]),
                key=lambda r: r["from_gib"]),
            "fits_at_most": float(raw["bands"]["fits_at_most"]),
            "attention_not_in_header": {str(k): str(v)
                                        for k, v in raw["attention_not_in_header"].items()},
            "unmodelled_attention_keys": [str(k) for k in raw["unmodelled_attention_keys"]],
        }
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise LocalModelsContractError(
            f"contract/local_inference.yaml is missing or malformed at {exc}. Every constant "
            "is required; a defaulted one would tell a reader a model fits on a number "
            "nobody chose.") from exc
    if not out["quants"] or not out["contexts"] or not out["kv_cache_bytes"]:
        raise LocalModelsContractError("local_inference.yaml: quants, contexts and "
                                       "kv_cache_bytes must each be non-empty.")
    shares = out["apple_gpu_share"]
    if not shares or shares[0]["from_gib"] != 0 or any(not 0 < r["share"] <= 1 for r in shares):
        raise LocalModelsContractError(
            "local_inference.yaml: apple_gpu_share needs a row from 0 GiB, and every share "
            "in (0, 1] - a Mac smaller than the first row would otherwise have no share.")
    if not 0 < out["fits_at_most"] <= 1:
        raise LocalModelsContractError(
            "local_inference.yaml: bands.fits_at_most must be in (0, 1].")
    if out["runtime_overhead_gib"] < 0 or out["recurrent_state_bytes"] <= 0:
        raise LocalModelsContractError(
            "local_inference.yaml: runtime_overhead_gib >= 0 and recurrent_state_bytes > 0.")
    return out


def gpu_share(memory_gib: float, table: list[dict]) -> float:
    """The row with the largest `from_gib` at or below this Mac's memory."""
    return [r for r in table if r["from_gib"] <= memory_gib][-1]["share"]


def hardware(settings: dict | None = None) -> list[dict[str, Any]]:
    """contract/local_hardware.yaml, validated, in the groups' order. A Mac
    carries its own GPU share from the memory-size table."""
    settings = settings or inference_settings()
    raw = _read("local_hardware.yaml") or {}
    try:
        groups = [(str(g["id"]), str(g["label"])) for g in raw["groups"]]
        sources = {str(k): str(v) for k, v in raw["sources"].items()}
        labels = dict(groups)
        order = [g for g, _ in groups]
        devices = [{"id": str(d["id"]), "name": str(d["name"]), "kind": str(d["kind"]),
                    "memory_gib": float(d["memory_gib"]), "group": labels[str(d["group"])],
                    "source": sources[str(d["source"])], "checked": d["checked"],
                    "_order": order.index(str(d["group"]))}
                   for d in raw["devices"]]
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise LocalModelsContractError(
            f"contract/local_hardware.yaml is missing or malformed at {exc}.") from exc
    # `checked` is required and must be a real boolean: a device whose figure
    # nobody has found on its page must say so, never default to checked.
    bad = [d["id"] for d in devices if d["kind"] not in ("discrete", "unified")
           or d["memory_gib"] <= 0 or not isinstance(d["checked"], bool)]
    ids = [d["id"] for d in devices]
    if bad or len(set(ids)) != len(ids):
        raise LocalModelsContractError(
            f"local_hardware.yaml: bad kind, memory or checked flag {bad}, or duplicate ids.")
    devices.sort(key=lambda d: d.pop("_order"))
    for d in devices:
        if d["kind"] == "unified":
            d["gpu_share"] = gpu_share(d["memory_gib"], settings["apple_gpu_share"])
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


def _positive(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def _unknown(why: str, max_context: int | None = None) -> dict[str, Any]:
    return {"basis": "unknown", "why": why, "full_elements": None, "windowed": [],
            "fixed_bytes": None, "max_context": max_context}


def cache_shape(header: dict | None, settings: dict) -> dict[str, Any]:
    """The memory a model needs beyond its file, from a GGUF header (module docstring)."""
    if not header:
        return _unknown("the file's header was not read")
    max_context = _positive(header.get("context_length"))
    layers = _positive(header.get("block_count"))
    if layers is None:
        return _unknown("the header states no layer count", max_context)
    for prefix in settings["unmodelled_attention_keys"]:
        if any(k == prefix or k.startswith(prefix + ".") for k in header):
            return _unknown(f"attention this calculator does not model ({prefix})", max_context)
    kv_heads = _per_layer(header.get("attention.head_count_kv"), layers)
    heads = _per_layer(header.get("attention.head_count"), layers)
    embedding = _positive(header.get("embedding_length"))
    if kv_heads is None:
        return _unknown("the header states no KV-head count", max_context)

    reasons: list[str] = []
    window = _positive(header.get("attention.sliding_window"))
    windowed_active = window is not None and (max_context is None or window < max_context)
    pattern = _per_layer(header.get("attention.sliding_window_pattern"), layers)
    if windowed_active and pattern is None:
        reasons.append("sliding-window layers whose pattern the header does not state")
        windowed_active = False
    latent = bool(header.get("attention.kv_lora_rank"))
    if latent:
        reasons.append("latent attention")
    hard_coded = settings["attention_not_in_header"].get(str(header.get("architecture")))
    if hard_coded:
        reasons.append(hard_coded)

    def length(key: str, i: int) -> int | None:
        stated = _positive(header.get(key))
        if stated:
            return stated
        if embedding and heads and heads[i]:
            return embedding // int(heads[i])  # llama.cpp's rule for an unstated head size
        return None

    def key_length(i: int, windowed: bool) -> int | None:
        swa = _positive(header.get("attention.key_length_swa"))
        return swa if windowed and swa else length("attention.key_length", i)

    # Which layers keep a cache, and which hold a recurrent state instead.
    interval = _positive(header.get("full_attention_interval"))
    feed_forward = _per_layer(header.get("feed_forward_length"), layers)
    shared = header.get("attention.shared_kv_layers")
    own_cache = layers - shared if isinstance(shared, int) and 0 < shared < layers else layers
    has_ssm = any(k.startswith("ssm.") for k in header)
    recurrent: list[int] = []
    caching: list[int] = []
    for i in range(layers):
        if interval is not None:
            (caching if (i + 1) % interval == 0 else recurrent).append(i)
        elif kv_heads[i]:
            caching.append(i)
        elif has_ssm and isinstance(header.get("attention.head_count_kv"), list):
            # llama.cpp's own test: no KV heads AND no feed-forward = state-space.
            if feed_forward is not None and not feed_forward[i]:
                recurrent.append(i)
            elif feed_forward is None:
                recurrent.append(i)  # cannot tell it from a feed-forward layer: count it
    if has_ssm and interval is None and not isinstance(header.get("attention.head_count_kv"), list):
        reasons.append("state-space layers the header does not place")
        recurrent = [i for i in range(layers)]  # every layer, so the state is a bound
    if (has_ssm and interval is None and feed_forward is None
            and isinstance(header.get("attention.head_count_kv"), list)):
        reasons.append("state-space layers the header cannot tell from feed-forward ones")

    full, windowed_elements = 0, 0
    for i in caching:
        if i >= own_cache:
            continue  # reuses an earlier layer's cache (shared_kv_layers)
        is_windowed = bool(windowed_active and pattern[i])
        k = key_length(i, is_windowed)
        v_key = "attention.value_length_swa" if is_windowed else "attention.value_length"
        v = _positive(header.get(v_key)) or k
        if k is None:
            return _unknown("the header states no head size", max_context)
        elements = int(kv_heads[i]) * (k + v)
        if is_windowed:
            windowed_elements += elements
        else:
            full += elements

    contradiction = None if latent else _head_size_contradiction(
        header, kv_heads, heads, caching, windowed_active, pattern, key_length)
    if contradiction:
        return _unknown(contradiction, max_context)

    fixed = 0.0
    if recurrent:
        conv = _positive(header.get("ssm.conv_kernel"))
        inner = _positive(header.get("ssm.inner_size"))
        state = _positive(header.get("ssm.state_size"))
        groups = _positive(header.get("ssm.group_count")) or 1
        if not (conv and inner and state):
            return _unknown("state-space layers whose size the header does not state",
                            max_context)
        per_layer = (conv - 1) * (inner + 2 * groups * state) + state * inner
        fixed = per_layer * len(recurrent) * settings["recurrent_state_bytes"]
    return {
        "basis": "upper_bound" if reasons else "exact",
        "why": "; ".join(dict.fromkeys(reasons)) or None,
        "full_elements": full,
        "windowed": [{"window": window, "elements": windowed_elements}]
        if windowed_elements else [],
        "fixed_bytes": fixed,
        "max_context": max_context,
    }


def _head_size_contradiction(header, kv_heads, heads, caching, windowed_active, pattern,
                             key_length) -> str | None:
    """The header's head size against the file's own key projection (rule 12)."""
    for kind in ("tensor.attn_k", "tensor.attn_qkv"):
        found = header.get(kind)
        if not isinstance(found, dict) or not isinstance(found.get("shape"), list):
            continue
        i, shape = found.get("layer"), found["shape"]
        if not isinstance(i, int) or i not in caching or len(shape) < 2 or not kv_heads[i]:
            continue
        stated = key_length(i, bool(windowed_active and pattern[i]))
        if stated is None:
            return None
        if kind == "tensor.attn_k":
            actual, per = shape[1] / kv_heads[i], "per KV head"
        else:
            if not heads or not heads[i]:
                continue
            actual, per = shape[1] / (heads[i] + 2 * kv_heads[i]), "per head"
        if actual != stated:
            return (f"the header implies a head size of {stated}, but the file's own key "
                    f"projection is {actual:g} {per}")
        return None
    return None


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
    settings = inference_settings()
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
        first = measured.get(settings["quants"][0]) or next(iter(measured.values()))
        header, header_note = first[6], first[7]
        shape = cache_shape(header, settings)
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
                for q, r in measured.items() if q in settings["quants"]
            },
            "cache": shape,
        })
    newest = max((q["measured_at"] for m in models for q in m["quants"].values()), default=None)
    constants = {k: settings[k] for k in ("quants", "contexts", "kv_cache_bytes",
                                          "runtime_overhead_gib", "overhead_per_card",
                                          "fits_at_most")}
    return {
        "constants": constants,
        "hardware": hardware(settings),
        "models": models,
        "not_measured": not_measured,
        "measured_at": newest,
    }
