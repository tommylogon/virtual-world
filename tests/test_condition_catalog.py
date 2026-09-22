"""task-462: conditions are a data-driven catalog.

The runtime truth is data/library/conditions/*.json; the hardcoded dict is the
fallback. These tests cover the derived constants, the idempotent seeder
(backfill without clobbering edits) and the in-place reload the library API
calls after a write.
"""

import json
import os

import pytest

from engine import player_conditions as pc


@pytest.fixture
def temp_condition_dir(monkeypatch, tmp_path):
    """Point the catalog at a scratch dir, then restore the real catalog."""
    monkeypatch.setattr(pc, "_condition_library_dir", lambda: str(tmp_path))
    yield tmp_path
    monkeypatch.undo()
    pc.reload_condition_library()


class TestDerivedCatalog:
    """Derived constants come from catalog data, not hand-maintained lists."""

    def test_hierarchy_is_ordered_and_excludes_unordered(self):
        assert pc.CONDITION_HIERARCHY[0] == "dead"
        assert pc.CONDITION_HIERARCHY[-1] == "awake"
        assert len(pc.CONDITION_HIERARCHY) == 22
        # Mature arousal state is surfaced by the mature prompt path, not here.
        assert "aroused" not in pc.CONDITION_HIERARCHY

    def test_perception_skip_comes_from_data(self):
        assert pc.PERCEPTION_SKIP == {"awake", "dead", "grappled"}

    def test_mature_conditions_flagged_in_data(self):
        assert len(pc.MATURE_CONDITIONS) == 10
        assert "aroused" in pc.MATURE_CONDITIONS
        assert "poisoned" not in pc.MATURE_CONDITIONS

    def test_every_entry_carries_the_metadata_keys(self):
        for cid, definition in pc.CONDITION_DEFINITIONS.items():
            assert "order" in definition, cid
            assert "perception_skip" in definition, cid
            assert "mature" in definition, cid

    def test_blocking_is_in_place_mutable(self):
        # reload() updates it in place; a frozen set would silently go stale
        assert isinstance(pc.BLOCKING_CONDITIONS, set)


class TestSeeder:
    def test_writes_one_file_per_condition(self, temp_condition_dir):
        pc.seed_condition_library()
        files = {f[:-5] for f in os.listdir(temp_condition_dir) if f.endswith(".json")}
        assert files == set(pc.CONDITION_DEFINITIONS)

    def test_preserves_edited_values_and_only_fills_missing_keys(self, temp_condition_dir):
        pc.seed_condition_library()
        path = os.path.join(temp_condition_dir, "aroused.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["attack_mod"] = -9
        data.pop("mature", None)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        pc.seed_condition_library()

        with open(path, "r", encoding="utf-8") as f:
            reread = json.load(f)
        assert reread["attack_mod"] == -9, "seeder clobbered an edited value"
        assert reread["mature"] is True, "seeder did not backfill the missing key"

    def test_is_idempotent(self, temp_condition_dir):
        pc.seed_condition_library()
        before = {f: os.path.getmtime(os.path.join(temp_condition_dir, f))
                  for f in os.listdir(temp_condition_dir)}
        pc.seed_condition_library()
        after = {f: os.path.getmtime(os.path.join(temp_condition_dir, f))
                 for f in os.listdir(temp_condition_dir)}
        assert before == after, "second seed rewrote untouched files"


class TestReload:
    def test_picks_up_a_library_edit_without_restart(self, temp_condition_dir):
        pc.seed_condition_library()
        path = os.path.join(temp_condition_dir, "aroused.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["order"] = 0
        data["mature"] = False
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        pc.reload_condition_library()

        assert pc.CONDITION_DEFINITIONS["aroused"]["order"] == 0
        assert pc.CONDITION_HIERARCHY[0] == "aroused"
        assert "aroused" not in pc.MATURE_CONDITIONS

    def test_reload_restores_builtin_for_deleted_file(self, temp_condition_dir):
        pc.seed_condition_library()
        os.remove(os.path.join(temp_condition_dir, "poisoned.json"))
        pc.reload_condition_library()
        # falls back to the built-in catalog entry
        assert "poisoned" in pc.CONDITION_DEFINITIONS
