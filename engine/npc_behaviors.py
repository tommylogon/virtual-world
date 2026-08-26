# engine/npc_behaviors.py — NPC behavior and AI hunting system extracted from VirtualWorld

import random
import time
from collections import deque
from typing import Optional, Dict, List, Any

from graph import EDGE_CONNECTION


class NPCBehaviorSystem:
    """Manages simple NPC behaviors (wander/flee/stationary), behavior-tree evaluation,
    and AI-driven hunting (BFS pathfinding toward players)."""

    def __init__(self, graph, player_manager, trigger_system, game_state):
        self.graph = graph
        self.player_manager = player_manager
        self.triggers = trigger_system
        self.gs = game_state  # Duck-typed VirtualWorld instance

    # ────────────────────── Simple NPC Processing ──────────────────────

    def process_npcs_on_combat(self, context: dict = None):
        """Process NPC reactions to combat events."""
        pass  # Stub — NPC combat reactions go here.

    def process_simple_npcs(self, trigger_type="on_tick", extra_context=None):
        """Process simple NPC behaviors and legacy wander/flee.

        Called from tick_turn() every tick, and from game commands with specific trigger types.
        """
        for pname, player in list(self.gs.players.items()):
            if not player.simple_npc:
                continue
            if player.state == "dead":
                continue
            # Busy/sleeping simple NPCs don't act (task-131)
            if player.state in ("sleeping", "unconscious"):
                continue
            if getattr(player, 'activity', None) and player.activity.get("type") in (
                "sleeping", "resting", "waiting", "meditating",
                "bathing", "sitting", "lying down",
            ):
                continue

            behaviors = getattr(player, 'behaviors', [])
            acted = False

            # Build context
            player_obj = self.gs.player
            player_area = player_obj.current_area if player_obj else None
            context = {
                "npc": player,
                "npc_state": getattr(player, 'npc_state', 'idle'),
                "npc_area": player.current_area,
                "state_enter_tick": getattr(player, 'state_enter_tick', 0),
                "current_tick": self.gs.time_ticks,
                "player": player_obj,
                "player_area": player_area,
            }
            if extra_context:
                context.update(extra_context)

            # Evaluate behaviors sorted by priority (higher first)
            sorted_behaviors = sorted(behaviors, key=lambda b: -b.get("priority", 0))
            for behavior in sorted_behaviors:
                b_trigger = behavior.get("trigger")
                if b_trigger and b_trigger != trigger_type:
                    continue
                interval = behavior.get("interval", 1)
                if interval > 1 and self.gs.time_ticks % interval != 0:
                    continue
                conditions = behavior.get("conditions", {})
                if conditions and not self.triggers._evaluate_conditions(
                    conditions, context, game_state=self.gs
                ):
                    continue
                actions = behavior.get("actions", [])
                if actions:
                    outputs = self.triggers._execute_behavior_actions(
                        pname, actions, game_state=self.gs
                    )
                    for output in outputs:
                        self.gs.add_log_entry(output)
                        self.gs.record_turn_event(pname, "npc_behavior", output, area_name=player.current_area)
                    acted = True

            # Legacy fallback (only in on_tick context)
            if not acted and trigger_type == "on_tick":
                interval = getattr(player, 'npc_action_interval', 3)
                if self.gs.time_ticks % interval != 0:
                    continue
                behavior = getattr(player, 'npc_behavior', 'wander')
                if behavior == "stationary":
                    continue
                elif behavior == "wander":
                    area = player.current_area
                    if not area:
                        continue
                    exits = self.gs._build_exits_for_area(area)
                    open_exits = {direction: ex for direction, ex in exits.items() if ex.get("state") == "open"}
                    if not open_exits:
                        continue
                    direction = random.choice(list(open_exits.keys()))
                    old_active = self.gs.active_player
                    self.gs.active_player = pname
                    try:
                        result = self.gs.movement.move_to_area(direction)
                        msg = f"[NPC] {pname} wanders {direction} to {player.current_area}."
                        self.gs.add_log_entry(msg)
                        self.gs.record_turn_event(pname, "move", msg, area_name=player.current_area)
                    except ValueError:
                        pass
                    finally:
                        self.gs.active_player = old_active
                elif behavior == "flee":
                    area = player.current_area
                    if not area:
                        continue
                    threat_nearby = False
                    for other_name, other in self.gs.players.items():
                        if other_name == pname:
                            continue
                        if other.current_area == area and not other.simple_npc and other.state != "dead":
                            threat_nearby = True
                            break
                    if not threat_nearby:
                        continue
                    exits = self.gs._build_exits_for_area(area)
                    open_exits = {direction: ex for direction, ex in exits.items() if ex.get("state") == "open"}
                    if not open_exits:
                        continue
                    direction = random.choice(list(open_exits.keys()))
                    old_active = self.gs.active_player
                    self.gs.active_player = pname
                    try:
                        result = self.gs.movement.move_to_area(direction)
                        msg = f"[NPC] {pname} flees {direction} from a threat."
                        self.gs.add_log_entry(msg)
                        self.gs.record_turn_event(pname, "move", msg, area_name=player.current_area)
                    except ValueError:
                        pass
                    finally:
                        self.gs.active_player = old_active

    # ────────────────────── Behavior `go` action ──────────────────────

    def execute_go_action(self, char_name: str, action: dict) -> Optional[str]:
        """Move an NPC one step via ways (goto/random/patrol). Returns log text."""
        player = self.gs.players.get(char_name)
        if not player or not player.current_area:
            return None

        mode = (action.get("mode") or "goto").lower()
        if mode == "random":
            return self._go_random(char_name, player)
        if mode == "patrol":
            return self._go_patrol(char_name, player, action)
        target_area = action.get("area") or action.get("room") or ""
        return self._go_toward_area(char_name, player, target_area)

    def _resolve_area_name(self, area_name: str) -> Optional[str]:
        if not area_name:
            return None
        needle = str(area_name).strip().lower()
        for node in self.graph.nodes.values():
            if node.type == "area" and node.name.lower() == needle:
                return node.name
        return None

    def _go_toward_area(self, char_name: str, player, target_area_name: str) -> str:
        resolved = self._resolve_area_name(target_area_name)
        if not resolved:
            return f"[{char_name}] cannot find area '{target_area_name}'."

        if player.current_area == resolved:
            return f"[{char_name}] is already in {resolved}."

        direction = self._get_path_to_area(player.current_area, resolved)
        if not direction:
            return f"[{char_name}] cannot find a path to {resolved}."

        old_active = self.gs.active_player
        self.gs.active_player = char_name
        old_area = player.current_area
        try:
            self.gs.movement.move_to_area(direction)
            new_area = player.current_area
            return (
                f"[{char_name}] goes {direction} "
                f"({old_area} → {new_area})."
            )
        except ValueError as err:
            first_line = str(err).split("\n", 1)[0]
            return f"[{char_name}] tries {direction} but cannot: {first_line}"
        finally:
            self.gs.active_player = old_active

    def _go_random(self, char_name: str, player) -> str:
        area = player.current_area
        exits = self.gs._build_exits_for_area(area)
        open_exits = {
            direction: ex
            for direction, ex in exits.items()
            if ex.get("state") == "open"
        }
        if not open_exits:
            return f"[{char_name}] has nowhere to go from {area}."

        direction = random.choice(list(open_exits.keys()))
        old_active = self.gs.active_player
        self.gs.active_player = char_name
        old_area = player.current_area
        try:
            self.gs.movement.move_to_area(direction)
            return (
                f"[{char_name}] wanders {direction} "
                f"({old_area} → {player.current_area})."
            )
        except ValueError as err:
            first_line = str(err).split("\n", 1)[0]
            return f"[{char_name}] tries {direction} but cannot: {first_line}"
        finally:
            self.gs.active_player = old_active

    def _go_patrol(self, char_name: str, player, action: dict) -> str:
        areas_str = action.get("areas", "")
        if areas_str:
            parsed = [
                self._resolve_area_name(part) or part.strip()
                for part in str(areas_str).split(",")
                if part.strip()
            ]
            if parsed:
                existing = list(getattr(player, "patrol_route", None) or [])
                if existing != parsed:
                    player.patrol_route = parsed
                    player.patrol_index = 0
                elif not existing:
                    player.patrol_route = parsed

        route = getattr(player, "patrol_route", None) or []
        if not route:
            return f"[{char_name}] has no patrol route."

        idx = int(getattr(player, "patrol_index", 0)) % len(route)
        target = self._resolve_area_name(route[idx]) or route[idx]

        if player.current_area == target:
            player.patrol_index = (idx + 1) % len(route)
            next_target = self._resolve_area_name(route[player.patrol_index]) or route[player.patrol_index]
            return f"[{char_name}] reached patrol point {target}; next: {next_target}."

        msg = self._go_toward_area(char_name, player, target)
        if player.current_area == target:
            player.patrol_index = (idx + 1) % len(route)
        return msg

    # ────────────────────── Hunt System ──────────────────────

    def hunt(self, hunter_name: str, target_name: str = None) -> str:
        """Agent-facing hunt command. Uses BFS to find a path to the nearest living player
        and returns the next direction to move. The agent must call 'go [direction]' to move.
        If target_name is given, hunts that specific player."""
        hunter = self.gs.players.get(hunter_name)
        if not hunter or not hunter.current_area:
            return ""

        if not target_name:
            target_name = self._get_nearest_player_to(hunter_name)

        if not target_name:
            return f"{hunter_name} sniffs the air but smells no one nearby."

        target = self.gs.players.get(target_name)
        if not target or not target.current_area:
            return f"{hunter_name} cannot find the target."

        if hunter.current_area == target.current_area:
            return f"{hunter_name} is in the same area as {target_name}! Attack!"

        # Get path
        direction = self._get_path_to_area(hunter.current_area, target.current_area)
        if not direction:
            return f"{hunter_name} growls in frustration, unable to find a path."

        return f"{hunter_name} senses {target_name} to the {direction}. {direction} is the way."

    def slasher_hunt(self, slasher_name: str) -> str:
        """AI-driven hunt action for a slasher character.
        Finds the nearest living player and starts moving toward them.
        Returns a description of what the slasher does."""
        hunter = self.gs.players.get(slasher_name)
        if not hunter:
            return ""

        target_name = self._get_nearest_player_to(slasher_name)
        if not target_name:
            return ""

        target = self.gs.players.get(target_name)
        if not target or not target.current_area:
            return ""

        if hunter.current_area == target.current_area:
            # Same area — attack! (combat.player_attack via facade delegate)
            return self.gs.player_attack(slasher_name, target_name)

        # Try to move toward the target
        direction = self._get_path_to_area(hunter.current_area, target.current_area)
        if not direction:
            return ""

        # Attempt movement (bypass normal move logic for the AI)
        area_id = self.gs._area_node_id(hunter.current_area)
        way_id = None
        for edge in self.graph.get_edges_for_source(area_id, EDGE_CONNECTION):
            if edge.properties.get("direction") == direction:
                way_id = edge.target
                break

        if not way_id:
            return f"{slasher_name} prowls the area, searching."

        way_node = self.graph.get_node(way_id)
        if way_node and way_node.type == "way":
            if way_node.properties.get("one_way"):
                source_area = way_node.properties.get("area_from")
                if hunter.current_area != source_area:
                    return f"{slasher_name} snarls at the {direction} but can't go that way — the passage is one-way."
            if way_node.properties.get("current_state") in ("closed",):
                # Slasher can force open closed ways
                way_node.properties["current_state"] = "open"
                way_node.updated = time.time()

            # Find target area
            for conn in self.graph.get_edges_for_source(way_id, EDGE_CONNECTION):
                if conn.target != area_id:
                    target_area_node = self.graph.get_node(conn.target)
                    if target_area_node:
                        old_area = hunter.current_area
                        self.gs.name_matcher._set_player_area(slasher_name, target_area_node.name)
                        self.gs.record_turn_event(
                            slasher_name, "move",
                            f"moved from the {old_area} to the {target_area_node.name}, hunting.",
                            area_name=target_area_node.name
                        )
                        return f"{slasher_name} moves through the {direction}, closer to {target_name}."

        return f"{slasher_name} pauses, listening."

    # ────────────────────── Pathfinding ──────────────────────

    def get_path_to(self, from_area: str, to_area: str) -> Optional[str]:
        """Public API: find the first direction to move from from_area to reach to_area.
        Returns direction name or None if no path exists."""
        return self._get_path_to_area(from_area, to_area)

    def _get_nearest_player_to(self, hunter_name: str) -> Optional[str]:
        """Find the nearest living player to the hunter, using BFS through area connections.
        Returns the target player's name, or None if no one is reachable/alive."""
        hunter = self.gs.players.get(hunter_name)
        if not hunter or not hunter.current_area:
            return None

        # Get all alive, non-slasher players
        targets = [
            pname for pname, player in self.gs.players.items()
            if player.state not in ("dead",)
            and pname != hunter_name
            and not self.player_manager.is_slasher(pname)
        ]

        if not targets:
            return None

        # BFS from hunter's area
        start_area = hunter.current_area
        visited = {start_area}
        queue = deque([(start_area, 0)])  # (area_name, distance)
        area_to_target = {}

        for target_name in targets:
            target_player = self.gs.players[target_name]
            if target_player.current_area:
                area_to_target[target_player.current_area] = target_name

        while queue:
            current_area, dist = queue.popleft()

            if current_area in area_to_target:
                return area_to_target[current_area]

            # Explore connected areas
            area_id = self.gs._area_node_id(current_area)
            for edge in self.graph.get_edges_for_source(area_id, EDGE_CONNECTION):
                way_node = self.graph.get_node(edge.target)
                if way_node and way_node.type == "way":
                    if way_node.properties.get("current_state") in ("open", "closed"):
                        if way_node.properties.get("one_way"):
                            source_name = way_node.properties.get("area_from", "")
                            source_id = self.gs._area_node_id(source_name) if source_name else None
                            if area_id != source_id:
                                continue
                        # Check the other side
                        for conn in self.graph.get_edges_for_source(way_node.id, EDGE_CONNECTION):
                            if conn.target != area_id:
                                other_area_node = self.graph.get_node(conn.target)
                                if other_area_node and other_area_node.name not in visited:
                                    visited.add(other_area_node.name)
                                    queue.append((other_area_node.name, dist + 1))

        return None

    def _get_path_to_area(self, from_area: str, to_area: str) -> Optional[str]:
        """Find the first exit direction to take to eventually reach to_area from from_area.
        Returns the direction (exit name) or None if no path exists."""
        if from_area == to_area:
            return None

        area_id = self.gs._area_node_id(from_area)
        target_id = self.gs._area_node_id(to_area)

        # BFS from source area to target, tracking first step
        visited = {area_id}
        queue = deque([(area_id, None)])  # (current_node_id, first_exit_to_take)

        while queue:
            current_id, first_exit = queue.popleft()

            if current_id == target_id:
                return first_exit

            # Find connected areas through ways
            for edge in self.graph.get_edges_for_source(current_id, EDGE_CONNECTION):
                way_node = self.graph.get_node(edge.target)
                if way_node and way_node.type == "way":
                    if way_node.properties.get("current_state") in ("open", "closed"):
                        if way_node.properties.get("one_way"):
                            source_name = way_node.properties.get("area_from", "")
                            source_id = self.gs._area_node_id(source_name) if source_name else None
                            if current_id != source_id:
                                continue
                        for conn in self.graph.get_edges_for_source(way_node.id, EDGE_CONNECTION):
                            if conn.target != current_id:
                                if conn.target not in visited:
                                    visited.add(conn.target)
                                    next_exit = first_exit or edge.properties.get("direction", "")
                                    queue.append((conn.target, next_exit))

        return None
