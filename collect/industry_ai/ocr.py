"""Text in a "not readable" post's first picture, in SHADOW MODE (#679 step 3).

Under CLAUDE.md's FOURTH fetch exception (#683, in force since 2026-11-26). Its
conditions are not settings, and each has its line here:

  1. only the picture link the provider's own response gave (`Item.picture_url`, from
     collect/industry_ai/media.py), for posts THIS run labelled "not readable";
  2. a plain request through `collect.http.build_client` (identifying User-Agent), no
     cookies, login, browser or page fetch;
  3. the first picture only, at most `ocr.max_bytes`, into a temporary folder that is
     removed in a `finally` whatever happened; only the text is kept;
  4. at most `ocr.max_per_run` posts, taken in turn by platform, then by account
     within a platform, newest first (`in_turn`); the rest are `over_cap`;
  5. robots.txt asked for every host and every redirect hop (`RobotsGate`), with no
     switch; a refusal is `refused`.

Tesseract reads the characters (CLAUDE.md rule 2's record for it): it decides nothing.
Every word is kept with its confidence, so `ocr.min_confidence` can be set from the
shadow week's hand-check without fetching a picture again. What the text WOULD have
decided is a flag only (rules.picture_text_flags).
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from collect.industry_ai.rules import UNREAD_STAGE, Item

#: Image and gallery posts; a video is step 2's (held, #681).
PICTURE_KINDS = ("image", "gallery")
MAX_REDIRECTS = 5
#: A status a later sighting may try again: the first run's cap or a passing failure.
RETRY_STATUSES = (None, "over_cap", "failed")
_OLDEST = datetime.min.replace(tzinfo=UTC)


@dataclass(frozen=True)
class PictureRead:
    """One picture's outcome (`iai_item.ocr_status` and what was read)."""

    status: str
    text: str | None = None
    confidence: tuple[int, ...] = ()
    detail: str = ""


def candidates(items: list[Item], results: dict, stored_status: dict[str, str | None], *,
               first_seen: dict[str, datetime | None], not_before: datetime) -> list[Item]:
    """This run's posts labelled "not readable", with a picture link, not yet read
    to a final answer. `stored_status` is each id's `ocr_status` in the database.

    NOT A POST ALREADY PAST THE RETENTION CUTOFF (#687 review): `first_seen` (each
    id's `first_seen_at`) before `not_before` means `store.clear_picture_text` would
    empty its text a few lines later in the same run - a fetch for nothing, and a
    flag whose text is gone at the next relabel. A post with no stored first sight
    is this run's own, so it is read."""
    return [
        it for it in items
        if it.picture_url and it.media_kind in PICTURE_KINDS
        and (r := results.get(it.id)) is not None and r.stage == UNREAD_STAGE
        and stored_status.get(it.id) in RETRY_STATUSES
        and ((seen := first_seen.get(it.id)) is None or seen >= not_before)
    ]


def in_turn(items: list[Item]) -> list[Item]:
    """Platforms in turn; within a platform, accounts in turn; each account's
    newest post first (condition 4). So no platform and no prolific account takes
    the cap every run, and `over_cap` lands on a stated order (rule 7)."""
    by: dict[str, dict[str, list[Item]]] = defaultdict(lambda: defaultdict(list))
    for it in items:
        by[it.platform][it.author_id or f"no author: {it.id}"].append(it)
    queues: dict[str, list[Item]] = {}
    for platform, accounts in sorted(by.items()):
        lanes = [sorted(posts, key=lambda p: p.created_at or _OLDEST, reverse=True)
                 for _, posts in sorted(accounts.items(),
                                        key=lambda kv: max((p.created_at or _OLDEST)
                                                           for p in kv[1]), reverse=True)]
        queues[platform] = _interleave(lanes)
    return _interleave([queues[p] for p in sorted(queues)])


def _interleave(lanes: list[list[Item]]) -> list[Item]:
    out: list[Item] = []
    for i in range(max((len(lane) for lane in lanes), default=0)):
        out += [lane[i] for lane in lanes if i < len(lane)]
    return out


def read_pictures(items: list[Item], ocr: dict, *, client, gate,
                  tesseract: str = "tesseract") -> dict[str, PictureRead]:
    """Every candidate's outcome: read in turn up to `ocr.max_per_run`, the rest
    `over_cap`. Refuses before any download when Tesseract is missing (rule 12): a
    run that fetched pictures it could not read would record them all as failed."""
    if items and shutil.which(tesseract) is None:
        raise RuntimeError(f"ocr.enabled is true but {tesseract!r} is not installed")
    ordered = in_turn(items)
    take = ordered[: ocr["max_per_run"]]
    out = {it.id: PictureRead("over_cap") for it in ordered[ocr["max_per_run"]:]}
    for it in take:
        out[it.id] = read_one(it.picture_url, client=client, gate=gate,
                              max_bytes=ocr["max_bytes"], timeout=ocr["timeout_seconds"],
                              tesseract=tesseract)
    return out


def read_one(url: str, *, client, gate, max_bytes: int, timeout: int,
             tesseract: str = "tesseract") -> PictureRead:
    """Download one picture and read it; the folder is removed whatever happens."""
    folder = Path(tempfile.mkdtemp(prefix="iai-ocr-"))
    try:
        picture = folder / "picture"
        refused = _download(url, picture, client=client, gate=gate, max_bytes=max_bytes)
        if refused is not None:
            return refused
        return _read(picture, timeout=timeout, tesseract=tesseract)
    except Exception as e:  # noqa: BLE001 - recorded as `failed` with its type, never silent
        return PictureRead("failed", detail=f"{type(e).__name__}: {str(e)[:120]}")
    finally:
        shutil.rmtree(folder, ignore_errors=True)  # condition 3: the picture is not kept


def _download(url: str, dest: Path, *, client, gate, max_bytes: int) -> PictureRead | None:
    """None when `dest` holds the picture; otherwise why not. robots.txt is asked for
    every hop (condition 5); a robots.txt that gave no answer is `failed`, which a
    later sighting tries again, not `refused`."""
    for _ in range(MAX_REDIRECTS + 1):
        if not url.startswith("https://"):
            return PictureRead("failed", detail="not https")
        decision = gate.allows(url)
        if not decision.allowed:
            if decision.ruling.status == "no-answer":
                return PictureRead("failed", detail=f"robots no answer: {decision.reason}")
            return PictureRead("refused", detail=f"robots.txt: {decision.reason}")
        with client.stream("GET", url, headers={"Accept": "image/*"}) as response:
            if response.is_redirect:
                url = str(response.next_request.url)
                continue
            if response.status_code != 200:
                return PictureRead("failed", detail=f"HTTP {response.status_code}")
            if not response.headers.get("content-type", "").startswith("image/"):
                return PictureRead("failed", detail="not an image")
            size = 0
            with dest.open("wb") as f:
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > max_bytes:
                        return PictureRead("too_large", detail=f"over {max_bytes} bytes")
                    f.write(chunk)
            return None
    return PictureRead("failed", detail=f"more than {MAX_REDIRECTS} redirects")


def _read(picture: Path, *, timeout: int, tesseract: str) -> PictureRead:
    """Tesseract's words and their confidences, in reading order."""
    try:
        r = subprocess.run([tesseract, str(picture), "stdout", "tsv"], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=timeout,
                           check=False)
    except subprocess.TimeoutExpired:
        return PictureRead("failed", detail=f"Tesseract over {timeout}s")
    if r.returncode != 0:
        return PictureRead("failed", detail=f"Tesseract exit {r.returncode}")
    words, confidence = parse_tsv(r.stdout)
    if not words:
        return PictureRead("no_text")
    return PictureRead("ok", text=" ".join(words), confidence=tuple(confidence))


def parse_tsv(tsv: str) -> tuple[list[str], list[int]]:
    """Words (level 5, non-empty, confidence not -1) and their whole confidences.
    A word Tesseract returned with spaces inside is split, each part keeping the
    word's confidence, so `ocr_text.split()` and `ocr_confidence` always align."""
    words: list[str] = []
    conf: list[int] = []
    lines = tsv.splitlines()
    if not lines:
        return words, conf
    head = lines[0].split("\t")
    try:
        at_level, at_conf, at_text = head.index("level"), head.index("conf"), head.index("text")
    except ValueError as e:
        raise ValueError(f"not Tesseract TSV: {lines[0][:80]!r}") from e
    for line in lines[1:]:
        cells = line.split("\t")
        if len(cells) <= at_text or cells[at_level] != "5":
            continue
        c = round(float(cells[at_conf]))
        if c < 0:
            continue
        for part in cells[at_text].split():
            words.append(part)
            conf.append(c)
    return words, conf
