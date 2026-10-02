"""task-513: the Kraktooth goblin gear spec emits valid, stable templates.

The gear matrix is authored as a compact spec and emitted by
`tools/gen_library_items.py`. These tests pin the properties the rest of the
engine relies on -- a weapon has damage and a damage type, a wearable declares a
real equip slot, tags are lowercase -- and that the emitted files still match the
spec (the compile-twice guarantee).
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import gen_library_items as gen

SPEC = ROOT / "data" / "library" / "items" / "_specs" / "kraktooth_gear.json"


def _spec():
    import json
    return json.loads(SPEC.read_text(encoding="utf-8-sig"))


def test_every_entry_emits_a_valid_template():
    items = gen.emit(_spec())
    assert items, "spec produced no items"
    for item_id, item in items.items():
        assert item.get("name"), item_id
        assert item.get("description"), item_id
        assert item.get("triggers") == []
        # `contents` is emitted only where the spec authors it (a carried
        # container); it is not a default. Blanket-assuming [] here rejected a
        # legitimate authored pouch, so assert the spec and the emission agree.
        spec_entry = _spec()["items"][item_id]
        assert item.get("contents") == (spec_entry.get("contents") or [])
        for tag in item.get("tags") or []:
            assert tag == tag.strip().lower(), f"{item_id}: {tag!r}"
        if item.get("equip_slots"):
            assert set(item["equip_slots"]) <= gen.VALID_SLOTS, item_id
        tags = set(item.get("tags") or [])
        if "weapon" in tags:
            assert item.get("damage"), f"{item_id}: weapon with no damage"
            assert item.get("damage_type") in gen.VALID_DAMAGE_TYPES, item_id
        if tags & {"clothing", "armor"}:
            assert item.get("equip_slots"), f"{item_id}: wearable with no slots"


def test_generator_check_is_clean():
    """Re-running the generator changes nothing: the emitted files are current."""
    items = gen.emit(_spec())
    for item_id, item in items.items():
        path = ROOT / "data" / "library" / "items" / f"{item_id}.json"
        assert path.exists(), f"missing emitted template {item_id}"
        assert path.read_text(encoding="utf-8") == gen._dump(item), item_id


def test_the_six_goblins_have_gear_in_the_spec():
    items = set(gen.emit(_spec()))
    for prefix in ("zikka_", "mikka_", "gribba_", "rikka_", "vekka_", "krikka_"):
        assert any(i.startswith(prefix) for i in items), f"no gear for {prefix}"


def test_invalid_category_is_rejected():
    with pytest.raises(ValueError):
        gen.build_item("bogus", {"category": "spaceship", "name": "x",
                                 "description": "y"})


def test_weapon_without_damage_type_is_rejected():
    with pytest.raises(ValueError):
        gen.build_item("bogus", {"category": "weapon", "name": "x",
                                 "description": "y", "damage": 3,
                                 "damage_type": "laser"})
