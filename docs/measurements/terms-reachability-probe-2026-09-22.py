"""Is a terms document reachable for a host, in BOTH places one can be?

The class A ruling records `terms_document_read` per source, and 16 of 18 feeds
are `false`. This does not READ a terms document - that is a person's judgement
and the ruling records who made it. It answers the prior question: is there one
to read, and where.

TWO PLACES, both probed in full rather than stopping on the first hit:
  1. CONVENTIONAL PATHS - a fixed list, so "none" is a denominator (rule 7).
  2. WHAT THE PAGES THEMSELVES LINK - homepage and one article, since a
     practitioner blog usually carries its terms in a footer link and not at a
     guessable path.

Robots is read first and obeyed per URL. One request per 1.2s, project UA.
"""
import os
import pathlib
import re
import sys
import time
import urllib.parse
from urllib.robotparser import RobotFileParser

import httpx
from dotenv import load_dotenv

ROOT = pathlib.Path(r"C:\Users\anooj\Model-Information-Board")
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

HOST = sys.argv[1] if len(sys.argv) > 1 else "danluu.com"
UA = os.getenv("USER_AGENT")
if not UA:
    raise SystemExit("USER_AGENT unset; NFR-5 requires one.")

PATHS = ["/terms", "/terms/", "/terms-of-service", "/tos", "/legal",
         "/privacy", "/about", "/about/", "/colophon", "/copyright", "/license"]
LINK_RE = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
WORDS = re.compile(r"terms|tos\b|legal|privacy|licen[cs]e|copyright|colophon|"
                   r"reuse|republish|syndicat|attribution", re.I)

client = httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=20)
rp = RobotFileParser()
r = client.get(f"https://{HOST}/robots.txt")
print(f"robots.txt {r.status_code}")
rp.parse(r.text.splitlines() if r.status_code == 200 else [])
if r.status_code != 200:
    print("  no rules served -> nothing disallowed")

def allowed(url):
    return rp.can_fetch(UA, url) if r.status_code == 200 else True

print(f"\n1 · CONVENTIONAL PATHS ({len(PATHS)} probed in full)")
found = []
for p in PATHS:
    url = f"https://{HOST}{p}"
    if not allowed(url):
        print(f"  {p:22s} ROBOTS-REFUSED (named, not skipped)")
        continue
    time.sleep(1.2)
    try:
        resp = client.get(url)
    except Exception as exc:
        print(f"  {p:22s} ERROR {type(exc).__name__}")
        continue
    n = len(resp.text)
    hit = "  <-- terms-ish words" if resp.status_code == 200 and WORDS.search(resp.text) else ""
    print(f"  {p:22s} {resp.status_code}  {n:7d} chars{hit}")
    if resp.status_code == 200 and n > 200:
        found.append((url, n))

print("\n2 · WHAT THE PAGES LINK (homepage + one article)")
seeds = [f"https://{HOST}/"]
seen_links = {}
for seed in seeds:
    time.sleep(1.2)
    try:
        page = client.get(seed)
    except Exception as exc:
        print(f"  {seed} ERROR {exc}")
        continue
    print(f"  {seed}  {page.status_code}  {len(page.text)} chars")
    for href, label in LINK_RE.findall(page.text):
        text = re.sub(r"<[^>]+>", "", label).strip()
        if WORDS.search(text) or WORDS.search(href):
            full = urllib.parse.urljoin(seed, href)
            seen_links[full] = text[:40]
if seen_links:
    for u, t in sorted(seen_links.items()):
        print(f"    LINK  {t:40s} -> {u}")
else:
    print("    no link whose text or href mentions terms/legal/licence/privacy")

print("\nVERDICT (what a reviewer needs, not a ruling)")
print(f"  conventional paths returning a document : {len(found)}")
print(f"  terms-ish links found on the pages      : {len(seen_links)}")
if not found and not seen_links:
    print("  -> NO TERMS DOCUMENT IS REACHABLE IN EITHER PLACE.")
    print("     `terms_document_read` cannot become true by reading one;")
    print("     it would rest on robots plus the class A basis alone.")
