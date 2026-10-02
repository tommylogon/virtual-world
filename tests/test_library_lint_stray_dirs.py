"""`tools/lint_library.py` — stray non-registry directories (task-645).

`data/library/rooms` holds stale save state, not a registry. It produced no
signal at all except a 400 on an endpoint that should not exist, so the check
makes the directory visible (warning, exit 0) rather than silently ignoring it.
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import lint_library  # noqa: E402


def test_non_registry_dir_is_reported():
    with tempfile.TemporaryDirectory() as tmp:
        lib = Path(tmp)
        (lib / "items").mkdir()
        (lib / "rooms").mkdir()
        (lib / "rooms" / "mansion.json").write_text("{}", encoding="utf-8")
        report = lint_library.Report()
        lint_library.check_stray_library_dirs(str(lib), report)
        assert len(report.warnings) == 1
        check, message = report.warnings[0]
        assert check == "stray_library_dirs"
        assert "rooms" in message
        assert "items" not in message


def test_hidden_directories_are_ignored():
    with tempfile.TemporaryDirectory() as tmp:
        lib = Path(tmp)
        (lib / "items").mkdir()
        (lib / "_rejected").mkdir()
        report = lint_library.Report()
        lint_library.check_stray_library_dirs(str(lib), report)
        assert report.warnings == []


def test_known_registry_types_logic_is_available():
    # A silently-empty set would make the check a no-op everywhere.
    assert "items" in lint_library._known_registry_types()
