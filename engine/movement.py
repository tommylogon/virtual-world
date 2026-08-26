# engine/movement.py — Movement, door management, and area connectivity extracted from VirtualWorld

import time
from typing import Optional, Dict, Any

from graph import Node, Edge, EDGE_CONNECTION, EDGE_TRIGGERS
from engine.room_perception import normalize_requires
from engine.traits import TraitSystem
from engine.size import size_tier, size_tier_from_name
from engine.conditions import effective_speed

# Movement kind → flavor line. The `time` part of a way's cost is a DURATION
# hint for the future stateful-action system (task-131), not per-action clock
# advancement — the clock advances exactly once per turn for everyone. So
# crawl/climb/jump do NOT scale costs today (task-187).
KIND_MOVE_LINE = {
    "crawl": "You drop to your hands and knees and crawl through the {d}.",
    "climb": "You climb through the {d}.",
    "jump": "You leap across the {d}.",
    "go": "You head through the {d}.",
}


class MovementSystem:
    """Manages player movement between areas, door state toggling,
    area creation and area graph connectivity."""

    def __init__(self, graph, player_manager, trigger_system, toggleable_items, name_matcher, game_state):
        self.graph = graph
        self.player_manager = player_manager
        self.triggers = trigger_system
        self.toggleable_items = toggleable_items
        self.name_matcher = name_matcher
        self.gs = game_state  # Duck-typed VirtualWorld instance

    def _learn_way_aspect(self, way_node, direction: str, aspect: str) -> None:
        """Record that the active character discovered a way's hidden aspect
        (locked / blocked / needs_force) — task-333 scene discovery."""
        player = self.player_manager.get_active_player_obj()
        area = getattr(self.player_manager, "current_area", None)
        if player is not None and area is not None and hasattr(player, "learn_way_aspect"):
            player.learn_way_aspect(area.name, direction, aspect)

    # ────────────────────── Area & Connection Management ──────────────────────

    def add_area(self, area):
        """Add a area node to the graph from a Area object."""
        node_id = self.gs._area_node_id(area.name)
        node = Node(
            id=node_id,
            type="area",
            name=area.name,
            properties={
                "description": area.description,
                "environment": area.environment,
            }
        )
        self.graph.add_node(node)

    def set_current_area(self, area_name: str) -> str:
        """Set the active player's current area. Raises ValueError if area doesn't exist."""
        node = self.graph.get_node(self.gs._area_node_id(area_name))
        if not node:
            raise ValueError(f"Area '{area_name}' does not exist.")
        self.name_matcher._set_player_area(self.gs.active_player, area_name)
        return f"You move into the {area_name}."

    def connect_areas(self, room1_name: str, room2_name: str, dir1: str, dir2: str,
                      state="open", desc="", cost=None, one_way=False):
        """Create a bidirectional connection between two areas via a door node."""
        way_id = self.gs._way_node_id(f"{room1_name}_{dir1}")
        way_node = Node(
            id=way_id,
            type="way",
            name=f"{room1_name}-{dir1}",
            properties={
                "current_state": state,
                "description": desc,
                "cost": cost or {},
            }
        )
        way_node.properties["area_from"] = room1_name
        way_node.properties["area_to"] = room2_name
        if one_way:
            way_node.properties["one_way"] = True
        self.graph.add_node(way_node)

        # Link room1 -> door (direction dir1) and door -> room2
        self.graph.add_edge(Edge(source=self.gs._area_node_id(room1_name), target=way_id,
                                 type=EDGE_CONNECTION, properties={"direction": dir1}))
        self.graph.add_edge(Edge(source=way_id, target=self.gs._area_node_id(room2_name),
                                 type=EDGE_CONNECTION, properties={"direction": dir2}))

        # Link room2 -> door (direction dir2) and door -> room1
        self.graph.add_edge(Edge(source=self.gs._area_node_id(room2_name), target=way_id,
                                 type=EDGE_CONNECTION, properties={"direction": dir2}))
        self.graph.add_edge(Edge(source=way_id, target=self.gs._area_node_id(room1_name),
                                 type=EDGE_CONNECTION, properties={"direction": dir1}))

    def _set_exit_state(self, area_name: str, direction: str, new_state: str):
        """Update the door node's current_state and propagate."""
        area_id = self.gs._area_node_id(area_name)
        # Find the door connected with that direction
        for edge in self.graph.get_edges_for_source(area_id, EDGE_CONNECTION):
            if edge.properties.get("direction") == direction:
                way_node = self.graph.get_node(edge.target)
                if way_node and way_node.type == "way":
                    way_node.properties["current_state"] = new_state
                    # Update timestamp
                    way_node.updated = time.time()
                    self.graph.nodes[way_node.id] = way_node
                    break

    # ────────────────────── Movement ──────────────────────

    def _get_encumbrance_energy_cost(self) -> int:
        """Return extra movement energy cost from carry encumbrance (tiered).

        Tiers:
          < 50% capacity  → 0
          50% – 80%       → +1 energy
          80% – 100%      → +2 energy, dash blocked
          >= 100%         → movement blocked entirely
        """
        player = self.gs.player
        if not player or player.state == "dead":
            return 0
        try:
            ratio_data = self.gs.item_actions.get_carry_load_ratio(self.gs.player_manager)
        except AttributeError:
            return 0
        ratio = ratio_data.get("ratio", 0.0)
        if ratio >= 1.0:
            raise ValueError("You're overencumbered and can't move.")
        if ratio >= 0.8:
            return 2
        if ratio >= 0.5:
            return 1
        return 0

    def move_to_area(self, direction: str, kind: str = "go") -> str:
        """Move the active player through an exit in the given direction.
        Handles door state checks, skill checks for locked/barred ways,
        NPC reactions, area transitions, toggleable item effects, and action costs.

        ``kind`` is the movement mode — ``go`` (default), ``crawl``, ``climb``,
        or ``jump`` (task-187). Crawl-only or tight ways auto-convert ``go``
        to a crawl; climb/jump ways require the matching verb.
        """
        if not self.gs.current_area:
            return "You are in an empty void."
        if self.gs.player.state in ["sleeping", "unconscious", "bound"]:
            raise ValueError(f"You can't move while {self.gs.player.state}.")
        if self.gs.player.state == "dead":
            if not self.gs.ghost_mode:
                raise ValueError("Your body lies still. You can do nothing.")
            # Ghosts can move freely — no physical cost

        if self.gs.player.has_condition("restrained"):
            raise ValueError("You're restrained and can't move. Try to escape first.")
        if self.gs.player.has_condition("grappled"):
            raise ValueError("You're grappled and can't move. Try to escape first.")

        # Prone — only crawl is allowed (catalog movement_mode: "crawl")
        if self.gs.player.has_condition("prone"):
            if kind in ("climb", "jump"):
                raise ValueError("You're prone — you can only crawl.")
            kind = "crawl"

        # Effective speed 0 — too exhausted to move (e.g. exhausted level 6).
        # Dead characters are exempt (ghosts move freely via the check above).
        if self.gs.player.state != "dead" and effective_speed(self.gs.player) <= 0:
            raise ValueError("You're too exhausted to move.")

        # Encumbrance gate — check before area transition so overburdened
        # characters never leave their current area.
        if self.gs.player.state != "dead":
            self._get_encumbrance_energy_cost()

        # Blind navigation — the world is pitch black for the blind character
        # regardless of any light. A plain "go" risks stumbling (→ prone) unless
        # a cane (sensory_aid) steadies them; climb/jump get a steeper DC reduced
        # by the same cane. Led characters don't self-move here (a cooperative
        # grab and drag covers that path).
        blind = self.gs.player.has_condition("blind")
        cane_bonus = 0
        if blind:
            try:
                cane_bonus = self.gs.narration._sensory_aid_bonus(self.gs.active_player)
            except Exception:
                cane_bonus = 0

        area_id = self.gs._get_current_area_id()
        old_area_name = self.gs.current_area.name if self.gs.current_area else None

        # Fuzzy match the direction
        matched_edge, _, matched_handle = self.name_matcher.resolve_exit(area_id, direction)
        way_id = None
        target_area_id = None
        if matched_edge:
            way_id = matched_edge.target
            direction = matched_handle
        if not way_id:
            visible = []
            for edge in self.graph.get_edges_for_source(area_id, EDGE_CONNECTION):
                d = edge.properties.get("direction", edge.target)
                visible.append(d)
            raise ValueError(f"No exit '{direction}'. Visible exits: {', '.join(visible) if visible else 'none'}")

        way_node = self.graph.get_node(way_id)

        if self.gs.active_player and (self.gs.player.state != "dead" or not self.gs.ghost_mode):
            from engine.character_spatial import approach_way
            pid = self.gs._player_node_id(self.gs.active_player)
            approach_way(self.graph, pid, way_id)

        # Frightened way-gate: won't use a feared passage again (source_type "way")
        if self.gs.player.has_condition("frightened"):
            from engine.conditions import frightened_block
            block = frightened_block(
                self.gs.player, "way",
                source_id=way_node.id, source_name=way_node.name,
            )
            if block:
                raise ValueError(block)

        # ── Passage requirements + size gate (task-187) ──
        # normalize_requires single-sources the legacy "none" handling
        # (engine/room_perception.py — same rule the panel uses).
        requires = normalize_requires(way_node.properties.get("requires", ""))
        if requires:
            if kind == "go" and requires == "crawl":
                kind = "crawl"  # auto-crawl crawl-only ways
            elif kind != requires:
                raise ValueError(f"You need to {requires} through the {direction}.")

        max_size = way_node.properties.get("max_size", "") or ""
        if max_size and max_size != "none":
            player_tier = size_tier(self.gs.player)
            max_tier = size_tier_from_name(max_size)
            if player_tier >= max_tier + 2:
                raise ValueError(f"You don't fit through the {direction}.")
            if player_tier > max_tier:
                # Tight fit — a crawl is the only way through.
                if kind not in ("go", "crawl"):
                    raise ValueError(f"You can't {kind} through the {direction} — it's too tight.")
                if kind == "go":
                    kind = "crawl"

        # ── Blind "go" — risk of stumbling and falling prone (unless a cane/guide) ──
        if blind and kind == "go" and requires not in ("jump", "climb", "crawl"):
            p = self.gs.player
            roll = self.gs.roll_dice(1, 20, 0)
            perception = p.skills.get("Perception", 0)
            dc = 12
            if roll + perception + cane_bonus < dc:
                try:
                    self.gs.conditions.apply_condition(self.gs.active_player, "prone", source="stumble")
                except Exception:
                    pass
                raise ValueError(
                    "You stumble blindly in the dark and fall — you're now prone. "
                    "Get back up with 'stand' before moving on. A cane or a guide would help."
                )

        # ── Climb/jump risk — failure fires the way's failure trigger (task-187) ──
        # Blind characters navigate ledges by feel: the DC climbs (a cane offsets it).
        skill_check_msg = ""
        if requires in ("jump", "climb"):
            dc = int(way_node.properties.get(f"{requires}_dc", 12) or 12)
            if blind:
                dc = max(dc, dc + 4 - cane_bonus)
            success, total, msg = self.gs.skill_check("Athletics", dc)
            self.gs.add_log_entry(msg)
            if not success:
                fail_outputs = self.triggers._execute_triggers(
                    way_node, f"on_fail_{requires}", game_state=self.gs
                )
                for out in fail_outputs:
                    self.gs.add_log_entry(out)
                fail_msg = fail_outputs[0] if fail_outputs else f"You fail to {requires} through the {direction}."
                raise ValueError(f"{msg}\n{fail_msg}")
            skill_check_msg = msg + "\n"

        if way_node.properties.get("one_way"):
            source_area = way_node.properties.get("area_from")
            if self.gs.current_area and self.gs.current_area.name != source_area:
                raise ValueError(
                    f"The {direction} is one-way — you can't go back that way."
                )
        state = way_node.properties.get("current_state")
        if state == "locked":
            self._learn_way_aspect(way_node, direction, "locked")
            raise ValueError(f"The {direction} is locked. You need to unlock it first.")
        if state == "blocked":
            self._learn_way_aspect(way_node, direction, "blocked")
            raise ValueError(f"The {direction} is blocked. There's no way through.")
        if state == "closed":
            # Check needs_open door property (checkbox-managed)
            needs_open = way_node.properties.get("needs_open", {})
            if needs_open.get("enabled", False):
                skill = needs_open.get("skill", "Athletics")
                dc = int(needs_open.get("dc", 10))
                success, total, msg = self.gs.skill_check(skill, dc)
                self.gs.add_log_entry(msg)
                if not success:
                    self._learn_way_aspect(way_node, direction, "needs_force")
                    raise ValueError(f"{msg}\nThe {direction} requires effort to open. ({skill} DC {dc}: roll {total})")
                # Skill check passed — auto-open
                skill_check_msg = msg + "\n"
                way_node.properties["current_state"] = "open"
                way_node.updated = time.time()
                self.graph.nodes[way_id] = way_node
                trigger_outputs = self.triggers._execute_triggers(way_node, "on_open")
                for output in trigger_outputs:
                    self.gs.add_log_entry(output)
            else:
                # Check for requires_open trigger edges (conditions that can block passage)
                req_open_triggers = [
                    e for e in self.graph.get_edges_for_source(way_id, EDGE_TRIGGERS)
                    if e.properties.get("trigger_type") == "requires_open"
                ]
                if req_open_triggers:
                    all_pass = True
                    for edge in req_open_triggers:
                        conds = edge.properties.get("conditions", [])
                        for cond in conds:
                            if cond and not self.triggers._evaluate_trigger_condition(cond, way_node):
                                all_pass = False
                                break
                        if not all_pass:
                            fail_msg = edge.properties.get("effect_params", {}).get(
                                "fail_message",
                                f"The {direction} is barred. Something prevents it from opening."
                            )
                            raise ValueError(fail_msg)
                # Default: auto-open the door (player walks through)
                way_node.properties["current_state"] = "open"
                way_node.updated = time.time()
                self.graph.nodes[way_id] = way_node
                trigger_outputs = self.triggers._execute_triggers(way_node, "on_open")
                for output in trigger_outputs:
                    self.gs.add_log_entry(output)

        # Find the area on the other side of the door
        for conn in self.graph.get_edges_for_source(way_id, EDGE_CONNECTION):
            if conn.target != area_id:
                target_area_id = conn.target
                break
        if not target_area_id:
            raise ValueError(f"The {direction} leads nowhere.")

        target_area_node = self.graph.get_node(target_area_id)

        # Trigger NPC behaviors for leaving area
        if self.gs.active_player and old_area_name:
            for pname, p in list(self.gs.players.items()):
                if p.simple_npc and p.state != "dead" and p.current_area == old_area_name:
                    self.gs.npc_behaviors.process_simple_npcs(
                        "on_player_leave_area",
                        {"player_area": old_area_name}
                    )

        # Frightened gates (Phase 3 + source types): won't re-enter a feared
        # area (source_type "area", or legacy untyped sources), and won't enter
        # an area a feared character (source_type "character") is currently in.
        if self.gs.player.has_condition("frightened"):
            from engine.conditions import frightened_block
            block = frightened_block(
                self.gs.player, "area", source_name=target_area_node.name
            )
            if not block:
                # legacy sources (pre-source_type) were area names — keep blocking
                for inst in self.gs.player.conditions.get("frightened", []):
                    if not inst.get("source_type") and inst.get("source") == target_area_node.name:
                        block = f"You're too afraid to go back into the {target_area_node.name}."
                        break
            if not block:
                feared_here = [
                    pname for pname, p in list(self.gs.players.items())
                    if p.state != "dead" and p.current_area == target_area_node.name
                ]
                for inst in self.gs.player.conditions.get("frightened", []):
                    if (inst.get("source_type") == "character"
                            and inst.get("source") in feared_here):
                        block = f"You're too afraid to go into the {target_area_node.name} — {inst['source']} is there."
                        break
            if block:
                raise ValueError(block)

        self.name_matcher._set_player_area(self.gs.active_player, target_area_node.name)

        from engine.character_spatial import set_character_at_way
        if self.gs.active_player and way_id:
            pid = self.gs._player_node_id(self.gs.active_player)
            set_character_at_way(self.graph, pid, way_id)

        # Phase 3 — save_on event hooks: enter_area always; crawl/climb/jump by kind
        try:
            area_tags = target_area_node.properties.get("tags", [])
            for line in self.gs._emit_save_on(
                self.gs.active_player, "enter_area",
                {"source": target_area_node.name, "source_type": "area",
                 "area_tags": area_tags},
            ):
                self.gs.add_log_entry(line)
            if kind == "crawl" and (
                way_node.properties.get("requires") == "crawl"
                or way_node.properties.get("max_size")
            ):
                for line in self.gs._emit_save_on(
                    self.gs.active_player, "crawl_tight_way",
                    {"source": way_node.name, "source_type": "way",
                     "passage_size": way_node.properties.get("max_size")},
                ):
                    self.gs.add_log_entry(line)
            elif kind == "climb":
                for line in self.gs._emit_save_on(
                    self.gs.active_player, "climb_way",
                    {"source": way_node.name, "source_type": "way"},
                ):
                    self.gs.add_log_entry(line)
            elif kind == "jump":
                for line in self.gs._emit_save_on(
                    self.gs.active_player, "jump_way",
                    {"source": way_node.name, "source_type": "way"},
                ):
                    self.gs.add_log_entry(line)
        except Exception:
            pass

        # Drag grappled targets along with the mover (grapple system) — each
        # target may resist with a STR save.
        drag_lines = []
        grapple = getattr(self.gs, "grapple", None)
        if grapple:
            drag_lines = grapple.drag_all(
                self.gs.active_player, target_area_node.name, direction, way_id,
            )
        drag_suffix = ("\n" + "\n".join(drag_lines)) if drag_lines else ""

        # Record turn event: character left old area and entered new area
        if old_area_name:
            self.gs.record_turn_event(
                self.gs.active_player, "move",
                f"left the {old_area_name} through the {direction}",
                area_name=old_area_name
            )
        self.gs.record_turn_event(
            self.gs.active_player, "move",
            f"entered the {target_area_node.name} through the {direction}",
            area_name=target_area_node.name
        )

        # Trigger NPC behaviors for entering new area
        if self.gs.active_player:
            for pname, p in list(self.gs.players.items()):
                if p.simple_npc and p.state != "dead" and p.current_area == target_area_node.name:
                    self.gs.npc_behaviors.process_simple_npcs(
                        "on_player_enter_area",
                        {"player_area": target_area_node.name}
                    )

        # Entertainment boost for area entry
        player = self.gs.player
        area_name = target_area_node.name
        if player and "Entertainment" in player.vitals:
            was_new = area_name not in player.visited_areas
            player.visited_areas.add(area_name)
            if was_new:
                base_boost = 15
                if TraitSystem.has_effect(player, "curious"):
                    base_boost = int(base_boost * 1.5)
                if TraitSystem.has_effect(player, "homebody"):
                    base_boost = 0
                player.vitals["Entertainment"] = min(100, player.vitals.get("Entertainment", 50) + base_boost)
            elif TraitSystem.has_effect(player, "wanderlust"):
                player.vitals["Entertainment"] = min(100, player.vitals.get("Entertainment", 50) + 3)

        # Apply move cost (ghosts get no energy cost). The way's authored cost
        # applies as-is — crawl/climb/jump don't scale it (see KIND_MOVE_LINE).
        if self.gs.player.state != "dead":
            exit_cost = way_node.properties.get("cost", {})
            self.gs.apply_action("move", exit_cost, player=self.gs.player)
            encumbrance_cost = self._get_encumbrance_energy_cost()
            if encumbrance_cost:
                self.gs.apply_action("move", {"energy": encumbrance_cost, "time": 0}, player=self.gs.player)
        # Fire on_enter triggers on the door (e.g., auto-close behind player,
        # fear saves on "fleshy orifice" doors) — game_state so save gates work
        enter_outputs = self.triggers._execute_triggers(
            way_node, "on_enter", game_state=self.gs
        )
        for output in enter_outputs:
            self.gs.add_log_entry(output)
        # Fire on_enter triggers on the area itself (rooms reacting to someone
        # arriving — announcements, atmosphere shifts, encounter gates).
        area_enter_outputs = self.triggers._execute_triggers(
            target_area_node, "on_enter", game_state=self.gs
        )
        for output in area_enter_outputs:
            self.gs.add_log_entry(output)
        auto_close_msg = ""
        if way_node.properties.get("auto_close", False):
            way_node.properties["current_state"] = "closed"
            way_node.updated = time.time()
            self.graph.nodes[way_id] = way_node
            self.gs.add_log_entry(f"The {way_node.name} swings shut behind you.")
            close_outputs = self.triggers._execute_triggers(way_node, "on_close")
            for output in close_outputs:
                self.gs.add_log_entry(output)
            auto_close_msg = f"\nThe {way_node.name} swings shut behind you."

        pass_msg = way_node.properties.get("pass_message", "")
        target_display = target_area_node.properties.get("display_name") or target_area_node.name
        arrival_suffix = f" — you're in {target_display}."
        move_line = KIND_MOVE_LINE.get(kind, "You head through the {d}.").format(d=direction)
        if pass_msg:
            return f"{skill_check_msg}{pass_msg + arrival_suffix + auto_close_msg + drag_suffix}"
        return f"{skill_check_msg}{move_line + arrival_suffix + auto_close_msg + drag_suffix}"

    def crawl_to_area(self, direction: str) -> str:
        """Crawl through a tight/crawl-only passage (2× time)."""
        return self.move_to_area(direction, kind="crawl")

    def climb_to_area(self, direction: str) -> str:
        """Climb through a climbable passage (1.5× time, risk)."""
        return self.move_to_area(direction, kind="climb")

    def jump_to_area(self, direction: str) -> str:
        """Jump across a gap (1× time, risk)."""
        return self.move_to_area(direction, kind="jump")

    def dash_to_area(self, direction: str) -> str:
        """Sprint through one exit — a fast ``go``.

        Dash is the first hop of a burst: the agent engine follows it up
        with an immediate second decision and chains another ``go``, so a
        dash can cross several rooms in one turn. This method only performs
        the single sprint (state checks + movement cost), mirroring
        ``move_to_area`` plus a small sprinting energy surcharge.
        """
        if not self.gs.current_area:
            return "You are in an empty void."
        if self.gs.player.state in ["sleeping", "unconscious", "bound"]:
            raise ValueError(f"You can't dash while {self.gs.player.state}.")
        if self.gs.player.state == "dead" and not self.gs.ghost_mode:
            raise ValueError("Your body lies still. You can do nothing.")

        # Too winded to sprint (prone / exhausted level 3+); ghosts exempt
        if self.gs.player.state != "dead" and effective_speed(self.gs.player) < 0.5:
            raise ValueError("You're too winded to sprint.")

        # Heavy encumbrance blocks dash
        if self.gs.player.state != "dead":
            encumbrance_cost = self._get_encumbrance_energy_cost()
            if encumbrance_cost >= 2:
                raise ValueError("You're too heavily encumbered to sprint.")

        hop = self.move_to_area(direction)

        # Scaled energy surcharge for sprinting (beyond the normal exit cost)
        if self.gs.player.state != "dead":
            self.gs.apply_action("move", {"energy": 4, "time": 0}, player=self.gs.player)
        return hop

    # ────────────────────── Way Toggling ──────────────────────

    def _open_passage_block(self, way_node, action: str, label: str):
        """Reason a way can't be opened/closed by a character, or None.

        Traversal-only ways (requires jump/climb/crawl — task-223) have no
        door to swing: task-187 means they exist to be crossed, not toggled.
        The author-facing ``prevent_close`` flag likewise pins a passage open.
        Triggers/authoring write ``current_state`` directly and never route
        through here, so they keep working.
        """
        if not way_node:
            return None
        props = way_node.properties or {}
        requires = normalize_requires(props.get("requires")).lower()
        if requires in ("jump", "climb", "crawl"):
            return (
                f"You can't {action} the {label} — it's an open {requires} "
                f"passage, not something you open or close."
            )
        if props.get("prevent_close") and action == "close":
            return f"You can't close the {label} — this opening is permanent."
        return None

    def toggle_way(self, direction: str, action: str = "open") -> str:
        """Open or close a door in the given direction. Validates player state,
        checks for locked/blocked/broken ways, and fires door triggers."""
        if not self.gs.current_area or self.gs.player.state in ["sleeping", "unconscious", "bound"]:
            raise ValueError(f"You can't do that while {self.gs.player.state}.")
        if self.gs.player.state == "dead":
            if not self.gs.ghost_mode:
                raise ValueError("Your body lies still. You can do nothing.")
            # Ghosts need wisdom check to interact with physical objects
            success, _, msg = self.gs.skill_check("Perception", 15)
            if not success:
                return f"Your ghostly hands pass right through the {direction}. You can't grasp it."
            # Ghost succeeded — proceed with toggle but note the ethereal nature

        area_id = self.gs._get_current_area_id()

        # Fuzzy match the direction
        matched_edge, _, matched_handle = self.name_matcher.resolve_exit(area_id, direction)
        way_id = None
        way_edge = None
        if matched_edge:
            way_edge = matched_edge
            way_id = matched_edge.target
            direction = matched_handle
        if not way_id:
            exits = []
            for edge in self.graph.get_edges_for_source(area_id, EDGE_CONNECTION):
                direction_name = edge.properties.get("direction", "?")
                way_ref = self.graph.get_node(edge.target)
                if way_ref:
                    state = way_ref.properties.get("current_state", "unknown")
                    exits.append(f"{direction_name} ({state})")
            raise ValueError(
                f"You can't go to '{direction}' — don't see an exit that way. "
                f"Available exits: {', '.join(exits) if exits else 'none you can see'}."
            )
        way_node = self.graph.get_node(way_id)
        current_state = way_node.properties["current_state"]

        from engine.character_spatial import approach_way
        if self.gs.active_player and (self.gs.player.state != "dead" or not self.gs.ghost_mode):
            pid = self.gs._player_node_id(self.gs.active_player)
            approach_way(self.graph, pid, way_id)

        block = self._open_passage_block(way_node, action, direction)
        if block:
            raise ValueError(block)

        if current_state == "locked":
            raise ValueError(f"The {direction} is locked. Try using a key on it.")
        if current_state == "blocked":
            raise ValueError(f"The {direction} is blocked.")
        if current_state == "broken":
            raise ValueError(f"The {direction} is broken.")

        new_state = "open" if action == "open" else "closed"
        if current_state == new_state:
            return f"The {direction} is already {current_state}."
        way_node.properties["current_state"] = new_state
        way_node.updated = time.time()
        self.graph.nodes[way_id] = way_node
        if self.gs.player.state != "dead":
            self.gs.apply_action(action, way_node.properties.get("cost", {}), player=self.gs.player)
        # Fire door triggers
        trigger_type = "on_open" if new_state == "open" else "on_close"
        trigger_outputs = self.triggers._execute_triggers(way_node, trigger_type)
        for output in trigger_outputs:
            self.gs.add_log_entry(output)
        # Record turn event
        area_name = self.gs.current_area.name if self.gs.current_area else None
        self.gs.record_turn_event(self.gs.active_player, action, f"{action}ed the {direction}", area_name=area_name)
        ghost_prefix = "With an ethereal effort, " if self.gs.player.state == "dead" else ""
        result = f"{ghost_prefix}You {action} the {direction}."
        if new_state == "open" and way_edge:
            vid = way_edge.properties.get("visible_in_direction", "")
            if vid:
                result += f"\n{vid}"
        return result

    def toggle_way_by_id(self, way_id: str, action: str = "open") -> str:
        """Open or close a door by its graph node ID (not direction)."""
        way_node = None
        way_id_lower = way_id.lower()
        for node_id, node in self.graph.nodes.items():
            if node_id.lower() == way_id_lower and node.type == "way":
                way_node = node
                way_id = node_id  # Use the original-cased ID
                break
        if not way_node:
            raise ValueError(f"Way '{way_id}' not found.")
        from engine.character_spatial import approach_way
        if self.gs.active_player and (self.gs.player.state != "dead" or not self.gs.ghost_mode):
            pid = self.gs._player_node_id(self.gs.active_player)
            approach_way(self.graph, pid, way_id)
        current_state = way_node.properties.get("current_state", "closed")

        way_label = way_node.name or way_id
        block = self._open_passage_block(way_node, action, way_label)
        if block:
            raise ValueError(block)

        if current_state == "locked":
            raise ValueError(f"The {way_id} is locked. Try using a key on it.")
        if current_state == "blocked":
            raise ValueError(f"The {way_id} is blocked.")
        if current_state == "broken":
            raise ValueError(f"The {way_id} is broken.")
        new_state = "open" if action == "open" else "closed"
        if current_state == new_state:
            return f"The {way_id} is already {current_state}."
        way_node.properties["current_state"] = new_state
        way_node.updated = time.time()
        self.graph.nodes[way_id] = way_node
        # Fire door triggers
        trigger_type = "on_open" if new_state == "open" else "on_close"
        trigger_outputs = self.triggers._execute_triggers(way_node, trigger_type)
        for output in trigger_outputs:
            self.gs.add_log_entry(output)
        ghost_prefix = ""
        if self.gs.player.state == "dead":
            ghost_prefix = "With an ethereal effort, "
        self.gs.record_turn_event(self.gs.active_player, action, f"{action}ed door {way_id}")
        result = f"{ghost_prefix}You {action} {way_id}."
        if new_state == "open":
            area_id = self.gs._get_current_area_id()
            for edge in self.graph.get_edges_for_source(area_id, EDGE_CONNECTION):
                if edge.target == way_id:
                    vid = edge.properties.get("visible_in_direction", "")
                    if vid:
                        result += f"\n{vid}"
                    break
        return result
