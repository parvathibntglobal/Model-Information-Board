"""What a harvested post carries besides its words (2026-11-25, anooj).

THE LANE READS TEXT ONLY: a caption, a title, a body. A post whose content is a
picture or a video is judged on whatever words came with it, and "no AI term" in
three words of caption is not a finding about the video. This module records
WHAT KIND of media a post carries, from fields the providers already send, so a
post with too little text to judge can be counted apart (pipeline.evaluate,
stage `unread`) instead of being filtered out as if it had been read (rules 4, 6).

Measured 2026-11-25 on the raw pages of that day's observer dry runs (#667's
worktree), counted by field, no text read:
  Instagram  360 posts of 30 accounts: GraphVideo 248 (247 `product_type: clips`),
             GraphSidecar 107, GraphImage 5. `accessibility_caption` was present on
             the 112 non-video posts and null on all 112: no alt text to read.
  X          391 posts: media on 173 (photo 178, video 79, animated_gif 2 items),
             alt text on 1 of 259 media items; 189 quote another post, whose text is
             in the payload (not read yet); 116 long posts, read via `note_tweet`.
  Reddit     1,075 posts: self 660, image 172, link 118, gallery 63, video 62;
             85 crossposts, each with its parent's title in the payload.
  Bluesky    one request, 50 posts of one account: external link card 20,
             images 11 (14 images, all with alt text), video 5, quote 2,
             quote with media 3, none 9.
  Hacker News  a story is a title and a link; its article is not read.

THE VOCABULARY (`iai_item.media_kind`):
  none     recorded, and the post carries no media
  image    one picture
  gallery  several pictures (or a carousel / sidecar)
  video    a video, a reel, an animated gif
  link     a link to something else (an article, a link card)
  NULL     NOT RECORDED: a platform this module does not read (GitHub, dev.to,
           feeds), a row stored before it existed, or a shape it does not know.
           Never read as "none" (rule 6).

Code only. No model looks at a picture here; reading one is a later, separate
decision (rule 2).
"""

from __future__ import annotations

import json
from typing import Any

MEDIA_KINDS = ("none", "image", "gallery", "video", "link")
#: The kinds whose content is not in the post's words.
VISUAL = frozenset({"image", "gallery", "video"})


def instagram(node: dict) -> str | None:
    t = node.get("__typename")
    if t == "GraphVideo" or node.get("is_video") is True:
        return "video"
    if t == "GraphSidecar":
        return "gallery"
    if t == "GraphImage":
        return "image"
    return None


def reddit(raw: dict) -> str | None:
    if not raw:
        return None
    kind = _reddit_own(raw)
    # A CROSSPOST carries its parent's media, not its own: a crossposted video reads
    # as a bare link on the child (85 of 1,075, 2026-11-25).
    parents = raw.get("crosspost_parent_list") or []
    if kind in ("link", None) and parents and isinstance(parents[0], dict):
        return _reddit_own(parents[0]) or kind
    return kind


def _reddit_own(d: dict) -> str | None:
    hint = str(d.get("post_hint") or "")
    if d.get("is_gallery"):
        return "gallery"
    if d.get("is_video") or hint in ("hosted:video", "rich:video"):
        return "video"
    if hint == "image":
        return "image"
    if d.get("is_self"):
        return "none"
    if d.get("url") or hint == "link":
        return "link"
    return None


def x(payload: str | dict | None) -> str | None:
    """From the tweet result X sent (`XPost.payload`). The post's OWN media only: a
    quoted post's media belongs to that post."""
    try:
        t = json.loads(payload) if isinstance(payload, str) else (payload or {})
    except ValueError:
        return None
    t = t.get("tweet") or t  # TweetWithVisibilityResults wraps the tweet
    legacy = t.get("legacy")
    if not isinstance(legacy, dict):
        return None
    media = (legacy.get("extended_entities") or legacy.get("entities") or {}).get("media") or []
    types = [m.get("type") for m in media if isinstance(m, dict)]
    if any(k in ("video", "animated_gif") for k in types):
        return "video"
    if len(types) > 1:
        return "gallery"
    if types:
        return "image"
    if t.get("card"):
        return "link"
    return "none"


def bluesky(raw: dict) -> str | None:
    """From the post view the API sent (`embed.$type` ends in `#view`)."""
    if not raw:
        return None
    return _bluesky_embed(raw.get("embed"))


def _bluesky_embed(embed: Any) -> str | None:
    if not embed:
        return "none"
    t = str(embed.get("$type") or "")
    if t.startswith("app.bsky.embed.images"):
        return "gallery" if len(embed.get("images") or []) > 1 else "image"
    if t.startswith("app.bsky.embed.video"):
        return "video"
    if t.startswith("app.bsky.embed.external"):
        return "link"
    if t.startswith("app.bsky.embed.recordWithMedia"):
        return _bluesky_embed(embed.get("media"))
    if t.startswith("app.bsky.embed.record"):
        return "none"  # a quote: its content is the quoted post's words
    return None


# ── TEXT THAT COMES WITH THE MEDIA (#679 step 1, anooj, 2026-11-26) ──────────────
#
# Words the provider already sends beside a post that are NOT the author's own:
#   alt_text          the description an author gave a picture (Bluesky, X)
#   quoted_post       the text of the post this one quotes (X, Bluesky)
#   crosspost_parent  a Reddit crosspost's original title and body
# They reach the AI-term and industry-term matching and the "too little to read"
# check (rules.judged_text), never the filters, the type label, the duplicate keys or
# what a page shows - the post's own words stay its own.
#
# Measured 2026-11-26 on the 25 Nov observer dry-run pages, by field, no text read:
#   Bluesky  alt text non-empty on 77 of 286 image entries; a quoted post's text on 67
#            quotes, and on 9 quotes-with-media.
#   X        `quoted_status_result` on 385 of 694 tweet entries; alt text on 1 of 259
#            media items (#676).
# Instagram's `accessibility_caption` is NOT read: it was null on all 112 non-video
# posts, and when present it is Instagram's own machine description, not the author's.
#
# Each reader returns (text or None, sorted kinds). None means nothing was found,
# which is not "the media says nothing" (rule 6) - it is only what this post carried.

MEDIA_TEXT_KINDS = ("alt_text", "quoted_post", "crosspost_parent")


def _joined(parts: list[tuple[str, Any]]) -> tuple[str | None, list[str]]:
    kept = [(k, " ".join(t.split())) for k, t in parts if isinstance(t, str) and t.strip()]
    if not kept:
        return None, []
    return "\n".join(t for _, t in kept), sorted({k for k, _ in kept})


def _x_tweet(d: Any) -> dict:
    d = d if isinstance(d, dict) else {}
    inner = d.get("tweet")
    return inner if isinstance(inner, dict) else d


def _x_full_text(t: dict) -> str | None:
    long = ((t.get("note_tweet") or {}).get("note_tweet_results") or {}).get("result") or {}
    return long.get("text") or (t.get("legacy") or {}).get("full_text")


def x_text(payload: str | dict | None) -> tuple[str | None, list[str]]:
    try:
        t = json.loads(payload) if isinstance(payload, str) else (payload or {})
    except ValueError:
        return None, []
    t = _x_tweet(t)
    legacy = t.get("legacy") if isinstance(t.get("legacy"), dict) else {}
    media = (legacy.get("extended_entities") or {}).get("media") or []
    parts: list[tuple[str, Any]] = [
        ("alt_text", m.get("ext_alt_text")) for m in media if isinstance(m, dict)]
    quoted = _x_tweet((t.get("quoted_status_result") or {}).get("result"))
    if quoted:
        parts.append(("quoted_post", _x_full_text(quoted)))
    return _joined(parts)


def bluesky_text(raw: dict) -> tuple[str | None, list[str]]:
    embed = (raw or {}).get("embed") or {}
    t = str(embed.get("$type") or "")
    images = embed.get("images") or (embed.get("media") or {}).get("images") or []
    parts: list[tuple[str, Any]] = [
        ("alt_text", i.get("alt")) for i in images if isinstance(i, dict)]
    if t.startswith("app.bsky.embed.recordWithMedia"):
        rec = (embed.get("record") or {}).get("record") or {}
    elif t.startswith("app.bsky.embed.record"):
        rec = embed.get("record") or {}
    else:
        rec = {}
    if isinstance(rec.get("value"), dict):
        parts.append(("quoted_post", rec["value"].get("text")))
    return _joined(parts)


def reddit_text(raw: dict) -> tuple[str | None, list[str]]:
    parents = (raw or {}).get("crosspost_parent_list") or []
    if not parents or not isinstance(parents[0], dict):
        return None, []
    p = parents[0]
    return _joined([("crosspost_parent", f"{p.get('title') or ''}\n{p.get('selftext') or ''}")])


# ── THE FIRST PICTURE'S LINK (#679 step 3, anooj, 2026-11-26) ───────────────────
#
# For the picture-text reader (collect/industry_ai/ocr.py), under CLAUDE.md's fourth
# fetch exception: only a link the provider's own response gave, the FIRST picture of
# the post only. Carried on the Item for this run and never stored. None = the payload
# names no picture this reader knows, which is not "the post has none" (rule 6).


def x_picture(payload: str | dict | None) -> str | None:
    try:
        t = json.loads(payload) if isinstance(payload, str) else (payload or {})
    except ValueError:
        return None
    legacy = _x_tweet(t).get("legacy")
    if not isinstance(legacy, dict):
        return None
    media = (legacy.get("extended_entities") or {}).get("media") or []
    first = next((m for m in media if isinstance(m, dict)), None)
    if first and first.get("type") == "photo":
        return first.get("media_url_https") or None
    return None


def reddit_picture(raw: dict) -> str | None:
    raw = raw or {}
    if raw.get("is_gallery"):
        order = [i.get("media_id") for i in ((raw.get("gallery_data") or {}).get("items") or [])
                 if isinstance(i, dict)]
        meta = raw.get("media_metadata") or {}
        for mid in order or list(meta):
            src = ((meta.get(mid) or {}).get("s") or {}).get("u")
            if src:
                import html

                return html.unescape(src)
        return None
    if raw.get("post_hint") == "image":
        return raw.get("url_overridden_by_dest") or raw.get("url") or None
    return None


def bluesky_picture(raw: dict) -> str | None:
    embed = (raw or {}).get("embed") or {}
    images = embed.get("images") or (embed.get("media") or {}).get("images") or []
    first = next((i for i in images if isinstance(i, dict)), None)
    return (first.get("fullsize") or first.get("thumb")) if first else None


def instagram_picture(node: dict) -> str | None:
    """Instagram's CDN refuses `*` in robots.txt (checked 2026-11-26), so this link is
    asked and recorded as `refused`, never fetched - kept so the count says so."""
    kids = ((node.get("edge_sidecar_to_children") or {}).get("edges") or [])
    first = ((kids[0] or {}).get("node") or {}) if kids else node
    if first.get("is_video"):
        return None
    return first.get("display_url") or None


def hackernews(hit: dict) -> str | None:
    if hit.get("comment_text"):
        return "none"
    if hit.get("story_text"):
        return "none"
    return "link" if hit.get("url") else "none"
