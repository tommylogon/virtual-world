#!/usr/bin/env python3
"""generate_scenario.py — assemble a scenario from library area pieces.

First-pass procedural generator. Treats each file in ``data/library/areas/`` as a
self-contained piece (description + environment + tags + embedded item copies +
exit hints) and assembles a connected, deterministic scenario from a pool.

Pipeline:
  1. select  — filter pieces by tag, walk exits from a root to build a connected
               group, optionally seed-fill to a target size
  2. emit    — area nodes, item copies (with ``in`` edges), ways derived from
               exit hints, and a minimal runtime/player block
  3. validate— reuse tools/validate_scenario.py and report

Determinism: same --seed + same library + same flags => byte-identical output.

Usage:
    python tools/generate_scenario.py \
        --tags goblin_camp --name kraktooth_generated --seed 7 \
        --max-areas 30 --output data/scenarios/kraktooth_generated.json
"""

import argparse
import json
import random
import re
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from validate_scenario import validate_scenario  # noqa: E402

DEFAULT_LIBRARY = TOOLS_DIR.parent / "data" / "library"
DEFAULT_PLAYER = "player_explorer"

if str(TOOLS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR.parent))

from engine.population import LibraryIndex, apply_population, plan_population  # noqa: E402


def slug(value: str) -> str:
    safe = "".join(c if c.isalnum() else "_" for c in str(value).lower())
    return "_".join(p for p in safe.split("_") if p)


def norm_name(value) -> str:
    return (str(value or "").lower()
            .replace("_", " ").replace("-", " ").replace("'", "").strip())


def load_area_pieces(library_dir: Path):
    """Return {area_id: piece} for every area library file."""
    pieces = {}
    area_dir = library_dir / "areas"
    if not area_dir.is_dir():
        raise SystemExit(f"Area library not found: {area_dir}")
    for path in sorted(area_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            print(f"  skip {path.name}: {exc}", file=sys.stderr)
            continue
        data.setdefault("name", path.stem.replace("_", " ").title())
        pieces[path.stem] = data
    return pieces


def matches_tags(piece, tags):
    if not tags:
        return True
    have = {str(t).lower() for t in (piece.get("tags") or [])}
    return bool(have & tags)


def resolve_target(hint, pieces, by_norm):
    """Map an exit target_room_hint to an area id in the pool."""
    if not hint:
        return None
    key = norm_name(hint)
    if key in by_norm:
        return by_norm[key]
    return None


def select_areas(pieces, tags, max_areas, seed, root=None, connected=True):
    """Pick a deterministic, optionally connected group of area ids."""
    pool = {aid: p for aid, p in pieces.items() if matches_tags(p, tags)}
    if not pool:
        raise SystemExit(f"No areas match tags: {sorted(tags)}")

    by_norm = {}
    for aid, p in pool.items():
        by_norm.setdefault(norm_name(p.get("name")), aid)
        by_norm.setdefault(norm_name(aid), aid)

    rng = random.Random(seed)
    ids = sorted(pool)

    # Root: explicit, else the most-connected piece (exit hints resolving in-pool).
    def connectivity(aid):
        return sum(1 for ex in (pool[aid].get("exits") or [])
                   if resolve_target(ex.get("target_room_hint"), pool, by_norm))

    if root:
        root_id = resolve_target(root, pool, by_norm) or (root if root in pool else None)
        if not root_id:
            raise SystemExit(f"Root '{root}' not found in pool")
    else:
        root_id = max(ids, key=lambda a: (connectivity(a), len(pool[a].get("items") or []), a))

    chosen = [root_id]
    seen = {root_id}
    if connected:
        # BFS over exit hints so the group is contiguous, then seed-fill.
        frontier = [root_id]
        while frontier and len(chosen) < max_areas:
            nxt = []
            for aid in frontier:
                for ex in (pool[aid].get("exits") or []):
                    tgt = resolve_target(ex.get("target_room_hint"), pool, by_norm)
                    if tgt and tgt not in seen:
                        seen.add(tgt)
                        chosen.append(tgt)
                        nxt.append(tgt)
                        if len(chosen) >= max_areas:
                            break
                if len(chosen) >= max_areas:
                    break
            frontier = nxt

    # Seed-fill if the connected group is smaller than requested.
    remaining = [a for a in ids if a not in seen]
    rng.shuffle(remaining)
    for aid in remaining:
        if len(chosen) >= max_areas:
            break
        chosen.append(aid)
        seen.add(aid)

    return chosen, pool, by_norm


def item_props(entry):
    tags = entry.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    props = {
        "description": entry.get("description", ""),
        "actions": entry.get("actions", ["examine", "take", "drop"]),
        "uses": int(entry.get("uses", -1)),
        "weight": float(entry.get("weight", 1)),
        "tags": tags,
        "current_state": "hidden" if entry.get("hidden") else entry.get("current_state", "normal"),
        "hidden": bool(entry.get("hidden", False)),
    }
    for key in ("light_level", "equip_slots", "damage", "damage_dice", "damage_type",
                "defense", "insulation", "heating_rate", "target_temperature",
                "stun_chance", "stun_duration", "action_costs", "skill_check"):
        if entry.get(key) is not None:
            props[key] = entry[key]
    ltags = [str(t).lower() for t in tags]
    if "weapon" in ltags:
        props.setdefault("damage_dice", "1d4")
        props.setdefault("damage_type", "slashing")
        props.setdefault("equip_slots", ["hand_right", "hand_left"])
    if "armor" in ltags:
        props.setdefault("equip_slots", ["torso"])
    if "light_source" in ltags or "light" in ltags:
        props.setdefault("light_level", "dim")
    if "container" in ltags:
        props.setdefault("max_weight_capacity", 10)
    return props


def emit_item(nodes, edges, area_node_id, entry, prefix, used_ids, parent=None):
    """Emit one item copy (and its contents) into the graph."""
    name = entry.get("name") or "Item"
    base = f"item_{prefix}_{slug(name)}"
    node_id = base
    i = 2
    while node_id in used_ids:
        node_id = f"{base}_{i}"
        i += 1
    used_ids.add(node_id)
    props = item_props(entry)
    props["library_name"] = name
    nodes[node_id] = {"id": node_id, "type": "item", "name": name, "properties": props}
    target = parent or area_node_id
    edges.append({"source": node_id, "target": target, "type": "in", "properties": {}})
    for child in (entry.get("contents") or []):
        if isinstance(child, dict):
            emit_item(nodes, edges, area_node_id, child, prefix, used_ids, parent=node_id)
    return node_id


def emit_way(nodes, edges, a_id, b_id, a_name, b_name, exit_hint, used_ids):
    base = f"way_{slug(a_id)}_to_{slug(b_id)}"
    node_id = base
    i = 2
    while node_id in used_ids:
        node_id = f"{base}_{i}"
        i += 1
    used_ids.add(node_id)
    direction = (exit_hint or {}).get("direction") or "passage"
    desc = (exit_hint or {}).get("description") or f"A passage between {a_name} and {b_name}."
    props = {
        "description": desc,
        "pass_message": f"You pass from {a_name} toward {b_name}.",
        "area_from": a_id,
        "area_to": b_id,
        "current_state": (exit_hint or {}).get("state", "open"),
        "hidden": bool((exit_hint or {}).get("hidden", False)),
        "tags": ["passage"],
        "cost": {},
        "direction_a": direction,
    }
    nodes[node_id] = {"id": node_id, "type": "way", "name": f"{a_name} to {b_name}", "properties": props}
    edges.append({"source": a_id, "target": node_id, "type": "connection",
                  "properties": {"direction": direction}})
    edges.append({"source": node_id, "target": b_id, "type": "connection",
                  "properties": {"direction": "enter"}})
    edges.append({"source": b_id, "target": node_id, "type": "connection",
                  "properties": {"direction": "back"}})
    edges.append({"source": node_id, "target": a_id, "type": "connection",
                  "properties": {"direction": "enter"}})
    return node_id


def generate(pieces, chosen, pool, by_norm, tags, seed, include_items, player,
             populate=False, index=None, items_per_area=6, furniture_max=3):
    nodes, edges = {}, []
    used_ids = set()
    id_to_name = {}
    id_to_node = {}
    population_report = []

    for aid in chosen:
        piece = pool[aid]
        name = piece.get("name", aid)
        node_id = f"area_{slug(aid)}"
        id_to_name[aid] = name
        id_to_node[aid] = node_id
        props = {
            "description": piece.get("description", ""),
            "environment": piece.get("environment", {
                "light": "normal", "temperature": 18.0,
                "air": "fresh", "smell": "neutral", "noise": "quiet"}),
            "tags": piece.get("tags", []),
            "floor": 0,
            "central_gravity_enabled": False,
        }
        nodes[node_id] = {"id": node_id, "type": "area", "name": name, "properties": props}
        used_ids.add(node_id)

    if include_items:
        for aid in chosen:
            piece = pool[aid]
            for entry in (piece.get("items") or []):
                if isinstance(entry, dict):
                    emit_item(nodes, edges, id_to_node[aid], entry, slug(aid), used_ids)

    # ── procedural population of the tag chain (task-9) ──────────────
    if populate and index is not None:
        def emit_library_node(library_id, prefix):
            entry = index.entries.get(library_id, {})
            name = entry.get("name") or library_id
            base = f"item_{prefix}_{slug(name)}"
            node_id = base
            i = 2
            while node_id in used_ids:
                node_id = f"{base}_{i}"
                i += 1
            used_ids.add(node_id)
            props = item_props(entry)
            props["library_id"] = library_id
            nodes[node_id] = {"id": node_id, "type": "item", "name": name, "properties": props}
            return node_id

        for aid in chosen:
            piece = pool[aid]
            rng = random.Random(f"{seed}:{aid}")
            plan = plan_population(piece.get("tags") or [], index, rng,
                                   furniture_max=furniture_max,
                                   items_per_area=items_per_area)
            if plan.is_empty:
                population_report.append(
                    (piece.get("name", aid), plan.unresolved_domains or plan.notes))
                continue

            def spawn(library_id, _prefix=slug(aid)):
                return emit_library_node(library_id, _prefix)

            def relate(child, parent, relation):
                edges.append({"source": child, "target": parent,
                              "type": relation, "properties": {}})

            apply_population(plan, spawn, relate, id_to_node[aid])
            population_report.append(
                (piece.get("name", aid), f"{len(plan.furniture)} furniture + {len(plan.items)} items"))

    # Ways from exit hints between selected areas (dedupe unordered pairs).
    made_pairs = set()
    unresolved = []
    for aid in chosen:
        piece = pool[aid]
        for ex in (piece.get("exits") or []):
            tgt = resolve_target(ex.get("target_room_hint"), pool, by_norm)
            if not tgt or tgt not in chosen:
                if ex.get("target_room_hint"):
                    unresolved.append((piece.get("name", aid), ex.get("target_room_hint")))
                continue
            pair = tuple(sorted((aid, tgt)))
            if pair in made_pairs:
                continue
            made_pairs.add(pair)
            emit_way(nodes, edges, id_to_node[aid], id_to_node[tgt],
                     id_to_name[aid], id_to_name[tgt], ex, used_ids)

    root_name = id_to_name[chosen[0]]
    scenario = {
        "name": None,  # filled by caller
        "active_player": player,
        "clock_start_hour": 6,
        "clock_start_minute": 0,
        "current_area": root_name,
        "game_time": "06:00:00",
        "ghost_mode": False,
        "narration_mode": "none",
        "time_per_tick_minutes": 1,
        "time_ticks": 0,
        "turn_number": 0,
        "turn_order": "sequential",
        "world_state": {"season": "summer", "day": 1, "weather": "clear"},
        "population": {},
        "events": [],
        "world_lore": [],
        "item_registry": {},
        "players_in_area": [],
        "players": {
            player: {
                "name": "Explorer",
                "description": "A traveler.",
                "personality": "You are an explorer.",
                "current_area": root_name,
                "autonomy": False,
                "simple_npc": False,
                "stats": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10},
                "skills": {},
                "vitals": {"HP": 100, "Max_HP": 100, "Hunger": 50, "Thirst": 50,
                           "Energy": 80, "Hygiene": 70, "Social": 60, "Bladder": 80,
                           "Sanity": 90, "Entertainment": 50, "Temperature": 37.0},
                "traits": {}, "tags": ["human", "adult"], "conditions": {"awake": [{"duration": None, "source": None, "level": 0}]},
                "equipped": {}, "decay_rates": {}, "emotion": {"current": "neutral", "description": "", "intensity": 0.0},
                "relationships": {}, "memories": [],
            }
        },
        "graph": {"nodes": nodes, "edges": edges},
        "schedules": {},
        "simultaneous_mode": False,
        "turn_interval_ms": 1000,
        "simultaneous_act_limit": 3,
        "knowledge": {},
        "world_events": [],
        "_generation": {
            "generator": "generate_scenario.py",
            "seed": seed,
            "tags": sorted(tags),
            "areas": chosen,
            "created_at": None,
            "population": [{"area": a, "result": r if isinstance(r, str) else list(r)}
                           for a, r in population_report],
        },
    }
    return scenario, unresolved, population_report


def main():
    ap = argparse.ArgumentParser(description="Assemble a scenario from library area pieces.")
    ap.add_argument("--name", required=True, help="Scenario name (output stem)")
    ap.add_argument("--tags", default="", help="Comma-separated tag filter, e.g. goblin_camp")
    ap.add_argument("--root", default="", help="Area id or name to start the connected walk")
    ap.add_argument("--max-areas", type=int, default=12)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--library", default=str(DEFAULT_LIBRARY))
    ap.add_argument("--player", default=DEFAULT_PLAYER)
    ap.add_argument("--no-items", action="store_true", help="Omit item copies")
    ap.add_argument("--disconnected", action="store_true", help="Skip exit-based connectivity")
    ap.add_argument("--populate", action="store_true",
                    help="Run the tag-chain population engine to furnish areas (task-9)")
    ap.add_argument("--furniture-max", type=int, default=3, help="Max furniture pieces per populated area")
    ap.add_argument("--items-per-area", type=int, default=6, help="Target item count per populated area")
    ap.add_argument("--output", default="", help="Output path (default data/scenarios/<name>.json)")
    args = ap.parse_args()

    tags = {t.strip().lower() for t in args.tags.split(",") if t.strip()}
    pieces = load_area_pieces(Path(args.library))
    chosen, pool, by_norm = select_areas(
        pieces, tags, args.max_areas, args.seed,
        root=args.root or None, connected=not args.disconnected)

    index = None
    if args.populate:
        index = LibraryIndex.from_directory(Path(args.library) / "items")
        print(f"Population index: {len(index.entries)} library items, "
              f"{len(index.by_tag)} tags")

    scenario, unresolved, population_report = generate(
        pieces, chosen, pool, by_norm, tags, args.seed,
        include_items=not args.no_items, player=args.player,
        populate=args.populate, index=index,
        items_per_area=args.items_per_area, furniture_max=args.furniture_max)
    scenario["name"] = args.name

    issues = validate_scenario(scenario)
    out = Path(args.output) if args.output else (TOOLS_DIR.parent / "data" / "scenarios" / f"{args.name}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(scenario, indent=2, ensure_ascii=False), encoding="utf-8")

    nodes = scenario["graph"]["nodes"]
    print(f"Seed {args.seed} | tags={sorted(tags) or 'all'} | areas={len(chosen)}")
    print(f"Nodes: {sum(1 for n in nodes.values() if n['type']=='area')} areas, "
          f"{sum(1 for n in nodes.values() if n['type']=='item')} items, "
          f"{sum(1 for n in nodes.values() if n['type']=='way')} ways | "
          f"edges={len(scenario['graph']['edges'])}")
    if unresolved:
        print(f"Unresolved boundary exits: {len(unresolved)} (e.g. {unresolved[:3]})")
    if args.populate and population_report:
        ok = sum(1 for _, r in population_report if isinstance(r, str))
        print(f"Population: furnished {ok}/{len(population_report)} areas")
        for area, r in population_report[:6]:
            print(f"  - {area}: {r}")
    if issues:
        print(f"Validation: {len(issues)} issue(s)")
        for i in issues[:15]:
            print("  -", i)
    else:
        print("Validation passed.")
    print("Wrote:", out)


if __name__ == "__main__":
    main()
