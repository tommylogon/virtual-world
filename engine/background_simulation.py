"""Deterministic background survival runner (task-399).

Characters with ``simulation_mode == "background"`` do not run the LLM loop.
Instead this module makes *coarse, deterministic* decisions against the
**same** Player/graph state so the character stays the same person (see
docs/design/reversibility-contract.md).

Decisions are paced by an **action credit** measured in game minutes, not
ticks: a character is entitled to one decision per ``DECISION_MINUTES`` of
game time, and a tick grants ``time_per_tick_minutes / DECISION_MINUTES`` of
credit. At 1 min/tick that is one decision per 10 ticks (the old fixed
interval); at 15 min/tick it is ~1.5 decisions per tick, so a character takes
the same number of decisions per game hour whatever the tick length. Gating on
ticks instead meant a 15-minute world gave everyone a fifteenth as many
decisions per hour and they starved while food was in reach.

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
from vital_rates import tick_minutes

logger = logging.getLogger(__name__)

FOOD_TAGS = ("food", "eat", "edible", "meal")
DRINK_TAGS = ("drink", "water", "beverage")

THIRST_THRESHOLD = 45     # drive: high = parched; act before it gets urgent
HUNGER_THRESHOLD = 50     # drive: high = starving
ENERGY_THRESHOLD = 30     # resource: low = tired

MEAL_RESTORE = 45         # Hunger (drive) reduced by this when eating
DRINK_RESTORE = 50        # Thirst (drive) reduced by this when drinking

DECISION_MINUTES = 10     # game minutes between background decisions
MAX_ACTIONS_PER_TICK = 4  # bound so a very long tick cannot run away


class BackgroundSimulation:
    """Runs due background characters. Owned by the engine, called each tick."""

    def __init__(self, game_state):
        self.gs = game_state
        self._areas_cache = {}

    # ───────────────────────────── entry point ─────────────────────────────

    def process_due(self):
        """Spend each background character's accrued action credit.

        Credit accrues in game minutes, so the number of decisions per game
        hour is the same at any ``time_per_tick_minutes``. A character who is
        mid-activity (sleeping) or unconscious neither decides nor banks
        credit, so a long sleep cannot leave a backlog to dump on waking.
        """
        gain = tick_minutes(self.gs) / DECISION_MINUTES
        for name, p in list(self.gs.players.items()):
            if getattr(p, "simulation_mode", "active") != "background":
                continue
            if p.state == "dead":
                continue
            if p.activity or p.state == "unconscious":
                continue  # committed to a duration; no decisions, no banking

            credit = getattr(p, "_action_credit", None)
            if credit is None:
                # First sighting: act at once (the old next_due_tick == 0 path),
                # unless a save/tool set an explicit "not before" tick. Starting
                # at a random fraction instead would both delay the first
                # decision and permanently shorten every later interval.
                credit = 0.0 if self.gs.time_ticks < getattr(p, "next_due_tick", 0) else 1.0
            credit = min(credit + gain, MAX_ACTIONS_PER_TICK)

            spent = 0
            while credit >= 1.0 and spent < MAX_ACTIONS_PER_TICK:
                try:
                    self._act(name, p)
                except Exception as e:  # never let one character stall the tick
                    logger.warning("[background] %s: %s", name, e)
                    break
                credit -= 1.0
                spent += 1
                if p.activity or p.state == "unconscious":
                    break  # a duration started; stop spending this tick
            p._action_credit = credit

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
        node = self._find_consumable(p, tags, verb=self._verb_for_need(kind))
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

    @staticmethod
    def _verb_for_need(need):
        """The action a search is really for, so a drink is not counted as food.

        Accepts both vocabularies in use: needs are `thirst`/`hunger` and the
        consume kind is `drink`/`eat`.
        """
        return "drink" if str(need).lower() in ("thirst", "drink") else "eat"

    def _travel_toward(self, p, tags, need):
        step = self._target_step(p, tags, verb=self._verb_for_need(need))
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

    #: Spatial relations a forager can reach *through*. An area holds things in,
    #: on, under, behind, beside or at it, and an item can hold the same ways —
    #: berries in a bush, bread on a table, a pouch beside a log.
    REACHABLE_RELATIONS = ("in", "on", "under", "behind", "beside", "at")

    def _spatial_items(self, container_id):
        """Items *container_id* holds by any spatial relation."""
        graph = self.gs.graph
        for rel in self.REACHABLE_RELATIONS:
            for edge in graph.get_edges_for_target(container_id, rel):
                node = graph.get_node(edge.source)
                if node is not None and node.type == "item":
                    yield node

    def _find_consumable(self, p, tags, depth=1, verb=None):
        """Nearest edible thing the character can actually reach.

        Carried first, then anything the area holds by a spatial relation, then
        ONE level into what those hold. Before this it only looked at items with
        an ``in`` edge to the area, so food in a container — berries on a bush, a
        larder, a basket — was invisible and the background tier could starve
        beside a full store.
        """
        graph = self.gs.graph
        player_id = self.gs._player_node_id(p.name)
        area_id = (self.gs.area_node_id(p.current_area)
                   if p.current_area else None)
        # carried items first
        for e in graph.edges:
            if e.type == EDGE_CARRYING and e.target == player_id:
                node = graph.get_node(e.source)
                if node and self._is_consumable(node, tags, verb):
                    return node
        if not area_id:
            return None
        for node in self._spatial_items(area_id):
            if self._is_consumable(node, tags, verb):
                return node
        if depth > 0:
            for holder in self._spatial_items(area_id):
                for node in self._spatial_items(holder.id):
                    if self._is_consumable(node, tags, verb):
                        return node
        return None

    def _is_consumable(self, node, tags, verb=None):
        """Can this node satisfy the search?

        The tag branch is inherently intent-specific (FOOD_TAGS vs DRINK_TAGS).
        The action branch must be too: it used to accept an item carrying EITHER
        an `eat` or a `drink` action, so a hungry character would eat a water
        skin and Hunger was satisfied.
        """
        props = node.properties or {}
        if props.get("current_state") == "hidden":
            return False
        node_tags = {str(t).lower() for t in (props.get("tags", []) or [])}
        if set(tags) & node_tags:
            return True
        if not verb:
            return False
        actions = props.get("actions", [])
        if isinstance(actions, str):
            actions = [a.strip() for a in actions.split(",")]
        return verb in {str(a).lower() for a in (actions or [])}

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

    def _target_step(self, p, tags, verb=None):
        """Nearest area holding ``tags`` reachable from the character's area.

        Returns ``(area_name, exit_label)`` or None. BFS walks the engine's own
        exits (``include_hidden=True`` so authoring-hidden passages still
        connect), which guarantees the returned label is one
        ``movement.move_to_area`` will accept.
        """
        areas = self._areas_with(tags, verb)
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

    def _areas_with(self, tags, verb=None):
        """Areas from which the character could satisfy this need.

        Reaches into containers exactly like `_find_consumable` does: a berry on
        a bush makes the forest a food area, otherwise nobody would ever travel
        to where the renewed supply actually is.
        """
        key = (tuple(tags), verb)
        if key in self._areas_cache:
            return self._areas_cache[key]
        areas = set()
        want = {str(t).lower() for t in tags}
        for node in self.gs.graph.nodes.values():
            if node.type != "area":
                continue
            # an area can itself be the resource (water sources, larders)
            ntags = {str(t).lower() for t in (node.properties.get("tags", []) or [])}
            if want & ntags:
                areas.add(node.name)
                continue
            for held in self._spatial_items(node.id):
                if self._is_consumable(held, tags, verb):
                    areas.add(node.name)
                    break
                if any(self._is_consumable(inner, tags, verb)
                       for inner in self._spatial_items(held.id)):
                    areas.add(node.name)
                    break
        self._areas_cache[key] = areas
        return areas
