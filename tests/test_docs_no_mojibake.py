"""The docs vault must not contain cp1252 mojibake sequences.

Complements ``tests/test_data_no_mojibake.py`` (which scans ``data/``) — the
Obsidian vault had 229 damaged sequences across 32 files that nothing guarded.
``tools/fix_docs_mojibake.py`` repairs them; this keeps them from coming back.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from fix_docs_mojibake import MOJIBAKE_MARK  # noqa: E402

DOCS_ROOT = ROOT / "docs"


def test_docs_have_no_mojibake():
    """Scans ALL of docs/ (not just the vault) and flags any `a-EUR` sequence —
    mapped or not — so an unrecognised variant cannot pass unnoticed."""
    offenders = []
    for path in sorted(DOCS_ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = text.count(MOJIBAKE_MARK)
        if hits:
            offenders.append(f"{path.relative_to(ROOT)} ({hits})")
    assert not offenders, (
        "cp1252 mojibake in docs — run `python tools/fix_docs_mojibake.py --fix`: "
        + ", ".join(offenders[:10])
    )
