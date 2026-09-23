from typing import Dict, List, Optional

from graph import EDGE_CONNECTION, EDGE_IN, EDGE_CARRYING, EDGE_EQUIPPED
from engine.runtime_config import config as _config

#: Fraction of a lit neighbor area's light that spills through an open door.
#: Backward-compat default; runtime_config may override (Engine Config).
SPILL_FACTOR = 0.5


def _spill_factor() -> float:
    value = _config.get("light.spill_factor", SPILL_FACTOR)
    try:
        return float(value)
    except (ValueError, TypeError):
        return SPILL_FACTOR


# Time-of-day outdoor light curve (task-230): (hour, light 0-100) anchors,
# linearly interpolated. Deep night ~8, dawn ramp 5-8, full day 9-16,
# dusk ramp 17-21, back to night.
_OUTDOOR_ANCHORS = [
    (0, 8), (5, 10), (7, 45), (9, 85), (16, 85), (18, 55), (19, 35), (21, 12), (24, 8),
]


def outdoor_light_for_hour(hour: int) -> int:
    """Outdoor ambient light (0-100) for an hour 0-23, interpolated."""
    hour = max(0, min(23, int(hour)))
    for (h0, v0), (h1, v1) in zip(_OUTDOOR_ANCHORS, _OUTDOOR_ANCHORS[1:]):
        if h0 <= hour <= h1:
            if h1 == h0:
                return v0
            frac = (hour - h0) / (h1 - h0)
            return int(round(v0 + (v1 - v0) * frac))
    return 8


class LightingSystem:
    """Manages light level calculations, ambient light with spill from adjacent areas,
    graph-scan lighting from lit items, and dark vision checks."""

    def __init__(self, graph):
        self.graph = graph
        # Optional callable returning the current in-game hour (0-23), wired by
        # the engine (task-230). When set, OUTDOOR areas' ambient light follows
        # the time-of-day curve instead of a static value.
        self.hour_provider = None
        # Optional callable returning the current moon phase dict
        # (task-229): {"name", "icon", "light_bonus"}. When set, outdoor
        # NIGHT areas gain the moon's light bonus (full moon = visibly
        # brighter, new moon = pitch black).
        self.moon_provider = None

    def light_to_level(self, value):
        """Convert a numeric or string light value to a 5-level enum string."""
        try:
            v = int(value)
        except (ValueError, TypeError):
            if isinstance(value, str) and value in ('pitch_black', 'dim', 'normal', 'bright', 'blinding'):
                return value
            return 'normal'
        if v <= 20:
            return 'pitch_black'
        elif v <= 40:
            return 'dim'
        elif v <= 70:
            return 'normal'
        elif v <= 90:
            return 'bright'
        else:
            return 'blinding'

    def get_light_int(self, env, default=80):
        """Get light as integer, handling both int and string enum formats."""
        raw = env.get("light", default)
        try:
            return int(raw)
        except (ValueError, TypeError):
            mapping = {'pitch_black': 10, 'dim': 30, 'normal': 55, 'bright': 80, 'blinding': 95}
            return mapping.get(raw, default)

    def get_item_light_contribution(self, area_id: str) -> int:
        """Sum light_level of all lit items in or carried/equipped in this area."""
        total, _ = self._item_light_stats(area_id)
        return total

    def _item_light_stats(self, area_id: str):
        """Return ``(total, max_level)`` for lit items in/around ``area_id``.

        The max is the strongest single source — used as the brightness CEILING
        so piling up dim/normal sources can never out-verb their own level
        (50 dim embers read as a warm glow, never a laser).
        """
        total = 0
        best = 0

        def add_item(node):
            nonlocal total, best
            if node and node.type == "item" and node.properties.get("current_state") in ("lit", "on"):
                tags = node.properties.get("tags", [])
                if "light_source" not in tags:
                    return
                raw = node.properties.get("light_level", "dim")
                level_map = {'pitch_black': 10, 'dim': 30, 'normal': 55, 'bright': 80, 'blinding': 95}
                if isinstance(raw, str) and raw in level_map:
                    light = level_map[raw]
                else:
                    try:
                        light = int(raw)
                    except (ValueError, TypeError):
                        light = 30
                total += light
                best = max(best, light)

        # task-407 perf: one pass over the area's contents instead of two
        # identical EDGE_IN scans, and one tuple lookup for carried+equipped
        # instead of two calls per character.
        for edge in self.graph.get_edges_for_target(area_id, EDGE_IN):
            node = self.graph.get_node(edge.source)
            if node is None:
                continue
            if node.type == "item":
                add_item(node)
            elif node.type == "character":
                for ce in self.graph.get_edges_for_target(
                        node.id, (EDGE_CARRYING, EDGE_EQUIPPED)):
                    add_item(self.graph.get_node(ce.source))

        return min(100, total), min(100, best)

    def is_outdoor_area(self, area_id: str) -> bool:
        """True when the area node carries the 'outdoor' tag (task-230)."""
        node = self.graph.get_node(area_id)
        if not node:
            return False
        tags = node.properties.get("tags", [])
        return "outdoor" in tags

    def _own_light(self, area_id: str, env: Dict, hour: Optional[int]) -> int:
        """Area's own effective light: authored/time-of-day base vs the
        brightest single lit item.

        task-407: the effective light is the **brightest source**, never the
        sum. Four dim torches read as one dim torch, not a laser — so this is
        ``max(base, best_item)``, and the old ``base + sum`` arithmetic (which
        the ceiling then discarded anyway) is gone.
        """
        explicit = isinstance(env, dict) and "light" in env
        own = self.get_light_int(env, 80)

        if hour is None and self.hour_provider is not None:
            try:
                hour = int(self.hour_provider()) % 24
            except (TypeError, ValueError):
                hour = None
        if hour is not None and self.is_outdoor_area(area_id):
            curve = outdoor_light_for_hour(hour)
            own = max(curve, own) if explicit else curve
            # task-229: the moon adds light to outdoor NIGHT areas — unless
            # the sky is obscured (stormy nullifies, foggy halves the bonus).
            if hour >= 19 or hour < 5:
                bonus = 0
                if self.moon_provider is not None:
                    try:
                        phase = self.moon_provider()
                    except TypeError:
                        phase = self.moon_provider
                    if isinstance(phase, dict):
                        bonus = int(phase.get("light_bonus", 0) or 0)
                if bonus:
                    weather = str((env or {}).get("weather", "") or "")
                    if weather == "stormy":
                        bonus = 0
                    elif weather == "foggy":
                        bonus = bonus // 2
                    own = min(100, own + bonus)

        best = self._item_light_stats(area_id)[1]
        return max(own, best)

    def _neighbour_light(self, area_id: str) -> int:
        """A neighbour's light for spill purposes: its authored/curved base vs
        its brightest lit item (no recursion into further spill)."""
        node = self.graph.get_node(area_id)
        if not node:
            return 0
        env = node.properties.get("environment", {})
        return max(self.get_light_int(env, 80), self._item_light_stats(area_id)[1])

    def _best_spill(self, area_id: str) -> int:
        best_spill = 0
        for edge in self.graph.get_edges_for_source(area_id, EDGE_CONNECTION):
            door = self.graph.get_node(edge.target)
            if door and door.type == "way" and (door.properties.get("current_state") == "open" or door.properties.get("see_through")):
                for conn in self.graph.get_edges_for_source(door.id, EDGE_CONNECTION):
                    if conn.target != area_id:
                        o_light = min(100, self._neighbour_light(conn.target))
                        spill = max(0, int(o_light * _spill_factor()))
                        if spill > best_spill:
                            best_spill = spill
                        break
        return best_spill

    def recompute_area_lights(self, hour: Optional[int] = None) -> None:
        """Compute every area's effective light once per tick (task-407).

        Two passes over areas: first each area's own light and brightest item,
        then spill from neighbours' stored values — so no neighbour is scanned
        twice. ``get_ambient_light`` returns this stamp when called without an
        explicit env/hour and the graph has not changed since.
        """
        areas = [n for n in self.graph.nodes.values() if n.type == "area"]
        own: Dict[str, int] = {}
        best_items: Dict[str, int] = {}
        authored: Dict[str, int] = {}
        for node in areas:
            env = node.properties.get("environment", {}) or {}
            own[node.id] = self._own_light(node.id, env, hour)
            best_items[node.id] = self._item_light_stats(node.id)[1]
            authored[node.id] = self.get_light_int(env, 80)

        result: Dict[str, int] = {}
        for node in areas:
            best_spill = 0
            for edge in self.graph.get_edges_for_source(node.id, EDGE_CONNECTION):
                door = self.graph.get_node(edge.target)
                if door and door.type == "way" and (
                        door.properties.get("current_state") == "open"
                        or door.properties.get("see_through")):
                    for conn in self.graph.get_edges_for_source(door.id, EDGE_CONNECTION):
                        if conn.target == node.id:
                            continue
                        if conn.target in authored:
                            o_light = min(100, max(authored[conn.target], best_items.get(conn.target, 0)))
                            best_spill = max(best_spill, int(o_light * _spill_factor()))
                        break
            result[node.id] = max(own[node.id], best_items.get(node.id, 0), best_spill)

        self._area_light = result
        self._area_light_rev = self.graph.get_revision()

    def get_ambient_light(self, area_id: str, env: Optional[Dict] = None, hour: Optional[int] = None) -> int:
        """Get effective light for a area, considering its own sources,
        lit items in the area, plus spill from adjacent areas through open ways.

        Outdoor areas (task-230): when an hour is available via ``hour_provider``,
        the area's base light follows the time-of-day curve. An explicitly
        authored ``environment.light`` acts as a FLOOR (a magically lit glade
        stays bright at midnight); otherwise the curve fully drives the base.
        """
        if env is None and hour is None:
            cache = getattr(self, "_area_light", None)
            if cache is not None and getattr(self, "_area_light_rev", None) == self.graph.get_revision():
                hit = cache.get(area_id)
                if hit is not None:
                    return hit
        if env is None:
            node = self.graph.get_node(area_id)
            if not node:
                return 80
            env = node.properties.get("environment", {})
        own = self._own_light(area_id, env, hour)
        return max(own, self._best_spill(area_id))

    def can_see_in_dark(self, player_manager, player_name=None) -> bool:
        """Check if a player can see in darkness (ghost, dark_vision trait, or slasher)."""
        name = player_name or player_manager.active_player
        if not name:
            return False
        player = player_manager.players.get(name)
        if not player:
            return False
        if player.state == "dead":
            return True
        from engine.traits import TraitSystem
        if TraitSystem.has_effect(player, "dark_vision"):
            return True
        return False
