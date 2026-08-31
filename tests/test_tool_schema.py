"""The extraction tool schema must be accepted by every function-calling backend.

Gemini (via OpenRouter, intermittently by route) rejects `prefixItems` — the
tuple form pydantic emits for `tuple[int, int]` like `quote_offset` — with
"quote_offset.items: missing field", failing the whole extraction. tool_schema_for
rewrites it to a plain `items` array; these pin that it stays gone.
"""

from __future__ import annotations

import json

from judge.extract.client import tool_schema_for
from judge.extract.schema import ExtractionResult


def test_no_prefixitems_anywhere_in_the_tool_schema():
    schema = tool_schema_for(ExtractionResult)
    assert "prefixItems" not in json.dumps(schema)


def test_quote_offset_is_a_plain_integer_array_with_a_typed_items():
    schema = tool_schema_for(ExtractionResult)
    qo = schema["properties"]["claims"]["items"]["properties"]["quote_offset"]
    assert qo["type"] == "array"
    assert qo["items"]["type"] == "integer"   # a type Gemini can read
    assert qo["minItems"] == 2 and qo["maxItems"] == 2  # length still pinned
