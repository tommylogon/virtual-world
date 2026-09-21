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

    # Skip empty/corrupt scenarios
    if not nodes and not players:
        results.append({
            "file": path.name,
            "name": data.get("_scenario_name", path.stem),
            "skip": "empty",
        })
        continue

    # Node type counts
    node_types = {}
    for nid, node in nodes.items():
        ntype = node.get("type", node.get("node_type", "unknown"))
        node_types[ntype] = node_types.get(ntype, 0) + 1

    areas = [n for n in nodes.values() if n.get("type") == "area"]
    ways = [n for n in nodes.values() if n.get("type") == "way"]
    chars = [n for n in nodes.values() if n.get("type") == "character"]
    items = [n for n in nodes.values() if n.get("type") == "item"]
    triggers = [n for n in nodes.values() if n.get("type") == "logic_trigger"]

    # Item tags
    food_items = [i.get("name","") for i in items if any(t in i.get("tags",[]) for t in ["food","eat","edible","meal","drink","water","beverage"])]
    weapon_items = [i.get("name","") for i in items if any(t in i.get("tags",[]) for t in ["weapon","damage","attack"])]
    container_items = [i.get("name","") for i in items if i.get("properties",{}).get("is_container") or "container" in i.get("tags",[])]

    # Trigger types
    trigger_types = {}
    for t in triggers:
        tt = t.get("properties", {}).get("trigger_type", t.get("trigger_type", "unknown"))
        if isinstance(tt, list):
            tt = ",".join(str(x) for x in tt)
        trigger_types[tt] = trigger_types.get(tt, 0) + 1

    # Weather / forecast
    forecast = data.get("forecast", {})
    weather_str = "none"
    if forecast:
        weather_str = json.dumps(forecast, ensure_ascii=False)[:300]

    # World lore
    lore = data.get("world_lore", [])
    lore_summary = ""
    if isinstance(lore, list):
        titles = [entry.get("title","") for entry in lore if isinstance(entry, dict)]
        lore_summary = "; ".join(titles[:8])
    elif isinstance(lore, str):
        lore_summary = lore[:300]

    # Clock / runtime
    clock_start_hour = data.get("clock_start_hour", "?")
    clock_start_minute = data.get("clock_start_minute", "?")
    time_per_tick = data.get("time_per_tick_minutes", "?")
    mature = data.get("mature_content", False)
    active_player = data.get("active_player", "?")
    scenario_name = data.get("_scenario_name", data.get("scenario_name", path.stem))

    # Edge counts by type
    edge_types = {}
    for e in edges:
        et = e.get("type", "unknown")
        edge_types[et] = edge_types.get(et, 0) + 1

    # Player info
    player_keys = list(players.keys())
    player_details = []
    for pk in player_keys[:5]:
        p = players[pk]
        if isinstance(p, dict):
            pname = p.get("name", p.get("personality", ""))[:60]
            simple = p.get("simple_npc", "?")
            autonomy = p.get("autonomy", "?")
            state = p.get("state", "?")
            current_area = p.get("current_area", "?")
            player_details.append(f"{pk}(s={simple},a={autonomy},st={state},area={current_area})")
        else:
            player_details.append(pk)
    player_details_str = " | ".join(player_details)

    results.append({
        "file": path.name,
        "name": scenario_name,
        "skip": False,
        "nodes_total": len(nodes),
        "areas": len(areas),
        "ways": len(ways),
        "characters": len(chars),
        "items": len(items),
        "logic_triggers": len(triggers),
        "total_edges": len(edges),
        "player_count": len(players),
        "player_keys": player_keys,
        "player_details": player_details_str,
        "clock_start": f"{clock_start_hour}:{clock_start_minute:02d}" if isinstance(clock_start_minute, int) else f"{clock_start_hour}:{clock_start_minute}",
        "time_per_tick_min": time_per_tick,
        "mature": mature,
        "forecast": weather_str[:200],
        "lore_summary": lore_summary[:300],
        "node_types": node_types,
        "edge_types": edge_types,
        "trigger_types": trigger_types,
        "food_items": food_items[:10],
        "weapon_items": weapon_items[:10],
        "container_items": container_items[:10],
        "char_names": [c.get("name","?") for c in chars[:25]],
    })

# Print compact table
print("=" * 130)
print(f"{'FILE':<42} {'NAME':<28} {'NODES':>5} {'AREA':>4} {'WAY':>4} {'CHR':>4} {'ITEM':>4} {'TRIG':>4} {'EDGES':>5} {'PLY':>3} {'TICK':>4}")
print("=" * 130)

for r in results:
    if isinstance(r, str):
        print(f"  {r}")
        continue
    if r.get("skip"):
        print(f"{r['file']:<42} {r['name']:<28}  --- EMPTY ---")
        continue
    print(f"{r['file']:<42} {r['name']:<28} {r['nodes_total']:>5} {r['areas']:>4} {r['ways']:>4} {r['characters']:>4} {r['items']:>4} {r['logic_triggers']:>4} {r['total_edges']:>5} {r['player_count']:>3} {r['time_per_tick_min']:>4}")

print("\n")
print("=" * 130)
print("DETAILED SCENARIO SUMMARIES")
print("=" * 130)

for r in results:
    if isinstance(r, str) or r.get("skip"):
        continue
    print(f"\n{'='*100}")
    print(f"  FILE:    {r['file']}")
    print(f"  NAME:    {r['name']}")
    print(f"  THEME:   {r['lore_summary']}")
    print(f"  CLOCK:   {r['clock_start']}  tick={r['time_per_tick_min']}min  mature={r['mature']}")
    print(f"  FORECAST:{r['forecast']}")
    print(f"  NODES:   {r['nodes_total']} total  areas={r['areas']} ways={r['ways']} chars={r['characters']} items={r['items']} triggers={r['logic_triggers']}")
    print(f"  EDGES:   {r['total_edges']} total  types={r['edge_types']}")
    print(f"  PLAYERS: {r['player_count']} -> {r['player_keys']}")
    print(f"  P DETAIL:{r['player_details']}")
    print(f"  CHARS:   {r['char_names']}")
    print(f"  TRIG_T:  {r['trigger_types']}")
    if r['food_items']:
        print(f"  FOOD:    {r['food_items']}")
    if r['weapon_items']:
        print(f"  WEAPONS: {r['weapon_items']}")
    if r['container_items']:
        print(f"  CONTAIN: {r['container_items']}")
