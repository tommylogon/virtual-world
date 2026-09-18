#!/usr/bin/env python3
"""
validate_scenario.py — Validate a scenario JSON against engine conventions.

Usage:
    python tools/validate_scenario.py --input data/scenarios/kraktooth_goblin_camp.json
"""

import argparse
import json
import sys
from pathlib import Path


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_areas(nodes: dict, issues: list):
    areas = [n for n in nodes.values() if n.get("type") == "area"]
    if not areas:
        issues.append("No areas found — the world will be empty after load.")
    for area_id, node in nodes.items():
        if node.get("type") != "area":
            continue
        name = node.get("name", "")
        if not name:
            issues.append(f"Area {area_id} has empty name.")
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


def validate_triggers(nodes: dict, edges: list, issues: list):
    trigger_targets = {e.get("source") for e in edges if e.get("type") == "triggers"}
    for trigger_id, node in nodes.items():
        if node.get("type") != "logic_trigger":
            continue
        props = node.get("properties", {})
        target = props.get("target")
        if not target:
            issues.append(f"Trigger {trigger_id} missing target.")
        elif target not in nodes:
            issues.append(f"Trigger {trigger_id} targets missing node '{target}'.")
        if trigger_id not in trigger_targets:
            issues.append(f"Trigger {trigger_id} has no incoming triggers edge.")


def validate_players(players: dict, nodes: dict, issues: list):
    area_ids = {nid for nid, n in nodes.items() if n.get("type") == "area"}
    for player_name, player in players.items():
        current_area = player.get("current_area")
        if current_area and current_area not in area_ids:
            issues.append(f"Player '{player_name}' is in missing area '{current_area}'.")


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


def main():
    parser = argparse.ArgumentParser(description="Validate a Viwo scenario JSON.")
    parser.add_argument("--input", required=True, help="Path to scenario JSON")
    args = parser.parse_args()

    path = Path(args.input)
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    try:
        data = load_json(str(path))
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        sys.exit(1)

    issues = validate_scenario(data)
    if issues:
        print(f"Found {len(issues)} issue(s):")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("Scenario validation passed.")


if __name__ == "__main__":
    main()
