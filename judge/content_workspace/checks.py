"""The platform fit check: every rule of a platform, run against one draft.

Plain Python, no model. Each rule (a `cw_note` row in section `rule`) names a
coded check and a severity; the check says whether the draft meets it, and the
severity says how a miss is shown (`fail` or `warn`). A rule whose check is
`manual` is listed for a person to tick.

Nothing here blocks anything (rule 8). These checks are word lists and
patterns whose error rates have not been measured on any population; a draft
is saved, marked ready and posted whatever they say. The report is counts of
rules, never a score (rule 3).

Outcomes per rule:
  pass        the check ran and the draft meets the rule
  warn/fail   the check ran and the draft misses it (the rule's severity)
  manual      a person checks it
  unchecked   the check could not run (a missing limit, an unset site
              address), said in words; never counted as a pass (rule 6)
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

URL = re.compile(r"https?://[^\s<>()\[\]\"']+", re.I)
HASHTAG = re.compile(r"(?<![\w&/])#[A-Za-z_][\w]*")
HANDLE = re.compile(r"(?<![\w./])@[A-Za-z0-9_]{2,}|(?<![\w/])u/[A-Za-z0-9_-]{3,}")
PERCENT = re.compile(r"\d+(?:\.\d+)?\s?%")
POPULATION = re.compile(
    r"\b\d[\d,]*\s+(?:engineers?|developers?|people|users?|posts?|reports?|respondents?|"
    r"threads?|comments?|reviewers?|teams?|companies)\b", re.I)
DENOMINATOR = re.compile(r"\b(?:of|out of|from|among|across|in)\s+[\d,]+\b|\bn\s*=\s*\d", re.I)
SCORE = re.compile(r"\b\d+(?:\.\d+)?\s*/\s*(?:5|10|100)\b|\bout of (?:5|10|100)\b(?!\s+\w+s\b)",
                   re.I)
QUOTED = re.compile(r"[\"“”]([^\"“”]+)[\"“”]")
TABLE_RULE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", re.M)
FIGURE = re.compile(r"\b\d[\d,]*(?:\.\d+)?\b")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+|\n+")


def _parts(d: dict[str, Any], cfg: dict[str, Any]) -> list[str]:
    body = d.get("body") or ""
    if d.get("format") in cfg["per_part_formats"]:
        sep = cfg["part_separator"]
        parts = [p.strip() for p in re.split(rf"^\s*{re.escape(sep)}\s*$", body, flags=re.M)]
        return [p for p in parts if p] or [""]
    return [body]


def _words_text(d: dict[str, Any]) -> str:
    return f"{d.get('title') or ''}\n{d.get('body') or ''}"


def _need(params: dict[str, Any], key: str) -> Any:
    """A rule's parameter, or None when the rule does not set it (the caller
    reports the rule as unchecked rather than guessing a limit)."""
    v = params.get(key)
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


Result = tuple[bool | None, str]


def check_length(d, params, cfg) -> Result:
    limit = _need(params, "max_chars")
    if limit is None:
        return None, "this rule sets no max_chars"
    url_chars = _need(params, "url_chars")
    worst = []
    parts = _parts(d, cfg)
    for i, part in enumerate(parts, 1):
        n = len(URL.sub("x" * int(url_chars), part)) if url_chars else len(part)
        if n > limit:
            worst.append(f"part {i}: {n:,}" if len(parts) > 1 else f"{n:,}")
    counted = f" (links counted as {int(url_chars)})" if url_chars else ""
    if worst:
        return False, f"over {limit:,} characters{counted}: {', '.join(worst)}"
    longest = max(len(p) for p in parts)
    where = f"longest of {len(parts)} parts" if len(parts) > 1 else "length"
    return True, f"{where} {longest:,} of {limit:,} characters{counted}"


def check_title_length(d, params, cfg) -> Result:
    limit = _need(params, "max_chars")
    if limit is None:
        return None, "this rule sets no max_chars"
    title = (d.get("title") or "").strip()
    if not title:
        return False, "no title written"
    if len(title) > limit:
        return False, f"title is {len(title)} characters, over {limit}"
    return True, f"title {len(title)} of {limit} characters"


def check_hook_length(d, params, cfg) -> Result:
    limit = _need(params, "max_chars")
    if limit is None:
        return None, "this rule sets no max_chars"
    body = (d.get("body") or "").strip()
    if not body:
        return False, "no text written"
    first = SENTENCE_END.split(body, maxsplit=1)[0]
    if len(first) > limit:
        return False, (f"the first sentence runs {len(first)} characters; the post is cut at "
                       f"about {limit}, so the point may land after the cut")
    return True, f"first sentence {len(first)} characters, inside the first {limit}"


def check_denominator(d, params, cfg) -> Result:
    missing, figures = [], 0
    for sentence in SENTENCE_END.split(_words_text(d)):
        found = PERCENT.findall(sentence) + POPULATION.findall(sentence)
        figures += len(found)
        if found and not DENOMINATOR.search(sentence):
            missing.extend(f.strip() for f in found)
    if not figures:
        return True, "no percentages or counts of people/posts to check"
    if missing:
        shown = ", ".join(f"'{m}'" for m in missing[:4])
        return False, (f"{len(missing)} of {figures} figures have no denominator in their "
                       f"sentence: {shown}")
    return True, f"all {figures} figures name what they were counted over"


def check_hashtags(d, params, cfg) -> Result:
    limit = _need(params, "max")
    if limit is None:
        return None, "this rule sets no max"
    tags = HASHTAG.findall(d.get("body") or "")
    if len(tags) > limit:
        return False, f"{len(tags)} hashtags, over {limit}: {' '.join(tags[:8])}"
    return True, f"{len(tags)} hashtag{'s' if len(tags) != 1 else ''} (at most {limit})"


def check_link_placement(d, params, cfg) -> Result:
    mode = params.get("mode")
    links = URL.findall(d.get("body") or "")
    has = f"{len(links)} link{'s' if len(links) != 1 else ''} in the text"
    if mode == "record":
        return None, f"{has}. Record which placement this post tests (in the post, or in a reply)."
    if mode == "avoid":
        if links:
            return False, f"{has}; keep links out of the body"
        return True, "no link in the body"
    if mode == "not_clickable":
        if links:
            return False, f"{has}, and links are not clickable here"
        return True, "no link in the text"
    return None, "this rule sets no mode (record, avoid or not_clickable)"


def check_verbatim_quote(d, params, cfg) -> Result:
    text = _words_text(d)
    long_quotes = [q for q in QUOTED.findall(text) if len(q.split()) >= cfg["quote_min_words"]]
    blockquotes = [ln for ln in text.splitlines() if ln.lstrip().startswith(">")]
    if long_quotes or blockquotes:
        n = len(long_quotes) + len(blockquotes)
        return False, (f"{n} quotation{'s' if n != 1 else ''} found; confirm none is a Reddit "
                       "or X user's words (paraphrase and count instead)")
    return True, "no long quotation found"


def check_handles(d, params, cfg) -> Result:
    found = sorted(set(HANDLE.findall(_words_text(d))))
    if found:
        plural = "s" if len(found) != 1 else ""
        return False, f"names {len(found)} handle{plural}: {', '.join(found[:5])}"
    return True, "no handles"


def check_score_words(d, params, cfg) -> Result:
    found = [m.group(0) for m in SCORE.finditer(_words_text(d))]
    if found:
        return False, f"looks like a score: {', '.join(found[:4])}"
    return True, "no scores"


def check_hype_words(d, params, cfg) -> Result:
    words = list(cfg["hype_words"]) + list(params.get("words") or [])
    text = _words_text(d)
    found = [w for w in words if re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text, re.I)]
    if found:
        return False, f"hype words: {', '.join(found)}"
    return True, f"none of the {len(words)} listed hype words"


def check_disclosure(d, params, cfg) -> Result:
    text = _words_text(d).lower()
    hit = next((p for p in cfg["disclosure_phrases"] if p in text), None)
    if hit:
        return True, f"discloses (\"{hit}\")"
    return False, "no disclosure found; say that we built the board"


def check_table_or_data(d, params, cfg) -> Result:
    body = d.get("body") or ""
    if TABLE_RULE.search(body):
        return True, "has a table"
    figures = FIGURE.findall(body)
    if len(figures) >= 2:
        return True, f"{len(figures)} figures in the text"
    return False, "no table and fewer than 2 figures: the data is not in the post"


def check_ai_assisted(d, params, cfg) -> Result:
    if d.get("ai_assisted"):
        return False, "marked as AI-assisted"
    return True, "marked as written by a person"


def check_utm(d, params, cfg, *, hosts: list[str]) -> Result:
    if not hosts:
        return None, ("the site address is not set (workspace.yaml site.hosts), "
                      "so no link is checked")
    ours = [u for u in URL.findall(d.get("body") or "")
            if any((urlsplit(u).hostname or "").endswith(h) for h in hosts)]
    if not ours:
        return True, "no link to our site"
    bare = [u for u in ours if "utm_source=" not in u]
    if bare:
        return False, f"{len(bare)} of {len(ours)} links to our site have no utm_source"
    return True, f"all {len(ours)} links to our site carry utm_source"


CHECKS: dict[str, Callable[..., Result] | None] = {
    "length": check_length,
    "title_length": check_title_length,
    "hook_length": check_hook_length,
    "denominator": check_denominator,
    "hashtags": check_hashtags,
    "link_placement": check_link_placement,
    "verbatim_quote": check_verbatim_quote,
    "handles": check_handles,
    "score_words": check_score_words,
    "hype_words": check_hype_words,
    "disclosure": check_disclosure,
    "table_or_data": check_table_or_data,
    "ai_assisted": check_ai_assisted,
    "utm": check_utm,
    "manual": None,
}

OUTCOMES = ("pass", "warn", "fail", "manual", "unchecked")


def applies(rule: dict[str, Any], fmt: str) -> bool:
    return not rule.get("formats") or fmt in rule["formats"]


def run(d: dict[str, Any], rules: list[dict[str, Any]], settings: dict[str, Any],
        environ: dict[str, str] | None = None) -> dict:
    """The fit report for draft `d` against `rules` (live, unarchived rule notes)."""
    from judge.content_workspace.settings import site_hosts

    cfg = settings["checks"]
    hosts = site_hosts(settings, environ)
    # A platform's own rule on a coded check replaces the rule for every
    # platform on that check (Hacker News fails hype words; the common rule
    # only warns), so one check is never reported twice.
    own = {r["check_id"] for r in rules
           if r["platform_key"] is not None and r["check_id"] != "manual"
           and applies(r, d["format"])}
    results, skipped, replaced = [], 0, 0
    for rule in rules:
        if not applies(rule, d["format"]):
            skipped += 1
            continue
        if rule["platform_key"] is None and rule["check_id"] in own:
            replaced += 1
            continue
        fn = CHECKS.get(rule["check_id"], "missing")
        if fn == "missing":
            ok, detail = None, f"no coded check is named {rule['check_id']!r}"
        elif fn is None:
            ok, detail = None, "checked by a person"
        else:
            kwargs = {"hosts": hosts} if rule["check_id"] == "utm" else {}
            ok, detail = fn(d, rule.get("params") or {}, cfg, **kwargs)
        if rule["check_id"] == "manual" or (ok is None and rule["severity"] == "manual"):
            outcome = "manual"
        elif ok is None:
            outcome = "unchecked"
        elif ok:
            outcome = "pass"
        else:
            outcome = "manual" if rule["severity"] == "manual" else rule["severity"]
        results.append({
            "note_id": rule["id"], "rule": rule["body"], "check": rule["check_id"],
            "severity": rule["severity"], "for_all_platforms": rule["platform_key"] is None,
            "outcome": outcome, "detail": detail,
        })
    counts = {o: sum(r["outcome"] == o for r in results) for o in OUTCOMES}
    counts["rules"] = len(results)
    counts["not_for_this_format"] = skipped
    counts["replaced_by_platform_rule"] = replaced
    return {"results": results, "counts": counts, "summary": summary(counts)}


def summary(c: dict[str, int]) -> str:
    """The report in words, with its denominator (rule 7). No score."""
    checked = c["pass"] + c["warn"] + c["fail"]
    parts = [f"{c['pass']} of {checked} coded checks met"]
    if c["fail"]:
        parts.append(f"{c['fail']} failed")
    if c["warn"]:
        parts.append(f"{c['warn']} warning{'s' if c['warn'] != 1 else ''}")
    if c["manual"]:
        parts.append(f"{c['manual']} to check by hand")
    if c["unchecked"]:
        parts.append(f"{c['unchecked']} could not be checked")
    return ", ".join(parts) + f" ({c['rules']} rules apply to this format)."
