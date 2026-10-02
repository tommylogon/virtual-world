"""The doc resolver route (task-578).

Indexes the two link sources (module `@docs` headers, library entry `docs`
fields), answers `?module=` / `?node=`, serves a body only for the narrative
vault, and rebuilds when a source's mtime changes.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from app import create_app
from routes import docs_ops


@pytest.fixture
def repo(tmp_path, monkeypatch):
    note = tmp_path / "docs/virtualWorld/Gameplay/Search & Forage.md"
    note.parent.mkdir(parents=True)
    note.write_text("# Search & Forage\n\nA weighted draw over skill tables.\n",
                    encoding="utf-8")
    (tmp_path / "engine").mkdir()
    (tmp_path / "engine/foraging.py").write_text(
        '"""Forage.\n\n@module foraging\n@contributes the draw\n'
        '@docs docs/virtualWorld/Gameplay/Search & Forage.md\n"""\n',
        encoding="utf-8")
    (tmp_path / "data/library/ways").mkdir(parents=True)
    (tmp_path / "data/library/ways/way_4f2a.json").write_text(
        '{"id": "way_4f2a", "docs": "docs/virtualWorld/Gameplay/Search & Forage.md"}',
        encoding="utf-8")

    monkeypatch.setattr(docs_ops, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(docs_ops, "VAULT", tmp_path / "docs/virtualWorld")
    monkeypatch.setattr(docs_ops, "JS_ROOT", tmp_path / "static/js")
    monkeypatch.setattr(docs_ops, "PY_ROOTS", (tmp_path / "engine",))
    monkeypatch.setattr(docs_ops, "LIBRARY_ROOT", tmp_path / "data/library")
    docs_ops._CACHE.update(index=None, paths=[], stamp=None, builds=0)
    app = create_app({"TESTING": True})
    return tmp_path, note, app.test_client()


def test_module_lookup_returns_title_summary_and_body_url(repo):
    _root, _note, client = repo
    resp = client.get("/api/docs/resolve?module=engine/foraging.py")
    assert resp.status_code == 200
    rows = resp.get_json()
    assert len(rows) == 1
    row = rows[0]
    assert row["title"] == "Search & Forage"
    assert row["summary"].startswith("A weighted draw")
    assert row["path"].endswith("Search & Forage.md")
    assert row["body_url"].startswith("/api/docs/body?path=")


def test_node_lookup_by_library_entry_id(repo):
    _root, _note, client = repo
    rows = client.get("/api/docs/resolve?node=way_4f2a").get_json()
    assert len(rows) == 1 and rows[0]["title"] == "Search & Forage"


def test_unknown_key_is_empty_200_not_404(repo):
    _root, _note, client = repo
    resp = client.get("/api/docs/resolve?module=engine/nope.py")
    assert resp.status_code == 200 and resp.get_json() == []


def test_index_is_built_once_and_reused(repo):
    _root, _note, client = repo
    client.get("/api/docs/resolve?module=engine/foraging.py")
    assert docs_ops._CACHE["builds"] == 1
    client.get("/api/docs/resolve?node=way_4f2a")
    assert docs_ops._CACHE["builds"] == 1, "a second request must not rescan"


def test_touching_a_note_rebuilds_the_index(repo):
    root, note, client = repo
    client.get("/api/docs/resolve?module=engine/foraging.py")
    assert docs_ops._CACHE["builds"] == 1
    os.utime(note, (note.stat().st_atime + 10, note.stat().st_mtime + 10))
    client.get("/api/docs/resolve?module=engine/foraging.py")
    assert docs_ops._CACHE["builds"] == 2


def test_body_is_served_for_a_vault_note(repo):
    _root, note, client = repo
    rel = "docs/virtualWorld/Gameplay/Search & Forage.md"
    resp = client.get("/api/docs/body", query_string={"path": rel})
    assert resp.status_code == 200
    assert b"# Search & Forage" in resp.data


def test_dev_tasks_body_is_not_served(repo):
    _root, _note, client = repo
    rel = "docs/virtualWorld/dev_tasks/todo/docs/secret.md"
    resp = client.get("/api/docs/body", query_string={"path": rel})
    assert resp.status_code == 404


def test_traversal_and_absolute_paths_are_rejected(repo):
    _root, _note, client = repo
    for bad in ("../../etc/passwd", "/etc/passwd",
                "docs/virtualWorld/../../secret.md",
                "docs%2FvirtualWorld%2F..%2F..%2Fsecret.md"):
        resp = client.get("/api/docs/body", query_string={"path": bad})
        assert resp.status_code == 404, bad
        # No existence leak: the shape is the same as a plain miss.
        assert resp.get_json() == {"error": "not found"}
