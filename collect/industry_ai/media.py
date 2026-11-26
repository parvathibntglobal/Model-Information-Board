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


def hackernews(hit: dict) -> str | None:
    if hit.get("comment_text"):
        return "none"
    if hit.get("story_text"):
        return "none"
    return "link" if hit.get("url") else "none"
