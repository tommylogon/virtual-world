#!/usr/bin/env python3
"""
assemble_scenario.py — Scenario assembly workflow driver.

Usage:
    python tools/assemble_scenario.py --goal "Kraktooth goblin camp sandbox" \
        --seed data/scenarios/kraktooth_goblin_camp.json \
        --constraints '{"areas":30,"ways":29,"characters":23}' \
        --output data/scenarios/kraktooth_goblin_camp_assembled.json
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


def load_library_entry(library_dir: Path, kind: str, entry_id: str):
    path = library_dir / kind / f"{entry_id}.json"
    if not path.exists():
        return None
    return load_json(path)


def build_scenario_from_components(
    seed: dict | None,
    library_dir: Path,
    constraints: dict | None,
) -> dict:
    constraints = constraints or {}
    target_areas = int(constraints.get("areas", 0))
    target_ways = int(constraints.get("ways", 0))
    target_characters = int(constraints.get("characters", 0))
    target_items = int(constraints.get("items", 0))

    if seed:
        scenario = json.loads(json.dumps(seed))
    else:
        scenario = {
            "active_player": "player_human_explorer",
            "clock_start_hour": 6,
            "clock_start_minute": 0,
            "current_area": "area_camp_entrance_trail",
            "game_time": "06:00:00",
            "ghost_mode": False,
            "narration_mode": "none",
            "time_per_tick_minutes": 1,
            "time_ticks": 0,
            "turn_number": 0,
            "turn_order": "sequential",
            "world_state": {
                "season": "summer",
                "day": 1,
                "weather": "clear",
                "river_level": "normal",
                "human_patrol_activity": "medium",
                "wolf_activity": "medium",
                "goblin_food_stock": 60,
                "camp_mood": "tense but stable",
            },
            "population": {},
            "events": [],
            "world_lore": [],
            "item_registry": {},
            "players_in_area": [],
            "players": {},
            "graph": {"nodes": {}, "edges": []},
            "schedules": {},
            "simultaneous_mode": False,
            "turn_interval_ms": 1000,
            "simultaneous_act_limit": 3,
            "knowledge": {},
            "world_events": [],
        }

    nodes = scenario.setdefault("graph", {}).setdefault("nodes", {})
    edges = scenario.setdefault("graph", {}).setdefault("edges", [])

    existing_areas = {nid for nid, n in nodes.items() if n.get("type") == "area"}
    existing_items = {nid for nid, n in nodes.items() if n.get("type") == "item"}
    existing_characters = {nid for nid, n in nodes.items() if n.get("type") == "character"}
    existing_ways = {nid for nid, n in nodes.items() if n.get("type") == "way"}

    # Supplement areas from library only if under target or missing
    if target_areas and len(existing_areas) < target_areas:
        area_dir = library_dir / "areas"
        if area_dir.exists():
            imported = 0
            for path in sorted(area_dir.glob("*.json")):
                entry = load_json(path)
                name = entry.get("name", path.stem)
                area_id = f"area_{name.lower().replace(' ', '_').replace('-', '_')}"
                if area_id in nodes:
                    continue
                nodes[area_id] = {
                    "id": area_id,
                    "type": "area",
                    "name": name,
                    "properties": {
                        "description": entry.get("description", ""),
                        "environment": entry.get("environment", {"light": "normal", "temperature": 18.0, "air": "fresh", "smell": "neutral", "noise": "quiet"}),
                        "human_description": entry.get("description", ""),
                        "goblin_description": entry.get("description", ""),
                        "goblin_knowledge": {"known_as": name, "importance": "medium", "common_activities": []},
                        "features": entry.get("features", []),
                        "possible_items": entry.get("items", []),
                        "possible_encounters": [],
                        "tags": entry.get("tags", []),
                        "floor": 0,
                        "central_gravity_enabled": False,
                    },
                }
                imported += 1
                if len([n for n in nodes.values() if n.get("type") == "area"]) >= target_areas:
                    break
            print(f"Imported {imported} areas from library")

    # Supplement items from library only if a target is set and unmet
    if library_dir and target_items and len(existing_items) < target_items:
        item_dir = library_dir / "items"
        if item_dir.exists():
            placed = 0
            for path in sorted(item_dir.glob("*.json")):
                entry = load_json(path)
                item_name = entry.get("name", path.stem)
                item_id = f"item_{item_name.lower().replace(' ', '_').replace('-', '_')}"
                if item_id in nodes:
                    continue
                props = {
                    "description": entry.get("description", ""),
                    "actions": entry.get("actions", ["examine", "take", "drop"]),
                    "uses": entry.get("uses", -1),
                    "weight": entry.get("weight", 1),
                    "current_state": entry.get("current_state", "normal"),
                    "hidden": entry.get("hidden", False),
                    "light_level": entry.get("light_level", "dim"),
                    "defense": entry.get("defense", 0),
                    "damage": entry.get("damage", entry.get("damage_dice", "0")),
                    "insulation": entry.get("insulation", 0),
                    "tags": entry.get("tags", []),
                    "triggers": entry.get("triggers", []),
                    "contents": entry.get("contents", []),
                }
                if "weapon" in [t.lower() for t in props["tags"]]:
                    props.setdefault("damage_dice", "1d4")
                    props.setdefault("damage_type", "slashing")
                    props.setdefault("equip_slots", ["hand"])
                if "armor" in [t.lower() for t in props["tags"]]:
                    props.setdefault("equip_slots", ["torso"])
                if "container" in [t.lower() for t in props["tags"]]:
                    props.setdefault("max_weight_capacity", 10)
                nodes[item_id] = {"id": item_id, "type": "item", "name": item_name, "properties": props}
                area_candidates = [nid for nid in nodes if nodes[nid].get("type") == "area"]
                if area_candidates:
                    edges.append({"source": item_id, "target": area_candidates[0], "type": "in", "properties": {}})
                placed += 1
                if len(existing_items) + placed >= target_items:
                    break
            print(f"Imported {placed} items from library")

    # Supplement characters from library only if a target is set and unmet
    if library_dir and target_characters and len(existing_characters) < target_characters:
        char_dir = library_dir / "characters"
        if char_dir.exists():
            placed = 0
            for path in sorted(char_dir.glob("*.json")):
                entry = load_json(path)
                char_name = entry.get("name", path.stem)
                char_id = f"character_{char_name.lower().replace(' ', '_').replace('-', '_')}"
                if char_id in nodes:
                    continue
                area_candidates = [nid for nid in nodes if nodes[nid].get("type") == "area"]
                current_area = area_candidates[0] if area_candidates else ""
                props = {
                    "description": entry.get("description", ""),
                    "personality": entry.get("personality", ""),
                    "base_description": entry.get("base_description", entry.get("description", "")),
                    "stats": entry.get("stats", {}),
                    "skills": entry.get("skills", {}),
                    "vitals": entry.get("vitals", {}),
                    "tags": entry.get("tags", []),
                    "emotion": entry.get("emotion", {"current": "neutral", "description": "", "intensity": 0.0}),
                    "traits": entry.get("traits", {}),
                    "interest_tags": entry.get("interest_tags", []),
                    "autonomy": True,
                    "simple_npc": False,
                    "memories": entry.get("memories", []),
                    "relationships": entry.get("relationships", {}),
                    "decay_rates": entry.get("decay_rates", {}),
                    "current_area": current_area,
                }
                nodes[char_id] = {"id": char_id, "type": "character", "name": char_name, "properties": props}
                if current_area:
                    scenario.setdefault("players", {})[char_name] = {
                        "current_area": current_area,
                        "simple_npc": False,
                        "autonomy": True,
                        "personality": entry.get("personality", ""),
                        "stats": entry.get("stats", {}),
                        "skills": entry.get("skills", {}),
                        "vitals": entry.get("vitals", {}),
                        "tags": entry.get("tags", []),
                        "emotion": entry.get("emotion", {"current": "neutral", "description": "", "intensity": 0.0}),
                        "traits": entry.get("traits", {}),
                        "interest_tags": entry.get("interest_tags", []),
                        "decay_rates": entry.get("decay_rates", {}),
                        "relationships": entry.get("relationships", {}),
                        "memories": entry.get("memories", []),
                    }
                placed += 1
                if len(existing_characters) + placed >= target_characters:
                    break
            print(f"Imported {placed} characters from library")

    # Supplement ways from library only if under target or missing
    if target_ways and len(existing_ways) < target_ways:
        way_dir = library_dir / "ways"
        if way_dir.exists():
            placed = 0
            for path in sorted(way_dir.glob("*.json")):
                entry = load_json(path)
                way_name = entry.get("name", path.stem)
                way_id = f"way_{way_name.lower().replace(' ', '_').replace('-', '_')}"
                if way_id in nodes:
                    continue
                props = {
                    "description": entry.get("description", ""),
                    "pass_message": entry.get("pass_message", f"You pass through {way_name}."),
                    "visible_in_direction": entry.get("visible_in_direction", ""),
                    "hidden": entry.get("hidden", False),
                    "tags": entry.get("tags", []),
                    "area_from": entry.get("area_from", ""),
                    "area_to": entry.get("area_to", ""),
                    "direction_a": entry.get("direction_a", "north"),
                    "direction_b": entry.get("direction_b", "south"),
                    "current_state": entry.get("current_state", "open"),
                    "needs_open": entry.get("needs_open", {}),
                    "cost": entry.get("cost", {}),
                    "requires": entry.get("requires", "none"),
                }
                nodes[way_id] = {"id": way_id, "type": "way", "name": way_name, "properties": props}
                placed += 1
            print(f"Imported {placed} ways from library")

    scenario["graph"]["nodes"] = nodes
    scenario["graph"]["edges"] = edges
    return scenario


def validate_areas(nodes: dict, issues: list):
    areas = [n for n in nodes.values() if n.get("type") == "area"]
    if not areas:
        issues.append("No areas found — the world will be empty after load.")
    for area_id, node in nodes.items():
        if node.get("type") != "area":
            continue
        props = node.get("properties", {})
        env = props.get("environment", {})
        for key in ("light", "temperature", "air", "smell", "noise"):
            if key not in env:
                issues.append(f"Area {area_id} missing environment.{key}.")


def validate_ways(nodes: dict, edges: list, issues: list):
    ways = {nid: n for nid, n in nodes.items() if n.get("type") == "way"}
    for way_id, node in ways.items():
        props = node.get("properties", {})
        if not props.get("pass_message"):
            issues.append(f"Way {way_id} has no pass_message.")
        area_from = props.get("area_from")
        area_to = props.get("area_to")
        if area_from and area_from not in nodes:
            issues.append(f"Way {way_id} area_from '{area_from}' missing.")
        if area_to and area_to not in nodes:
            issues.append(f"Way {way_id} area_to '{area_to}' missing.")
    connection_targets = {e.get("target") for e in edges if e.get("type") == "connection"}
    for way_id in ways:
        if way_id not in connection_targets:
            issues.append(f"Way {way_id} has no incoming connection edge.")


def validate_items(nodes: dict, issues: list):
    for item_id, node in nodes.items():
        if node.get("type") != "item":
            continue
        props = node.get("properties", {})
        tags = [t.lower() for t in props.get("tags", [])]
        if "weapon" in tags:
            if "damage_dice" not in props and "damage" not in props:
                issues.append(f"Item {item_id} has weapon tag but no damage.")
            if "damage_type" not in props:
                issues.append(f"Item {item_id} has weapon tag but no damage_type.")
        if "armor" in tags:
            if "equip_slots" not in props:
                issues.append(f"Item {item_id} has armor tag but no equip_slots.")
        if "container" in tags:
            if "max_weight_capacity" not in props:
                issues.append(f"Item {item_id} has container tag but no max_weight_capacity.")


def validate_characters(nodes: dict, issues: list):
    for char_id, node in nodes.items():
        if node.get("type") != "character":
            continue
        props = node.get("properties", {})
        if not props.get("description"):
            issues.append(f"Character {char_id} missing description.")


def validate_players(players: dict, nodes: dict, issues: list):
    area_ids = {nid for nid, n in nodes.items() if n.get("type") == "area"}
    for player_name, player in players.items():
        current_area = player.get("current_area")
        if current_area and current_area not in area_ids:
            issues.append(f"Player '{player_name}' is in missing area '{current_area}'.")


def validate_triggers(nodes: dict, edges: list, issues: list):
    trigger_targets = {e.get("source") for e in edges if e.get("type") == "triggers"}
    for trigger_id, node in nodes.items():
        if node.get("type") != "logic_trigger":
            continue
        if trigger_id not in trigger_targets:
            issues.append(f"Trigger {trigger_id} has no incoming triggers edge.")


def validate_scenario(data: dict) -> list:
    issues = []
    nodes = data.get("graph", {}).get("nodes", {})
    edges = data.get("graph", {}).get("edges", [])
    players = data.get("players", {})
    validate_areas(nodes, issues)
    validate_ways(nodes, edges, issues)
    validate_items(nodes, issues)
    validate_characters(nodes, issues)
    validate_triggers(nodes, edges, issues)
    validate_players(players, nodes, issues)
    return issues


def parse_constraints(raw: str) -> dict:
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def main():
    parser = argparse.ArgumentParser(description="Assemble a scenario from seed/library/constraints.")
    parser.add_argument("--goal", default="", help="Scenario goal/prompt")
    parser.add_argument("--image", default="", help="Optional reference image path/URL")
    parser.add_argument("--seed", default="", help="Optional seed scenario JSON")
    parser.add_argument("--library", default="data/library", help="Library root directory")
    parser.add_argument("--constraints", default="{}", help="JSON constraints, e.g. {\"areas\":30,\"ways\":29,\"characters\":23}")
    parser.add_argument("--output", default="data/scenarios/assembled_scenario.json", help="Output scenario JSON path")
    args = parser.parse_args()

    seed = load_json(Path(args.seed)) if args.seed and Path(args.seed).exists() else None
    constraints = parse_constraints(args.constraints)
    library_dir = Path(args.library)

    print("Stage 1: seed loaded" if seed else "Stage 1: blank world")
    scenario = build_scenario_from_components(seed, library_dir, constraints)

    print("Stage 2: library-backed assembly complete")
    issues = validate_scenario(scenario)
    if issues:
        print(f"Validation found {len(issues)} issue(s):")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("Validation passed.")

    out_path = Path(args.output)
    save_json(out_path, scenario)
    print(f"Wrote scenario to {out_path}")
    print(f"Areas: {len([n for n in scenario['graph']['nodes'].values() if n.get('type') == 'area'])}")
    print(f"Ways: {len([n for n in scenario['graph']['nodes'].values() if n.get('type') == 'way'])}")
    print(f"Items: {len([n for n in scenario['graph']['nodes'].values() if n.get('type') == 'item'])}")
    print(f"Characters: {len([n for n in scenario['graph']['nodes'].values() if n.get('type') == 'character'])}")
    print(f"Triggers: {len([n for n in scenario['graph']['nodes'].values() if n.get('type') == 'logic_trigger'])}")
    print(f"Edges: {len(scenario['graph']['edges'])}")


if __name__ == "__main__":
    main()
