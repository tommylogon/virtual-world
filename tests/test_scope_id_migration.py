"""Migrate the goblin camp scope id off `deep_woods_2` (task-565).

The id was minted once as a slug of the name at creation and the rename route
only ever touched the display name, so a scope called "goblin camp" kept the id
`deep_woods_2` forever. The project's rule is the opposite — ids change and
display names do not — so the id was the stale half of the rename.

These tests cover the migration tool and, more importantly, the state of the
checked-in camp afterwards: a scope tree that is still coherent, and no surviving
reference to the old id anywhere.
"""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.migrate_scope_id import migrate  # noqa: E402
from tools.scenario_refs import load_json  # noqa: E402

ROOT = Path(__file__).parent.parent
CAMP = ROOT / "data" / "scenarios" / "kraktooth_goblin_camp.json"

OLD = "deep_woods_2"
NEW = "goblin_camp"


def _camp():
    return load_json(CAMP)


def _refs(data, needle):
    """Every path in *data* still mentioning *needle*, as strings."""
    found = []

    def walk(value, path):
        if isinstance(value, dict):
            for key, child in value.items():
                if needle in str(key):
                    found.append(f"{path}.{key}")
                walk(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")
        elif isinstance(value, str) and needle in value:
            found.append(f"{path}={value!r}")

    walk(data, "$")
    return found


# ── the camp after the migration ───────────────────────────────────────────


def test_the_camp_scope_id_is_its_name():
    payload = _camp()
    scopes = payload["world_scopes"]
    assert NEW in scopes, f"the camp scope is {sorted(scopes)}"
    assert OLD not in scopes
    assert scopes[NEW]["name"] == "goblin camp"
    assert scopes[NEW]["id"] == NEW, "a scope record must agree with its own key"


def test_no_reference_to_the_old_id_survives_anywhere():
    payload = _camp()
    assert _refs(payload, OLD) == [], (
        f"{len(_refs(payload, OLD))} surviving reference(s) to {OLD!r}: "
        f"{_refs(payload, OLD)[:6]}"
    )


def test_the_outer_deep_woods_scope_is_untouched():
    """The task says to check it first, and it is genuinely a forest zone.

    `deep_woods` is a painted 45x30 grid with no areas and no children — a real
    WorldPainter scope whose id and name both agree. Renaming it would churn a
    scope nobody asked about, and its id is not the stale one.
    """
    scopes = _camp()["world_scopes"]
    assert "deep_woods" in scopes, "the outer forest scope should still exist"
    outer = scopes["deep_woods"]
    assert outer["id"] == "deep_woods" and outer["name"] == "deep woods"
    assert outer.get("parent_id") == "world"
    assert outer.get("area_ids") is not None
    assert outer["grid"]["w"] == 45 and outer["grid"]["h"] == 30


def test_the_scope_tree_is_still_coherent():
    payload = _camp()
    scopes = payload["world_scopes"]

    for scope_id, scope in scopes.items():
        assert scope["id"] == scope_id, f"{scope_id}: record id disagrees"
        for child in scope.get("children") or []:
            assert child in scopes, f"{scope_id} lists missing child {child}"
            parent = scopes[child].get("parent_id")
            assert parent == scope_id, (
                f"{child} is a child of {scope_id} but says parent {parent!r}"
            )
        parent = scope.get("parent_id")
        if parent is not None:
            assert parent in scopes, f"{scope_id}: dangling parent {parent!r}"
            assert scope_id in (scopes[parent].get("children") or []), (
                f"{scope_id} names parent {parent} but is not in its children"
            )


def test_the_camp_still_owns_its_21_areas():
    payload = _camp()
    camp = payload["world_scopes"][NEW]
    assert len(camp["area_ids"]) == 21, len(camp["area_ids"])
    owned = [k for k, v in payload["graph"]["nodes"].items()
             if v.get("type") == "area"
             and v.get("properties", {}).get("world_scope_id") == NEW]
    assert len(owned) == 21
    assert set(owned) == set(camp["area_ids"]), (
        "the scope's area_ids and the nodes that claim it have drifted apart"
    )


def test_the_child_scope_repointed_and_no_other_scope_moved():
    scopes = _camp()["world_scopes"]
    assert scopes["test"].get("parent_id") == NEW
    assert NEW in (scopes["world"].get("children") or [])
    assert scopes["west_woods"].get("world_scope_id") != NEW
    assert len(scopes["west_woods"]["area_ids"]) == 53
    assert len(scopes["world"]["area_ids"]) == 51


# ── the migration itself ───────────────────────────────────────────────────


def _old_fixture():
    """A scenario in the pre-migration shape, so the tool is tested on data."""
    return {
        "world_scopes": {
            "world": {"id": "world", "name": "world", "children": [OLD],
                      "area_ids": ["area_a"]},
            OLD: {"id": OLD, "name": "goblin camp", "children": ["inner"],
                  "area_ids": ["area_a", "area_b"],
                  "placements": {OLD: {"10,10": "area_a"}}},
            "inner": {"id": "inner", "name": "inner", "parent_id": OLD,
                      "area_ids": []},
        },
        "graph": {"nodes": {
            "area_a": {"id": "area_a", "type": "area", "name": "A",
                       "properties": {"world_scope_id": OLD,
                                      "cell": {"x": 1, "y": 2}}},
            "area_other": {"id": "area_other", "type": "area", "name": "Other",
                           "properties": {"world_scope_id": "world"}},
            "way_z": {"id": "way_z", "type": "way", "name": "Z",
                      "properties": {"world_scope_id": OLD}},
        }, "edges": []},
    }


def test_the_migration_renames_every_reference():
    report = migrate(_old_fixture(), OLD, NEW)
    assert report["error"] is None
    assert report["leftovers"] == []
    data_after = _old_fixture()
    migrate(data_after, OLD, NEW)

    scopes = data_after["world_scopes"]
    assert OLD not in scopes and NEW in scopes
    assert scopes["world"]["children"] == [NEW]
    assert scopes[NEW]["children"] == ["inner"]
    assert scopes["inner"]["parent_id"] == NEW
    assert NEW in scopes[NEW]["placements"]
    assert data_after["graph"]["nodes"]["area_a"]["properties"]["world_scope_id"] == NEW
    assert data_after["graph"]["nodes"]["way_z"]["properties"]["world_scope_id"] == NEW
    # And nothing else moved.
    assert data_after["graph"]["nodes"]["area_other"]["properties"]["world_scope_id"] \
        == "world"
    assert scopes["world"]["area_ids"] == ["area_a"]


def test_the_migration_renames_area_ids_minted_from_the_scope_id():
    """A compiled grid mints `area_<scope>_<x>_<y>`, so a rename has to follow
    the node id or every reference to those cells dangles."""
    data = _old_fixture()
    nodes = data["graph"]["nodes"]
    cell = {"id": f"area_{OLD}_10_14", "type": "area", "name": "Forest",
            "properties": {"world_scope_id": OLD}}
    nodes[cell["id"]] = cell
    data["world_scopes"][OLD]["area_ids"].append(cell["id"])

    migrate(data, OLD, NEW)
    renamed = f"area_{NEW}_10_14"
    assert renamed in data["graph"]["nodes"]
    assert cell["id"] == renamed, "the record's own id must follow its key"
    assert data["graph"]["nodes"][renamed]["properties"]["world_scope_id"] == NEW
    assert renamed in data["world_scopes"][NEW]["area_ids"]


def test_the_migration_is_a_no_op_the_second_time():
    data = _old_fixture()
    assert migrate(data, OLD, NEW)["changes"]
    second = migrate(data, OLD, NEW)
    assert second["changes"] == []
    assert second.get("already"), "a re-run should say 'already', not error"


def test_the_migration_refuses_to_merge_two_scopes():
    data = _old_fixture()
    data["world_scopes"]["goblin_camp"] = {"id": "goblin_camp", "name": "taken",
                                           "area_ids": []}
    report = migrate(data, OLD, NEW)
    assert "refusing" in report["error"]
    assert OLD in data["world_scopes"], "a refused migration changes nothing"
    assert NEW in data["world_scopes"]


def test_the_migration_reports_an_unrecognised_reference_instead_of_ignoring_it():
    """The whole point of the leftover scan: a reference in a shape the script
    did not anticipate is a report, not a silent breakage."""
    data = _old_fixture()
    data["some_future_field"] = {"note": f"see {OLD} for details"}
    report = migrate(data, OLD, NEW)
    assert report["error"] is None
    assert report["leftovers"], "an unknown reference was missed"
    assert any("some_future_field" in path for path in report["leftovers"])


def test_the_migration_says_so_when_there_is_nothing_to_rename():
    data = _old_fixture()
    report = migrate(data, "no_such_scope", "whatever")
    assert "no scope" in report["error"]
    assert report["changes"] == []


def test_the_migration_refuses_a_scenario_with_no_scopes():
    report = migrate({"graph": {"nodes": {}}}, OLD, NEW)
    assert "no world_scopes" in report["error"]


def test_the_migration_does_not_mutate_its_input_on_a_refusal():
    data = _old_fixture()
    before = copy.deepcopy(data)
    migrate(data, "nope", "also_nope")
    assert data == before


@pytest.mark.parametrize("old,new", [("deep_woods_2", "goblin_camp")])
def test_the_pair_in_the_tool_matches_the_task(old, new):
    from tools import migrate_scope_id

    assert migrate_scope_id.DEFAULT_FROM == old
    assert migrate_scope_id.DEFAULT_TO == new


def test_the_camp_file_still_parses_as_utf8_json():
    raw = CAMP.read_bytes()
    raw.decode("utf-8")
    payload = json.loads(raw.decode("utf-8"))
    assert payload["_scenario_name"] == "kraktooth_goblin_camp"
