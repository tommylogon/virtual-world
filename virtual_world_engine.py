# virtual_world_engine.py — FULL GRAPH INTEGRATION
# All world data now lives in self.graph (WorldGraph).
# Legacy properties (areas, current_area, etc.) are generated on‑the‑fly for compatibility.

from item import Item
from area import Area
from player import Player, CONDITION_DEFINITIONS
import time
import logging
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

logger = logging.getLogger(__name__)

class VirtualWorld:
    def __init__(self):
        self.graph = WorldGraph()
        # players dict lives in self.player_manager.players, accessed via self.players property
        self.active_player = None
        self.time_ticks = 0
        self.time_per_tick_minutes = 1
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

        # ── Calendar (task-228) ──
        self.calendar_config = {
            "minutes_per_day": 1440,
            "days_per_week": 7,
            "days_per_month": 30,
            "months_per_year": 12,
            "year_start_day": 1,
        }

        # ── Weather forecast (task-227): authored schedule + GM override ──
        # Default: authored with ZERO entries — a strict no-op until a
        # scenario authors a schedule or a GM sets an override.
        self.forecast_schedule = {
            "mode": "authored",
            "seed": None,
            "granularity": "hourly",
            "entries": [],
            "current_state": "clear",
            "transition_interval": 1,
            "transition_table": {},
        }
        self.forecast_override = None
        self._forecast_sched_obj = None
        self._forecast_last_entry_key = None
        self._forecast_last_minute = None
        # task-234 one-shot cache: {(node_id, trigger_type): game_day_bucket}.
        self._time_trigger_cache = {}

        # Initialize modular subsystems
        self.player_manager = PlayerManager(self.graph)
        self.lighting = LightingSystem(self.graph)
        # task-230: outdoor areas follow the time-of-day curve. The provider
        # reads the live clock (ticks + start offset) at call time.
        self.lighting.hour_provider = self.current_game_hour
        # task-229: moon phase feeds the outdoor-night light bonus.
        self.lighting.moon_provider = self.current_moon_phase
        self.ghost_system = GhostSystem(self.graph, self, self)
        self.effects = Effects(self.graph, self)
        self.triggers = TriggerSystem(self.graph, self, self)
        from engine.event_queue import DelayedEventQueue
        self.delayed_events = DelayedEventQueue()
        # task-330: transient browser-side LLM responses (llm_respond effect).
        # The engine queues; the browser generates + posts back; never saved.
        self.llm_pending_requests = []
        # task-360 presence window: per-area ledger {area_id: {char: entry_tick}}
        # — who is in each room and since when. The agent prompt only witnesses
        # events from entry_tick forward; leaving to another room starts a
        # fresh window; back-and-forth is the memory system's job.
        self.area_presence = {}
        self.equipment = EquipmentSystem(self.graph, self.triggers, self.game_logger, self.player_manager, world=self)
        self.skills = SkillSystem(self.player_manager, self.game_logger)
        self.name_matcher = NameMatching(self.graph, self)
        self.grapple = GrappleSystem(self.graph, self.player_manager, self.skills, self.name_matcher, self)
        self.node_ids = NodeIDHelper
        self.toggleable_items = ToggleableItems(self.graph, self)
        self.item_actions = ItemActions(self.graph, self.name_matcher, self.triggers, self.equipment, self.ghost_system, self)
        from engine.crafting import CraftingSystem
        self.crafting = CraftingSystem(self.graph, self.player_manager, self.triggers, self.effects, game_state=self)
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
        self.narration = NarrationSystem(self.graph, self.player_manager, self.area_description, self.lighting, self.tick_manager, self.game_logger, self.skills, self.node_ids, self, trigger_fn=self.triggers._execute_triggers)
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

    def build_exits_for_area(self, area_name: str, include_hidden: bool = False) -> Dict[str, Any]:
        return self.area_description.build_exits_for_area(area_name, include_hidden=include_hidden)

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

    def approach(self, target: str) -> str:
        """Walk over to a way/item/person and stop (never crosses a way)."""
        return self.movement.approach(target)

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

    def stow_item(self, item_name: str) -> str:
        return self.item_actions.stow_item(self, item_name)

    def combine_items(self, source_name: str, target_name: str) -> str:
        return self.item_actions.combine_items(self, source_name, target_name)

    def split_item(self, item_name: str, parts: int = 2) -> str:
        return self.item_actions.split_item(self, item_name, parts)

    def craft_item(self, recipe_name: str) -> str:
        return self.crafting.craft(self, recipe_name)

    def teach_item(self, subject: str, student_name: str) -> str:
        return self.crafting.teach(self, student_name, subject)

    def auto_dress_character(self, player_name: str) -> str:
        from engine.dressing import auto_dress
        return auto_dress(self, player_name)

    def _recipe_known_names(self, player_name: str) -> list:
        return self.crafting._recipe_known_names(player_name)

    def _record_area_presence(self, char_name: str, area_name: str):
        """task-360: mark *char_name* as present in *area_name* since `time_ticks`
        (and remove them from every other area's ledger)."""
        area_id = self._area_node_id(area_name) or area_name
        if self.area_presence is None:
            self.area_presence = {}
        for aid, present in list(self.area_presence.items()):
            if aid != area_id and char_name in present:
                del present[char_name]
        self.area_presence.setdefault(area_id, {})[char_name] = self.time_ticks

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

    def use_item_on(self, item_name: str, target_name: str = None, params: str = None, amount: int = 1) -> str:
        return self.item_actions.use_item_on(self, item_name, target_name, params=params, amount=amount)

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

    def queue_llm_respond(self, request):
        """Queue a browser-side LLM response request (task-330, llm_respond).

        Returns True when accepted; False when a pending request for the
        same node is still unconsumed (cooldown — prevents chatty loops).
        """
        node_id = request.get("node_id", "")
        now = request.get("ts", 0)
        cooldown = request.get("cooldown", 30)
        # drop if a pending request for this node is still in the queue
        for pending in self.llm_pending_requests:
            if pending.get("node_id") == node_id:
                return False
        self.llm_pending_requests.append(request)
        # keep the queue small (fresh first)
        self.llm_pending_requests = self.llm_pending_requests[-5:]
        return True

    def consume_llm_respond(self, request_id):
        """Remove a pending LLM response request (called after the browser
        posts the generated line back)."""
        before = len(self.llm_pending_requests)
        self.llm_pending_requests = [
            r for r in self.llm_pending_requests if r.get("id") != request_id
        ]
        return len(self.llm_pending_requests) < before

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

    # ─────────────────────── Calendar (task-228) ───────────────────────

    @property
    def game_day(self) -> int:
        """Day of the scenario's calendar (1-based, derived from time_ticks)."""
        return int(self.total_game_minutes() // 1440) + 1

    @property
    def game_month(self) -> int:
        cfg = self.calendar_config or {}
        days_per_month = max(1, int(cfg.get("days_per_month", 30)))
        months_per_year = max(1, int(cfg.get("months_per_year", 12)))
        return ((self.game_day - 1) // days_per_month) % months_per_year + 1

    @property
    def game_year(self) -> int:
        cfg = self.calendar_config or {}
        days_per_month = max(1, int(cfg.get("days_per_month", 30)))
        months_per_year = max(1, int(cfg.get("months_per_year", 12)))
        return ((self.game_day - 1) // (days_per_month * months_per_year)) + 1

    def set_game_time(self, hour=None, minute=None):
        """task-234 set_time: rotate the clock-start offset so the displayed
        time matches. Tick count (and thus game progression) is preserved;
        the change wraps across midnight."""
        cur_total = self.total_game_minutes()
        cur_h = int(cur_total // 60) % 24
        cur_m = int(cur_total) % 60
        desired = (int(hour if hour is not None else cur_h) * 60
                   + int(minute if minute is not None else cur_m)) % 1440
        delta = desired - (int(cur_total) % 1440)
        total_start = int(getattr(self, "clock_start_hour", 8)) * 60 \
            + int(getattr(self, "clock_start_minute", 0))
        new_start = (total_start + delta) % 1440
        self.clock_start_hour = new_start // 60
        self.clock_start_minute = new_start % 60

    def set_game_date(self, day=None, month=None, year=None):
        """task-234 set_date: rewrite time_ticks so the calendar shows the
        requested (day, month, year) — the hour of day is preserved."""
        cfg = self.calendar_config or {}
        days_per_month = max(1, int(cfg.get("days_per_month", 30)))
        months_per_year = max(1, int(cfg.get("months_per_year", 12)))
        cur_day = self.game_day
        year_idx = ((cur_day - 1) // (days_per_month * months_per_year)) + 1
        month_idx = ((cur_day - 1) // days_per_month) % months_per_year + 1
        day_idx = ((cur_day - 1) % days_per_month) + 1
        if year is not None:
            year_idx = max(1, int(year))
        if month is not None:
            month_idx = max(1, min(months_per_year, int(month)))
        if day is not None:
            day_idx = max(1, min(days_per_month, int(day)))
        new_day = (year_idx - 1) * days_per_month * months_per_year \
            + (month_idx - 1) * days_per_month + day_idx
        cur_hour_min = int(self.total_game_minutes()) % 1440
        desired_total = (new_day - 1) * 1440 + cur_hour_min
        start = int(getattr(self, "clock_start_hour", 8)) * 60 \
            + int(getattr(self, "clock_start_minute", 0))
        per_tick = abs(float(getattr(self, "time_per_tick_minutes", 1)) or 1)
        self.time_ticks = max(0, int(round((desired_total - start) / per_tick)))
        return True

    # ─────────────────── Weather forecast (task-227/229) ───────────────────

    def current_moon_phase(self) -> dict:
        """Current moon phase (task-229). A GM/trigger ``blood_moon`` override
        turns the night red: stronger light bonus, distinct phase name."""
        from engine.weather_forecast import get_moon_phase
        override = getattr(self, "forecast_override", None) or {}
        if override.get("blood_moon"):
            return {"name": "blood_moon", "icon": "🔴",
                    "light_bonus": 30, "cycle_day": self.game_day % 30}
        return get_moon_phase(self.game_day)

    def _fire_turn_triggers(self, trigger_type: str):
        """task-234: fire ``on_turn_start`` / ``on_turn_end`` triggers on every
        area, way, and character node that has one attached."""
        for node in list(self.graph.nodes.values()):
            if node.type not in ("area", "way", "character"):
                continue
            try:
                outputs = self.triggers._execute_triggers(node, trigger_type, game_state=self)
                for out in outputs:
                    self.add_log_entry(out)
            except Exception as e:
                logger.warning("[triggers] %s on %s: %s", trigger_type, node.id, e)

    def _fire_time_triggers(self):
        """task-234: one-shot time-of-day & moon triggers — on_dawn, on_dusk,
        on_day, on_night, on_full_moon, on_blood_moon — fired on area/way/
        character nodes. Each fires once per game-day transition (cache)."""
        hour = self.current_game_hour()
        moon = self.current_moon_phase()
        override = getattr(self, "forecast_override", None) or {}
        checks = {
            "on_dawn": 5 <= hour <= 6,
            "on_dusk": 18 <= hour <= 19,
            "on_day": 6 <= hour <= 18,
            "on_night": hour >= 19 or hour < 5,
            "on_full_moon": moon.get("name") == "full_moon",
            "on_blood_moon": bool(override.get("blood_moon")),
        }
        cache = self._time_trigger_cache
        bucket = self.game_day
        for node in list(self.graph.nodes.values()):
            if node.type not in ("area", "way", "character"):
                continue
            for trigger_type, active in checks.items():
                if not active:
                    continue
                key = (node.id, trigger_type)
                if cache.get(key) == bucket:
                    continue
                cache[key] = bucket
                try:
                    outputs = self.triggers._execute_triggers(node, trigger_type, game_state=self)
                    for out in outputs:
                        self.add_log_entry(out)
                except Exception as e:
                    logger.warning("[triggers] %s on %s: %s", trigger_type, node.id, e)
        if len(cache) > 400:
            for key in list(cache)[:len(cache) - 200]:
                cache.pop(key, None)

    def _forecast_sched(self):
        """Cached ForecastSchedule object (survives across ticks so the
        state machine keeps its current_state)."""
        from engine.weather_forecast import ForecastSchedule
        sched = getattr(self, "_forecast_sched_obj", None)
        raw = getattr(self, "forecast_schedule", None) or {}
        if sched is None or getattr(sched, "_raw", None) is not raw:
            sched = ForecastSchedule(raw)
            sched._raw = raw
            self._forecast_sched_obj = sched
        return sched

    def set_forecast_override(self, data: dict):
        """Set (or clear) a GM/trigger forecast override (task-234).

        ``data`` accepts weather/wind/humidity/temperature_mod/light_mod/air/
        blood_moon + ``duration_ticks``; ``clear_all`` or an empty payload
        clears the override. Returns the active override (None if cleared).
        """
        override = {}
        for key in ("weather", "wind", "humidity", "temperature_mod", "light_mod", "air", "blood_moon"):
            if data.get(key) is not None:
                override[key] = data[key]
        if data.get("duration_ticks") is not None:
            override["duration_ticks"] = max(1, int(data["duration_ticks"]))
        if data.get("clear_all") or not override:
            self.forecast_override = None
            return None
        self.forecast_override = override
        return override

    def _forecast_tick(self):
        """Apply the forecast baseline + override expiry (task-227/234).

        Called from TickManager.tick_turn() right after the clock advances.
        Strict no-op with the default authored/empty schedule.
        """
        raw = getattr(self, "forecast_schedule", None)
        if not isinstance(raw, dict) or not any([
            raw.get("entries"), raw.get("mode") in ("deterministic", "random", "hybrid"),
        ]):
            # Still let a duration-based GM override revert even without a schedule.
            override = getattr(self, "forecast_override", None)
            if not override:
                return
        from engine.runtime_config import config as _cfg

        sched = self._forecast_sched()

        # 1. State-machine roll at transition boundaries.
        minute_now = int(self.total_game_minutes())
        prev = getattr(self, "_forecast_last_minute", None)
        if prev is not None and sched.mode in ("deterministic", "random", "hybrid"):
            interval_minutes = max(1, sched.transition_interval) * max(1, int(self.time_per_tick_minutes))
            bounds_crossed = (minute_now // interval_minutes) - (prev // interval_minutes)
            for _ in range(max(0, min(bounds_crossed, 10))):
                sched.roll_state()
            if isinstance(self.forecast_schedule, dict):
                self.forecast_schedule["current_state"] = sched.current_state
        self._forecast_last_minute = minute_now

        # 2. Override countdown + auto-revert.
        override = getattr(self, "forecast_override", None) or None
        if override and override.get("duration_ticks") is not None:
            override["duration_ticks"] = int(override.get("duration_ticks", 1)) - 1
            if override["duration_ticks"] <= 0:
                self.forecast_override = None
                override = None
                self.add_log_entry("[Weather] The override wears off — the sky returns to the forecast.")

        # 3. Effective environment + apply to exterior areas.
        sched_env = sched.current_environment(
            self.time_ticks, self.time_per_tick_minutes, self.game_day)
        eff = sched.resolve(sched_env, override)
        if not any(eff.get(k) for k in ("weather", "wind", "humidity", "air",
                                        "temperature_mod", "light_mod")):
            return
        self._apply_forecast_env(eff)

        # 4. Narrate weather entry transitions.
        entry = sched.get_entry_for_time(minute_now, self.game_day)
        key = (entry.get("offset"), entry.get("weather")) if entry else None
        if key and key != getattr(self, "_forecast_last_entry_key", None):
            self._forecast_last_entry_key = key
            message = entry.get("message")
            if message:
                self.add_log_entry(f"[Weather] {message}")

    def _apply_forecast_env(self, eff: dict):
        """Write the effective weather baseline onto exterior (or all) areas."""
        from engine.runtime_config import config as _cfg
        scope = str(_cfg.get("forecast.apply_scope", "exterior"))
        temp_mod = eff.get("temperature_mod") or 0
        light_mod = eff.get("light_mod") or 0
        for node in self.graph.nodes.values():
            if node.type != "area":
                continue
            tags = node.properties.get("tags", []) or []
            if scope == "exterior" and "exterior" not in tags:
                continue
            env = node.properties.setdefault("environment", {})
            if eff.get("weather"):
                env["weather"] = eff["weather"]
            if eff.get("wind"):
                env["wind"] = eff["wind"]
            if eff.get("humidity"):
                env["humidity"] = eff["humidity"]
            if eff.get("air"):
                env["air"] = eff["air"]
            if temp_mod:
                # temperature_mod is a delta from the outdoor base (21°C).
                env["temperature"] = round(21.0 + float(temp_mod), 1)
            if light_mod:
                env["light"] = round(min(100, 80 + float(light_mod)))
            node.updated = time.time()

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
        """Get candidate target names for a given verb and prefix (delegated)."""
        from engine.autocomplete import get_autocomplete_options as _options
        return _options(self, verb, prefix, character_name)
