"""The AI glossary (2026-10-20): a short definition of each concept, one
paragraph, for `/glossary` and `/glossary/<slug>`.

The terms and their paragraphs live in `glossary.yaml`, written by Claude Code
and reviewed like any copy; this module reads the file, checks every entry,
and answers the two pages. The checks are the ones a reader would notice
broken - a definition that runs to a blog post, a sentence nobody can finish,
a related link to a term that does not exist - and they run on load, so a
broken file is refused with its reasons rather than half-served (rule 12).

A DEFINITION STATES WHAT A THING IS, AND NO FIGURE ABOUT HOW WELL IT WORKS.
No percentage, no "3x faster", no benchmark score: a number on this page
would be a claim with no denominator beside it (rules 3 and 7). How a
technique fares in practice is what the board and the blog report, with their
sources, and a term page links there.

The sentence limits are the newsroom's (blog_rules.yaml `limits`), so the
glossary and the blog read alike.

No model is called here (rule 2).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "glossary.yaml"
NEWSROOM = ROOT / "blog_rules.yaml"

#: The groups the index filters by, in the order it shows them.
CATEGORIES = {
    "foundations": "Foundations",
    "prompting": "Prompting and context",
    "reasoning": "Reasoning",
    "decisions": "Decision models",
    "decoding": "Decoding and sampling",
    "retrieval": "Retrieval and RAG",
    "training": "Training and tuning",
    "inference": "Inference and serving",
    "agents": "Agents and tools",
    "evaluation": "Evaluation",
    "safety": "Safety and security",
    "deployment": "Running models locally",
    "web": "AI and the web",
}
SENTENCES = (6, 10)
TEASER_MAX_CHARS = 160
RELATED = (2, 5)
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
#: A figure about performance: a percentage, a multiple ("3x", "10 times").
PERFORMANCE_FIGURE = re.compile(r"\d\s*%|\b\d+(?:\.\d+)?\s*[x×]\b|\b\d+(?:\.\d+)?\s+times\b", re.I)


class GlossaryError(ValueError):
    """glossary.yaml has an entry that would render wrong; every reason is listed."""


def _limits() -> dict[str, int]:
    raw = yaml.safe_load(NEWSROOM.read_text(encoding="utf-8")) or {}
    lim = raw.get("limits") or {}
    missing = {"sentence_average_words", "sentence_max_words"} - set(lim)
    if missing:
        raise GlossaryError(f"blog_rules.yaml limits missing: {', '.join(sorted(missing))}")
    return {k: int(lim[k]) for k in ("sentence_average_words", "sentence_max_words")}


def sentences(text: str) -> list[str]:
    """Split on a full stop, question or exclamation mark followed by a space
    and a capital or digit - so "e.g. a" and "v1.5" stay inside a sentence."""
    t = " ".join(str(text or "").split())
    t = re.sub(r"\b(e\.g|i\.e|vs|etc)\.", lambda m: m.group(0).replace(".", "․"), t)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", t)
    return [p.replace("․", ".") for p in parts if p.strip()]


def words(sentence: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’.\-/+]*", sentence)


def problems(entries: list[dict], known: set[str] | None = None,
             limits: dict[str, int] | None = None) -> list[str]:
    """Every reason an entry would render wrong. `known` is the slug set
    related terms may point at (the whole file's, by default)."""
    lim = limits or _limits()
    out: list[str] = []
    seen: dict[str, str] = {}
    slugs = {str(e.get("slug")) for e in entries if isinstance(e, dict)}
    known = known if known is not None else slugs
    names: dict[str, str] = {}
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            out.append(f"[{i}] is not a mapping")
            continue
        slug = str(e.get("slug") or "")
        at = f"{slug or f'[{i}]'}"
        if not SLUG.match(slug):
            out.append(f"{at}: slug must be lowercase words joined by hyphens")
        if slug in seen:
            out.append(f"{at}: slug used twice")
        seen[slug] = at
        term = str(e.get("term") or "").strip()
        if not term:
            out.append(f"{at}: no term")
        aka = e.get("aka") or []
        if not isinstance(aka, list) or not all(isinstance(a, str) and a.strip() for a in aka):
            out.append(f"{at}: aka must be a list of names")
            aka = []
        for name in [term, *aka]:
            k = name.strip().lower()
            if k and k in names and names[k] != slug:
                out.append(f"{at}: the name {name!r} is also {names[k]!r}'s")
            names.setdefault(k, slug)
        if e.get("category") not in CATEGORIES:
            out.append(f"{at}: category {e.get('category')!r} is not one of "
                       f"{', '.join(CATEGORIES)}")
        teaser = " ".join(str(e.get("teaser") or "").split())
        if not teaser or len(sentences(teaser)) != 1 or not teaser.endswith("."):
            out.append(f"{at}: teaser must be one sentence ending in a full stop")
        if len(teaser) > TEASER_MAX_CHARS:
            out.append(f"{at}: teaser is {len(teaser)} characters; at most {TEASER_MAX_CHARS}")
        d = " ".join(str(e.get("definition") or "").split())
        ss = sentences(d)
        if not SENTENCES[0] <= len(ss) <= SENTENCES[1]:
            out.append(f"{at}: definition has {len(ss)} sentences; "
                       f"{SENTENCES[0]} to {SENTENCES[1]}")
        if ss and not any(n.lower() in ss[0].lower() for n in [term, *aka] if n):
            out.append(f"{at}: the first sentence must name the term "
                       "(it is the answer a search shows)")
        for s in ss:
            if len(words(s)) > lim["sentence_max_words"]:
                out.append(f"{at}: a {len(words(s))}-word sentence (at most "
                           f"{lim['sentence_max_words']}): {s[:90]!r}")
        if ss:
            avg = sum(len(words(s)) for s in ss) / len(ss)
            if avg > lim["sentence_average_words"]:
                out.append(f"{at}: sentences average {avg:.1f} words; at most "
                           f"{lim['sentence_average_words']}")
        for field, text in (("teaser", teaser), ("definition", d)):
            if m := PERFORMANCE_FIGURE.search(text):
                out.append(f"{at}: {field} carries a performance figure ({m.group(0)!r}); "
                           "a definition says what a thing is, and the board reports how it fares")
            if any(c in text for c in "«»\"“”"):
                out.append(f"{at}: {field} quotes something; write it in your own words")
        rel = e.get("related") or []
        if not isinstance(rel, list) or not RELATED[0] <= len(rel) <= RELATED[1]:
            out.append(f"{at}: related must list {RELATED[0]} to {RELATED[1]} terms")
            rel = rel if isinstance(rel, list) else []
        for r in rel:
            if r == slug:
                out.append(f"{at}: related lists itself")
            elif r not in known:
                out.append(f"{at}: related term {r!r} is not in the glossary")
        if len(set(rel)) != len(rel):
            out.append(f"{at}: related lists a term twice")
    return out


def load(path: Path | None = None) -> list[dict]:
    """Every entry, checked. Raises GlossaryError naming every problem."""
    path = path or PATH
    if not path.exists():
        raise GlossaryError(f"{path.name} is missing")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = raw.get("terms") or []
    bad = problems(entries)
    if bad:
        raise GlossaryError(f"{path.name}: {len(bad)} problem(s):\n- " + "\n- ".join(bad))
    for e in entries:
        e["teaser"] = " ".join(e["teaser"].split())
        e["definition"] = " ".join(e["definition"].split())
        e["aka"] = e.get("aka") or []
    return sorted(entries, key=lambda e: e["term"].lower())


def _card(e: dict) -> dict[str, Any]:
    return {"slug": e["slug"], "term": e["term"], "aka": e["aka"], "category": e["category"],
            "teaser": e["teaser"]}


def index(path: Path | None = None) -> dict[str, Any]:
    """The index page: every term's card, and the categories in use."""
    entries = load(path)
    used = {e["category"] for e in entries}
    return {"terms": [_card(e) for e in entries],
            "categories": [{"key": k, "name": v} for k, v in CATEGORIES.items() if k in used]}


def entry(slug: str, path: Path | None = None) -> dict[str, Any] | None:
    """One term's page: its paragraph, its related terms, and its neighbours
    in A-Z order. None for a slug the glossary does not have."""
    entries = load(path)
    by = {e["slug"]: e for e in entries}
    e = by.get(slug)
    if e is None:
        return None
    i = entries.index(e)
    return {
        **_card(e),
        "category_name": CATEGORIES[e["category"]],
        "definition": e["definition"],
        "related": [_card(by[r]) for r in e["related"]],
        "previous": _card(entries[i - 1]) if i > 0 else None,
        "next": _card(entries[i + 1]) if i + 1 < len(entries) else None,
    }


if __name__ == "__main__":  # python -m judge.glossary check PART.yaml [--slugs SLUGS.txt]
    import sys

    args = sys.argv[1:]
    if not args or args[0] != "check":
        raise SystemExit("usage: python -m judge.glossary check FILE.yaml [--slugs SLUGS.txt]")
    f = Path(args[1]) if len(args) > 1 else PATH
    known = None
    if "--slugs" in args:
        known = set(Path(args[args.index("--slugs") + 1]).read_text(encoding="utf-8").split())
    data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    terms = data.get("terms") or []
    bad = problems(terms, known=known)
    print(f"{len(terms)} terms, {len(bad)} problem(s)")
    for b in bad:
        print("-", b)
    raise SystemExit(1 if bad else 0)
