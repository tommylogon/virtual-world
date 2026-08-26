"""Grapple system: grab, drag, escape, and release mechanics.

A character can ``grab`` another in the same area. Two things happen:

1. A **``grappled`` edge** (grappler node → target node) records WHO holds whom —
   the single source of truth for the relationship, queryable in both directions.
2. The target gets the **``grappled`` condition** for the mechanical effects
   (blocks movement, attack/defense mods, ``ends_on: ["escape"]``).

When the grappler moves (``go``/``dash``), each grappled target is dragged along
unless they resist with a skill save. Grappled characters can attempt to escape
on their own turn (``escape``/``struggle``); the grappler can ``release`` a
target (or all).

Grapplers have hands: they can hold at most one target per hand (two by
default, one if ``one_armed``/``disable_slot``). Each target already held makes
grabbing another harder — the resist DC climbs by ``+2`` per extra target.

All resist checks go through ``SkillSystem.saving_throw`` (task-159) and
surface in the event stream as ``[Save] ... vs DC ...``.
"""

from typing import List, Optional

from graph import EDGE_GRAPPLED, Edge

#: Base DC to resist a grappler's grip; the grappler's Athletics skill and the
#: relationship modifier are added on top (task: dynamic grapple).
GRAPPLE_SAVE_BASE_DC = 10
#: Base DC for grapple checks (task: dynamic grapple).
GRAPPLE_BASE_DC = 10
#: Relationship modifier per 25 closeness levels (positive = friend, negative = enemy).
#: Friends lower the DC (easier to grab / escape), enemies raise it.
GRAPPLE_REL_PER_LEVEL = 2
#: Extra resist DC per target already held by the grappler.
GRAPPLE_EXTRA_TARGET_DC = 2
#: Clamp relationship modifier to this range.
GRAPPLE_REL_MIN = -8
GRAPPLE_REL_MAX = 8


class GrappleSystem:
    def __init__(self, graph, player_manager, skills, name_matcher, game_state):
        self.graph = graph
        self.player_manager = player_manager
        self.skills = skills
        self.name_matcher = name_matcher
        self.gs = game_state

    # ─────────────────────────── Helpers ───────────────────────────

    def _athletics(self, player) -> int:
        """The player's Athletics skill value (0 if unknown)."""
        return (player.skills or {}).get("Athletics", 0)

    def _best_escape_skill(self, player) -> int:
        """The player's best escape skill — max of Athletics / Acrobatics."""
        skills = player.skills or {}
        return max(skills.get("Athletics", 0), skills.get("Acrobatics", 0))

    def _relationship_mod(self, target_name: str, grappler_name: str) -> int:
        """Linear relationship modifier for grapple checks.

        Positive closeness (friend) lowers the DC by 2 per 25 levels.
        Negative closeness (enemy) raises the DC by 2 per 25 levels.
        Clamped to [-8, +8].
        """
        closeness = self._closeness(target_name, grappler_name)
        mod = -(closeness // 25) * GRAPPLE_REL_PER_LEVEL
        return max(GRAPPLE_REL_MIN, min(GRAPPLE_REL_MAX, mod))

    def _grab_dc(self, grappler_name: str, target_name: str) -> int:
        """DC for a grab check: 10 + grabber_athletics + rel + extra - target_best_escape_skill."""
        target = self.player_manager.players.get(target_name)
        grappler = self.player_manager.players.get(grappler_name)
        held = self._grappling_targets(grappler_name)
        extra = len(held) * GRAPPLE_EXTRA_TARGET_DC
        rel = self._relationship_mod(target_name, grappler_name)
        grabber_ath = self._athletics(grappler) if grappler else 0
        target_skill = self._best_escape_skill(target) if target else 0
        return max(2, GRAPPLE_BASE_DC + grabber_ath + rel + extra - target_skill)

    def _escape_dc(self, player_name: str) -> int:
        """DC for an escape check: 10 + grabber_athletics + rel - extra - target_best_escape_skill.

        Extra targets held by the grabber LOWER the escape DC (each additional person
        means less grip strength per person).
        """
        player = self.player_manager.players.get(player_name)
        grappler_name = self._grappler_of(player_name)
        if not grappler_name:
            return GRAPPLE_BASE_DC
        grappler = self.player_manager.players.get(grappler_name)
        held = self._grappling_targets(grappler_name)
        extra = len(held) * GRAPPLE_EXTRA_TARGET_DC
        rel = self._relationship_mod(player_name, grappler_name)
        grabber_ath = self._athletics(grappler) if grappler else 0
        target_skill = self._best_escape_skill(player) if player else 0
        return max(2, GRAPPLE_BASE_DC + grabber_ath + rel - extra - target_skill)

    def _closeness(self, target_name: str, grappler_name: str) -> int:
        """Target's relationship closeness toward the grappler (0 = unknown)."""
        target = self.player_manager.players.get(target_name)
        if not target:
            return 0
        return (target.relationships or {}).get(grappler_name, {}).get("closeness", 0)

    def _grappler_grab_check(self, grappler_name: str, dc: int) -> tuple:
        """Grappler-side grab attempt (grappler rolls d20+Athletics vs DC)."""
        grappler = self.player_manager.players.get(grappler_name)
        mod = self._athletics(grappler)
        roll = self.skills.roll_dice(1, 20, 0)
        total = roll + mod
        success = total >= dc
        message = (
            f"[Grab] Athletics vs DC {dc}: roll {roll} + {mod} = {total} => "
            f"{'success' if success else 'failure'}"
        )
        self.gs.add_log_entry(message)
        return (success, total, message)

    def _player_node_id(self, player_name: str) -> str:
        """Graph node id for a player."""
        return self.player_manager.get_player_node_id(player_name)

    def _grappling_targets(self, grappler_name: str) -> List[str]:
        """Names of players currently held by *grappler_name*.

        Source of truth: the ``grappled`` edge (grappler node → target node).
        """
        grappler_node = self._player_node_id(grappler_name)
        names = []
        for edge in self.graph.get_edges_for_source(grappler_node, EDGE_GRAPPLED):
            node = self.graph.get_node(edge.target)
            if node and node.type == "character":
                names.append(node.name)
        return names

    def _grappled_targets(self, grappler_name: str) -> List[str]:
        """Alias — see _grappling_targets (edge-driven)."""
        return self._grappling_targets(grappler_name)

    def _grappler_of(self, target_name: str) -> Optional[str]:
        """Who holds *target_name* (None if nobody). Edge-driven lookup."""
        target_node = self._player_node_id(target_name)
        for edge in self.graph.get_edges_for_target(target_node, EDGE_GRAPPLED):
            node = self.graph.get_node(edge.source)
            if node and node.type == "character":
                return node.name
        return None

    def _free_hands(self, grappler_name: str) -> int:
        """Number of hands a grappler can hold targets with (2 default, 1 one-armed)."""
        grappler = self.player_manager.players.get(grappler_name)
        hands = 2
        if grappler:
            try:
                from engine.traits import TraitSystem
                disabled = TraitSystem.get_disabled_slots(grappler)
                if "hand_right" in disabled:
                    hands -= 1
                if "hand_left" in disabled:
                    hands -= 1
            except Exception:
                pass
        return max(0, hands)

    def _add_edge(self, grappler_name: str, target_name: str) -> None:
        """Create the grappled edge (grappler → target)."""
        source = self._player_node_id(grappler_name)
        target = self._player_node_id(target_name)
        existing = self.graph.get_edges_for_source(source, EDGE_GRAPPLED)
        if any(e.target == target for e in existing):
            return
        self.graph.add_edge(Edge(source=source, target=target, type=EDGE_GRAPPLED))

    def _remove_edge(self, grappler_name: str, target_name: str) -> None:
        """Delete the grappled edge (grappler → target)."""
        source = self._player_node_id(grappler_name)
        target = self._player_node_id(target_name)
        self.graph.remove_edge(source, target, EDGE_GRAPPLED)

    def _release_target(self, grappler_name: str, target_name: str) -> None:
        """Symmetric cleanup: drop the edge + clear the target's condition."""
        self._remove_edge(grappler_name, target_name)
        target = self.player_manager.players.get(target_name)
        if target:
            target.remove_condition("grappled")

    def sync(self) -> None:
        """Edge ⇔ condition reconcile (edge is authoritative for WHO).

        - Legacy ``grappling`` condition instances → dropped (edges replace them).
        - ``grappled`` condition with no matching edge → orphan, cleared.
        - ``grappled`` edge whose target lacks the condition → condition re-added.
        """
        players = self.player_manager.players
        # Drop legacy grappling conditions entirely — edges are the tracking now.
        for player in players.values():
            if "grappling" in player.conditions:
                del player.conditions["grappling"]
        # Orphans: condition present but no edge.
        for pname, player in list(players.items()):
            if player.has_condition("grappled") and self._grappler_of(pname) is None:
                player.remove_condition("grappled")
        # Desync repair: edge present but condition missing → re-add condition.
        for grappler_name in list(players.keys()):
            for held in self._grappling_targets(grappler_name):
                target = players.get(held)
                if target and not target.has_condition("grappled"):
                    target.add_condition("grappled")

    def release(self, grappler_name: str, target_name: str = "") -> str:
        """Let go of *target_name* (or everyone if no name given)."""
        targets = self._grappling_targets(grappler_name)
        if not targets:
            return "You aren't holding anyone."
        if target_name:
            if target_name not in targets:
                return f"You aren't holding {target_name}."
            self._release_target(grappler_name, target_name)
            return f"You let go of {target_name}."
        for held in list(targets):
            self._release_target(grappler_name, held)
        return f"You release everyone you were holding ({', '.join(targets)})."

    def release_all_for(self, grappler_name: str) -> None:
        """Drop everyone held (used when the grappler is incapacitated)."""
        for held in list(self._grappling_targets(grappler_name)):
            self._release_target(grappler_name, held)

    # ─────────────────────────── Actions ───────────────────────────

    def grab(self, grappler_name: str, target_name: str) -> str:
        """Grab *target_name*.

        Mechanics (task: dynamic grapple):
        - The grappler always rolls a grab check: d20 + Athletics vs DC.
        - DC = 10 + grabber_athletics + rel + extra - target_best_escape_skill.
          (target's skill makes them harder to grab, so it lowers the DC).
        - Friends lower the DC (easier grab), enemies raise it (harder grab).
        - Each target already held ADDS to the DC (grabbing a third person while
          already holding two is harder).
        - The grappler needs a free hand.
        """
        target = self.player_manager.players.get(target_name)
        if not target:
            return f"You can't grab {target_name}."
        if target.has_condition("grappled"):
            return f"{target_name} is already grappled."
        if target_name == grappler_name:
            return "You can't grab yourself."

        held = self._grappling_targets(grappler_name)
        if len(held) >= self._free_hands(grappler_name):
            hands = self._free_hands(grappler_name)
            return (
                f"Your hands are full — you're already holding {len(held)} "
                f"people ({hands} hand{'s' if hands != 1 else ''}). "
                f"Release someone first."
            )

        dc = self._grab_dc(grappler_name, target_name)
        success, total, msg = self._grappler_grab_check(grappler_name, dc)
        if not success:
            return f"Your fingers slip — you miss grabbing {target_name}. ({msg})"

        self._add_edge(grappler_name, target_name)
        target.add_condition("grappled")
        from engine.character_spatial import approach_character
        approach_character(self.graph, self.gs, target_name, actor_name=grappler_name)
        self.gs.add_log_entry(f"{grappler_name} grabs {target_name}!")
        return f"You grab hold of {target_name}. They're grappled and can't move on their own. ({msg})"

    def lead(self, guide_name: str, target_name: str) -> str:
        """Cooperatively lead *target_name* by the hand (e.g. a blind character).

        Unlike ``grab`` there is no resisted roll — the target consents, so the
        grip lands at the minimum DC and always succeeds. The target is grappled
        (edge + condition) and positioned *beside* the guide, which lets
        ``drag_all`` pull them along as the guide moves.
        """
        target = self.player_manager.players.get(target_name)
        if not target:
            return f"You can't lead {target_name}."
        if target_name == guide_name:
            return "You can't lead yourself."
        if target.has_condition("grappled") and self._grappler_of(target_name):
            return f"{target_name} is already being held."
        held = self._grappling_targets(guide_name)
        if len(held) >= self._free_hands(guide_name):
            return "Your hands are full — release someone first."

        self._add_edge(guide_name, target_name)
        target.add_condition("grappled")
        from engine.character_spatial import approach_character
        approach_character(self.graph, self.gs, target_name, actor_name=guide_name)
        self.gs.add_log_entry(f"{guide_name} takes {target_name}'s hand and leads them.")
        return f"You take {target_name} by the hand and lead them — they go along willingly. Move to drag them with you."

    def escape(self, player_name: str) -> str:
        """Attempt to break free of whoever is grappling *player_name*.

        The grappled player rolls their best of Athletics / Acrobatics.
        DC = 10 + grabber's Athletics + relationship modifier + extra_target_penalty
             - target's best escape skill.
        Friends escape easily (low DC), enemies wrench hard (high DC).
        """
        player = self.player_manager.players.get(player_name)
        if not player:
            return "You can't do that."
        if not player.has_condition("grappled"):
            return "You aren't grappled."

        grappler_name = self._grappler_of(player_name)
        if not grappler_name:
            player.remove_condition("grappled")
            return "You wriggle free."

        dc = self._escape_dc(player_name)
        escape_skill = self._best_escape_skill(player)
        success, total, msg = self.skills.saving_throw(player, escape_skill, dc)
        if success:
            self._release_target(grappler_name, player_name)
            return f"You break free of {grappler_name}'s grip! ({msg})"
        return f"You struggle, but {grappler_name}'s grip holds. ({msg})"

    def drag_all(
        self,
        grappler_name: str,
        new_area_name: str,
        direction: str,
        way_id: str = None,
    ) -> List[str]:
        """Drag grappled targets along when *grappler_name* moves.

        Dragging is mechanical — the grappler physically pulls the target, so
        there is no mid-move resist. The struggle is the target's own turn:
        on their next action they can ``escape`` (STR save) or go along.
        """
        lines = []
        for pname in self._grappling_targets(grappler_name):
            player = self.player_manager.players.get(pname)
            if not player or player.current_area == new_area_name:
                continue
            self.name_matcher._set_player_area(pname, new_area_name)
            if way_id:
                from engine.character_spatial import approach_way
                pid = self.player_manager.get_player_node_id(pname)
                approach_way(self.graph, pid, way_id)
            self.gs.record_turn_event(
                pname, "move",
                f"dragged through the {direction} into the {new_area_name}",
                area_name=new_area_name,
            )
            lines.append(f"You drag {pname} along with you into the {new_area_name}.")
        return lines
