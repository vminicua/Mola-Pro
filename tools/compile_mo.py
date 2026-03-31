from __future__ import annotations

import ast
import struct
from pathlib import Path


def _unquote(value: str) -> str:
    return ast.literal_eval(value)


def parse_po(po_path: Path) -> dict[str, str]:
    messages: dict[str, str] = {}
    msgctxt: str | None = None
    msgid: str | None = None
    msgstr: str | None = None
    state: str | None = None
    fuzzy = False

    def flush() -> None:
        nonlocal msgctxt, msgid, msgstr, state, fuzzy
        if msgid is None or msgstr is None or fuzzy:
            msgctxt = None
            msgid = None
            msgstr = None
            state = None
            fuzzy = False
            return

        key = f"{msgctxt}\x04{msgid}" if msgctxt else msgid
        messages[key] = msgstr
        msgctxt = None
        msgid = None
        msgstr = None
        state = None
        fuzzy = False

    for raw_line in po_path.read_text(encoding="utf-8").splitlines() + [""]:
        line = raw_line.strip()

        if line.startswith("#,") and "fuzzy" in line:
            fuzzy = True
            continue

        if line.startswith("msgctxt "):
            msgctxt = _unquote(line[7:].strip())
            state = "msgctxt"
            continue

        if line.startswith("msgid "):
            if msgid is not None and msgstr is not None:
                flush()
            msgid = _unquote(line[5:].strip())
            msgstr = None
            state = "msgid"
            continue

        if line.startswith("msgstr "):
            msgstr = _unquote(line[6:].strip())
            state = "msgstr"
            continue

        if line.startswith('"'):
            fragment = _unquote(line)
            if state == "msgctxt" and msgctxt is not None:
                msgctxt += fragment
            elif state == "msgid" and msgid is not None:
                msgid += fragment
            elif state == "msgstr" and msgstr is not None:
                msgstr += fragment
            continue

        if not line:
            flush()

    return messages


def write_mo(messages: dict[str, str], mo_path: Path) -> None:
    ordered = sorted(messages.items())
    ids_blob = b""
    strs_blob = b""
    id_table: list[tuple[int, int]] = []
    str_table: list[tuple[int, int]] = []

    keystart = 7 * 4 + len(ordered) * 16

    for msgid, _ in ordered:
        encoded = msgid.encode("utf-8")
        id_table.append((len(encoded), keystart + len(ids_blob)))
        ids_blob += encoded + b"\0"

    valuestart = keystart + len(ids_blob)
    for _, msgstr in ordered:
        encoded = msgstr.encode("utf-8")
        str_table.append((len(encoded), valuestart + len(strs_blob)))
        strs_blob += encoded + b"\0"

    output = bytearray()
    output.extend(struct.pack("Iiiiiii", 0x950412DE, 0, len(ordered), 28, 28 + len(ordered) * 8, 0, 0))

    for length, offset in id_table:
        output.extend(struct.pack("ii", length, offset))

    for length, offset in str_table:
        output.extend(struct.pack("ii", length, offset))

    output.extend(ids_blob)
    output.extend(strs_blob)

    mo_path.parent.mkdir(parents=True, exist_ok=True)
    mo_path.write_bytes(output)


def compile_catalog(po_path: Path) -> Path:
    messages = parse_po(po_path)
    mo_path = po_path.with_suffix(".mo")
    write_mo(messages, mo_path)
    return mo_path


def main() -> None:
    locale_root = Path("locale")
    po_files = sorted(locale_root.glob("*/LC_MESSAGES/*.po"))
    if not po_files:
        print("No .po files found under locale/.")
        return

    for po_file in po_files:
        mo_file = compile_catalog(po_file)
        print(f"Compiled {po_file} -> {mo_file}")


if __name__ == "__main__":
    main()
