"""Read the official developer sources and PyVideo's talk index
(contract/official_sources.yaml, 2026-10-30) into official_doc, official_release
and video_ref, recording every repository's read in official_fetch.

THE GITHUB REST API ONLY (ruling `github-api-terms`, whose live precondition is
`access_path: api`). Per repository: its record (to compare the licence), one
tree listing, then each kept file's blob by sha - and an SDK's releases. Nothing
is read from github.com pages, raw.githubusercontent.com, YouTube or Vimeo.

INCREMENTAL BY BLOB SHA. A file whose sha matches the stored row is not fetched
again. A fetched blob is checked against the sha it was asked for
(`parse.git_blob_sha`): bytes that are not the listed file are refused, never
stored under its name.

EVERYTHING NOT DONE IS COUNTED, on the repository's official_fetch row: files
deferred by the per-run cap, too large to fetch, failed, no longer listed; talks
in events with no year or before the minimum year, withheld or withdrawn under
PyVideo's NO_PUBLISH.json. A run that stopped early says so (rule 4, rule 6).
A request that gets no answer (a timeout, a dropped connection) is one failed
file, or an `http_error` for the repository whose record, tree or releases it
was - never the end of the run (#591 review).

NOTHING HERE IS EVIDENCE and no model reads it. The intended reader is phase B's
writing packs, which do not exist yet - contract/column_states.yaml says so per
column (rule 9).
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx

from collect.config import settings
from collect.ids import content_hash, stable_id
from collect.official.parse import (
    DOC_KIND,
    Contract,
    PyVideo,
    Repo,
    event_year,
    first_h1,
    flatten_notebook,
    git_blob_sha,
    glob_regex,
    load_contract,
    no_publish_ids,
    parse_talk,
    selected,
    title_for,
)
from collect.rawstore import FLATTENED, RAW, build_ref

JSON_ACCEPT = "application/vnd.github+json"
RAW_ACCEPT = "application/vnd.github.raw+json"
API_VERSION = "2022-11-28"
RELEASES_PER_PAGE = 100


class OfficialHarvestError(RuntimeError):
    """The harvest cannot start: no token, or the terms check refused."""


class RequestFailed(ValueError):
    """A request that got no answer: a timeout, a refused or dropped connection.
    A ValueError, so a blob that fails this way is counted with the blobs that
    failed any other way (`files_failed`)."""


class _Stop(Exception):
    """The run stops here: GitHub throttled us, or the budget fell below
    `stop_below_remaining`. Every repository not yet read is recorded as such."""


# ── the API ──────────────────────────────────────────────────────────────────

class GitHub:
    """GET against the REST API: paced, counted, and watching the hourly budget.

    The pace is `politeness.min_interval_seconds`; the budget is GitHub's own
    `x-ratelimit-remaining`, read off every response. Once it falls below
    `stop_below_remaining` no further request is made - the token is shared
    with the evidence harvest, and this one must never drain it."""

    def __init__(self, client, contract: Contract, token: str, *, limiter=None) -> None:
        from collect.limiter import HostLimiter

        self._client = client
        self._contract = contract
        self._token = token
        self._limiter = limiter or HostLimiter(min_interval=contract.min_interval_seconds)
        self.calls = 0
        #: The last `x-ratelimit-remaining` GitHub sent; None until one has -
        #: never an assumed full budget (rule 6).
        self.remaining: int | None = None

    def get(self, path: str, *, accept: str = JSON_ACCEPT, params: dict | None = None):
        from collect.adapters.github import GitHubHarvester

        if self.remaining is not None and self.remaining < self._contract.stop_below_remaining:
            raise _Stop(f"GitHub reports {self.remaining} core requests left this hour, below "
                        f"stop_below_remaining ({self._contract.stop_below_remaining})")
        url = self._contract.api + path
        self._limiter.wait(url)
        # Counted as a call whether or not it is answered: a request that timed
        # out may still have reached GitHub and spent the budget.
        self.calls += 1
        try:
            response = self._client.get(url, params=params, headers={
                "Accept": accept, "Authorization": f"Bearer {self._token}",
                "X-GitHub-Api-Version": API_VERSION})
        except httpx.HTTPError as exc:
            raise RequestFailed(f"{type(exc).__name__} {str(exc)[:160]}".strip()) from exc
        left = response.headers.get("x-ratelimit-remaining")
        if left is not None and left.isdigit():
            self.remaining = int(left)
        if GitHubHarvester.is_throttled(response):
            raise _Stop(f"GitHub throttled the run (HTTP {response.status_code})")
        return response

    def blob(self, owner_repo: str, sha: str) -> bytes:
        """A blob's bytes, checked against its sha. Raises ValueError otherwise."""
        response = self.get(f"/repos/{owner_repo}/git/blobs/{sha}", accept=RAW_ACCEPT)
        if response.status_code != 200:
            raise ValueError(f"blob {sha[:12]}: HTTP {response.status_code}")
        payload = response.content
        if git_blob_sha(payload) != sha:
            raise ValueError(f"blob {sha[:12]}: the bytes returned are not that blob")
        return payload


class DryStore:
    """A raw store that writes nothing: the ref a payload WOULD get, for --dry-run."""

    def put(self, given: bytes | str, *, namespace=RAW):
        as_bytes = given.encode("utf-8") if isinstance(given, str) else given
        return type("Stored", (), {"ref": build_ref(content_hash(as_bytes), namespace)})()

    def tombstone(self, ref: str, **_: Any) -> None:
        return None


# ── one official_fetch row ───────────────────────────────────────────────────

_FILE_COUNTS = ("files_listed", "files_unchanged", "files_fetched", "files_new",
                "files_changed", "files_deferred", "files_too_large", "files_failed",
                "files_unlisted")
_TALK_COUNTS = ("talks_no_year", "talks_before_min_year", "talks_withheld", "talks_withdrawn")
_RELEASE_COUNTS = ("releases_seen", "releases_new", "releases_changed")


def _tally(*, talks: bool, releases: bool) -> dict[str, Any]:
    """Every count the row carries: 0 where it applies, None where it does not -
    a cookbook has no releases, and NULL says so where 0 would claim it had none."""
    t: dict[str, Any] = {k: 0 for k in _FILE_COUNTS}
    t.update({k: (0 if talks else None) for k in _TALK_COUNTS})
    t.update({k: (0 if releases else None) for k in _RELEASE_COUNTS})
    t.update(outcome="ok", http_status=None, problems=[])
    return t


def _settle(t: dict[str, Any]) -> None:
    """ok, or partial with every reason named. A run that stopped, or failed to
    read the tree, already carries its own outcome."""
    reasons = t["problems"]
    for key, what in (("files_deferred", "deferred to a later run (max_blob_fetches_per_run)"),
                      ("files_too_large", "larger than max_blob_bytes, not fetched"),
                      ("files_failed", "failed")):
        if t[key]:
            reasons.insert(0, f"{t[key]} {what}")
    if t["outcome"] == "ok" and reasons:
        t["outcome"] = "partial"
    t["detail"] = "; ".join(reasons)[:1000] if reasons else None


_FETCH_INSERT = """
INSERT INTO official_fetch (run_id, source_key, fetched_at, outcome, http_status, detail,
  files_listed, files_unchanged, files_fetched, files_new, files_changed, files_deferred,
  files_too_large, files_failed, files_unlisted, talks_no_year, talks_before_min_year,
  talks_withheld, talks_withdrawn, releases_seen, releases_new, releases_changed,
  api_calls, rate_remaining)
VALUES (%(run_id)s, %(source_key)s, %(fetched_at)s, %(outcome)s, %(http_status)s, %(detail)s,
  %(files_listed)s, %(files_unchanged)s, %(files_fetched)s, %(files_new)s, %(files_changed)s,
  %(files_deferred)s, %(files_too_large)s, %(files_failed)s, %(files_unlisted)s,
  %(talks_no_year)s, %(talks_before_min_year)s, %(talks_withheld)s, %(talks_withdrawn)s,
  %(releases_seen)s, %(releases_new)s, %(releases_changed)s, %(api_calls)s,
  %(rate_remaining)s)
"""


# ── writing ──────────────────────────────────────────────────────────────────

_DOC_UPSERT = """
INSERT INTO official_doc (id, repo_key, provider, doc_kind, path, format, blob_sha, size_bytes,
  licence, html_url, title, title_source, raw_ref, text_ref, first_seen_at, changed_at,
  unlisted_at, pipeline_version)
VALUES (%(id)s, %(repo_key)s, %(provider)s, %(doc_kind)s, %(path)s, %(format)s, %(blob_sha)s,
  %(size_bytes)s, %(licence)s, %(html_url)s, %(title)s, %(title_source)s, %(raw_ref)s,
  %(text_ref)s, %(now)s, %(now)s, NULL, %(pipeline_version)s)
ON CONFLICT (id) DO UPDATE SET
  blob_sha = EXCLUDED.blob_sha, size_bytes = EXCLUDED.size_bytes, format = EXCLUDED.format,
  licence = EXCLUDED.licence, html_url = EXCLUDED.html_url, title = EXCLUDED.title,
  title_source = EXCLUDED.title_source, raw_ref = EXCLUDED.raw_ref,
  text_ref = EXCLUDED.text_ref, changed_at = EXCLUDED.changed_at, unlisted_at = NULL,
  pipeline_version = EXCLUDED.pipeline_version
RETURNING (xmax = 0) AS inserted
"""

_TALK_UPSERT = """
INSERT INTO video_ref (id, path, blob_sha, event, event_year, pyvideo_id, title, recorded,
  speakers, description, video_urls, video_hosts, thumbnail_url, duration_seconds, language,
  copyright_text, llm_terms, raw_ref, first_seen_at, changed_at, unlisted_at, pipeline_version)
VALUES (%(id)s, %(path)s, %(blob_sha)s, %(event)s, %(event_year)s, %(pyvideo_id)s, %(title)s,
  %(recorded)s, %(speakers)s, %(description)s, %(video_urls)s, %(video_hosts)s,
  %(thumbnail_url)s, %(duration_seconds)s, %(language)s, %(copyright_text)s, %(llm_terms)s,
  %(raw_ref)s, %(now)s, %(now)s, NULL, %(pipeline_version)s)
ON CONFLICT (id) DO UPDATE SET
  blob_sha = EXCLUDED.blob_sha, event_year = EXCLUDED.event_year,
  pyvideo_id = EXCLUDED.pyvideo_id, title = EXCLUDED.title, recorded = EXCLUDED.recorded,
  speakers = EXCLUDED.speakers, description = EXCLUDED.description,
  video_urls = EXCLUDED.video_urls, video_hosts = EXCLUDED.video_hosts,
  thumbnail_url = EXCLUDED.thumbnail_url, duration_seconds = EXCLUDED.duration_seconds,
  language = EXCLUDED.language, copyright_text = EXCLUDED.copyright_text,
  llm_terms = EXCLUDED.llm_terms, raw_ref = EXCLUDED.raw_ref, changed_at = EXCLUDED.changed_at,
  unlisted_at = NULL, pipeline_version = EXCLUDED.pipeline_version
RETURNING (xmax = 0) AS inserted
"""

# A release is read on every run and rewritten only when what GitHub says about
# it changed (an edited body, a renamed release, a pre-release made final).
_RELEASE_UPSERT = """
INSERT INTO official_release (id, repo_key, provider, tag, name, published_at, html_url,
  prerelease, raw_ref, first_seen_at, changed_at, pipeline_version)
VALUES (%(id)s, %(repo_key)s, %(provider)s, %(tag)s, %(name)s, %(published_at)s, %(html_url)s,
  %(prerelease)s, %(raw_ref)s, %(now)s, %(now)s, %(pipeline_version)s)
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name, published_at = EXCLUDED.published_at, html_url = EXCLUDED.html_url,
  prerelease = EXCLUDED.prerelease, raw_ref = EXCLUDED.raw_ref,
  changed_at = EXCLUDED.changed_at, pipeline_version = EXCLUDED.pipeline_version
WHERE (official_release.name, official_release.published_at, official_release.html_url,
       official_release.prerelease, official_release.raw_ref)
  IS DISTINCT FROM (EXCLUDED.name, EXCLUDED.published_at, EXCLUDED.html_url,
                    EXCLUDED.prerelease, EXCLUDED.raw_ref)
RETURNING (xmax = 0) AS inserted
"""


def _known_docs(conn, repo_key: str) -> dict[str, tuple]:
    """path -> (blob_sha, unlisted_at) for the repository's stored files."""
    if conn is None:
        return {}
    rows = conn.execute("SELECT path, blob_sha, unlisted_at FROM official_doc "
                        "WHERE repo_key = %s", (repo_key,)).fetchall()
    return {r[0]: tuple(r[1:]) for r in rows}


def _known_talks(conn) -> dict[str, tuple]:
    """path -> (blob_sha, unlisted_at, pyvideo_id, raw_ref) for the stored talks."""
    if conn is None:
        return {}
    rows = conn.execute("SELECT path, blob_sha, unlisted_at, pyvideo_id, raw_ref "
                        "FROM video_ref").fetchall()
    return {r[0]: tuple(r[1:]) for r in rows}


def _upserted(conn, sql: str, row: dict[str, Any]) -> bool | None:
    """True: inserted. False: an existing row changed. None: nothing changed."""
    got = conn.execute(sql, row).fetchone()
    return None if got is None else bool(got[0])


# ── reading one repository ───────────────────────────────────────────────────

@dataclass
class _Run:
    gh: GitHub
    contract: Contract
    store: Any
    conn: Any            # None on a dry run
    now: datetime
    budget: int          # blob fetches left this run
    version: str


def _check_repo(run: _Run, owner_repo: str, licence: str, t: dict[str, Any]) -> bool:
    """The repository's own record: does GitHub still report the licence the
    contract names? A mismatch stops this repository's read (rule 12)."""
    try:
        response = run.gh.get(f"/repos/{owner_repo}")
    except RequestFailed as exc:
        t.update(outcome="http_error")
        t["problems"].append(f"repository record: {exc}")
        return False
    if response.status_code != 200:
        t.update(outcome="http_error", http_status=response.status_code)
        t["problems"].append(f"repository record: HTTP {response.status_code}")
        return False
    reported = ((response.json() or {}).get("license") or {}).get("spdx_id")
    if reported != licence:
        t.update(outcome="licence_mismatch")
        t["problems"].append(f"the contract says {licence}, GitHub reports {reported or 'none'}; "
                             "not read until the contract is reviewed")
        return False
    return True


def _tree(run: _Run, owner_repo: str, branch: str, t: dict[str, Any]):
    """(blobs, complete) - complete is False when GitHub truncated the listing,
    and then nothing is marked unlisted, because absence from a cut list is not
    absence from the repository."""
    try:
        response = run.gh.get(f"/repos/{owner_repo}/git/trees/{quote(branch, safe='')}",
                              params={"recursive": "1"})
    except RequestFailed as exc:
        t.update(outcome="http_error")
        t["problems"].append(f"tree: {exc}")
        return None, False
    if response.status_code != 200:
        t.update(outcome="http_error", http_status=response.status_code)
        t["problems"].append(f"tree: HTTP {response.status_code}")
        return None, False
    listing = response.json()
    blobs = [e for e in listing.get("tree") or [] if e.get("type") == "blob"]
    complete = listing.get("truncated") is not True
    if not complete:
        t["problems"].append("tree listing truncated by GitHub; removals not checked")
    return blobs, complete


def _plan(run: _Run, keep: list[dict], known: dict[str, tuple], t: dict[str, Any],
          relist: Callable[[str], None]) -> list[dict]:
    """Which listed files to fetch: new or changed sha, within size. An unchanged
    file that had dropped out of the listing and is back is marked listed again."""
    to_fetch = []
    for entry in sorted(keep, key=lambda e: e["path"]):
        prior = known.get(entry["path"])
        if prior is not None and prior[0] == entry["sha"]:
            t["files_unchanged"] += 1
            if prior[1] is not None and run.conn is not None:
                relist(entry["path"])
            continue
        # A listing without a size (GitHub gives one for every blob) is fetched:
        # the run's cap still bounds it, and skipping it would lose the file.
        if (entry.get("size") or 0) > run.contract.max_blob_bytes:
            t["files_too_large"] += 1
            continue
        to_fetch.append(entry)
    return to_fetch


def _fetch_each(run: _Run, owner_repo: str, to_fetch: list[dict], t: dict[str, Any],
                write: Callable[[dict, bytes], bool | None]) -> None:
    """Fetch within the run's budget; the rest are deferred. `write` stores one
    file and says whether it was new (True), changed (False) or neither (None)."""
    for i, entry in enumerate(to_fetch):
        if run.budget <= 0:
            t["files_deferred"] += len(to_fetch) - i
            return
        try:
            fetched = run.gh.blob(owner_repo, entry["sha"])
        except _Stop:
            t["files_deferred"] += len(to_fetch) - i
            raise
        except ValueError as exc:
            run.budget -= 1          # an attempt that failed still spent a request
            t["files_failed"] += 1
            if len(t["problems"]) < 5:
                t["problems"].append(f"{entry['path']}: {exc}")
            continue
        run.budget -= 1
        t["files_fetched"] += 1
        try:
            outcome = write(entry, fetched)
        except ValueError as exc:
            t["files_failed"] += 1
            if len(t["problems"]) < 5:
                t["problems"].append(f"{entry['path']}: {exc}")
            continue
        if outcome is True:
            t["files_new"] += 1
        elif outcome is False:
            t["files_changed"] += 1


_UNLIST_DOCS = ("UPDATE official_doc SET unlisted_at = %s "
                "WHERE path = ANY(%s) AND repo_key = %s")
_UNLIST_TALKS = "UPDATE video_ref SET unlisted_at = %s WHERE path = ANY(%s)"


def _mark_unlisted(run: _Run, sql: str, known: dict[str, tuple], listed: set[str],
                   t: dict[str, Any], *args: Any) -> None:
    """A stored file a complete listing no longer has in scope - deleted
    upstream, or excluded since by a changed glob or year - is marked, never
    deleted: what was read stays readable, and the reader can tell it is gone."""
    gone = [p for p, prior in known.items() if p not in listed and prior[1] is None]
    t["files_unlisted"] = len(gone)
    if gone and run.conn is not None:
        run.conn.execute(sql, (run.now, gone, *args))


def _doc_writer(run: _Run, repo: Repo):
    def write(entry: dict, payload: bytes) -> bool | None:
        path = entry["path"]
        fmt = path.rsplit(".", 1)[-1].lower() if "." in path.rsplit("/", 1)[-1] else "none"
        raw_ref = run.store.put(payload).ref
        text_ref, h1 = None, None
        if fmt == "ipynb":
            try:
                nb = flatten_notebook(payload)
            except ValueError:
                nb = None   # the raw file is kept; text_ref stays NULL (rule 6)
            if nb is not None:
                text_ref = run.store.put(nb.text, namespace=FLATTENED).ref
                h1 = nb.h1
        elif fmt == "md" and repo.kind != "spec":
            # Markdown is its own text - except in a spec repository, whose rows
            # carry no text (official_doc_spec_has_no_text_ck), so a `.md` added
            # to a spec's include list is stored rather than refused.
            text_ref = raw_ref
            try:
                h1 = first_h1(payload.decode("utf-8"))
            except UnicodeDecodeError:
                h1 = None
        title, title_source = title_for(path, h1)
        row = {
            "id": stable_id("odoc", repo.key, path), "repo_key": repo.key,
            "provider": repo.provider, "doc_kind": DOC_KIND[repo.kind], "path": path,
            "format": fmt, "blob_sha": entry["sha"], "size_bytes": len(payload),
            "licence": repo.licence,
            "html_url": f"https://github.com/{repo.repo}/blob/{quote(repo.branch)}/{quote(path)}",
            "title": title, "title_source": title_source, "raw_ref": raw_ref,
            "text_ref": text_ref, "now": run.now, "pipeline_version": run.version,
        }
        if run.conn is None:
            return True
        return _upserted(run.conn, _DOC_UPSERT, row)
    return write


def _read_releases(run: _Run, repo: Repo, t: dict[str, Any]) -> None:
    """Every page of the releases API up to `max_release_pages`. Drafts are not
    public and never listed to us; a release with no tag or link is skipped."""
    releases: list[dict] = []
    complete = False
    for page in range(1, run.contract.max_release_pages + 1):
        try:
            response = run.gh.get(f"/repos/{repo.repo}/releases",
                                  params={"per_page": RELEASES_PER_PAGE, "page": page})
        except RequestFailed as exc:
            t["problems"].append(f"releases page {page}: {exc}")
            t["outcome"] = "partial"
            break
        if response.status_code != 200:
            t["problems"].append(f"releases page {page}: HTTP {response.status_code}")
            t["outcome"] = "partial"
            break
        batch = response.json()
        if not isinstance(batch, list):
            t["problems"].append(f"releases page {page}: not a list")
            t["outcome"] = "partial"
            break
        releases.extend(batch)
        if 'rel="next"' not in (response.headers.get("link") or ""):
            complete = True
            break
    else:
        t["problems"].append(f"releases: stopped at max_release_pages "
                             f"({run.contract.max_release_pages}); older releases not read")
    if not complete and t["outcome"] == "ok":
        t["outcome"] = "partial"
    for r in releases:
        if not isinstance(r, dict) or r.get("draft") or not r.get("tag_name") \
                or not r.get("html_url"):
            continue
        t["releases_seen"] += 1
        when = r.get("published_at")
        row = {
            "id": stable_id("orel", repo.key, r["tag_name"]), "repo_key": repo.key,
            "provider": repo.provider, "tag": r["tag_name"],
            "name": (r.get("name") or "").strip() or None,
            "published_at": datetime.fromisoformat(when.replace("Z", "+00:00")) if when else None,
            "html_url": r["html_url"], "prerelease": bool(r.get("prerelease")),
            # THE RELEASE AS GITHUB GAVE IT, one record in the house JSON
            # spelling - its notes are its `body`. Never the notes picked out
            # alone: the raw store keeps the platform's bytes, and anything
            # derived is derived from them (tests/test_writers_store_the_payload.py).
            "raw_ref": run.store.put(json.dumps(r, sort_keys=True, ensure_ascii=False)).ref,
            "now": run.now, "pipeline_version": run.version,
        }
        outcome = True if run.conn is None else _upserted(run.conn, _RELEASE_UPSERT, row)
        if outcome is True:
            t["releases_new"] += 1
        elif outcome is False:
            t["releases_changed"] += 1


def _read_repo(run: _Run, repo: Repo, t: dict[str, Any]) -> None:
    if not _check_repo(run, repo.repo, repo.licence, t):
        return
    blobs, complete = _tree(run, repo.repo, repo.branch, t)
    if blobs is None:
        return
    keep = [e for e in blobs if selected(e["path"], repo.include, repo.exclude)]
    t["files_listed"] = len(keep)
    known = _known_docs(run.conn, repo.key)
    to_fetch = _plan(run, keep, known, t, lambda path: run.conn.execute(
        "UPDATE official_doc SET unlisted_at = NULL WHERE repo_key = %s AND path = %s",
        (repo.key, path)))
    _fetch_each(run, repo.repo, to_fetch, t, _doc_writer(run, repo))
    if complete:
        _mark_unlisted(run, _UNLIST_DOCS, known, {e["path"] for e in keep}, t, repo.key)
    if repo.kind == "sdk":
        _read_releases(run, repo, t)


def _read_pyvideo(run: _Run, pv: PyVideo, t: dict[str, Any]) -> None:
    """PyVideo's talks in events from `min_event_year` on, NO_PUBLISH honoured.

    A WITHHELD TALK IS READ AGAIN NEXT RUN. Nothing about it is stored - not a
    row, not its bytes - so there is nothing to compare its sha with. That is at
    most one read per listed id per run (2 ids on 2026-10-30).

    A STORED TALK THAT IS LISTED IS WITHDRAWN, found either way: by the id
    stored with it, or - for a talk stored with no id that gained a listed one
    later - by the id in its newly fetched record (#591 review).

    WHAT A WITHDRAWAL TOMBSTONES IS THE BYTES THE ROW POINTS AT: the talk's
    latest stored version. An earlier version, stored before the record changed,
    is not tracked by any row and stays in the raw store untouched. The
    tombstone is immediate; the row's DELETE commits with the source, so if the
    source then fails the row survives pointing at tombstoned bytes - the safe
    direction for a takedown, and the next run deletes it."""
    if not _check_repo(run, pv.repo, pv.licence, t):
        return
    blobs, complete = _tree(run, pv.repo, pv.branch, t)
    if blobs is None:
        return
    by_path = {e["path"]: e for e in blobs}
    listed = by_path.get(pv.no_publish_path)
    if listed is None:
        t.update(outcome="error")
        t["problems"].append(f"{pv.no_publish_path} is not in the tree: talks are not read "
                             "without it (an absent list is not an empty one)")
        return
    try:
        withheld_ids = no_publish_ids(run.gh.blob(pv.repo, listed["sha"]))
    except ValueError as exc:
        t.update(outcome="error")
        t["problems"].append(f"{pv.no_publish_path}: {exc}; talks are not read without it")
        return

    talk = glob_regex(pv.talk_glob)
    in_scope = []
    for entry in blobs:
        if not talk.match(entry["path"]):
            continue
        year = event_year(entry["path"].split("/", 1)[0])
        if year is None:
            t["talks_no_year"] += 1
        elif year < pv.min_event_year:
            t["talks_before_min_year"] += 1
        else:
            in_scope.append(entry | {"event_year": year})
    t["files_listed"] = len(in_scope)
    known = _known_talks(run.conn)

    def withdraw(path: str, pid: int) -> None:
        """Stored before PyVideo listed it: the row goes, and its stored bytes
        are tombstoned as a takedown - "never stored" holds from here on."""
        raw_ref = known.pop(path)[3]
        t["talks_withdrawn"] += 1
        if run.conn is not None:
            run.store.tombstone(raw_ref, reason="takedown-request",
                                detail=f"PyVideo {pv.no_publish_path} lists talk id {pid}")
            run.conn.execute("DELETE FROM video_ref WHERE path = %s", (path,))

    for path, (_sha, _unlisted, pid, _ref) in list(known.items()):
        if pid is not None and pid in withheld_ids:
            withdraw(path, pid)

    to_fetch = _plan(run, in_scope, known, t, lambda path: run.conn.execute(
        "UPDATE video_ref SET unlisted_at = NULL WHERE path = %s", (path,)))

    def write(entry: dict, payload: bytes) -> bool | None:
        rec = parse_talk(payload, entry["path"], pv)
        if rec["pyvideo_id"] is not None and rec["pyvideo_id"] in withheld_ids:
            if entry["path"] in known:
                withdraw(entry["path"], rec["pyvideo_id"])   # stored with no id
            else:
                t["talks_withheld"] += 1
            return None
        row = rec | {"id": stable_id("video", entry["path"]), "blob_sha": entry["sha"],
                     "event_year": entry["event_year"], "raw_ref": run.store.put(payload).ref,
                     "now": run.now, "pipeline_version": run.version}
        if run.conn is None:
            return True
        return _upserted(run.conn, _TALK_UPSERT, row)

    _fetch_each(run, pv.repo, to_fetch, t, write)
    if complete:
        _mark_unlisted(run, _UNLIST_TALKS, known, {e["path"] for e in in_scope}, t)


# ── one run ──────────────────────────────────────────────────────────────────

def harvest(conn, client, *, terms: Callable[[], None], token: str | None = None,
            store=None, contract: Contract | None = None, only: set[str] | None = None,
            dry_run: bool = False, limiter=None,
            clock=lambda: datetime.now(UTC)) -> dict[str, Any]:
    """Read every repository and PyVideo once (or only the keys named).

    `terms` is REQUIRED and runs before the first request: the CLI passes
    `check_github_terms`. There is no default, so no caller can forget it.

    DRY RUN: every read happens (within the same caps), nothing is written -
    no row, no raw-store payload - and no database is read, so every file
    counts as new AND IS FETCHED: a dry run spends the shared token's budget
    like a first real run (2,529 calls on 2026-10-30, every source).

    COMMITTED AS IT GOES otherwise: after each repository, so a failure late in
    a run costs only the repository it was reading."""
    contract = contract or load_contract()
    if only is not None:
        keys = {r.key for r in contract.repos} | {contract.pyvideo.key}
        unknown = sorted(only - keys)
        if unknown or not only:
            raise OfficialHarvestError(
                f"--only names {', '.join(unknown) or 'no source'}, not a source in "
                f"contract/official_sources.yaml ({', '.join(sorted(keys))}). Nothing was read: "
                "a run that matches no source would report success having read nothing.")
    token = token if token is not None else settings().github_token
    if not token:
        raise OfficialHarvestError(
            "GITHUB_TOKEN is not set. The harvest makes thousands of API calls and the "
            "unauthenticated budget is 60 an hour; it does not run without one.")
    terms()
    if dry_run:
        conn, store = None, DryStore()
    elif store is None:
        from collect.rawstore import RawStore
        store = RawStore()
    run = _Run(GitHub(client, contract, token, limiter=limiter), contract, store, conn, clock(),
               contract.max_blob_fetches_per_run, settings().pipeline_version)
    run_id = f"official_{uuid.uuid4().hex[:12]}"
    sources: list[tuple[str, Any]] = [(r.key, r) for r in contract.repos]
    sources.append((contract.pyvideo.key, contract.pyvideo))
    out: dict[str, Any] = {"run_id": run_id, "dry_run": dry_run, "by_source": {}}
    stopped: str | None = None
    for key, source in sources:
        if only and key not in only:
            continue
        is_pv = isinstance(source, PyVideo)
        t = _tally(talks=is_pv, releases=not is_pv and source.kind == "sdk")
        calls_before = run.gh.calls
        at = clock()
        if stopped:
            t.update(outcome="rate_limited")
            t["problems"].append(f"not read: the run stopped earlier ({stopped})")
        else:
            try:
                (_read_pyvideo if is_pv else _read_repo)(run, source, t)
            except _Stop as stop:
                stopped = str(stop)
                t.update(outcome="rate_limited")
                t["problems"].append(str(stop))
        _settle(t)
        t.update(run_id=run_id, source_key=key, fetched_at=at,
                 api_calls=run.gh.calls - calls_before, rate_remaining=run.gh.remaining)
        if conn is not None:
            conn.execute(_FETCH_INSERT, t)
            conn.commit()
        out["by_source"][key] = {k: v for k, v in t.items()
                                 if k not in ("problems", "run_id", "fetched_at")}
    out["api_calls"] = run.gh.calls
    out["rate_remaining"] = run.gh.remaining
    out["stopped"] = stopped
    return out


def check_github_terms() -> None:
    """The `github-api-terms` ruling, checked as scripts/harvest_github.py does:
    a known unexpired ruling, evidence not stale, and this run's own observation
    of the access path - the REST API."""
    from collect.registry.assertions import assert_terms_reviewed
    from collect.registry.sources import load_sources

    contract = load_sources()
    github = next(s for s in contract.platforms if s["id"] == "github")
    assert_terms_reviewed([github], rulings=contract.rulings,
                          observations={"github": {"access_path": "api"}},
                          today=datetime.now(UTC).date())
