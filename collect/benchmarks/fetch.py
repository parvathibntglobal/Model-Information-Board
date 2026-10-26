"""Stage 1: get the page, politely, and say exactly what came back (doc 4).

    static     HTTP GET through `collect.http.build_client` (identifying
               User-Agent), robots.txt asked first, 3 retries with 2/4/8 s backoff
    browser    headless Chromium in its own process, fresh context, downloads
               off, the same User-Agent, robots.txt asked first
    data_file  a file the site offers its visitors; only while
               `allow_data_files` is true (doc 4.1 steps 5-8)

L2 (doc 20.1) is checked here: HTTP 200, a minimum size, not a block page.
A failure is a value, never an exception: the runner records it and moves on
to the next source (golden rule 1).
"""

from __future__ import annotations

import contextlib
import hashlib
import re
import time
from dataclasses import dataclass

import httpx

from collect.adapters.blog.robots import RobotsGate
from collect.benchmarks.config import Config, Source
from collect.config import settings
from collect.http import build_client

BACKOFF_SECONDS = (2, 4, 8)
#: How long a rendered page may take to go network-quiet before it is read anyway.
IDLE_WAIT_MS = 10_000


@dataclass
class Fetched:
    ok: bool
    method: str
    url: str
    http_status: int | None = None
    content: bytes = b""
    content_type: str = ""
    final_url: str | None = None
    error: str | None = (
        None  # reason code: fetch_error | blocked_page | robots_denied | data_files_off
    )
    detail: str = ""
    attempts: int = 0

    @property
    def size(self) -> int:
        return len(self.content)

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.content).hexdigest()

    @property
    def redirected(self) -> bool:
        """A different page, not the same one with a client-side "#/" route."""
        if not self.final_url:
            return False
        return self.final_url.split("#", 1)[0].rstrip("/") != self.url.split("#", 1)[0].rstrip("/")


class Fetcher:
    """One per run: one HTTP client, one robots cache, at most one browser."""

    def __init__(self, config: Config, *, client: httpx.Client | None = None):
        self.config = config
        self.user_agent = settings().user_agent
        timeouts = config.settings["timeouts"]
        self.static_timeout = float(timeouts["static_seconds"])
        self.browser_timeout_ms = int(float(timeouts["browser_seconds"]) * 1000)
        self.retries = int(config.settings["retries"])
        self.client = client or build_client(follow_redirects=True, timeout=self.static_timeout)
        self.robots = RobotsGate(self.client, user_agent=self.user_agent)
        self._sleep = time.sleep

    def close(self) -> None:
        self.client.close()

    # ── entry point ──────────────────────────────────────────────────────

    def fetch(self, source: Source, *, wait_for: str | None = None) -> Fetched:
        if source.method == "data_file" and not self.config.settings["allow_data_files"]:
            return Fetched(
                ok=False,
                method=source.method,
                url=source.url,
                error="data_files_off",
                detail="allow_data_files is false in module_settings.yaml",
            )
        if self.config.settings["respect_robots"]:
            decision = self.robots.allows(source.url)
            if not decision.allowed:
                return Fetched(
                    ok=False,
                    method=source.method,
                    url=source.url,
                    error="robots_denied",
                    detail=decision.reason,
                )
        if source.method == "browser":
            got = self._browser(source.url, wait_for=wait_for)
        else:
            got = self._static(source.url, method=source.method)
        if got.ok:
            self._check_l2(got, html=source.method != "data_file")
        return got

    # ── methods ──────────────────────────────────────────────────────────

    def _static(self, url: str, *, method: str) -> Fetched:
        last = ""
        for attempt in range(1, self.retries + 2):
            try:
                response = self.client.get(url)
            except httpx.HTTPError as error:
                last = f"{type(error).__name__}: {error}"
            else:
                if response.status_code < 500:
                    return Fetched(
                        ok=response.status_code == 200,
                        method=method,
                        url=url,
                        http_status=response.status_code,
                        content=response.content,
                        content_type=response.headers.get("content-type", ""),
                        final_url=str(response.url),
                        error=None if response.status_code == 200 else "fetch_error",
                        detail=""
                        if response.status_code == 200
                        else f"HTTP {response.status_code}",
                        attempts=attempt,
                    )
                last = f"HTTP {response.status_code}"
            if attempt <= len(BACKOFF_SECONDS) and attempt <= self.retries:
                self._sleep(BACKOFF_SECONDS[attempt - 1])
        return Fetched(
            ok=False,
            method=method,
            url=url,
            error="fetch_error",
            detail=last,
            attempts=self.retries + 1,
        )

    def _browser(self, url: str, *, wait_for: str | None) -> Fetched:
        """Chromium in its own process, a fresh profile, closed after the page.

        No saved logins or cookies, downloads blocked (doc 22.3 #25). The page
        is read after the network goes idle and, when the mapping names one,
        after its `must_contain` text appears.
        """
        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import sync_playwright
        except ImportError:
            return Fetched(
                ok=False,
                method="browser",
                url=url,
                error="fetch_error",
                detail=(
                    "playwright is not installed "
                    "(pip install playwright; playwright install chromium)"
                ),
            )
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                try:
                    context = browser.new_context(
                        user_agent=self.user_agent, accept_downloads=False
                    )
                    page = context.new_page()
                    # "load", then a SHORT wait for the network to go quiet: a page
                    # with analytics beacons (epoch.ai) never goes idle, and
                    # waiting for it timed out with the table already drawn.
                    response = page.goto(url, wait_until="load", timeout=self.browser_timeout_ms)
                    with contextlib.suppress(PlaywrightError):
                        page.wait_for_load_state("networkidle", timeout=IDLE_WAIT_MS)
                    status = response.status if response else None
                    if wait_for and status == 200:
                        # A table that never appears is reported by parse, with its reason.
                        with contextlib.suppress(PlaywrightError):
                            page.wait_for_selector(
                                f"text={wait_for}", timeout=self.browser_timeout_ms
                            )
                    html = page.content()
                    final = page.url
                finally:
                    browser.close()
        except Exception as error:  # noqa: BLE001 - one source failing never stops the run
            return Fetched(
                ok=False,
                method="browser",
                url=url,
                error="fetch_error",
                detail=f"{type(error).__name__}: {str(error).splitlines()[0][:200]}",
            )
        return Fetched(
            ok=status == 200,
            method="browser",
            url=url,
            http_status=status,
            content=html.encode("utf-8"),
            content_type="text/html; charset=utf-8",
            final_url=final,
            error=None if status == 200 else "fetch_error",
            detail="" if status == 200 else f"HTTP {status}",
            attempts=1,
        )

    # ── L2 ───────────────────────────────────────────────────────────────

    def _check_l2(self, got: Fetched, *, html: bool) -> None:
        rules = self.config.validation["fetch"]
        if got.size < int(rules["min_bytes"]):
            got.ok, got.error = False, "blocked_page"
            got.detail = f"only {got.size} bytes (minimum {rules['min_bytes']})"
            return
        if html:
            head = visible_text(got.content[:200_000])[:4000].lower()
            for marker in rules["block_page_markers"]:
                if marker.lower() in head:
                    got.ok, got.error = False, "blocked_page"
                    got.detail = f"block-page marker {marker!r} in the page text"
                    return


_TAGS = re.compile(rb"<(script|style)\b.*?</\1>|<[^>]+>", re.S | re.I)


def visible_text(html: bytes) -> str:
    """Rough page text for marker checks: tags, scripts and styles removed."""
    return " ".join(_TAGS.sub(b" ", html).decode("utf-8", "replace").split())
