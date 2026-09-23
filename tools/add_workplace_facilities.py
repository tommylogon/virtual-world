"""Give the camp's workplaces the facilities a working day needs (task-409).

Measured first: 16 scheduled characters produced 388 hops of schedule travel and
only 53 work blocks over three days, and their Hygiene/Social/Entertainment
collapsed (48.8 vs 69.2 off). The diagnosis at the time was arithmetic — that a
background character takes one action per 10 game minutes, leaving ~96 actions a
day, and that a working day of twelve 30-minute blocks cannot fit alongside the
survival errands.

**That diagnosis was wrong, and this tool is kept with the caveat rather than
used.** The real cause was that the background tier was on a different clock from
the live one (see `ACTIONS_PER_TURN` in engine/background_simulation.py — it is now
one action per turn, matching live play). Worse, this pass *made things worse* and
was reverted: tagging work areas `latrine`/`water` broke the no-schedule baseline
too (Hygiene 69.2 → 24.4), because **area tags are not neutral** — they are what
`_areas_with` consults for *every* need search, so tagging the work areas
redirected where the whole camp travelled for every need. Any future use of this
must be measured against a schedule-less baseline, not just the scheduled run.

The intended shape remains reasonable in principle: a settlement puts water, a
latrine and somewhere to wash where people actually work, rather than in one
corner. It just cannot be applied as a local data tweak.

Two mechanisms, chosen because neither consumes anything:

- **Area tags** — `latrine` and `water` are already how the engine models "you can
  relieve/drink here" (`_in_water_area`, `RELIEF_TAGS`). `recreation` likewise
  works as an area tag through `_service_here`.
- **`wash_spot` fixtures** — the existing library item, used by `_wash` and never
  consumed.

Deliberately NOT tagged `water` on the fixtures: a drinkable *item* is destroyed by
`_consume_here` (anything with `uses <= 1` is removed), so a barrel would vanish on
first use. Water has to be the area tag.

Dry-run by default; `--apply` writes. Idempotent.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEFAULT_SCENARIO = ROOT / "data" / "scenarios" / "kraktooth_goblin_camp.json"

#: Areas characters are scheduled to work in, and what to give them. Tags are
#: added, never replaced, so existing authoring is preserved.
FACILITIES = {
    "Workshop": {"tags": ["water", "latrine", "recreation"], "wash": True},
    "Scouting Rooms": {"tags": ["water", "latrine"], "wash": False},
    "Training Pit": {"tags": ["water", "latrine", "recreation"], "wash": True},
    "Chief's Den": {"tags": ["water", "latrine"], "wash": False},
    "Scrap Pile": {"tags": ["water", "latrine"], "wash": False},
    "Food Storage": {"tags": ["water", "latrine"], "wash": False},
    "Cooking Area": {"tags": ["water", "latrine", "recreation"], "wash": True},
    # Outside the cave: the trail and the village have natural water and a
    # latrine pit; the farmer has the ruins of a farmstead.
    "Camp Entrance Trail": {"tags": ["water", "latrine"], "wash": False},
    "Eldenford": {"tags": ["water", "latrine", "recreation"], "wash": True},
    "Human Road": {"tags": ["water"], "wash": False},
    "Abandoned Farm": {"tags": ["water", "latrine"], "wash": False},
}

WASH_SPOT = "wash_spot"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default=str(DEFAULT_SCENARIO))
    parser.add_argument("--apply", action="store_true",
                        help="write the changes (default: dry run)")
    args = parser.parse_args()

    path = Path(args.scenario)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    nodes = data["graph"]["nodes"]
    if isinstance(nodes, dict):
        nodes = list(nodes.values())
    by_name = {n["name"]: n for n in nodes if n.get("type") == "area"}

    missing = sorted(set(FACILITIES) - set(by_name))
    if missing:
        print(f"ERROR: no such area(s) in the scenario: {missing}")
        return 1

    # The library entry the fixture is copied from, so the placed node carries the
    # authored `on_use → adjust_vital Hygiene` trigger and is never consumed.
    library_item = json.loads(
        (ROOT / "data" / "library" / "items" / f"{WASH_SPOT}.json")
        .read_text(encoding="utf-8-sig"))

    changed_tags = 0
    placed = 0
    for area_name, spec in sorted(FACILITIES.items()):
        node = by_name[area_name]
        props = node.setdefault("properties", {})
        tags = list(props.get("tags") or [])
        lowered = {str(t).lower() for t in tags}
        added = [t for t in spec["tags"] if t not in lowered]
        if added:
            props["tags"] = tags + added
            changed_tags += 1
            print(f"  {area_name:24s} +tags {added}")

        if not spec.get("wash"):
            continue
        fixture_id = f"item_wash_spot_{area_name}".lower().replace(" ", "_").replace("'", "")
        exists = any(n.get("id") == fixture_id for n in nodes)
        if exists:
            continue
        placed += 1
        placed_node = {
            "id": fixture_id,
            "type": "item",
            "name": "Wash Basin",
            "properties": {
                "name": "Wash Basin",
                "description": library_item.get("description", ""),
                "actions": library_item.get("actions", "examine,use"),
                "uses": library_item.get("uses", -1),
                "weight": library_item.get("weight", 0.1),
                "current_state": library_item.get("current_state", "normal"),
                "tags": list(library_item.get("tags") or []),
                "library_id": WASH_SPOT,
            },
        }
        nodes.append(placed_node)
        data["graph"]["edges"].append({
            "source": fixture_id, "target": node["id"], "type": "in",
            "properties": {},
        })
        print(f"  {area_name:24s} +a wash basin ({fixture_id})")

    # Triggers are copied at placement in the real app; a scenario needs the
    # trigger nodes too or the fixture grants nothing.
    existing_triggers = {e["source"] for e in data["graph"]["edges"]
                         if e.get("type") == "triggers"}
    for area_name, spec in sorted(FACILITIES.items()):
        if not spec.get("wash"):
            continue
        fixture_id = f"item_wash_spot_{area_name}".lower().replace(" ", "_").replace("'", "")
        if fixture_id in existing_triggers:
            continue
        trigger_id = f"trigger_{fixture_id}"
        if any(n.get("id") == trigger_id for n in nodes):
            continue
        nodes.append({
            "id": trigger_id,
            "type": "logic_trigger",
            "name": "on_use → adjust_vital",
            "properties": {
                "trigger_type": "on_use",
                "effect_type": "adjust_vital",
                "effect_params": {"stat": "Hygiene", "amount": 70, "target": "self"},
                "success_message": "You scrub yourself clean.",
            },
        })
        data["graph"]["edges"].append({
            "source": fixture_id, "target": trigger_id, "type": "triggers",
            "properties": {},
        })

    print(f"\n{changed_tags} area(s) tagged, {placed} wash basin(s) to place")
    if not args.apply:
        print("\n(dry run — pass --apply to write)")
        return 0
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
