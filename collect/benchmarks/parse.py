"""Stage 2: locate the data in what was fetched and reshape it (doc 5).

    html_table     the first <table> whose text contains `must_contain`
    embedded_json  a <script id=...> JSON block the page ships its own data in
    next_flight    the Next.js flight data (self.__next_f) the page is built from
    gradio_config  the table in a Gradio app's own config (2026-11-03)
    html_rows      a board drawn as a list of entries, not a <table> (2026-11-03)

Every table becomes rows of `{header: raw text}`, then raw observations, one
per (row, mapped header). Nothing is converted here: values stay text until
`values`. L3 (doc 20.1) is checked here - a header the mapping expects and
the page does not have is `layout_changed`, and the source keeps its old values.

Ranks are only ever the BOARD's: a printed rank column, the row position on a
board that prints its rows in rank order, or the order of the field the board
sorts by. A rank among our own tracked models is never computed (Parvathi,
2026-10-22: raw values only).
"""

from __future__ import annotations

import html as html_module
import json
import re
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup

from collect.benchmarks.config import Source, Table
from collect.benchmarks.values import the_number

_FOOTNOTES = re.compile(r"[*†‡§¹²³⁴⁵⁶⁷⁸⁹⁰]+")
_ARROWS = re.compile(r"[↑↓▲▼△▽⬆⬇]")


def clean_label(text: Any) -> str:
    """Trim, collapse spaces (incl. non-breaking), drop arrows and footnote marks."""
    s = str(text if text is not None else "").replace("\xa0", " ")
    s = _ARROWS.sub(" ", s)
    s = _FOOTNOTES.sub("", s)
    return " ".join(s.split())


@dataclass
class RawObservation:
    source_key: str
    table_index: int
    raw_model_name: str
    benchmark: str
    metric: str
    raw_text: str
    url: str
    scale: str | None = None
    variant: str | None = None
    raw_setting: str | None = None
    collected_on: str | None = None  # the source's own date for this value, if it gives one
    rank_board: str | None = None
    rank_out_of: int | None = None
    row_index: int = 0
    priority: int | None = None
    duplicates: str | None = None
    # A rank worked out from the board's order (row_order / order_by) that
    # another row shares: "25" for three models is a tie (2026-10-27).
    tied: bool = False


@dataclass
class Parsed:
    rows_parsed: int = 0
    observations: list[RawObservation] = field(default_factory=list)
    problems: list[tuple[str, str]] = field(default_factory=list)  # (reason code, message)
    tables_found: int = 0
    notes: list[str] = field(default_factory=list)
    release: str | None = None  # the page's release date, when the table reads one

    @property
    def blocked(self) -> bool:
        return any(code in ("layout_changed", "table_not_found") for code, _ in self.problems)


# ── locate ───────────────────────────────────────────────────────────────────

#: Keys a located row may carry besides its headers: the model name and the
#: setting read from inside the model cell (`model_selector`, `setting_attr`).
MODEL_KEY = "\x00model"
SETTING_KEY = "\x00setting"
LINK_KEY = "\x00link"  # the model cell's own link, for `setting_from_page_data`


def _model_cell(cell, table: Table | None) -> dict[str, str]:
    """The name (and setting) from inside the model cell, when the mapping says where.

    LiveBench renders `<span class="nm" data-tip="Kimi K3 · reasoning effort: max">Kimi K3</span>
    <span class="opn">open</span>`: the cell's whole text would be "Kimi K3 open".
    """
    out: dict[str, str] = {}
    if table is not None and table.setting_from_page_data:
        link = cell.find("a", href=True)
        if link is not None:
            out[LINK_KEY] = link["href"]
    if table is None or not table.model_selector:
        return out
    found = cell.select_one(table.model_selector)
    if found is None:
        return out
    out[MODEL_KEY] = clean_label(found.get_text(" "))
    if table.setting_attr and table.setting_pattern:
        match = re.search(table.setting_pattern, found.get(table.setting_attr) or "")
        if match:
            out[SETTING_KEY] = clean_label(match.group(1))
    return out


def locate_html_table(
    html: bytes | str, locate: dict[str, Any], table_config: Table | None = None
) -> tuple[list[str], list[dict[str, str]]] | None:
    soup = BeautifulSoup(html, "lxml")
    needle = clean_label(locate["must_contain"]).lower()
    for table in soup.find_all("table"):
        if needle not in clean_label(table.get_text(" ")).lower():
            continue
        # A page can carry a small pinned copy of its table above the real one
        # (the MMLU-Pro Space: same headers, one row); `min_rows` skips it.
        if len(table.find_all("tr")) < int(locate.get("min_rows", 0)):
            continue
        skip = locate.get("skip_row_class")
        header_rows = table.find("thead").find_all("tr") if table.find("thead") else []
        all_rows = table.find_all("tr")
        if not header_rows:
            header_rows = [all_rows[0]] if all_rows else []
        # Multi-row headers are joined per column ("SWE-bench Verified · % Resolved").
        columns: list[list[str]] = []
        for tr in header_rows:
            cells = tr.find_all(["th", "td"])
            position = 0
            for cell in cells:
                span = int(cell.get("colspan", 1) or 1)
                for _ in range(span):
                    while len(columns) <= position:
                        columns.append([])
                    label = clean_label(cell.get_text(" "))
                    if label and (not columns[position] or columns[position][-1] != label):
                        columns[position].append(label)
                    position += 1
        headers = [" · ".join(parts) for parts in columns]
        body = [tr for tr in all_rows if tr not in header_rows]
        rows = []
        for tr in body:
            if skip and skip in (tr.get("class") or []):
                continue
            cells = tr.find_all(["td", "th"])
            if not cells:
                continue
            row = {
                headers[i] if i < len(headers) else f"col{i}": clean_label(cell.get_text(" "))
                for i, cell in enumerate(cells)
            }
            if table_config is not None and table_config.model_column in headers:
                position = headers.index(table_config.model_column)
                if position < len(cells):
                    row.update(_model_cell(cells[position], table_config))
            rows.append(row)
        return headers, rows
    return None


_NEXT_PUSH = re.compile(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)')


def locate_next_flight(html: bytes | str, locate: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Records from a Next.js page's own data (`self.__next_f.push([1, "..."])`).

    The page ships the data it draws its chart from inside its HTML. Every JSON
    object that starts at `locate.object_start` and carries all of
    `locate.required_keys` is a record; a record seen twice (the page repeats
    them) is kept once, by `locate.unique_key`. Still the page itself, not an
    API (doc 5, embedded_data).
    """
    text = html.decode("utf-8", "replace") if isinstance(html, bytes) else html
    payload = "".join(json.loads('"' + part + '"') for part in _NEXT_PUSH.findall(text))
    if not payload:
        return None
    start = locate["object_start"]
    required = locate["required_keys"]
    unique = locate.get("unique_key")
    decoder = json.JSONDecoder()
    records: dict[Any, dict[str, Any]] = {}
    position = payload.find(start)
    while position != -1:
        try:
            obj, _ = decoder.raw_decode(payload, position)
        except ValueError:
            obj = None
        if isinstance(obj, dict) and all(k in obj for k in required):
            # `records`: the found object holds the list (Scale's {"key": "full",
            # "entries": [...]}), so only that view's entries are read.
            items = obj[locate["records"]] if locate.get("records") else [obj]
            for item in items if isinstance(items, list) else []:
                if isinstance(item, dict):
                    records.setdefault(item.get(unique) if unique else len(records), item)
            if locate.get("records"):
                break
        position = payload.find(start, position + 1)
    return list(records.values()) or None


def locate_embedded_json(html: bytes | str, locate: dict[str, Any]) -> list[dict[str, Any]] | None:
    soup = BeautifulSoup(html, "lxml")
    script = soup.find("script", id=locate["script_id"])
    if script is None or not script.string:
        return None
    data = json.loads(script.string)
    where = locate.get("list_where")
    if where:
        data = next(
            (item for item in data if all(item.get(k) == v for k, v in where.items())), None
        )
        if data is None:
            return None
    # `records` may be a dotted path into the data ("props.pageProps.benchmark.
    # globalLeaderboard", Mercor's Next.js page data; 2026-10-28).
    records = data
    if locate.get("records"):
        for step in locate["records"].split("."):
            records = records.get(step) if isinstance(records, dict) else None
    return records if isinstance(records, list) else None


_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def _cell_text(value: Any) -> str:
    """A Gradio table cell as text: a link's words, never its address."""
    text = "" if value is None else str(value)
    if "<" in text and ">" in text:
        text = BeautifulSoup(text, "lxml").get_text(" ")
    return clean_label(_MD_LINK.sub(r"\1", text))


def locate_gradio_config(
    content: bytes | str, locate: dict[str, Any]
) -> tuple[list[str], list[dict[str, str]]] | None:
    """A table from a Gradio app's own config (2026-11-03).

    A Gradio leaderboard draws its table from the config the app is built from:
    Gradio 4 writes it into the page (`window.gradio_config = {...}`, VBench),
    Gradio 5 and later serve it beside the page as the app's `/config` (Open ASR),
    because the drawn table only ever holds the rows on screen. It is the same
    data the page shows - no API call, no key, no data file.

    The table is the dataframe whose headers include every one of
    `locate.must_contain`; of several (a board and its filtered copy), the one
    with the most rows.
    """
    text = content.decode("utf-8", "replace") if isinstance(content, bytes) else content
    if text.lstrip().startswith("{"):
        config = json.loads(text)
    else:
        found = re.search(r"window\.gradio_config\s*=\s*", text)
        if not found:
            return None
        config, _ = json.JSONDecoder().raw_decode(text, found.end())
    wanted = [clean_label(h) for h in locate["must_contain"]]
    best = None
    for component in config.get("components") or []:
        if component.get("type") != "dataframe":
            continue
        value = (component.get("props") or {}).get("value") or {}
        headers = [clean_label(h) for h in value.get("headers") or []]
        data = value.get("data") or []
        if all(w in headers for w in wanted) and (best is None or len(data) > len(best[1])):
            best = (headers, data)
    if best is None:
        return None
    headers, data = best
    return headers, [dict(zip(headers, (_cell_text(c) for c in row), strict=False)) for row in data]


def locate_html_rows(
    html: bytes | str, locate: dict[str, Any]
) -> tuple[list[str], list[dict[str, str]]] | None:
    """A board drawn as a list of rows that is not a <table> (TTS Arena's cards).

    `container` is the CSS selector of the list, `row` of each entry inside it,
    and `fields` maps a header name to the CSS selector of that value inside
    the entry. An entry without the model's field is not a row.
    """
    soup = BeautifulSoup(html, "lxml")
    container = soup.select_one(locate["container"])
    if container is None:
        return None
    fields: dict[str, str] = locate["fields"]
    rows = []
    for entry in container.select(locate["row"]):
        row = {}
        for header, selector in fields.items():
            found = entry.select_one(selector)
            if found is not None:
                row[header] = clean_label(found.get_text(" "))
        if row.get(locate["model"]):
            rows.append(row)
    return list(fields), rows


def flatten(record: dict[str, Any], prefix: str = "", depth: int = 0) -> dict[str, Any]:
    """A record's nested fields as flat keys a mapping can name (2026-10-28).

    `{"metrics": {"accuracy": 58.2}}` adds "metrics.accuracy"; a list of objects
    is reached by one of its fields, so `{"passScores": [{"pass": "mean-score",
    "score": 69.3}]}` adds "passScores[pass=mean-score].score". The record's own
    keys are kept as they are, so a mapping that names a top-level field reads
    exactly what it did before.
    """
    out: dict[str, Any] = {}
    for key, value in record.items():
        name = f"{prefix}{key}"
        out[name] = value
        if depth >= 4:
            continue
        if isinstance(value, dict):
            out.update(flatten(value, f"{name}.", depth + 1))
        elif isinstance(value, list):
            for item in value:
                if not isinstance(item, dict):
                    continue
                for field, tag in item.items():
                    if isinstance(tag, str) and tag:
                        out.update(flatten(item, f"{name}[{field}={tag}].", depth + 1))
    return out


# ── reshape ──────────────────────────────────────────────────────────────────


def _competition_ranks(values: list[float | None]) -> list[int | None]:
    """Standard competition ranking of the board's own order: 1, 2, 2, 4."""
    ranks: list[int | None] = [None] * len(values)
    order = sorted((i for i, v in enumerate(values) if v is not None), key=lambda i: -values[i])
    previous, previous_rank = None, 0
    for position, i in enumerate(order, start=1):
        if values[i] != previous:
            previous_rank, previous = position, values[i]
        ranks[i] = previous_rank
    return ranks


def labelled_part(text: str, label: str) -> str:
    """The part of a cell that carries "(label)", when a cell holds several.

    ARC Prize's ARC-AGI-3 cell is "52.7%, $7.6K (Standard) · 96.2%, $3.8K
    (Provider Adapter)": two results under two setups. `labelled: Standard`
    reads only the first part; a cell without that part has no value for the
    column (2026-10-28).
    """
    wanted = f"({label})".lower()
    return next((p.strip() for p in text.split("·") if wanted in p.lower()), "")


def _number(text: Any) -> float | None:
    """The cell's one number, read as strictly as a value is (values.the_number);
    None for a cell that cannot be read - it never decides an order."""
    number, error = the_number(text)
    return None if error else number


def _identity(
    row: dict[str, Any], table: Table, model_header: str
) -> tuple[str, str | None, str | None]:
    """(model name, setting, test setup) as the row states them."""
    name = row.get(MODEL_KEY) or clean_label(row.get(model_header))
    setting = (
        clean_label(row.get(table.setting_field)) if table.setting_field else row.get(SETTING_KEY)
    )
    variant = clean_label(row.get(table.variant_field)) if table.variant_field else table.variant
    if name and table.name_pattern:
        split = re.fullmatch(table.name_pattern, name)
        if split:
            parts = split.groupdict()
            name = clean_label(parts["model"])
            if parts.get("variant"):
                variant = clean_label(parts["variant"])
            if parts.get("setting"):
                setting = clean_label(parts["setting"])
    if name and table.bare_setting_words and not setting:
        words = "|".join(re.escape(w) for w in table.bare_setting_words)
        bare = re.fullmatch(rf"(?P<model>.+?)[- ](?P<setting>{words})", name, re.I)
        if bare:
            name, setting = bare["model"], bare["setting"]
    return name, setting, variant


def _page_settings(
    content: bytes | str,
    table: Table,
    rows: list[dict[str, Any]],
    identities: list[tuple[str, str | None, str | None]],
    score_header: str | None,
) -> dict[int, str]:
    """The setting each row was run at, from the page's own data (2026-11-03).

    Vals AI prints "GPT 5.2" in its table, but the page's data holds each run's
    record, keyed by the model id its name links to (`/models/openai_gpt-5.2-
    2025-12-11`), with the effort it was run at: `"reasoning_effort": "xhigh"`.
    A row whose name states no setting takes the effort of the record with the
    same model and the same score (within `score_tolerance`) - only when
    exactly one such word is found,
    and only a word `setting_from_page_data.words` lists (Inkling's "0.99" is
    not an effort word). Anything else leaves the row as the table prints it.
    """
    spec = table.setting_from_page_data
    if not spec or score_header is None:
        return {}
    text = content.decode("utf-8", "replace") if isinstance(content, bytes) else content
    data = html_module.unescape(text)
    prefix, field, words = spec["link_prefix"], spec["field"], set(spec["words"])
    tolerance = float(spec["score_tolerance"])
    decoder = json.JSONDecoder()

    def unwrap(value: Any) -> Any:
        # The page serialises each value as [0, value].
        return value[1] if isinstance(value, list) and len(value) == 2 else value

    out: dict[int, str] = {}
    for i, row in enumerate(rows):
        link, (name, setting, _variant) = row.get(LINK_KEY) or "", identities[i]
        if not link.startswith(prefix) or not name or setting or "(" in name:
            continue
        model_id = link[len(prefix) :].replace("_", "/", 1)
        score = _number(row.get(score_header))
        if score is None:
            continue
        found: set[str] = set()
        key = f'"{model_id}":[0,{{'
        position = data.find(key)
        while position != -1:
            try:
                record, _ = decoder.raw_decode(data, position + len(key) - 1)
            except ValueError:
                record = None
            if isinstance(record, dict):
                accuracy = unwrap(record.get("accuracy"))
                word = unwrap(record.get(field))
                if (
                    isinstance(accuracy, (int, float))
                    and abs(float(accuracy) - score) < tolerance
                    and word is not None
                ):
                    found.add(str(word))
            position = data.find(key, position + 1)
        if len(found) == 1 and (word := found.pop()) in words:
            out[i] = word
    return out


def _by_host(
    rows: list[dict[str, Any]], identities: list[tuple[str, str | None, str | None]], table: Table
) -> tuple[set[int], dict[int, str]]:
    """A board that measures one model on several hosts' APIs (Artificial
    Analysis's speech to text) gives one value per host (Parvathi, 2026-11-03).
    With `first_party_field` (the row's field naming the model's maker):

      the maker serves it   only the maker's own API is read (Nova-3 on Deepgram,
                            not on Telnyx); the resellers' rows are left out
      it does not           each host is its own setting row, named after the
                            host ("Whisper Large v3 (fal.ai)"): every value is
                            shown and none is chosen for the reader

    Returns the rows to leave out, and the host setting of each row that gets one.
    """
    if not table.first_party_field:
        return set(), {}
    by_model: dict[tuple[str, str], list[int]] = {}
    for i, (name, setting, _variant) in enumerate(identities):
        if name:
            by_model.setdefault((name.lower(), (setting or "").lower()), []).append(i)
    skipped: set[int] = set()
    hosts: dict[int, str] = {}
    for positions in by_model.values():
        if len(positions) < 2:
            continue
        own = [
            i
            for i in positions
            if identities[i][2]
            and identities[i][2].lower()
            == clean_label(rows[i].get(table.first_party_field)).lower()
        ]
        if own:
            skipped.update(i for i in positions if i not in own)
        else:
            hosts.update({i: identities[i][2] for i in positions if identities[i][2]})
    return skipped, hosts


def parse(source: Source, content: bytes, *, url: str) -> Parsed:
    out = Parsed()
    for index, table in enumerate(source.tables):
        try:
            _parse_table(source, index, table, content, url, out)
        except (ValueError, KeyError, json.JSONDecodeError) as error:
            out.problems.append(
                ("table_not_found", f"table {index + 1}: {type(error).__name__}: {error}")
            )
    return out


def _parse_table(
    source: Source, index: int, table: Table, content: bytes, url: str, out: Parsed
) -> None:
    kind = table.locate["type"]
    where = f"table {index + 1}"
    if kind == "html_table":
        found = locate_html_table(content, table.locate, table)
        if found is None:
            out.problems.append(
                ("table_not_found", f"{where}: no table contains {table.locate['must_contain']!r}")
            )
            return
        headers, rows = found
    elif kind in ("gradio_config", "html_rows"):
        found = (
            locate_gradio_config(content, table.locate)
            if kind == "gradio_config"
            else locate_html_rows(content, table.locate)
        )
        if found is None:
            out.problems.append(("table_not_found", f"{where}: no {kind} table found"))
            return
        headers, rows = found
    elif kind == "next_flight":
        records = locate_next_flight(content, table.locate)
        if records is None:
            out.problems.append(
                (
                    "table_not_found",
                    f"{where}: no Next.js page data with {table.locate['required_keys']}",
                )
            )
            return
        rows = [flatten(r) for r in records]
        headers = sorted({k for r in rows for k in r})
    else:  # embedded_json
        records = locate_embedded_json(content, table.locate)
        if records is None:
            out.problems.append(
                (
                    "table_not_found",
                    f"{where}: no data block <script id={table.locate['script_id']!r}>",
                )
            )
            return
        rows = [flatten(r) for r in records]
        headers = sorted({k for r in rows for k in r})
    out.tables_found += 1
    release = None
    if table.release_selector:
        found_release = BeautifulSoup(content, "lxml").select_one(table.release_selector)
        release = clean_label(found_release.get_text(" ")) if found_release else None
        if release:
            out.release = release
        else:
            out.problems.append(
                ("release_not_found", f"{where}: nothing at {table.release_selector!r}")
            )

    model_key = table.model_column or table.model_field
    expected = [model_key, *table.benchmark_map]
    cleaned = {clean_label(h): h for h in headers}
    missing = [h for h in expected if clean_label(h) not in cleaned]
    if missing:
        out.problems.append(
            ("layout_changed", f"{where}: header(s) {missing} not found; page has {headers[:12]}")
        )
        return
    actual = {h: cleaned[clean_label(h)] for h in expected}
    if not rows:
        out.problems.append(("layout_changed", f"{where}: the table has no rows"))
        return
    out.rows_parsed += len(rows)
    out.notes.append(f"{where}: {len(rows)} rows")

    rank = table.rank or {}
    rank_values: list[int | None] = [None] * len(rows)
    rank_out_of = len(rows)
    if rank.get("from") == "row_order":
        score_header = next(
            (
                h
                for h, t in table.benchmark_map.items()
                if t["benchmark"] == rank["benchmark"] and t["metric"] == "score"
            ),
            None,
        )
        # The row position is the rank only if the board really is in score
        # order (PR #573 review: the order was trusted). Scores must not rise
        # down the page; if they do, no rank is read and the scores still are.
        scores = [_number(row.get(actual[score_header])) for row in rows]
        known = [s for s in scores if s is not None]
        if any(later > earlier for earlier, later in zip(known, known[1:], strict=False)):
            out.problems.append(
                (
                    "rank_order_unsorted",
                    f"{where}: the rows are not in {score_header!r} order, so their "
                    "positions are not ranks; no rank read",
                )
            )
        else:
            previous_score, previous_rank = object(), 0
            for position, score in enumerate(scores, start=1):
                if score is None or score != previous_score:
                    previous_rank, previous_score = position, score
                rank_values[position - 1] = previous_rank
    elif rank.get("from") == "order_by":
        values = [_number(row.get(rank["field"])) for row in rows]
        rank_values = _competition_ranks(values)
        rank_out_of = sum(v is not None for v in values)

    identities = [_identity(row, table, actual[model_key]) for row in rows]
    skipped, hosts = _by_host(rows, identities, table)
    if skipped:
        out.notes.append(
            f"{where}: {len(skipped)} rows from another host left out: the maker's own API "
            "lists the same model"
        )
    if hosts:
        out.notes.append(f"{where}: {len(hosts)} rows read as one setting row per host")
    score_header = next(
        (actual[h] for h, t in table.benchmark_map.items() if t["metric"] == "score"), None
    )
    page_settings = _page_settings(content, table, rows, identities, score_header)
    if table.setting_from_page_data:
        out.notes.append(
            f"{where}: {len(page_settings)} rows take the setting the page's data states"
        )

    for position, row in enumerate(rows):
        if position in skipped:
            continue
        name, setting, variant = identities[position]
        if not name:
            continue
        if position in hosts and not setting:
            setting = hosts[position]
        if position in page_settings:
            setting = page_settings[position]
        if table.date_column:
            collected = clean_label(row.get(table.date_column))[:10] or None
        elif table.date_field:
            collected = clean_label(row.get(table.date_field))[:10] or None
        else:
            collected = release
        common = dict(
            source_key=source.key,
            table_index=index,
            raw_model_name=name,
            url=url,
            variant=variant or None,
            raw_setting=setting or None,
            collected_on=collected,
            row_index=position,
            priority=table.priority,
            duplicates=table.duplicates,
        )
        for header, target in table.benchmark_map.items():
            raw_text = row.get(actual[header])
            raw_text = "" if raw_text is None else str(raw_text)
            if target.get("labelled"):
                raw_text = labelled_part(raw_text, target["labelled"])
            if target["metric"] == "rank":
                out.observations.append(
                    RawObservation(
                        benchmark=target["benchmark"],
                        metric="rank",
                        raw_text=raw_text,
                        rank_board=table.rank_board,
                        rank_out_of=len(rows),
                        **common,
                    )
                )
            else:
                out.observations.append(
                    RawObservation(
                        benchmark=target["benchmark"],
                        metric=target["metric"],
                        raw_text=raw_text,
                        scale=target.get("scale"),
                        **common,
                    )
                )
        if rank and rank_values[position] is not None:
            out.observations.append(
                RawObservation(
                    benchmark=rank["benchmark"],
                    metric="rank",
                    raw_text=str(rank_values[position]),
                    rank_board=rank.get("board"),
                    rank_out_of=rank_out_of,
                    tied=rank_values.count(rank_values[position]) > 1,
                    **common,
                )
            )
