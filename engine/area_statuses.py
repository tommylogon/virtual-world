"""Dynamic area status system (task-233).

Areas can carry a ``statuses`` property list — instances of dynamic
environmental states like ``on_fire``, ``flooded`` or ``poison_gas``. Each
status ticks environment mutations, damage and condition application on
everyone present, and (for the definitions that declare it) propagates to
neighbouring areas through open ways.

Deliberately separate from the character condition system
(``engine/conditions.py``): area statuses have no state hierarchy, no action
gates, and they mutate the environment and propagate spatially. They share
the *pattern* (registry + instance schema), not the code. Area statuses can
inflict character conditions via the existing ``apply_condition`` pathway.

Status instances live on the area node's ``properties["statuses"]`` list, so
they persist through the regular graph serialization — no extra save/load
surface needed.
"""

from __future__ import annotations

import random
from typing import Any, Optional

#: Severity cap when stacking the same status type on one area.
MAX_SEVERITY = 5

#: Status type definitions. ``default_tick_effects`` values:
#:   temperature  — °C added to the area environment each tick
#:   air          — env air override while active
#:   light        — ambient light delta each tick (clamped 0-100)
#:   damage       — {vital: amount} applied to every character present
#:   condition    — character condition applied to everyone present
#:   movement_cost — extra Energy per move action while present
#: ``propagation``: spread to areas connected through open ways.
AREA_STATUS_DEFINITIONS: dict[str, dict[str, Any]] = {
    "on_fire": {
        "name": "On Fire",
        "default_tick_effects": {"temperature": 10, "air": "smoke", "light": 15,
                                 "damage": {"hp": 1}},
        "propagation": {"rate": 0.05, "target_statuses": ["on_fire", "smoke"]},
        "clear_on": ["extinguished", "duration_expired"],
    },
    "smoke": {
        "name": "Smoky",
        "default_tick_effects": {"air": "smoke"},
        "propagation": {"rate": 0.03, "target_statuses": ["smoke"]},
        "clear_on": ["aired_out", "duration_expired"],
    },
    "flooded": {
        "name": "Flooded",
        "default_tick_effects": {"movement_cost": 1},
        "propagation": {"rate": 0.02, "target_statuses": ["flooded"]},
        "clear_on": ["drained", "duration_expired"],
    },
    "poison_gas": {
        "name": "Poison Gas",
        "default_tick_effects": {"damage": {"hp": 2}, "condition": "poisoned",
                                 "air": "toxic"},
        "propagation": {"rate": 0.03, "target_statuses": ["poison_gas"]},
        "clear_on": ["vented", "duration_expired"],
    },
    "blessed": {
        "name": "Blessed",
        "default_tick_effects": {"light": 5},
        "clear_on": ["duration_expired"],
    },
    "darkness_magic": {
        "name": "Magical Darkness",
        "default_tick_effects": {"light": -10},
        "clear_on": ["dispelled", "duration_expired"],
    },
}


class AreaStatusSystem:
    """Applies, ticks, and propagates dynamic statuses on area nodes."""

    def __init__(self, graph, game_state=None):
        self.graph = graph
        self.gs = game_state

    # ── mutation ──────────────────────────────────────────────────────────

    def apply_status(self, area_id: str, status_type: str, severity: int = 1,
                     duration: Optional[int] = None, source: Optional[str] = None) -> bool:
        """Add (or stack) *status_type* on the area. Returns True on success."""
        area = self.graph.get_node(area_id) if area_id else None
        if area is None or status_type not in AREA_STATUS_DEFINITIONS:
            return False
        statuses = area.properties.setdefault("statuses", [])
        for inst in statuses:
            if inst.get("type") == status_type:
                inst["severity"] = min(MAX_SEVERITY, int(inst.get("severity", 1)) + int(severity))
                if duration is not None and inst.get("duration") is not None:
                    inst["duration"] = max(int(inst["duration"]), int(duration))
                return True
        definition = AREA_STATUS_DEFINITIONS[status_type]
        statuses.append({
            "type": status_type,
            "severity": max(1, min(MAX_SEVERITY, int(severity))),
            "duration": duration,
            "source": source,
            "tick_effects": dict(definition.get("default_tick_effects", {})),
            "propagation": definition.get("propagation"),
            "clear_on": list(definition.get("clear_on", [])),
        })
        return True

    def clear_status(self, area_id: str, status_type: str) -> bool:
        """Remove every instance of *status_type* from the area."""
        area = self.graph.get_node(area_id) if area_id else None
        if area is None:
            return False
        statuses = area.properties.get("statuses", [])
        kept = [s for s in statuses if s.get("type") != status_type]
        if len(kept) == len(statuses):
            return False
        area.properties["statuses"] = kept
        return True

    def has_status(self, area_id: str, status_type: str) -> bool:
        area = self.graph.get_node(area_id) if area_id else None
        if area is None:
            return False
        return any(s.get("type") == status_type for s in area.properties.get("statuses", []))

    # ── per-tick processing ───────────────────────────────────────────────

    def process_tick(self) -> None:
        """Tick every area's statuses: environment mutations, damage,
        condition application, duration expiry, then propagation."""
        if not self.graph:
            return
        for node in list(self.graph.nodes.values()):
            if node.type != "area":
                continue
            statuses = node.properties.get("statuses", [])
            if not statuses:
                continue
            env = node.properties.setdefault("environment", {})
            alive = []
            for status in statuses:
                effects = status.get("tick_effects", {}) or {}
                severity = int(status.get("severity", 1))
                if "temperature" in effects:
                    env["temperature"] = round(
                        float(env.get("temperature", 21)) + float(effects["temperature"]) * severity, 2)
                if "air" in effects:
                    env["air"] = effects["air"]
                if "light" in effects:
                    env["light"] = max(0, min(100, int(env.get("light", 0)) + int(effects["light"]) * severity))
                if "damage" in effects:
                    self._apply_area_damage(node, effects["damage"], severity)
                if "condition" in effects:
                    self._apply_area_condition(node, effects["condition"])
                duration = status.get("duration")
                if duration is not None:
                    duration -= 1
                    status["duration"] = duration
                    if duration <= 0:
                        continue  # expired
                alive.append(status)
            if alive:
                node.properties["statuses"] = alive
            else:
                node.properties["statuses"] = []
            # Propagation after the tick effects settle.
            for status in alive:
                propagation = status.get("propagation")
                if propagation:
                    self._propagate_status(node, status, propagation)

    # ── internals ─────────────────────────────────────────────────────────

    def _area_characters(self, area_node) -> list[str]:
        """Names of characters currently in the area (presence graph edges)."""
        names: list[str] = []
        try:
            for edge in self.graph.edges:
                if edge.type == "in" and edge.target == area_node.id:
                    src = self.graph.get_node(edge.source)
                    if src and src.type == "character":
                        name = getattr(src, "name", None) or src.properties.get("name") or src.id
                        if name and name not in names:
                            names.append(name)
        except Exception:
            pass
        return names

    def _apply_area_damage(self, area_node, damage: dict, severity: int) -> None:
        if not self.gs or not isinstance(damage, dict):
            return
        players = getattr(self.gs, "players", {}) or {}
        for name in self._area_characters(area_node):
            obj = players.get(name)
            if obj is None or getattr(obj, "state", "") == "dead":
                continue
            vitals = getattr(obj, "vitals", None)
            for vital, amount in damage.items():
                key = "HP" if str(vital).lower() in ("hp", "health") else str(vital)
                if isinstance(vitals, dict) and key in vitals:
                    try:
                        vitals[key] = max(0, int(vitals[key]) - int(amount) * severity)
                    except (TypeError, ValueError):
                        continue
                elif hasattr(obj, key):
                    current = getattr(obj, key, None)
                    try:
                        setattr(obj, key, max(0, int(current) - int(amount) * severity))
                    except (TypeError, ValueError):
                        continue
            if getattr(self.gs, "player_manager", None) is not None:
                try:
                    self.gs.player_manager.add_log_entry(
                        f"[{status_label(self, area_node)}] {name} suffers in the {area_node.name}.")
                except Exception:
                    pass

    def _apply_area_condition(self, area_node, condition: str) -> None:
        if not self.gs or not condition:
            return
        conditions_system = getattr(self.gs, "conditions", None)
        if conditions_system is None or not hasattr(conditions_system, "apply_condition"):
            return
        players = getattr(self.gs, "players", {}) or {}
        for name in self._area_characters(area_node):
            if name in players:
                try:
                    conditions_system.apply_condition(
                        name, condition,
                        duration=3,
                        source=f"area:{area_node.id}",
                    )
                except Exception:
                    continue

    def _propagate_status(self, area_node, status: dict, propagation: dict) -> None:
        """Spread to areas connected through open ways with probability ``rate``."""
        rate = float(propagation.get("rate", 0.0))
        targets = propagation.get("target_statuses") or [status.get("type")]
        if rate <= 0:
            return
        for neighbour_id in self._open_neighbours(area_node.id):
            if random.random() > rate:
                continue
            for status_type in targets:
                if status_type in AREA_STATUS_DEFINITIONS:
                    self.apply_status(neighbour_id, status_type,
                                      severity=1, duration=status.get("duration"),
                                      source=status.get("source"))

    def _open_neighbours(self, area_id: str) -> list[str]:
        """Areas reachable from *area_id* through ways that are open."""
        neighbours: list[str] = []
        way_to_areas: dict[str, set[str]] = {}
        for edge in self.graph.edges:
            if edge.type == "connection":
                src = self.graph.get_node(edge.source)
                if src and src.type == "way":
                    way_to_areas.setdefault(edge.source, set()).add(edge.target)
        for way_id, area_ids in way_to_areas.items():
            if area_id not in area_ids:
                continue
            way = self.graph.get_node(way_id)
            if not way or way.properties.get("current_state") != "open":
                continue
            for other in area_ids:
                if other != area_id and other not in neighbours:
                    neighbours.append(other)
        return neighbours


def status_label(system: "AreaStatusSystem", area_node) -> str:
    """Short human label of the area's strongest status (for log lines)."""
    statuses = area_node.properties.get("statuses", []) if area_node else []
    if not statuses:
        return "area status"
    strongest = max(statuses, key=lambda s: int(s.get("severity", 1)))
    return AREA_STATUS_DEFINITIONS.get(strongest.get("type"), {}).get("name", strongest.get("type", "status"))
