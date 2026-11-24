"""Character internal state prompt builder (task-1002).

Reads directly from ``Player`` (vitals, ``emotions_description()``,
``somatic_description()``, equipped/carried items, turn slots) so the LLM
experiences felt state in first person without raw numbers.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _vital_lines(player: Any) -> List[str]:
    vitals = getattr(player, "vitals", None) or {}
    lines: List[str] = []
    # Hunger and Thirst are drives (0 = satisfied, 100 = critical).
    # HP and Energy are reserves (100 = full, 0 = critical).
    hunger = float(vitals.get("Hunger", 0) or 0)
    thirst = float(vitals.get("Thirst", 0) or 0)
    energy = float(vitals.get("Energy", 100) or 100)
    hp = float(vitals.get("HP", 100) or 100)
    if hp <= 30:
        lines.append("You are badly hurt.")
    elif hp <= 60:
        lines.append("You are bruised and aching.")
    if hunger >= 75:
        lines.append("You are very hungry and your energy is flagging.")
    elif hunger >= 50:
        lines.append("You are getting hungry.")
    if thirst >= 75:
        lines.append("You are very thirsty and it is draining you.")
    elif thirst >= 50:
        lines.append("You are thirsty.")
    if energy <= 25:
        lines.append("You are exhausted.")
    return lines


def build_character_state(
    player: Any,
    *,
    world: Any = None,
    action_points: Optional[Dict[str, int]] = None,
) -> str:
    """Render === YOUR STATE === directly from the authoritative Python Player."""
    lines: List[str] = []
    lines.extend(_vital_lines(player))

    emo_desc = player.emotions_description() if hasattr(player, "emotions_description") else ""
    if emo_desc:
        lines.append(f"Mood: {emo_desc}")

    somatic = player.somatic_description() if hasattr(player, "somatic_description") else ""
    if somatic:
        lines.append(f"Body: {somatic}")

    conds = list((getattr(player, "conditions", None) or {}).keys())
    if conds:
        lines.append("Conditions: " + ", ".join(conds))

    ap = action_points if action_points is not None else action_points
    if ap:
        parts = [f"{k} {v}" for k, v in ap.items() if k in ("major", "minor", "free")]
        if parts:
            lines.append("=== ACTION POINTS LEFT THIS TURN ===\n" + " · ".join(parts))

    if not lines:
        lines.append("You feel steady and alert.")

    # Wearing & Carrying (authoritative from Player, gated by available action_points)
    major_ap = int((ap or {}).get("major", 1))
    minor_ap = int((ap or {}).get("minor", 1))
    worn_acts: List[str] = []
    if major_ap > 0:
        worn_acts.append("use")
    if minor_ap > 0:
        worn_acts.extend(["remove", "drop"])
    worn_tag = f" [{', '.join(worn_acts)}]" if worn_acts else ""

    pname_prefix = f"{str(getattr(player, 'name', '') or '').lower()}_"

    def _clean_item_label(raw: Any) -> str:
        label = str(raw.get("name") if isinstance(raw, dict) else raw)
        if label.startswith("item_"):
            label = label[5:]
        elif label.startswith("inv_"):
            label = label[4:]
        if pname_prefix and label.lower().startswith(pname_prefix):
            label = label[len(pname_prefix):]
        parts = label.split("_")
        if len(parts) >= 3 and parts[-1].isdigit() and parts[-2].isdigit():
            label = "_".join(parts[:-2])
        return label

    equipped = getattr(player, "equipped", None) or {}
    if isinstance(equipped, dict) and equipped:
        worn: List[str] = []
        for slot, raw_items in equipped.items():
            items = raw_items if isinstance(raw_items, list) else ([raw_items] if raw_items else [])
            for item in items:
                worn.append(f"{_clean_item_label(item)} ({slot}){worn_tag}")
        if worn:
            lines.append("Wearing: " + ", ".join(worn))

    inv: List[Any] = []
    if world is not None:
        graph = getattr(world, "graph", None)
        if graph is not None:
            pname_us = str(player.name).replace(" ", "_")
            pid_candidates = {
                str(getattr(player, "id", "") or "").lower(),
                f"player_{player.name}".lower(),
                f"player_{pname_us}".lower(),
                str(player.name).lower(),
            }
            pid_candidates.discard("")
            nodes_map = getattr(graph, "nodes", None) or {}
            get_node = graph.get_node if hasattr(graph, "get_node") else nodes_map.get
            seen_inv = set()
            for edge in list(getattr(graph, "edges", None) or []):
                if getattr(edge, "type", None) != "carrying":
                    continue
                src = str(getattr(edge, "source", "") or "")
                tgt = str(getattr(edge, "target", "") or "")
                item_id = None
                if tgt.lower() in pid_candidates and src:
                    item_id = src
                elif src.lower() in pid_candidates and tgt:
                    item_id = tgt
                if not item_id or item_id in seen_inv:
                    continue
                seen_inv.add(item_id)
                node = get_node(item_id)
                if node is not None:
                    inv.append({"name": getattr(node, "name", item_id), "tags": list((getattr(node, "properties", None) or {}).get("tags") or [])})
                else:
                    inv.append(item_id)
    if inv:
        carried: List[str] = []
        for x in inv:
            if not x:
                continue
            label = _clean_item_label(x)
            low = label.lower()
            tags = set(str(t).lower() for t in (x.get("tags", []) if isinstance(x, dict) else []))
            acts: List[str] = []
            if major_ap > 0:
                if "edible" in tags or "food" in tags or any(k in low for k in ("bar", "bread", "food", "meat", "apple", "ration", "snack")):
                    acts.append("eat")
                if "drinkable" in tags or "drink" in tags or any(k in low for k in ("water", "bottle", "tea", "wine", "potion", "drink", "monster")):
                    acts.append("drink")
                if "usable" in tags or any(k in low for k in ("emf", "lighter", "flashlight", "compass", "key", "phone", "opener")):
                    acts.append("use")
                acts.append("examine")
            if minor_ap > 0:
                if "wearable" in tags or "clothing" in tags:
                    acts.append("wear")
                acts.append("drop")
            tag_str = f" [{', '.join(acts)}]" if acts else ""
            carried.append(f"{label}{tag_str}")
        if carried:
            lines.append("Carrying: " + ", ".join(carried))

    return "=== YOUR STATE ===\n" + "\n".join(lines)
