"""Route tests for the compiler-vocabulary API (task-589).

The surface is browsable/editable but never materializable: biomes and features
are read by the compiler, so the API offers list/save/delete with no place action.
Saves go through the same per-record validators `engine.biomes.validate()` uses.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app


def _client(tmp_path):
    return create_app({"TESTING": True, "DATA_DIR": str(tmp_path)}).test_client()


VALID_BIOME = {
    "name": "Test Shop", "terrain": "urban", "tags": ["building", "commercial"],
    "surface": "stone", "descriptions": ["A quiet shop."],
}


def test_vocabulary_rejects_an_unknown_type(tmp_path):
    client = _client(tmp_path)
    assert client.get("/api/vocabulary/nope").status_code == 400


def test_vocabulary_save_validates_and_round_trips(tmp_path):
    client = _client(tmp_path)
    empty = client.get("/api/vocabulary/biomes").get_json()
    assert empty["type"] == "biomes"
    assert empty["entries"] == []

    resp = client.post("/api/vocabulary/biomes/test_glade", json=VALID_BIOME)
    assert resp.status_code == 200, resp.get_json()

    listing = client.get("/api/vocabulary/biomes").get_json()
    ids = {e["id"] for e in listing["entries"]}
    assert "test_glade" in ids
    # Written one-file-per-entry into the library dir the engine already reads.
    assert (Path(tmp_path) / "library" / "biomes" / "test_glade.json").is_file()


def test_vocabulary_save_refuses_an_invalid_record(tmp_path):
    client = _client(tmp_path)
    bad = {"name": "", "terrain": "forest", "tags": ["forest"],
           "surface": "grass", "descriptions": ["x"]}
    resp = client.post("/api/vocabulary/biomes/bad", json=bad)
    assert resp.status_code == 400
    assert "problems" in resp.get_json()
    assert not (Path(tmp_path) / "library" / "biomes" / "bad.json").exists()


def test_wild_biome_needs_loot_rules(tmp_path):
    # task-589 coverage: a wild biome with no resource/hostile rules is refused,
    # and accepted once its loot tables exist (mirrors validate()'s rule).
    client = _client(tmp_path)
    wild = {"name": "Misty Hollow", "terrain": "forest", "tags": ["forest"],
            "surface": "moss", "descriptions": ["A damp hollow."]}
    resp = client.post("/api/vocabulary/biomes/misty_hollow", json=wild)
    assert resp.status_code == 400
    assert "no resource rules" in " ".join(resp.get_json()["problems"])

    client.post("/api/vocabulary/resource_distribution/misty_hollow_herb", json={
        "id": "misty_hollow_herb", "name": "hollow herb",
        "biome_tags": ["misty_hollow"], "location_tags": [],
        "item_tags": ["coin", "currency"], "weight": 1, "conditions": {}})
    client.post("/api/vocabulary/hostile_distribution/misty_hollow_wolf", json={
        "id": "misty_hollow_wolf", "name": "hollow wolf",
        "biome_tags": ["misty_hollow"], "location_tags": [], "kind": "predator",
        "base_chance": 0.01, "per_area_from_settlement": 0.005, "max_chance": 0.1,
        "conditions": {}})
    assert client.post("/api/vocabulary/biomes/misty_hollow",
                       json=wild).status_code == 200


def test_vocabulary_delete(tmp_path):
    client = _client(tmp_path)
    client.post("/api/vocabulary/biomes/test_glade", json=VALID_BIOME)
    assert client.delete("/api/vocabulary/biomes/test_glade").status_code == 200
    assert client.delete("/api/vocabulary/biomes/test_glade").status_code == 404


def test_vocabulary_features_use_the_feature_validator(tmp_path):
    client = _client(tmp_path)
    good = {"name": "Ford", "tags": ["road"], "descriptions": ["A shallow crossing."]}
    assert client.post("/api/vocabulary/features/ford", json=good).status_code == 200
    bad = {"name": "F", "tags": [], "descriptions": []}
    assert client.post("/api/vocabulary/features/bad", json=bad).status_code == 400


VALID_FLOOR_PLAN = {
    "label": "Test Hut", "storeys": 1,
    "legend": {"=": "wall", " ": "door", "R": "hearth_room"},
    "plan": ["=RR=", "=  =", "===="],
}
VALID_RESOURCE = {
    "id": "test_coin", "name": "test coin", "biome_tags": ["beach"],
    "location_tags": [], "item_tags": ["coin", "currency"], "weight": 2, "conditions": {},
}
VALID_HOSTILE = {
    "id": "test_wolf", "name": "test wolf", "biome_tags": ["sparse_forest"],
    "location_tags": [], "kind": "predator", "base_chance": 0.01,
    "per_area_from_settlement": 0.005, "max_chance": 0.1, "conditions": {},
}


def test_floor_plans_are_file_backed_and_preserve_siblings(tmp_path):
    import json as _json
    client = _client(tmp_path)
    path = Path(tmp_path) / "worldpainter" / "interiors.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"version": 1, "plans": {}, "fallback": {"plan": ["=  ="]}}',
                    encoding="utf-8")

    assert client.post("/api/vocabulary/floor_plans/test_hut",
                       json=VALID_FLOOR_PLAN).status_code == 200
    got = client.get("/api/vocabulary/floor_plans").get_json()
    assert {e["id"] for e in got["entries"]} == {"test_hut"}
    # The single-file save must not clobber its siblings.
    saved = _json.loads(path.read_text(encoding="utf-8"))
    assert saved["version"] == 1 and saved["fallback"]

    assert client.delete("/api/vocabulary/floor_plans/test_hut").status_code == 200
    assert client.get("/api/vocabulary/floor_plans").get_json()["entries"] == []


def test_floor_plan_is_lenient_about_a_ragged_row(tmp_path):
    client = _client(tmp_path)
    ragged = dict(VALID_FLOOR_PLAN)
    ragged["plan"] = ["=RR=", "=  =="]   # ragged on purpose; the generator pads it
    assert client.post("/api/vocabulary/floor_plans/ragged", json=ragged).status_code == 200


def test_floor_plan_rejects_a_missing_legend(tmp_path):
    client = _client(tmp_path)
    resp = client.post("/api/vocabulary/floor_plans/bad",
                       json={"label": "X", "storeys": 1, "plan": ["=="]})
    assert resp.status_code == 400
    assert "legend" in " ".join(resp.get_json()["problems"])


def test_loot_tables_validate(tmp_path):
    client = _client(tmp_path)
    assert client.post("/api/vocabulary/resource_distribution/test_coin",
                       json=VALID_RESOURCE).status_code == 200
    bad_res = dict(VALID_RESOURCE, id="bad", item_tags=["not_a_real_tag"])
    assert client.post("/api/vocabulary/resource_distribution/bad",
                       json=bad_res).status_code == 400

    assert client.post("/api/vocabulary/hostile_distribution/test_wolf",
                       json=VALID_HOSTILE).status_code == 200
    bad_host = dict(VALID_HOSTILE, id="badh", kind="dragon")
    assert client.post("/api/vocabulary/hostile_distribution/badh",
                       json=bad_host).status_code == 400


def test_hazard_registry_is_file_backed_and_validates(tmp_path):
    client = _client(tmp_path)
    good = {
        "name": "Test Sluice", "ability": "DEX",
        "dc": {"1": 10, "10": 15, "20": 20},
        "on_fail": {"conditions": ["wet"], "tags": ["swept"]},
        "message_success": "You make it.", "message_fail": "Down you go.",
    }
    assert client.post("/api/vocabulary/hazards/test_sluice", json=good).status_code == 200
    got = client.get("/api/vocabulary/hazards").get_json()
    assert {e["id"] for e in got["entries"]} == {"test_sluice"}
    bad = dict(good, ability="LUCK")
    assert client.post("/api/vocabulary/hazards/bad", json=bad).status_code == 400


