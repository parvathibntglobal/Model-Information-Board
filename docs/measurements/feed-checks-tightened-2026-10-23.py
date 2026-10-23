"""MEASURED 2026-10-23 for the #558 review: the tightened paraphrase checks against
the old ones, over every paraphrase stored at the current prompt version on the
LOCAL copy (mib_feed_local, 4,102 rows). That population passed the old checks -
the old checks chose it, which is the upstream filter rule 8 asks about.

Usage, from the repo root:
    git show 8b4c3b1:judge/feed/checks.py > old_checks.py
    python docs/measurements/feed-checks-tightened-2026-10-23.py old_checks.py
Output: feed-checks-tightened-2026-10-23.out.txt
"""

import collections
import importlib.util
import re
import sys

import psycopg

sys.path.insert(0, ".")
from judge.config import evidence_feed_settings  # noqa: E402
from judge.feed import checks as new  # noqa: E402
from judge.feed.paraphrase import max_chars  # noqa: E402

spec = importlib.util.spec_from_file_location("old", sys.argv[1])
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)

with open(".env.test", encoding="utf-8-sig") as fh:
    dsn = next(line.split("=", 1)[1].strip().strip('"') for line in fh
               if line.startswith("TEST_DATABASE_URL="))
dsn = re.sub(r"/[^/?]+(\?|$)", r"/mib_feed_local\1", dsn, count=1)
settings = evidence_feed_settings()["paraphrase"]

with psycopg.connect(dsn) as c:
    rows = c.execute(
        "SELECT fp.model_version_id, fp.document_id, fp.text, "
        "       coalesce(v.display_name, v.canonical_id, v.id) "
        "FROM feed_paraphrase fp JOIN model_version v ON v.id = fp.model_version_id "
        "WHERE fp.prompt_version = %s", (settings["prompt_version"],)).fetchall()
    entries = collections.defaultdict(list)
    for mv, doc, quote, name, slug in c.execute(
        "SELECT v.id, be.document_id, be.quote, be.name, COALESCE(be.ruling_target, be.slug) "
        "FROM board_entry be JOIN model_version v "
        "  ON v.id = be.model_version_id OR v.canonical_id = be.model_version_id "
        "WHERE be.ruling IS DISTINCT FROM 'declined'").fetchall():
        entries[(mv, doc)].append({"quote": quote, "name": name, "slug": slug})

newly, fixed = collections.Counter(), 0
samples = collections.defaultdict(list)
for mv, doc, text, label in rows:
    es = entries.get((mv, doc), [])
    kw = {"max_chars": max_chars({"entries": es}, settings),
          "max_copied_words": settings["max_copied_words"],
          "topics": [e["name"] or e["slug"] or "" for e in es]}
    excerpts = [e["quote"] or "" for e in es]
    was = old.paraphrase_problem(text, excerpts, label, **kw)
    now = new.paraphrase_problem(text, excerpts, label, **kw)
    if was is None and now is not None:
        key = re.sub(r"\(.*", "", now).strip().split(":")[0]
        newly[key] += 1
        if len(samples[key]) < 40:
            samples[key].append((label, now, text[:160]))
    if was is not None and now is None:
        fixed += 1

print(f"stored paraphrases checked: {len(rows)} (prompt_version {settings['prompt_version']}, "
      "local copy mib_feed_local)")
print(f"passed the old checks and refused by the new: {sum(newly.values())}; "
      f"refused before and passing now: {fixed}")
for key, n in newly.most_common():
    print(f"  {n:4}  {key}")
for key, found in samples.items():
    print("==", key)
    for label, why, t in found:
        print("   ", label, "|", why, "|", t)
