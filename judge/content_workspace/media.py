"""Media files for a draft: carousel PDFs, card and chart images.

The files are MADE outside the page - in Claude Code, with the media skills
(theme-factory's Model Information Board theme, dataviz, pdf, canvas-design;
see docs in the workspace's media plan) - and stored here, in the workspace's
own database, so the page can show and download them. Like everything in the
workspace they are internal: served only to a signed-in person.

What is checked on the way in (code, no model): the file is a real PNG or PDF
(read, not trusted from its name), its size is within `media.max_bytes`, and
its pixel size or page count is recorded. Whether the picture says only what
the draft and the board say is NOT checked: a person looks at it before use.
"""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any

from judge.content_workspace import store

KINDS = ("carousel_pdf", "card_png", "chart_png", "cover_png", "other")
COLUMNS = ("id", "draft_id", "kind", "filename", "content_type", "size_bytes", "width",
           "height", "pages", "made_with", "content_sha", "note", "created_at", "created_by")


def _inspect(data: bytes) -> dict[str, Any]:
    """What the bytes actually are. Refuses anything that is not a PNG or PDF."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        from PIL import Image

        with Image.open(io.BytesIO(data)) as im:
            im.verify()
        with Image.open(io.BytesIO(data)) as im:
            width, height = im.size
        return {"content_type": "image/png", "width": width, "height": height, "pages": None}
    if data[:5] == b"%PDF-":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        box = reader.pages[0].mediabox if reader.pages else None
        # PDF points at 72 per inch; a carousel page made at 1080 px is 810 pt.
        return {"content_type": "application/pdf", "pages": len(reader.pages),
                "width": round(float(box.width) * 96 / 72) if box else None,
                "height": round(float(box.height) * 96 / 72) if box else None}
    raise store.WorkspaceRequestError("a media file is a PNG or a PDF (checked from its "
                                      "contents, not its name)")


def add(conn: Any, draft_id: int, *, data: bytes, filename: str, kind: str, made_with: str,
        note: str | None, by: str | None, s: dict[str, Any]) -> dict[str, Any]:
    d = store.draft(conn, draft_id)
    if kind not in KINDS:
        raise store.WorkspaceRequestError(f"kind is one of {', '.join(KINDS)}")
    if not (made_with or "").strip():
        raise store.WorkspaceRequestError("say how the file was made (made_with)")
    limit = s["media"]["max_bytes"]
    if len(data) > limit:
        raise store.WorkspaceRequestError(f"the file is {len(data):,} bytes, over {limit:,}")
    info = _inspect(data)
    if kind == "carousel_pdf" and info["content_type"] != "application/pdf":
        raise store.WorkspaceRequestError("a carousel is a PDF")
    if kind.endswith("_png") and info["content_type"] != "image/png":
        raise store.WorkspaceRequestError(f"a {kind} is a PNG")
    row = conn.execute(
        "INSERT INTO cw_media (draft_id, kind, filename, content_type, data, size_bytes, width,"
        " height, pages, made_with, content_sha, note, created_by)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        f" RETURNING {', '.join(COLUMNS)}",
        (draft_id, kind, re.sub(r"[^A-Za-z0-9._-]", "-", Path(filename).name)[:120],
         info["content_type"], data, len(data),
         info["width"], info["height"], info["pages"], made_with.strip(), d["content_sha"],
         (note or "").strip() or None, by),
    ).fetchone()
    return _row(row, d["content_sha"])


def _row(row: tuple, current_sha: str) -> dict[str, Any]:
    m = dict(zip(COLUMNS, row, strict=True))
    m["created_at"] = m["created_at"].isoformat()
    # Made from text the draft no longer has: shown as out of date, not hidden.
    m["out_of_date"] = m["content_sha"] != current_sha
    return m


def listing(conn: Any, draft_id: int) -> list[dict[str, Any]]:
    d = store.draft(conn, draft_id)
    return [_row(r, d["content_sha"]) for r in conn.execute(
        f"SELECT {', '.join(COLUMNS)} FROM cw_media WHERE draft_id = %s"
        " ORDER BY created_at DESC, id DESC", (draft_id,)).fetchall()]


def fetch(conn: Any, media_id: int) -> tuple[bytes, str, str]:
    row = conn.execute("SELECT data, content_type, filename FROM cw_media WHERE id = %s",
                       (media_id,)).fetchone()
    if row is None:
        raise store.WorkspaceRequestError(f"no media file {media_id}", 404)
    return bytes(row[0]), row[1], row[2]
