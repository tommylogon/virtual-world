#!/usr/bin/env python3
"""Fix three authoring defects the trigger validator reports:

1. **Ways** — every bidirectional way has only one authored side (cardinal +
   direction + visible_in_direction); the reverse side falls back to the way
   name, which is why exits read backwards ("passage to scouting rooms" from
   *inside* the rooms). This derives the opposite side.
2. **Weapons** — `tag: weapon` needs a `damage` value (combat reads
   `weapon_props["damage"]`, defaulting to a flat 5). Items that carry
   `damage_dice` get `damage` mirrored from it.
3. **Legacy triggers** — authored as `logic_trigger -> owner` with the event on
   the node. The runtime matches `owner -> logic_trigger` with `trigger_type` on
   the edge, so these never fire. This inverts the edge and moves the legacy
   flat fields (`message`, `spawn_items`, `grant_memory`) into `effects[]`.

Dry run by default; pass ``--apply`` to write.

Usage:
    python tools/fix_scenario_authoring.py --input data/scenarios/kraktooth_goblin_camp.json
    python tools/fix_scenario_authoring.py --input data/scenarios/kraktooth_goblin_camp.json --apply
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

OPPOSITE = {
    "north": "south", "south": "north", "east": "west", "west": "east",
    "northeast": "southwest", "southwest": "northeast",
    "northwest": "southeast", "southeast": "northwest",
    "up": "down", "down": "up", "in": "out", "out": "in",
    "upstream": "downstream", "downstream": "upstream",
}

DIRECTIONAL_WORDS = {
    "out": "outward", "up": "upward", "down": "downward",
    "in": "inward", "upstream": "upstream", "downstream": "downstream",
}


def _noun_for(way: dict) -> str:
    name = str(way.get("name", "")).lower()
    for noun in ("trail", "road", "tunnel", "path", "passage"):
        if noun in name:
            return noun
    return "passage"


def _direction_label(opposite: str, way: dict, donor_direction: str) -> str:
    noun = ""
    m = re.search(r"([a-z]+)\s*$", donor_direction.strip().lower())
    if m and m.group(1) in ("passage", "trail", "road", "tunnel", "path"):
        noun = m.group(1)
    noun = noun or _noun_for(way)
    word = DIRECTIONAL_WORDS.get(opposite, opposite)
    return f"{word} {noun}".strip()


def _first_sentence(text: str, limit: int = 130) -> str:
    text = " ".join(str(text or "").split())
    if not text:
        return ""
    cut = text.find(". ")
    snippet = text[: cut + 1] if cut != -1 else text
    return snippet[:limit].strip()


def fix_ways(nodes: dict, edges: list, changes: List[str]) -> None:
    ways = {nid: n for nid, n in nodes.items() if n.get("type") == "way"}
    for way_id, way in ways.items():
        props = way.setdefault("properties", {})
        if not str(props.get("description") or "").strip():
            props["description"] = f"A {_noun_for(way)} through the camp."
            changes.append(f"way {way_id}: added description")
        if not str(props.get("pass_message") or "").strip():
            props["pass_message"] = f"You pass through the {_noun_for(way)}."
            changes.append(f"way {way_id}: added pass_message")

        sides = [e for e in edges
                 if e.get("type") == "connection" and e.get("target") == way_id]
        donor = next(
            (e for e in sides
             if str((e.get("properties") or {}).get("cardinal") or "").strip()),
            None,
        )
        if donor is None:
            # Hand-added way with no authored bearing on either side. Assign a
            # stable default pair (cardinal only seeds map layout) and a view
            # from the far area so the exit still reads sensibly.
            for idx, edge in enumerate(sides):
                eprops = edge.setdefault("properties", {})
                if not str(eprops.get("cardinal") or "").strip():
                    eprops["cardinal"] = ("east", "west")[idx % 2]
                    changes.append(f"way {way_id}: {edge.get('source')} cardinal -> {eprops['cardinal']} (default)")
                if not str(eprops.get("visible_in_direction") or "").strip():
                    other = next((e for e in sides if e is not edge), None)
                    view = _first_sentence(
                        nodes.get(other.get("source"), {}).get("properties", {}).get("description", "")
                    ) if other else ""
                    if view:
                        eprops["visible_in_direction"] = view
                        changes.append(f"way {way_id}: {edge.get('source')} visible_in_direction -> {view[:40]!r}...")
            continue
        donor_props = donor.get("properties") or {}
        donor_cardinal = str(donor_props.get("cardinal")).strip().lower()
        donor_direction = str(donor_props.get("direction") or "")
        opposite = OPPOSITE.get(donor_cardinal)
        if not opposite:
            continue
        for edge in sides:
            if edge is donor:
                continue
            eprops = edge.setdefault("properties", {})
            area_id = edge.get("source")
            if not str(eprops.get("cardinal") or "").strip():
                eprops["cardinal"] = opposite
                changes.append(f"way {way_id}: {area_id} cardinal -> {opposite}")
            if not str(eprops.get("direction") or "").strip():
                eprops["direction"] = _direction_label(opposite, way, donor_direction)
                changes.append(f"way {way_id}: {area_id} direction -> {eprops['direction']!r}")
            if not str(eprops.get("visible_in_direction") or "").strip():
                view = _first_sentence(nodes.get(donor.get("source"), {}).get("properties", {}).get("description", ""))
                if view:
                    eprops["visible_in_direction"] = view
                    changes.append(f"way {way_id}: {area_id} visible_in_direction -> {view[:50]!r}...")


def fix_weapons(nodes: dict, changes: List[str]) -> None:
    for item_id, node in nodes.items():
        if node.get("type") != "item":
            continue
        props = node.setdefault("properties", {})
        tags = [str(t).lower() for t in (props.get("tags") or [])]
        if "weapon" not in tags or props.get("damage"):
            continue
        dice = props.get("damage_dice")
        if not dice:
            continue
        props["damage"] = dice
        changes.append(f"item {item_id}: damage -> {dice!r}")


def _message_effect(text: str) -> dict:
    return {"type": "message", "params": {"message": text, "success_message": text}}


def _has_same_message(effects: list, text: str) -> bool:
    for eff in effects:
        params = eff.get("params") or {}
        if text and text in (params.get("message") or params.get("success_message") or ""):
            return True
    return False


def fix_triggers(nodes: dict, edges: list, changes: List[str]) -> None:
    logic_ids = {nid for nid, n in nodes.items() if n.get("type") == "logic_trigger"}
    rewritten: List[dict] = []
    by_pair = set()
    for edge in edges:
        is_legacy = (
            edge.get("type") == "triggers"
            and edge.get("source") in logic_ids
            and edge.get("target") not in logic_ids
        )
        if not is_legacy:
            rewritten.append(edge)
            continue

        trigger_id = edge["source"]
        owner_id = edge["target"]
        node = nodes.get(trigger_id) or {}
        props = node.setdefault("properties", {})
        event = props.get("event") or props.get("trigger_type") or "on_use"

        effects = [dict(e) for e in (props.get("effects") or []) if isinstance(e, dict)]

        message = str(props.get("message") or "").strip()
        if message and not _has_same_message(effects, message):
            effects.append(_message_effect(message))

        for item_id in (props.get("spawn_items") or []):
            effects.append({"type": "spawn_item", "params": {"item_id": item_id}})

        memory = props.get("grant_memory")
        if isinstance(memory, dict) and memory.get("text"):
            effects.append({
                "type": "grant_memory",
                "params": {"target": "self", "memory": memory},
            })

        props["effects"] = effects
        props["trigger_type"] = event
        for legacy in ("event", "target", "message", "spawn_items", "grant_memory"):
            props.pop(legacy, None)

        rewritten.append({
            "source": owner_id,
            "target": trigger_id,
            "type": "triggers",
            "properties": {"trigger_type": event},
        })
        by_pair.add((owner_id, trigger_id))
        changes.append(
            f"trigger {trigger_id}: inverted edge {trigger_id} -> {owner_id} "
            f"to {owner_id} -> {trigger_id} (type={event}, {len(effects)} effect(s))"
        )

    edges[:] = rewritten


LEGACY_EFFECT_ALIASES = {
    "decrement_uses": ("adjust_uses", {"delta": -1}),
    "increment_uses": ("adjust_uses", {"delta": 1}),
    "roll_condition": ("save", {}),
}


def fix_effects(nodes: dict, edges: list, changes: List[str]) -> None:
    """Rewrite effect types that don't exist in the engine to their canonical
    equivalents (e.g. decrement_uses -> adjust_uses delta -1)."""
    def rewrite(effect: dict) -> None:
        etype = effect.get("type")
        if etype not in LEGACY_EFFECT_ALIASES:
            return
        new_type, extra = LEGACY_EFFECT_ALIASES[etype]
        effect["type"] = new_type
        params = effect.setdefault("params", {})
        for key, value in extra.items():
            params.setdefault(key, value)
        if etype == "roll_condition":
            for branch in ("on_success", "on_fail"):
                value = params.get(branch)
                if isinstance(value, dict):
                    params[branch] = [value]
        changes.append(f"effect {etype} -> {new_type}")

    for node in nodes.values():
        for effect in ((node.get("properties") or {}).get("effects") or []):
            if isinstance(effect, dict):
                rewrite(effect)
    for edge in edges:
        for effect in ((edge.get("properties") or {}).get("effects") or []):
            if isinstance(effect, dict):
                rewrite(effect)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Scenario JSON to fix")
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry run)")
    parser.add_argument("--only", default="ways,weapons,triggers,effects",
                        help="Comma list of ways,weapons,triggers,effects")
    args = parser.parse_args()

    path = Path(args.input)
    data = json.loads(path.read_text(encoding="utf-8"))
    graph = data.setdefault("graph", {})
    nodes = graph.setdefault("nodes", {})
    edges = graph.setdefault("edges", [])

    wanted = {p.strip() for p in args.only.split(",") if p.strip()}
    changes: List[str] = []
    if "ways" in wanted:
        fix_ways(nodes, edges, changes)
    if "weapons" in wanted:
        fix_weapons(nodes, changes)
    if "triggers" in wanted:
        fix_triggers(nodes, edges, changes)
    if "effects" in wanted:
        fix_effects(nodes, edges, changes)

    print(f"{path}: {len(changes)} fix(es)")
    for line in changes:
        print(f"  - {line}")

    if not changes:
        print("Nothing to do.")
        return 0

    if args.apply:
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"\nApplied {len(changes)} fix(es) to {path}.")
        print("Reload the scenario (or restart the server) to pick them up.")
    else:
        print("\nDry run — re-run with --apply to write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
