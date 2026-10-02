"""task-649: rejected reference art must not be offered by the picker.

The known-bad ``eldenford - wrong orientatoin.png`` sits next to the correct
``eldenford.png``; an author tracing faithfully over it would paint a mirrored
map. It is parked in ``_rejected/`` (recoverable, not deleted) and the endpoint
only lists files.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app

ROOT = Path(__file__).resolve().parents[1]
BACKGROUNDS = ROOT / "static" / "images" / "backgrounds"


def test_rejected_reference_is_not_offered_but_still_on_disk():
    app = create_app({"TESTING": True})
    resp = app.test_client().get("/api/world/painter/backgrounds")
    assert resp.status_code == 200
    images = resp.get_json()["images"]
    assert any(src.endswith("/eldenford.png") for src in images), images
    assert not any("wrong orientation" in src or "wrong orientatoin" in src for src in images)
    # Reversible: the file is moved, never deleted.
    assert (BACKGROUNDS / "_rejected" / "eldenford - wrong orientatoin.png").is_file()
    assert not (BACKGROUNDS / "eldenford - wrong orientatoin.png").exists()
