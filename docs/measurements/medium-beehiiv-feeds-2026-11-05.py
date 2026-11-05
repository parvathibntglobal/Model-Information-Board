"""Candidate Medium and beehiiv feeds: which ones carry model evidence.

READ-ONLY AND STORES NOTHING. For each candidate: its host's robots.txt, then
its feed. A beehiiv candidate with no known feed URL has its homepage read once,
only to find a feed link in the markup. No article page is requested.

WHAT EACH FIGURE COUNTS, AND OVER WHAT

    entries               the items the feed served on the day. Medium serves
                          the latest 10, beehiiv the latest 20, so every rate
                          below is over THAT window, never over the publication.
    names_a_model_family  entries whose title or body names one of 13 model
                          families (GPT, Claude, Gemini, Llama, Qwen, DeepSeek,
                          Mistral, Grok, Kimi, GLM, MiniMax, Gemma, Phi),
                          case-sensitive whole word. The measure the seated
                          newsletter rows use (contract/sources.yaml, 2026-10-26).
                          A mention, not a first-hand report: extraction decides
                          that.
    stubs_or_short        bodies under 600 characters, or carrying Medium's
                          "Continue reading on" cut. A members-only Medium post
                          arrives this way.
    median_body_chars     after stripping markup.

    python docs/measurements/medium-beehiiv-feeds-2026-11-05.py OUT.json

TWO RUNS ON 2026-11-05, from a developer machine with the identifying
User-Agent, and both outputs are kept:

    .run1.out.json   ended 14:43 IST. Every candidate answered except three timeouts.
                     The figures in docs/proposals/seat-medium-and-beehiiv-feeds.md
                     come from this run. It was made by an earlier copy of this
                     script that differed only in catching every exception and
                     not writing a `platform` field; the measures are identical.
    .run2.out.json   ended about 15:00 IST, this file as committed. Medium answered 503
                     or 504 for 16 of its 32 feeds, the two seated controls among
                     them. The same feeds answered 200 fifteen minutes earlier, so this
                     reads as throttling, not as 16 dead feeds.
"""
import datetime as dt
import json
import re
import statistics
import sys
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import httpx

UA = "ModelInformationBoard/1.0 (+https://github.com/parvathibntglobal/Model-Information-Board)"
FAM = ["GPT", "Claude", "Gemini", "Llama", "Qwen", "DeepSeek", "Mistral", "Grok", "Kimi", "GLM",
       "MiniMax", "Gemma", "Phi"]
PAT = re.compile(r"\b(" + "|".join(FAM) + r")\b")
TODAY = dt.datetime(2026, 11, 5, tzinfo=dt.UTC)
C = "{http://purl.org/rss/1.0/modules/content/}encoded"
DC = "{http://purl.org/dc/elements/1.1/}creator"
A = "{http://www.w3.org/2005/Atom}"

MEDIUM = {
    # The five contract/sources.yaml named on 2026-08-14 as "the first
    # candidates to add".
    "instacart": "https://tech.instacart.com/feed",
    "pinterest-engineering": "https://medium.com/feed/pinterest-engineering",
    "expedia-group-tech": "https://medium.com/feed/expedia-group-tech",
    "lyft": "https://eng.lyft.com/feed",
    "faire": "https://craft.faire.com/feed",
    # Other engineering blogs on Medium.
    "walmartglobaltech": "https://medium.com/feed/walmartglobaltech",
    "paypal-tech": "https://medium.com/feed/paypal-tech",
    "zillow-tech-hub": "https://medium.com/feed/zillow-tech-hub",
    "udemy-engineering": "https://medium.com/feed/udemy-engineering",
    "booking": "https://medium.com/feed/booking-com-development",
    "swiggy-bytes": "https://bytes.swiggy.com/feed",
    "myntra": "https://medium.com/feed/myntra-engineering",
    "razorpay": "https://engineering.razorpay.com/feed",
    "miro-engineering": "https://medium.com/feed/miro-engineering",
    "wise-engineering": "https://medium.com/feed/wise-engineering",
    "disney-streaming": "https://medium.com/feed/disney-streaming",
    "strava-engineering": "https://medium.com/feed/strava-engineering",
    # AI and developer publications on Medium.
    "google-cloud": "https://medium.com/feed/google-cloud",
    "google-developer-experts": "https://medium.com/feed/google-developer-experts",
    "neo4j": "https://medium.com/feed/neo4j",
    "data-science-collective": "https://medium.com/feed/data-science-collective",
    "gitconnected": "https://medium.com/feed/gitconnected",
    "the-ai-forum": "https://medium.com/feed/the-ai-forum",
    "ai-advances": "https://medium.com/feed/ai-advances",
    "generative-ai": "https://medium.com/feed/generative-ai",
    "llamaindex-blog": "https://medium.com/feed/llamaindex-blog",
    "mongodb": "https://medium.com/feed/mongodb",
    "thedeephub": "https://medium.com/feed/thedeephub",
    "towards-data-science": "https://medium.com/feed/towards-data-science",
    "better-programming": "https://medium.com/feed/better-programming",
    # Seated, as controls.
    "airbnb-engineering (seated)": "https://medium.com/feed/airbnb-engineering",
    "netflixtechblog (seated)": "https://netflixtechblog.com/feed",
}

# beehiiv feeds live at rss.beehiiv.com/feeds/<id>.xml and are opt-in per
# publication, so the URL cannot be guessed: the homepage markup is the only
# place a feed link can be found.
BEEHIIV_FEEDS = {"theneurondaily (seated)": "https://rss.beehiiv.com/feeds/N4eCstxvgX.xml"}
BEEHIIV_HOMES = {
    "aibreakfast": "https://aibreakfast.beehiiv.com/",
    "mindstream": "https://www.mindstream.news/",
    "thedeepview": "https://www.thedeepview.com/",
    "turingpost": "https://www.turingpost.com/",
    "unwindai": "https://www.theunwindai.com/",
    "theaivalley": "https://www.theaivalley.com/",
    "aitoolreport": "https://www.aitoolreport.com/",
    "aifire": "https://www.aifire.co/",
    "thecode": "https://www.thecode.ai/",
    "notabot": "https://www.notabot.news/",
    "neatprompts": "https://www.neatprompts.com/",
    "therundown (rejected 2026-10-26)": "https://www.therundown.ai/",
    "superhuman (rejected 2026-10-26)": "https://www.superhuman.ai/",
    "aiagentsimplified": "https://aiagentsimplified.beehiiv.com/",
}

cli = httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=25)


def strip(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h or "")).strip()


def robots_ok(url):
    p = urlparse(url)
    r = cli.get(f"{p.scheme}://{p.netloc}/robots.txt")
    if r.status_code != 200:
        return r.status_code, r.status_code == 404
    rp = robotparser.RobotFileParser()
    rp.parse(r.text.splitlines())
    return r.status_code, rp.can_fetch(UA, url)


def discover(home):
    st, ok = robots_ok(home)
    if not ok:
        return None, f"robots {st} refuses homepage"
    r = cli.get(home)
    for tag in re.findall(r'<link[^>]+type="application/(?:rss|atom)\+xml"[^>]*>', r.text):
        h = re.search(r'href="([^"]+)"', tag)
        if h:
            return urljoin(str(r.url), h.group(1).replace("&amp;", "&")), None
    plat = "beehiiv" if "beehiiv" in r.text else "?"
    return None, f"no feed link in homepage markup (page {r.status_code}, platform marker {plat})"


def parse_date(d):
    if not d:
        return None
    try:
        if "," in d:
            return parsedate_to_datetime(d)
        return dt.datetime.fromisoformat(d.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def probe(name, url, home=None):
    out = {"name": name}
    if url is None:
        url, why = discover(home)
        if url is None:
            out["error"] = why
            return out
    out["feed"] = url
    st, ok = robots_ok(url)
    out["robots_http"], out["feed_allowed"] = st, ok
    if not ok:
        out["error"] = "robots refuses feed"
        return out
    r = cli.get(url)
    out["http"], out["final"] = r.status_code, str(r.url)
    if r.status_code != 200:
        out["error"] = f"feed {r.status_code}"
        return out
    try:
        root = ET.fromstring(r.content)
    except ET.ParseError:
        out["error"] = f"not XML ({r.headers.get('content-type')})"
        return out
    out["generator"] = root.findtext("channel/generator") or root.findtext(f"{A}generator")
    items = root.findall("channel/item") or root.findall(f"{A}entry")
    bodies, dates, names, bylines, stubs = [], [], 0, set(), 0
    for it in items:
        title = it.findtext("title") or it.findtext(f"{A}title") or ""
        body = (it.findtext(C) or it.findtext(f"{A}content") or it.findtext("description")
                or it.findtext(f"{A}summary") or "")
        txt = strip(body)
        bodies.append(len(txt))
        if re.search(r"Continue reading on|Read more on Medium", txt) or len(txt) < 600:
            stubs += 1
        if PAT.search(title + " " + txt):
            names += 1
        d = parse_date(it.findtext("pubDate") or it.findtext(f"{A}published")
                       or it.findtext(f"{A}updated"))
        if d:
            dates.append(d if d.tzinfo else d.replace(tzinfo=dt.UTC))
        by = it.findtext(DC) or it.findtext(f"{A}author/{A}name")
        if by:
            bylines.add(by.strip())
    out.update(entries=len(items), dated=len(dates), names_a_model_family=names,
               median_body_chars=int(statistics.median(bodies)) if bodies else 0,
               stubs_or_short=stubs,
               newest=max(dates).date().isoformat() if dates else None,
               oldest=min(dates).date().isoformat() if dates else None,
               days_since_newest=(TODAY - max(dates)).days if dates else None,
               distinct_bylines=len(bylines))
    return out


def main(path):
    cands = ([("medium", n, u, None) for n, u in MEDIUM.items()]
             + [("beehiiv", n, u, None) for n, u in BEEHIIV_FEEDS.items()]
             + [("beehiiv", n, None, h) for n, h in BEEHIIV_HOMES.items()])
    res = []
    for platform, name, url, home in cands:
        try:
            row = probe(name, url, home)
        except httpx.HTTPError as e:
            row = {"name": name, "error": f"{type(e).__name__}: {e}"[:160]}
        row["platform"] = platform
        res.append(row)
        print(json.dumps(row, ensure_ascii=True), flush=True)
        time.sleep(1)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1])
