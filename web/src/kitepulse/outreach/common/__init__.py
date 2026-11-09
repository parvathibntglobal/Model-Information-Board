"""Kite Pulse outreach: what every platform's Finder shares.

    thread.py    the Thread record, statuses, drop reasons and flags
    filters.py   the code filters (no model)
    config.py    loads a platform's config/*.yaml; a missing key is an error
    text.py      HTML to plain text, for a person to read
    match.py     phrase matching in code, for sources we cannot search
    http.py      a GET-only, paced client that obeys robots.txt

Each platform folder (`hackernews/`, `discourse/`, `devto/`) imports these as `common.*`;
its `find.py` puts this folder's parent on `sys.path`.
"""
