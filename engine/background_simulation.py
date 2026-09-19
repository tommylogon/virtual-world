"""Deterministic background survival runner (task-399).

Characters with ``simulation_mode == "background"`` do not run the LLM loop.
Instead this module makes a *coarse, scheduled, deterministic* decision when
the character is due (``next_due_tick``), executing it against the **same**
Player/graph state so the character stays the same person (see
docs/design/reversibility-contract.md).

v1 scope — survival only:
    drink when thirsty, eat when hungry, sleep when tired, travel one hop
    toward a known food/water area when the local area has none.

Every decision writes an objective trace entry with a reason tag
(docs/design/trace-format.md) so the span can later be summarized into memory.

Deliberately NOT here yet: schedules/work, relationships, dialogue, combat.
Those are the next slices. No LLM calls are made.
"""

from __future__ import annotations

import logging
import random
from collections import deque

from graph import EDGE_IN, EDGE_CARRYING
from engine.trace import record

logger = logging.getLogger(__name__)

FOOD_TAGS = ("food", "eat", "edible", "meal")
DRINK_TAGS = ("drink", "water", "beverage")

THIRST_THRESHOLD = 45     # drive: high = parched; act before it gets urgent
HUNGER_THRESHOLD = 50     # drive: high = starving
ENERGY_THRESHOLD = 30     # resource: low = tired

MEAL_RESTORE = 45         # Hunger (drive) reduced by this when eating
DRINK_RESTORE = 50        # Thirst (drive) reduced by this when drinking

DECISION_INTERVAL = 10    # base ticks between background decisions


class BackgroundSimulation:
    """Runs due background characters. Owned by the engine, called each tick."""

    def __init__(self, game_state):
        self.gs = game_state
        self._areas_cache = {}

    # ───────────────────────────── entry point ─────────────────────────────

    def process_due(self):
        """Handle every background character whose next_due_tick has arrived."""
        for name, p in list(self.gs.players.items()):
            if getattr(p, "simulation_mode", "active") != "background":
                continue
            if p.state == "dead":
                continue
            if self.gs.time_ticks < getattr(p, "next_due_tick", 0):
                continue
            try:
                self._act(name, p)
            except Exception as e:  # never let one character stall the tick
                logger.warning("[background] %s: %s", name, e)
            p.next_due_tick = self.gs.time_ticks + self._interval(p)

    # ───────────────────────────── decisions ───────────────────────────────

    def _act(self, name, p):
        if p.activity:
            return  # mid-activity (e.g. sleeping) — leave them to it
        if p.state == "unconscious":
            return  # collapsed; the engine's recovery path handles waking

        v = p.vitals
        thirst = v.get("Thirst", 0)
        hunger = v.get("Hunger", 0)
        energy = v.get("Energy", 100)

        # Critical exhaustion wins over everything: without this, a character
        # chasing water they can't reach never sleeps and dies of exhaustion
        # (the exact failure the 2-day soak showed).
        if energy <= 15:
            self._sleep(p)
            return

        if thirst >= THIRST_THRESHOLD:
            # The scenario models natural water as an AREA tag ("water") you
            # drink from by standing in it, not as an item to consume.
            if self._in_water_area(p):
                p.vitals["Thirst"] = max(0, p.vitals.get("Thirst", 0) - DRINK_RESTORE)
                record(p, self.gs.time_ticks, "act",
                       f"drank from {p.current_area}", why="needs:drink",
                       area=p.current_area, tags=["need"])
                self.gs.add_log_entry(f"[{p.name}] drinks from {p.current_area}.")
                return
            if self._consume_here(p, DRINK_TAGS, "drink"):
                return
            if self._travel_toward(p, DRINK_TAGS, "thirst"):
                return
            return

        if energy <= ENERGY_THRESHOLD:
            self._sleep(p)
            return

        if hunger >= HUNGER_THRESHOLD:
            if self._consume_here(p, FOOD_TAGS, "eat"):
                return
            if self._travel_toward(p, FOOD_TAGS, "hunger"):
                return

    # ───────────────────────────── actions ─────────────────────────────────

    def _consume_here(self, p, tags, kind):
        node = self._find_consumable(p, tags)
        if not node:
            return False
        props = node.properties or {}
        count = props.get("count")
        uses = props.get("uses")
        if isinstance(count, int) and count > 1:
            props["count"] = count - 1
        elif isinstance(uses, (int, float)) and uses > 1:
            props["uses"] = uses - 1
        else:
            self.gs.graph.remove_node(node.id)
        # The set of areas holding a resource changes when the last item in an
        # area is consumed; a stale cache makes characters keep "head toward"
        # their own now-empty area instead of a real source.
        self._areas_cache.clear()

        tick = self.gs.time_ticks
        if kind == "drink":
            p.vitals["Thirst"] = max(0, p.vitals.get("Thirst", 0) - DRINK_RESTORE)
            verb = "drank"
        else:
            p.vitals["Hunger"] = max(0, p.vitals.get("Hunger", 0) - MEAL_RESTORE)
            verb = "ate"
        record(p, tick, "act", f"{verb} {node.name}", why=f"needs:{kind}",
               area=p.current_area, tags=["need"])
        self.gs.add_log_entry(f"[{p.name}] {verb} the {node.name}.")
        return True

    def _sleep(self, p):
        try:
            self.gs.activities.start_activity(p.name, "sleeping")
        except Exception:
            return
        record(p, self.gs.time_ticks, "act", "went to sleep", why="needs:energy",
               area=p.current_area, tags=["need"])
        self.gs.add_log_entry(f"[{p.name}] settles down to sleep.")

    def _travel_toward(self, p, tags, need):
        step = self._target_step(p, tags)
        if not step:
            return False
        target_name, direction = step
        if not direction:
            return False
        old_active = self.gs.active_player
        self.gs.active_player = p.name
        try:
            self.gs.movement.move_to_area(direction)
        except Exception as e:
            logger.warning("[background] travel %s (%s): %s", p.name, direction, e)
            return False
        finally:
            self.gs.active_player = old_active
        record(p, self.gs.time_ticks, "move",
               f"travelled {direction} toward {target_name}",
               why=f"needs:{need}", area=p.current_area, tags=["travel"])
        self.gs.add_log_entry(f"[{p.name}] heads {direction} toward {target_name}.")
        return True

    # ───────────────────────────── lookups ─────────────────────────────────

    def _find_consumable(self, p, tags):
        graph = self.gs.graph
        player_id = self.gs._player_node_id(p.name)
        area_id = (self.gs.area_node_id(p.current_area)
                   if p.current_area else None)
        # carried items first
        for e in graph.edges:
            if e.type == EDGE_CARRYING and e.target == player_id:
                node = graph.get_node(e.source)
                if node and self._is_consumable(node, tags):
                    return node
        if area_id:
            for e in graph.edges:
                if e.type == EDGE_IN and e.target == area_id:
                    node = graph.get_node(e.source)
                    if node and self._is_consumable(node, tags):
                        return node
        return None

    def _is_consumable(self, node, tags):
        props = node.properties or {}
        if props.get("current_state") == "hidden":
            return False
        node_tags = {str(t).lower() for t in (props.get("tags", []) or [])}
        if set(tags) & node_tags:
            return True
        actions = props.get("actions", [])
        if isinstance(actions, str):
            actions = [a.strip() for a in actions.split(",")]
        verbs = {str(a).lower() for a in (actions or [])}
        return bool(verbs & {"eat", "drink"})

    # ── navigation ────────────────────────────────────────────────────────
    # Way edges in the scenario reference sanitized area ids (e.g.
    # "area_chiefs_pit") while the area node id keeps the apostrophe
    # ("area_chief's_pit"), so strict-id pathfinding returns None from most
    # areas. Resolve both endpoints by normalized name instead.

    @staticmethod
    def _norm(text):
        return "".join(ch for ch in str(text).lower() if ch.isalnum())

    def _norm_area_table(self):
        if getattr(self, "_area_table", None) is not None:
            return self._area_table
        table = {}
        for node in self.gs.graph.nodes.values():
            if node.type != "area":
                continue
            table[self._norm(node.name)] = node.id
            key = self._norm(node.id)
            table[key] = node.id
            if key.startswith("area"):
                table[key[4:]] = node.id
        self._area_table = table
        return table

    def _resolve_area_id(self, area_id_or_name):
        if not area_id_or_name:
            return None
        node = self.gs.graph.get_node(area_id_or_name)
        if node and node.type == "area":
            return node.id
        return self._norm_area_table().get(self._norm(area_id_or_name))

    def _target_step(self, p, tags):
        """Nearest area holding ``tags`` reachable from the character's area.

        Returns ``(area_name, exit_label)`` or None. BFS walks the engine's own
        exits (``include_hidden=True`` so authoring-hidden passages still
        connect), which guarantees the returned label is one
        ``movement.move_to_area`` will accept.
        """
        areas = self._areas_with(tags)
        start = p.current_area
        if not start or not areas:
            return None
        seen = {start}
        queue = deque([(start, None)])
        while queue:
            current, first = queue.popleft()
            # Never treat the current area as a travel target: _act already
            # tried to consume/water here, so travel only makes sense to a
            # different area (otherwise we'd return a None direction and stall).
            if current in areas and current != start:
                return current, first
            for label, exit_data in self.gs.build_exits_for_area(
                    current, include_hidden=True).items():
                target = exit_data.get("target")
                if target and target not in seen:
                    seen.add(target)
                    queue.append((target, first or label))
        return None

    def _in_water_area(self, p):
        """True if the character's area is itself a water source (natural
        water is modelled as an area tag, not an item)."""
        if not p.current_area:
            return False
        node = self.gs.graph.get_node(self._resolve_area_id(p.current_area))
        if not node:
            return False
        ntags = {str(t).lower() for t in (node.properties.get("tags", []) or [])}
        return "water" in ntags

    def _areas_with(self, tags):
        key = tuple(tags)
        if key in self._areas_cache:
            return self._areas_cache[key]
        areas = set()
        graph = self.gs.graph
        want = {str(t).lower() for t in tags}
        for node in graph.nodes.values():
            if node.type != "area":
                continue
            # an area can itself be the resource (water sources, larders)
            ntags = {str(t).lower() for t in (node.properties.get("tags", []) or [])}
            if want & ntags:
                areas.add(node.name)
        for e in graph.edges:
            if e.type != EDGE_IN:
                continue
            tgt = graph.get_node(e.target)
            if not tgt or tgt.type != "area":
                continue
            src = graph.get_node(e.source)
            if src and self._is_consumable(src, tags):
                areas.add(tgt.name)
        self._areas_cache[key] = areas
        return areas

    def _interval(self, p):
        """Small deterministic jitter so the camp doesn't act in lockstep."""
        seed = f"{getattr(p, 'id', p.name)}:{self.gs.time_ticks}"
        return DECISION_INTERVAL + random.Random(seed).randint(0, 4)
