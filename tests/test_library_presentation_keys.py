"""Canvas-only node properties (x/y) must never reach a library template.

A world laid out over a background map stores each node's position in
`properties.x`/`y`. Those are presentation data: if they were written into an
archetype, importing that template elsewhere would carry the original map's
coordinates with it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from routes.library_ops import (
    PRESENTATION_ONLY_PROPERTIES,
    _strip_presentation_properties,
    load_registry,
)


def test_presentation_properties_are_stripped_and_input_is_not_mutated():
    entry = {"properties": {"x": 10, "y": 20, "description": "keep me"}}
    cleaned = _strip_presentation_properties(entry)
    assert cleaned["properties"] == {"description": "keep me"}
    # The caller's payload must survive untouched.
    assert entry["properties"] == {"x": 10, "y": 20, "description": "keep me"}


def test_entry_without_coordinates_is_returned_unchanged():
    entry = {"properties": {"description": "no coords here"}}
    assert _strip_presentation_properties(entry) is entry


def test_non_dict_inputs_are_safe():
    assert _strip_presentation_properties(None) is None
    assert _strip_presentation_properties([]) == []


def test_route_does_not_write_coordinates_into_the_registry(tmp_path):
    # Isolated DATA_DIR so the real library registry is untouched.
    data_dir = tmp_path / "data"
    (data_dir / "library").mkdir(parents=True, exist_ok=True)
    client, _app = (lambda a: (a.test_client(), a))(
        create_app({"TESTING": True, "DATA_DIR": str(data_dir)})
    )

    resp = client.post("/api/library/items", json={
        "id": "present-test",
        "data": {
            "name": "Present Test",
            "properties": {"x": 123.4, "y": -56.7, "description": "kept"},
        },
    })
    assert resp.status_code == 200, resp.get_data(as_text=True)

    # Read back through the same loader the handler wrote with.
    registry = load_registry(str(data_dir), "items.json")
    entry = registry.get("present-test", {})
    props = entry.get("properties", {})
    assert props, "entry was not written"
    for key in PRESENTATION_ONLY_PROPERTIES:
        assert key not in props, f"'{key}' leaked into the library template"
    assert props.get("description") == "kept"
