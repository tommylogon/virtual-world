"""Tests for the node image endpoint (routes/graph.py upload_node_image).

Covers: uploading binds the node's `image` property and persists a bundled
asset file, invalid types are rejected, and clearing via PATCH unbinds it.
The endpoint's `IMAGES_DIR` config override keeps file writes OUT of the
repo's real static dir during tests.
"""
import atexit
import base64
import io
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app

# A 1x1 transparent PNG (70 bytes).
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

_TMP_IMAGES = Path(tempfile.mkdtemp(prefix='vw-image-tests-'))
atexit.register(lambda: shutil.rmtree(_TMP_IMAGES, ignore_errors=True))


def _fresh_client():
    app = create_app({'TESTING': True, 'IMAGES_DIR': str(_TMP_IMAGES)})
    return app.test_client(), app


def _first_area(app):
    return next((n for n in app.world.graph.nodes.values() if n.type == 'area'), None)


def _png_buf():
    return (io.BytesIO(_PNG), 'test.png')


def test_upload_sets_image_property_and_persists_file():
    client, app = _fresh_client()
    area = _first_area(app)
    assert area is not None

    resp = client.post(f'/api/graph/node/{area.id}/image',
                       data={'file': _png_buf()},
                       content_type='multipart/form-data')
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['status'] == 'success'
    assert body['image'].startswith('/static/images/nodes/')

    # Node property bound
    area = app.world.graph.get_node(area.id)
    assert area.properties.get('image') == body['image']

    # File actually written (under the temp IMAGES_DIR, not the real static dir)
    filename = Path(body['image']).name
    saved = _TMP_IMAGES / filename
    assert saved.is_file()
    saved.unlink(missing_ok=True)


def test_upload_rejects_unsupported_type():
    client, app = _fresh_client()
    area = _first_area(app)
    resp = client.post(f'/api/graph/node/{area.id}/image',
                       data={'file': (io.BytesIO(b'not an image'), 'evil.txt')},
                       content_type='multipart/form-data')
    assert resp.status_code == 400
    assert 'Unsupported image type' in resp.get_json()['error']
    area = app.world.graph.get_node(area.id)
    assert 'image' not in area.properties


def test_clear_via_patch_removes_image_property():
    client, app = _fresh_client()
    area = _first_area(app)

    client.post(f'/api/graph/node/{area.id}/image',
                data={'file': _png_buf()},
                content_type='multipart/form-data')
    area = app.world.graph.get_node(area.id)
    assert 'image' in area.properties

    resp = client.patch(f'/api/graph/node/{area.id}', json={'properties': {'image': None}})
    assert resp.status_code == 200
    area = app.world.graph.get_node(area.id)
    assert area.properties.get('image') is None