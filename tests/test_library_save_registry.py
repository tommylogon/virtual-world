"""save_registry must not churn the registry when one entry changes."""

import json
import os

from routes.helpers import load_registry, save_registry


def _entry(tmp_path, kind, key):
    return os.path.join(str(tmp_path), "library", kind, f"{key}.json")


def test_a_saved_entry_ends_with_a_newline(tmp_path):
    save_registry(str(tmp_path), "items.json", {"axe": {"name": "Axe"}})
    raw = open(_entry(tmp_path, "items", "axe"), "rb").read()
    assert raw.endswith(b"\n")
    assert json.loads(raw.decode("utf-8")) == {"name": "Axe"}


def test_an_unchanged_entry_is_not_rewritten(tmp_path):
    data = {"axe": {"name": "Axe"}, "rope": {"name": "Rope"}}
    save_registry(str(tmp_path), "items.json", data)
    path = _entry(tmp_path, "items", "axe")
    marker = 1_600_000_000
    os.utime(path, (marker, marker))

    save_registry(str(tmp_path), "items.json", data)

    assert os.stat(path).st_mtime == marker


def test_a_changed_entry_is_rewritten_and_keeps_the_newline(tmp_path):
    save_registry(str(tmp_path), "items.json", {"axe": {"name": "Axe"}})
    path = _entry(tmp_path, "items", "axe")
    marker = 1_600_000_000
    os.utime(path, (marker, marker))

    save_registry(str(tmp_path), "items.json", {"axe": {"name": "Hatchet"}})

    assert os.stat(path).st_mtime != marker
    raw = open(path, "rb").read()
    assert raw.endswith(b"\n")
    assert json.loads(raw.decode("utf-8")) == {"name": "Hatchet"}


def test_a_partial_dict_never_deletes_other_entries(tmp_path):
    save_registry(
        str(tmp_path),
        "items.json",
        {"axe": {"name": "Axe"}, "rope": {"name": "Rope"}},
    )
    save_registry(str(tmp_path), "items.json", {"axe": {"name": "Hatchet"}})

    assert set(load_registry(str(tmp_path), "items.json")) == {"axe", "rope"}
