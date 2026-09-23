import json
import os
from pathlib import Path

scenario_dir = Path(r"C:\Projects\virtual-world\data\scenarios")
results = []

for path in sorted(scenario_dir.glob("*.json")):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        results.append((path.name, f"LOAD ERROR: {e}"))
        continue

    graph = data.get("graph", {})
    nodes = graph.get("nodes", {})
    edges = graph.get("edges", [])
    players = data.get("players", {})

    # Count node types
    node_types = {}
    for nid, node in nodes.items():
        ntype = node.get("type", node.get("node_type", "unknown"))
        node_types[ntype] = node_types.get(ntype, 0) + 1

    # Count items
    items = [n for n in nodes.values() if n.get("type") == "item"]
    item_count = len(items)

    # Count characters
    chars = [n for n in nodes.values() if n.get("type") == "character"]
    char_count = len(chars)

    # Count areas
    areas = [n for n in nodes.values() if n.get("type") == "area"]
    area_count = len(areas)

    # Count ways
    ways = [n for n in nodes.values() if n.get("type") == "way"]
    way_count = len(ways)

    # Count triggers
    triggers = [n for n in nodes.values() if n.get("type") == "logic_trigger"]
    trigger_count = len(triggers)

    # Count trigger edges
    trigger_edges = [e for e in edges if e.get("type") == "triggers"]
    trigger_edge_count = len(trigger_edges)

    # Weather / forecast
    forecast = data.get("forecast", None)
    weather_info = "none"
    if forecast:
        weather_info = json.dumps(forecast)[:200]

    # World lore
    lore = data.get("world_lore", "")
    lore_preview = lore[:300] if lore else ""

    # Starting clock
    clock_start_hour = data.get("clock_start_hour", "?")
    clock_start_minute = data.get("clock_start_minute", "?")
    time_per_tick = data.get("time_per_tick_minutes", "?")

    # Active player
    active = data.get("active_player", "?")

    # Mature content
    mature = data.get("mature_content", False)

    # Scenario name
    scen_name = data.get("_scenario_name", data.get("scenario_name", path.stem))

    # Count equipped/carrying edges
    equipped_edges = [e for e in edges if e.get("type") == "equipped"]
    carrying_edges = [e for e in edges if e.get("type") == "carrying"]
    in_edges = [e for e in edges if e.get("type") == "in"]

    # Tags on nodes
    all_tags = set()
    for node in nodes.values():
        tags = node.get("tags", [])
        if isinstance(tags, list):
            all_tags.update(tags)

    # Player keys
    player_keys = list(players.keys())

    results.append({
        "file": path.name,
        "name": scen_name,
        "nodes_total": len(nodes),
        "areas": area_count,
        "ways": way_count,
        "characters": char_count,
        "items": item_count,
        "logic_triggers": trigger_count,
        "trigger_edges": trigger_edge_count,
        "equipped_edges": len(equipped_edges),
        "carrying_edges": len(carrying_edges),
        "in_edges": len(in_edges),
        "total_edges": len(edges),
        "player_keys": player_keys,
        "player_count": len(players),
        "clock_start": f"{clock_start_hour}:{clock_start_minute:02d}" if isinstance(clock_start_minute, int) else f"{clock_start_hour}:{clock_start_minute}",
        "time_per_tick_min": time_per_tick,
        "mature": mature,
        "forecast": weather_info[:150],
        "lore_preview": lore_preview[:200],
        "node_types": node_types,
        "tags": sorted(all_tags)[:30],
    })

# Print summary
print("=" * 120)
print(f"{'FILE':<45} {'NAME':<30} {'NODES':>6} {'AREA':>5} {'WAY':>5} {'CHAR':>5} {'ITEM':>5} {'TRIG':>5} {'EDGES':>6} {'PLAYERS':>7}")
print("=" * 120)

for r in results:
    if isinstance(r, str):
        print(f"  {r}")
        continue
    print(f"{r['file']:<45} {r['name']:<30} {r['nodes_total']:>6} {r['areas']:>5} {r['ways']:>5} {r['characters']:>5} {r['items']:>5} {r['logic_triggers']:>5} {r['total_edges']:>6} {r['player_count']:>7}")

print("\n")
print("=" * 120)
print("DETAILED PER SCENARIO")
print("=" * 120)

for r in results:
    if isinstance(r, str):
        print(f"\n--- {r} ---")
        continue
    print(f"\n--- {r['file']} ---")
    print(f"  Name:           {r['name']}")
    print(f"  Nodes:          {r['nodes_total']} total  (areas={r['areas']}, ways={r['ways']}, chars={r['characters']}, items={r['items']}, triggers={r['logic_triggers']})")
    print(f"  Edges:          {r['total_edges']} total  (equipped={r['equipped_edges']}, carrying={r['carrying_edges']}, in={r['in_edges']}, trigger={r['trigger_edges']})")
    print(f"  Players:        {r['player_count']}  -> {r['player_keys']}")
    print(f"  Clock:          {r['clock_start']}  tick={r['time_per_tick_min']}min  mature={r['mature']}")
    print(f"  Forecast:       {r['forecast']}")
    print(f"  Lore preview:   {r['lore_preview']}")
    print(f"  Node types:     {r['node_types']}")
    print(f"  Tags:           {r['tags']}")
