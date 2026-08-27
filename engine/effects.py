"""Effect handlers for the virtual world trigger system.

Each effect type defined in the merged HANDLERS registry maps to a
category-specific handler function. The Effects class remains the public
composition root; private helpers live here while handler bodies live in
engine/effect_handlers/<category>.py.
"""

import inspect
import time
from typing import Any, Callable, Dict, List, Optional

from graph import Node, Edge, EDGE_IN, EDGE_CARRYING, EDGE_TRIGGERS
from engine.item_actions import normalize_item_actions

from engine.effect_handlers.vitals import HANDLERS as VITAL_HANDLERS
from engine.effect_handlers.memory import HANDLERS as MEMORY_HANDLERS
from engine.effect_handlers.spawn import HANDLERS as SPAWN_HANDLERS
from engine.effect_handlers.state import HANDLERS as STATE_HANDLERS
from engine.effect_handlers.environment import HANDLERS as ENVIRONMENT_HANDLERS
from engine.effect_handlers.teleport import HANDLERS as TELEPORT_HANDLERS
from engine.effect_handlers.equipment import HANDLERS as EQUIPMENT_HANDLERS
from engine.effect_handlers.properties import HANDLERS as PROPERTIES_HANDLERS
from engine.effect_handlers.conditions import HANDLERS as CONDITIONS_HANDLERS
from engine.effect_handlers.misc import HANDLERS as MISC_HANDLERS

HANDLERS = {}
HANDLERS.update(VITAL_HANDLERS)
HANDLERS.update(MEMORY_HANDLERS)
HANDLERS.update(SPAWN_HANDLERS)
HANDLERS.update(STATE_HANDLERS)
HANDLERS.update(ENVIRONMENT_HANDLERS)
HANDLERS.update(TELEPORT_HANDLERS)
HANDLERS.update(EQUIPMENT_HANDLERS)
HANDLERS.update(PROPERTIES_HANDLERS)
HANDLERS.update(CONDITIONS_HANDLERS)
HANDLERS.update(MISC_HANDLERS)


class Effects:
    """Dispatches and executes all trigger effect types.

    Effect handlers access the world through a *game_state* object (duck-typed).
    The game_state must expose the helpers the effect handlers need
    (see each method's docstring for details).
    """

    def __init__(
        self,
        graph,
        logging_events,
        trigger_fn: Optional[Callable] = None,
        render_template_fn: Optional[Callable] = None,
    ):
        self.graph = graph
        self.logging_events = logging_events
        self._trigger_fn = trigger_fn
        self._render_template_fn = render_template_fn or (lambda text, ctx: text)

    def set_trigger_system(self, trigger_system) -> None:
        """Connect this Effects instance to its parent TriggerSystem.

        This resolves the circular dependency so that set_state effects
        can recursively fire state-entry and state-exit triggers.
        """
        self._trigger_fn = trigger_system._execute_triggers
        self._render_template_fn = trigger_system._render_template

    def execute(
        self,
        effect_type: str,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        target_item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Dispatch a single effect by type.

        Returns a list of output strings to append to the action result.
        """
        handler = HANDLERS.get(effect_type)
        if handler is None:
            return [f"[Unknown effect type: {effect_type}]"]
        kwargs = {"item_node": item_node, "game_state": game_state}
        if target_item_node is not None and "target_item_node" in inspect.signature(handler).parameters:
            kwargs["target_item_node"] = target_item_node
        return handler(self, params, context, **kwargs)

    # ─────────────────── Handler wrappers ───────────────────

    def handle_message(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.misc import handle_message
        return handle_message(self, params, context, item_node=item_node, game_state=game_state)

    def handle_damage(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.vitals import handle_damage
        return handle_damage(self, params, context, item_node=item_node, game_state=game_state)

    def handle_save(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.vitals import handle_save
        return handle_save(self, params, context, item_node=item_node, game_state=game_state)

    def handle_heal(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.vitals import handle_heal
        return handle_heal(self, params, context, item_node=item_node, game_state=game_state)

    def handle_spawn_item(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.spawn import handle_spawn_item
        return handle_spawn_item(self, params, context, item_node=item_node, game_state=game_state)

    def handle_give_item(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.spawn import handle_give_item
        return handle_give_item(self, params, context, item_node=item_node, game_state=game_state)

    def handle_spawn_character(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.spawn import handle_spawn_character
        return handle_spawn_character(self, params, context, item_node=item_node, game_state=game_state)

    def handle_remove_item(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.spawn import handle_remove_item
        return handle_remove_item(self, params, context, item_node=item_node, game_state=game_state)

    def handle_set_state(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.state import handle_set_state
        return handle_set_state(self, params, context, item_node=item_node, game_state=game_state)

    def handle_set_environment(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.environment import handle_set_environment
        return handle_set_environment(self, params, context, item_node=item_node, game_state=game_state)

    def handle_teleport(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.teleport import handle_teleport
        return handle_teleport(self, params, context, item_node=item_node, game_state=game_state)

    def handle_unlock_way(self, params, context, item_node=None, target_item_node=None, game_state=None):
        from engine.effect_handlers.teleport import handle_unlock_way
        return handle_unlock_way(self, params, context, item_node=item_node, target_item_node=target_item_node, game_state=game_state)

    def handle_adjust_vital(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.vitals import handle_adjust_vital
        return handle_adjust_vital(self, params, context, item_node=item_node, game_state=game_state)

    def handle_adjust_environment(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.environment import handle_adjust_environment
        return handle_adjust_environment(self, params, context, item_node=item_node, game_state=game_state)

    def handle_set_hidden(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.state import handle_set_hidden
        return handle_set_hidden(self, params, context, item_node=item_node, game_state=game_state)

    def handle_add_tag(self, params, context, item_node=None, target_item_node=None, game_state=None):
        from engine.effect_handlers.equipment import handle_add_tag
        return handle_add_tag(self, params, context, item_node=item_node, target_item_node=target_item_node, game_state=game_state)

    def handle_remove_tag(self, params, context, item_node=None, target_item_node=None, game_state=None):
        from engine.effect_handlers.equipment import handle_remove_tag
        return handle_remove_tag(self, params, context, item_node=item_node, target_item_node=target_item_node, game_state=game_state)

    def handle_surface_memory(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.memory import handle_surface_memory
        return handle_surface_memory(self, params, context, item_node=item_node, game_state=game_state)

    def handle_suppress_memory(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.memory import handle_suppress_memory
        return handle_suppress_memory(self, params, context, item_node=item_node, game_state=game_state)

    def handle_unblock_memory(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.memory import handle_unblock_memory
        return handle_unblock_memory(self, params, context, item_node=item_node, game_state=game_state)

    def handle_set_parameter(self, params, context, item_node=None, target_item_node=None, game_state=None):
        from engine.effect_handlers.properties import handle_set_parameter
        return handle_set_parameter(self, params, context, item_node=item_node, target_item_node=target_item_node, game_state=game_state)

    def handle_adjust_parameter(self, params, context, item_node=None, target_item_node=None, game_state=None):
        from engine.effect_handlers.properties import handle_adjust_parameter
        return handle_adjust_parameter(self, params, context, item_node=item_node, target_item_node=target_item_node, game_state=game_state)

    def handle_adjust_uses(self, params, context, item_node=None, target_item_node=None, game_state=None):
        from engine.effect_handlers.equipment import handle_adjust_uses
        return handle_adjust_uses(self, params, context, item_node=item_node, target_item_node=target_item_node, game_state=game_state)

    def handle_destroy_self(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.equipment import handle_destroy_self
        return handle_destroy_self(self, params, context, item_node=item_node, game_state=game_state)

    def handle_drain(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.equipment import handle_drain
        return handle_drain(self, params, context, item_node=item_node, game_state=game_state)

    def handle_consume_item(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.equipment import handle_consume_item
        return handle_consume_item(self, params, context, item_node=item_node, game_state=game_state)

    def handle_set_description(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.properties import handle_set_description
        return handle_set_description(self, params, context, item_node=item_node, game_state=game_state)

    def handle_append_description(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.properties import handle_append_description
        return handle_append_description(self, params, context, item_node=item_node, game_state=game_state)

    def handle_rename(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.properties import handle_rename
        return handle_rename(self, params, context, item_node=item_node, game_state=game_state)

    def handle_end_scenario(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.misc import handle_end_scenario
        return handle_end_scenario(self, params, context, item_node=item_node, game_state=game_state)

    def handle_restart_scenario(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.misc import handle_restart_scenario
        return handle_restart_scenario(self, params, context, item_node=item_node, game_state=game_state)

    def handle_schedule_trigger(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.misc import handle_schedule_trigger
        return handle_schedule_trigger(self, params, context, item_node=item_node, game_state=game_state)

    def handle_apply_condition(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.conditions import handle_apply_condition
        return handle_apply_condition(self, params, context, item_node=item_node, game_state=game_state)

    def handle_remove_condition(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.conditions import handle_remove_condition
        return handle_remove_condition(self, params, context, item_node=item_node, game_state=game_state)

    def handle_apply_trait(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.conditions import handle_apply_trait
        return handle_apply_trait(self, params, context, item_node=item_node, game_state=game_state)

    def handle_remove_trait(self, params, context, item_node=None, game_state=None):
        from engine.effect_handlers.conditions import handle_remove_trait
        return handle_remove_trait(self, params, context, item_node=item_node, game_state=game_state)

    # ─────────────────── Private helpers ───────────────────

    def _hydrate_item(self, item_id, params, always_fresh=False):
        """Materialize an item node from the library if it isn't in the graph.

        With ``always_fresh=True`` a brand-new standalone node is created on
        every call (``add_node`` appends a unique suffix when the id is taken),
        so the same library entry can be spawned any number of times as
        distinct copies — one puddle per relieve, ad infinitum. With the
        default False the existing graph node is reused when present.

        Returns ``(node, lib_data)``. Reused by ``spawn_item`` (drops into an
        area) and ``give_item`` (places into a character's inventory).
        """
        spawn_node = None if always_fresh else self.graph.get_node(item_id)
        lib_data = {}
        if spawn_node is None:
            # Try to hydrate from library file
            try:
                import os, json
                lib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'library', 'items')
                lib_path = os.path.join(lib_dir, f"{item_id}.json")
                if os.path.exists(lib_path):
                    with open(lib_path, 'r', encoding='utf-8-sig') as f:
                        lib_data = json.load(f)
            except Exception:
                pass

            display_name = params.get("display_name") or params.get("name") or lib_data.get("name", item_id)
            desc = params.get("description") or lib_data.get("description", "")
            tags = lib_data.get("tags", [])
            actions = normalize_item_actions(lib_data.get("actions", ""))
            uses = lib_data.get("uses", -1)
            weight = params.get("weight", lib_data.get("weight", 0.1))
            equip_slots = lib_data.get("equip_slots", [])
            hidden = lib_data.get("hidden", False)
            current_state = params.get("current_state") or lib_data.get("current_state", "normal")
            if hidden and current_state in ("", "normal"):
                current_state = "hidden"

            properties = {
                "description": desc,
                "tags": tags,
                "actions": actions,
                "uses": uses,
                "weight": weight,
                "equip_slots": equip_slots,
                "current_state": current_state,
                "library_id": item_id,
            }
            for extra_field in (
                "light_level",
                "target_temperature",
                "heating_rate",
                "contents",
                "aliases",
            ):
                if extra_field in lib_data:
                    properties[extra_field] = lib_data[extra_field]

            spawn_node = Node(
                id=item_id,
                type="item",
                name=display_name,
                properties=properties,
            )
            self.graph.add_node(spawn_node)
            if lib_data:
                self._materialize_spawn_triggers(spawn_node.id, lib_data)
        return spawn_node, lib_data

    def _check_container_capacity(
        self, game_state, container_node_id: str, item_weight: float
    ) -> Optional[str]:
        """Enforce container max_weight_capacity for spawn-into-container effects."""
        if item_weight <= 0:
            return None
        item_actions = getattr(game_state, "item_actions", None) if game_state else None
        if item_actions is not None:
            return item_actions._check_container_capacity(container_node_id, item_weight)
        container_node = self.graph.get_node(container_node_id)
        if not container_node:
            return None
        max_cap = container_node.properties.get("max_weight_capacity")
        if max_cap is None:
            return None
        current_weight = 0.0
        for edge in self.graph.get_edges_for_target(container_node_id, EDGE_IN):
            content_node = self.graph.get_node(edge.source)
            if content_node:
                current_weight += float(content_node.properties.get("weight", 0) or 0)
        remaining = float(max_cap) - current_weight
        if item_weight > remaining:
            return (
                f"The {container_node.name} can't hold that — it's too heavy "
                f"(capacity: {current_weight:.1f}/{float(max_cap)} kg)."
            )
        return None

    def _check_target_capacity(self, game_state, pname, player_node_id, item_weight):
        """Enforce the player carry cap in effects, mirroring ``ItemActions``."""
        if item_weight <= 0 or game_state is None:
            return None
        try:
            players = getattr(game_state, "players", None) or {}
            item_actions = getattr(game_state, "item_actions", None)
            if pname in players and item_actions is not None:
                return item_actions._check_player_capacity(game_state, item_weight, player_name=pname)
            from engine.item_actions import BASE_CARRY_CAPACITY
            current = 0.0
            for edge in self.graph.get_edges_for_target(player_node_id, EDGE_CARRYING):
                cnode = self.graph.get_node(edge.source)
                if cnode:
                    current += float(cnode.properties.get("weight", 0) or 0)
            if current + item_weight > BASE_CARRY_CAPACITY:
                return (
                    f"{pname} can't carry any more "
                    f"({current:.1f}/{BASE_CARRY_CAPACITY:.1f} kg)."
                )
        except Exception:
            return None
        return None

    def _materialize_spawn_triggers(self, spawn_id, lib_data):
        """Wire library triggers onto a freshly spawned item node."""
        import random

        for trigger_data in lib_data.get("triggers", []) or []:
            trigger_type = trigger_data.get("trigger_type", "on_use")
            effects = trigger_data.get("effects", []) or []
            first_effect = effects[0].get("type", "message") if effects else "message"
            trigger_id = (
                f"trigger_{spawn_id}_{trigger_type}_"
                f"{int(time.time() * 1000)}_{random.randint(0, 999)}"
            )
            trigger_properties = {
                "trigger_type": trigger_type,
                "conditions": trigger_data.get("conditions", {}),
                "conditions_logic": trigger_data.get("conditions_logic", "and"),
                "effects": effects,
                "target_name": trigger_data.get("target_name", ""),
                "target_state": trigger_data.get("target_state", ""),
                "success_message": trigger_data.get("success_message", ""),
                "fail_message": trigger_data.get("fail_message", ""),
            }
            trigger_node = Node(
                id=trigger_id,
                type="logic_trigger",
                name=f"{trigger_type} → {first_effect}",
                properties=trigger_properties,
            )
            self.graph.add_node(trigger_node)
            self.graph.add_edge(
                Edge(
                    source=spawn_id,
                    target=trigger_id,
                    type=EDGE_TRIGGERS,
                    properties=dict(trigger_properties),
                )
            )

    def _hydrate_character(self, char_id, params, game_state=None):
        """Materialize a character from the library if not already present.

        Returns ``(player_obj, lib_data)``. Reused by ``handle_spawn_character``.
        """
        player_node_id = f"player_{char_id}".replace(' ', '_')
        existing_node = self.graph.get_node(player_node_id)
        if existing_node is not None and game_state is not None:
            existing_player = game_state.get_player(char_id)
            if existing_player is not None:
                return existing_player, {}

        lib_data = {}
        try:
            import os, json
            lib_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'library', 'characters'
            )
            lib_path = os.path.join(lib_dir, f"{char_id}.json")
            if os.path.exists(lib_path):
                with open(lib_path, 'r', encoding='utf-8-sig') as f:
                    lib_data = json.load(f)
        except Exception:
            pass

        if not lib_data:
            return None, {}

        from player import Player
        display_name = (
            params.get("display_name") or params.get("name") or lib_data.get("name", char_id)
        )
        p = Player(display_name)
        p.personality = lib_data.get("personality", "")
        p.description = lib_data.get("description", "")
        p.base_description = lib_data.get("base_description", "")
        p.stats = lib_data.get("stats", {})
        p.vitals = {**p.vitals, **lib_data.get("vitals", {})}
        if "Max_HP" not in p.vitals:
            p.vitals["Max_HP"] = 100
        if "HP" in p.vitals:
            p.vitals["HP"] = max(0, min(p.vitals["Max_HP"], p.vitals["HP"]))
        if "Energy" in p.vitals:
            p.vitals["Energy"] = max(0, min(100, p.vitals["Energy"]))
        p.decay_rates = lib_data.get("decay_rates", p.decay_rates)
        p.skills = lib_data.get("skills", {})
        p.traits = lib_data.get("traits", {})
        p.tags = list(lib_data.get("tags", []))
        p.interest_tags = list(lib_data.get("interest_tags", []))
        p.state = lib_data.get("state", "awake")
        p.load_conditions(lib_data.get("conditions", {}))
        p.simple_npc = lib_data.get("simple_npc", False)
        p.autonomy = lib_data.get("autonomy", True)
        p.npc_behavior = lib_data.get("npc_behavior", "wander")
        p.npc_action_interval = lib_data.get("npc_action_interval", 3)
        p.npc_state = lib_data.get("npc_state", "idle")
        p.behaviors = lib_data.get("behaviors", [])
        p.patrol_route = lib_data.get("patrol_route", [])
        p.patrol_index = lib_data.get("patrol_index", 0)
        p.current_area = lib_data.get("current_area")
        p.emotion = lib_data.get("emotion", {}).get("current", "neutral") if isinstance(lib_data.get("emotion"), dict) else "neutral"
        p.emotion_intensity = lib_data.get("emotion", {}).get("intensity", 0.0) if isinstance(lib_data.get("emotion"), dict) else 0.0
        p.relationships = dict(lib_data.get("relationships", {}))
        p.memories = list(lib_data.get("memories", []))
        return p, lib_data

    def _resolve_effect_target(self, params, item_node, target_item_node=None):
        """Resolve which node an effect targets: explicit node_id, self, or fallback."""
        node_id = params.get("node_id", "")
        if node_id and node_id != "self":
            return self.graph.get_node(node_id)
        if node_id == "self" and item_node:
            return item_node
        if item_node is not None:
            return item_node
        return target_item_node

    @staticmethod
    def _resolve_player_name(game_state, target):
        """Resolve a possibly-mixed-case player name against the players dict."""
        if target == "self" and game_state is not None:
            return game_state.active_player
        players = getattr(game_state, "players", None) or {}
        if target in players:
            return target
        target_lower = str(target).lower()
        for name in players:
            if str(name).lower() == target_lower:
                return name
        return target

    def _normalize_tags(self, raw_tags):
        """Return a mutable list from a tag list or comma-string."""
        if raw_tags is None:
            return []
        if isinstance(raw_tags, str):
            return [t.strip() for t in raw_tags.split(",") if t.strip()]
        if isinstance(raw_tags, list):
            return list(raw_tags)
        return []

    def _resolve_memory_target(self, params, game_state=None):
        """Resolve the target player for a memory effect."""
        target = params.get("target", "self")
        if target == "self" and game_state is not None:
            return getattr(game_state, "player", None)
        players = getattr(game_state, "players", None) or {}
        if target in players:
            return players[target]
        target_lower = str(target).lower()
        for name, p in players.items():
            if str(name).lower() == target_lower:
                return p
        return None
