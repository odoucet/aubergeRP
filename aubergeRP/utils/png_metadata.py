from __future__ import annotations

import base64
import json
import struct
import zlib
from pathlib import Path
from typing import Any

_CHARA_KEY = "chara"

# PNG tEXt chunk: keyword\x00text (no compression, no encoding declaration)
# Format: length(4) + type(4) + data + crc(4)


def _read_chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a valid PNG file")
    chunks = []
    pos = 8
    while pos < len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        chunk_type = data[pos + 4 : pos + 8]
        chunk_data = data[pos + 8 : pos + 8 + length]
        chunks.append((chunk_type, chunk_data))
        pos += 12 + length
    return chunks


def _build_chunk(chunk_type: bytes, chunk_data: bytes) -> bytes:
    length = struct.pack(">I", len(chunk_data))
    crc = struct.pack(">I", zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF)
    return length + chunk_type + chunk_data + crc


def read_png_metadata(path: str | Path) -> dict[str, Any] | None:
    """Read the 'chara' tEXt chunk from a PNG and return the decoded JSON, or None."""
    data = Path(path).read_bytes()
    for chunk_type, chunk_data in _read_chunks(data):
        if chunk_type == b"tEXt":
            if b"\x00" in chunk_data:
                key, _, value = chunk_data.partition(b"\x00")
                if key.decode("latin-1") == _CHARA_KEY:
                    decoded = base64.b64decode(value).decode("utf-8")
                    return json.loads(decoded)  # type: ignore[no-any-return]
    return None


def write_png_metadata(src_path: str | Path, dst_path: str | Path, card: dict[str, Any]) -> None:
    """Embed a character card dict as a base64-encoded tEXt 'chara' chunk in a PNG."""
    data = Path(src_path).read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a valid PNG file")

    encoded = base64.b64encode(json.dumps(card, ensure_ascii=False).encode("utf-8"))
    chara_chunk = _build_chunk(b"tEXt", _CHARA_KEY.encode("latin-1") + b"\x00" + encoded)

    chunks = _read_chunks(data)

    result = bytearray(data[:8])
    inserted = False
    for chunk_type, chunk_data in chunks:
        if chunk_type == b"tEXt":
            raw = chunk_data
            if b"\x00" in raw and raw.partition(b"\x00")[0].decode("latin-1") == _CHARA_KEY:
                if not inserted:
                    result += chara_chunk
                    inserted = True
                continue
        if chunk_type == b"IEND" and not inserted:
            result += chara_chunk
            inserted = True
        result += _build_chunk(chunk_type, chunk_data)

    Path(dst_path).write_bytes(bytes(result))
