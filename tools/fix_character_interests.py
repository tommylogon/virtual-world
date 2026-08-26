"""Fix character interest_tags across data/library/characters/.

Modes per character:
  set   — replace interest_tags wholesale (empty/dead-only characters)
  patch — drop listed tags, append listed tags, keep everything else

Every resulting tag is validated against the library item-tag vocabulary;
unknown tags hard-error before anything is written (dry-run shows them).
Run tools/lint_library.py --check dead_interests afterwards: must be clean.

Usage:
  python tools/fix_character_interests.py            # dry-run
  python tools/fix_character_interests.py --apply    # write changes
"""

import json
import os
import sys

CHAR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "library", "characters")
ITEM_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "library", "items")

# file_id (stem) -> ("set", [tags]) or ("patch", {"drop": [...], "add": [...]})
FIXES = {
    # ── empty characters: full sets ──────────────────────────────────
    "Gromm": ("set", ["weapon", "melee", "meat", "bone", "fire", "drink", "wooden", "heavy"]),
    "Kaelen Voss": ("set", ["clue", "evidence", "documents", "letter", "key",
                            "book", "journal", "secret", "investigation", "weapon"]),
    "Lyrie": ("set", ["elven", "flower", "linen", "clothing", "jewelry",
                      "candle", "doll", "candy"]),
    "Viktor": ("set", ["weapon", "armor", "meat", "drink", "bandage",
                       "medical", "money", "blood"]),
    "Violet halloway": ("set", ["candy", "phone", "music", "toy", "book",
                                "secret", "clue", "clothing"]),
    "rat": ("set", ["food", "cheese", "warmth"]),
    # ── patches: drop dead, add live, keep the rest ──────────────────
    "amber": ("patch", {"drop": ["game", "video", "pizza", "sports", "romance", "cute"],
                        "add": ["toy", "food", "drink", "letter", "jewelry"]}),
    "angeline": ("patch", {"drop": ["alcohol", "party", "home"],
                           "add": ["jewelry", "mirror"]}),
    "anna": ("patch", {"drop": ["cigarette", "snack", "tv", "alcohol"],
                       "add": ["wine", "money", "phone", "clothing"]}),
    "anne": ("patch", {"drop": ["family", "home", "dark"],
                       "add": ["candle", "diary"]}),
    "audrey": ("patch", {"drop": ["coffee", "record", "guitar", "cat", "garden"],
                         "add": ["tea", "instrument", "plant", "companion"]}),
    "brittany": ("patch", {"drop": ["record", "guitar", "punk"],
                           "add": ["instrument", "leather"]}),
    "ghost": ("patch", {"drop": ["locket"], "add": []}),
    "james": ("patch", {"drop": [], "add": ["tea", "journal", "knowledge", "writing"]}),
    "jessie": ("patch", {"drop": ["necklace", "game"],
                         "add": ["bandage", "drink", "clothing", "weapon"]}),
    "kayla-sister": ("patch", {"drop": [], "add": ["cosmetic", "jewelry", "restraint", "mirror"]}),
    "kaylee": ("patch", {"drop": ["animal", "egg", "farming"],
                         "add": ["plant", "vegetation", "ingredient", "meal"]}),
    "kissy": ("patch", {"drop": ["perfume", "lipstick"],
                        "add": ["cosmetic", "clothing", "jewelry", "flower"]}),
    "koharu-biyori": ("patch", {"drop": [], "add": ["flower", "tea", "doll", "clothing"]}),
    "kyrie": ("patch", {"drop": ["wrench"], "add": []}),
    "eliza-reed": ("patch", {"drop": [], "add": ["tea", "knowledge", "writing"]}),
    "feral-goblin": ("patch", {"drop": ["treat", "window"], "add": ["gold", "key"]}),
    "miiya": ("patch", {"drop": [], "add": ["toy", "headphones", "energy_drink", "drink"]}),
    "lopunny": ("patch", {"drop": ["berry", "wood"],
                          "add": ["honey", "plant", "warmth"]}),
    "lydia": ("patch", {"drop": [], "add": ["cosmetic", "clothing", "music", "drink"]}),
    "mamako": ("patch", {"drop": [], "add": ["tea", "soap", "flower", "warmth", "clothing"]}),
    "maya": ("patch", {"drop": ["cute", "color", "sweet"],
                       "add": ["jewelry", "hair_accessory"]}),
    "miki-takahashi": ("patch", {"drop": ["ramen", "convenience_store", "gang", "street_food"],
                                 "add": ["food", "drink", "clothing", "candy", "knife"]}),
    "nia": ("patch", {"drop": ["cuffs", "uniform", "patrol", "gym", "suspects"],
                      "add": ["weapon", "clothing", "evidence", "clue", "key",
                              "restraint", "food"]}),
    "nina": ("patch", {"drop": ["videogames", "strategy", "boardgame", "gaming", "plush"],
                       "add": ["toy", "headphones", "phone", "electric", "energy_drink", "book"]}),
    "pam": ("patch", {"drop": ["books", "animals", "studying", "science", "videogames", "homework"],
                      "add": ["book", "eyewear", "tea", "knowledge", "candy", "phone", "plant"]}),
    "satsuki": ("patch", {"drop": ["track", "running", "gym", "hoodies", "sports", "competition"],
                          "add": ["clothing", "outerwear", "footwear", "water",
                                  "energy_drink", "music", "phone"]}),
    "tala": ("patch", {"drop": ["garden", "record", "home"], "add": ["plant", "flower"]}),
    "uzume-chan": ("patch", {"drop": ["farming", "gardening", "animals", "livestock", "cooking", "produce"],
                             "add": ["plant", "vegetation", "ingredient", "meal", "tool", "water"]}),
}


def load_item_vocab():
    vocab = set()
    for filename in os.listdir(ITEM_DIR):
        if filename.endswith(".json"):
            with open(os.path.join(ITEM_DIR, filename), encoding="utf-8") as handle:
                for tag in json.load(handle).get("tags", []):
                    vocab.add(str(tag).strip().lower())
    return vocab


def main():
    apply = "--apply" in sys.argv
    vocab = load_item_vocab()
    changed = unchanged = errors = 0

    for filename in sorted(os.listdir(CHAR_DIR)):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(CHAR_DIR, filename)
        file_id = filename[:-5]
        if file_id not in FIXES:
            continue

        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        current = list(data.get("interest_tags") or [])
        mode, spec = FIXES[file_id]

        if mode == "set":
            new_tags = list(spec)
        else:
            new_tags = [t for t in current if t not in spec.get("drop", [])]
            for tag in spec.get("add", []):
                if tag not in new_tags:
                    new_tags.append(tag)

        unknown = sorted({t for t in new_tags if str(t).lower() not in vocab})
        if unknown:
            print(f"ERROR {file_id}: tags not in item vocabulary: {', '.join(unknown)}")
            errors += 1
            continue

        if new_tags == current:
            unchanged += 1
            continue

        dropped = [t for t in current if t not in new_tags]
        added = [t for t in new_tags if t not in current]
        print(f"{'APPLY' if apply else 'PLAN '} {file_id} ({len(new_tags)} tags)")
        if dropped:
            print(f"        drop: {', '.join(dropped)}")
        if added:
            print(f"        add : {', '.join(added)}")

        if apply:
            data["interest_tags"] = new_tags
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
        changed += 1

    action = "Applied" if apply else "Planned"
    print(f"\n{action}: {changed} characters changed, {unchanged} already clean, "
          f"{errors} blocked by validation errors")


if __name__ == "__main__":
    main()
