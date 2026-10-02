"""`tools/lint_library.py` — biome resource coverage (task-573).

The check turns "this biome's resource_distribution resolves to no item" from a
silent empty search into a countable warning. These tests pin the rule, not the
library's contents.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import lint_library  # noqa: E402


def _warnings(items, biomes):
    report = lint_library.Report()
    lint_library.check_biome_coverage(items, biomes, report)
    return report.warnings


def test_entry_matching_an_item_is_covered():
    items = {"berry": {"tags": ["berry", "fruit", "forage"]}}
    biomes = {"resource_distribution": {"forest": [{"tags": ["berry", "fruit"], "weight": 3}]}}
    assert _warnings(items, biomes) == []


def test_entry_matching_no_item_is_reported():
    items = {"berry": {"tags": ["berry", "fruit", "forage"]}}
    biomes = {"resource_distribution": {"marsh": [{"tags": ["reeds"], "weight": 3}]}}
    warnings = _warnings(items, biomes)
    assert len(warnings) == 1
    assert "marsh" in warnings[0][1]
    assert "reeds" in warnings[0][1]


def test_entry_matching_an_untagged_item_is_still_covered():
    """Mirrors the consumer exactly: `engine/foraging.py::_pick_item` scores every
    item sharing a tag with the entry, and only prefers the `forage`-tagged subset
    of *those* matches when that subset is non-empty. Narrowing the pool never
    turns a non-empty match set into nothing, so an entry that matches only an
    untagged item is still found and is NOT a gap.

    (The check once intersected a global `forage` set here, which reported these
    as gaps -- false positives against the engine it claims to mirror.)
    """
    items = {"berry": {"tags": ["berry"]}, "stick": {"tags": ["stick", "forage"]}}
    biomes = {"resource_distribution": {"forest": [{"tags": ["berry"], "weight": 3}]}}
    assert _warnings(items, biomes) == []


def test_main_reads_the_sibling_worldpainter_file():
    tmp = tempfile.mkdtemp()
    try:
        lib = Path(tmp) / "library"
        (lib / "items").mkdir(parents=True)
        (lib / "items" / "reeds.json").write_text(
            json.dumps({"name": "Reeds", "tags": ["reeds", "forage"]}), encoding="utf-8")
        wp = Path(tmp) / "worldpainter"
        wp.mkdir()
        (wp / "biomes.json").write_text(json.dumps({
            "resource_distribution": {
                "marsh": [{"tags": ["reeds"], "weight": 2}],
                "bog": [{"tags": ["peat"], "weight": 1}],
            }
        }), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "lint_library.py"),
             "--data-dir", str(lib), "--check", "biome_coverage"],
            capture_output=True, text=True, cwd=ROOT)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "bog" in result.stdout and "peat" in result.stdout
        assert "marsh" not in result.stdout
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
