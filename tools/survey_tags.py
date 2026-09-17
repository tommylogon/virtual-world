"""task-324 survey: dump area + furniture tag inventory for domain-tag design.

Usage: python tools/survey_tags.py
Prints:
  1. All areas with their current tags (name, id, tags)
  2. All furniture items (tagged 'furniture') with their tags
  3. Tag vocabulary summary
"""
import glob, json, os, sys

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "library")

def load(name):
    out = {}
    for path in sorted(glob.glob(os.path.join(LIB, name, "*.json"))):
        fid = os.path.splitext(os.path.basename(path))[0]
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            d["_file"] = fid
            out[fid] = d
        except Exception as e:
            print(f"SKIP {name}/{fid}: {e}", file=sys.stderr)
    return out

areas = load("areas")
items = load("items")

print("=== AREAS (%d) ===" % len(areas))
for fid, a in sorted(areas.items()):
    print(f"{fid}\t{a.get('name','')}\t{a.get('tags', [])}")

print("\n=== FURNITURE ITEMS (%d) ===" % sum(1 for i in items.values() if "furniture" in [t.lower() for t in i.get("tags", [])]))
for fid, i in sorted(items.items()):
    tags = [t.lower() for t in i.get("tags", [])]
    if "furniture" in tags:
        print(f"{fid}\t{i.get('name','')}\t{tags}")

print("\n=== ALL ITEM TAG VOCABULARY (%d distinct) ===" % len({t.lower() for i in items.values() for t in i.get("tags", [])}))
print(sorted({t.lower() for i in items.values() for t in i.get("tags", [])}))

print("\n=== AREA TAG VOCABULARY (%d distinct) ===" % len({t.lower() for a in areas.values() for t in a.get("tags", [])}))
print(sorted({t.lower() for a in areas.values() for t in a.get("tags", [])}))