#!/usr/bin/env python3
"""compile_scenario.py — compile a folder-authored scenario into one JSON (task-408).

Authoring a whole scenario as a single JSON has proven unreliable for LLMs:
one entity per small file is reviewable and individually regeneratable. This
compiles such a folder into the single-file shape the runtime already loads.

Layout::

    <scenario>/
      scenario.json      # manifest: name + runtime config + world_lore/scopes
      rooms/*.json       # one area per file ("areas/" is accepted too)
      ways/*.json
      items/*.json
      characters/*.json  # each becomes a player + a canonical player node
      triggers/*.json    # optional

Deterministic: files are read in sorted order, ids are derived from filenames,
and output is written with sorted keys — compiling twice is byte-identical.

Usage:
    python tools/compile_scenario.py --input data/scenarios/src/goblin --output data/scenarios/goblin.json
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = Path(__file__).resolve().parent
for _path in (ROOT, TOOLS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from build_scenario import build_scenario, load_component_dir_at  # noqa: E402

MANIFEST_RUNTIME_KEYS = (
    "active_player", "clock_start_hour", "clock_start_minute", "game_time",
    "ghost_mode", "narration_mode", "time_per_tick_minutes", "turn_order",
    "world_state", "world_lore", "world_scopes", "schedules", "simultaneous_mode",
    "turn_interval_ms", "simultaneous_act_limit", "knowledge", "world_events",
    "population", "events",
)

PLAYER_KEYS = (
    "name", "description", "personality", "autonomy", "simple_npc", "stats",
    "skills", "vitals", "traits", "tags", "equipped", "decay_rates",
    "relationships", "memories", "interest_tags", "state", "conditions",
)


def load_json(path: Path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def resolve_dir_names(folder: Path):
    """Map canonical kind -> actual folder name. Supports ``rooms/`` for areas."""
    names = {}
    if not (folder / "areas").exists() and (folder / "rooms").exists():
        names["areas"] = "rooms"
    return names


def compile_players(folder: Path, dir_names, scenario: dict) -> dict:
    """Build the ``players`` block from ``characters/*.json``.

    ``current_area`` must be the area DISPLAY NAME (engine convention —
    ``engine/room_perception.resolve_area_node`` matches by name), so the
    authored area id is translated here. IDs are stable per player key.
    """
    nodes = scenario["graph"]["nodes"]
    id_to_name = {n["id"]: n.get("name", n["id"])
                  for n in nodes.values() if n.get("type") == "area"}

    char_folder = dir_names.get("characters", "characters")
    players = {}
    for stem, comp in load_component_dir_at(folder / char_folder):
        entry = {}
        for key in PLAYER_KEYS:
            if key in comp:
                entry[key] = comp[key]
        name = entry.get("name") or stem
        entry.setdefault("name", name)
        entry.setdefault("description", "")
        entry.setdefault("personality", "")
        entry.setdefault("autonomy", False)
        entry.setdefault("simple_npc", False)
        entry.setdefault("tags", [])
        entry.setdefault("traits", {})
        current_area = comp.get("current_area")
        entry["current_area"] = id_to_name.get(current_area, current_area)
        key = comp.get("player_key") or name
        players[key] = entry

    return {k: players[k] for k in sorted(players)}


def compile_scenario(folder: Path) -> dict:
    folder = Path(folder)
    manifest = {}
    manifest_path = folder / "scenario.json"
    if manifest_path.exists():
        manifest = load_json(manifest_path)

    dir_names = resolve_dir_names(folder)

    runtime_overrides = {k: manifest[k] for k in MANIFEST_RUNTIME_KEYS if k in manifest}
    graph_scenario = build_scenario(folder, runtime_overrides, dir_names)

    graph_scenario["players"] = compile_players(folder, dir_names, graph_scenario)
    graph_scenario["_scenario_name"] = manifest.get("name") or folder.name
    return graph_scenario


def main():
    ap = argparse.ArgumentParser(description="Compile a folder-authored scenario to one JSON.")
    ap.add_argument("--input", required=True, help="Scenario source folder")
    ap.add_argument("--output", required=True, help="Output scenario JSON path")
    args = ap.parse_args()

    folder = Path(args.input)
    if not folder.is_dir():
        print(f"Input folder not found: {folder}", file=sys.stderr)
        sys.exit(1)

    scenario = compile_scenario(folder)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(scenario, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                   encoding="utf-8")

    nodes = scenario["graph"]["nodes"]
    counts = {}
    for node in nodes.values():
        counts[node.get("type")] = counts.get(node.get("type"), 0) + 1
    print(f"Wrote {out}")
    print(f"Nodes: {counts} | players: {len(scenario['players'])} | "
          f"edges: {len(scenario['graph']['edges'])}")


if __name__ == "__main__":
    main()
