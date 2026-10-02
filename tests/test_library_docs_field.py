"""The authorable `docs` field on library entries (task-577).

`docs` is an optional repo-relative link from a library entry (keyed by id) to
the note that describes it. It must survive a save/load round trip, reject a
non-string, warn (never reject) on a path that does not exist yet, and reach a
materialised world node.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from routes.library_ops import REGISTRY_TYPES, load_registry
from engine.library_nodes import library_item_properties


def _client(tmp_path):
    data_dir = tmp_path / "data"
    (data_dir / "library").mkdir(parents=True, exist_ok=True)
    app = create_app({"TESTING": True, "DATA_DIR": str(data_dir)})
    return app.test_client(), data_dir


def _existing_path():
    # A real note in the repo, so the happy path is not "missing" too.
    return "docs/virtualWorld/Welcome.md"


def test_docs_round_trips_for_every_registry_type(tmp_path):
    client, data_dir = _client(tmp_path)
    for registry_type in REGISTRY_TYPES:
        entry_id = f"docs-test-{registry_type}"
        resp = client.post(f"/api/library/{registry_type}", json={
            "id": entry_id,
            "data": {"name": "Docs Test", "docs": _existing_path()},
        })
        assert resp.status_code == 200, resp.get_data(as_text=True)
        reg = load_registry(str(data_dir), f"{registry_type}.json")
        assert reg[entry_id]["docs"] == _existing_path(), registry_type


def test_missing_docs_path_is_a_warning_not_a_rejection(tmp_path):
    client, data_dir = _client(tmp_path)
    resp = client.post("/api/library/items", json={
        "id": "docs-missing",
        "data": {"name": "Missing", "docs": "docs/virtualWorld/Does Not Exist.md"},
    })
    assert resp.status_code == 200
    warnings = resp.get_json()["warnings"]
    assert any("does not exist" in w for w in warnings), warnings
    # ...and it is still stored, because an author may write the page next.
    assert load_registry(str(data_dir), "items.json")["docs-missing"]["docs"]


def test_non_string_docs_is_rejected(tmp_path):
    client, _ = _client(tmp_path)
    resp = client.post("/api/library/items", json={
        "id": "docs-bad",
        "data": {"name": "Bad", "docs": ["not", "a", "string"]},
    })
    assert resp.status_code == 400
    assert "docs" in resp.get_json()["error"]


def test_renaming_the_display_name_keeps_the_docs_link(tmp_path):
    client, data_dir = _client(tmp_path)
    client.post("/api/library/items", json={
        "id": "docs-rename",
        "data": {"name": "Original Name", "docs": _existing_path()},
    })
    client.post("/api/library/items", json={
        "id": "docs-rename",
        "data": {"name": "A Completely New Name", "docs": _existing_path()},
    })
    # Keyed by id, so the link survives a display-name change.
    entry = load_registry(str(data_dir), "items.json")["docs-rename"]
    assert entry["name"] == "A Completely New Name"
    assert entry["docs"] == _existing_path()


def test_docs_reaches_a_materialised_node():
    props = library_item_properties(
        {"name": "Lantern", "docs": "docs/virtualWorld/Items & Inventory/Items Overview.md"},
        "lantern")
    assert props["docs"] == "docs/virtualWorld/Items & Inventory/Items Overview.md"
    # Absent means absent: no empty key on an entry that never declared one.
    assert "docs" not in library_item_properties({"name": "Rock"}, "rock")
