"""Scene snapshot for the human turn panel (task-333 Phase 1).

One call assembles everything the panel's scene view renders:

- the current area (+ light level so the client can degrade in darkness)
- characters present, stranger-masked until met (unknown_display_name)
- visible items with their data-driven ``available actions``
  (TriggerSystem._get_available_actions contract: {action,label,enabled,reason})
- ways out reporting ONLY discovered state — hidden ways stay out entirely
  (same slasher/discovered_exits rule as look), and lock/block/force
  knowledge comes from Player.known_way_aspects and is never leaked here
- the player's own strip data: vitals, visible conditions, carrying/worn,
  activity, recent memories

Pure read module: no engine state is mutated here.
"""

from typing import Any, Dict, List

from graph import (
    EDGE_CARRYING,
    EDGE_CONNECTION,
    EDGE_EQUIPPED,
)
from engine.room_perception import (
    characters_in_area,
    normalize_requires,
    resolve_area_node,
    visible_area_items,
    way_visible_to,
)


def _first_sentence(text: str, fallback: str = "") -> str:
    text = str(text or "").strip()
    if not text:
        return fallback
    for sep in (". ", ".\n", "! ", "? "):
        idx = text.find(sep)
        if 0 < idx < 220:
            return text[: idx + 1]
    return text[:220]


def _identity_tags(tags: List[str]) -> List[str]:
    """The subset of tags the panel renders as stranger labels/icons."""
    keep = {"male", "female", "man", "woman", "girl", "boy", "child", "animal"}
    return [t for t in tags if str(t).lower() in keep]


def _known_aspects(player: Any, area_name: str, handle: str) -> Dict[str, bool]:
    return {
        aspect: player.knows_way_aspect(area_name, handle, aspect)
        for aspect in ("locked", "blocked", "needs_force")
    }


def _area_node_id(world: Any, area_name: str) -> str:
    """Resolve the area's graph node id via the shared perception rule
    (engine/room_perception.py — name-based, bug-26), falling back to the
    canonical constructed string so callers always get a usable key."""
    graph = getattr(world, "graph", None)
    node = resolve_area_node(graph, area_name)
    if node is not None:
        return node.id
    return f"area_{str(area_name).lower().replace(' ', '_')}"


def build_scene(world: Any, player_name: str) -> Dict[str, Any]:
    """Build the panel scene payload for *player_name*'s current area."""
    player_manager = world.player_manager
    player = player_manager.players.get(player_name)
    if player is None:
        raise ValueError(f"Unknown character '{player_name}'.")
    area_name = player.current_area
    if not area_name:
        raise ValueError(f"'{player_name}' is nowhere.")

    graph = world.graph
    area_id = _area_node_id(world, area_name)
    area_node = graph.get_node(area_id)

    # ── light ────────────────────────────────────────────────────────
    env = area_node.properties.get("environment", {}) if area_node else {}
    try:
        light_level = int(world.lighting.get_ambient_light(area_id, env))
    except Exception:
        light_level = 100

    scene: Dict[str, Any] = {
        "area": {
            "id": area_id,
            "name": area_name,
            "display_name": (area_node.properties.get("display_name") if area_node else None)
            or area_name,
            "desc": _first_sentence(
                getattr(world.area_description, "_render_node", lambda n: "")(area_node)
                if area_node else "",
                "",
            ),
            "light_level": light_level,
            "dark": light_level < 40,
        },
        "people": [],
        "items": [],
        "ways": [],
        "you": {},
    }

    # ── people ───────────────────────────────────────────────────────
    # Mirrors area_description's recognition contract (task-154 + task-339):
    # seeing someone registers the relationship (stable masked label) but
    # NEVER reveals the name — names are learned only by hearing them
    # spoken or by reading a name tag. `first_sighting` means "name unknown".
    for node in characters_in_area(graph, area_id, exclude_name=player_name):
        name = node.name
        p_obj = player_manager.players.get(name)
        met = player.has_met(name)
        name_known = player.knows_name(name) if hasattr(player, "knows_name") else met
        desc = str(node.properties.get("description", "") or "")
        p_desc = getattr(p_obj, "description", None) if p_obj is not None else None
        if isinstance(p_desc, str) and p_desc.strip():
            desc = p_desc
        display = name
        if not name_known:
            label = None
            if p_obj is not None:
                try:
                    candidate = p_obj.unknown_display_name()
                    if isinstance(candidate, str) and candidate.strip():
                        label = candidate
                except Exception:
                    label = None
            display = label or _first_sentence(desc) or "the stranger"
        entry = {
            "id": node.id,
            "name": name if name_known else None,
            "display_name": display,
            "met": met,
            "desc": _first_sentence(desc),
            "tags": _identity_tags(list(node.properties.get("tags", []) or [])),
        }
        scene["people"].append(entry)
        if hasattr(player, "register_first_meeting"):
            player.register_first_meeting(
                name, getattr(player_manager, "time_ticks", 0) or 0
            )

    # ── items (hidden ones stay out) ─────────────────────────────────
    for node in visible_area_items(graph, area_id):
        render = getattr(world.area_description, "_render_node", None)
        desc = ""
        if callable(render):
            try:
                candidate = render(node)
                desc = str(candidate) if isinstance(candidate, str) else ""
            except Exception:
                desc = ""
        try:
            available = world._get_available_actions(node)
        except Exception:
            available = []
        scene["items"].append({
            "id": node.id,
            "name": node.name,
            "state": node.properties.get("current_state", ""),
            "desc": _first_sentence(desc),
            "available_actions": available,
        })

    # ── ways out (discovered state only) ────────────────────────────
    seen_way_ids = set()
    for edge in graph.get_edges_for_source(area_id, EDGE_CONNECTION):
        way_node = graph.get_node(edge.target)
        if not way_node or way_node.id in seen_way_ids:
            continue
        seen_way_ids.add(way_node.id)

        # Hidden ways stay out until discovered — shared perception rule
        # (engine/room_perception.py, same rule the agent path uses).
        if not way_visible_to(player, player_manager, player_name,
                              way_node, area_name,
                              edge.properties.get("direction", "")):
            continue

        raw_direction = edge.properties.get("direction", "") or way_node.name
        try:
            handle = world.name_matcher.way_handle(
                way_node, raw_direction, area_name
            ) or raw_direction
        except Exception:
            handle = raw_direction

        target_area_id = None
        for conn in graph.get_edges_for_source(way_node.id, EDGE_CONNECTION):
            if conn.target != area_id:
                target_area_id = conn.target
                break
        target_node = graph.get_node(target_area_id) if target_area_id else None
        target_display = (
            (target_node.properties.get("display_name") if target_node else None)
            or (target_node.name if target_node else "")
        )

        real_state = way_node.properties.get("current_state", "closed")
        known = _known_aspects(player, area_name, handle)
        needs_open = way_node.properties.get("needs_open", {}) or {}
        render = getattr(world.area_description, "_render_node", None)
        try:
            way_desc_raw = render(way_node) if callable(render) else ""
            way_desc = str(way_desc_raw) if isinstance(way_desc_raw, str) else ""
        except Exception:
            way_desc = ""

        # Legacy "none" normalizes to "" via the shared perception rule —
        # a truthy "requires none" used to disable Go and hide Open.
        requires = normalize_requires(way_node.properties.get("requires", ""))

        reported_state = real_state
        if real_state in ("locked", "blocked") and not known[real_state]:
            reported_state = "closed"  # reads as closed at a glance
        if real_state == "closed" and known["needs_force"]:
            pass  # still just closed until opened; force hint is client-side

        entry = {
            "id": way_node.id,
            "direction": handle,
            "name": way_node.name,
            "to": target_display,
            "state": reported_state,
            "desc": _first_sentence(way_desc),
            "see_through": bool(way_node.properties.get("see_through")),
            "visible_in_direction": edge.properties.get("visible_in_direction", "") or "",
            "requires": requires,
            "auto_close": bool(way_node.properties.get("auto_close")),
            "known_locked": known["locked"],
            "known_blocked": known["blocked"],
            "needs_force_known": known["needs_force"],
        }
        if known["needs_force"] and needs_open.get("enabled"):
            entry["force_skill"] = needs_open.get("skill", "Athletics")
            entry["force_dc"] = int(needs_open.get("dc", 10))
        scene["ways"].append(entry)

    # ── you ─────────────────────────────────────────────────────────
    player_node = _player_node_id(world, player_name)

    def _inv_entry(node: Any) -> Dict[str, Any]:
        actions = node.properties.get("actions", [])
        if isinstance(actions, str):
            actions = [a.strip() for a in actions.split(",") if a.strip()]
        render = getattr(world.area_description, "_render_node", None)
        desc = ""
        if callable(render):
            try:
                candidate = render(node)
                desc = str(candidate) if isinstance(candidate, str) else ""
            except Exception:
                desc = ""
        return {
            "id": node.id,
            "name": node.name,
            "actions": actions,
            "desc": _first_sentence(desc),
        }

    carrying = []
    for edge in graph.get_edges_for_target(player_node, EDGE_CARRYING):
        node = graph.get_node(edge.source)
        if node:
            entry = _inv_entry(node)
            entry["id"] = node.id
            entry["name"] = node.name
            carrying.append(entry)
    # Worn = graph EDGE_EQUIPPED edges (player.equipped is a derived cache
    # that desyncs; equipment.py rebuilds it from these same edges).
    worn = []
    for edge in graph.get_edges_for_target(player_node, EDGE_EQUIPPED):
        node = graph.get_node(edge.source)
        if node and not node.name.startswith("__"):
            entry = _inv_entry(node)
            entry["id"] = node.id
            entry["name"] = node.name
            entry["slot"] = edge.properties.get("slot", "")
            worn.append(entry)
    worn.sort(key=lambda w: w["slot"])
    conditions = []
    for cond_id, instances in (getattr(player, "conditions", {}) or {}).items():
        visible_instances = [
            i for i in instances
            if isinstance(i, dict) and i.get("known", True)
        ]
        if visible_instances and cond_id != "awake":
            conditions.append(cond_id)
    memories = [
        m.get("text", "") for m in reversed(getattr(player, "memories", []) or [])
        if isinstance(m, dict)
    ][:5]

    scene["you"] = {
        "name": player_name,
        "vitals": dict(getattr(player, "vitals", {}) or {}),
        "conditions": conditions,
        "carrying": carrying,
        "wearing": worn,
        "activity": getattr(player, "activity", None),
        "recent_memories": memories,
    }
    return scene


def _player_node_id(world: Any, player_name: str) -> str:
    getter = getattr(world.player_manager, "_player_node_id", None)
    if callable(getter):
        try:
            result = getter(player_name)
            if isinstance(result, str):
                return result
        except Exception:
            pass
    getter = getattr(world, "_player_node_id", None)
    if callable(getter):
        try:
            result = getter(player_name)
            if isinstance(result, str):
                return result
        except Exception:
            pass
    return f"player_{player_name}".replace(" ", "_")
