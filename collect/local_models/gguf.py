"""Read a GGUF file's header: the key/value metadata that comes before the tensors.

GGUF (llama.cpp's file format) opens with a fixed preamble - magic `GGUF`, a
version, a tensor count, a key/value count - then that many key/value pairs.
Everything the local VRAM tool needs about a model's attention is in those
pairs: layers, KV heads, head size, sliding window, which layers keep a cache.
The tensors come after, and nothing here reads them.

`parse_header` works on a PREFIX of the file and raises `Incomplete` when the
prefix ends mid-header, so a caller can fetch the next ranged step and try
again rather than downloading a multi-gigabyte file to read a few megabytes.

What is kept: the architecture, and every `<arch>.*` key whose value is a
number, a boolean, or an array of them (per-layer KV heads, a sliding-window
pattern). Strings and string arrays - the tokenizer's vocabulary is most of a
header - are skipped, never stored.
"""

from __future__ import annotations

import struct

MAGIC = b"GGUF"

#: GGUF value types: size in bytes and struct format, for the fixed-size ones.
_SCALARS = {
    0: (1, "<B"), 1: (1, "<b"), 2: (2, "<H"), 3: (2, "<h"), 4: (4, "<I"), 5: (4, "<i"),
    6: (4, "<f"), 7: (1, "<?"), 10: (8, "<Q"), 11: (8, "<q"), 12: (8, "<d"),
}
_STRING, _ARRAY = 8, 9

#: A per-layer array longer than this is not a per-layer array. No model has
#: thousands of layers; a header claiming one is read as unusable, not stored.
MAX_KEPT_ARRAY = 4096


class Incomplete(Exception):
    """The buffer ends inside the header. Fetch more and parse again."""


class NotGGUF(ValueError):
    """The bytes are not a GGUF file, or not one this reader understands."""


def parse_header(buf: bytes) -> tuple[dict, int]:
    """`(fields, end)`: the kept key/values, and where the key/value section ends."""
    if len(buf) < 24:
        raise Incomplete
    if buf[:4] != MAGIC:
        raise NotGGUF(f"starts with {buf[:4]!r}, not {MAGIC!r}")
    version, _tensors, pairs = struct.unpack_from("<IQQ", buf, 4)
    if version < 2:
        raise NotGGUF(f"GGUF version {version}: only 2 and later carry 64-bit counts")
    reader = _Reader(buf, 24)
    raw: dict = {}
    for _ in range(pairs):
        key = reader.string()
        value = reader.value(reader.u32())
        if value is not None:
            raw[key] = value
    return keep_fields(raw), reader.offset


def keep_fields(raw: dict) -> dict:
    """The architecture and its own keys, with the `<arch>.` prefix removed."""
    arch = raw.get("general.architecture")
    if not isinstance(arch, str):
        raise NotGGUF("no general.architecture in the header")
    prefix = f"{arch}."
    kept = {"architecture": arch}
    for key, value in raw.items():
        if key.startswith(prefix):
            kept[key[len(prefix):]] = value
    return kept


class _Reader:
    def __init__(self, buf: bytes, offset: int) -> None:
        self.buf, self.offset = buf, offset

    def _take(self, n: int) -> int:
        if self.offset + n > len(self.buf):
            raise Incomplete
        at = self.offset
        self.offset += n
        return at

    def u32(self) -> int:
        return struct.unpack_from("<I", self.buf, self._take(4))[0]

    def string(self) -> str:
        n = struct.unpack_from("<Q", self.buf, self._take(8))[0]
        return self.buf[self._take(n):self.offset].decode("utf-8", "replace")

    def value(self, kind: int):
        """The value, or None for one that is skipped (a string, a string
        array, an over-long array). The general.architecture string is the
        exception - it is the one string kept."""
        if kind in _SCALARS:
            size, fmt = _SCALARS[kind]
            return struct.unpack_from(fmt, self.buf, self._take(size))[0]
        if kind == _STRING:
            text = self.string()
            return text if len(text) <= 64 else None
        if kind == _ARRAY:
            item = self.u32()
            count = struct.unpack_from("<Q", self.buf, self._take(8))[0]
            if item == _STRING:
                for _ in range(count):
                    self.string()
                return None
            if item not in _SCALARS:
                raise NotGGUF(f"array of unknown type {item}")
            size, fmt = _SCALARS[item]
            at = self._take(size * count)
            if count > MAX_KEPT_ARRAY:
                return None
            return [struct.unpack_from(fmt, self.buf, at + size * i)[0] for i in range(count)]
        raise NotGGUF(f"unknown value type {kind}")
