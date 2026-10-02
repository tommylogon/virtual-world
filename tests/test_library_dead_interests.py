"""task-599: library characters carry no dead interest tags.

`interest_tags` is matched against item tags (room attention, auto-dress), so a
tag no item carries can never fire — the character is quietly uninterested in
everything. `tools/lint_library.py --check dead_interests` is the guard; these
tests pin the rule and the current contents.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import lint_library  # noqa: E402


class _Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, check, message):
        self.errors.append((check, message))

    def warn(self, check, message):
        self.warnings.append((check, message))


def test_a_tag_no_item_carries_is_reported():
    items = {"apple": {"tags": ["food"]}}
    chars = {"Someone": {"interest_tags": ["food", "quantum_plasma"]}}
    report = _Report()
    lint_library.check_dead_interests(items, chars, report)
    assert len(report.errors) == 1
    assert "quantum_plasma" in report.errors[0][1]
    assert "food" not in report.errors[0][1]


def test_a_live_tag_is_not_reported():
    items = {"cleaver": {"tags": ["weapon"]}}
    chars = {"Zikka": {"interest_tags": ["weapon"]}}
    report = _Report()
    lint_library.check_dead_interests(items, chars, report)
    assert report.errors == []


def test_the_library_has_no_dead_interests():
    lib = ROOT / "data" / "library"
    items = lint_library.load_registry(str(lib), "items")
    characters = lint_library.load_registry(str(lib), "characters")
    report = _Report()
    lint_library.check_dead_interests(items, characters, report)
    assert report.errors == [], report.errors
