"""One-time migration: split monolithic registry JSONs into per-entity files under data/library/."""

import json
import os
import sys
import shutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
LIBRARY_DIR = os.path.join(DATA_DIR, 'library')


def split_registry(filename, subdir):
    """Read a monolithic registry JSON and write one file per entry."""
    src = os.path.join(DATA_DIR, filename)
    dst = os.path.join(LIBRARY_DIR, subdir)
    os.makedirs(dst, exist_ok=True)

    if not os.path.exists(src):
        print(f"  [SKIP] {filename} not found")
        return

    with open(src, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)

    count = 0
    for key, value in data.items():
        safe = f"{key}.json"
        path = os.path.join(dst, safe)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(value, f, indent=2, ensure_ascii=False)
        count += 1

    print(f"  [OK] {filename} -> {count} files in {subdir}/")


def copy_standalone_characters():
    """Copy standalone character JSONs (jake.json, etc.) into library/characters/."""
    dst = os.path.join(LIBRARY_DIR, 'characters')
    standalone = ['jake.json', 'kyrie.json', 'kayla.json', 'sammy.json']
    count = 0
    for fn in standalone:
        src = os.path.join(DATA_DIR, fn)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dst, fn))
            count += 1
            print(f"  [OK] {fn} -> library/characters/")
        else:
            print(f"  [SKIP] {fn} not found")
    return count


def migrate():
    print("Migrating monolithic registries to per-entity files...\n")

    split_registry('items.json', 'items')
    split_registry('characters.json', 'characters')
    split_registry('traits.json', 'traits')

    sc = copy_standalone_characters()

    # Check for areas/ scenarios that could also be library entries
    scenarios_dir = os.path.join(DATA_DIR, 'scenarios')
    if os.path.exists(scenarios_dir):
        for fn in os.listdir(scenarios_dir):
            if fn.endswith('.json'):
                shutil.copy2(
                    os.path.join(scenarios_dir, fn),
                    os.path.join(LIBRARY_DIR, 'areas', fn)
                )
                print(f"  [OK] scenarios/{fn} -> library/areas/")

    print(f"\nDone. Library is at: {LIBRARY_DIR}")
    print("You can now delete the old monolithic files if desired.")


if __name__ == '__main__':
    migrate()
