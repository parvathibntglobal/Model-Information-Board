"""Print the blog generator's prompts and model as JSON, for Admin -> Prompts.

`judge/` may not import `generate_sample_blogs` (it imports `collect/`, and the
lane boundary forbids judge reaching collect - tests/test_lane_boundary.py), so
the admin page runs this as a subprocess instead, exactly as
`judge/blog_posts.py` runs the generator itself. Read-only: it builds strings
with the generator's own functions and calls no model.

Prints one JSON object: the generation model, the format names, and - for the
first format in blog_formats.yaml - the system prompt, the user message (with
placeholders where the subject and discussions go) and the tool schema.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    import generate_sample_blogs as gen

    formats = gen.load_formats()["formats"]
    fmt = formats[0]
    brief = gen.brief_for(fmt, "«subject»", "«model A»", "«model B»")
    doc = {"text": "«one whole engineering discussion, as harvested»"}
    out = {
        "model": gen.GEN_MODEL,
        "formats": [f["name"] for f in formats],
        "format": fmt["name"],
        "system": gen.system_for(fmt),
        "user": gen.user_message({"brief": brief}, [doc], []),
        "tool": gen.tool_for(fmt),
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
