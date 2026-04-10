"""
Compile locale/*/LC_MESSAGES/django.po to .mo.

Prefers `polib` when available, otherwise uses a small built-in compiler that
supports the plain msgid/msgstr format used in this project.
"""
from __future__ import annotations

import ast
import struct
from pathlib import Path

try:
    import polib
except ImportError:
    polib = None

ROOT = Path(__file__).resolve().parent.parent


def _unquote(value: str) -> str:
    return ast.literal_eval(value)


def parse_po(po_path: Path) -> dict[str, str]:
    messages: dict[str, str] = {}
    msgid: str | None = None
    msgstr: str | None = None
    active: str | None = None

    def flush() -> None:
        nonlocal msgid, msgstr
        if msgid is not None and msgstr is not None:
            messages[msgid] = msgstr
        msgid = None
        msgstr = None

    for raw_line in po_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("msgid "):
            flush()
            msgid = _unquote(line[6:])
            msgstr = None
            active = "msgid"
            continue

        if line.startswith("msgstr "):
            msgstr = _unquote(line[7:])
            active = "msgstr"
            continue

        if line.startswith('"'):
            value = _unquote(line)
            if active == "msgid" and msgid is not None:
                msgid += value
            elif active == "msgstr" and msgstr is not None:
                msgstr += value

    flush()
    return messages


def write_mo(messages: dict[str, str], mo_path: Path) -> None:
    keys = sorted(messages)
    ids = [key.encode("utf-8") for key in keys]
    strs = [messages[key].encode("utf-8") for key in keys]

    keystart = 7 * 4 + len(keys) * 8 * 2
    id_block = b""
    str_block = b""
    key_offsets = []
    value_offsets = []

    offset = 0
    for item in ids:
        key_offsets.append((len(item), keystart + offset))
        id_block += item + b"\0"
        offset += len(item) + 1

    valuestart = keystart + len(id_block)
    offset = 0
    for item in strs:
        value_offsets.append((len(item), valuestart + offset))
        str_block += item + b"\0"
        offset += len(item) + 1

    output = bytearray()
    output += struct.pack("<Iiiiiii", 0x950412DE, 0, len(keys), 28, 28 + len(keys) * 8, 0, 0)

    for length, offset_value in key_offsets:
        output += struct.pack("<II", length, offset_value)
    for length, offset_value in value_offsets:
        output += struct.pack("<II", length, offset_value)

    output += id_block
    output += str_block
    mo_path.write_bytes(output)


def compile_po(po_path: Path) -> None:
    mo_path = po_path.with_suffix(".mo")
    if polib is not None:
        polib.pofile(str(po_path)).save_as_mofile(str(mo_path))
    else:
        write_mo(parse_po(po_path), mo_path)
    print("Wrote", mo_path.relative_to(ROOT))


def main() -> None:
    for po_path in ROOT.glob("locale/*/LC_MESSAGES/django.po"):
        compile_po(po_path)


if __name__ == "__main__":
    main()
