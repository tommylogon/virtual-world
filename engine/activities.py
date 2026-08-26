"""Activity system — persistent multi-turn character activities (task-131).

An activity is what a character is *doing* across turns (sleeping, resting,
bathing, waiting, meditating, sitting, lying down). It is stored on
``Player.activity`` as a plain dict and is purely descriptive at the data
level; mechanical gating comes from ``player.state`` plus the command gate in
``routes/action.py``.

Key facts:
- Activities advance one step per ``tick_turn()`` (once per full turn cycle).
- ``rest``/``sleep`` are **persistent** — no fast-forward. The clock advances
  when every character has acted.
- ``sleep`` wakes on: ``wake`` command, taking damage, loud noise (perception
  save), reaching full Energy, or an optional duration timer.
- Interruptible activities (resting/waiting/meditating/sitting/lying down) end
  automatically when the character takes any other action.
- ``strip``/``undress`` are instant but drop clothes into a ``clothing_pile``
  container node in the room; ``dress`` re-equips instantly from the pile.
"""

from typing import Optional, List, Dict, Any

from graph import Node, Edge, EDGE_IN, EDGE_CARRYING, EDGE_EQUIPPED


#: player condition applied when an activity starts (None = none).
#: ``sleep`` applies `unconscious` — sleep IS an activity that causes
#: unconsciousness (auto-fail saves while asleep). All the occupied activities
#: share the single `busy` condition; the activity carries the flavor + regen mix.
ACTIVITY_CONDITIONS: Dict[str, Optional[str]] = {
    "sleeping": "unconscious",
    "resting": "busy",
    "waiting": "busy",
    "meditating": "busy",
    "bathing": "busy",
    "sitting": "busy",
    "lying down": "busy",
}

#: per-tick vital regeneration while an activity is active.
#: Values are tuned against baseline decay (Energy -1/tick) so restful
#: activities NET positive.
ACTIVITY_REGEN: Dict[str, Dict[str, int]] = {
    "sleeping": {"Energy": 0},   # handled by tick_manager state logic (+3 → net +2)
    "resting": {"Energy": 2},    # net +1
    "waiting": {},
    "meditating": {"Sanity": 2},  # net +1
    "bathing": {"Hygiene": 5},
    "sitting": {"Energy": 2},     # net +1
    "lying down": {"Energy": 3},  # net +2
}

#: human-readable labels
ACTIVITY_LABELS: Dict[str, str] = {
    "sleeping": "sleeping",
    "resting": "resting",
    "waiting": "waiting",
    "meditating": "meditating",
    "bathing": "bathing",
    "sitting": "sitting",
    "lying down": "lying down",
}

#: activities that block taking most other actions (speech/look/etc. allowed)
ACTIVITY_BLOCKING = {"sleeping", "bathing"}

#: activities that consume the character's turn (agent loop / simple NPCs skip)
ACTIVITY_SKIP_TURNS = {
    "sleeping", "resting", "waiting", "meditating",
    "bathing", "sitting", "lying down",
}

#: activities that end automatically when the character does anything else
ACTIVITY_INTERRUPTIBLE = {"resting", "waiting", "meditating", "sitting", "lying down"}

#: commands allowed while a blocking activity is active
_ALLOWED_WHILE_BLOCKED = {
    "look", "stats", "status", "inventory", "inv", "i",
    "examine", "read", "inspect", "check",
    "speak", "say", "whisper", "shout", "scream", "do", "wake", "fumble",
    "fumble around", "grope", "grope around", "feel around",
}

PILE_TAGS = ["container", "clothing_pile"]


def activity_description(activity: Optional[dict], char_name: str = "") -> str:
    """Render an activity as a short flavor line, e.g. ``sleeping in the bed``.

    Activities with a set duration show how many ticks remain; open-ended
    ones say so explicitly (task feedback: "no indication when she will
    stop resting").
    """
    if not activity:
        return ""
    label = ACTIVITY_LABELS.get(activity.get("type"), activity.get("type", ""))
    target = activity.get("target_item")
    base = f"{label} in the {target}" if target else label
    duration = activity.get("duration_ticks")
    if duration is not None:
        remaining = max(0, int(duration) - int(activity.get("elapsed_ticks", 0) or 0))
        base += f", {remaining} tick{'s' if remaining != 1 else ''} left"
    else:
        base += " (until woken)"
    return base


def pile_node_id(char_name: str) -> str:
    """Stable node id for a character's clothing pile."""
    clean = char_name.lower().replace(" ", "_").replace("'", "")
    return f"pile_of_clothes_{clean}"


class ActivitySystem:
    """Manages starting/ending/interrupting activities and per-tick progress."""

    def __init__(self, world):
        self.world = world
        self.player_manager = world.player_manager
        self.graph = world.graph
        self.logging = world.game_logger

    # ─────────────────────────── helpers ───────────────────────────

    def _current_tick(self) -> int:
        return getattr(self.world, "time_ticks", 0) or 0

    def _log(self, message: str):
        self.world.add_log_entry(message)

    def _turn_event(self, actor: str, action_type: str, description: str):
        area_name = None
        current_area = self.player_manager.current_area
        if current_area:
            area_name = getattr(current_area, "name", current_area)
        self.logging.record_turn_event(
            actor, action_type, description, area_name=area_name
        )

    def get_activity(self, player_name: str) -> Optional[dict]:
        player = self.player_manager.players.get(player_name)
        return getattr(player, "activity", None) if player else None

    # ─────────────────────────── lifecycle ───────────────────────────

    def start_activity(
        self,
        player_name: str,
        activity_type: str,
        target_item: Optional[str] = None,
        duration_ticks: Optional[int] = None,
    ) -> str:
        """Begin a persistent activity. Returns narration for the actor."""
        player = self.player_manager.players.get(player_name)
        if not player:
            raise ValueError(f"No character named '{player_name}'.")
        if player.state in ("dead", "unconscious"):
            raise ValueError(f"You can't do that while {player.state}.")
        if player.activity:
            current = activity_description(player.activity, player_name)
            raise ValueError(f"You're already {current}. Stop first.")

        activity = {
            "type": activity_type,
            "started_at_tick": self._current_tick(),
            "target_item": target_item,
            "duration_ticks": duration_ticks,
            "elapsed_ticks": 0,
            "visible": True,
        }
        player.activity = activity
        cond = ACTIVITY_CONDITIONS.get(activity_type)
        if cond == "unconscious":
            # sleep = an unconscious instance: held items drop, mumbling allowed,
            # woken by the activity system (wake command / damage / loud noise /
            # full energy), not by the condition tick.
            player.add_condition(
                "unconscious", duration=None, source="sleep",
                ends_on=["wake", "damage", "loud_noise", "energy_full"],
                overrides={"blocks_speech": False,
                           "description": "You are asleep. You can't act until you wake."},
            )
            # drops_held_items — asleep people let go of what's in their hands
            try:
                self.world.item_actions.drop_held_items(self.world, player_name)
            except Exception:
                pass
        elif cond:
            player.add_condition(cond)

        desc = activity_description(activity, player_name)
        self._turn_event(player_name, activity_type, f"is {desc}.")
        return f"You start {desc}."

    def end_activity(self, player_name: str, reason: str = "finished") -> Optional[str]:
        """End the current activity, clearing its condition. Returns a narration line."""
        player = self.player_manager.players.get(player_name)
        if not player or not player.activity:
            return None
        activity = player.activity
        desc = activity_description(activity, player_name)
        player.activity = None
        cond = ACTIVITY_CONDITIONS.get(activity.get("type"))
        if cond == "unconscious":
            # remove only sleep-sourced unconscious instances (a knockout from
            # damage stays; wake on damage handles that flow separately)
            remaining = [
                inst for inst in player.conditions.get("unconscious", [])
                if inst.get("source") != "sleep"
            ]
            if remaining:
                player.conditions["unconscious"] = remaining
            else:
                player.conditions.pop("unconscious", None)
            if not player.conditions:
                player.conditions["awake"] = [{"duration": None, "source": None, "level": 0}]
        elif cond:
            player.remove_condition(cond)
        label = reason if reason != "finished" else f"finished {activity_description(activity)}"
        self._turn_event(player_name, "activity_end", f"{label}.")
        return label

    def interrupt_activity(self, player_name: str) -> Optional[str]:
        """End an activity abruptly (character does something else)."""
        player = self.player_manager.players.get(player_name)
        if not player or not player.activity:
            return None
        activity = player.activity
        desc = activity_description(activity, player_name)
        self.end_activity(player_name, reason="stopped")
        return f"You stop {desc}."

    def has_activity(self, player_name: str) -> bool:
        return self.get_activity(player_name) is not None

    # ─────────────────────────── per-tick progress ───────────────────────────

    def tick_activity(self, player_name: str) -> Optional[str]:
        """Advance one character's activity by one tick. Returns actor-facing log."""
        player = self.player_manager.players.get(player_name)
        if not player or not player.activity:
            return None
        # Dead characters stop whatever they were doing. Unconscious also stops
        # activities EXCEPT sleep (sleep IS an unconscious instance — its own
        # regen/wake flow must keep ticking).
        knocked_out = (
            player.has_condition("unconscious")
            and not any(
                inst.get("source") == "sleep"
                for inst in player.conditions.get("unconscious", [])
            )
        )
        if player.state == "dead" or knocked_out:
            player.activity = None
            return None
        activity = player.activity
        activity_type = activity.get("type")
        activity["elapsed_ticks"] = activity.get("elapsed_ticks", 0) + 1
        outputs = []

        # Vital regen
        for stat, amount in ACTIVITY_REGEN.get(activity_type, {}).items():
            if stat in player.vitals:
                before = player.vitals[stat]
                player.vitals[stat] = min(100, player.vitals[stat] + amount)
                if player.vitals[stat] > before and stat == "Hygiene" and activity_type == "bathing":
                    outputs.append(f"You scrub yourself clean. Hygiene {player.vitals[stat]}%.")

        if activity_type == "sleeping":
            self._tick_sleeping(player, activity, outputs)
        elif activity_type == "bathing":
            self._tick_bathing(player, activity, outputs)
        elif activity_type in ACTIVITY_INTERRUPTIBLE:
            self._maybe_end_by_duration(player, activity, outputs)

        return "\n".join(outputs) if outputs else None

    def _tick_sleeping(self, player, activity: dict, outputs: List[str]):
        energy = player.vitals.get("Energy", 100)
        if energy >= 100:
            self.end_activity(player.name, reason="finished")
            outputs.append("You wake fully rested.")
            return
        # Natural timer (sleep <minutes>): wake when elapsed time runs out
        if activity.get("duration_ticks") is not None:
            if activity.get("elapsed_ticks", 0) >= activity["duration_ticks"]:
                self.end_activity(player.name, reason="finished")
                outputs.append("Your sleep is over.")
                return

    def _tick_bathing(self, player, activity: dict, outputs: List[str]):
        hygiene = player.vitals.get("Hygiene", 100)
        if hygiene >= 100:
            desc = activity_description(activity)
            self.end_activity(player.name, reason="finished")
            outputs.append(f"You finish {desc}.")
            # Auto-dress from the pile left by the instant strip (if any)
            try:
                dressed = self.dress_from_pile(player.name)
                if dressed:
                    outputs.append(dressed)
            except ValueError:
                pass
        elif activity.get("duration_ticks") is not None:
            if activity.get("elapsed_ticks", 0) >= activity["duration_ticks"]:
                self.end_activity(player.name, reason="finished")
                outputs.append("You finish bathing.")

    def _maybe_end_by_duration(self, player, activity: dict, outputs: List[str]):
        if activity.get("duration_ticks") is not None:
            if activity.get("elapsed_ticks", 0) >= activity["duration_ticks"]:
                self.end_activity(player.name, reason="finished")
                outputs.append("You finish.")

    # ─────────────────────────── wake / interrupt ───────────────────────────

    def wake(self, player_name: str, waker_name: Optional[str] = None) -> str:
        """Wake a sleeping character — or stop any other activity (task-339
        feedback: 'wake' on a resting character said 'isn't sleeping')."""
        player = self.player_manager.players.get(player_name)
        if not player:
            raise ValueError(f"No character named '{player_name}'.")
        activity_type = (player.activity or {}).get("type")
        if not activity_type:
            raise ValueError(f"{player_name} isn't sleeping or busy.")
        if activity_type == "sleeping":
            self.end_activity(player_name, reason="woke up")
            if waker_name and waker_name != player_name:
                return f"You wake {player_name}."
            return "You wake up."
        result = self.interrupt_activity(player_name)
        if waker_name and waker_name != player_name:
            return f"You get {player_name} to stop {activity_type}."
        return result or f"You stop {activity_type}."

    def wake_on_damage(self, player_name: str, source: str = None, source_type: str = None) -> Optional[str]:
        """Interrupt activities when the character takes damage. Returns log."""
        # Phase 3 — takes_damage save_on hook (cowardly, ...). Combat passes the
        # attacker (source_type "character"); traps/effects stay generic.
        try:
            self.world._emit_save_on(
                player_name, "takes_damage",
                {"source": source or "damage", "source_type": source_type},
            )
        except Exception:
            pass
        player = self.player_manager.players.get(player_name)
        if not player or not player.activity:
            return None
        activity_type = player.activity.get("type")
        if activity_type == "sleeping":
            self.end_activity(player_name, reason="woke up")
            return f"{player_name} jolts awake!"
        if activity_type in ACTIVITY_INTERRUPTIBLE:
            return self.interrupt_activity(player_name)
        return None

    def wake_on_noise(self, player_name: str) -> Optional[str]:
        """Loud noise can wake a sleeper (perception save vs DC 10)."""
        player = self.player_manager.players.get(player_name)
        if not player or not (player.activity and player.activity.get("type") == "sleeping"):
            return None
        try:
            success, _, _ = self.world.skills.saving_throw(player, "WIS", 10)
        except Exception:
            success = False
        if success:
            self.end_activity(player_name, reason="woke up")
            return "The noise stirs you awake."
        return None

    # ─────────────────────────── strip / dress / piles ───────────────────────────

    def _ensure_pile(self, player_name: str) -> Optional[Node]:
        """Find or create the clothing_pile container in the player's area."""
        player = self.player_manager.players.get(player_name)
        if not player or not player.current_area:
            return None
        area_node = self.graph.get_node(self.world.area_node_id(player.current_area))
        if not area_node:
            return None
        pile_id = pile_node_id(player_name)
        pile = self.graph.get_node(pile_id)
        if not pile:
            pile = Node(
                id=pile_id,
                type="item",
                name=f"pile of {player_name}'s clothes",
                properties={
                    "description": f"A pile of clothes {player_name} took off.",
                    "actions": "examine,take",
                    "tags": list(PILE_TAGS),
                    "uses": -1,
                    "weight": 2.0,
                    "current_state": "normal",
                },
            )
            self.graph.add_node(pile)
            self.graph.add_edge(Edge(source=pile_id, target=area_node.id, type=EDGE_IN))
        return pile

    def _remove_pile_if_empty(self, pile_id: str):
        pile = self.graph.get_node(pile_id)
        if not pile:
            return
        for edge in self.graph.get_edges_for_target(pile_id, EDGE_IN):
            return  # still has contents
        # No contents → remove pile node and its placement edge
        for edge in self.graph.edges[:]:
            if edge.source == pile_id:
                self.graph.remove_edge(edge.source, edge.target, edge.type)
        self.graph.remove_node(pile_id)

    def strip_to_pile(self, player_name: str) -> str:
        """Instant strip: remove every equipped item into a clothing pile."""
        player = self.player_manager.players.get(player_name)
        if not player:
            raise ValueError(f"No character named '{player_name}'.")
        player_id = self.player_manager.get_player_node_id(player_name)

        real_items = []
        for slot, stack in list((player.equipped or {}).items()):
            for item_id in stack:
                if item_id and not str(item_id).startswith("__"):
                    real_items.append(item_id)

        if not real_items:
            raise ValueError("You're already wearing nothing.")

        pile = self._ensure_pile(player_name)
        removed = []
        for item_id in dict.fromkeys(real_items):  # dedupe multi-slot items
            item_node = self.graph.get_node(item_id)
            # Remove equipped edges (multi-slot items may have several)
            for edge in self.graph.get_edges_for_target(player_id, EDGE_EQUIPPED):
                if edge.source == item_id:
                    self.graph.remove_edge(edge.source, edge.target, edge.type)
            # Clean multi-slot markers from all slots
            marker = f"__multi_slot_{item_id}"
            for slot in list(player.equipped.keys()):
                player.equipped[slot] = [
                    x for x in player.equipped[slot] if str(x) != marker
                ]
            if pile:
                self.graph.add_edge(Edge(source=item_id, target=pile.id, type=EDGE_IN))
            if item_node:
                self.triggers_execute_unequip(item_node, player_name)
                removed.append(f"{item_node.name}")

        # Clear every slot stack
        for slot in player.equipped.keys():
            player.equipped[slot] = []

        names = ", ".join(dict.fromkeys(removed)) or "your clothes"
        return f"You strip off: {names}. They land in a pile on the floor."

    def triggers_execute_unequip(self, item_node, player_name: str):
        try:
            self.world._execute_triggers(item_node, "on_unequip")
        except Exception:
            pass

    def triggers_execute_equip(self, item_node, player_name: str):
        try:
            self.world._execute_triggers(item_node, "on_equip")
        except Exception:
            pass

    def dress_from_pile(self, player_name: str) -> str:
        """Instant dress: re-equip everything from the clothing pile."""
        player = self.player_manager.players.get(player_name)
        if not player:
            raise ValueError(f"No character named '{player_name}'.")
        pile_id = pile_node_id(player_name)
        pile = self.graph.get_node(pile_id)
        if not pile:
            raise ValueError("There's no pile of your clothes here.")

        contents = [
            edge.source
            for edge in self.graph.get_edges_for_target(pile_id, EDGE_IN)
            if self.graph.get_node(edge.source)
        ]
        if not contents:
            self._remove_pile_if_empty(pile_id)
            raise ValueError("The pile is empty.")

        # Dress innermost first (pile order is outermost→innermost).
        dressed = []
        for item_id in reversed(contents):
            item_node = self.graph.get_node(item_id)
            if not item_node:
                continue
            self.graph.remove_edge(item_id, pile_id, EDGE_IN)
            self.graph.add_edge(Edge(source=item_id, target=self.player_manager.get_player_node_id(player_name), type=EDGE_CARRYING))
            try:
                self.world.equip_item(item_node.name)
                dressed.append(item_node.name)
            except Exception:
                # Item can't be re-equipped (e.g. no slots) → leave carried
                dressed.append(f"{item_node.name} (carried)")
            self.triggers_execute_equip(item_node, player_name)

        self._remove_pile_if_empty(pile_id)
        if not dressed:
            raise ValueError("Nothing in the pile could be worn again.")
        return "You get dressed: " + ", ".join(dressed) + "."

    # ─────────────────────────── bathe chain ───────────────────────────

    def bathe(self, player_name: str, target_item: Optional[str] = None,
              duration_ticks: Optional[int] = None) -> str:
        """Instant strip → pile, then start a bathing activity."""
        player = self.player_manager.players.get(player_name)
        if not player:
            raise ValueError(f"No character named '{player_name}'.")
        lines = []
        try:
            lines.append(self.strip_to_pile(player_name))
        except ValueError:
            pass  # already wearing nothing — fine, just bathe
        lines.append(self.start_activity(player_name, "bathing", target_item, duration_ticks))
        return " ".join(lines)
