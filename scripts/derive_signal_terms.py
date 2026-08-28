"""What the unselected near-misses say. Read-only, no model call, no writes.

A NEAR-MISS is a document where the subject group hits, the topic group hits,
and the signal group does not — and where NO entry passed. That last clause
matters: a document already yielding a claim is not material for deriving terms
we lack, and counting it inflated an earlier figure from 123 to 126.

WHAT THIS IS FOR, AND WHAT IT DID NOT PRODUCE

`contract/queries.yaml` carries 207 signal terms of which 101 fire on neither
platform, and one stem (`truncat`) supplies 34.2% of all GitHub firings. Adding
terms one at a time is how it got that way, so the intent here is to derive them
from what engineers actually wrote rather than to invent more.

On 123 documents it produced **one** candidate. The write-up explains why that is
structural rather than a bug in the method:
`docs/measurements/deriving-signal-terms-from-123-near-misses.md`.

TWO FILTERS, AND THE SECOND IS THE ONE THAT EARNS ITS PLACE

Document frequency, not raw count — a phrase repeated twenty times in one post is
one document's opinion. And **cross-corpus**: a phrase is only reported if it
appears in BOTH the blog and Reddit near-misses, because a phrase used on two
platforms is unlikely to be one site's navigation. Without it the top twenty is
link-blog boilerplate: `recent articles`, `th august`, `hugging face`.

GITHUB IS DELIBERATELY NOT READ HERE. Every GitHub candidate matched an alias
query to be in the corpus at all, so 63.9% of them clear subject against 23.7%
on blogs and 10.9% on Reddit. Deriving from them recovers the vocabulary we have.

    python scripts/derive_signal_terms.py [--ngram 2]
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import time

import psycopg

from collect.adapters.queries import load_queries
from collect.adapters.queries.sieve import author_prose, matches, normalize
from collect.config import settings
from collect.ops.sweep import seated_variants

#: Hours back to read Reddit listing pages from the raw store. The listing sweep
#: stores one page per request, so this bounds the pass to a recent sweep rather
#: than every page ever stored.
LISTING_WINDOW_HOURS = 12

#: Function words, plus the model names and family words themselves. The names
#: are excluded because subject already matched them - a term that IS a model
#: name is not a signal term, it is the thing signal is supposed to be about.
STOP = frozenset(
    """
        the a an and or but if of to in on at for with from by as is are was
        were be been being it its this that these those i you he she we they
        them us our your my me not no do does did have has had will would
        can could should may might must about into over under again more
        most other some such only own same so than too very just now then
        there here what which who whom when where why how all any both each
        few nor s t ve ll re m d o y one two get got go going make made use
        used using like really much even still also way thing things time
        lot bit see know think want need try trying new good great better
        best bad worse worst first last next different model models ai llm
        claude gpt gemini qwen opus sonnet haiku flash fable sol luna code
    """.split()  # noqa: SIM905 - 161 words; a list literal is unreadable
)

_WORD = re.compile(r"[a-z][a-z'\-]{2,}")


def _term_sets(conn):
    """`{surface: (subject_terms, term_sets)}`, grouped so subject tests once."""
    surfaces = sorted({s for v in seated_variants(conn).values() for s in v})
    entries = [
        e for e in load_queries().all_entries if not e.direction_from_extraction
    ]
    out = {}
    for surface in surfaces:
        rendered = tuple(e.terms.substitute(surface) for e in entries)
        out[surface] = (rendered[0].subject, rendered)
    return out, entries


def near_misses(texts, by_surface):
    """Texts where topic hit, signal did not, and nothing passed."""
    out = []
    for text in texts:
        haystack = normalize(text)
        prose = normalize(author_prose(text))
        missed = passed = False
        for subject_terms, term_sets in by_surface.values():
            if not all(matches(t, haystack) for t in subject_terms):
                continue
            for terms in term_sets:
                topic = any(matches(t, haystack) for t in terms.topic)
                signal = any(matches(t, prose) for t in terms.signal)
                if topic and signal:
                    passed = True
                elif topic:
                    missed = True
        if missed and not passed:
            out.append(text)
    return out


def _blog_texts():
    return [
        p.read_text(encoding="utf-8", errors="replace")
        for p in pathlib.Path("raw_store/flattened").rglob("*")
        if p.is_file()
    ]


def _reddit_texts():
    """Posts from listing pages stored in the last `LISTING_WINDOW_HOURS`."""
    cutoff = time.time() - LISTING_WINDOW_HOURS * 3600
    posts = {}
    for path in pathlib.Path("raw_store/raw").rglob("*"):
        if not path.is_file() or path.stat().st_mtime < cutoff:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except ValueError:
            continue
        if not isinstance(payload, dict):
            continue
        data = payload.get("data")
        if not isinstance(data, dict):
            continue
        for entry in data.get("posts") or []:
            if isinstance(entry, dict) and isinstance(entry.get("data"), dict):
                posts[entry["data"].get("id")] = entry["data"]
    return [
        (p.get("title") or "") + "\n" + (p.get("selftext") or "")
        for p in posts.values()
    ]


def _gram_set(text: str, n: int) -> set[str]:
    """Distinct n-grams in one document. A SET, so repetition counts once."""
    words = _WORD.findall(author_prose(text).casefold())
    out = set()
    for i in range(len(words) - n + 1):
        gram = words[i : i + n]
        if gram[0] in STOP or gram[-1] in STOP:
            continue
        out.add(" ".join(gram))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ngram", type=int, default=2)
    parser.add_argument("--top", type=int, default=30)
    args = parser.parse_args()

    with psycopg.connect(settings().database_url, connect_timeout=25) as conn:
        by_surface, entries = _term_sets(conn)

    blog = near_misses(_blog_texts(), by_surface)
    reddit = near_misses(_reddit_texts(), by_surface)
    print(
        f"near-misses: blog {len(blog)}  reddit {len(reddit)}  "
        f"total {len(blog) + len(reddit)}"
    )
    print("POPULATION: unselected corpora only. GitHub excluded — see the docstring.\n")

    existing = {t.casefold() for e in entries for t in (e.terms.signal + e.terms.topic)}
    blog_freq: collections.Counter = collections.Counter()
    reddit_freq: collections.Counter = collections.Counter()
    for text in blog:
        blog_freq.update(_gram_set(text, args.ngram))
    for text in reddit:
        reddit_freq.update(_gram_set(text, args.ngram))

    shared = {
        gram: (blog_freq[gram], reddit_freq[gram])
        for gram in set(blog_freq) & set(reddit_freq)
        if gram not in existing
    }
    ranked = sorted(shared.items(), key=lambda kv: -(kv[1][0] + kv[1][1]))
    print(
        f"{args.ngram}-grams in BOTH corpora, not already a term "
        f"({len(shared)} such)"
    )
    print("   blog reddit  term")
    for gram, (a, b) in ranked[: args.top]:
        print(f"   {a:4d} {b:6d}  {gram}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
