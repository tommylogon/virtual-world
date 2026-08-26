"""Effect handlers for the virtual world trigger system.

Each effect type defined in TRIGGER_EFFECTS maps to a handle_* method
on the Effects class.
"""

import inspect
import time
from typing import Any, Callable, Dict, List, Optional

from graph import Node, Edge, EDGE_IN, EDGE_CARRYING, EDGE_TRIGGERS
from engine.item_actions import normalize_item_actions


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

    # ─────────────────── Public wiring hook ───────────────────

    def set_trigger_system(self, trigger_system) -> None:
        """Connect this Effects instance to its parent TriggerSystem.

        This resolves the circular dependency so that set_state effects
        can recursively fire state-entry and state-exit triggers.
        """
        self._trigger_fn = trigger_system._execute_triggers
        self._render_template_fn = trigger_system._render_template

    # ─────────────────── Core dispatch ───────────────────

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
        handler_name = f"handle_{effect_type}"
        handler = getattr(self, handler_name, None)
        if handler is None:
            return [f"[Unknown effect type: {effect_type}]"]
        kwargs = {"item_node": item_node, "game_state": game_state}
        if target_item_node is not None and "target_item_node" in inspect.signature(
            handler
        ).parameters:
            kwargs["target_item_node"] = target_item_node
        return handler(params, context, **kwargs)

    # ─────────────────── Individual effect handlers ───────────────────

    def handle_message(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Output a narrative message.

        game_state: unused.
        """
        msg = params.get("message", "")
        if not msg.strip():
            return []
        msg = self._render_template_fn(msg, context)
        return [msg]

    def handle_damage(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Deal damage to the active player or another character.

        params:
          amount (int) — raw damage dealt on a failed (or absent) save.
          target — ``"self"``, ``"other"`` (first character in the area /
                   the one named by ``character_name``), or an explicit
                   character name.
          character_name (str) — which character for ``target="other"``.
          save (dict) — optional save to resist the damage (task-159):
              ``{"stat": "DEX", "dc": 12, "on_success": "half"|"none"}``
            ``stat`` may be an ability (STR/DEX/...) or a skill (Athletics...).
            On success the damage is halved (default) or avoided entirely; the
            ``[Save] ...`` roll is emitted alongside the damage message.

        game_state must provide:
          game_state.player        -- the active Player (or None)
          game_state.players       -- dict of all Player objects
          game_state.get_players_in_area(area_name, exclude_self) -> list
          game_state.saving_throw(player, stat, dc) -> (success, total, msg)
        """
        amount = int(params.get("amount", 5))
        target = params.get("target", "self")
        outputs = []

        target_player = None
        label = ""
        if target == "self" and game_state:
            target_player = game_state.player
            label = "You"
        elif target == "other":
            others = game_state.get_players_in_area() if game_state else []
            if others:
                character_name = params.get("character_name", others[0]["name"])
                target_player = game_state.players.get(character_name) if game_state else None
                label = character_name
        elif game_state:
            target_player = (getattr(game_state, "players", None) or {}).get(target)
            label = target

        if target_player is None:
            return outputs

        applied = amount
        save_cfg = params.get("save") or {}
        if save_cfg:
            check = save_cfg.get("stat") or save_cfg.get("skill") or "DEX"
            dc = int(save_cfg.get("dc", 12))
            success, total, msg = game_state.saving_throw(target_player, check, dc)
            outputs.append(msg)
            if success:
                on_success = save_cfg.get("on_success", "half")
                applied = 0 if on_success == "none" else amount // 2
            else:
                outputs.append(f"{label} fails to resist!")

        target_player.vitals["HP"] = max(
            0, target_player.vitals.get("HP", 100) - applied
        )
        if applied == 0:
            outputs.append(f"{label} avoids the damage entirely!")
        elif applied < amount:
            outputs.append(f"{label} takes {applied} damage (was {amount})!")
        else:
            outputs.append(f"{label} takes {applied} damage!")
        # Damage interrupts activities / wakes sleepers (task-131)
        if game_state is not None and hasattr(game_state, "activities"):
            wake_msg = game_state.activities.wake_on_damage(target_player.name)
            if wake_msg:
                outputs.append(wake_msg)
        return outputs

    def handle_save(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Roll a saving throw, then run the matching effect branch.

        params:
          stat (str) — ability (WIS...) or skill (Athletics...) to roll.
          dc (int) — difficulty class of the save.
          on_fail (list) — effects to run when the save fails.
          on_success (list) — effects to run when the save succeeds.

        This is the world-authoring gate for fears and hazards: a way or item
        trigger can force a fear save and apply ``frightened`` on failure.
        ``source`` defaults to the triggering node's name for any
        ``apply_condition`` sub-effect, so authors only set ``source_type``.

        game_state must provide ``saving_throw(player, stat, dc)`` and the
        active player.
        """
        if game_state is None:
            return []
        player = getattr(game_state, "player", None)
        if player is None:
            return []
        check = params.get("stat") or params.get("skill") or "WIS"
        dc = int(params.get("dc", 12))
        success, total, msg = game_state.saving_throw(player, check, dc)
        outputs = [msg]
        branch = "on_success" if success else "on_fail"
        sub_context = dict(context)
        for effect in params.get(branch) or []:
            etype = effect.get("type", "message")
            eparams = dict(effect.get("params", {}))
            if etype == "apply_condition" and "source" not in eparams and item_node is not None:
                eparams["source"] = item_node.name
            outputs.extend(
                self.execute(
                    etype, eparams, sub_context,
                    item_node=item_node, game_state=game_state,
                )
            )
        return outputs

    def handle_heal(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Restore a vital stat (HP by default) on the active player.

        game_state must provide: game_state.player
        """
        amount = int(params.get("amount", 10))
        stat = params.get("stat", "HP")
        outputs = []
        if game_state and game_state.player:
            if stat in game_state.player.vitals:
                game_state.player.vitals[stat] = min(
                    100, game_state.player.vitals.get(stat, 100) + amount
                )
                msg = params.get("message", f"You restore {amount} {stat}.")
                outputs.append(msg)
            else:
                game_state.player.vitals["HP"] = min(
                    100, game_state.player.vitals.get("HP", 100) + amount
                )
                outputs.append(f"You heal {amount} HP.")
        return outputs

    def handle_spawn_item(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Spawn a new item into the current area (default) or into a container.

        params:
          item_id — library / graph id to spawn
          into — ``"area"`` (default) or ``"container"`` (``EDGE_IN`` into the
                 triggering container; requires ``item_node``)
          message / fail_message — narration on success / capacity failure

        game_state must provide: game_state.get_current_area_id() -> str | None
        """
        spawn_id = params.get("item_id", "")
        if not spawn_id:
            return []
        spawn_node, _ = self._hydrate_item(spawn_id, params, always_fresh=True)
        if spawn_node is None:
            return []
        if params.get("current_state") and spawn_node is not None:
            spawn_node.properties["current_state"] = params["current_state"]

        item_weight = float(spawn_node.properties.get("weight", 0) or 0)
        into = (params.get("into") or "area").lower()

        if into == "container":
            if item_node is None:
                return [params.get("fail_message", "Nothing to put that into.")]
            cap_error = self._check_container_capacity(
                game_state, item_node.id, item_weight
            )
            if cap_error:
                return [params.get("fail_message") or cap_error]
            for edge in self.graph.edges[:]:
                if edge.source == spawn_node.id and edge.type in (EDGE_IN, EDGE_CARRYING):
                    self.graph.edges.remove(edge)
            self.graph.add_edge(
                Edge(source=spawn_node.id, target=item_node.id, type=EDGE_IN)
            )
            msg = params.get("message") or f"A {spawn_node.name} appears inside the {item_node.name}."
            return [self._render_template_fn(msg, context)]

        area_id = game_state.get_current_area_id() if game_state else None
        if not area_id:
            return []
        for edge in self.graph.edges[:]:
            if edge.source == spawn_node.id and edge.type == EDGE_IN:
                self.graph.edges.remove(edge)
        self.graph.add_edge(
            Edge(source=spawn_node.id, target=area_id, type=EDGE_IN)
        )
        msg = params.get("message") or f"A {spawn_node.name} appears!"
        return [self._render_template_fn(msg, context)]

    def _hydrate_item(self, item_id: str, params: dict, always_fresh: bool = False) -> tuple:
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
                    with open(lib_path, 'r', encoding='utf-8') as f:
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

    def handle_give_item(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Place a library item directly into a character's inventory.

        params:
          item_id (str) — library id (or existing graph node id) to give.
          target — ``"self"`` (active player, default), ``"target"``
                   (the on_use_on target), or a character name.
          message (str) — optional narration (supports {target_name}).
          display_name / description / current_state — overrides when
          hydrating from the library (same knobs as spawn_item).

        Unlike ``spawn_item`` (drops in the area), this attaches the item via
        a ``carrying`` edge, so the character is immediately infected / in
        possession — e.g. a failed Medicine check on a corpse puts the hidden
        disease carrier on you.
        """
        item_id = params.get("item_id", "")
        if not item_id:
            return []
        target = params.get("target", "self")
        if target == "target":
            target = context.get("target_name") or (game_state.active_player if game_state else "")
        if game_state is None:
            return []
        pname = self._resolve_player_name(game_state, target)
        player_node_id = f"player_{pname}".replace(" ", "_")
        if not self.graph.get_node(player_node_id):
            player_node = next((n for n in self.graph.nodes.values()
                                if n.type in ("player", "character") and n.name == pname), None)
            if player_node is None:
                return []
            player_node_id = player_node.id

        node, _ = self._hydrate_item(item_id, params, always_fresh=True)
        if node is None:
            return []
        if params.get("current_state") and node is not None:
            node.properties["current_state"] = params["current_state"]

        item_weight = float(node.properties.get("weight", 0) or 0)
        cap_error = self._check_target_capacity(game_state, pname, player_node_id, item_weight)
        if cap_error:
            return [cap_error]

        # Clear any area/container/carrying placement, then attach to the character
        for edge in self.graph.edges[:]:
            if edge.source == node.id and edge.type in (EDGE_IN, EDGE_CARRYING):
                self.graph.edges.remove(edge)
        self.graph.add_edge(
            Edge(source=node.id, target=player_node_id, type=EDGE_CARRYING)
        )
        msg = params.get("message", f"{node.name} is added to your inventory.")
        return [self._render_template_fn(msg, context)]

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

    def _check_target_capacity(self, game_state, pname: str, player_node_id: str, item_weight: float) -> Optional[str]:
        """Enforce the player carry cap in effects, mirroring ``ItemActions``.

        Uses the world's ``item_actions._check_player_capacity`` when the target
        is a registered player; falls back to a plain ``EDGE_CARRYING`` sum up to
        ``BASE_CARRY_CAPACITY`` for graph characters without a Player object.
        """
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

    def _materialize_spawn_triggers(self, spawn_id: str, lib_data: dict) -> None:
        """Wire library triggers onto a freshly spawned item node.

        Mirrors scenario loading (engine/serialization.py): for each entry
        in the library item's ``triggers`` list, create a ``logic_trigger``
        node plus a ``triggers`` edge from the spawned item to it, so the
        trigger system can resolve the triggers through graph edges
        (e.g. the burn-down ``on_tick`` / ``on_depleted`` pair).
        """
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

    def _hydrate_character(self, char_id: str, params: dict, game_state=None) -> tuple:
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
                with open(lib_path, 'r', encoding='utf-8') as f:
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

    def handle_spawn_character(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Spawn a character from the library into the world.

        params:
          character_id — library id to spawn
          area — optional area name override (defaults to current actor's area)
          message — optional narration (supports {character_name})

        game_state must provide: add_player, get_player, get_current_area_id,
        set_player_area, active_player, graph.
        """
        char_id = params.get("character_id", "")
        if not char_id:
            return []

        player_obj, _ = self._hydrate_character(char_id, params, game_state)
        if player_obj is None:
            return []

        if params.get("display_name") or params.get("name"):
            player_obj.name = params.get("display_name") or params.get("name")
        if params.get("description"):
            player_obj.description = params["description"]
        if params.get("current_state"):
            player_obj.state = params["current_state"]

        area_name = params.get("area")
        if not area_name and game_state:
            area_id = game_state.get_current_area_id()
            if area_id:
                area_node = game_state.graph.get_node(area_id)
                if area_node:
                    area_name = area_node.name

        if area_name:
            player_obj.current_area = area_name

        if game_state is None:
            return []

        prev_active = game_state.active_player
        game_state.add_player(player_obj)
        if game_state.active_player != prev_active:
            game_state.active_player = prev_active

        if area_name:
            game_state.set_player_area(player_obj.name, area_name)

        msg = params.get("message") or f"{player_obj.name} arrives!"
        return [self._render_template_fn(msg, context)]

    def handle_remove_item(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Remove an item node from the graph entirely.

        game_state: unused.
        """
        remove_id = params.get("item_id", "")
        if not remove_id:
            return []
        self.graph.remove_node(remove_id)
        return [params.get("message", f"{remove_id} vanishes!")]

    def handle_set_state(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Set the current_state property on a node.

        When the state changes, fires on_state_exit and on_state_enter
        triggers recursively.

        game_state: passed through to recursive trigger calls.
        """
        new_state = params.get("state", "open")
        target_node = self._resolve_effect_target(params, item_node)
        if target_node is None:
            return []
        old_state = target_node.properties.get("current_state", "")
        target_node.properties["current_state"] = new_state
        outputs = [
            params.get("message", f"{target_node.name} is now {new_state}.")
        ]
        if old_state != new_state and self._trigger_fn:
            outputs.extend(
                self._trigger_fn(
                    target_node,
                    "on_state_exit",
                    context=context,
                    expected_target_state=old_state,
                    game_state=game_state,
                )
            )
            outputs.extend(
                self._trigger_fn(
                    target_node,
                    "on_state_enter",
                    context=context,
                    expected_target_state=new_state,
                    game_state=game_state,
                )
            )
        return outputs

    def handle_set_environment(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Override environment properties (light, temperature, air, etc.) on a area node.

        game_state must provide: game_state._light_to_level(val) -> str
        """
        target_id = params.get("node_id", "")
        if not target_id and game_state:
            target_id = game_state.get_current_area_id()
        if not target_id:
            return []
        area_node = self.graph.get_node(target_id)
        if area_node is None:
            return []
        env = area_node.properties.get("environment", {})
        if not isinstance(env, dict):
            env = {}
        for key in ["light", "temperature", "air", "smell", "noise"]:
            if key in params:
                if key == "light":
                    env[key] = game_state._light_to_level(params[key])
                else:
                    env[key] = params[key]
        area_node.properties["environment"] = env
        area_node.updated = time.time()
        return [params.get("message", f"The environment in {area_node.name} shifts.")]

    def handle_teleport(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Teleport the active player to a different area.

        game_state must provide:
          game_state.player
          game_state._set_player_area(player_name, area_name)
          game_state.active_player
        """
        area_name = params.get("area", "")
        if not area_name or not game_state or not game_state.player:
            return []
        game_state._set_player_area(game_state.active_player, area_name)
        return [params.get("message", f"You are teleported to {area_name}!")]

    def handle_unlock_way(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        target_item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Set a door node to closed state (unlocking doesn't open it).

        ``way_id`` may be an explicit way id, ``"target"``, or blank — the
        latter two unlock the on_use_on target (the door the item was used
        on), resolved by the trigger system.

        game_state: unused.
        """
        way_id = params.get("way_id", "")
        way_node = (
            self.graph.get_node(way_id)
            if way_id and way_id != "target"
            else None
        )
        if way_node is None and way_id in ("", "target"):
            way_node = target_item_node
        if way_node and way_node.type == "way":
            way_node.properties["current_state"] = "closed"
            way_node.updated = time.time()
            return [params.get("message", "A lock clicks open!")]
        return []

    def handle_adjust_vital(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Adjust a vital stat (HP, Energy, Sanity, etc.) on a player.

        game_state must provide:
          game_state.player
          game_state.players
        """
        stat = params.get("stat", "HP")
        amount = int(params.get("amount", 0))
        target = params.get("target", "self")
        outputs = []
        if target == "self" and game_state and game_state.player:
            if stat in game_state.player.vitals:
                game_state.player.vitals[stat] = max(
                    0, min(100, game_state.player.vitals[stat] + amount)
                )
            if stat == "HP":
                max_hp = game_state.player.vitals.get("Max_HP", 100)
                game_state.player.vitals[stat] = max(
                    0, min(max_hp, game_state.player.vitals[stat])
                )
        elif target != "self" and game_state:
            target_player = game_state.players.get(target)
            if target_player and stat in target_player.vitals:
                target_player.vitals[stat] = max(
                    0, min(100, target_player.vitals[stat] + amount)
                )
                if stat == "HP":
                    max_hp = target_player.vitals.get("Max_HP", 100)
                    target_player.vitals[stat] = max(
                        0, min(max_hp, target_player.vitals[stat])
                    )
        from engine.vitals import format_vital_change
        msg = params.get("message") or format_vital_change(stat, amount)
        msg = self._render_template_fn(msg, context)
        outputs.append(msg)
        return outputs

    def handle_adjust_environment(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Incrementally adjust environment properties (temperature, light, air, etc.).

        game_state must provide: game_state.get_current_area_id() -> str | None
        """
        if game_state is None:
            return []
        area_id = game_state.get_current_area_id()
        if not area_id:
            return []
        area_node = self.graph.get_node(area_id)
        if area_node is None:
            return []
        env = area_node.properties.get("environment", {})
        for key in ["temperature", "light"]:
            if key in params:
                try:
                    current = int(env.get(key, 0))
                    env[key] = max(-50, min(100, current + int(params[key])))
                except (ValueError, TypeError):
                    pass
        for key in ["air", "smell", "noise"]:
            if key in params:
                env[key] = params[key]
        area_node.properties["environment"] = env
        area_node.updated = time.time()
        msg = params.get("message", "The environment shifts.")
        msg = self._render_template_fn(msg, context)
        return [msg]

    def handle_set_hidden(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Toggle the hidden state on a node (via current_state).

        game_state: unused.
        """
        hidden = params.get("hidden", True)
        target_node = self._resolve_effect_target(params, item_node)
        if target_node is None:
            return []
        if hidden:
            target_node.properties["current_state"] = "hidden"
        else:
            if target_node.properties.get("current_state") == "hidden":
                target_node.properties["current_state"] = "normal"
        target_node.updated = time.time()
        return [
            params.get(
                "message",
                f"{target_node.name} is now {'hidden' if hidden else 'visible'}.",
            )
        ]

    def _resolve_effect_target(self, params: dict, item_node, target_item_node=None):
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
    def _resolve_player_name(game_state, target: str) -> str:
        """Resolve a possibly-mixed-case player name against the players dict.

        The on_use_on target arrives lowercased (``kaelen voss``) while the
        players dict is keyed by display name (``Kaelen Voss``), so exact
        lookup misses. Falls back to the original string.
        """
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

    def handle_add_tag(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        target_item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Add a tag to a target node's tags list.

        Tag from params['tag']; targets via node_id / self / target_tag fan-out.
        game_state: unused.
        """
        tag = str(params.get("tag", "")).strip()
        if not tag:
            return []
        target_node = self._resolve_effect_target(params, item_node, target_item_node)
        if target_node is None:
            return []
        tags = self._normalize_tags(target_node.properties.get("tags"))
        if tag not in tags:
            tags.append(tag)
        target_node.properties["tags"] = tags
        target_node.updated = time.time()
        message = params.get("message", f"Added tag '{tag}' to {target_node.name}.")
        return [message] if message else []

    def handle_remove_tag(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        target_item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Remove a tag from a target node's tags list.

        Tag from params['tag']; targets via node_id / self / target_tag fan-out.
        game_state: unused.
        """
        tag = str(params.get("tag", "")).strip()
        if not tag:
            return []
        target_node = self._resolve_effect_target(params, item_node, target_item_node)
        if target_node is None:
            return []
        tags = self._normalize_tags(target_node.properties.get("tags"))
        if tag in tags:
            tags.remove(tag)
        target_node.properties["tags"] = tags
        target_node.updated = time.time()
        message = params.get("message", f"Removed tag '{tag}' from {target_node.name}.")
        return [message] if message else []

    def handle_surface_memory(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Force a matching memory into active recall with a salience boost.

        params:
          tags (list[str]) — memories tagged with ALL of these are matched.
          keywords (str) — text substring match (case-insensitive).
          salience_boost (int, default 3) — temporary relevance bump written
            into the memory entry as ``salience_override``.
          message (str) — optional narrative line; if empty, no output is
            emitted when there is no match.

        game_state must provide:
          game_state.players — dict of Player objects
          game_state.active_player — current active player name
        """
        tags = [str(t).lower() for t in (params.get("tags") or []) if t]
        keywords = (params.get("keywords") or "").lower().strip()
        salience_boost = int(params.get("salience_boost", 3))
        msg_template = params.get("message", "")

        player = self._resolve_memory_target(params, game_state)
        if player is None:
            return [msg_template] if msg_template else []

        matches = []
        for m in player.memories:
            if m.get("suppressions"):
                continue
            mem_tags = [t.lower() for t in (m.get("tags") or [])]
            tag_match = bool(tags) and all(t in mem_tags for t in tags)
            kw_match = bool(keywords) and keywords in m.get("text", "").lower()
            if (tags and tag_match) or (keywords and kw_match) or (not tags and not keywords):
                m["salience_override"] = salience_boost
                matches.append(m)

        if not matches:
            return [msg_template] if msg_template else []

        matches.sort(key=lambda m: m.get("importance", 5), reverse=True)
        top = matches[0]
        outputs = []
        if msg_template:
            outputs.append(msg_template.replace("{memory}", top.get("text", "")))
        return outputs

    def handle_suppress_memory(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Mark matching memories as inaccessible for `duration` turns.

        params:
          tags (list[str])
          keywords (str)
          duration (int, default 1) — turns to suppress; 0 = permanent until
            ``unblock_memory`` fires.
          scope (str, default "self") — "self" or explicit character name.

        game_state must provide:
          game_state.players — dict of Player objects
          game_state.active_player — current active player name
        """
        player = self._resolve_memory_target(params, game_state)
        if player is None:
            return []
        tags = params.get("tags") or []
        keywords = params.get("keywords", "")
        duration = int(params.get("duration", 1))
        scope = params.get("scope", "self")
        suppressed = player.suppress_memory(tags=tags, keywords=keywords, duration=duration, scope=scope)
        msg = params.get("message", "")
        if suppressed and msg:
            return [msg]
        return []

    def handle_unblock_memory(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Remove active suppressions from matching memories.

        params:
          tags (list[str])
          keywords (str)
          scope (str, default "self")

        game_state must provide:
          game_state.players — dict of Player objects
          game_state.active_player — current active player name
        """
        player = self._resolve_memory_target(params, game_state)
        if player is None:
            return []
        tags = params.get("tags") or []
        keywords = params.get("keywords", "")
        scope = params.get("scope", "self")
        unblocked = player.unblock_memory(tags=tags, keywords=keywords, scope=scope)
        msg = params.get("message", "")
        if unblocked and msg:
            return [msg]
        return []

    def _resolve_memory_target(self, params: dict, game_state: Optional[Any] = None):
        """Resolve the target player for a memory effect.

        Mirrors ``_resolve_save_target`` but returns the Player object.
        """
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

    def handle_set_parameter(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        target_item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Set a key in a target node's ``parameters`` dict to an explicit value.

        Targets via node_id / self / target_tag fan-out (any node type — item,
        way, area, character). Read back with ``{param:<key>}`` in descriptions.
        game_state: unused.
        """
        key = str(params.get("key", "")).strip()
        if not key:
            return []
        target_node = self._resolve_effect_target(params, item_node, target_item_node)
        if target_node is None:
            return []
        params_dict = target_node.properties.setdefault("parameters", {})
        if not isinstance(params_dict, dict):
            params_dict = {}
            target_node.properties["parameters"] = params_dict
        params_dict[key] = params.get("value", "")
        target_node.updated = time.time()
        message = params.get(
            "message",
            f"Set '{key}' on {target_node.name} to '{params_dict[key]}'.",
        )
        return [message] if message else []

    def handle_adjust_parameter(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        target_item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Add a numeric delta to a key in a target node's ``parameters`` dict.

        For counters/gauges (e.g. ``{delta: +1}`` on a charges param). Targets via
        node_id / self / target_tag fan-out on any node type.
        game_state: unused.
        """
        key = str(params.get("key", "")).strip()
        if not key:
            return []
        target_node = self._resolve_effect_target(params, item_node, target_item_node)
        if target_node is None:
            return []
        params_dict = target_node.properties.setdefault("parameters", {})
        if not isinstance(params_dict, dict):
            params_dict = {}
            target_node.properties["parameters"] = params_dict
        try:
            current = int(params_dict.get(key, 0))
        except (ValueError, TypeError):
            current = 0
        delta = int(params.get("delta", 0))
        params_dict[key] = current + delta
        target_node.updated = time.time()
        message = params.get(
            "message",
            f"Adjusted '{key}' on {target_node.name} to '{params_dict[key]}'.",
        )
        return [message] if message else []

    def handle_adjust_uses(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        target_item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Change the remaining-use count on an item node.

        Uses node_id from params, or falls back to target_item_node (for on_use_on).
        game_state: unused.
        """
        node_id = params.get("node_id", "")
        target_node = None
        if node_id and node_id != "self":
            target_node = self.graph.get_node(node_id)
        if target_node is None and node_id == "self" and item_node:
            target_node = item_node
        if target_node is None and target_item_node:
            target_node = target_item_node
        if target_node is None:
            return []
        delta = int(params.get("delta", -1))
        current_uses = int(target_node.properties.get("uses", -1))
        if current_uses >= 0:
            target_node.properties["uses"] = max(0, current_uses + delta)
            target_node.updated = time.time()
            message = params.get(
                "message",
                f"{target_node.name} uses: {current_uses} -> {target_node.properties['uses']}.",
            )
            if not message:
                return []
            return [message]
        return []

    def handle_destroy_self(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Remove the triggering item node from the graph.

        game_state: unused.
        """
        if item_node is None:
            return []
        msg = params.get("message", "The item crumbles to dust!")
        for edge in self.graph.edges[:]:
            if edge.source == item_node.id and edge.type == EDGE_IN:
                self.graph.edges.remove(edge)
        self.graph.remove_node(item_node.id)
        return [msg]

    def handle_drain(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Reduce an item's remaining uses.

        game_state: unused.
        """
        if item_node is None:
            return []
        amount = int(params.get("amount", 1))
        stat = params.get("stat", "uses")
        outputs = []
        if stat == "uses":
            uses = item_node.properties.get("uses", -1)
            if uses > 0:
                item_node.properties["uses"] = max(0, uses - amount)
                if item_node.properties["uses"] == 0:
                    outputs.append(
                        params.get(
                            "message",
                            f"The {item_node.name} runs out of power.",
                        )
                    )
        return outputs

    def handle_consume_item(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Remove a named item from the active player's inventory,
        decrementing uses if tracked.

        game_state must provide:
          game_state.player
          game_state.active_player
          game_state._player_node_id(name) -> str
        """
        consume_name = params.get("item", "")
        if not consume_name or not game_state or not game_state.player:
            return []
        player_id = game_state._player_node_id(game_state.active_player)
        inventory_edges = self.graph.get_edges_for_target(
            player_id, EDGE_CARRYING
        )
        needle = str(consume_name).lower()
        target_item_id = None
        for edge in inventory_edges:
            node = self.graph.get_node(edge.source)
            if (
                node
                and node.type == "item"
                and (needle in node.name.lower() or needle in node.id.lower())
            ):
                target_item_id = node.id
                break
        if target_item_id is None:
            return []
        for edge in self.graph.edges[:]:
            if (
                edge.source == target_item_id
                and edge.target == player_id
                and edge.type == EDGE_CARRYING
            ):
                self.graph.edges.remove(edge)
        target_node = self.graph.get_node(target_item_id)
        if target_node:
            uses = int(target_node.properties.get("uses", -1))
            if uses > 0:
                target_node.properties["uses"] = uses - 1
                if target_node.properties["uses"] <= 0:
                    self.graph.remove_node(target_item_id)
            elif uses == 1:
                self.graph.remove_node(target_item_id)
        msg = params.get("message", f"{consume_name} is consumed.")
        msg = self._render_template_fn(msg, context)
        return [msg]

    def handle_set_description(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Replace the description on a target node.

        game_state: unused.
        """
        target = params.get("target", "")
        new_desc = params.get("value") or params.get("description", "")
        if not target or not new_desc:
            return []
        target_node = self.graph.get_node(target)
        if target_node is None:
            return []
        target_node.properties["description"] = self._render_template_fn(
            new_desc, context
        )
        msg = params.get("message", "Description changed.")
        msg = self._render_template_fn(msg, context)
        return [msg]

    def handle_append_description(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Append text to the description on a target node.

        game_state: unused.
        """
        target = params.get("target", "")
        append_text = params.get("text", "")
        if not target or not append_text:
            return []
        target_node = self.graph.get_node(target)
        if target_node is None:
            return []
        current = target_node.properties.get("description", "")
        target_node.properties["description"] = (
            current + "\n" + self._render_template_fn(append_text, context)
        )
        msg = params.get("message", "Description updated.")
        msg = self._render_template_fn(msg, context)
        return [msg]

    def handle_rename(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Rename a node (used for the "unknown name" discovery flow).

        Targets the triggering item by default; pass ``node_id`` (or ``"self"``)
        to target a different node. The display name lives on ``Node.name`` —
        set there so examine/matching/take all see the new name. ``properties``
        is left untouched except mirroring into ``properties["name"]`` for
        any legacy readers.

        game_state: unused.
        """
        new_name = params.get("name", "")
        if not new_name:
            return []
        node_id = params.get("node_id", "")
        if not node_id or node_id == "self":
            if item_node:
                node_id = item_node.id
            else:
                return []
        target_node = self.graph.get_node(node_id)
        if target_node is None:
            return []
        rendered = self._render_template_fn(new_name, context)
        target_node.name = rendered
        target_node.properties["name"] = rendered
        msg = params.get("message", f"It is now called {rendered}.")
        msg = self._render_template_fn(msg, context)
        return [msg]

    def handle_end_scenario(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Set the scenario-ended flag.

        game_state must provide: game_state.scenario_ended (writable attribute)
        """
        if game_state is not None:
            game_state.scenario_ended = True
        return [params.get("message", "The scenario has ended.")]

    def handle_restart_scenario(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Set both the scenario-ended and restart-requested flags.

        game_state must provide:
          game_state.scenario_ended (writable)
          game_state._restart_requested (writable)
        """
        if game_state is not None:
            game_state.scenario_ended = True
            game_state._restart_requested = True
        return [params.get("message", "The scenario will restart.")]

    def handle_schedule_trigger(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Queue a trigger fire N ticks in the future (task-90).

        Pure scheduling: this effect only records when *and on which node* the
        delayed fire happens. What actually occurs is defined by the target
        node's ``on_delayed`` trigger, reusing all normal effect types.

        params:
          delay_ticks (int) — ticks from now until the fire.
          target (str, optional) — item/node name **or** graph node ID whose
              ``on_delayed`` triggers should run. Defaults to the node the
              scheduling trigger sits on (``item_node``).

        game_state must provide:
          game_state.time_ticks          -- current tick count
          game_state.schedule_delayed(fire_tick, target_node_id,
                                      trigger_type, label) -- queue hook
        """
        if game_state is None:
            return []
        try:
            delay = max(1, int(params.get("delay_ticks", 1)))
        except (ValueError, TypeError):
            delay = 1

        # Resolve the target node: explicit name/ID, else the trigger's parent.
        target = params.get("target", "")
        target_node = None
        if target:
            needle = str(target).lower()
            for node in self.graph.nodes.values():
                if node.id.lower() == needle or (node.name or "").lower() == needle:
                    target_node = node
                    break
        if target_node is None:
            target_node = item_node
        if target_node is None:
            return []

        fire_tick = game_state.time_ticks + delay
        label = f"{target_node.name} in {delay} tick(s)"
        game_state.schedule_delayed(fire_tick, target_node.id, "on_delayed", label)
        return []

    def handle_apply_condition(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Apply a condition to a character.
        params: {"condition": "poisoned", "target": "self", "duration": 10,
                 "source": "viper", "source_type": "item", "level": 0,
                 "periodic": {"HP": -7},              // per-instance drain override
                 "extra_conditions": [{"condition": "blind", "duration": 3}],
                 "ends_on": ["fix"], "symptoms": {...}, "known": false}
        """
        condition = params.get("condition", "")
        if not condition:
            return []
        target = params.get("target", "self")
        if target == "target":
            # Ally-administered cure: "use X on <name>" resolves to the target.
            target = context.get("target_name") or (game_state.active_player if game_state else "")
        if game_state is not None:
            pname = self._resolve_player_name(game_state, target)
            game_state.conditions.apply_condition(
                pname, condition,
                duration=params.get("duration"),
                source=params.get("source"),
                level=params.get("level"),
                periodic=params.get("periodic"),
                extra_conditions=params.get("extra_conditions"),
                ends_on=params.get("ends_on"),
                symptoms=params.get("symptoms"),
                known=params.get("known"),
                source_type=params.get("source_type"),
            )
        return [params.get("message", f"{condition} applied.")]

    def handle_remove_condition(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Remove a condition from a character.
        params: {"condition": "poisoned", "target": "self"}
        """
        condition = params.get("condition", "")
        if not condition:
            return []
        target = params.get("target", "self")
        if target == "target":
            # Ally-administered cure: "use X on <name>" resolves to the target.
            target = context.get("target_name") or (game_state.active_player if game_state else "")
        if game_state is not None:
            pname = self._resolve_player_name(game_state, target)
            game_state.conditions.remove_condition(pname, condition)
        msg = params.get("message", f"{condition} cured.")
        return [self._render_template_fn(msg, context)]

    def handle_apply_trait(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Apply a trait to a character.
        params: {"trait": "dark_vision", "target": "self", "param": true}

        SILENT by default — no announcement is emitted unless the trigger
        author explicitly sets ``message``. A cursed object can curse you
        without your knowledge; a button can flag someone else without telling
        the presser.
        """
        trait_id = params.get("trait", "")
        if not trait_id:
            return []
        target = params.get("target", "self")
        param_value = params.get("param", True)
        from engine.traits import TraitSystem
        trait_def = TraitSystem.get_definition(trait_id)
        label = trait_def["name"] if trait_def else trait_id
        if game_state is not None:
            pname = game_state.active_player if target == "self" else target
            player = game_state.players.get(pname)
            if player:
                conflicts = TraitSystem.conflicting_traits(player, trait_id)
                if conflicts:
                    # Conflict = a failed grant. Surface it to the SYSTEM log
                    # (event stream / UI) but never to the agent's action
                    # result — the character shouldn't meta-know their trait
                    # grants failed unless the author wrote a message for it.
                    if params.get("message"):
                        return [params["message"]]
                    if hasattr(game_state, "add_log_entry"):
                        conflict_names = ", ".join(
                            TraitSystem.get_definition(c).get("name", c) for c in conflicts
                        )
                        game_state.add_log_entry(
                            f"Trait conflict: {pname} couldn't gain {label} "
                            f"(conflicts with {conflict_names})."
                        )
                    return []
                player.traits[trait_id] = param_value
                # grants_conditions: trait-sourced conditions stay in sync
                TraitSystem.sync_granted_conditions(player)
                # Only surface an announcement when the author wrote one.
                if params.get("message"):
                    return [params["message"]]
                return []
        return [params["message"]] if params.get("message") else []

    def handle_remove_trait(
        self,
        params: dict,
        context: dict,
        item_node: Optional[Any] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Remove a trait from a character.
        params: {"trait": "dark_vision", "target": "self"}

        SILENT by default — only announces when ``message`` is explicitly set.
        """
        trait_id = params.get("trait", "")
        if not trait_id:
            return []
        target = params.get("target", "self")
        from engine.traits import TraitSystem
        trait_def = TraitSystem.get_definition(trait_id)
        label = trait_def["name"] if trait_def else trait_id
        if game_state is not None:
            pname = game_state.active_player if target == "self" else target
            player = game_state.players.get(pname)
            if player:
                if trait_id in player.traits:
                    del player.traits[trait_id]
                    TraitSystem.sync_granted_conditions(player)
                    # Only surface an announcement when the author wrote one.
                    if params.get("message"):
                        return [params["message"]]
                    return []
        return [params["message"]] if params.get("message") else []
