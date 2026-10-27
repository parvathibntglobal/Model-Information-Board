"""Stage 2: locate the data in what was fetched and reshape it (doc 5).

    html_table     the first <table> whose text contains `must_contain`
    embedded_json  a <script id=...> JSON block the page ships its own data in
    next_flight    the Next.js flight data (self.__next_f) the page is built from

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


def _model_cell(cell, table: Table | None) -> dict[str, str]:
    """The name (and setting) from inside the model cell, when the mapping says where.

    LiveBench renders `<span class="nm" data-tip="Kimi K3 · reasoning effort: max">Kimi K3</span>
    <span class="opn">open</span>`: the cell's whole text would be "Kimi K3 open".
    """
    if table is None or not table.model_selector:
        return {}
    found = cell.select_one(table.model_selector)
    if found is None:
        return {}
    out = {MODEL_KEY: clean_label(found.get_text(" "))}
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
    records = data.get(locate["records"]) if locate.get("records") else data
    return records if isinstance(records, list) else None


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


def _number(text: Any) -> float | None:
    """The cell's one number, read as strictly as a value is (values.the_number);
    None for a cell that cannot be read - it never decides an order."""
    number, error = the_number(text)
    return None if error else number


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
        rows = records
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
        rows = records
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

    for position, row in enumerate(rows):
        name = row.get(MODEL_KEY) or clean_label(row.get(actual[model_key]))
        if not name:
            continue
        setting = (
            clean_label(row.get(table.setting_field))
            if table.setting_field
            else row.get(SETTING_KEY)
        )
        variant = (
            clean_label(row.get(table.variant_field)) if table.variant_field else table.variant
        )
        if table.name_pattern:
            split = re.fullmatch(table.name_pattern, name)
            if split:
                parts = split.groupdict()
                name = clean_label(parts["model"])
                if parts.get("variant"):
                    variant = clean_label(parts["variant"])
                if parts.get("setting"):
                    setting = clean_label(parts["setting"])
        if table.bare_setting_words and not setting:
            words = "|".join(re.escape(w) for w in table.bare_setting_words)
            bare = re.fullmatch(rf"(?P<model>.+?)[- ](?P<setting>{words})", name, re.I)
            if bare:
                name, setting = bare["model"], bare["setting"]
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
