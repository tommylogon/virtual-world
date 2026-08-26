# virtual_world_engine.py — FULL GRAPH INTEGRATION
# All world data now lives in self.graph (WorldGraph).
# Legacy properties (areas, current_area, etc.) are generated on‑the‑fly for compatibility.

from item import Item
from area import Area
from player import Player, CONDITION_DEFINITIONS
import time
from typing import Optional, Dict, List, Any
from graph import WorldGraph, Node, EDGE_CONNECTION
from engine.trigger_system import TriggerSystem, TRIGGER_TYPES, EFFECT_TYPES
from engine.effects import Effects
from engine.equipment import EquipmentSystem
from engine.combat import CombatSystem
from engine.grapple import GrappleSystem
from engine.player_manager import PlayerManager
from engine.item_actions import ItemActions
from engine.area_description import AreaDescription
from engine.lighting import LightingSystem
from engine.ghost import GhostSystem
from engine.toggleable_items import ToggleableItems
from engine.tick_manager import TickManager
from engine.serialization import WorldSerializer
from engine.movement import MovementSystem
from engine.npc_behaviors import NPCBehaviorSystem
from engine.matching import NameMatching
from engine.narration import NarrationSystem
from engine.conditions import ConditionsSystem
from engine.activities import ActivitySystem
from engine.save_on import SaveOnResolver
from engine.logging_events import GameLogger
from engine.skills import SkillSystem
from engine.legacy_compat import LegacyCompat
from engine.node_ids import NodeIDHelper

class AmbiguousItemError(ValueError):
    """Raised when multiple items match a name and user must pick one."""
    def __init__(self, message, options):
        self.options = options  # List of {id, name, description}
        super().__init__(message)

class VirtualWorld:
    def __init__(self):
        self.graph = WorldGraph()
        # players dict lives in self.player_manager.players, accessed via self.players property
        self.active_player = None
        self.time_ticks = 0
        self.time_per_tick_minutes = 5
        self._scenario_source = None
        self.scenario_ended = False
        self._restart_requested = False

        # Game clock start time (08:00 by default so it's a proper time-of-day clock)
        self.clock_start_hour = 8
        self.clock_start_minute = 0

        # Narration mode: 'none' | 'player' | 'ai'
        self.narration_mode = 'none'

        # Ghost mode: when True, dead characters can act with limitations
        self.ghost_mode = False

        # Auto-generate equipment descriptions on equip/unequip (False = manual only)
        self.auto_generate_descriptions = True

        self.baseline_decay = {
            "Energy": 1, "Hunger": 1, "Thirst": 1,
            "Social": 1, "Hygiene": 1,
            "Sanity": 1, "Entertainment": 1,
            "Mana": 0
        }
        self.game_logger = GameLogger()
        self.turn_active = False  # True when a turn cycle is in progress

        self.add_log_entry("[System] Welcome to VirtualWorld. Available Actions:")
        self.add_log_entry(" - Movement: go [exit] (e.g., 'go doorway', 'go grand_stairs', 'go trapdoor')")
        self.add_log_entry(" - Interaction: open/close [door], use [item] (on [target])")
        self.add_log_entry(" - Items: take [item], drop [item], examine [item], inventory")
        self.add_log_entry(" - Vitals: rest [minutes], eat/drink (use item), stats")
        self.add_log_entry(" - CRITICAL: Keep Energy above 25% to survive and enable HP regeneration! Hunger and Thirst RISE over time — eat and drink before they max out!")
        self.add_log_entry(" - WARNING: Environmental conditions affect your needs. Pay attention to temperature, air, noise, and smell!")

        self.ACTION_COSTS = {
            "move": {"time": 1, "energy": 1},
            "open": {"time": 0, "energy": 1},
            "close": {"time": 0, "energy": 1},
            "look": {"time": 1, "energy": 0},
            "use": {"time": 1, "energy": 1},
            "take": {"time": 1, "energy": 1},
            "drop": {"time": 1, "energy": 0},
            "fumble": {"time": 2, "energy": 3}, 
        }
        self._action_time_consumed = False

        # World lore: shared list of structured lore entries
        self.world_lore = []

        # Initialize modular subsystems
        self.player_manager = PlayerManager(self.graph)
        self.lighting = LightingSystem(self.graph)
        # task-230: outdoor areas follow the time-of-day curve. The provider
        # reads the live clock (ticks + start offset) at call time.
        self.lighting.hour_provider = self.current_game_hour
        self.ghost_system = GhostSystem(self.graph, self, self)
        self.effects = Effects(self.graph, self)
        self.triggers = TriggerSystem(self.graph, self, self)
        from engine.event_queue import DelayedEventQueue
        self.delayed_events = DelayedEventQueue()
        self.equipment = EquipmentSystem(self.graph, self.triggers, self.game_logger, self.player_manager, world=self)
        self.skills = SkillSystem(self.player_manager, self.game_logger)
        self.name_matcher = NameMatching(self.graph, self)
        self.grapple = GrappleSystem(self.graph, self.player_manager, self.skills, self.name_matcher, self)
        self.node_ids = NodeIDHelper
        self.toggleable_items = ToggleableItems(self.graph, self)
        self.item_actions = ItemActions(self.graph, self.name_matcher, self.triggers, self.equipment, self.ghost_system, self)
        self.area_description = AreaDescription(self.graph, self.lighting, self, self.item_actions)
        self.tick_manager = TickManager(self.graph, self, self.lighting, self.toggleable_items, self.triggers, self)
        self.serializer = WorldSerializer(self.graph, self, self)
        self.save_on = SaveOnResolver(self)
        self.save_on = SaveOnResolver(self)
        # Initialize newly extracted subsystems
        self.logger = self.game_logger
        self.legacy_compat = LegacyCompat(self.graph, self.player_manager, self.area_description)
        self.npc_behaviors = NPCBehaviorSystem(self.graph, self.player_manager, self.triggers, self)
        # Combat needs the facade (roll_dice/is_slasher/get_player/time_ticks) as
        # its "skills" handle plus the real NPCBehaviorSystem — build it after both.
        self.combat = CombatSystem(self.graph, self, self.ghost_system, self.npc_behaviors)
        self.movement = MovementSystem(self.graph, self.player_manager, self.triggers, self.toggleable_items, self.name_matcher, self)
        self.narration = NarrationSystem(self.graph, self.player_manager, self.area_description, self.lighting, self.tick_manager, self.game_logger, self.skills, self.node_ids, self)
        # task-322 R2: speech whisper-target resolution reuses the shared matcher.
        self.narration.set_name_matcher(self.name_matcher)
        self.conditions = ConditionsSystem(self.player_manager, self)
        self.activities = ActivitySystem(self)

        # Create default player (must happen after all subsystems are initialized)
        default_player = Player()
        self.add_player(default_player)
        self.active_player = default_player.name

    # ────── Property accessors (backward compat) ──────
    @property
    def players(self):
        return self.player_manager.players

    @players.setter
    def players(self, value):
        self.player_manager.players = value

    def get_active_player_obj(self):
        return self.player_manager.get_active_player_obj()

    @property
    def active_player(self):
        if hasattr(self, 'player_manager'):
            return self.player_manager.active_player
        return self.__dict__.get('active_player')

    @active_player.setter
    def active_player(self, value):
        # player_manager may not exist yet during __init__
        if hasattr(self, 'player_manager'):
            self.player_manager.active_player = value
        else:
            self.__dict__['active_player'] = value

    # ────── GameLogger property accessors (backward compat) ──────
    @property
    def game_log(self):
        return self.game_logger.game_log

    @game_log.setter
    def game_log(self, value):
        self.game_logger.game_log = value

    @property
    def log_revision(self):
        return self.game_logger.log_revision

    @log_revision.setter
    def log_revision(self, value):
        self.game_logger.log_revision = value

    @property
    def speech_log(self):
        return self.game_logger.speech_log

    @speech_log.setter
    def speech_log(self, value):
        self.game_logger.speech_log = value

    @property
    def turn_events(self):
        return self.game_logger.turn_events

    @turn_events.setter
    def turn_events(self, value):
        self.game_logger.turn_events = value

    @property
    def turn_number(self):
        return self.game_logger.turn_number

    @turn_number.setter
    def turn_number(self, value):
        self.game_logger.turn_number = value

    # ────── Fuzzy match note forwarded to NameMatching ──────
    @property
    def _fuzzy_match_note(self):
        return self.name_matcher._fuzzy_match_note if hasattr(self, 'name_matcher') else None

    @_fuzzy_match_note.setter
    def _fuzzy_match_note(self, value):
        if hasattr(self, 'name_matcher'):
            self.name_matcher._fuzzy_match_note = value

    # ────── _last_skill_check_msg forwarded to trigger system ──────
    @property
    def _last_skill_check_msg(self):
        return self.triggers._last_skill_check_msg if hasattr(self, 'triggers') else None

    @_last_skill_check_msg.setter
    def _last_skill_check_msg(self, value):
        if hasattr(self, 'triggers'):
            self.triggers._last_skill_check_msg = value

    # ────────────────────── Convenience helpers ──────────────────────
    # ────── Public Node ID helpers (for engine modules that need them) ──────
    def area_node_id(self, name: str) -> str:
        return NodeIDHelper.area_node_id(name)

    def player_node_id(self, name: str) -> str:
        return NodeIDHelper.player_node_id(name)

    def item_node_id(self, name: str) -> str:
        return NodeIDHelper.item_node_id(name)

    def set_player_area(self, player_name: str, area_name: str):
        return self.name_matcher._set_player_area(player_name, area_name)

    def _area_node_id(self, area_name: str) -> str:
        return NodeIDHelper.area_node_id(area_name)

    def _way_node_id(self, way_name: str) -> str:
        return f"way_{way_name}"

    def _item_node_id(self, item_name: str) -> str:
        return NodeIDHelper.item_node_id(item_name)

    def _is_item_reachable(self, item_id: str, area_id: str) -> bool:
        return self.name_matcher._is_item_reachable(item_id, area_id)

    def _player_node_id(self, player_name: str) -> str:
        return NodeIDHelper.player_node_id(player_name)

    def _match_exit_direction(self, area_id: str, input_str: str) -> Optional[str]:
        return self.name_matcher._match_exit_direction(area_id, input_str)

    def resolve_exit(self, area_id: str, input_str: str):
        """Resolve an exit by any facet (handle/cardinal/name/description/
        state), including empty-direction ways. Returns (edge, way_node,
        handle) or (None, None, "")."""
        return self.name_matcher.resolve_exit(area_id, input_str)

    def _match_item_name(self, input_str: str) -> Optional[str]:
        return self.name_matcher._match_item_name(input_str)

    def _match_character_name(self, input_str: str, exclude_self: bool = True):
        """Resolve a character target by name or description (task-154).

        Returns ``(name, candidates)``; ``candidates`` is non-empty when the
        input is ambiguous across several same-area characters.
        """
        return self.name_matcher._match_character_name(input_str, exclude_self=exclude_self)

    def get_current_area_id(self) -> Optional[str]:
        return self.area_description.get_current_area_id()

    def _get_current_area_id(self) -> Optional[str]:
        return self.get_current_area_id()

    def _set_player_area(self, player_name: str, area_name: str):
        return self.name_matcher._set_player_area(player_name, area_name)

    # ────────────────── Legacy compatibility properties ──────────────────
    @property
    def areas(self) -> Dict[str, Area]:
        return self.legacy_compat.areas

    @property
    def current_area(self) -> Optional[Area]:
        return self.legacy_compat.current_area

    def build_exits_for_area(self, area_name: str) -> Dict[str, Any]:
        return self.area_description.build_exits_for_area(area_name)

    def _build_exits_for_area(self, area_name: str) -> Dict[str, Any]:
        return self.area_description.build_exits_for_area(area_name)

    @property
    def player(self) -> Optional[Player]:
        return self.legacy_compat.player

    # ─────────────────── Area & Connection Management ───────────────────
    def add_area(self, area: Area):
        return self.movement.add_area(area)

    def set_current_area(self, area_name: str):
        return self.movement.set_current_area(area_name)

    def connect_areas(self, room1_name: str, room2_name: str, dir1: str, dir2: str,
                      state="open", desc="", cost=None, one_way=False):
        return self.movement.connect_areas(room1_name, room2_name, dir1, dir2, state, desc, cost, one_way)

    def _set_exit_state(self, area_name: str, direction: str, new_state: str):
        """Update the door node's current_state and propagate."""
        area_id = self._area_node_id(area_name)
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

    # ─────────────────── Movement & Interaction ───────────────────
    def move_to_area(self, direction: str) -> str:
        return self.movement.move_to_area(direction)

    def dash_to_area(self, direction: str) -> str:
        return self.movement.dash_to_area(direction)

    def crawl_to_area(self, direction: str) -> str:
        return self.movement.crawl_to_area(direction)

    def climb_to_area(self, direction: str) -> str:
        return self.movement.climb_to_area(direction)

    def jump_to_area(self, direction: str) -> str:
        return self.movement.jump_to_area(direction)

    def toggle_way(self, direction: str, action: str = "open") -> str:
        return self.movement.toggle_way(direction, action)

    def toggle_way_by_id(self, way_id: str, action: str = "open") -> str:
        return self.movement.toggle_way_by_id(way_id, action)

    def get_area_description(self) -> str:
        return self.area_description.get_area_description()

    def get_area_items(self, include_hidden=False) -> List[str]:
        return self.area_description.get_area_items(include_hidden)

    # ─────────────────── Light Level Helpers ───────────────────

    def _light_to_level(self, val):
        return self.lighting.light_to_level(val)

    def _get_light_int(self, env, default=80):
        return self.lighting.get_light_int(env, default)

    def _get_ambient_light(self, area_id: str, env: Optional[Dict] = None) -> int:
        return self.lighting.get_ambient_light(area_id, env)


    def _can_see_in_dark(self, player_name=None) -> bool:
        return self.lighting.can_see_in_dark(self, player_name)

    # ─────────────────── Trigger System ───────────────────


    def _evaluate_conditions(self, conditions, context):
        return self.triggers._evaluate_conditions(conditions, context)

    def _execute_behavior_actions(self, char_name, actions):
        return self.triggers._execute_behavior_actions(
            char_name, actions, game_state=self
        )

    def _evaluate_trigger_condition(self, condition, item_node=None):
        return self.triggers._evaluate_trigger_condition(condition, item_node)

    def _get_available_actions(self, item_node) -> list:
        return self.triggers._get_available_actions(item_node)

    def _contextual_failure(self, verb, target_name, available_actions):
        return self.triggers._contextual_failure(verb, target_name, available_actions)


    def _execute_triggers(self, item_node, trigger_type, target_name=None, context=None, expected_target_state=None, game_state=None):
        return self.triggers._execute_triggers(item_node, trigger_type, target_name, context, expected_target_state, game_state=self)

    # ─────────────────── Ghost Mode ───────────────────

    def _spawn_body_item(self, player_name: str, cause_of_death: str = "unknown causes"):
        return self.ghost_system.spawn_body_item(player_name, cause_of_death)

    def _check_ghost_action(self, action_type: str, target_name: str = None) -> Optional[str]:
        return self.ghost_system.check_ghost_action(self, action_type, target_name)

    # ─────────────────── Items & Inventory ───────────────────

    def get_item_desc(self, target_name: str) -> str:
        return self.item_actions.get_item_desc(self, target_name)

    def take_item(self, item_name: str, item_id: Optional[str] = None) -> str:
        return self.item_actions.take_item(self, item_name, item_id)

    def drop_item(self, item_name: str) -> str:
        return self.item_actions.drop_item(self, item_name)

    def put_item_in_container(self, item_name: str, container_name: str) -> str:
        return self.item_actions.put_item_in_container(self, item_name, container_name)

    def place_item(self, item_name: str, target_name: str, relation: str = "on") -> str:
        return self.item_actions.place_item(self, item_name, target_name, relation)

    def give_item(self, item_name: str, target_name: str) -> str:
        return self.item_actions.give_item(self, item_name, target_name)

    def steal_item(self, item_name: str, target_name: str) -> str:
        return self.item_actions.steal_item(self, item_name, target_name)

    def get_inventory(self) -> List[str]:
        return self.item_actions.get_inventory(self)

    # ─────────────────── Equipment System ───────────────────


    def _get_slot_for_item(self, item_node) -> Optional[str]:
        """Auto-detect which slot an item belongs to based on equip_slots property."""
        equip_slots = item_node.properties.get("equip_slots", [])
        if isinstance(equip_slots, str):
            equip_slots = [s.strip() for s in equip_slots.split(",")]
        if equip_slots:
            return equip_slots[0]
        return None

    @property
    def EQUIP_SLOTS(self):
        return self.equipment.EQUIP_SLOTS

    def _slot_has_area(self, player, slot: str) -> bool:
        """Check if a slot has area for another item in its stack."""
        if slot not in self.EQUIP_SLOTS:
            return False
        config = self.EQUIP_SLOTS[slot]
        max_depth = config["max_depth"]
        if max_depth is None:
            return True  # accessory is unlimited
        return len(player.equipped.get(slot, [])) < max_depth

    def equip_item(self, item_name: str, slot: str = None, under: str = None) -> str:
        return self.equipment.equip_item(item_name, slot, under)

    def unequip_item(self, slot: str = None, item_name: str = None) -> str:
        return self.equipment.unequip_item(slot, item_name)

    def get_visible_equipment(self, player_name: str = None) -> dict:
        return self.equipment.get_visible_equipment(player_name)

    def get_full_equipment(self, player_name: str = None) -> dict:
        return self.equipment.get_full_equipment(player_name)

    def get_equipment_narrative(self, player_name: str = None, viewer_name: str = None) -> str:
        return self.equipment.get_equipment_narrative(player_name, viewer_name)

    def _log_llm_call(self, label, prompt, response=None, player_name=None):
        return self.game_logger.log_llm_call(label, prompt, response, player_name, self.active_player)

    def _update_equipment_description(self, p):
        return self.equipment.update_equipment_description(p)

    def _add_entertainment_gain(self, amount=5):
        return self.equipment.add_entertainment_gain(amount)

    def get_hygiene_modifier(self, player_name=None) -> int:
        return self.equipment.get_hygiene_modifier(player_name)

    def toggle_item_status(self, item_name: str) -> str:
        return self.toggleable_items.toggle_item_status(self, item_name)

    def get_path_to(self, from_area: str, to_area: str) -> Optional[str]:
        """Delegate to npc_behaviors."""
        return self.npc_behaviors.get_path_to(from_area, to_area)

    def process_simple_npcs(self, trigger_type="on_tick", extra_context=None):
        return self.npc_behaviors.process_simple_npcs(trigger_type, extra_context)

    # ─────────────────── Eat / Drink System ───────────────────

    def eat_item(self, item_name: str) -> str:
        return self.item_actions.eat_item(self, item_name)

    def drink_item(self, item_name: str) -> str:
        return self.item_actions.drink_item(self, item_name)

    def _consume_item(self, item_name: str, trigger_type: str, action_verb: str) -> str:
        return self.item_actions.consume_item(self, item_name, trigger_type, action_verb)

    def use_item(self, item_name: str, trigger_type: str = "on_use") -> str:
        return self.item_actions.use_item(self, item_name, trigger_type)

    def use_item_on(self, item_name: str, target_name: str = None, params: str = None) -> str:
        return self.item_actions.use_item_on(self, item_name, target_name, params)

    def find_item_node(self, item_name: str) -> Optional[Node]:
        return self.player_manager.find_item_node(item_name)

    def _find_item_node(self, item_name: str) -> Optional[Node]:
        return self.find_item_node(item_name)

    def rest(self, minutes=10, target_item_name=None):
        # `or 10`: the route passes minutes=None for a bare "rest", which
        # would clobber the signature default and start an endless rest
        # (task-339 feedback round — miki rested into the void).
        return self.activities.start_activity(
            self.active_player, "resting", target_item_name,
            self._activity_duration_ticks(minutes or 10),
        )

    def sleep(self, minutes=None, target_item_name=None):
        return self.activities.start_activity(
            self.active_player, "sleeping", target_item_name,
            self._activity_duration_ticks(minutes) if minutes else None,
        )

    def wait(self, minutes=None):
        return self.activities.start_activity(
            self.active_player, "waiting", None,
            self._activity_duration_ticks(minutes) if minutes else None,
        )

    def meditate(self, minutes=None):
        return self.activities.start_activity(
            self.active_player, "meditating", None,
            self._activity_duration_ticks(minutes) if minutes else None,
        )

    def sit(self):
        return self.activities.start_activity(self.active_player, "sitting")

    def lie_down(self):
        return self.activities.start_activity(self.active_player, "lying down")

    def stand(self):
        activity = self.activities.get_activity(self.active_player)
        result = None
        if activity and activity.get("type") in (
            "sitting", "lying down", "meditating", "waiting", "resting"
        ):
            result = self.activities.interrupt_activity(self.active_player)
        # Standing also ends conditions whose ends_on includes "stand" (prone)
        ended = self.conditions.end_conditions(self.active_player, "stand")
        if not result and not ended:
            raise ValueError("You aren't sitting or lying down.")
        return result or "You stand up."

    def fix(self, target=None):
        """Treat injuries: end every condition whose ends_on includes 'fix'.

        e.g. a broken leg (`prone`, permanent, ends_on: ["fix"]) can only be
        treated, not stood off.
        """
        ended = self.conditions.end_conditions(self.active_player, "fix")
        if not ended:
            raise ValueError("There's nothing to fix — you aren't hurt or broken.")
        labels = ", ".join(
            CONDITION_DEFINITIONS[c]["name"] for c, _ in ended if c in CONDITION_DEFINITIONS
        )
        return f"Treated: {labels}."

    def wake(self, player_name=None):
        target = player_name or self.active_player
        return self.activities.wake(target, self.active_player)

    def bathe(self, target_item_name=None, minutes=None):
        return self.activities.bathe(
            self.active_player, target_item_name,
            self._activity_duration_ticks(minutes) if minutes else None,
        )

    def strip(self):
        return self.activities.strip_to_pile(self.active_player)

    def dress(self):
        return self.activities.dress_from_pile(self.active_player)

    def stop_activity(self):
        result = self.activities.interrupt_activity(self.active_player)
        if not result:
            raise ValueError("You aren't doing anything right now.")
        return result

    def _activity_duration_ticks(self, minutes):
        if not minutes or minutes <= 0:
            return None
        return max(1, minutes // getattr(self, "time_per_tick_minutes", 5))

    # ─────────────────── Hunt system (usable by any agent via LLM) ───────────────────
    def hunt(self, hunter_name: str, target_name: str = None) -> str:
        return self.npc_behaviors.hunt(hunter_name, target_name)

    # ─────────────────── Player Management ───────────────────

    def is_slasher(self, player_name: str) -> bool:
        return self.player_manager.is_slasher(player_name)
    def _get_nearest_player_to(self, hunter_name: str) -> Optional[str]:
        return self.npc_behaviors.get_nearest_player_to(hunter_name)

    def _get_path_to_area(self, from_area: str, to_area: str) -> Optional[str]:
        return self.npc_behaviors.get_path_to_area(from_area, to_area)

    def slasher_hunt(self, slasher_name: str) -> str:
        return self.npc_behaviors.slasher_hunt(slasher_name)

    def _player_attack(self, attacker_name: str, target_name: str, weapon_node=None,
                       where=None) -> str:
        return self.combat.player_attack(attacker_name, target_name, weapon_node, where=where)

    def _emit_save_on(self, player_name: str, event: str, context: dict = None) -> list:
        """Phase 3: emit a world event for the save_on trait resolver."""
        return self.save_on.emit(player_name, event, context)

    def _find_weapon_in_inventory(self, player_name: str, weapon_name: str):
        return self.combat.find_weapon_in_inventory(player_name, weapon_name)
    def add_player(self, player_obj):
        return self.player_manager.add_player(player_obj)

    def get_player(self, player_name: str) -> Optional[Player]:
        """Resolve a player object by name (delegates to player_manager).

        The world facade is passed to CombatSystem as its ``skills`` handle,
        which expects ``get_player`` alongside ``roll_dice``/``is_slasher``.
        """
        return self.player_manager.get_player(player_name)

    # ─────────────────── Grapple (task-4 / task-159) ───────────────────

    def _grapple_grab(self, grappler_name: str, target_name: str) -> str:
        return self.grapple.grab(grappler_name, target_name)

    def _grapple_escape(self, player_name: str) -> str:
        return self.grapple.escape(player_name)

    def _grapple_release(self, player_name: str, target_name: str = "") -> str:
        return self.grapple.release(player_name, target_name)

    def set_active_player(self, name):
        return self.player_manager.set_active_player(name)

    # ─────────────────── Action Cost System ───────────────────
    def apply_action(self, action_name, override_cost=None, player=None):
        return self.tick_manager.apply_action(action_name, override_cost, player)

    def advance_clock(self, ticks=1):
        return self.tick_manager.advance_clock(ticks)

    def tick_turn(self, skip_npcs=False):
        return self.tick_manager.tick_turn(skip_npcs)

    # Keep the old tick() method for backwards compatibility
    def tick(self, ticks=1):
        return self.tick_manager.tick(ticks)

    def schedule_delayed(self, fire_tick, target_node_id, trigger_type="on_delayed", label=""):
        """Schedule a trigger fire N ticks in the future (task-90)."""
        self.delayed_events.schedule(fire_tick, target_node_id, trigger_type, label)

    def _process_delayed_events(self):
        """Fire all delayed events that are now due (task-90)."""
        outputs = []
        for event in self.delayed_events.pop_due(self.time_ticks):
            node = self.graph.get_node(event["target_node_id"])
            if node is None:
                continue
            out = self.triggers._execute_triggers(node, event["trigger_type"], game_state=self)
            for line in out:
                outputs.append(line)
            self.record_turn_event("__system__", "delayed", event["label"])
        return outputs

    def _build_graph_from_legacy(self, data: dict):
        return self.serializer._build_graph_from_legacy(data)

    def _create_locked_with_unlocks(self):
        """No-op: locked_with was removed from door nodes."""

    # ─────────────────── Serialization ───────────────────
    def to_dict(self):
        return self.serializer.to_dict()


    def to_scenario_dict(self) -> dict:
        return self.serializer.to_scenario_dict()

    def load_from_dict(self, data):
        return self.serializer.load_from_dict(data)

    def _load_from_template_format(self, data):
        return self.serializer._load_from_template_format(data)

    # ─────────────────── Player location helper ───────────────────
    def get_players_in_area(self, area_name=None, exclude_self=True):
        return self.player_manager.get_players_in_area(area_name, exclude_self)

    def get_all_dead_players(self) -> List[str]:
        return self.player_manager.get_all_dead_players()

    def get_all_alive_players(self) -> List[str]:
        return self.player_manager.get_all_alive_players()

    # ─────────────────── Run Logging ───────────────────
    def save_run_log(self, filename=None):
        return self.game_logger.save_run_log(
            players=self.players,
            active_player=self.active_player,
            ghost_mode=self.ghost_mode,
            time_ticks=self.time_ticks,
            current_time_str=self.get_current_time(),
            graph=self.graph,
            build_exits_fn=self._build_exits_for_area,
            filename=filename,
        )

    # ─────────────────── Other methods ───────────────────
    def process_emote(self, actor_name, emote_text):
        return self.narration.process_emote(actor_name, emote_text)

    def add_log_entry(self, text):
        return self.game_logger.add_log_entry(text)

    def record_turn_event(self, actor_name, action_type, description, area_name=None):
        return self.game_logger.record_turn_event(actor_name, action_type, description, area_name, tick=self.time_ticks)

    def clear_turn_events(self):
        """Delegate to game_logger."""
        return self.game_logger.clear_turn_events()

    def total_game_minutes(self) -> float:
        """Total in-game minutes elapsed since midnight of day one (task-322 R3).

        Single source for clock math: derives from ticks × per-tick minutes
        plus the editable clock start offset. current_game_hour() and
        TickManager.get_current_time() both read this.
        """
        ticks = getattr(self, "time_ticks", 0) or 0
        per_tick = getattr(self, "time_per_tick_minutes", 5) or 5
        start_h = getattr(self, "clock_start_hour", 8)
        start_m = getattr(self, "clock_start_minute", 0)
        return ticks * per_tick + start_h * 60 + start_m

    def current_game_hour(self) -> int:
        """Current in-game hour 0-23 (task-230)."""
        return int(self.total_game_minutes() // 60) % 24

    def get_turn_events_for_area(self, area_name, exclude_actor=None):
        return self.game_logger.get_turn_events_for_area(area_name, exclude_actor)

    def broadcast_speech(self, speaker_name, speech_text, area_name=None, speech_level="normal", whisper_target=None):
        self.narration.broadcast_speech(speaker_name, speech_text, area_name, speech_level, whisper_target)
        # Fire on_speech triggers on the speaking area node (password doors,
        # magic words, NPC reactions). The speech + speaker are exposed in the
        # trigger context so speech_matches conditions / message templates can
        # reference {speech} / {speaker}. A DIRECTED whisper (task-248) is
        # private to its target — doors and area triggers cannot eavesdrop.
        if speech_level == "whisper" and whisper_target:
            return
        if not area_name:
            speaker = self.player_manager.get_player(speaker_name)
            area_name = getattr(speaker, "current_area", None) if speaker else None
        if area_name:
            area_id = self.area_node_id(area_name)
            area_node = self.graph.get_node(area_id)
            if area_node:
                outputs = self.triggers._execute_triggers(
                    area_node,
                    "on_speech",
                    context={"speech": speech_text, "speaker": speaker_name},
                    game_state=self,
                )
                for out in outputs:
                    self.game_logger.add_log_entry(out)

    def fumble_around(self):
        return self.narration.fumble_around()

    def listen(self):
        """Focused audio scan of the current area (recently heard speech + sounds).

        The blind character's primary sense — mirrors what's already in the
        room context but returns it as an explicit, filtered audio report.
        """
        return self.narration.listen()

    def roll_dice(self, num_dice=1, sides=20, modifier=0):
        return self.skills.roll_dice(num_dice, sides, modifier)

    def skill_check(self, skill_name, difficulty_class=10, use_active_player=True):
        return self.skills.skill_check(skill_name, difficulty_class, use_active_player)

    def saving_throw(self, player, stat, dc=12):
        """Unified save primitive (task-159) — stat or skill, any player."""
        return self.skills.saving_throw(player, stat, dc)

    def _render_template(self, text, context):
        return self.triggers._render_template(text, context)

    def test_trigger(self, trigger_def, item_node=None, dry_run=True, context=None):
        """Evaluate a trigger definition against the live world (editor Run)."""
        return self.triggers.test_trigger(
            trigger_def, item_node=item_node, game_state=self, dry_run=dry_run, context=context
        )

    def validate_triggers(self, node_id: Optional[str] = None) -> list:
        """Scan every trigger in the world for broken references.

        Returns a list of issue dicts
        (``{severity, code, message, source_node_id, ...}``); each issue's
        ``source_node_id`` is the node whose trigger is broken so the UI can
        offer a clickable "open node" jump.
        """
        from engine.trigger_validator import TriggerValidator
        return TriggerValidator(self.graph).validate(node_id=node_id)

    def validate_trigger_props(self, trigger_props: dict, source_node_id: str = "") -> list:
        """Validate a single trigger definition dict (editor Run button)."""
        from engine.trigger_validator import TriggerValidator
        return TriggerValidator(self.graph).validate_trigger_props(
            trigger_props, source_node_id=source_node_id
        )

    def get_current_time(self):
        return self.tick_manager.get_current_time()

    def player_state_remedy(self, state):
        return self.skills.player_state_remedy(state)

    # ─────────────────── Narration System ───────────────────

    def get_narration_context_for_area(self, area_name=None):
        return self.narration.get_narration_context_for_area(area_name)

    def get_narration_context_for_action(self, actor_name, action_type, description, area_name=None):
        return self.narration.get_narration_context_for_action(actor_name, action_type, description, area_name)

    def inject_narration(self, narration_text, source="player", area_name=None, actor_name=None):
        return self.narration.inject_narration(narration_text, source, area_name, actor_name)

    def _get_area_id_for_player(self, player_name: str) -> Optional[str]:
        player_obj = self.player_manager.get_player(player_name)
        if not player_obj:
            return None
        player_node_id = self.player_manager.get_player_node_id(player_name)
        in_edges = self.graph.get_edges_for_source(player_node_id, 'in')
        if in_edges:
            return in_edges[0].target.lower()
        if player_obj.current_area:
            area_id = f"area_{player_obj.current_area.lower()}".replace(' ', '_')
            node = self.graph.get_node(area_id)
            if node:
                return node.id.lower()
        return None

    def get_autocomplete_options(self, verb: str, prefix: str = "", character_name: str = None) -> list:
        """Get candidate target names for a given verb and prefix."""
        player_name = character_name or self.player_manager.active_player
        if not player_name or player_name not in self.player_manager.players:
            return []

        verb = (verb or "").strip().lower()
        prefix = (prefix or "").strip().lower()

        current_area_id = self._get_area_id_for_player(player_name)

        room_items = []
        if current_area_id:
            in_edges = self.graph.get_edges_for_target(current_area_id, 'in')
            for e in in_edges:
                n = self.graph.get_node(e.source)
                if n and n.type == 'item':
                    room_items.append(n)

        player_id = self.player_manager.get_player_node_id(player_name)
        carried_edges = (
            self.graph.get_edges_for_target(player_id, 'carrying') +
            self.graph.get_edges_for_target(player_id, 'equipped')
        )
        carried_items = [
            self.graph.get_node(e.source) for e in carried_edges
            if self.graph.get_node(e.source)
        ]

        room_ways = []
        way_directions = []
        if current_area_id:
            edges = self.graph.get_edges_for_source(current_area_id) + self.graph.get_edges_for_target(current_area_id)
            for e in edges:
                if e.type in ('way', 'connection'):
                    other_id = e.target if e.source.lower() == current_area_id else e.source
                    other_node = self.graph.get_node(other_id)
                    if other_node and other_node.type in ('way', 'door'):
                        room_ways.append(other_node)
                    dir_name = e.properties.get('direction')
                    if dir_name:
                        way_directions.append(dir_name)

        area_chars = [
            pname for pname, p in self.player_manager.players.items()
            if pname != player_name and self._get_area_id_for_player(pname) == current_area_id
        ]

        candidates = []

        def _add(name):
            if name and isinstance(name, str) and name not in candidates:
                candidates.append(name)

        def _get_actions(node):
            acts = node.properties.get('actions', [])
            if isinstance(acts, str):
                acts = [a.strip().lower() for a in acts.split(',')]
            elif isinstance(acts, list):
                acts = [str(a).strip().lower() for a in acts]
            return acts

        def _get_tags(node):
            tags = node.properties.get('tags', [])
            if isinstance(tags, str):
                tags = [t.strip().lower() for t in tags.split(',')]
            elif isinstance(tags, list):
                tags = [str(t).strip().lower() for t in tags]
            return tags

        if verb in ('take', 'get', 'grab'):
            for item in room_items:
                acts = _get_actions(item)
                takeable = item.properties.get('takeable', True)
                if 'take' in acts or verb in acts or takeable:
                    _add(item.properties.get('name') or item.id)

        elif verb in ('examine', 'search', 'inspect', 'check', 'x', 'read'):
            for item in room_items + carried_items + room_ways:
                _add(item.properties.get('name') or item.id)
            for cname in area_chars:
                _add(cname)

        elif verb in ('use',):
            for item in carried_items + room_items:
                acts = _get_actions(item)
                if 'use' in acts or verb in acts or item in carried_items:
                    _add(item.properties.get('name') or item.id)

        elif verb in ('open', 'close', 'unlock', 'lock'):
            for way in room_ways:
                _add(way.properties.get('name') or way.id)
            for d in way_directions:
                _add(d)

        elif verb in ('drop', 'stow', 'put'):
            for item in carried_items:
                _add(item.properties.get('name') or item.id)

        elif verb in ('eat', 'drink'):
            for item in carried_items + room_items:
                acts = _get_actions(item)
                tags = _get_tags(item)
                if verb in acts or any(t in ('food', 'drink', 'consumable', 'edible') for t in tags):
                    _add(item.properties.get('name') or item.id)

        elif verb in ('toggle',):
            for item in room_items + carried_items:
                acts = _get_actions(item)
                tags = _get_tags(item)
                if 'toggleable' in tags or 'toggle' in acts:
                    _add(item.properties.get('name') or item.id)

        elif verb in ('attack', 'kill', 'speak', 'say', 'talk', 'whisper', 'shout'):
            for cname in area_chars:
                _add(cname)

        elif verb in ('go', 'walk', 'move', 'enter'):
            for way in room_ways:
                _add(way.properties.get('name') or way.id)
            for d in way_directions:
                _add(d)

        else:
            for item in room_items + carried_items:
                _add(item.properties.get('name') or item.id)

        if prefix:
            candidates = [c for c in candidates if c.lower().startswith(prefix.lower())]

        return candidates
