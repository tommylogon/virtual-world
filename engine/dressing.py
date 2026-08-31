"""Auto-dressing from interest tags (task-325).

Given a character's ``interest_tags``, scan the item library for wearable
pieces (non-empty ``equip_slots``, not intrinsic abilities) whose tags
intersect those interests, then equip them through the normal equipment
stacking rules — innermost→outermost, slot depth respected, one instance
per name. Weather-aware: in a hot area, heavy-insulation pieces are skipped;
in a cold area, insulated pieces are preferred.

Idempotent by construction: ``equip_item`` refuses already-worn names and
full slots, so re-running dresses only what's missing. Seeds are optional
for reproducible runs.
"""

import json
import os
import random

from graph import Edge, EDGE_CARRYING, EDGE_IN

_INTRINSIC = {"spell", "ability", "innate", "intrinsic", "power"}


def _library_items():
    lib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'library', 'items')
    if not os.path.isdir(lib_dir):
        return []
    out = []
    for fname in os.listdir(lib_dir):
        if not fname.endswith('.json'):
            continue
        path = os.path.join(lib_dir, fname)
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        out.append((fname[:-5], data))
    return out


def _player_area_env(gs, player):
    try:
        area_id = gs._get_current_area_id()
        node = gs.graph.get_node(area_id) if area_id else None
        env = (node.properties or {}).get("environment", {}) if node else {}
        return float(env.get("temperature", 21) or 21)
    except Exception:
        return 21.0


def auto_dress(gs, player_name=None, seed=None) -> str:
    """Dress a character from their interest tags. Returns a report."""
    pm = gs.player_manager
    name = player_name or pm.active_player
    player = pm.players.get(name)
    if not player:
        raise ValueError(f"No character '{name}'.")

    interest = {str(t).lower().strip() for t in (player.interest_tags or [])}
    temp = _player_area_env(gs, player)
    hot = temp >= 30
    cold = temp <= 5

    candidates = []
    for lib_id, data in _library_items():
        slots = data.get("equip_slots", [])
        if isinstance(slots, str):
            slots = [s.strip() for s in slots.split(",")]
        if not slots:
            continue
        tags = {str(t).lower().strip() for t in (data.get("tags", []) or [])}
        if tags & _INTRINSIC:
            continue
        if interest:
            if not (tags & interest):
                continue
        else:
            # No interests set: dress basic essentials only.
            if not (tags & {"clothing", "armor", "wear", "wearable"}):
                continue
        insulation = int(data.get("insulation", 0) or 0)
        if hot and insulation >= 15:
            continue
        if cold and insulation <= 0:
            continue
        candidates.append({
            "lib_id": lib_id,
            "name": data.get("name", lib_id),
            "slots": slots,
            "tags": sorted(tags),
            "insulation": insulation,
        })

    rng = random.Random(seed)
    rng.shuffle(candidates)

    player_id = pm.get_player_node_id(name)
    dressed = []
    skipped = []
    for cand in candidates:
        try:
            node, _lib = gs.effects._hydrate_item(cand["lib_id"], {}, always_fresh=True)
            if node is None:
                skipped.append((cand["name"], "no library data"))
                continue
            gs.graph.add_edge(Edge(source=node.id, target=player_id, type=EDGE_CARRYING))
            msg = gs.equipment.equip_item(cand["name"], slot=cand["slots"][0])
            dressed.append(cand["name"])
        except Exception as e:
            # Undress the failed candidate: back to carrying, then into the room.
            try:
                for edge in list(gs.graph.edges):
                    if edge.source == node.id and edge.type in (EDGE_CARRYING,):
                        gs.graph.edges.remove(edge)
                area_id = gs._get_current_area_id()
                if area_id:
                    gs.graph.add_edge(Edge(source=node.id, target=area_id, type=EDGE_IN))
            except Exception:
                pass
            skipped.append((cand["name"], str(e)[:60]))

    lines = [f"Auto-dress for {name}: {len(dressed)} item(s) equipped."]
    for n in dressed:
        lines.append(f"- {n}")
    return "\n".join(lines)
