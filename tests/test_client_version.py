from app import create_app


def test_index_exposes_uncached_client_asset_version(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    app = create_app({"TESTING": True, "DATA_DIR": str(data_dir)})

    with app.test_client() as client:
        page = client.get("/")
        version = client.get("/api/client-version")

    assert page.status_code == 200
    assert version.status_code == 200
    current = version.get_json()["version"]
    assert current
    assert f'data-client-version="{current}"'.encode() in page.data
    assert "no-store" in version.headers["Cache-Control"]
