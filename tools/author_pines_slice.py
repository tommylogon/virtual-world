"""Author the Pines vertical slice: scope manifest + background schedules (task-400).

Data pass only — no new engine behaviour. It writes:

- a `world_scopes` manifest: Millbrook Falls -> Downtown / The Pines -> floors ->
  apartments, with every existing area assigned to its scope (`world_scope_id`);
- an unmade `apartment_3b` scope (recipe + stable seed) for the generation demo;
- authored daily schedules for five residents, chosen for different outcomes.

Dry-run by default; `--write` saves the scenario back through the standard
`_save_scenario` path so nothing is authored by a parallel code path.

    python tools/author_pines_slice.py            # show the plan
    python tools/author_pines_slice.py --write    # apply it
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.schedule import normalize as normalize_schedule

#: scope_id -> record. `apartment_3b` is `unmade`: generation-on-open proves the
#: frontier (task-398/task-400) without generating the whole complex.
MANIFEST = {
    "millbrook_falls": {
        "id": "millbrook_falls", "name": "Millbrook Falls", "kind": "settlement",
        "children": ["downtown", "the_pines"],
    },
    "downtown": {
        "id": "downtown", "name": "Downtown District", "kind": "district",
        "parent_id": "millbrook_falls",
        "area_ids": ["area_street", "area_downtown_district", "area_town_square",
                     "area_the_daily_grind", "area_vargas_fitness",
                     "area_suds_&_duds_laundromat"],
    },
    "the_pines": {
        "id": "the_pines", "name": "The Pines Apartment Complex", "kind": "building",
        "parent_id": "downtown",
        "children": ["pines_ground", "pines_floor_1", "pines_floor_2",
                     "pines_floor_3", "pines_roof"],
    },
    "pines_ground": {
        "id": "pines_ground", "name": "Ground Floor", "kind": "floor",
        "parent_id": "the_pines", "area_ids": ["area_main_lobby"],
    },
    "pines_floor_1": {
        "id": "pines_floor_1", "name": "Floor 1", "kind": "floor",
        "parent_id": "the_pines",
        "area_ids": ["area_hallway_1", "area_apartment_1a", "area_apartment_1b",
                     "area_apartment_1d", "area_apartment_1e", "area_apartment_1f"],
    },
    "pines_floor_2": {
        "id": "pines_floor_2", "name": "Floor 2", "kind": "floor",
        "parent_id": "the_pines",
        "area_ids": ["area_hallway_2", "area_apartment_2a", "area_apartment_2b",
                     "area_apartment_2c", "area_apartment_2d", "area_apartment_2e"],
    },
    "pines_floor_3": {
        "id": "pines_floor_3", "name": "Floor 3", "kind": "floor",
        "parent_id": "the_pines", "children": ["apartment_3a", "apartment_3b"],
        "area_ids": ["area_hallway_3"],
    },
    "apartment_3a": {
        "id": "apartment_3a", "name": "Apartment 3A", "kind": "apartment",
        "parent_id": "pines_floor_3", "area_ids": ["area_apartment_3a"],
    },
    "apartment_3b": {
        "id": "apartment_3b", "name": "Apartment 3B", "kind": "apartment",
        "parent_id": "pines_floor_3", "state": "unmade",
        "recipe": "apartment.v1", "seed": "pines-3b-01",
    },
    "pines_roof": {
        "id": "pines_roof", "name": "Roof", "kind": "floor", "parent_id": "the_pines",
        "area_ids": ["area_rooftop", "area_attic"],
    },
}

#: area node id -> the scope it belongs to (mirrors the manifest for rendering).
AREA_SCOPES = {
    "area_main_lobby": "pines_ground",
    "area_hallway_1": "pines_floor_1",
    "area_apartment_1a": "pines_floor_1",
    "area_apartment_1b": "pines_floor_1",
    "area_apartment_1d": "pines_floor_1",
    "area_apartment_1e": "pines_floor_1",
    "area_apartment_1f": "pines_floor_1",
    "area_hallway_2": "pines_floor_2",
    "area_apartment_2a": "pines_floor_2",
    "area_apartment_2b": "pines_floor_2",
    "area_apartment_2c": "pines_floor_2",
    "area_apartment_2d": "pines_floor_2",
    "area_apartment_2e": "pines_floor_2",
    "area_hallway_3": "pines_floor_3",
    "area_apartment_3a": "pines_floor_3",
    "area_rooftop": "pines_roof",
    "area_attic": "pines_roof",
    "area_street": "downtown",
    "area_downtown_district": "downtown",
    "area_town_square": "downtown",
    "area_the_daily_grind": "downtown",
    "area_vargas_fitness": "downtown",
    "area_suds_&_duds_laundromat": "downtown",
}

#: Five residents with deliberately different days: working away, working at
#: home, roaming, waiting, and keeping a night routine. Areas are named exactly
#: as the scenario stores `current_area`.
SCHEDULES = {
    "miki": [
        {"start": "08:00", "activity": "work", "area": "the daily grind", "fallback": "wait"},
        {"start": "17:30", "activity": "socialise", "area": "main lobby", "fallback": "wait"},
        {"start": "22:00", "activity": "sleep", "area": "apartment 1b", "fallback": "rest"},
    ],
    "rose": [
        {"start": "07:30", "activity": "work", "area": "suds & duds laundromat", "fallback": "wait"},
        {"start": "18:00", "activity": "socialise", "area": "main lobby", "fallback": "wait"},
        {"start": "23:00", "activity": "sleep", "area": "apartment 1b", "fallback": "rest"},
    ],
    "kevin": [
        {"start": "07:00", "activity": "work", "area": "vargas fitness", "fallback": "wait"},
        {"start": "19:00", "activity": "roam", "area": "street", "fallback": "wait"},
        {"start": "22:30", "activity": "sleep", "area": "apartment 3a", "fallback": "rest"},
    ],
    "haruka": [
        {"start": "08:30", "activity": "work", "area": "town square", "fallback": "wait"},
        {"start": "18:00", "activity": "wait", "area": "hallway 2", "fallback": "wait"},
        {"start": "22:00", "activity": "sleep", "area": "apartment 2b", "fallback": "rest"},
    ],
    "mateo": [
        {"start": "10:00", "activity": "work", "area": "attic", "fallback": "wait"},
        {"start": "20:00", "activity": "roam", "area": "rooftop", "fallback": "wait"},
        {"start": "23:00", "activity": "sleep", "area": "attic", "fallback": "rest"},
    ],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default=os.path.join("data", "scenarios", "pines.json"))
    ap.add_argument("--write", action="store_true", help="save the scenario (else dry run)")
    args = ap.parse_args()

    with open(args.scenario, encoding="utf-8-sig") as fh:
        data = json.load(fh)

    changed = 0
    scopes = data.get("world_scopes")
    if not isinstance(scopes, dict):
        scopes = {}
        data["world_scopes"] = scopes
    new_scopes = [sid for sid in MANIFEST if sid not in scopes]
    scopes.update(MANIFEST)
    changed += len(new_scopes)
    print("scopes: +%d (%s)" % (len(new_scopes), ", ".join(new_scopes) or "none"))

    graph_nodes = (data.get("graph") or {}).get("nodes") or {}
    for area_id, scope_id in AREA_SCOPES.items():
        node = graph_nodes.get(area_id)
        if node is None:
            print("  ! no such area: %s" % area_id)
            continue
        props = node.setdefault("properties", {})
        if props.get("world_scope_id") != scope_id:
            props["world_scope_id"] = scope_id
            changed += 1
            print("  ~ %-30s -> %s" % (area_id, scope_id))

    players = data.get("players") or {}
    for player_name, steps in SCHEDULES.items():
        player = players.get(player_name)
        if player is None:
            print("  ! no such player: %s" % player_name)
            continue
        normalised = normalize_schedule(steps)
        if player.get("schedule") != normalised:
            player["schedule"] = normalised
            changed += 1
            print("  + schedule %-10s %d steps" % (player_name, len(normalised)))
        else:
            print("  = schedule %-10s already current" % player_name)

    print("\n%d change(s)" % changed)
    if not changed:
        return 0
    if not args.write:
        print("dry run — rerun with --write to save")
        return 1
    with open(args.scenario, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("wrote", args.scenario)
    return 0


if __name__ == "__main__":
    sys.exit(main())
