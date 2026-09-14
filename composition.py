"""The composition root: the one place allowed to touch both lanes.

WHY THIS IS A MODULE AND NOT A FUNCTION INSIDE `run-backend.py`
---------------------------------------------------------------

`judge/` may not import `collect/` — `tests/test_lane_boundary.py` enforces it
in both directions since 2026-08-18 — so `judge/app.py` cannot read a payload by
itself. Something outside both lanes has to hand it a reader, and until
2026-09-14 that something was `run-backend.py`, which is fine while a laptop is
the only way to start the server.

It stopped being fine when a container needed the same wiring.
`run-backend.py` refuses to start without `--staging` or `--write` **at module
level**, so `serve.py` importing it to reuse one function triggered the refusal
instead — the import printed the "name the database you mean" block and exited.
Correct behaviour from that guard, and the wrong place to borrow from.

Two entry points, one implementation, and this file is the implementation:

    run-backend.py    a person chooses per invocation, and must
    serve.py          the deployment chose once, in its environment

**This file is deliberately at the repo root, beside `run-backend.py`.** The
boundary test walks `collect/` and `judge/`; a module that imports both belongs
outside both, and putting it inside either lane would make the test right to
fail.
"""

from __future__ import annotations

from pathlib import Path


def wire_source_text_reader() -> bool:
    """Give `judge/app.py` a way to read a payload, without either lane importing the other.

    `collect/rawstore.py` is the only reader of the payload store and
    `collect/assemble/prose.py` is the only thing that turns a payload into what
    a human wrote. This binds the two together and hands the result to
    `judge/app.py` as a plain callable.

    Returns whether it wired — reported at startup rather than assumed, because
    an unwired reader makes `/documents/{id}/source` answer "unwired", and a
    silent failure there would read as "this document has no text".
    """
    import judge.app as app_module
    from collect.assemble import prose
    from collect.config import settings as collect_settings
    from collect.rawstore import RawStore

    store = RawStore(Path(collect_settings().raw_store_path))

    def read(source: str, text_ref: str) -> str:
        extract = prose.for_source(source)
        if extract is None:
            # NOT a passthrough. A payload flattened verbatim lets a quote
            # verify against a JSON field value - the defect `prose.py` exists
            # to prevent, and the one that put raw JSON in front of the
            # classifier on 2026-09-10.
            raise ValueError(
                f"no prose extractor is mapped for source {source!r}; refusing "
                f"to serve the payload verbatim"
            )
        return extract(store.get_text(text_ref))

    app_module.SOURCE_TEXT_READER = read
    return True
