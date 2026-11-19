"""Confound checks on profile_rows.json.

X: likes per view (partly removes account reach) by format feature.
Reddit: score by post kind and by question title WITHIN each of the larger subreddits.
"""
import collections
import json
import os
import statistics as st

OUT = os.path.dirname(os.path.abspath(__file__))
rows = json.load(open(os.path.join(OUT, "profile_rows.json"), encoding="utf-8"))

x = [r for r in rows if r["source"] == "x" and r.get("views", 0) >= 500]
print(f"X posts with >= 500 views: {len(x)} of {sum(r['source'] == 'x' for r in rows)}")


def rate(rs):
    v = [r["eng"] / r["views"] for r in rs]
    return f"n={len(v):3} median likes/1k views {1000 * st.median(v):.1f}" if v else "n=0"


for name, f in (("hashtag", lambda r: r["hashtags"] > 0), ("media photo/video", lambda r: r["x_kind"] in ("photo", "video", "photo+video", "animated_gif")),
                ("text only", lambda r: r["x_kind"] == "text"), ("link card/url", lambda r: r["x_kind"] == "link"),
                ("long post >280", lambda r: r["x_long_post"]), ("bullets/arrows", lambda r: r["bullets"] > 0),
                ("ends with question", lambda r: r["ends_question"]), ("quote post", lambda r: r["x_quote"]),
                ("link in text", lambda r: r["links"] > 0)):
    yes = [r for r in x if f(r)]
    no = [r for r in x if not f(r)]
    print(f"  {name:20} yes {rate(yes)} | no {rate(no)}")
print("  X bookmarks per 1k views, long vs short:",
      1000 * st.median(r["bookmarks"] / r["views"] for r in x if r["x_long_post"]),
      1000 * st.median(r["bookmarks"] / r["views"] for r in x if not r["x_long_post"]))

rd = [r for r in rows if r["source"] == "reddit"]
subs = [s for s, n in collections.Counter(r["x_group"] for r in rd).most_common() if n >= 15]
print("\nReddit, median score within subreddit (subs with >= 15 sampled posts)")
for s in subs:
    rs = [r for r in rd if r["x_group"] == s]
    by = collections.defaultdict(list)
    for r in rs:
        by["text" if r["x_kind"] == "text" else "image/video/gallery" if r["x_kind"] in ("image", "video", "gallery", "rich:video") else "link"].append(r["eng"])
    q = [r["eng"] for r in rs if r["t_question"]]
    nq = [r["eng"] for r in rs if not r["t_question"]]
    print(f"  r/{s:20} n={len(rs):3} " + "  ".join(f"{k} {st.median(v):g} (n={len(v)})" for k, v in sorted(by.items()))
          + f" | title '?' {st.median(q) if q else '-'} (n={len(q)}) vs not {st.median(nq):g} (n={len(nq)})")
hn = [r for r in rows if r["source"] == "hackernews" and r["x_kind"] == "link"]
print("\nHN link stories: median points by title colon:",
      st.median(r["eng"] for r in hn if r["t_colon"]), sum(r["t_colon"] for r in hn),
      "vs", st.median(r["eng"] for r in hn if not r["t_colon"]), sum(not r["t_colon"] for r in hn))
print("HN link stories: median points by title chars <=50 vs >50:",
      st.median(r["eng"] for r in hn if r["t_chars"] <= 50), sum(r["t_chars"] <= 50 for r in hn),
      "vs", st.median(r["eng"] for r in hn if r["t_chars"] > 50), sum(r["t_chars"] > 50 for r in hn))
