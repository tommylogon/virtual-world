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
- ``fishing`` (task-716) is a persistent activity that samples the painted
  area's biome resource distribution at runtime and puts catches in the
  creel using pooled quantity rules.
- Activities are **data-driven**: their metadata and tick behavior come from
  JSON files under ``data/library/activities/``. Authoring a new activity is
  a JSON edit; no Python change is required unless the activity needs a new
  tick action or completion checker.
"""

import json
import os
import random
from typing import Any, Dict, List, Optional

from graph import Node, Edge, EDGE_IN, EDGE_CARRYING, EDGE_EQUIPPED
from vital_rates import change, tick_minutes

from engine.activities_loader import load as load_activity_defs, get as get_activity_def

PILE_TAGS = ["container", "clothing_pile"]


# ─────────────────────────── description ────────────────────────────────────

def activity_description(activity: Optional[dict], char_name: str = "") -> str:
    """Render an activity as a short flavor line, e.g. ``sleeping on the bed``.

    Activities with a set duration show how many ticks remain; open-ended
    ones say so explicitly (task feedback: "no indication when she will
    stop resting").
    """
    if not activity:
        return ""
    activity_type = activity.get("type", "")
    definition = get_activity_def(activity_type) or {}
    name = str(definition.get("name") or activity_type)
    target = activity.get("target_item")
    preposition = str(definition.get("preposition") or "in")
    base = f"{name} {preposition} the {target}" if target else name
    duration = activity.get("duration_ticks")
    if duration is not None:
        remaining = max(0, int(duration) - int(activity.get("elapsed_ticks", 0) or 0))
        base += f", {remaining} tick{'s' if remaining != 1 else ''} left"
    else:
        no_duration_label = definition.get("no_duration_label")
        if no_duration_label:
            base += f" ({no_duration_label})"
    return base


def pile_node_id(char_name: str) -> str:
    """Stable node id for a character's clothing pile."""
    clean = char_name.lower().replace(" ", "_").replace("'", "")
    return f"pile_of_clothes_{clean}"


# ─────────────────────────── ActivitySystem ──────────────────────────────────

class ActivitySystem:
    """Manages starting/ending/interrupting activities and per-tick progress."""

    def __init__(self, world):
        self.world = world
        self.player_manager = world.player_manager
        self.graph = world.graph
        self.logging = world.game_logger

    # ─────────────────────────── helpers ────────────────────────────────────

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

    def _definition(self, activity_type: str) -> dict:
        return get_activity_def(activity_type) or {}

    # ─────────────────────────── lifecycle ──────────────────────────────────

    def start_activity(
        self,
        player_name: str,
        activity_type: str,
        target_item: Optional[str] = None,
        duration_ticks: Optional[int] = None,
        duration_minutes: Optional[float] = None,
        **kwargs,
    ) -> str:
        """Begin a persistent activity. Returns narration for the actor.

        Extra kwargs are stored on the activity dict so the pursuit step can
        declare completion conditions (e.g. ``catch_count_target``).
        """
        player = self.player_manager.players.get(player_name)
        if not player:
            raise ValueError(f"No character named '{player_name}'.")
        if player.state in ("dead", "unconscious"):
            raise ValueError(f"You can't do that while {player.state}.")
        if player.activity:
            current = activity_description(player.activity, player_name)
            raise ValueError(f"You're already {current}. Stop first.")

        definition = self._definition(activity_type)
        condition = definition.get("condition")
        activity = {
            "type": activity_type,
            "started_at_tick": self._current_tick(),
            "target_item": target_item,
            "duration_ticks": duration_ticks,
            "duration_minutes": duration_minutes,
            "elapsed_ticks": 0,
            "elapsed_minutes": 0.0,
            "visible": True,
        }
        for key, value in kwargs.items():
            if value is not None:
                activity[key] = value
        player.activity = activity
        if condition == "unconscious":
            player.add_condition(
                "unconscious", duration=None, source="sleep",
                ends_on=["wake", "damage", "loud_noise", "energy_full"],
                overrides={"blocks_speech": False,
                           "description": "You are asleep. You can't act until you wake."},
            )
            try:
                self.world.item_actions.drop_held_items(self.world, player_name)
            except Exception:
                pass
        elif condition:
            player.add_condition(condition)

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
        activity_type = activity.get("type")
        definition = self._definition(activity_type)
        condition = definition.get("condition")
        if reason == "finished":
            player._last_completed_activity_type = activity_type
        else:
            player._last_completed_activity_type = None
        player.activity = None
        if condition == "unconscious":
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
        elif condition:
            player.remove_condition(condition)

        # Data-driven on-complete actions
        on_complete = definition.get("on_complete") or []
        complete_outputs = []
        for action in on_complete:
            action_type = action.get("type")
            if action_type == "auto_dress":
                try:
                    dressed = self.dress_from_pile(player_name)
                    if dressed:
                        complete_outputs.append(dressed)
                except ValueError:
                    pass

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

    # ─────────────────────────── per-tick progress ──────────────────────────

    def tick_activity(self, player_name: str) -> Optional[str]:
        """Advance one character's activity by one tick. Returns actor-facing log."""
        player = self.player_manager.players.get(player_name)
        if not player or not player.activity:
            return None
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
        definition = self._definition(activity_type)
        activity["elapsed_ticks"] = activity.get("elapsed_ticks", 0) + 1

        minutes = tick_minutes(self.world)
        activity["elapsed_minutes"] = activity.get("elapsed_minutes", 0.0) + minutes
        outputs: List[str] = []
        for stat, amount in (definition.get("regen") or {}).items():
            if stat in player.vitals:
                before = player.vitals[stat]
                change(player, stat, amount, minutes=minutes)
                if (player.vitals[stat] > before
                        and stat == "Hygiene" and activity_type == "bathing"):
                    outputs.append(f"You scrub yourself clean. Hygiene {player.vitals[stat]}%.")

        # Generic tick-by-definition
        tick_def = definition.get("tick") or {}
        tick_actions = tick_def.get("actions") or []
        interval = max(1, int(tick_def.get("interval_ticks") or 1))
        if activity.get("elapsed_ticks", 0) % interval == 0:
            for action in tick_actions:
                action_type = action.get("type")
                if action_type == "sample_biome_resource":
                    msg = self._handle_sample_biome_resource(player, activity, action)
                    if msg:
                        outputs.append(msg)

        # Generic completion checks
        for condition in definition.get("completion") or []:
            if self._check_completion(activity, condition, player):
                self.end_activity(player_name, reason="finished")
                outputs.append(f"You finish {activity_type}.")
                return "\n".join(outputs) if outputs else None

        return "\n".join(outputs) if outputs else None

    # ─────────────────────────── completion checkers ────────────────────────

    def _check_completion(self, activity: dict, condition: dict, player) -> bool:
        ctype = condition.get("type")
        if ctype == "duration_elapsed":
            return self._duration_elapsed(activity)
        if ctype == "vital_full":
            vital = str(condition.get("vital") or "").strip()
            if not vital:
                return False
            return float(player.vitals.get(vital, 0) or 0) >= 100.0
        if ctype == "field_threshold":
            field = str(condition.get("field") or "").strip()
            if not field:
                return False
            value = condition.get("value")
            if value is None:
                param = condition.get("param")
                if param:
                    value = activity.get(param)
            if value is None:
                return False
            try:
                return float(activity.get(field, 0) or 0) >= float(value)
            except (TypeError, ValueError):
                return False
        return False

    # ─────────────────────────── tick action handlers ───────────────────────

    def _handle_sample_biome_resource(
        self, player, activity: dict, action_def: dict
    ) -> Optional[str]:
        """Sample the current area's biome resource distribution and add a catch.

        Generic handler parameterized by the activity JSON definition:
        - ``container_tag`` — tag used to find the player's container item
        - ``result_field`` — activity dict field to increment on success
        - ``item_properties`` — tags/description/plural for the spawned item
        """
        entry = self._sample_biome_resource_for_player(player.name)
        if entry is None:
            return None
        item_id = self._pick_item_for_resource_entry(entry)
        if item_id is None:
            return None
        quantity = max(1, int(entry.get("quantity") or entry.get("weight") or 1))
        container_tag = str(action_def.get("container_tag") or "creel").lower()
        item_props = action_def.get("item_properties") or {}
        return self._add_catch_to_container(
            player.name, item_id, quantity, container_tag, item_props
        )

    # ─────────────────────────── biome resource sampling ────────────────────

    _ITEM_INDEX: Optional[Dict[str, List[str]]] = None

    def _build_item_index(self) -> Dict[str, List[str]]:
        """tag -> [item_id] over data/library/items (built once per process)."""
        if self._ITEM_INDEX is not None:
            return self._ITEM_INDEX
        index: Dict[str, List[str]] = {}
        base = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "library", "items",
        )
        try:
            for fname in os.listdir(base):
                if not fname.endswith(".json"):
                    continue
                try:
                    with open(os.path.join(base, fname), "r", encoding="utf-8-sig") as f:
                        data = json.load(f)
                except Exception:
                    continue
                item_id = fname[:-5]
                for tag in (data.get("tags") or []):
                    index.setdefault(str(tag).lower(), []).append(item_id)
        except OSError:
            pass
        ActivitySystem._ITEM_INDEX = index
        return index

    def _sample_biome_resource_for_player(self, player_name: str) -> Optional[dict]:
        """Pick one weighted resource_distribution entry matching the player's area."""
        player = self.player_manager.players.get(player_name)
        if not player or not player.current_area:
            return None
        area_id = self.world.area_node_id(player.current_area)
        area_node = self.graph.get_node(area_id) if area_id else None
        if area_node is None:
            return None
        area_tags = {str(t).lower() for t in ((area_node.properties or {}).get("tags") or [])}
        return self._sample_biome_resource(area_tags)

    def _sample_biome_resource(self, area_tags) -> Optional[dict]:
        """Pick one weighted resource_distribution entry matching the area tags."""
        try:
            from engine import biomes as biome_mod
            library = biome_mod.resource_library()
        except Exception:
            return None
        candidates = []
        weights = []
        for entry in library.values():
            entry_biome_tags = {str(t).lower() for t in (entry.get("biome_tags") or [])}
            if entry_biome_tags and not (entry_biome_tags & area_tags):
                continue
            conditions = entry.get("conditions") or {}
            if conditions.get("requires_weather"):
                continue
            w = float(entry.get("weight") or 1)
            if w <= 0:
                continue
            candidates.append(entry)
            weights.append(w)
        if not candidates:
            return None
        try:
            return random.choices(candidates, weights=weights, k=1)[0]
        except Exception:
            return candidates[0]

    def _pick_item_for_resource_entry(self, entry) -> Optional[str]:
        """Resolve a resource_distribution entry to a library item_id."""
        want = {str(t).lower() for t in (entry.get("item_tags") or [])}
        if not want:
            return None
        index = self._build_item_index()
        scores: Dict[str, int] = {}
        for tag in want:
            for item_id in index.get(tag, []):
                scores[item_id] = scores.get(item_id, 0) + 1
        if not scores:
            return None
        best = max(scores.values())
        top = [item_id for item_id, score in scores.items() if score == best]
        return random.choice(top)

    def _add_catch_to_container(
        self, player_name: str, item_id: str, quantity: int,
        container_tag: str, item_properties: dict,
    ) -> str:
        """Spawn a catch item and place it inside the player's tagged container."""
        player = self.player_manager.players.get(player_name)
        if player is None:
            return ""
        container_id = self._find_container_id(player_name, container_tag)
        if container_id is None:
            return ""
        container_node = self.graph.get_node(container_id)
        if container_node is None:
            return ""
        tags = [str(t) for t in (item_properties.get("tags") or [])]
        description = str(item_properties.get("description") or "A freshly caught item.")
        plural = str(item_properties.get("plural") or "items")
        catch_node = Node(
            id=item_id,
            type="item",
            name=item_id.replace("_", " "),
            properties={
                "description": description,
                "tags": tags,
                "actions": "examine,take",
                "uses": -1,
                "weight": 0.1,
                "current_state": "normal",
                "quantity": max(1, quantity),
                "plural": plural,
            },
        )
        self.graph.add_node(catch_node)
        self.graph.add_edge(Edge(source=catch_node.id, target=container_id, type=EDGE_IN))
        return f"You reel in {quantity} {plural}."

    def _find_container_id(self, player_name: str, container_tag: str) -> Optional[str]:
        """Locate the player's container item id matching *container_tag*."""
        player_id = self.player_manager.get_player_node_id(player_name)
        for edge in (
            self.graph.get_edges_for_target(player_id, EDGE_CARRYING)
            + self.graph.get_edges_for_target(player_id, EDGE_EQUIPPED)
        ):
            node = self.graph.get_node(edge.source)
            if node and container_tag in {
                str(t).lower() for t in (node.properties.get("tags") or [])
            }:
                return node.id
        return None

    @staticmethod
    def _duration_elapsed(activity: dict) -> bool:
        """Has the activity's authored duration run out?

        Two units, deliberately. ``duration_ticks`` counts *turns* and predates
        the author-in-game-minutes rule; ``duration_minutes`` counts game time
        and is what a task must use if its length is to mean the same thing at a
        1-minute turn and a 30-minute one (task-436). An activity may use either,
        or neither, in which case it ends on its own condition (energy full,
        hygiene clean).
        """
        if activity.get("duration_minutes") is not None:
            return activity.get("elapsed_minutes", 0.0) >= activity["duration_minutes"]
        if activity.get("duration_ticks") is not None:
            return activity.get("elapsed_ticks", 0) >= activity["duration_ticks"]
        return False

    # ─────────────────────────── wake / interrupt ──────────────────────────

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
        definition = self._definition(activity_type)
        if definition.get("interruptible"):
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

    # ─────────────────────────── strip / dress / piles ──────────────────────

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
        if pile:
            return pile
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
        for item_id in dict.fromkeys(real_items):
            item_node = self.graph.get_node(item_id)
            for edge in self.graph.get_edges_for_target(player_id, EDGE_EQUIPPED):
                if edge.source == item_id:
                    self.graph.remove_edge(edge.source, edge.target, edge.type)
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
                dressed.append(f"{item_node.name} (carried)")
            self.triggers_execute_equip(item_node, player_name)

        self._remove_pile_if_empty(pile_id)
        if not dressed:
            raise ValueError("Nothing in the pile could be worn again.")
        return "You get dressed: " + ", ".join(dressed) + "."

    # ─────────────────────────── bathe chain ────────────────────────────────

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
            pass
        lines.append(self.start_activity(player_name, "bathing", target_item, duration_ticks))
        return " ".join(lines)


# ─────────────────────── backward-compatible exports ────────────────────────

def _rebuild_legacy_activity_sets():
    definitions = load_activity_defs()
    blocking = set()
    interruptible = set()
    skip_turns = set()
    conditions = {}
    labels = {}
    regen = {}
    for aid, defn in definitions.items():
        if defn.get("blocks_turns"):
            skip_turns.add(aid)
        if defn.get("interruptible"):
            interruptible.add(aid)
        condition = defn.get("condition")
        if condition:
            conditions[aid] = condition
        labels[aid] = defn.get("name") or aid
        regen[aid] = defn.get("regen") or {}
        if aid in ("sleeping", "bathing"):
            blocking.add(aid)
    return blocking, interruptible, skip_turns, conditions, labels, regen


ACTIVITY_BLOCKING, ACTIVITY_INTERRUPTIBLE, ACTIVITY_SKIP_TURNS, ACTIVITY_CONDITIONS, ACTIVITY_LABELS, ACTIVITY_REGEN = _rebuild_legacy_activity_sets()
