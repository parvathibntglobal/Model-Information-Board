"""The pure half of the official-sources harvest: the contract, globs, notebook
flattening, titles, PyVideo talk records. No network and no database here.

contract/official_sources.yaml says what is read and why; harvest.py reads it.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

CONTRACT = Path(__file__).resolve().parents[2] / "contract" / "official_sources.yaml"
KINDS = ("cookbook", "sdk", "spec")
PROVIDERS = ("openai", "anthropic", "google", "mistral")

#: What an official_doc row is, by the kind of repository it came from.
DOC_KIND = {"cookbook": "cookbook", "sdk": "changelog", "spec": "spec"}


class OfficialContractError(ValueError):
    """contract/official_sources.yaml is missing something a read needs (rule 12)."""


@dataclass(frozen=True)
class Repo:
    key: str
    repo: str
    branch: str
    provider: str
    kind: str
    licence: str
    include: tuple[str, ...]
    exclude: tuple[str, ...]


@dataclass(frozen=True)
class PyVideo:
    key: str
    repo: str
    branch: str
    licence: str
    talk_glob: str
    min_event_year: int
    no_publish_path: str
    #: host label -> domains, e.g. {"youtube": ("youtube.com", "youtu.be")}
    video_hosts: dict[str, tuple[str, ...]]
    llm_terms: re.Pattern


@dataclass(frozen=True)
class Contract:
    api: str
    min_interval_seconds: float
    max_blob_fetches_per_run: int
    stop_below_remaining: int
    max_release_pages: int
    max_blob_bytes: int
    repos: tuple[Repo, ...]
    pyvideo: PyVideo


def _positive_int(raw: dict, key: str, where: str, problems: list[str]) -> int:
    value = raw.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        problems.append(f"{where}{key} must be a positive integer")
        return 0
    return value


def _globs(raw: dict, key: str, where: str, problems: list[str], *, empty_ok: bool) -> tuple:
    value = raw.get(key)
    if (not isinstance(value, list) or (not value and not empty_ok)
            or not all(isinstance(g, str) and g for g in value)):
        problems.append(f"{where}{key} must be a list of globs"
                        + ("" if empty_ok else ", not empty"))
        return ()
    return tuple(value)


def _text(raw: dict, key: str, where: str, problems: list[str]) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        problems.append(f"{where}{key} is required")
        return ""
    return value


def terms_pattern(words: list[str]) -> re.Pattern:
    """Whole words, any case, longest first so "language models" wins over
    "language model". The same shape as the News LLM badge."""
    longest_first = sorted(words, key=len, reverse=True)
    return re.compile(r"\b(" + "|".join(re.escape(w) for w in longest_first) + r")\b", re.I)


def load_contract(path: Path = CONTRACT) -> Contract:
    """Every value the harvest uses, refused when absent - no defaults here."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    problems: list[str] = []
    api = _text(raw, "api", "", problems)
    if api and not api.startswith("https://"):
        problems.append("api must be https://")
    pol = raw.get("politeness")
    if not isinstance(pol, dict):
        problems.append("politeness is required")
        pol = {}
    interval = pol.get("min_interval_seconds")
    if not isinstance(interval, (int, float)) or isinstance(interval, bool) or interval < 0:
        problems.append("politeness.min_interval_seconds must be a number >= 0")
    caps = {k: _positive_int(pol, k, "politeness.", problems)
            for k in ("max_blob_fetches_per_run", "stop_below_remaining",
                      "max_release_pages", "max_blob_bytes")}

    repos: list[Repo] = []
    seen: set[str] = set()
    raw_repos = raw.get("repos")
    if not isinstance(raw_repos, list) or not raw_repos:
        problems.append("repos must be a non-empty list")
        raw_repos = []
    for i, r in enumerate(raw_repos):
        where = f"repos[{i}]."
        if not isinstance(r, dict):
            problems.append(f"repos[{i}] must be a mapping")
            continue
        before = len(problems)
        key, repo, branch, licence = (_text(r, f, where, problems)
                                      for f in ("key", "repo", "branch", "licence"))
        if r.get("kind") not in KINDS:
            problems.append(f"{where}kind must be one of {KINDS}")
        if r.get("provider") not in PROVIDERS:
            problems.append(f"{where}provider must be one of {PROVIDERS}")
        if repo and repo.count("/") != 1:
            problems.append(f"{where}repo must be owner/name")
        include = _globs(r, "include", where, problems, empty_ok=False)
        exclude = _globs(r, "exclude", where, problems, empty_ok=True)
        if key in seen:
            problems.append(f"{where}key {key!r} is listed twice")
        seen.add(key)
        if len(problems) == before:
            repos.append(Repo(key, repo, branch, r["provider"], r["kind"], licence,
                              include, exclude))

    pv = raw.get("pyvideo")
    if not isinstance(pv, dict):
        problems.append("pyvideo is required")
        pv = {}
    where = "pyvideo."
    pv_key, pv_repo, pv_branch, pv_licence, talk_glob, no_publish = (
        _text(pv, f, where, problems)
        for f in ("key", "repo", "branch", "licence", "talk_glob", "no_publish_path"))
    if pv_key and pv_key in seen:
        problems.append(f"pyvideo.key {pv_key!r} is also a repository key")
    min_year = _positive_int(pv, "min_event_year", where, problems)
    hosts = pv.get("video_hosts")
    if (not isinstance(hosts, dict) or not hosts
            or not all(isinstance(v, list) and v and all(isinstance(d, str) and d for d in v)
                       for v in hosts.values())):
        problems.append("pyvideo.video_hosts must map each host label to a list of domains")
        hosts = {}
    elif "other" in hosts:
        problems.append("pyvideo.video_hosts must not name `other`: it is every other domain")
    words = pv.get("llm_terms")
    if not isinstance(words, list) or not words or not all(isinstance(w, str) and w
                                                           for w in words):
        problems.append("pyvideo.llm_terms must be a non-empty list of words")
        words = []
    if problems:
        raise OfficialContractError("contract/official_sources.yaml: " + "; ".join(problems))
    return Contract(
        api=api.rstrip("/"), min_interval_seconds=float(interval), repos=tuple(repos),
        pyvideo=PyVideo(pv_key, pv_repo, pv_branch, pv_licence, talk_glob, min_year, no_publish,
                        {k: tuple(d.lower() for d in v) for k, v in hosts.items()},
                        terms_pattern(words)),
        **caps)


# ── globs ────────────────────────────────────────────────────────────────────

def glob_regex(pattern: str) -> re.Pattern:
    """`*` stays inside one folder, `?` is one character in a folder, `**/` is
    any number of folders including none, and a trailing `/**` is everything
    under a folder. Matched against the whole path, case-sensitively."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def selected(path: str, include: tuple[str, ...], exclude: tuple[str, ...]) -> bool:
    """Kept when an include glob matches and no exclude glob does."""
    return (any(glob_regex(g).match(path) for g in include)
            and not any(glob_regex(g).match(path) for g in exclude))


def git_blob_sha(data: bytes) -> str:
    """The sha git names a blob by: sha1 of `blob <size>\\0` and the bytes. A
    fetched blob is checked against the sha it was asked for, so bytes that are
    not the file the tree listed are refused rather than stored under its name."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()  # noqa: S324 - git's id


# ── titles and notebook text ─────────────────────────────────────────────────

_ATX_H1 = re.compile(r"^ {0,3}#[ \t]+(.+?)[ \t]*#*[ \t]*$")
_SETEXT_H1 = re.compile(r"^ {0,3}=+[ \t]*$")
_FENCE = re.compile(r"^ {0,3}(```|~~~)")


def first_h1(markdown: str) -> str | None:
    """The first level-one heading - `# Title`, or a line underlined with `===` -
    outside fenced code. A `# comment` inside a ``` block is code, not a title.
    None when there is none."""
    in_fence = None
    previous = ""
    for line in markdown.splitlines():
        fence = _FENCE.match(line)
        if fence:
            if in_fence is None:
                in_fence = fence.group(1)
            elif fence.group(1) == in_fence:
                in_fence = None
            previous = ""
            continue
        if in_fence:
            continue
        m = _ATX_H1.match(line)
        if m and m.group(1).strip():
            return m.group(1).strip()
        if _SETEXT_H1.match(line) and previous.strip():
            return previous.strip()
        previous = line
    return None


def title_for(path: str, h1: str | None) -> tuple[str, str]:
    """(title, where it came from). The file's first H1, or - when it has none -
    its file name, and `title_source` says which, so a file name never passes
    for a title the author wrote (rule 6)."""
    if h1:
        return h1, "h1"
    return path.rsplit("/", 1)[-1], "file_name"


def _source(cell: dict) -> str:
    src = cell.get("source", "")
    return "".join(src) if isinstance(src, list) else str(src or "")


@dataclass(frozen=True)
class Notebook:
    text: str
    h1: str | None


def flatten_notebook(data: bytes) -> Notebook:
    """The notebook as text a writing pack reads: markdown cells as they are,
    code cells as fenced code, outputs dropped. Raw cells (nbconvert directives)
    are dropped too. The fence names the notebook's own language when its
    metadata gives one, and no language otherwise - never an assumed `python`.

    Raises ValueError on bytes that are not a notebook: the caller keeps the raw
    file and records that it could not be read, rather than storing an empty
    text that looks like an empty notebook."""
    try:
        nb = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"not a notebook: {exc}") from exc
    if not isinstance(nb, dict) or not isinstance(nb.get("cells"), list):
        raise ValueError("not a notebook: no `cells` list")
    meta = nb.get("metadata") if isinstance(nb.get("metadata"), dict) else {}
    lang = ((meta.get("kernelspec") or {}).get("language")
            or (meta.get("language_info") or {}).get("name") or "")
    parts: list[str] = []
    h1 = None
    for cell in nb["cells"]:
        if not isinstance(cell, dict):
            continue
        body = _source(cell).strip("\n")
        if not body.strip():
            continue
        if cell.get("cell_type") == "markdown":
            parts.append(body)
            if h1 is None:
                h1 = first_h1(body)
        elif cell.get("cell_type") == "code":
            parts.append(f"```{lang}\n{body}\n```")
    return Notebook("\n\n".join(parts) + ("\n" if parts else ""), h1)


# ── PyVideo ──────────────────────────────────────────────────────────────────

_YEAR = re.compile(r"(?<!\d)((?:19|20)\d\d)(?!\d)")


def event_year(event: str) -> int | None:
    """The year in an event folder's name ("pycon-us-2024" -> 2024); the latest
    when it names two. None when it names none - never a guessed year."""
    years = [int(y) for y in _YEAR.findall(event)]
    return max(years) if years else None


def video_host(url: str, hosts: dict[str, tuple[str, ...]]) -> str:
    """`youtube`, `vimeo` (or whatever the contract names) by the end of the
    link's domain, else `other`. Derived from the link alone: nothing is asked
    of the host."""
    host = (urlsplit(url).hostname or "").lower()
    for label, domains in hosts.items():
        if any(host == d or host.endswith("." + d) for d in domains):
            return label
    return "other"


def matched_terms(pattern: re.Pattern, *texts: str | None) -> list[str]:
    return sorted({m.group(1).lower() for t in texts if t for m in pattern.finditer(t)})


def no_publish_ids(data: bytes) -> frozenset[int]:
    """PyVideo's NO_PUBLISH.json: a list of talk ids. Anything else raises - an
    unreadable list must stop the read, never be taken as an empty one."""
    try:
        ids = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"NO_PUBLISH.json is not JSON: {exc}") from exc
    if not isinstance(ids, list) or not all(isinstance(i, int) and not isinstance(i, bool)
                                            for i in ids):
        raise ValueError("NO_PUBLISH.json is not a list of talk ids")
    return frozenset(ids)


def parse_talk(data: bytes, path: str, pv: PyVideo) -> dict[str, Any]:
    """One talk record, as PyVideo gives it. A value it does not give stays None
    (rule 6). Raises ValueError on a record with no title or a date that is not
    a date - recorded as a failed file, never stored half-read."""
    try:
        rec = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"not JSON: {exc}") from exc
    if not isinstance(rec, dict):
        raise ValueError("not a talk record")
    title = rec.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("no title")
    recorded = rec.get("recorded")
    if recorded is not None:
        try:
            recorded = date.fromisoformat(str(recorded)[:10])
        except ValueError as exc:
            raise ValueError(f"recorded {rec.get('recorded')!r} is not a date") from exc
    urls = [v["url"] for v in rec.get("videos") or []
            if isinstance(v, dict) and isinstance(v.get("url"), str) and v["url"].strip()]
    pid = rec.get("id")
    duration = rec.get("duration")
    description = rec.get("description") if isinstance(rec.get("description"), str) else None
    return {
        "path": path, "event": path.split("/", 1)[0],
        "pyvideo_id": pid if isinstance(pid, int) and not isinstance(pid, bool) else None,
        "title": title.strip(), "recorded": recorded,
        "speakers": [s for s in rec.get("speakers") or [] if isinstance(s, str) and s.strip()],
        "description": description or None,
        "video_urls": urls, "video_hosts": [video_host(u, pv.video_hosts) for u in urls],
        "thumbnail_url": rec.get("thumbnail_url") or None,
        "duration_seconds": duration if isinstance(duration, int)
                                        and not isinstance(duration, bool) else None,
        "language": rec.get("language") or None,
        "copyright_text": rec.get("copyright_text") or None,
        "llm_terms": matched_terms(pv.llm_terms, title, description),
    }
