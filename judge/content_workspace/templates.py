"""Phase 3: fill a platform/format template from a draft's suggestion.

Coded, no model (YouTube and Instagram allow no AI writer). Every figure in
the result comes from the suggestion through a placeholder; the template text
states none. The person edits the result before saving it.
"""

from __future__ import annotations

import os
import re
import string
from pathlib import Path
from typing import Any

import yaml

from judge.content_workspace import store
from judge.content_workspace.settings import HERE

TEMPLATES = HERE / "templates.yaml"
PLACEHOLDERS = {"headline", "detail", "date", "price", "model_page", "evidence", "proof", "topic"}
FIELDS = ("title", "body", "first_comment")


def load(path: Path | None = None) -> dict[str, Any]:
    data = yaml.safe_load((path or TEMPLATES).read_text(encoding="utf-8"))
    for platform, formats in data.items():
        for fmt, t in formats.items():
            for field in FIELDS:
                names = {n for _, n, _, _ in string.Formatter().parse(t.get(field) or "") if n}
                unknown = names - PLACEHOLDERS
                if unknown:
                    raise ValueError(f"templates.yaml {platform}/{fmt}/{field}: unknown "
                                     f"placeholder(s) {', '.join(sorted(unknown))}")
    return data


def available(platform_key: str, data: dict[str, Any] | None = None) -> list[str]:
    data = data if data is not None else load()
    return sorted((data.get(platform_key) or {}).keys())


def _values(d: dict[str, Any], s: dict[str, Any]) -> dict[str, str]:
    sug = d.get("suggestion") or {}

    def missing(name: str) -> str:
        return f"[no {name} in this suggestion]"

    page = next((link["path"] for link in sug.get("links") or [] if link.get("path")), None)
    if page:
        base = (os.environ.get(s["site"]["hosts_env"]) or "").strip().rstrip("/")
        page = f"{base}{page}"
    kind = s["topic_kinds"].get(d.get("topic_kind") or "", {})
    proof = [f"- {p.get('period')}, {p.get('platform') or 'source'}: {p['text']}"
             for p in sug.get("proof") or []]
    price = sug.get("price")
    return {
        "headline": sug.get("headline") or missing("headline"),
        "detail": sug.get("detail") or missing("detail"),
        "date": sug.get("date") or missing("date"),
        "price": (price + ".") if price and not price.endswith(".") else (price or
                                                                          missing("price")),
        "model_page": page or missing("model page"),
        "evidence": "\n".join(f"- {e}" for e in sug.get("evidence") or []) or missing("evidence"),
        "proof": "\n".join(proof) or missing("paraphrased report"),
        "topic": kind.get("label") or missing("topic"),
    }


def fill(d: dict[str, Any], p: dict[str, Any], s: dict[str, Any],
         data: dict[str, Any] | None = None) -> dict[str, Any]:
    """The template for the draft's platform and format, filled. Raises when
    the platform/format has no template."""
    data = data if data is not None else load()
    t = (data.get(p["key"]) or {}).get(d["format"])
    if t is None:
        raise store.WorkspaceRequestError(
            f"no template for {p['name']} {d['format']} (config/templates.yaml)", 404)
    values = _values(d, s)
    out = {f: (t.get(f) or "").format(**values) or None for f in FIELDS}
    out["unfilled"] = sorted(set(re.findall(r"\[no ([a-z ]+) in this suggestion\]",
                                            " ".join(v or "" for v in out.values()))))
    out["to_write"] = len(re.findall(r"\[(?!no )[^\]]+\]", out["body"] or ""))
    return out
