"""The SHORTLISTER (ARCHITECTURE.md 5.2): order To review, one model call per thread.

    py -3.12 web/src/kitepulse/outreach/shortlist.py --dry-run --limit 5
    py -3.12 web/src/kitepulse/outreach/shortlist.py --limit 5
    py -3.12 web/src/kitepulse/outreach/shortlist.py --limit 5 --source devto

For every thread still in To review ('found') with no row for the current
prompt version, in this order:

1. CODE SETS ASIDE (no model, no spend): too_old, hiring_thread,
   words_far_apart (config/shortlist.yaml). Recorded as `set_aside` and kept
   in To review, at the bottom, saying why. Never dropped (rule 8).
2. CODE CHECKS THE CAP: common/spend.check against OUTREACH_DAILY_BUDGET_USD.
   Reached: no more calls today; the rest wait, unrecorded.
3. THE MODEL PROPOSES, through one forced tool call (prompts/shortlist/):
   problem, relevance, article_slug, reason.
4. CODE RECORDS what it cost (kp_outreach_spend), then CHECKS every field and
   stores the answer as `proposed`, or as `invalid` with the reason. An invalid
   answer is never corrected to the nearest valid value (rule 12).

What the model's answer can do: ORDER To review (kp_review.listing). It
changes no thread's status, hides nothing, drops nothing, posts nothing.
"An LLM may propose, it may never decide" (CLAUDE.md rule 2); outreach is a
recorded caller there, stage `shortlist`.

`--limit` is required: the most MODEL CALLS this run may make. Set-asides are
free and not counted. A provider failure STOPS the run (a bad key would
otherwise fail on every thread); whether that failed call was billed is
unknown, and the run says so.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
for _p in (str(HERE), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import yaml  # noqa: E402
from common import config as cfg  # noqa: E402
from common import db, llm, spend  # noqa: E402
from common import match as m  # noqa: E402

CONFIG = HERE / "config"
PROMPTS = HERE / "prompts" / "shortlist"
SOURCE_DIRS = {s: HERE / s / "config"
               for s in ("hackernews", "discourse", "devto", "github", "reddit")}
RELEVANCE = ("high", "medium", "low")
NONE = "none"
FIELDS = ("problem", "relevance", "article_slug", "reason")

# The article index (ARCHITECTURE.md 5.3) is not built: no Kite Pulse page is
# public yet, so there is nothing a reply may link to. Empty means "no
# linkable page exists", and the prompt tells the model so.
ARTICLES: tuple[dict[str, str], ...] = ()


class ShortlistError(RuntimeError):
    """Config or prompt files are wrong. Nothing was sent."""


# ── settings ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Settings:
    model: str
    max_output_tokens: int
    max_post_chars: int
    max_reason_words: int
    closeness_window_words: int
    set_aside_parent_titles: tuple[str, ...]


def _need(data: Any, key: str) -> Any:
    if not isinstance(data, dict) or key not in data:
        raise ShortlistError(f"shortlist.yaml: missing key {key!r}")
    return data[key]


def _positive(data: Any, key: str) -> int:
    v = _need(data, key)
    if not isinstance(v, int) or isinstance(v, bool) or v < 1:
        raise ShortlistError(f"shortlist.yaml: {key} must be a positive whole number, got {v!r}")
    return v


def load_settings(config_dir: Path = CONFIG) -> Settings:
    data = yaml.safe_load((config_dir / "shortlist.yaml").read_text(encoding="utf-8"))
    model = _need(data, "model")
    if not isinstance(model, str) or not model.strip():
        raise ShortlistError("shortlist.yaml: model must be an OpenRouter model id")
    titles = _need(data, "set_aside_parent_titles")
    if not isinstance(titles, list) or not all(isinstance(t, str) and t.strip() for t in titles):
        raise ShortlistError("shortlist.yaml: set_aside_parent_titles must be a list of text")
    return Settings(
        model=model.strip(),
        max_output_tokens=_positive(data, "max_output_tokens"),
        max_post_chars=_positive(data, "max_post_chars"),
        max_reason_words=_positive(data, "max_reason_words"),
        closeness_window_words=_positive(data, "closeness_window_words"),
        set_aside_parent_titles=tuple(t.strip().lower() for t in titles),
    )


def problems(source: str) -> dict[str, str]:
    """The source's problem keys and descriptions, from its queries.yaml."""
    if source not in SOURCE_DIRS:
        raise ShortlistError(f"no config folder for source {source!r}")
    path = SOURCE_DIRS[source] / "queries.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    out = {}
    for key, body in (data or {}).get("problems", {}).items():
        desc = body.get("description") if isinstance(body, dict) else None
        if not isinstance(desc, str) or not desc.strip():
            raise ShortlistError(f"{path}: problem {key!r} has no description")
        out[key] = desc.strip()
    if not out or NONE in out:
        raise ShortlistError(f"{path}: needs at least one problem, and none may be named {NONE!r}")
    return out


def max_age_days(source: str) -> int:
    return cfg.pace(source, SOURCE_DIRS[source]).max_thread_age_days


# ── the prompt ───────────────────────────────────────────────────────────────

PROMPT_FILES = ("system.md", "user.md", "tool.json")


def prompt_version(folder: Path = PROMPTS) -> str:
    """A hash of the three prompt files: changes whenever any word does."""
    h = hashlib.sha256()
    for name in PROMPT_FILES:
        h.update(name.encode() + b"\0" + (folder / name).read_bytes() + b"\0")
    return h.hexdigest()[:12]


def _fill(template: str, values: dict[str, str], where: str) -> str:
    """Replace {key} placeholders. The template's set and the values' set must
    be the same: a placeholder nobody fills, or a value nobody uses, fails."""
    wanted = set(re.findall(r"\{([a-z_]+)\}", template))
    if wanted != set(values):
        raise ShortlistError(f"{where}: placeholders {sorted(wanted)} but code fills "
                             f"{sorted(values)}")
    for k, v in values.items():
        template = template.replace("{" + k + "}", v)
    return template


def _tool(problem_keys: list[str], slugs: list[str], max_words: int,
          folder: Path = PROMPTS) -> dict[str, Any]:
    raw = (folder / "tool.json").read_text(encoding="utf-8")
    seen: set[str] = set()

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v) for v in node]
        if node == "{problem_keys}":
            seen.add("problem_keys")
            return [*problem_keys, NONE]
        if node == "{article_slugs}":
            seen.add("article_slugs")
            return [*slugs, None]
        if isinstance(node, str) and "{max_reason_words}" in node:
            seen.add("max_reason_words")
            return node.replace("{max_reason_words}", str(max_words))
        if isinstance(node, str) and re.search(r"\{[a-z_]+\}", node):
            raise ShortlistError(f"tool.json: unfilled placeholder in {node!r}")
        return node

    tool = walk(json.loads(raw))
    missing = {"problem_keys", "article_slugs", "max_reason_words"} - seen
    if missing:
        raise ShortlistError(f"tool.json: placeholders never used: {sorted(missing)}")
    return tool


@dataclass(frozen=True)
class Prompt:
    system: str
    user: str
    tool: dict[str, Any]
    post_chars: int          # characters of post text sent, after any cut
    cut: bool


def post_text(th: dict[str, Any]) -> str:
    """What the author wrote. A comment's title is its STORY's title, not theirs."""
    if th["kind"] == "comment":
        return th.get("body") or ""
    return "\n\n".join(x for x in (th.get("title"), th.get("body")) if x)


def build_prompt(th: dict[str, Any], s: Settings, *, folder: Path = PROMPTS) -> Prompt:
    probs = problems(th["source"])
    post = post_text(th)
    cut = len(post) > s.max_post_chars
    if cut:
        post = post[:s.max_post_chars] + f"\n[... cut: the post continues for " \
                                         f"{len(post) - s.max_post_chars} more characters]"
    # The post may contain "<<<POST" / "POST>>>" itself; neutralise the markers
    # so it cannot close the untrusted block early.
    post = post.replace("<<<POST", "<<<post").replace("POST>>>", "post>>>")
    part_of = (f"It is a reply in the thread titled: {th['title']}\n"
               if th["kind"] == "comment" and th.get("title") else "")
    user = _fill((folder / "user.md").read_text(encoding="utf-8"), {
        "problems": "\n".join([*(f"- {k}: {d}" for k, d in probs.items()),
                               f"- {NONE}: none of these"]),
        "articles": "\n".join(f"- {a['slug']}: {a['title']}" for a in ARTICLES)
                    or "(none: no article may be linked yet, so article_slug is null)",
        "source": th["source"], "kind": th["kind"], "community": th["community"],
        "part_of": part_of,
        "post": "\x00POST\x00",          # filled last, below, so braces in it are inert
    }, "user.md")
    user = user.replace("\x00POST\x00", post)
    return Prompt(system=(folder / "system.md").read_text(encoding="utf-8"), user=user,
                  tool=_tool(list(probs), [a["slug"] for a in ARTICLES], s.max_reason_words,
                             folder),
                  post_chars=min(len(post_text(th)), s.max_post_chars), cut=cut)


# ── step 1: code sets aside ──────────────────────────────────────────────────

def set_aside(th: dict[str, Any], s: Settings, *, now: datetime, max_age: int) -> str | None:
    """Why code will not send this thread to the model, or None to send it."""
    if th["created_at"] < now - timedelta(days=max_age):
        return "too_old"
    if th["kind"] == "comment" and any(t in (th.get("title") or "").lower()
                                       for t in s.set_aside_parent_titles):
        return "hiring_thread"
    text = post_text(th)
    spans = [m.span(p, text) for p in th["matched_phrases"]]
    if not any(w is not None and w <= s.closeness_window_words for w in spans):
        return "words_far_apart"
    return None


# ── step 4: code checks the answer ───────────────────────────────────────────

@dataclass(frozen=True)
class Checked:
    outcome: str                         # proposed | invalid
    problem: str | None
    relevance: str | None
    article_slug: str | None
    slug_verified: bool | None
    reason: str | None
    invalid_why: str | None


def _as_text(v: Any) -> str | None:
    if v is None:
        return None
    return (v if isinstance(v, str) else json.dumps(v))[:1000]


def check_answer(answer: llm.Answer, *, problem_keys: list[str], slugs: list[str],
                 max_reason_words: int) -> Checked:
    """Every field against the rules. Kept as given either way; never corrected."""
    a = answer.arguments or {}
    why: list[str] = []
    if answer.arguments is None:
        why.append(answer.problem or "no answer")
    if answer.hit_output_ceiling:
        why.append("stopped at max_output_tokens")
    if answer.arguments is not None:
        extra, missing = set(a) - set(FIELDS), set(FIELDS) - set(a)
        if missing:
            why.append(f"missing {', '.join(sorted(missing))}")
        if extra:
            why.append(f"unexpected {', '.join(sorted(extra))}")
        if "problem" in a and a["problem"] not in [*problem_keys, NONE]:
            why.append(f"problem {a['problem']!r} is not a listed problem")
        if "relevance" in a and a["relevance"] not in RELEVANCE:
            why.append(f"relevance {a['relevance']!r} is not high, medium or low")
        r = a.get("reason")
        if "reason" in a and (not isinstance(r, str) or not r.strip()):
            why.append("reason is empty")
        elif isinstance(r, str) and len(r.split()) > max_reason_words:
            why.append(f"reason is {len(r.split())} words; the limit is {max_reason_words}")
        slug = a.get("article_slug")
        if slug is not None and not isinstance(slug, str):
            why.append("article_slug is not text or null")
    slug = a.get("article_slug")
    return Checked(
        outcome="invalid" if why else "proposed",
        problem=_as_text(a.get("problem")),
        relevance=_as_text(a.get("relevance")),
        article_slug=_as_text(slug),
        # An unknown slug is kept as given and marked unverified, never swapped
        # for a near match (ARCHITECTURE.md 5.2c).
        slug_verified=(slug in slugs) if isinstance(slug, str) else False,
        reason=_as_text(a.get("reason")),
        invalid_why="; ".join(why) or None,
    )


# ── the run ──────────────────────────────────────────────────────────────────

CANDIDATES = """
SELECT id, source, kind, community, url, title, body, created_at, matched_phrases
FROM kp_outreach_thread t
WHERE status = 'found'
  AND NOT EXISTS (SELECT 1 FROM kp_outreach_shortlist s
                  WHERE s.thread_id = t.id AND s.prompt_version = %s)
  {source}
ORDER BY created_at DESC, id DESC
"""

INSERT = """
INSERT INTO kp_outreach_shortlist
  (thread_id, prompt_version, outcome, set_aside_reason, model, spend_id, input_chars,
   problem, relevance, article_slug, slug_verified, reason, invalid_why)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (thread_id, prompt_version) DO NOTHING
"""


@dataclass
class Summary:
    candidates: int = 0
    set_aside: dict[str, int] = field(default_factory=dict)
    proposed: int = 0
    invalid: int = 0
    waiting: int = 0                 # sendable, not sent this run (limit, cap or failure)
    stopped: str | None = None
    usd: list[Any] = field(default_factory=list)   # per call, None = unpriced


def run(conn: Any, client: llm.Client | None, s: Settings, *, limit: int,
        budget: Any, now: datetime | None = None, source: str | None = None,
        dry_run: bool = False, out=print) -> Summary:
    from psycopg.rows import dict_row

    # Each write must commit when its `with conn.transaction()` ends. Without
    # autocommit, any earlier SELECT leaves a transaction open, the block
    # becomes a SAVEPOINT, and a crash later would roll back spend rows for
    # calls that were really paid for.
    if not conn.autocommit:
        raise RuntimeError("shortlist.run needs an autocommit connection")
    now = now or datetime.now(UTC)
    version = prompt_version()
    rows = conn.cursor(row_factory=dict_row).execute(
        CANDIDATES.format(source="AND source = %s" if source else ""),
        (version, source) if source else (version,)).fetchall()
    summary = Summary(candidates=len(rows))
    calls = 0
    for th in rows:
        reason = set_aside(th, s, now=now, max_age=max_age_days(th["source"]))
        if reason:
            summary.set_aside[reason] = summary.set_aside.get(reason, 0) + 1
            if not dry_run:
                with conn.transaction():
                    conn.execute(INSERT, (th["id"], version, "set_aside", reason, None, None,
                                          None, None, None, None, None, None, None))
            continue
        if summary.stopped or calls >= limit:
            summary.waiting += 1
            continue
        prompt = build_prompt(th, s)
        if dry_run:
            if calls == 0:
                out(f"--- the first prompt that would be sent (thread {th['id']}) ---")
                out(prompt.system)
                out(prompt.user)
                out(json.dumps(prompt.tool, indent=1))
                out("--- end of prompt ---")
            calls += 1
            continue
        try:
            spend.check(conn, budget, now)
        except spend.BudgetReached as exc:
            summary.stopped = str(exc)
            summary.waiting += 1
            continue
        try:
            answer = client.call(system=prompt.system, user=prompt.user, tool=prompt.tool,
                                 max_output_tokens=s.max_output_tokens)
        except llm.CallFailed as exc:
            summary.stopped = (f"call for thread {th['id']} failed, run stopped: {exc}. "
                               "Whether it was billed is unknown; nothing was recorded "
                               "for it in kp_outreach_spend")
            summary.waiting += 1
            continue
        calls += 1
        # Money first, in its own transaction: spent is recorded even if what
        # follows fails.
        spend_id = spend.record(conn, step="shortlist", model=answer.model, thread_id=th["id"],
                                input_tokens=answer.input_tokens,
                                output_tokens=answer.output_tokens, usd=answer.usd)
        summary.usd.append(answer.usd)
        probs = list(problems(th["source"]))
        c = check_answer(answer, problem_keys=probs, slugs=[a["slug"] for a in ARTICLES],
                         max_reason_words=s.max_reason_words)
        with conn.transaction():
            conn.execute(INSERT, (th["id"], version, c.outcome, None, answer.model, spend_id,
                                  prompt.post_chars, c.problem, c.relevance, c.article_slug,
                                  c.slug_verified, c.reason, c.invalid_why))
        if c.outcome == "proposed":
            summary.proposed += 1
        else:
            summary.invalid += 1
        cost = "no cost reported" if answer.usd is None else f"${answer.usd:.6f}"
        out(f"  {th['id']:>5} {th['source']:<10} {c.outcome:<8} "
            f"{c.relevance or '-':<6} {c.problem or '-':<22} {cost}"
            + (f"  ({c.invalid_why})" if c.invalid_why else ""))
    if dry_run:
        summary.waiting += calls     # nothing was sent
    return summary


def report(s: Summary, *, dry_run: bool, out=print) -> None:
    out("")
    out(f"threads in To review not yet shortlisted under this prompt: {s.candidates}")
    aside = ", ".join(f"{k} {v}" for k, v in sorted(s.set_aside.items())) or "none"
    out(f"  set aside by code, not sent: {sum(s.set_aside.values())} ({aside})"
        + ("  [dry run: not written]" if dry_run else ""))
    if dry_run:
        out(f"  would go to the model: {s.waiting} (a real run sends at most --limit of them)")
        return
    out(f"  sent to the model: {s.proposed + s.invalid} "
        f"({s.proposed} proposed, {s.invalid} invalid)")
    out(f"  waiting for a later run: {s.waiting}")
    priced = [u for u in s.usd if u is not None]
    if s.usd:
        total = sum(priced)
        line = f"  cost of this run: ${total:.6f} over {len(priced)} priced call(s)"
        if len(priced) < len(s.usd):
            line += f"; {len(s.usd) - len(priced)} call(s) reported no cost, so this is a floor"
        elif priced:
            line += f", ${total / len(priced):.6f} per call"
        out(line)
    if s.stopped:
        out(f"  STOPPED: {s.stopped}")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(prog="shortlist.py", description=__doc__.split("\n")[0])
    p.add_argument("--limit", type=int, required=True,
                   help="the most model calls this run may make (set-asides are free)")
    p.add_argument("--source", choices=sorted(SOURCE_DIRS))
    p.add_argument("--dry-run", action="store_true",
                   help="write nothing, call nothing; print the first prompt and the counts")
    args = p.parse_args(argv)
    if args.limit < 1:
        p.error("--limit must be at least 1")

    from collect.config import settings as load_env  # loads .env; no other collect/ import

    load_env()
    try:
        s = load_settings()
        budget = None if args.dry_run else spend.daily_budget()
        client = None if args.dry_run else llm.OpenRouter.from_env(s.model)
        with db.connect() as conn:
            conn.autocommit = True
            print(f"database {conn.info.dbname}; model {s.model}; prompt {prompt_version()}"
                  + (f"; cap ${budget}/day" if budget else ""))
            summary = run(conn, client, s, limit=args.limit, budget=budget,
                          source=args.source, dry_run=args.dry_run)
    except (ShortlistError, cfg.ConfigError, spend.SpendError, llm.CallFailed,
            db.OutreachDbError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    report(summary, dry_run=args.dry_run)
    return 1 if summary.stopped and "failed" in summary.stopped else 0


if __name__ == "__main__":
    raise SystemExit(main())
