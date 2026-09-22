"""LOCAL ATTRIBUTABILITY: can a quote from this feed carry its own subject?

"Resolves to exactly one" asks a DOCUMENT-level question — is this post about
one model — and a comparative survey answers no by construction. But extraction
does not quote documents, it quotes SENTENCES, and `subject_verbatim` needs the
model named in the same span as the claim.

So this measures the sentence-level version, read-only with the registry's own
resolver and no model call:

    of the sentences that name any tracked model,
    what share name EXACTLY ONE owner?

That is the property `quoted_support` can verify in code afterwards. A survey
whose sentences each name one model is highly attributable however many models
the post covers; a survey whose sentences compare four models in one breath is
not, and no amount of yield fixes it.

LIMITS, attached rather than left to a reader:
  - the sample is the same ten articles the feed probe fetched, so it inherits
    that sample's bias (sources.yaml §3a: a ten-entry sample overstates naming
    by 3-5x on any feed deeper than ten entries).
  - `trafilatura` extraction here, not the pipeline's `extract_article_text`.
  - sentence splitting is a regex. A sentence naming two models is counted
    unattributable even where a human would read one as the subject.
"""

import collections
import os
import pathlib
import re
import sys

import psycopg
import trafilatura
from dotenv import load_dotenv

ROOT = pathlib.Path(r"C:\Users\anooj\Model-Information-Board")
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from collect.triage.entity import build_population, resolve  # noqa: E402

SENT = re.compile(r"(?<=[.!?])\s+|\n+")


def main() -> int:
    with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
        models = list(
            conn.execute("SELECT canonical_id, display_name FROM model_version")
        )
    pop = build_population(models, [])

    def owners_of(text):
        out = set()
        for s in resolve(text, pop):
            out.update(pop.owners.get(s, ()))
        return out

    for host in sys.argv[1:]:
        root = "_danluu_probe" if host == "danluu.com" else "_six_host_probe"
        files = sorted((ROOT / root / host).glob("a*.html"))
        if not files:
            print(f"{host}: no article HTML on disk")
            continue
        naming = one = many = 0
        widest = collections.Counter()
        docs_with = 0
        for f in files:
            html = f.read_text(encoding="utf-8", errors="replace")
            text = trafilatura.extract(html) or ""
            found_here = 0
            for sentence in SENT.split(text):
                sentence = sentence.strip()
                if len(sentence) < 15:
                    continue
                owners = owners_of(sentence)
                if not owners:
                    continue
                naming += 1
                found_here += 1
                if len(owners) == 1:
                    one += 1
                else:
                    many += 1
                    widest[len(owners)] += 1
            docs_with += 1 if found_here else 0

        print(f"\n=== {host} — {len(files)} articles ===")
        print(f"  sentences naming a tracked model : {naming}")
        if naming:
            print(
                f"    naming EXACTLY ONE             : {one}  "
                f"({one / naming * 100:.0f}%)  <- locally attributable"
            )
            print(
                f"    naming TWO OR MORE             : {many}  "
                f"({many / naming * 100:.0f}%)"
            )
            if widest:
                print(
                    "    models per multi-model sentence: "
                    f"{dict(sorted(widest.items()))}"
                )
        print(f"  articles with >=1 naming sentence : {docs_with}/{len(files)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
