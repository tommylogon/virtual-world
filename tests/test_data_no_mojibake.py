"""Regression guard: JSON data files must not contain cp1252 mojibake.

Emoji (and other non-ASCII) saved as UTF-8 but later decoded with the
Windows cp1252 default produces the classic 'ðŸŽ—ï¸' corruption. This test
fails if any .json under data/ or saves/ still carries that damage, so a bad
future write can't silently re-corrupt files.
"""
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).parent.parent
SCAN_ROOTS = [ROOT / "data", ROOT / "saves"]

# C1 control block (U+0080-U+009F) appears whenever a >=0x80 byte of a UTF-8
# sequence was mis-decoded as cp1252; U+FFFD is the replacement-char artifact.
_MOJIBAKE_C1 = set(chr(c) for c in range(0x80, 0xA0))
_REPLACEMENT = "\ufffd"
# 'ðŸ' — the lead bytes (F0 9F) of a 4-byte emoji mis-decoded as cp1252.
_UTF8_EMOJI_LEAD_PAIR = "\u00f0\u0178"


def _json_files():
    files = []
    for root in SCAN_ROOTS:
        if root.exists():
            files.extend(root.rglob("*.json"))
    return files


@pytest.mark.parametrize("path", _json_files(), ids=lambda p: str(p.relative_to(ROOT)))
def test_json_file_has_no_mojibake(path):
    raw = path.read_bytes()
    # The file must be valid UTF-8 JSON.
    text = raw.decode("utf-8-sig")
    json.loads(text)

    problems = []
    if _UTF8_EMOJI_LEAD_PAIR in text:
        problems.append("emoji-lead-pair 'ðŸ'")
    if _REPLACEMENT in text:
        problems.append("U+FFFD replacement char")
    c1 = sorted({hex(ord(c)) for c in text if c in _MOJIBAKE_C1})
    if c1:
        problems.append(f"C1 control chars: {c1}")

    assert not problems, f"{path} contains mojibake: {', '.join(problems)}"
