"""Render the HN pull into `articles/deepseek-v4-pro/hackernews-report.md`.

    py -3 scripts/build_hackernews_report.py

The raw pull under `var/hackernews/` is the input; the Markdown report is the
committed source of truth, and `articles/build_data.py` derives the page JSON
from it. Same chain as arXiv: scrape -> report -> build -> page.

THE LABELS IN THIS FILE ARE HAND-ASSIGNED. `LABELS` below is 81 comments read
in full and labelled by content type with a stated reason, exactly as the Reddit
pull hand-read 150 posts. It lives in version control rather than in a notebook
because it is the judgement, and a judgement nobody can diff is not reviewable.
Everything else in the report is counted mechanically from the pull.

Imports nothing from `collect/` or `judge/`. Opens no database.
"""

from __future__ import annotations

import collections
import glob
import json
import pathlib
import sys
from datetime import UTC, datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fetch_hackernews_articles import (  # noqa: E402
    artifacts_of,
    is_comment,
    strip_html,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_MD = ROOT / "articles" / "deepseek-v4-pro" / "hackernews-report.md"

HN = "https://news.ycombinator.com/item?id="

#: objectID -> (content_type, why this label). Read in full, labelled by hand.
#: Two mappings are worth stating because the vocabulary is fixed and the fit is
#: not always obvious:
#:  - `deep_analysis` covers evidenced corrections and original arithmetic - a
#:    price claim checked against the vendor's own pricing page, a margin
#:    derived from published throughput - not only long essays.
#:  - `comparison` is for lining named models up against each other; when the
#:    comparison is the author's own measured run it is `benchmark` instead.
LABELS: dict[str, tuple[str, str]] = {
    # ── 48002136 DeepClaude ────────────────────────────────────────────────
    "48002640": (
        "workflow",
        "The `#!/bin/sh` wrapper itself - exports ANTHROPIC_BASE_URL/AUTH_TOKEN/MODEL to "
        "point Claude Code at DeepSeek. Runnable as posted.",
    ),
    "48003077": (
        "workflow",
        "Same redirect as a single-line env prefix, routed through OpenRouter instead of the "
        "DeepSeek API.",
    ),
    "48004086": (
        "workflow",
        "Model/subagent pairing (`pro[1m]` + Flash) with a week of first-hand use behind it, "
        "and the training-opt-out caveat stated rather than glossed.",
    ),
    "48004484": (
        "usage_demo",
        "Reports which CLI fits the model and a cache-hit rate above 95% for programming "
        "tasks, plus in-context switching between Flash and Pro.",
    ),
    "48005694": (
        "deep_analysis",
        "Corrects the submission's headline price with the vendor's own pricing page and the "
        "dated expiry - the claim is checkable in one click.",
    ),
    "48006241": (
        "deep_analysis",
        "The same price correction plus two further checkable claims: the cheap rate only "
        "exists by passing through to the China-based API, and a first-hand line about which "
        "route the author actually uses.",
    ),
    "48006325": (
        "usage_demo",
        "Names the concrete local-inference state: a fork running Q2 expert layers of Flash "
        "in 128GB RAM without disk offload.",
    ),
    "48012870": (
        "workflow",
        "Shell function with the timeout and small-fast-model settings included, unsetting "
        "the inherited token first.",
    ),
    "48013784": (
        "workflow",
        "The verbatim alias, corrected from the author's own earlier phone-typed version, "
        "with the VPS-isolation reason for running it credential-free.",
    ),
    # ── 48440448 beats GPT-5.5 Pro on precision ────────────────────────────
    "48440796": (
        "benchmark",
        "The author's own vulnerability-scanning benchmark with cost per case: ~$1 for the "
        "whole V4 Pro run against $22/case for GPT-5.5 Pro, and 4-of-9 bugs found tied with "
        "Opus 4.8.",
    ),
    "48441514": (
        "workflow",
        "A working config script to try it for $5, paired with an honest 'not quite as good' "
        "quality caveat.",
    ),
    "48442945": (
        "usage_demo",
        "Extended first-hand report across a spec/test-driven harness: 98.5% input cache-hit "
        "ratio, degradation at 400-500K context, and named porting tasks completed.",
    ),
    "48444400": (
        "comparison",
        "Corrects a cached-price claim with an effective-input-price table for MiMo V2.5 Pro "
        "against V4 Pro Max.",
    ),
    "48444621": (
        "benchmark",
        "Throughput figures against the OpenRouter performance page - sub-2s to first token, "
        "15-50 tps by provider - offered as a correction.",
    ),
    "48452996": (
        "deep_analysis",
        "Small but checkable: the alias in question resolves to V4 Flash with reasoning "
        "disabled, cited to the API docs.",
    ),
    "48488118": (
        "deep_analysis",
        "Cache-read-to-input cost ratios (Pro 0.83%, Flash 2%) sourced to a third-party "
        "write-up, with the ZDR caveat that voids response caching.",
    ),
    # ── 47884971 DeepSeek v4 (launch) ──────────────────────────────────────
    "47885263": (
        "opinion",
        "Frontier-level-at-a-fraction claim with a weights link but no measurement behind it.",
    ),
    "47885574": (
        "usage_demo",
        "Runs the author's standing SVG test on both variants and links four prior "
        "generations for comparison.",
    ),
    "47885649": ("announcement", "The two OpenRouter model pages, nothing more."),
    "47885654": (
        "deep_analysis",
        "Works the streaming-experts memory requirement from the published active-parameter "
        "count: 49B active is ~100GB at 16-bit, ~50GB at 8-bit.",
    ),
    "47885796": ("announcement", "Base-model weights appearing on Hugging Face."),
    "47886609": (
        "announcement",
        "Reproduces the official launch post because the submitted link went to a generic "
        "docs page - parameter counts, context length, tech report and weights.",
    ),
    "47887485": (
        "deep_analysis",
        "Quotes the technical report abstract: 1.6T/49B MoE, CSA+HCA attention, mHC "
        "residuals, Muon optimiser, 32T training tokens.",
    ),
    "47888227": (
        "deep_analysis",
        "Checks the 'runs entirely on Huawei' claim against the tech report, quotes the "
        "fine-grained-EP speedup figures, and flags that the author leaned on the model to "
        "read it.",
    ),
    "47888887": (
        "benchmark",
        "Third-party benchmark placing it outside the top ten, with the confound named: Pro "
        "was rate-limited and timing out during testing.",
    ),
    "47889301": (
        "benchmark",
        "The author's own customer-support benchmark with scores for Flash against two Qwen "
        "sizes and Gemini 3 Flash, and a question about Pro scoring below Flash.",
    ),
    "47891553": ("announcement", "Both variants' weights are MIT-licensed, with links."),
    "47901068": (
        "benchmark",
        "Follow-up after the API issues cleared: the score moved to roughly GLM 5 level.",
    ),
    # ── 47977026 almost on the frontier ────────────────────────────────────
    "47982523": (
        "usage_demo",
        "A layer-by-layer type audit of a TypeScript codebase for $0.09 on Pro, with the Opus "
        "counterfactual estimated from prior experience.",
    ),
    "47985381": (
        "deep_analysis",
        "Identifies the hidden cost: Pro burns 190M reasoning tokens on the AA index against "
        "GPT-5.5-high's 45M, so cheap per token is not cheap per task.",
    ),
    "47986125": (
        "deep_analysis",
        "Efficiency claims from the release paper - 27% of the FLOPs and 10% of the KV cache "
        "of V3.2 - with the author's own local before/after.",
    ),
    "47987685": (
        "benchmark",
        "Their ranking has Flash outperforming Pro, and separates why: Pro is stronger "
        "one-shot, weaker with unfamiliar tools over long horizons.",
    ),
    "47988232": (
        "benchmark",
        "Hallucination rates of 94% (Pro) and 96% (Flash) on the omniscience eval, linked.",
    ),
    "47988728": (
        "usage_demo",
        "A working arm64 compiler port in about half an hour for roughly $8 of API spend, "
        "with the Pro-to-Flash switch and where each model failed.",
    ),
    "47989937": (
        "deep_analysis",
        "Derives a ~202% margin at promotional pricing from DeepSeek's own V3 infra numbers, "
        "NVIDIA's throughput figure and a $7/hr B300.",
    ),
    "47990148": (
        "benchmark",
        "Flash scoring slightly better than Pro in the author's tests, attributed to Flash "
        "reasoning twice as much.",
    ),
    "47990809": (
        "workflow",
        "Multi-model consortium tool with Pro as one member and Flash as judge, with a "
        "rendered output to inspect.",
    ),
    # ── 49274600 V4 Pro 0813 ───────────────────────────────────────────────
    "49275180": (
        "benchmark",
        "The full ten-benchmark table for 0813 against Flash 0731, both Previews, GLM-5.2, "
        "Kimi-K3, Opus-4.8 and Fable 5.",
    ),
    "49275340": (
        "opinion",
        "A speed-for-accuracy preference stated as a feel, with one unattributed percentage.",
    ),
    "49275464": (
        "comparison",
        "Names a concrete task MiMo solved that Flash could not, and points out the AA pages "
        "would not have predicted it.",
    ),
    "49275586": (
        "usage_demo",
        "Full unquantized Flash locally at full 1M context for $8000 of hardware, with the "
        "setup repo linked.",
    ),
    "49275606": (
        "announcement",
        "The pricing page plus the banner notice that Flash pricing rises first, amount "
        "undetermined.",
    ),
    "49275709": (
        "comparison",
        "Benchmark-by-benchmark against Qwen3.8-max released the same day, with each "
        "published figure named and the vision caveat.",
    ),
    "49275775": (
        "deep_analysis",
        "Per-request cost derived from OpenCode's published token split (750 in / 290 out / "
        "82k cached): $0.000875 against $0.052 for Opus.",
    ),
    "49275985": (
        "benchmark",
        "Same feature built twice on Codex CLI: Pro 12m02s at $0.12 with a bug, Grok 4.6 "
        "3m18s at $1.41 without.",
    ),
    "49277160": (
        "deep_analysis",
        "The author's harness cost simulation, with the caveat about which numbers to trust, "
        "concluding Pro beats the Luna models on caching.",
    ),
    "49282465": (
        "opinion",
        "A multilingual-prose complaint about Flash, rated below the author's local Qwen, "
        "with no artifact beyond the comparison.",
    ),
    "49285797": (
        "announcement",
        "The peak/off-peak price table with the exact UTC windows and effective date, plus "
        "the batching implication.",
    ),
    # ── 48237663 price discount permanent ──────────────────────────────────
    "48239072": ("comparison", "Output price per million lined up across six named models."),
    "48241620": (
        "deep_analysis",
        "Reads the caching clause: cache-hit input at 0.8% of input price for Pro, an "
        "effective ~$0.04/M, and notes there is no end date.",
    ),
    "48242980": (
        "usage_demo",
        "First-hand on Pi and Gptel - happy on price, unhappy on speed, with the reasoning "
        "trace called out as unusually transparent.",
    ),
    "48243363": (
        "promo",
        "The author's own coding agent now supports the model. Useful, but it is his project "
        "being advertised.",
    ),
    "48258264": (
        "deep_analysis",
        "Quotes the clause that sets post-promotion pricing at a quarter of the original, "
        "answering a claim in the thread.",
    ),
    "48262042": (
        "benchmark",
        "Cost-to-solve one task across models on OpenRouter, with the result against "
        "expectation: V4 Pro at $2.47 against GPT-5.4's $0.45.",
    ),
    "48262873": (
        "benchmark",
        "Per-task rather than per-token costing from the author's own SQL benchmark: Kimi "
        "K2.5 at double the token price came in at $0.05 against $0.16.",
    ),
    "48263099": (
        "usage_demo",
        "Cache-hit behaviour from integrating the model into his own agent, with the running "
        "total ($1.15 over two weekends). Self-referential but measured.",
    ),
    # ── 48446639 MiMo UltraSpeed ───────────────────────────────────────────
    "48447778": (
        "benchmark",
        "Throughput correction: the fastest Pro providers on OpenRouter are ~50tps, slower "
        "than Opus.",
    ),
    "48450276": (
        "benchmark",
        "Pro fastest of 21 models in the author's runs, published - and the author names the "
        "confound himself, that he may have hit a quiet period.",
    ),
    "48450981": (
        "benchmark",
        "Explains the ranking: Pro struggles with their custom harness so it is down-weighted "
        "on agentic tasks while leading one-shot, and warns about benchmaxxing.",
    ),
    # ── 48311647 Claude Opus 4.8 ───────────────────────────────────────────
    "48313418": (
        "comparison",
        "Third-party hosting against first-party: DeepInfra $1.30/$2.60 at 37 t/s on an FP4 "
        "quant, against DeepSeek's $0.435/$0.87.",
    ),
    "48315040": (
        "comparison",
        "Positions Pro against Sonnet and argues Opus 4.5 is the fairer comparison.",
    ),
    "48318989": (
        "comparison",
        "Fireworks' three-part pricing for the model, called about a third of Sonnet.",
    ),
    # ── 48143284 frontier access ───────────────────────────────────────────
    "48144828": (
        "opinion",
        "The cost collapse as felt rather than measured - $150 of work a year ago now 35 "
        "cents - with no source for either figure.",
    ),
    "48145354": (
        "news_roundup",
        "Points at the NIST CAISI evaluation and its graph, and says plainly that the model "
        "found the link.",
    ),
    "48145833": (
        "usage_demo",
        "Two weeks on an Ollama Cloud subscription without hitting the limits that one Opus "
        "prompt could exhaust.",
    ),
    "48145930": (
        "comparison",
        "Corrects the state of the art in the parent's comparison, naming release dates and "
        "context sizes across four families.",
    ),
    "48146121": (
        "opinion",
        "Argues benchmarks miss domain feel, with a made-up example the author flags as made "
        "up.",
    ),
    # ── 48256953 reasonix ──────────────────────────────────────────────────
    "48261733": (
        "deep_analysis",
        "Real billing dump from the author's own script: 486.3M tokens, 97.27% cache hit, $10 "
        "paid against a $241.79 Sonnet-equivalent.",
    ),
    # ── 48383056 Uber's AI limit ───────────────────────────────────────────
    "48392791": (
        "deep_analysis",
        "Argues Western inference providers set the floor price and that ~$0.80/M was never "
        "intended to be permanent.",
    ),
    "48395242": (
        "deep_analysis",
        "Uses the provider list and a third-party cost analysis to argue the cheap Chinese "
        "prices are closer to true cost than the US API prices.",
    ),
    "48396839": (
        "comparison",
        "Two providers' exact three-part prices side by side, offered to settle a "
        "disagreement.",
    ),
    "48404092": (
        "usage_demo",
        "Substituting Pro at Max reasoning for Opus 4.8 after hitting subscription limits: "
        "passable, with repeated corrections and token waste.",
    ),
    # ── 48809877 margin collapse ───────────────────────────────────────────
    "48811296": (
        "comparison",
        "Places GLM 5.2 above V4 Pro from sustained use, with the subscription quota "
        "arithmetic that made the author reconsider.",
    ),
    "48812660": (
        "comparison",
        "A concrete failure: a Fable-written implementation guide executed by V4 Pro came "
        "back ~80% wrong by Fable's own assessment, where GLM 5.2 did better.",
    ),
    "48813015": (
        "opinion",
        "The commodity-abundance framing, carrying the two published prices as its only "
        "artifact.",
    ),
    # ── 48502347 Kimi K2.7-Code ────────────────────────────────────────────
    "48503533": (
        "workflow",
        "A multi-provider routing recipe with the prices to sign up at and what to send "
        "where.",
    ),
    "48506648": (
        "comparison",
        "Argues DS4 over GLM 5.1 on context window with a benchmark comparison linked.",
    ),
    "48507479": (
        "deep_analysis",
        "Cached-input arithmetic for a real token mix: Kimi K2.7 Code is 53x more expensive "
        "on the 95% of spend that is cached input.",
    ),
    # ── 48709670 GLM 5.2 beats Claude ──────────────────────────────────────
    "48712434": (
        "benchmark",
        "Security bug-hunting benchmark across releases: Pro consistently among the best "
        "while MiMo's early showing did not hold, plus the finding that semgrep-as-a-tool "
        "made models worse.",
    ),
    "48713609": (
        "benchmark",
        "Points at the author's own write-up on how the two models approach security research "
        "differently, with the version caveat stated.",
    ),
    "48714414": (
        "usage_demo",
        "Elixir work across both models with the actual bills - $20/day on GLM via OpenRouter "
        "against $10 lasting six weeks on DeepSeek direct.",
    ),
}

TYPE_ORDER = ["deep_analysis", "benchmark", "usage_demo", "workflow",
              "comparison", "opinion", "announcement", "news_roundup", "promo"]
TYPE_NAME = {
    "deep_analysis": "Deep Analysis", "benchmark": "Benchmark",
    "usage_demo": "Usage Demo", "workflow": "Workflow", "comparison": "Comparison",
    "opinion": "Opinion", "announcement": "Announcement",
    "news_roundup": "News Roundup", "promo": "Promo",
}


def load_pull() -> dict:
    paths = sorted(glob.glob(str(ROOT / "var" / "hackernews" / "hn-*.json")))
    if not paths:
        sys.exit("no pull found under var/hackernews/ - run fetch_hackernews_articles.py first")
    return json.load(open(paths[-1], encoding="utf-8"))


def main() -> None:
    d = load_pull()
    recs = d["records"]
    matched_ids = d["matched_ids"]
    matched = [recs[i] for i in matched_ids]
    comments = [r for r in matched if is_comment(r)]
    stories = [r for r in matched if not is_comment(r)]

    def arts(r: dict) -> list[str]:
        return artifacts_of(strip_html(r.get("comment_text") or r.get("story_text")),
                            r.get("comment_text") or r.get("story_text"))

    art_of = {r["objectID"]: arts(r) for r in comments}
    art_kinds = collections.Counter(a for v in art_of.values() for a in v)
    art_n = collections.Counter(len(v) for v in art_of.values())

    by_thread: dict[str, list[dict]] = collections.defaultdict(list)
    for r in comments:
        by_thread[str(r.get("story_id"))].append(r)

    threads = []
    for sid, cs in by_thread.items():
        t = d["threads"].get(sid) or {}
        st = t.get("story") or {}
        cs.sort(key=lambda c: c.get("created_at_i") or 0)
        threads.append({
            "sid": sid,
            "title": st.get("title") or cs[0].get("story_title") or "(unknown)",
            "url": st.get("url"),
            "points": st.get("points") or 0,
            "num_comments": st.get("num_comments") or 0,
            "fetched": len(t.get("comments") or []),
            "date": (st.get("created_at") or cs[0].get("created_at") or "")[:10],
            "matched": cs,
            "authors": len({c.get("author") for c in cs if c.get("author")}),
            "with_artifact": sum(1 for c in cs if art_of[c["objectID"]]),
            "labelled": sum(1 for c in cs if c["objectID"] in LABELS),
        })
    threads.sort(key=lambda t: (-len(t["matched"]), -t["points"]))
    full = [t for t in threads if t["labelled"]]

    labelled_types = collections.Counter(LABELS[c["objectID"]][0]
                                         for t in threads for c in t["matched"]
                                         if c["objectID"] in LABELS)
    dates = sorted((c.get("created_at") or "")[:10] for c in comments if c.get("created_at"))
    months = collections.Counter(x[:7] for x in dates)
    authors_all = {c.get("author") for c in comments if c.get("author")}

    L: list[str] = []
    A = L.append

    A("# DeepSeek V4 Pro — Hacker News data pull\n")
    A("A sweep of Hacker News for substantive discussion of the language model "
      "**DeepSeek V4 Pro**, run over the Algolia HN Search API. Comments are "
      "included alongside stories and are the point of the exercise: on this "
      "platform, for this model, the evidence is in the replies.\n")
    A("> **One-off research pull, contained by design.** Nothing was written to any "
      "database. Nothing was imported from `collect/` or `judge/`. The raw pull lives "
      "under `var/hackernews/` (gitignored); this report is the committed artifact. "
      "See §9 *Method and containment* — including why this data is **not** admissible "
      "to the pipeline as it stands.\n")

    # ── 1 ──
    A("## 1. Run metadata\n")
    st = d["stats"]
    n_rec, n_hit = st["records_returned"], st["literal_pro_matches"]
    n_com, n_thr = st["literal_pro_comments"], st["threads_followed"]
    A("| Field | Value |")
    A("|---|---|")
    A(f"| Report generated | {datetime.now(UTC).isoformat(timespec='seconds')} |")
    A(f"| Pull fetched at | {d['fetched_at']} |")
    A("| Route | `scripts/fetch_hackernews_articles.py` — standalone, no `collect/` import |")
    A(f"| API | Algolia HN Search — `{d['api']}` |")
    A("| Endpoints | `/search`, `/search_by_date`, `/search_by_date?tags=comment,story_<id>` |")
    A(f"| Auth | {d['auth']} |")
    w = d["window"]
    A(f"| Window requested | {w['from']} → {w['to']} ({w['months']} months) |")
    kws = ", ".join("`" + k + "`" for k in d["keywords"])
    A(f"| Keyword surfaces | {len(d['keywords'])} — {kws} |")
    A(f"| Queries | {st['queries']} (each keyword × both ranking endpoints) |")
    A(f"| Total API calls | {st['api_calls']} |")
    A(f"| Windows bisected | {st['bisections']} (see §2.3) |")
    A(f"| Records returned | {st['records_returned']} |")
    A(f"| **Literal matches** | **{n_hit}** "
      f"({n_com} comments, {len(stories)} stories) |")
    A(f"| Threads followed | {st['threads_followed']} |")
    A(f"| Comments hand-read and labelled | {len(LABELS)} |")
    A("| Terms ruling | **none exists** for Algolia/HN in `contract/sources.yaml`. "
      "The gate was not invoked because this does not route through `collect/`. "
      "See §9.1 |")
    A("")

    # ── 2 ──
    A("## 2. What the queries returned\n")
    A("### 2.1 Per query, with the denominator\n")
    A("`returned` is what Algolia handed back for that query; `literal` is how many "
      "of those actually contain the model's name once matched locally. The gap is "
      "the API's, not the corpus's — see §2.2.\n")
    A("| Keyword | Endpoint | Returned | Literal | Literal share |")
    A("|---|---|---|---|---|")
    for q in d["per_query"]:
        share = f"{100 * q['literal_pro_matches'] / q['returned']:.0f}%" if q["returned"] else "—"
        A(f"| `{q['keyword']}` | `{q['endpoint']}` | {q['returned']} | "
          f"{q['literal_pro_matches']} | {share} |")
    A("")
    A(f"After union and dedup across all {st['queries']} queries: "
      f"**{n_rec} distinct records, {n_hit} literal matches "
      f"({100 * n_hit / n_rec:.0f}%).**\n")

    A("### 2.2 Algolia prefix-matches query tokens, so raw hit counts are not match counts\n")
    A("The index matches a trailing token as a prefix. A query for `deepseek v4 pro` "
      "therefore matches *problem*, *production* and every unrelated `Pro`-suffixed "
      "model name. Nothing in the response marks these as weak hits.\n")
    A("Every record is consequently re-verified in this repo against "
      "`deepseek[\\s\\-_]*v?4[\\s\\-_]*pro(?:[\\s\\-_]*\\d{3,4})?` over title, story "
      "title, URL and body before it counts as a match. **The unverified count would "
      f"have been {st['records_returned']}; the verified count is {st['literal_pro_matches']}.**\n")

    A("### 2.3 The API silently truncates at 1000 hits\n")
    A("Pagination is capped at 1000 records per query. A query whose `nbHits` is 2000 "
      "still returns `nbPages: 1` and hands back 1000 records with no error field, so "
      "a naive fetch is short and looks complete. Any window reporting at or above the "
      f"cap is bisected by `created_at_i` until it is under — **{st['bisections']} "
      "bisections** in this run.\n")
    A("**The union landing on exactly 2000 looked like a cap artifact, so it was checked "
      "rather than assumed.** Re-walking the broadest query's bisection tree and summing "
      "each leaf window's own `nbHits` gives **1997**, with no leaf sitting at the cap. "
      "Were the true corpus larger than the reported 2000, the leaf sum would exceed it. "
      "So the round number is the corpus, not a ceiling; the 3-record difference is "
      "boundary effects across split windows.\n")
    A("One residual hole is worth naming: the bisection stops at a one-hour floor, so a "
      "single hour containing 1000+ matching records would still truncate silently. No "
      "window in this run came close, but the guard has a bottom.\n")

    # ── 3 ──
    A("## 3. Headline numbers\n")
    A("| Figure | Value | Denominator |")
    A("|---|---|---|")
    A(f"| Literal matches | {n_hit} | of {n_rec} records returned |")
    A(f"| Comments | {len(comments)} | of {st['literal_pro_matches']} matches |")
    A(f"| Stories | {len(stories)} | of {st['literal_pro_matches']} matches |")
    A(f"| Distinct comment authors | {len(authors_all)} | "
      f"across {len(comments)} matched comments |")
    A(f"| Threads containing a match | {len(threads)} | "
      f"of {n_thr} threads followed |")
    n3 = sum(1 for t in threads if len(t["matched"]) >= 3)
    A(f"| Threads with 3+ matched comments | {n3} | of {len(threads)} |")
    A(f"| Comments hand-labelled | {len(LABELS)} | of {len(comments)} matched comments |")
    A(f"| Date range of matches | {dates[0]} → {dates[-1]} | — |")
    A("")
    A("**The comment/story split is the finding.** "
      f"{100 * len(comments) // st['literal_pro_matches']}% of matches are comments, not "
      "submissions. A stories-only fetch — the default shape for a platform sweep — "
      f"would have returned {len(stories)} items and lost everything below.\n")
    A("Matches by month:\n")
    A("| Month | Matched comments |")
    A("|---|---|")
    for m, n in sorted(months.items()):
        A(f"| {m} | {n} |")
    A("")

    # ── 4 ──
    A("## 4. Artifacts — what separates a checkable claim from an opinion\n")
    A("Post length does not separate them. The comment this pull was commissioned "
      "around ([48006241](" + HN + "48006241)) is four sentences, and it carries a quoted "
      "price, the vendor's pricing URL, a dated expiry, a routing claim and a "
      "first-hand line. Meanwhile long comments in the same threads carry nothing a "
      "reader can check.\n")
    A("So each matched comment is tested for four artifacts, each independently "
      "falsifiable by a reader: a **link** resolves or 404s, a **number** is right or "
      "wrong, a **version** string names a build that shipped or did not, **code** runs "
      "or does not.\n")
    A(f"| Artifact | Comments carrying it | of {len(comments)} matched |")
    A("|---|---|---|")
    for k in ("link", "number", "version", "code"):
        n = art_kinds.get(k, 0)
        A(f"| `{k}` | {n} | {100 * n / len(comments):.0f}% |")
    A("")
    A(f"| Artifacts per comment | Comments | of {len(comments)} |")
    A("|---|---|---|")
    for k in sorted(art_n):
        A(f"| {k} | {art_n[k]} | {100 * art_n[k] / len(comments):.0f}% |")
    A("")
    n_bare = art_n.get(0, 0)
    A(f"**{n_bare} matched comments ({100 * n_bare / len(comments):.0f}%) carry no "
      "artifact at all** — that is the discrimination the column buys. It is not the "
      "same axis as content type: an `opinion` can carry a link and a `benchmark` can "
      "carry none.\n")
    A("### 4.1 Two detector corrections worth recording\n")
    A("Both of these produced a confident wrong number first, and both are the kind "
      "that survives review because the output looks plausible.\n")
    A("- **`version` fired on 601 of 623 comments (96%) in the first pass**, because "
      "the detector counted `v4 pro` — the keyword every matched comment contains by "
      "construction. A figure that is 96% by definition measures the query, not the "
      "comment. The model's own surface is now stripped before the test, and `version` "
      f"means *a different build named*: a dated build (0813/0731) or a rival's version. "
      f"It now stands at {art_kinds.get('version', 0)}.")
    A("- **`code` found 2 blocks in the whole corpus in the first pass**, because it ran "
      "after HTML stripping and Algolia returns comment bodies with `<pre><code>` "
      "intact. It is now tested against the raw HTML and finds "
      f"{art_kinds.get('code', 0)} — including the `#!/bin/sh` block in the DeepClaude "
      "thread that prompted this fetch, which the first pass missed.\n")

    # ── 5 ──
    A("## 5. Content type\n")
    A(f"Content type is **hand-assigned**, on {len(LABELS)} comments read in full — "
      f"{100 * len(LABELS) / len(comments):.0f}% of the {len(comments)} matched comments. "
      "The rest are counted, indexed and left unlabelled rather than guessed; §8 lists "
      "them with their mechanically-detected artifacts and no content type.\n")
    A("| Content type | Labelled comments |")
    A("|---|---|")
    for t in TYPE_ORDER:
        if labelled_types.get(t):
            A(f"| {TYPE_NAME[t]} | {labelled_types[t]} |")
    A(f"| **Total** | **{sum(labelled_types.values())}** |")
    A("")
    A("Two mappings, stated because the vocabulary is fixed and the fit is not always "
      "obvious. **`deep_analysis`** covers evidenced corrections and original "
      "arithmetic, not only long essays — a price claim checked against the vendor's "
      "own pricing page is a deep-analysis item at four sentences. **`comparison`** is "
      "for lining named models up against each other; where the comparison is the "
      "author's own measured run it is filed as **`benchmark`** instead.\n")
    A("The labelling set was chosen as: matched comments carrying **two or more** "
      f"artifact kinds, within the {len(full)} threads holding the most matches. That is a "
      "stated selection rule, not a quality claim about the remainder — a one-artifact "
      "comment can be excellent and several are.\n")

    # ── 6 ──
    A("## 6. Threads\n")
    A(f"All {len(threads)} threads containing at least one matched comment are indexed in "
      f"§7. The {len(full)} below are the ones whose matched comments were read and "
      "labelled, in full.\n")
    for i, t in enumerate(full, 1):
        A(f"### 6.{i} {t['title']}\n")
        A(f"**Thread** [{t['sid']}]({HN}{t['sid']}) · {t['points']} points · "
          f"{t['num_comments']} comments ({t['fetched']} fetched) · {t['date']}  ")
        A(f"*{len(t['matched'])} matched comments · {t['authors']} distinct authors · "
          f"{t['with_artifact']} of {len(t['matched'])} carry an artifact · "
          f"{t['labelled']} labelled below*\n")
        n = 0
        for c in t["matched"]:
            oid = c["objectID"]
            if oid not in LABELS:
                continue
            n += 1
            ctype, why = LABELS[oid]
            a = art_of[oid]
            body = strip_html(c.get("comment_text"))
            body = " ".join(body.split())
            if len(body) > 900:
                body = body[:900].rstrip() + "…"
            A(f"**{n}. {c.get('author')}** · [{oid}]({HN}{oid}) · "
              f"{(c.get('created_at') or '')[:10]} · `{ctype}` · "
              f"artifacts: {', '.join('`' + x + '`' for x in a) if a else '`none`'}  ")
            A(f"> **Why this label:** {why}\n")
            A(f"> {body}\n")

    # ── 7 ──
    A("## 7. Every thread containing a match\n")
    A(f"All {len(threads)} of them, most-matched first. `matched` counts comments "
      "carrying the model's name; `comments` is the thread's own size, so the ratio is "
      "visible. A thread appears here because a comment in it matched, which does not "
      "make the thread about the model.\n")
    A("| Thread | Date | Pts | Comments | Fetched | Matched | Authors | With artifact |")
    A("|---|---|---|---|---|---|---|---|")
    for t in threads:
        title = t["title"].replace("|", "\\|")
        A(f"| [{title[:64]}]({HN}{t['sid']}) | {t['date']} | {t['points']} | "
          f"{t['num_comments']} | {t['fetched']} | {len(t['matched'])} | {t['authors']} | "
          f"{t['with_artifact']} |")
    A("")

    # ── 8 ──
    A("## 8. Full index of matched comments\n")
    A(f"All {len(comments)} of them. `type` is filled only where the comment was "
      "hand-read; `—` means unlabelled, not unclassifiable. Artifacts are mechanical "
      "and present for every row.\n")
    A("| Comment | Author | Date | Thread | Type | Artifacts |")
    A("|---|---|---|---|---|---|")
    for c in sorted(comments, key=lambda c: -(c.get("created_at_i") or 0)):
        oid = c["objectID"]
        ctype = LABELS[oid][0] if oid in LABELS else "—"
        a = art_of[oid]
        ttl = (c.get("story_title") or "").replace("|", "\\|")[:44]
        A(f"| [{oid}]({HN}{oid}) | {c.get('author')} | {(c.get('created_at') or '')[:10]} | "
          f"{ttl} | {ctype} | {', '.join(a) if a else '—'} |")
    A("")

    # ── 9 ──
    A("## 9. Method and containment, and what these numbers do not mean\n")
    A("### 9.1 Containment, and the ruling that does not exist\n")
    A("- The fetcher imports nothing from `collect/` or `judge/`, opens no database "
      "connection, and writes only to `var/hackernews/` (gitignored) and this report. "
      "The containment is the same as the arXiv path's and it is deliberate: an "
      "unverified scrape must not be able to reach `document`, `claim` or `cell`.")
    A("- **Consequence, stated rather than worked around:** because this does not route "
      "through `harvester_for_source()`, the `assert_terms_reviewed()` gate did not run. "
      "`contract/sources.yaml` carries no `terms_ruling` for Algolia or Hacker News at "
      "all — not a failed one, an absent one. **This data is therefore publishable on "
      "the Articles page and is not admissible to the pipeline.** Feeding it to "
      "`collect/` requires writing that ruling first, with a basis and an expiry, the "
      "way `reddit-via-rapidapi` was written.")
    A("- The API is public and unauthenticated. No credentials were created or used, so "
      "no key is at risk in this path.\n")
    A("### 9.2 The sample is retrieval-shaped, not representative\n")
    A("- These are the records **our five keyword surfaces and two ranking endpoints "
      "returned**, deduped. A different keyword set returns a different corpus. Nothing "
      "here supports a claim about what HN as a whole thinks.")
    A("- `/search` ranks by relevance and `/search_by_date` by recency. Both were run "
      "and unioned precisely because either alone is a biased slice, but the union is "
      "still a slice.")
    A("- Thread-following is **triggered by a match**, so a thread with substantial "
      "discussion that never spells the model's name is absent. This is a known and "
      "material gap: inside a thread already titled about the model, commenters write "
      "*V4 Pro*, *DS4* or *it*, and none of those match. The per-thread `matched` against "
      "`comments` columns in §7 make the size of the gap visible rather than hiding it — "
      f"in the DeepClaude thread it is {len(full[0]['matched']) if full else 0} of "
      f"{full[0]['num_comments'] if full else 0}.\n")
    A("### 9.3 The figures in these comments are theirs, not ours\n")
    A("- Every price, token count, benchmark score and throughput number quoted in §6 is "
      "**the commenter's own claim, reproduced**. None has been re-run or verified here. "
      "The artifact column says a claim is *checkable*; it does not say it is *checked*.")
    A("- Several are contradicted inside the same corpus, and the contradictions are kept "
      "rather than resolved — one commenter measures Pro as the fastest of 21 models, "
      "another measures the fastest providers at ~50tps and slower than Opus. Both are "
      "in §6.\n")
    A("### 9.4 Points and comment counts are read at fetch time\n")
    A("- HN scores drift. Every figure is as of the fetch timestamp in §1, not as of "
      "posting, and a re-run will differ.")
    A("- `fetched` is below `comments` on several threads. Algolia does not return "
      "deleted or dead comments, and on the largest threads its 1000-record cap applies "
      "to the comment listing too. Both are retrieval properties, not findings about "
      "the discussion.\n")
    A("### 9.5 Reproducing this\n")
    A("```\npy -3 scripts/fetch_hackernews_articles.py     # -> var/hackernews/hn-*.json\n"
      "py -3 scripts/build_hackernews_report.py      # -> this file\n"
      "py -3 articles/build_data.py                  # -> web/src/data/*.json\n```\n")
    A("The pull is timestamped and kept, so the report and the page JSON can both be "
      "rebuilt from it without re-fetching. Hand labels live in `LABELS` in "
      "`scripts/build_hackernews_report.py`.")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{OUT_MD.relative_to(ROOT)}: {len(comments)} matched comments, "
          f"{len(LABELS)} labelled, {len(threads)} threads, {len(full)} written in full")


if __name__ == "__main__":
    main()
