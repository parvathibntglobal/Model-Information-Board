"""Topic recipes: each topic kind's look, and per platform its format and media.

Read from workspace.yaml `looks` and `topic_recipes` (rule 5). `problems()` checks
the table against the seed's platforms, their formats and topic lists, and the
media kinds the workspace stores; the test suite runs it so a recipe naming a
format a platform does not have fails before anyone reads it. `for_block()` is
what a suggestion block shows: a pair with no recipe says so rather than
guessing one (rule 6).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from judge.content_workspace.media import KINDS as MEDIA_KINDS

SPECIAL_LOOKS = ("none", "inherit")
#: The repository root, which a look's `generator` path is relative to.
REPO = Path(__file__).resolve().parents[2]


def problems(settings: dict[str, Any], seed: dict[str, Any]) -> list[str]:
    """Everything wrong with the recipe table, as sentences. Empty when sound."""
    out: list[str] = []
    looks = settings["looks"]
    kinds = settings["topic_kinds"]
    recipes = settings["topic_recipes"]
    platforms = {p["key"]: p for p in seed["platforms"]}

    for name, look in looks.items():
        for field in ("label", "suits", "generator"):
            if not str(look.get(field) or "").strip():
                out.append(f"look {name!r} has no {field}")
        gen = str(look.get("generator") or "").strip()
        if gen and not (REPO / gen).is_file():
            out.append(f"look {name!r}: generator {gen} does not exist")

    for kind, r in recipes.items():
        if kind not in kinds:
            out.append(f"recipe {kind!r} is not a topic kind in workspace.yaml")
        look = r.get("look")
        if look not in looks and look not in SPECIAL_LOOKS:
            out.append(f"{kind}: look {look!r} is none of {sorted(looks)} or {SPECIAL_LOOKS}")
        if look == "none" and not str(r.get("why") or "").strip():
            out.append(f"{kind}: look none needs a why")
        for pkey, rec in (r.get("platforms") or {}).items():
            p = platforms.get(pkey)
            if p is None:
                out.append(f"{kind}: platform {pkey!r} is not in the seed")
                continue
            if kind not in p["topics"]:
                out.append(f"{kind}: {pkey} has a recipe but does not list this topic kind")
            if rec.get("format") not in p["formats"]:
                out.append(f"{kind}: {pkey} format {rec.get('format')!r} is not one of "
                           f"{p['formats']}")
            media = rec.get("media")
            if not isinstance(media, list):
                out.append(f"{kind}: {pkey} media must be a list (empty for text only)")
                continue
            for m in media:
                if m not in MEDIA_KINDS:
                    out.append(f"{kind}: {pkey} media {m!r} is not one of {MEDIA_KINDS}")
            if media and look == "none":
                out.append(f"{kind}: {pkey} makes media but the kind's look is none")

    for pkey, p in platforms.items():
        for kind in p["topics"]:
            if pkey not in ((recipes.get(kind) or {}).get("platforms") or {}):
                out.append(f"{pkey} lists {kind!r} but there is no recipe for it")
    return out + pain_problems(settings)


def pain_problems(settings: dict[str, Any]) -> list[str]:
    """workspace.yaml `pain_angles` and `pain_not_counted`, as sentences."""
    out: list[str] = []
    sections = set(settings["capability_split"]["sections"])
    seen: set[str] = set()
    for i, a in enumerate(settings["pain_angles"]):
        key = a.get("key")
        where = f"pain_angles[{i}] {key!r}"
        if not key or key in seen:
            out.append(f"{where}: a key is required and unique")
        seen.add(key)
        for field in ("label", "says"):
            if not str(a.get(field) or "").strip():
                out.append(f"{where}: no {field}")
        if a.get("fit") not in ("well", "partly"):
            out.append(f"{where}: fit is well or partly, not {a.get('fit')!r}")
        slugs = a.get("slugs")
        if not isinstance(slugs, list) or not slugs:
            out.append(f"{where}: slugs must be a non-empty list")
            continue
        for s in slugs:
            section, _, slug = str(s).partition(":")
            if section not in sections or not slug:
                out.append(f"{where}: {s!r} is not section:slug with a section in "
                           f"capability_split.sections {sorted(sections)}")
    nc = settings["pain_not_counted"]
    if not isinstance(nc, list) or not all(str(x).strip() for x in nc):
        out.append("pain_not_counted must be a list of names")
    return out


def for_block(settings: dict[str, Any], platform_key: str, kind: str) -> dict[str, Any]:
    """The look and this platform's recipe for one topic kind, for the page."""
    r = settings["topic_recipes"].get(kind)
    rec = ((r or {}).get("platforms") or {}).get(platform_key)
    if r is None or rec is None:
        # `no_recipe`, not `missing`: tests/test_an_emitted_field_has_a_reader.py
        # matches fields by NAME, and `missing` is /compare's, declared unread.
        return {"no_recipe": True,
                "note": "No recipe yet for this topic on this platform "
                        "(workspace.yaml topic_recipes)."}
    look = r["look"]
    out: dict[str, Any] = {"no_recipe": False, "format": rec["format"],
                           "media": list(rec["media"])}
    if look in settings["looks"]:
        out["look"] = {"key": look, "label": settings["looks"][look]["label"],
                       "suits": " ".join(settings["looks"][look]["suits"].split())}
    elif look == "inherit":
        out["look"] = {"key": "inherit", "label": "The source draft's look"}
    else:
        out["look"] = {"key": "none", "label": "Text only", "suits": r["why"]}
    return out
