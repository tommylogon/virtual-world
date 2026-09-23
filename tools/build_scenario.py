#!/usr/bin/env python3
"""
build_scenario.py — Assemble a scenario from component files.

Usage:
    python tools/build_scenario.py --components tools/scenario_components --output data/scenarios/kraktooth_goblin_camp.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.character_identity import canonical_character_node_id  # noqa: E402


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_component_dir_at(directory: Path) -> List[Tuple[str, dict]]:
    if not directory.exists():
        return []
    results = []
    for path in sorted(directory.glob("*.json")):
        try:
            data = load_json(path)
            results.append((path.stem, data))
        except json.JSONDecodeError as e:
            print(f"Warning: failed to parse {path}: {e}", file=sys.stderr)
    return results


def load_component_dir(base: Path, kind: str) -> List[Tuple[str, dict]]:
    return load_component_dir_at(base / kind)


def _slugify(name: str) -> str:
    safe = "".join(c if c.isalnum() else "_" for c in name.lower())
    parts = [p for p in safe.split("_") if p]
    return "_".join(parts)


def ensure_area_id(name: str) -> str:
    return f"area_{_slugify(name)}"


def ensure_way_id(name: str) -> str:
    return f"way_{_slugify(name)}"


def ensure_item_id(name: str) -> str:
    return f"item_{_slugify(name)}"


def ensure_character_id(name: str) -> str:
    return canonical_character_node_id(name)


def ensure_trigger_id(name: str) -> str:
    return f"logic_trigger_{_slugify(name)}"


def normalize_area(area: dict) -> dict:
    area.setdefault("type", "area")
    area.setdefault("id", ensure_area_id(area.get("name", "unnamed")))
    area.setdefault("name", area["id"].replace("area_", "").replace("_", " ").title())
    if not str(area["id"]).startswith("area_"):
        area["id"] = ensure_area_id(area.get("name") or area["id"])
    props = area.setdefault("properties", {})
    props.setdefault("description", "")
    props.setdefault("environment", {"light": "normal", "temperature": 18.0, "air": "fresh", "smell": "neutral", "noise": "quiet"})
    props.setdefault("tags", [])
    props.setdefault("floor", 0)
    props.setdefault("central_gravity_enabled", False)
    return area


def normalize_way(way: dict, area_ids: set) -> dict:
    way.setdefault("type", "way")
    way.setdefault("id", ensure_way_id(way.get("name", "unnamed")))
    way.setdefault("name", way["id"].replace("way_", "").replace("_", " ").title())
    if not str(way["id"]).startswith("way_"):
        way["id"] = ensure_way_id(way.get("name") or way["id"])
    props = way.setdefault("properties", {})
    props.setdefault("description", "")
    if not props.get("pass_message"):
        props["pass_message"] = f"You pass through {way['name']}."
    props.setdefault("area_from", "")
    props.setdefault("area_to", "")
    props.setdefault("current_state", "open")
    props.setdefault("hidden", False)
    props.setdefault("tags", [])
    props.setdefault("cost", {})
    if props["area_from"] not in area_ids or props["area_to"] not in area_ids:
        raise ValueError(f"Way {way['id']} references unknown area(s): {props.get('area_from')}, {props.get('area_to')}")
    return way


def normalize_item(item: dict) -> dict:
    item.setdefault("type", "item")
    item.setdefault("id", ensure_item_id(item.get("name", "unnamed")))
    item.setdefault("name", item["id"].replace("item_", "").replace("_", " ").title())
    if not str(item["id"]).startswith("item_"):
        item["id"] = ensure_item_id(item.get("name") or item["id"])
    props = item.setdefault("properties", {})
    props.setdefault("description", "")
    props.setdefault("actions", [])
    props.setdefault("weight", 1)
    props.setdefault("tags", [])
    props.setdefault("current_state", "normal")
    props.setdefault("hidden", False)
    tags = [t.lower() for t in props.get("tags", [])]
    if "weapon" in tags:
        props.setdefault("damage_dice", "1d4")
        props.setdefault("damage", 2)
        props.setdefault("damage_type", "slashing")
        props.setdefault("equip_slots", ["hand"])
    if "armor" in tags:
        props.setdefault("defense", 1)
        props.setdefault("equip_slots", ["torso"])
    if "container" in tags:
        props.setdefault("max_weight_capacity", 10)
    if "light_source" in tags:
        props.setdefault("light_level", 40)
    return item


def normalize_character(character: dict, area_ids: set) -> dict:
    character.setdefault("type", "character")
    character.setdefault("id", ensure_character_id(character.get("name", "unnamed")))
    character.setdefault(
        "name",
        character["id"].replace("player_", "").replace("character_", "").replace("_", " ").title(),
    )
    props = character.setdefault("properties", {})
    props.setdefault("description", "")
    props.setdefault("personality", "")
    current_area = character.get("current_area")
    if current_area and current_area not in area_ids:
        raise ValueError(f"Character {character['id']} references missing area '{current_area}'")
    return character


def _remap_refs(value: Any, remap: Dict[str, str]) -> Any:
    """Rewrite exact string references to a remapped node id, recursively."""
    if isinstance(value, dict):
        return {key: _remap_refs(item, remap) for key, item in value.items()}
    if isinstance(value, list):
        return [_remap_refs(item, remap) for item in value]
    if isinstance(value, str):
        return remap.get(value.lower(), value)
    return value


def canonicalize_character_ids(characters: List[dict], triggers: List[dict]) -> Dict[str, str]:
    """Point every character at the canonical ``player_<Name>`` node (task-463).

    Component filenames can carry a legacy ``character_<slug>`` id whose slug
    drifts from the display name; remap it and every trigger reference onto the
    runtime anchor so the built world has one node per character.
    """
    remap: Dict[str, str] = {}
    for character in characters:
        old_id = character.get("id")
        new_id = canonical_character_node_id(character.get("name") or old_id or "unnamed")
        if old_id and old_id != new_id:
            remap[str(old_id).lower()] = new_id
        character["id"] = new_id
    if remap:
        for trigger in triggers:
            trigger.update(_remap_refs(trigger, remap))
    return remap


def normalize_trigger(trigger: dict, node_ids: set) -> dict:
    trigger.setdefault("type", "logic_trigger")
    trigger.setdefault("id", ensure_trigger_id(trigger.get("name", "unnamed")))
    trigger.setdefault("name", trigger["id"].replace("logic_trigger_", "").replace("_", " ").title())
    if not str(trigger["id"]).startswith("logic_trigger_"):
        trigger["id"] = ensure_trigger_id(trigger.get("name") or trigger["id"])
    props = trigger.setdefault("properties", {})
    props.setdefault("event", "on_examine")
    props.setdefault("target", "")
    props.setdefault("once", False)
    props.setdefault("conditions", [])
    props.setdefault("conditions_logic", "and")
    props.setdefault("effects", [])
    if props.get("target") and props["target"] not in node_ids:
        raise ValueError(f"Trigger {trigger['id']} targets missing node '{props['target']}'")
    return trigger


def build_connection_edges(ways: List[dict]) -> List[dict]:
    edges = []
    for way in ways:
        wid = way.get("id")
        area_from = way.get("properties", {}).get("area_from")
        area_to = way.get("properties", {}).get("area_to")
        if not all([wid, area_from, area_to]):
            continue
        edges.append({
            "source": area_from,
            "target": wid,
            "type": "connection",
            "properties": {"direction": "out", "visible_in_direction": ""}
        })
        edges.append({
            "source": wid,
            "target": area_to,
            "type": "connection",
            "properties": {"direction": "enter"}
        })
        edges.append({
            "source": area_to,
            "target": wid,
            "type": "connection",
            "properties": {"direction": "out", "visible_in_direction": ""}
        })
        edges.append({
            "source": wid,
            "target": area_from,
            "type": "connection",
            "properties": {"direction": "enter"}
        })
    return edges


def build_in_edges(characters: List[dict], items: List[dict]) -> List[dict]:
    edges = []
    for char in characters:
        area = char.get("current_area")
        if area:
            edges.append({"source": char.get("id"), "target": area, "type": "in", "properties": {}})
    for item in items:
        area = item.get("current_area")
        if area:
            edges.append({"source": item.get("id"), "target": area, "type": "in", "properties": {}})
    return edges


def build_trigger_edges(triggers: List[dict]) -> List[dict]:
    edges = []
    for trigger in triggers:
        tid = trigger.get("id")
        target = trigger.get("properties", {}).get("target")
        if tid and target:
            edges.append({"source": target, "target": tid, "type": "triggers", "properties": {}})
    return edges


def load_components_with_ids(base: Path, kind: str, folder: str = None) -> List[dict]:
    """Load component files, using the filename stem as the node id.

    Component filenames are authored with the canonical id (e.g.
    ``area_chiefs_pit.json``); deriving the id from the display name instead
    makes punctuation-sensitive names ("Chief's Pit") drift from the ids the
    ways/characters reference.

    ``folder`` overrides the subdirectory name for this kind (e.g. ``rooms``
    instead of ``areas``), which the folder-authoring compiler uses.
    """
    entries = []
    for stem, data in load_component_dir_at(base / (folder or kind)):
        data.setdefault("id", stem)
        entries.append(data)
    return entries


def build_scenario(components_dir: Path, runtime_overrides: dict,
                   dir_names: Dict[str, str] = None) -> dict:
    names = dir_names or {}
    areas = [normalize_area(a) for a in load_components_with_ids(components_dir, "areas", names.get("areas"))]
    ways_raw = load_components_with_ids(components_dir, "ways", names.get("ways"))
    items = [normalize_item(i) for i in load_components_with_ids(components_dir, "items", names.get("items"))]
    characters = [normalize_character(c, {a["id"] for a in areas}) for c in load_components_with_ids(components_dir, "characters", names.get("characters"))]
    triggers_raw = load_components_with_ids(components_dir, "triggers", names.get("triggers"))
    canonicalize_character_ids(characters, triggers_raw)

    all_node_ids = {n["id"] for n in areas + ways_raw + items + characters + triggers_raw}
    ways = [normalize_way(w, {a["id"] for a in areas}) for w in ways_raw]
    triggers = [normalize_trigger(t, all_node_ids) for t in triggers_raw]

    nodes = {}
    for area in areas:
        nodes[area["id"]] = {"id": area["id"], "type": area["type"], "name": area["name"], "properties": area["properties"]}
    for way in ways:
        nodes[way["id"]] = {"id": way["id"], "type": way["type"], "name": way["name"], "properties": way["properties"]}
    for item in items:
        nodes[item["id"]] = {"id": item["id"], "type": item["type"], "name": item["name"], "properties": item["properties"]}
    for char in characters:
        nodes[char["id"]] = {"id": char["id"], "type": char["type"], "name": char["name"], "properties": char["properties"]}
    for trigger in triggers:
        nodes[trigger["id"]] = {"id": trigger["id"], "type": trigger["type"], "name": trigger["name"], "properties": trigger["properties"]}

    edges = []
    edges.extend(build_connection_edges(ways))
    edges.extend(build_in_edges(characters, items))
    edges.extend(build_trigger_edges(triggers))

    world = {
        "active_player": runtime_overrides.get("active_player", "player_human_explorer"),
        "clock_start_hour": runtime_overrides.get("clock_start_hour", 6),
        "clock_start_minute": runtime_overrides.get("clock_start_minute", 0),
        "current_area": runtime_overrides.get("current_area", areas[0]["id"] if areas else ""),
        "game_time": runtime_overrides.get("game_time", "06:00:00"),
        "ghost_mode": runtime_overrides.get("ghost_mode", False),
        "narration_mode": runtime_overrides.get("narration_mode", "none"),
        "time_per_tick_minutes": runtime_overrides.get("time_per_tick_minutes", 1),
        "time_ticks": runtime_overrides.get("time_ticks", 0),
        "turn_number": runtime_overrides.get("turn_number", 0),
        "turn_order": runtime_overrides.get("turn_order", "sequential"),
        "world_state": runtime_overrides.get("world_state", {}),
        "population": runtime_overrides.get("population", {}),
        "events": runtime_overrides.get("events", []),
        "world_lore": runtime_overrides.get("world_lore", []),
        "item_registry": {},
        "players_in_area": [],
        "players": runtime_overrides.get("players", {}),
        "graph": {"nodes": nodes, "edges": edges},
        "schedules": runtime_overrides.get("schedules", {}),
        "simultaneous_mode": runtime_overrides.get("simultaneous_mode", False),
        "turn_interval_ms": runtime_overrides.get("turn_interval_ms", 1000),
        "simultaneous_act_limit": runtime_overrides.get("simultaneous_act_limit", 3),
        "knowledge": runtime_overrides.get("knowledge", {}),
        "world_events": runtime_overrides.get("world_events", []),
    }
    return world


def main():
    parser = argparse.ArgumentParser(description="Build a scenario from component files.")
    parser.add_argument("--components", required=True, help="Path to scenario_components directory")
    parser.add_argument("--output", required=True, help="Output scenario JSON path")
    parser.add_argument("--runtime", default="", help="Optional runtime overrides JSON file")
    args = parser.parse_args()

    components_dir = Path(args.components)
    if not components_dir.exists():
        print(f"Components directory not found: {components_dir}")
        sys.exit(1)

    runtime_overrides = {}
    if args.runtime:
        runtime_path = Path(args.runtime)
        if runtime_path.exists():
            runtime_overrides = load_json(runtime_path)

    scenario = build_scenario(components_dir, runtime_overrides)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(scenario, f, indent=2, ensure_ascii=False)
    print(f"Wrote scenario to {out_path}")
    print(f"Areas: {len([n for n in scenario['graph']['nodes'].values() if n.get('type') == 'area'])}")
    print(f"Ways: {len([n for n in scenario['graph']['nodes'].values() if n.get('type') == 'way'])}")
    print(f"Items: {len([n for n in scenario['graph']['nodes'].values() if n.get('type') == 'item'])}")
    print(f"Characters: {len([n for n in scenario['graph']['nodes'].values() if n.get('type') == 'character'])}")
    print(f"Triggers: {len([n for n in scenario['graph']['nodes'].values() if n.get('type') == 'logic_trigger'])}")
    print(f"Edges: {len(scenario['graph']['edges'])}")


if __name__ == "__main__":
    main()
