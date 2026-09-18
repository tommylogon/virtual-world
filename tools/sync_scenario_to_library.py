#!/usr/bin/env python3
"""
sync_scenario_to_library.py — Extract scenario components into the library.

Usage:
    python tools/sync_scenario_to_library.py --scenario data/scenarios/kraktooth_goblin_camp.json
"""

import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(name: str) -> str:
    safe = "".join(c if c.isalnum() else "_" for c in name.lower())
    parts = [p for p in safe.split("_") if p]
    return "_".join(parts)


def sync_areas(scenario: dict, library_dir: Path):
    nodes = scenario.get("graph", {}).get("nodes", {})
    area_dir = library_dir / "areas"
    area_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for node_id, node in nodes.items():
        if node.get("type") != "area":
            continue
        props = node.get("properties", {})
        entry = {
            "name": node.get("name", node_id),
            "description": props.get("description", props.get("goblin_description", "")),
            "tags": props.get("tags", []),
            "environment": props.get("environment", {}),
            "items": [],
            "exits": [],
            "triggers": []
        }
        path = area_dir / f"{slugify(node.get('name', node_id))}.json"
        save_json(path, entry)
        count += 1
    print(f"Synced {count} areas to {area_dir}")
    return count


def sync_items(scenario: dict, library_dir: Path):
    nodes = scenario.get("graph", {}).get("nodes", {})
    item_dir = library_dir / "items"
    item_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for node_id, node in nodes.items():
        if node.get("type") != "item":
            continue
        props = node.get("properties", {})
        entry = {
            "name": node.get("name", node_id),
            "description": props.get("description", ""),
            "actions": props.get("actions", []),
            "uses": props.get("uses", -1),
            "weight": props.get("weight", 1),
            "current_state": props.get("current_state", "normal"),
            "light_level": props.get("light_level", "dim"),
            "defense": props.get("defense", 0),
            "damage": props.get("damage", props.get("damage_dice", "0")),
            "insulation": props.get("insulation", 0),
            "tags": props.get("tags", []),
            "triggers": props.get("triggers", []),
            "contents": props.get("contents", [])
        }
        path = item_dir / f"{slugify(node.get('name', node_id))}.json"
        save_json(path, entry)
        count += 1
    print(f"Synced {count} items to {item_dir}")
    return count


def sync_characters(scenario: dict, library_dir: Path):
    nodes = scenario.get("graph", {}).get("nodes", {})
    players = scenario.get("players", {})
    char_dir = library_dir / "characters"
    char_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for node_id, node in nodes.items():
        if node.get("type") != "character":
            continue
        props = node.get("properties", {})
        player = players.get(node.get("name", ""), {})
        entry = {
            "name": node.get("name", node_id),
            "personality": props.get("personality", ""),
            "description": props.get("description", ""),
            "base_description": props.get("base_description", props.get("description", "")),
            "unknown_name": "",
            "stats": props.get("stats", {}),
            "vitals": props.get("vitals", {}),
            "decay_rates": props.get("decay_rates", {}),
            "skills": props.get("skills", {}),
            "traits": props.get("traits", {}),
            "tags": props.get("tags", []),
            "interest_tags": props.get("interest_tags", []),
            "state": player.get("state", props.get("state", "awake")),
            "conditions": player.get("conditions", props.get("conditions", {"awake": [{"duration": None, "level": 0, "source": None}]})),
            "equipped": player.get("equipped", props.get("equipped", {})),
            "emotion": props.get("emotion", {}),
            "memories": props.get("memories", []),
            "relationships": props.get("relationships", {}),
            "behaviors": player.get("behaviors", props.get("behaviors", [])),
            "inventory": [],
            "current_area": player.get("current_area", props.get("current_area", "")),
            "autonomy": player.get("autonomy", props.get("autonomy", True)),
            "simple_npc": player.get("simple_npc", props.get("simple_npc", False))
        }
        path = char_dir / f"{slugify(node.get('name', node_id))}.json"
        save_json(path, entry)
        count += 1
    print(f"Synced {count} characters to {char_dir}")
    return count


def sync_ways(scenario: dict, library_dir: Path):
    nodes = scenario.get("graph", {}).get("nodes", {})
    way_dir = library_dir / "ways"
    way_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for node_id, node in nodes.items():
        if node.get("type") != "way":
            continue
        props = node.get("properties", {})
        entry = {
            "name": node.get("name", node_id),
            "description": props.get("description", ""),
            "pass_message": props.get("pass_message", f"You pass through {node.get('name', node_id)}."),
            "visible_in_direction": props.get("visible_in_direction", ""),
            "hidden": props.get("hidden", False),
            "tags": props.get("tags", []),
            "area_from": props.get("area_from", ""),
            "area_to": props.get("area_to", ""),
            "direction_a": props.get("direction_a", "north"),
            "direction_b": props.get("direction_b", "south"),
            "current_state": props.get("current_state", "open"),
            "needs_open": props.get("needs_open", {}),
            "cost": props.get("cost", {}),
            "requires": props.get("requires", "none")
        }
        path = way_dir / f"{slugify(node.get('name', node_id))}.json"
        save_json(path, entry)
        count += 1
    print(f"Synced {count} ways to {way_dir}")
    return count


def sync_triggers(scenario: dict, library_dir: Path):
    nodes = scenario.get("graph", {}).get("nodes", {})
    trigger_dir = library_dir / "triggers"
    trigger_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for node_id, node in nodes.items():
        if node.get("type") != "logic_trigger":
            continue
        props = node.get("properties", {})
        entry = {
            "name": node.get("name", node_id),
            "trigger_type": props.get("event", props.get("trigger_type", "on_examine")),
            "target": props.get("target", ""),
            "target_name": props.get("target", ""),
            "target_state": props.get("target_state", ""),
            "conditions": props.get("conditions", []),
            "conditions_logic": props.get("conditions_logic", "and"),
            "effects": props.get("effects", []),
            "once": props.get("once", False),
            "success_message": props.get("message", ""),
            "fail_message": ""
        }
        path = trigger_dir / f"{slugify(node.get('name', node_id))}.json"
        save_json(path, entry)
        count += 1
    print(f"Synced {count} triggers to {trigger_dir}")
    return count


def main():
    parser = argparse.ArgumentParser(description="Sync scenario components to library.")
    parser.add_argument("--scenario", required=True, help="Path to scenario JSON")
    parser.add_argument("--library", default="data/library", help="Library root directory")
    args = parser.parse_args()

    scenario_path = Path(args.scenario)
    library_dir = Path(args.library)

    if not scenario_path.exists():
        print(f"Scenario not found: {scenario_path}")
        sys.exit(1)

    scenario = load_json(scenario_path)
    total = 0
    total += sync_areas(scenario, library_dir)
    total += sync_items(scenario, library_dir)
    total += sync_characters(scenario, library_dir)
    total += sync_ways(scenario, library_dir)
    total += sync_triggers(scenario, library_dir)
    print(f"Done. Synced {total} total components to {library_dir}")


if __name__ == "__main__":
    main()
