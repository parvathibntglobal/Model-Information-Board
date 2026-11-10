"""The REPLY CHECK: rules a reply must pass, in plain code (ARCHITECTURE.md 5.4b).

Pure functions of the reply text, the thread it answers, and two config files:
config/claims.yaml (what may be said about Kite Pulse, the disclosure line) and
config/reply_rules.yaml (links, length). No model, no network, no database.

    check(text, thread, rules) -> Result(passed, failures, claims_used, ...)

THE RULES, each a failure code:

    no_disclosure        the disclosure line is not on a line of its own
    too_many_mentions    Kite Pulse named more than once outside the disclosure
    unapproved_claim     a mention of Kite Pulse that is not inside an approved
                         sentence copied whole
    refused_phrase       a refused phrase anywhere (whole words, any case)
    pitch_first          Kite Pulse named in the first paragraph of the answer
    link_not_allowed     a link to a host not in reply_rules.yaml
    too_many_kp_links    more than one link to Kite Pulse's own site
    number_not_in_sources  a number that is in neither the thread's saved text
                         nor an approved sentence the reply uses
    too_long             longer than the source's max_reply_chars

WHAT A PASS DOES NOT MEAN. It says the reply keeps the rules, not that it is
right, helpful or what the person asked; `not_checked` lists that and the
check's own blind spots, and the review screen shows them beside every result
so a green result cannot read as an approved answer (rule 4).

PHASE 1: ADVISORY, NOT A GATE. A person checks a hand-written reply before
posting it; "Mark posted" does not require a pass, because the text checked is
not necessarily the text posted, and because this check's error rate has not
been measured (rule 8: a weight first, a gate on evidence). Phase 2 makes it the
gate on Approve for model drafts, which is where ARCHITECTURE.md puts it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config"

MENTION = re.compile(r"kite[\s\-_]*pulse", re.I)
URL = re.compile(r"(?:https?://|www\.)[^\s<>()\[\]\"']+", re.I)
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                         " ": " "})

NOT_CHECKED = (
    "whether the answer is correct, helpful, or what the person asked",
    "claims made without naming Kite Pulse (\"it also tracks...\"): only sentences "
    "that name it are matched against the approved list",
    "links written without http:// or www. (a bare domain such as example.com)",
    "numbers in the full thread: only the title and the text the Finder saved are "
    "compared, which for some forums is the title alone",
)


class RulesError(RuntimeError):
    """A config file is missing a key or holds a wrong value."""


class Refused(ValueError):
    """Nothing to check (empty text)."""


@dataclass(frozen=True)
class Rules:
    disclosure: str
    approved: tuple[tuple[str, str], ...]      # (id, text)
    refused: tuple[tuple[str, str], ...]       # (phrase, why)
    claims_reviewed_by: str | None
    allowed_link_domains: frozenset[str]
    also_allow_thread_host: bool
    kite_pulse_link_domains: frozenset[str]
    max_reply_chars: dict[str, int]


@dataclass(frozen=True)
class Failure:
    code: str
    detail: str


@dataclass(frozen=True)
class Result:
    passed: bool
    failures: tuple[Failure, ...]
    claims_used: tuple[str, ...]
    chars: int
    max_chars: int
    warnings: tuple[str, ...] = ()
    not_checked: tuple[str, ...] = field(default=NOT_CHECKED)

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "failures": [{"code": f.code, "detail": f.detail} for f in self.failures],
            "claims_used": list(self.claims_used),
            "chars": self.chars,
            "max_chars": self.max_chars,
            "warnings": list(self.warnings),
            "not_checked": list(self.not_checked),
        }


# ── config ───────────────────────────────────────────────────────────────────

def _need(mapping: Any, key: str, where: str) -> Any:
    if not isinstance(mapping, dict) or key not in mapping:
        raise RulesError(f"{where}: missing key {key!r}")
    return mapping[key]


def load_rules(config_dir: Path = CONFIG) -> Rules:
    claims = yaml.safe_load((config_dir / "claims.yaml").read_text(encoding="utf-8"))
    rules = yaml.safe_load((config_dir / "reply_rules.yaml").read_text(encoding="utf-8"))
    disclosure = _need(_need(claims, "disclosure", "claims.yaml"), "line",
                       "claims.yaml: disclosure")
    approved = tuple((_need(c, "id", "claims.yaml: approved"), _norm(_need(c, "text", c.get("id"))))
                     for c in _need(claims, "approved", "claims.yaml"))
    refused = tuple((_need(r, "phrase", "claims.yaml: refused"), _need(r, "why", r.get("phrase")))
                    for r in _need(claims, "refused", "claims.yaml"))
    lengths = _need(rules, "max_reply_chars", "reply_rules.yaml")
    if not isinstance(lengths, dict) or not all(
            isinstance(v, int) and v > 0 for v in lengths.values()):
        raise RulesError("reply_rules.yaml: max_reply_chars must map each source to a "
                         "positive number")
    also = _need(rules, "also_allow_thread_host", "reply_rules.yaml")
    if not isinstance(also, bool):
        raise RulesError("reply_rules.yaml: also_allow_thread_host must be true or false")
    return Rules(
        disclosure=_norm(disclosure),
        approved=approved,
        refused=refused,
        claims_reviewed_by=_need(claims, "reviewed_by", "claims.yaml"),
        allowed_link_domains=frozenset(
            h.lower() for h in _need(rules, "allowed_link_domains", "reply_rules.yaml")),
        also_allow_thread_host=also,
        kite_pulse_link_domains=frozenset(
            h.lower() for h in _need(rules, "kite_pulse_link_domains", "reply_rules.yaml") or ()),
        max_reply_chars=dict(lengths),
    )


# ── helpers ──────────────────────────────────────────────────────────────────

def _norm(text: str) -> str:
    """Curly quotes to straight, every run of whitespace to one space."""
    return re.sub(r"\s+", " ", (text or "").translate(_QUOTES)).strip()


def _host(url: str) -> str:
    if not re.match(r"https?://", url, re.I):
        url = "https://" + url
    return (urlsplit(url).hostname or "").lower().removeprefix("www.")


def _has_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text, re.I) is not None


def _sentence_around(text: str, start: int, end: int) -> str:
    left = max(text.rfind(c, 0, start) for c in ".!?\n")
    right = [i for i in (text.find(c, end) for c in ".!?\n") if i != -1]
    return text[left + 1:(min(right) + 1 if right else len(text))].strip()


def _disclosure_lines(text: str, line: str) -> list[int]:
    """Indexes of lines that are the disclosure line, with optional . or !"""
    want = re.compile(rf"{re.escape(line)}[.!]?", re.I)
    return [i for i, raw in enumerate(text.splitlines()) if want.fullmatch(_norm(raw))]


# ── the check ────────────────────────────────────────────────────────────────

def check(text: str, thread: dict[str, Any], rules: Rules) -> Result:
    """Every rule, every failure (not only the first), and what was not checked."""
    text = (text or "").translate(_QUOTES).replace("\r\n", "\n").strip()
    if not text:
        raise Refused("paste the reply to check")
    source = thread["source"]
    if source not in rules.max_reply_chars:
        raise RulesError(f"reply_rules.yaml: max_reply_chars has no entry for {source!r}")
    failures: list[Failure] = []

    # Disclosure, and the answer with it taken out.
    lines = text.splitlines()
    found = _disclosure_lines(text, rules.disclosure)
    if not found:
        failures.append(Failure("no_disclosure",
                                f"add the line \"{rules.disclosure}\" on its own"))
    body = "\n".join(ln for i, ln in enumerate(lines) if i not in found).strip()
    flat = _norm(body)

    # Mentions.
    mentions = list(MENTION.finditer(flat))
    if len(mentions) > 1:
        failures.append(Failure(
            "too_many_mentions",
            f"Kite Pulse is named {len(mentions)} times outside the disclosure; at most once"))

    # Approved claims: blank out every approved sentence the reply uses, then any
    # mention left over is outside one.
    used: list[str] = []
    rest = flat
    for claim_id, claim in rules.approved:
        if claim in rest:
            used.append(claim_id)
            rest = rest.replace(claim, " " * len(claim))
    for m in MENTION.finditer(rest):
        failures.append(Failure(
            "unapproved_claim",
            f"\"{_sentence_around(flat, m.start(), m.end())}\" is not an approved sentence; "
            "use one from claims.yaml word for word, or leave Kite Pulse out"))

    # Refused phrases, over the whole reply.
    for phrase, why in rules.refused:
        if _has_phrase(text, phrase):
            failures.append(Failure("refused_phrase", f"\"{phrase}\": {why}"))

    # Help first.
    paragraphs = [p for p in re.split(r"\n\s*\n", body) if p.strip()]
    if paragraphs and MENTION.search(paragraphs[0]):
        failures.append(Failure(
            "pitch_first", "Kite Pulse is named in the first paragraph; answer the question first"))

    # Links.
    thread_host = _host(thread["url"])
    allowed = set(rules.allowed_link_domains) | set(rules.kite_pulse_link_domains)
    if rules.also_allow_thread_host:
        allowed.add(thread_host)
    kp_links = 0
    for m in URL.finditer(text):
        host = _host(m.group().rstrip(".,;:!?"))
        if host in rules.kite_pulse_link_domains:
            kp_links += 1
        if host not in allowed:
            why = ("Kite Pulse has no public site to link to yet"
                   if MENTION.search(host.replace(".", " ")) else "not in reply_rules.yaml")
            failures.append(Failure("link_not_allowed", f"{host}: {why}"))
    if kp_links > 1:
        failures.append(Failure("too_many_kp_links",
                                f"{kp_links} links to Kite Pulse; at most one"))

    # Numbers: from the thread's saved text or an approved sentence used.
    sources = " ".join([thread.get("title") or "", thread.get("body") or ""]
                       + [c for cid, c in rules.approved if cid in used])
    known = set(NUMBER.findall(sources))
    unsourced = sorted({n for n in NUMBER.findall(URL.sub(" ", text)) if n not in known})
    if unsourced:
        failures.append(Failure(
            "number_not_in_sources",
            f"{', '.join(unsourced)}: not in the thread's saved text or an approved "
            "sentence; check it, or write it in words if it is not a figure"))

    # Length.
    limit = rules.max_reply_chars[source]
    if len(text) > limit:
        failures.append(Failure("too_long", f"{len(text)} characters; the limit here is {limit}"))

    warnings = []
    if rules.claims_reviewed_by is None:
        warnings.append("claims.yaml has not been reviewed by the product owner yet, so an "
                        "approved sentence is not yet confirmed true")
    return Result(passed=not failures, failures=tuple(failures), claims_used=tuple(used),
                  chars=len(text), max_chars=limit, warnings=tuple(warnings))
