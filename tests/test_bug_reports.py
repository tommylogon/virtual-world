"""Bug reports filed in the app become real dev-task files.

The mechanism under test is the write: the route must allocate an id from the
task tool's own allocator, land the file in ``<root>/todo/<area>/`` with the
frontmatter ``tools/tasks.py validate`` expects, and carry the evidence (image
link, app state, picked elements) into the body. The id race matters too:
``next_id`` is ``max + 1``, so two reports in the same instant collide by
construction and the loser has to retry rather than overwrite.
"""

import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from tools import tasks as dev_tasks


def _app(tmp_path):
    root = tmp_path / "dev_tasks"
    images = tmp_path / "images" / "bug-reports"
    app = create_app({"TESTING": True, "DATA_DIR": str(tmp_path / "data")})
    app.config["DEV_TASKS_ROOT"] = str(root)
    app.config["BUG_REPORT_IMAGES_DIR"] = str(images)
    return app


def _png_bytes():
    """A real 1x1 PNG — enough for the handler, which stores bytes verbatim."""
    return (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
            b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")


def _post(client, **fields):
    data = {k: v for k, v in fields.items() if v is not None}
    return client.post("/api/bugs/report", data=data,
                       content_type="multipart/form-data")


def test_report_writes_a_bug_task_file(tmp_path):
    client = _app(tmp_path).test_client()
    response = _post(
        client,
        message="The map cards overlap each other at high pitch.",
        area="ui",
        title="Map cards overlap",
        context=json.dumps({"layoutMode": "map", "mapSpacingPx": 583}),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"
    assert payload["id"].startswith("bug-")

    path = tmp_path / "dev_tasks" / payload["path"]
    assert path.exists()
    body = path.read_text(encoding="utf-8")
    # Frontmatter shape is what tools/tasks.py validate reads.
    assert body.startswith("---\ntype: bug\nstatus: todo\narea: ui\n")
    assert f"# {payload['id']}: Map cards overlap" in body
    assert "The map cards overlap each other at high pitch." in body
    # The evidence a reader needs, not just the prose.
    assert "## Evidence" in body
    assert '"layoutMode": "map"' in body


def test_report_carries_the_screenshot_into_the_task(tmp_path):
    client = _app(tmp_path).test_client()
    response = client.post(
        "/api/bugs/report",
        data={"message": "cramped", "area": "ui",
              "screenshot": (io.BytesIO(_png_bytes()), "shot.png")},
        content_type="multipart/form-data",
    )

    payload = response.get_json()
    assert payload["status"] == "success"
    # The directory is overridden to a tmp path here, so there is no honest
    # /static URL to hand back — the task file still links to the stored image.
    assert payload["image"] is None

    stored = tmp_path / "images" / "bug-reports"
    files = list(stored.glob("*.png"))
    assert len(files) == 1
    assert files[0].read_bytes() == _png_bytes()

    task_path = tmp_path / "dev_tasks" / payload["path"]
    body = task_path.read_text(encoding="utf-8")
    # Resolved from the task file's own folder, not from the CWD.
    link = body.split("![screenshot](", 1)[1].split(")", 1)[0]
    resolved = (task_path.parent / link).resolve()
    assert resolved.is_file() and resolved.suffix == ".png"


def test_picked_elements_are_recorded_with_selector_and_markup(tmp_path):
    client = _app(tmp_path).test_client()
    elements = [{
        "selector": "#graph-container > canvas",
        "summary": "<canvas>",
        "rect": {"x": 0, "y": 0, "width": 800, "height": 600},
        "ancestors": ["#graph-container"],
        "computed": {"display": "block"},
        "text": "Road (world 6,3)",
        "outerHTML": "<canvas width='800' height='600'></canvas>",
    }]
    response = _post(client, message="labels collide", area="ui",
                     elements=json.dumps(elements))

    payload = response.get_json()
    body = (tmp_path / "dev_tasks" / payload["path"]).read_text(encoding="utf-8")
    assert "### Picked elements" in body
    assert "`#graph-container > canvas`" in body
    assert "rect: x=0 y=0 w=800 h=600" in body
    assert "<canvas width='800' height='600'></canvas>" in body


def test_two_reports_never_share_an_id(tmp_path):
    client = _app(tmp_path).test_client()
    first = _post(client, message="first problem", area="bugs").get_json()
    second = _post(client, message="second problem", area="bugs").get_json()
    assert first["id"] != second["id"]
    assert first["path"] != second["path"]


def test_a_lost_id_race_retries_instead_of_overwriting(tmp_path):
    """The exclusive create is what turns a collision into a retry."""
    app = _app(tmp_path)
    client = app.test_client()
    root = Path(app.config["DEV_TASKS_ROOT"])

    # Simulate the race: the id the allocator is about to hand out already exists.
    dev_tasks.next_id(root, "bug")  # -> 1
    squatter = root / "todo" / "bugs" / "bug-1-already-there.md"
    squatter.parent.mkdir(parents=True, exist_ok=True)
    squatter.write_text("occupied", encoding="utf-8")

    payload = _post(client, message="racing report", area="bugs").get_json()
    assert payload["id"] == "bug-2"
    assert squatter.read_text(encoding="utf-8") == "occupied"


def test_description_is_required(tmp_path):
    client = _app(tmp_path).test_client()
    response = _post(client, message="   ", area="bugs")
    assert response.status_code == 400
    assert "description" in response.get_json()["error"].lower()
    # Nothing was written: not even the tree.
    assert not (tmp_path / "dev_tasks").exists()


def test_unknown_area_is_rejected(tmp_path):
    client = _app(tmp_path).test_client()
    response = _post(client, message="something", area="not-an-area")
    assert response.status_code == 400
    assert "not-an-area" in response.get_json()["error"]


def test_title_defaults_to_the_first_line_of_the_description(tmp_path):
    client = _app(tmp_path).test_client()
    payload = _post(client, message="Cards touch each other.\n\nMore detail here.",
                    area="ui").get_json()
    body = (tmp_path / "dev_tasks" / payload["path"]).read_text(encoding="utf-8")
    assert "Cards touch each other" in body
    assert "cards-touch-each-other" in payload["path"]


def test_non_image_attachment_is_rejected(tmp_path):
    client = _app(tmp_path).test_client()
    response = client.post(
        "/api/bugs/report",
        data={"message": "with a file", "area": "ui",
              "screenshot": (io.BytesIO(b"not an image"), "payload.exe")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "unsupported image type" in response.get_json()["error"]


def test_malformed_evidence_json_does_not_500(tmp_path):
    client = _app(tmp_path).test_client()
    response = _post(client, message="bad json", area="ui",
                     context="{not json", elements="<xml/>")
    assert response.status_code == 200
    payload = response.get_json()
    body = (tmp_path / "dev_tasks" / payload["path"]).read_text(encoding="utf-8")
    assert "_No evidence was attached._" in body


def test_reporting_does_not_broadcast_a_world_change(tmp_path):
    """A report changes no world state, so it must not trigger a 2.48 MB refetch."""
    app = _app(tmp_path)
    published = []
    try:
        from engine import world_events
        original = world_events.hub.publish
        world_events.hub.publish = lambda event: published.append(event)
        _post(app.test_client(), message="quiet please", area="bugs")
    finally:
        from engine import world_events
        world_events.hub.publish = original
    assert published == []