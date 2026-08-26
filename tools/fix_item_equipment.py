"""Backfill equip_slots on wearable library items and normalize tag casing.

One-time data fix (plus reusable validator):
  - Adds equip_slots to clothing/armor library items that lack them.
    Slot assignments are an explicit table reviewed against the conventions
    of items that already had slots (thong->legs, hoodie->torso, choker->neck,
    hair pins/earrings->accessory, boots->feet).
  - Lowercases and de-duplicates item tags (fixes 'Container'/'container',
    'Consumable'/'consumable' drift).

Usage:
  python tools/fix_item_equipment.py            # dry-run: print planned changes
  python tools/fix_item_equipment.py --apply    # write changes
"""

import json
import os
import sys

LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "library", "items")

# file_id (stem) -> equip_slots, primary slot first.
EQUIP_SLOT_FIXES = {
    "apron": ["torso"],
    "black_basketball_shorts": ["legs"],
    "black_choker": ["neck"],
    "black_cotton_panties": ["legs"],
    "black_crop_top": ["torso"],
    "black_ear_cuff_earrings": ["accessory"],
    "black_hair_tie": ["accessory"],
    "black_high_cut_thong": ["legs"],
    "black_hollow_star_hair_pin": ["accessory"],
    "blue_butterfly_earring": ["accessory"],
    "boxer_briefs": ["legs"],
    "cargo_shorts": ["legs"],
    "child_dress_item": ["torso"],
    "compression_shorts": ["legs"],
    "compression_sports_bra": ["torso"],
    "cotton_briefs": ["legs"],
    "cotton_training_bra": ["torso"],
    "dark_cargo_pants": ["legs"],
    "dark_trousers": ["legs"],
    "denim_cut_offs": ["legs"],
    "duct_tape_jacket": ["torso"],
    "faded_black_band_tee": ["torso"],
    "faded_green_tank_top": ["torso"],
    "field_jacket": ["torso"],
    "green_tunic": ["torso"],
    "grey_black_striped_hoodie": ["torso"],
    "grey_black_striped_thigh_high": ["legs"],
    "grey_tank_top": ["torso"],
    "heavy_black_boots": ["feet"],
    "heavy_fur_lined_coat": ["torso"],
    "hiking_boots": ["feet"],
    "kyrie_running_shoes": ["feet"],
    "lightweight_linen_shirt": ["torso"],
    "lyrie_linen_shift": ["torso"],
    "mismatched_socks": ["feet"],
    "oversized_arctic_monkeys_tee": ["torso"],
    "pink_star_twintail_band": ["accessory"],
    "reinforced_wool_trousers": ["legs"],
    "shoes": ["feet"],
    "short_forest_cape": ["back"],
    "sneakers": ["feet"],
    "sports_bra": ["torso"],
    "stained_work_shirt": ["torso"],
    "stirrup_socks": ["legs"],
    "stovepipe_leather_boots": ["feet"],
    "syringe_necklace": ["neck"],
    "torn_black_thigh_high_stocking": ["legs"],
    "upside_down_cross_hair_pin": ["accessory"],
    "waxed_canvas_vest": ["torso"],
    "wool_blend_undershirt_drawers": ["torso", "legs"],
}

VALID_SLOTS = {
    "head", "neck", "torso", "arms", "hands", "legs", "feet",
    "back", "waist", "accessory", "hand_left", "hand_right",
}


def normalize_tags(tags):
    """Lowercase tags, preserve order, drop duplicates."""
    seen = set()
    out = []
    for tag in tags:
        low = str(tag).strip().lower()
        if low and low not in seen:
            seen.add(low)
            out.append(low)
    return out


def main():
    apply = "--apply" in sys.argv
    slots_added = tags_fixed = skipped = 0

    for filename in sorted(os.listdir(LIB_DIR)):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(LIB_DIR, filename)
        file_id = filename[:-5]
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        changes = []

        if file_id in EQUIP_SLOT_FIXES:
            existing = data.get("equip_slots") or []
            if existing:
                skipped += 1
                print(f"SKIP {file_id}: already has equip_slots {existing}")
            else:
                slots = EQUIP_SLOT_FIXES[file_id]
                bad = [s for s in slots if s not in VALID_SLOTS]
                if bad:
                    print(f"ERROR {file_id}: invalid slots {bad}, not written")
                    continue
                changes.append(("equip_slots", slots))

        new_tags = normalize_tags(data.get("tags", []))
        if new_tags != data.get("tags", []):
            changes.append(("tags", new_tags))

        if not changes:
            continue

        for field, value in changes:
            print(f"{'APPLY' if apply else 'PLAN '} {file_id}: {field} = {value}")
            data[field] = value

        if any(f == "equip_slots" for f, _ in changes):
            slots_added += 1
        if any(f == "tags" for f, _ in changes):
            tags_fixed += 1

        if apply:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, ensure_ascii=False)
                handle.write("\n")

    action = "Applied" if apply else "Planned"
    print(f"\n{action}: equip_slots added to {slots_added} items, "
          f"tags normalized on {tags_fixed} items, skipped {skipped} (already slotted)")


if __name__ == "__main__":
    main()
