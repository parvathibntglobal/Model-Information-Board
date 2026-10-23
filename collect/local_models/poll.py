"""Measure the files the local VRAM tool shows: sizes from the Hub API, and the
architecture from each model's GGUF header. Weekly. See
docs/proposals/can-i-run-it.md.

WHAT IS MEASURED IS WHAT contract/local_models.yaml LISTS, AND NOTHING ELSE.
Each entry names its GGUF repo and the exact files per quantization. This module
never searches a repo for "something that looks like Q4_K_M": a looser match took
a 177B model's speculative-decoding helper (`mtp-...`) for the model while the
list was being seeded. A listed file the repo no longer has is recorded MISSING
and the size stays NULL (rule 6) - never replaced by a look-alike (rule 12).

THE SIZE AND THE HEADER COME FROM THE SAME COMMIT. The API call returns the
repo's commit (`sha`); the header is read from `resolve/<sha>/`, so a repo that
re-uploads between the two calls cannot pair one file's size with another's
architecture.

THE HEADER IS READ BY RANGE, AND A RESPONSE THAT IGNORES THE RANGE IS REFUSED.
Each step asks for `header_read.chunk_bytes` and must come back 206. A 200 would
be the whole file - gigabytes - so the stream is closed unread and the header
recorded as unread. Reading stops at the first step that completes the
key/value section, or at `max_header_bytes`. Tensors are never parsed or stored.

NO CREDENTIAL. The GGUF repos in the list are not gated; a gated vendor repo
would need a token and a licence accepted per model, which is why the list
points at GGUF repos rather than vendor ones.

collect/registry/ may not import adapters (tests/test_lane_boundary.py), so this
is a package of its own rather than a registry module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import yaml
from psycopg.types.json import Jsonb

from collect.config import CONTRACT_DIR, settings
from collect.local_models.gguf import Incomplete, NotGGUF, parse_header

API_URL = "https://huggingface.co/api/models/{repo}"
FILE_URL = "https://huggingface.co/{repo}/resolve/{sha}/{path}"

#: The Hub publishes no anonymous rate limit; `daily_papers` once drew 56 HTTP
#: 429s (collect/adapters/huggingface.py). One request a second, like it.
MIN_INTERVAL = 1.0


class LocalModelsContractError(ValueError):
    """contract/local_models.yaml or local_inference.yaml is missing a key."""


@dataclass(frozen=True)
class LocalModel:
    id: str
    gguf_repo: str
    files: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class ReadSettings:
    quants: tuple[str, ...]
    chunk_bytes: int
    max_header_bytes: int


def load_models(path=None) -> tuple[LocalModel, ...]:
    """The list, validated: every key required, ids unique, every quant listed."""
    settings_ = load_read_settings()
    with open(path or CONTRACT_DIR / "local_models.yaml", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    try:
        models = tuple(
            LocalModel(
                id=str(m["id"]),
                gguf_repo=str(m["gguf_repo"]),
                files={q: tuple(str(f) for f in m["files"][q]) for q in settings_.quants},
            )
            for m in raw["models"]
        )
    except (KeyError, TypeError) as exc:
        raise LocalModelsContractError(
            f"contract/local_models.yaml is missing or malformed at {exc}: every model needs "
            f"an id, a gguf_repo and files for each of {', '.join(settings_.quants)}."
        ) from exc
    ids = [m.id for m in models]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise LocalModelsContractError(f"duplicate ids in local_models.yaml: {duplicates}")
    empty = [f"{m.id} {q}" for m in models for q, files in m.files.items() if not files]
    if empty:
        raise LocalModelsContractError(f"no files listed for: {', '.join(empty)}")
    return models


def load_read_settings(path=None) -> ReadSettings:
    with open(path or CONTRACT_DIR / "local_inference.yaml", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    try:
        out = ReadSettings(
            quants=tuple(str(q) for q in raw["quants"]),
            chunk_bytes=int(raw["header_read"]["chunk_bytes"]),
            max_header_bytes=int(raw["header_read"]["max_header_bytes"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise LocalModelsContractError(
            f"contract/local_inference.yaml is missing or malformed at {exc}: `quants` and "
            "`header_read.chunk_bytes` / `max_header_bytes` are required."
        ) from exc
    if not out.quants or out.chunk_bytes < 1 or out.max_header_bytes < out.chunk_bytes:
        raise LocalModelsContractError(
            "local_inference.yaml: `quants` must be non-empty and "
            "0 < chunk_bytes <= max_header_bytes.")
    return out


def read_header(client, limiter, url: str, read: ReadSettings) -> tuple[dict | None, str | None]:
    """`(fields, None)`, or `(None, why it is unread)`. Ranged steps only."""
    buf = b""
    while len(buf) < read.max_header_bytes:
        start = len(buf)
        end = min(start + read.chunk_bytes, read.max_header_bytes) - 1
        limiter.wait(url)
        with client.stream("GET", url, headers={"Range": f"bytes={start}-{end}"},
                           follow_redirects=True) as response:
            if response.status_code != 206:
                # 200 is the whole file. Close the stream unread.
                return None, f"HTTP {response.status_code} to a ranged request; not read"
            chunk = response.read()
        if not chunk:
            return None, "the file ended inside its header"
        buf += chunk
        try:
            fields, _end = parse_header(buf)
            return fields, None
        except Incomplete:
            continue
        except NotGGUF as exc:
            return None, f"not a readable GGUF header: {exc}"
    return None, f"header longer than {read.max_header_bytes} bytes; not read further"


def measure(client, limiter, store, model: LocalModel, read: ReadSettings) -> list[dict[str, Any]]:
    """One row per quantization. Never raises for a missing file or an unread
    header - those are what the row records."""
    now = datetime.now(UTC)
    base = {"model_id": model.id, "gguf_repo": model.gguf_repo, "measured_at": now,
            "pipeline_version": settings().pipeline_version}
    url = API_URL.format(repo=model.gguf_repo)
    limiter.wait(url)
    response = client.get(url, params={"blobs": "true"})
    if response.status_code != 200:
        why = f"HTTP {response.status_code} from the Hub API"
        return [{**base, "quant": q, "files": list(files), "bytes": None,
                 "missing_files": list(files), "header": None, "header_note": why,
                 "repo_sha": None, "raw_ref": None} for q, files in model.files.items()]
    raw_ref = store.put(response.content).ref
    info = response.json()
    sha = info.get("sha")
    sizes = {s.get("rfilename"): s.get("size") for s in info.get("siblings") or []}

    header, note = None, None
    first = model.files[read.quants[0]][0]
    if not sha:
        note = "the Hub API returned no commit sha; header not read"
    elif sizes.get(first) is None:
        note = f"{first} is not in the repo; header not read"
    else:
        header, note = read_header(
            client, limiter, FILE_URL.format(repo=model.gguf_repo, sha=sha, path=first), read)

    rows = []
    for q, files in model.files.items():
        missing = [f for f in files if not isinstance(sizes.get(f), int)]
        rows.append({**base, "quant": q, "files": list(files),
                     "bytes": None if missing else sum(sizes[f] for f in files),
                     "missing_files": missing, "header": header, "header_note": note,
                     "repo_sha": sha, "raw_ref": raw_ref})
    return rows


UPSERT = """
INSERT INTO local_model_file (model_id, quant, gguf_repo, files, bytes, missing_files,
                              header, header_note, repo_sha, raw_ref, measured_at,
                              pipeline_version)
VALUES (%(model_id)s, %(quant)s, %(gguf_repo)s, %(files)s, %(bytes)s, %(missing_files)s,
        %(header)s, %(header_note)s, %(repo_sha)s, %(raw_ref)s, %(measured_at)s,
        %(pipeline_version)s)
ON CONFLICT (model_id, quant) DO UPDATE SET
  gguf_repo = EXCLUDED.gguf_repo, files = EXCLUDED.files, bytes = EXCLUDED.bytes,
  missing_files = EXCLUDED.missing_files, header = EXCLUDED.header,
  header_note = EXCLUDED.header_note, repo_sha = EXCLUDED.repo_sha,
  raw_ref = EXCLUDED.raw_ref, measured_at = EXCLUDED.measured_at,
  pipeline_version = EXCLUDED.pipeline_version
"""


def write_rows(conn, rows: list[dict[str, Any]]) -> None:
    for row in rows:
        conn.execute(UPSERT, {**row, "header": Jsonb(row["header"]) if row["header"] else None})


def poll_local_models(conn, client, *, store=None, limiter=None, models=None) -> dict[str, int]:
    """Measure every listed model and write its rows. Counts for the run log;
    a model whose files or header could not be read is counted, not dropped
    (rule 4)."""
    from collect.limiter import HostLimiter
    from collect.rawstore import RawStore

    read = load_read_settings()
    store = store or RawStore()
    limiter = limiter or HostLimiter(min_interval=MIN_INTERVAL)
    counts = {"models": 0, "rows": 0, "missing_size": 0, "header_unread": 0}
    for model in models if models is not None else load_models():
        rows = measure(client, limiter, store, model, read)
        write_rows(conn, rows)
        counts["models"] += 1
        counts["rows"] += len(rows)
        counts["missing_size"] += sum(1 for r in rows if r["bytes"] is None)
        counts["header_unread"] += rows[0]["header"] is None
    return counts
