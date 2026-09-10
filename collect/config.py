"""Settings and contract paths.

Credentials and environment come from the process environment (see
`.env.example`). Everything that is *policy* — thresholds, weights,
half-lives, the capability list, alias variants, filter rules — lives in
versioned YAML under `contract/`, never here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DIR = REPO_ROOT / "contract"

TABLES_SQL = CONTRACT_DIR / "tables.sql"
SEED_MODELS_YAML = CONTRACT_DIR / "seed_models.yaml"
CAPABILITIES_YAML = CONTRACT_DIR / "capabilities.yaml"
CONDITIONS_YAML = CONTRACT_DIR / "conditions.yaml"

#: Stamped onto every derived row so any change is re-runnable and diffable
#: (NFR-4). Bump it whenever collect/ changes what it produces.
PIPELINE_VERSION = "collect-0.1.0"


@dataclass(frozen=True)
class Settings:
    """Process configuration. Read once, passed explicitly after that."""

    environment: str
    database_url: str | None
    raw_store_path: Path
    user_agent: str
    github_token: str | None
    #: Direct Reddit OAuth. Unused while access goes through RapidAPI — kept
    #: rather than deleted because the terms ruling has not been made, and a
    #: ruling that lands the other way needs them back.
    reddit_client_id: str | None
    reddit_client_secret: str | None

    #: RapidAPI, which proxies Reddit's official API rather than scraping it:
    #: the responses carry `kind`/`data` envelopes, `t2_`/`t3_` fullnames,
    #: `subreddit_id` and `created_utc` as an epoch float, none of which a
    #: scraper reconstructing from HTML can produce. Measured 2026-08-14.
    rapidapi_key: str | None
    #: The BARE HOST, e.g. `reddit34.p.rapidapi.com`. RapidAPI routes on the
    #: `x-rapidapi-host` header, so a full URL here silently addresses nothing.
    #:
    #: ⚠ SHARED, AND THAT WAS A DEFECT. `.env` declared this twice - once for
    #: Reddit and once for X - and the last one won, so the Reddit adapter
    #: addressed X's host and got 404 on every search. It is still read, but
    #: `reddit.py` now refuses it when it names a non-Reddit provider, and
    #: `reddit_provider` below is the setting that actually decides.
    rapidapi_host: str | None

    #: WHICH RAPIDAPI PROVIDER FRONTS REDDIT. Mirrors `scraper_provider` for X,
    #: for the same reason and after the same failure: one variable cannot
    #: address two vendors. `reddit34` is the provider this project has used.
    reddit_provider: str | None

    #: WHICH RAPIDAPI PROVIDER FRONTS X. `twitter241` today, and the host is
    #: DERIVED from it - `collect/adapters/x.py:host_for` turns it into
    #: `<provider>.p.rapidapi.com`. Moving provider is then an environment
    #: change rather than a code change.
    #:
    #: NOT DEFAULTED. An unconfigured process must not quietly call one
    #: particular vendor, so `host_for` raises rather than assuming (rule 6:
    #: a missing value is never silently converted into a definite one).
    #:
    #: There is NO `x_bearer_token`, deliberately. The X route is a RapidAPI
    #: scraper provider and not X's own API, so the credential is a RapidAPI
    #: key - `x_rapidapi_key` below, falling back to `rapidapi_key`.
    #:
    #: ⚠ IT IS NOT NECESSARILY THE SAME KEY AS REDDIT'S, AND THIS COMMENT SAID
    #: IT WAS. "the same key the Reddit path uses, billing the same
    #: subscription" was asserted here, in `.env.example` and in
    #: `judge/app.py`, and it is false on this project's own `.env`. Measured
    #: 2026-09-10, four requests: the Reddit key returns 200 on
    #: `reddit34` and 403 on `twitter241`; the X key does the exact reverse.
    #: Two accounts, two meters, two limits - 1,000,000 and 100,000, both read
    #: off `x-ratelimit-requests-limit` the same day.
    #: `docs/measurements/quota-headers.jsonl`.
    #:
    #: ⚠ A KEY IS NOT A CLEARANCE, AND THIS VALUE IS PINNED BY THE RULING.
    #: `contract/sources.yaml:x-via-rapidapi-scraper` (ratified 2026-09-08)
    #: names `twitter241` as a LIVE PRECONDITION, so setting this to anything
    #: else refuses at the terms gate rather than silently parsing a different
    #: provider's response envelope and reporting the platform as quiet. The
    #: ruling permits internal development only, while nothing is published
    #: externally - it clears none of the four conditions it records.
    scraper_provider: str | None

    #: X's OWN RAPIDAPI KEY. Mirrors `reddit_provider` for the host: one arm,
    #: one variable, after the same failure one variable over.
    #:
    #: ⚠ A KEY CANNOT BE VALIDATED BY INSPECTION, WHICH IS WHY THIS IS NOT
    #: SHAPED LIKE `host_for`. `reddit.py:host_for` can refuse a wrong host
    #: because `twitter241.p.rapidapi.com` visibly is not Reddit's. A key is
    #: 50 opaque characters, so nothing here can tell whose it is, and a wrong
    #: one comes back as a gateway 403 - indistinguishable from the platform
    #: refusing us, which is the failure `.env.example` already records.
    #:
    #: So the fallback to `rapidapi_key` is KEPT - a single RapidAPI account
    #: subscribed to both providers is a legitimate setup and was the assumed
    #: one - and `x.py:key_for` returns the VARIABLE NAME alongside the key so
    #: every refusal and every status line can say which was used. Naming the
    #: source is the honest substitute for a validation that cannot exist.
    x_rapidapi_key: str | None

    pipeline_version: str

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


def _load_dotenv() -> None:
    """Populate os.environ from .env if python-dotenv is installed.

    Absent dotenv is not an error: the process environment is the source of
    truth, and .env is only a developer convenience.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(REPO_ROOT / ".env", override=False)


def _bare_host(value: str | None) -> str | None:
    """`https://h/path?x=1` -> `h`. RapidAPI routes on a host, not a URL.

    Returns None for an empty value so an unset variable stays unset: an
    absent credential must not become a definite one (rule 6).
    """
    if not value:
        return None
    from urllib.parse import urlsplit

    trimmed = value.strip()
    if "//" in trimmed:
        return urlsplit(trimmed).hostname or None
    return trimmed.split("/")[0] or None


@lru_cache(maxsize=1)
def settings() -> Settings:
    _load_dotenv()
    return Settings(
        environment=os.getenv("ENVIRONMENT", "development"),
        database_url=os.getenv("DATABASE_URL") or None,
        raw_store_path=Path(os.getenv("RAW_STORE_PATH", str(REPO_ROOT / "raw_store"))),
        # NFR-5: an identifying User-Agent with a contact URL, on every
        # request, to every platform. Not optional — so there is no default
        # that would let an anonymous request out of the building.
        user_agent=os.getenv("USER_AGENT", ""),
        github_token=os.getenv("GITHUB_TOKEN") or None,
        reddit_client_id=os.getenv("REDDIT_CLIENT_ID") or None,
        reddit_client_secret=os.getenv("REDDIT_CLIENT_SECRET") or None,
        rapidapi_key=os.getenv("RAPIDAPI_KEY") or None,
        # Tolerated rather than trusted: the value in .env today is a full
        # endpoint URL, and a host header carrying a URL matches no route.
        # Normalised here so one bad paste does not read as "the API is down".
        rapidapi_host=_bare_host(os.getenv("RAPIDAPI_HOST")),
        reddit_provider=os.getenv("REDDIT_PROVIDER") or None,
        scraper_provider=os.getenv("SCRAPER_PROVIDER") or None,
        x_rapidapi_key=os.getenv("X_RAPIDAPI_KEY") or None,
        pipeline_version=os.getenv("PIPELINE_VERSION", PIPELINE_VERSION),
    )
