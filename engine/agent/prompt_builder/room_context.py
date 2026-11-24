"""Room, people, exits, and witnessed-speech prompt builder (task-1002).

Reads directly from ``VirtualWorld`` / ``Graph`` / ``Player`` - no duplicate
TypeScript language masking or stale partial-snapshot edges.
"""
from __future__ import annotations

from typing import Any, List


def _relationship_label(player: Any, other_name: str) -> str:
    try:
        from engine.relationships import get_relationship
        rel = get_relationship(player, other_name)
        if not rel:
            return ""
        c = float(rel.get("closeness", 0) or 0)
        if c <= -75:
            return "a mortal enemy"
        if c <= -50:
            return "an enemy"
        if c <= -25:
            return "a rival"
        if c < 0:
            return "unfriendly"
        if c == 0:
            return ""
        if c <= 25:
            return "an acquaintance"
        if c <= 50:
            return "a friend"
        if c <= 75:
            return "a close friend"
        return "inseparable"
    except Exception:
        return ""


def build_room_context(
    world: Any,
    player: Any,
    *,
    action_points: Any = None,
    include_witnessed: bool = False,
) -> str:
    """Build the area, exits (AP-gated), items (AP-gated), and people (with 1st-line desc + tells)."""
    area_name = getattr(player, "current_area", None) or "unknown"
    blocks: List[str] = [f"You are currently in {area_name}."]
    major_ap = int((action_points or {}).get("major", 1)) if isinstance(action_points, dict) else 1
    way_tag = " [go, approach, examine]" if major_ap > 0 else ""

    # Area description, exits, and items from graph node if available
    graph = getattr(world, "graph", None)
    if graph is not None:
        try:
            aid = None
            anode = None
            try:
                from engine.room_perception import resolve_area_node
                anode = resolve_area_node(graph, area_name)
                if anode is not None:
                    aid = getattr(anode, "id", None)
            except Exception:
                anode = None
            if anode is None and hasattr(graph, "nodes"):
                alow = str(area_name).lower()
                alow_us = alow.replace(" ", "_")
                for nid, n in graph.nodes.items():
                    if getattr(n, "type", None) == "area" and (
                        str(getattr(n, "name", "") or "").lower() == alow
                        or str(nid).lower() in (alow, f"area_{alow}", f"area_{alow_us}")
                    ):
                        aid = nid
                        anode = n
                        break
            if anode is not None:
                desc = getattr(anode, "description", None) or (anode.properties or {}).get("description") or ""
                if desc:
                    blocks.append(str(desc).strip())
            if aid:
                exit_lines: List[str] = []
                item_lines: List[str] = []
                all_edges = list(getattr(graph, "edges", None) or [])
                nodes_map = getattr(graph, "nodes", None) or {}
                get_node = graph.get_node if hasattr(graph, "get_node") else nodes_map.get
                seen_exits = set()
                seen_items = set()
                from engine.entity_existence import entity_exists_at, world_current_datetime
                cur_dt = world_current_datetime(world)
                for edge in all_edges:
                    src = getattr(edge, "source", None)
                    tgt = getattr(edge, "target", None)
                    other_id = tgt if src == aid else (src if tgt == aid else None)
                    if not other_id:
                        continue
                    onode = get_node(other_id)
                    if onode is None:
                        continue
                    if cur_dt and not entity_exists_at(onode, cur_dt):
                        continue
                    otype = getattr(onode, "type", None)
                    if otype == "way" and onode.name not in seen_exits:
                        seen_exits.add(onode.name)
                        exit_lines.append(f"  - {onode.name}{way_tag}")
                    elif otype == "item" and onode.name not in seen_items:
                        seen_items.add(onode.name)
                        idesc = str(getattr(onode, "description", None) or (onode.properties or {}).get("description") or "").strip()
                        item_tag = " [take, examine]" if major_ap > 0 else ""
                        item_lines.append(f"  - {onode.name}{item_tag}: {idesc}" if idesc else f"  - {onode.name}{item_tag}")
                if exit_lines:
                    blocks.append("Paths from here:\n" + "\n".join(exit_lines))
                if item_lines:
                    blocks.append("Items that catch your attention:\n" + "\n".join(item_lines[:20]))
        except Exception:
            pass

    # People in the same area (with first line of description + observable tells!)
    people_lines: List[str] = []
    players = getattr(world, "players", None) or {}
    listener_wis = int((getattr(player, "stats", None) or {}).get("WIS", 10) or 10)
    from engine.entity_existence import player_exists_now
    for other_name, other in players.items():
        if other_name == player.name:
            continue
        if getattr(other, "current_area", None) != area_name:
            continue
        if not player_exists_now(world, other_name, other):
            continue
        rel_lbl = _relationship_label(player, other_name)
        rel_part = f" - {rel_lbl}" if rel_lbl else ""
        state_str = getattr(other, "state", "awake") or "awake"
        raw_desc = str(getattr(other, "appearance", None) or getattr(other, "description", None) or "").strip()
        first_line = raw_desc.splitlines()[0].strip() if raw_desc else ""
        if ". " in first_line:
            first_line = first_line.split(". ", 1)[0].strip() + "."
        desc_part = f" - {first_line}" if first_line else ""
        tells = (
            other.observer_tells(light_level="normal", observer_insight=listener_wis)
            if hasattr(other, "observer_tells")
            else ""
        )
        tells_part = f" [{tells}]" if tells else ""
        people_lines.append(f"  - {other_name}{rel_part} ({state_str}){desc_part}{tells_part}")

    if people_lines:
        blocks.append("People here:\n" + "\n".join(people_lines))
    else:
        blocks.append("People here: (no one else)")

    if include_witnessed:
        blocks.append(build_room_events_block(world, player))

    return "\n\n".join(blocks)


def build_room_events_block(world: Any, player: Any, *, last_result: str = "") -> str:
    """Build === WHAT HAPPENED === combining room events, witnessed speech, and own last result."""
    lines: List[str] = []
    cur_tick = int(getattr(world, "time_ticks", 0) or 0) if world is not None else None

    # Heard speech (already masked & tone-perceived by engine/speech.py, time-locked to cur_tick)
    raw_hearing = list(getattr(player, "recent_hearing", None) or [])
    if cur_tick is not None:
        raw_hearing = [
            h for h in raw_hearing
            if not isinstance(h, dict) or h.get("tick") is None or int(h["tick"]) <= cur_tick
        ]
    hearing = raw_hearing[-6:]
    player_low = str(getattr(player, "name", "") or "").lower()
    for h in hearing:
        spk = h.get("speaker") or "Someone"
        txt = h.get("text") or ""
        adverb = h.get("tone_adverb") or ""
        adv_str = f" {adverb}" if adverb else ""
        vol = h.get("speech_level") or "normal"
        verb = "whispered" if vol == "whisper" else ("shouted" if vol == "shout" else "said")
        if str(spk).lower() == player_low:
            line = f'  - [You {verb}{adv_str}]: "{txt}"'
        else:
            line = f'  - [Heard] {spk} {verb}{adv_str}: "{txt}"'
        if line not in lines:
            lines.append(line)

    # Observed room/area events (speech, entries, exits, actions) from GameLogger.turn_events
    area_name = getattr(player, "current_area", None) or ""
    turn_events = []
    if area_name and hasattr(world, "get_turn_events_for_area"):
        try:
            turn_events = list(world.get_turn_events_for_area(area_name) or [])[-8:]
        except Exception:
            turn_events = []
    seen_texts = set(lines)
    for ev in turn_events:
        if isinstance(ev, dict):
            if cur_tick is not None and ev.get("tick") is not None:
                try:
                    if int(ev["tick"]) > cur_tick:
                        continue
                except (TypeError, ValueError):
                    pass
            txt = str(ev.get("text") or ev.get("summary") or ev.get("result") or "").strip()
            actor = str(ev.get("actor") or "").strip()
            if not txt:
                continue
            if actor and actor == player.name and not txt.lower().startswith(("you ", actor.lower())):
                line = f"  - [You] {txt}"
            else:
                line = f"  - {txt}"
        else:
            txt = str(ev).strip()
            if not txt:
                continue
            line = f"  - {txt}"
        if line not in seen_texts:
            seen_texts.add(line)
            lines.append(line)

    if last_result and last_result.strip():
        lines.append(f"  - [Your last action] {last_result.strip()}")

    if not lines:
        return "=== WHAT HAPPENED ===\nThe room is quiet for the moment."
    return "=== WHAT HAPPENED ===\n" + "\n".join(lines)
