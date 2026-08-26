"""Trigger execution and effect-target resolution for TriggerSystem.

Moved from engine/trigger_system.py.
"""

import re
from typing import Any, List, Optional

from engine.triggers.effect_resolution import _resolve_trigger_effects

from graph import (
    EDGE_CARRYING,
    EDGE_CONNECTION,
    EDGE_EQUIPPED,
    EDGE_IN,
    EDGE_TRIGGERS,
    Node,
)


class ExecutionMixin:
    """Trigger walking, effect fan-out, and item/target lookup."""

    def _find_item_by_name(self, name: str, game_state=None):
        """Find an item node in the graph by name."""
        if not name:
            return None
        name_lower = name.lower()
        for node in self.graph.nodes.values():
            if node.type == "item":
                node_name = (node.name or node.properties.get("name", "")).lower()
                if node_name == name_lower:
                    return node
        return None

    def _find_target_node(self, name: str, game_state=None):
        """Resolve the used-on target node for an on_use_on interaction.

        Matches by name across *all* node types (items, ways, areas,
        characters), so tags can be checked on any of them. For ways,
        also tries exit-direction matching in the current area so phrases
        like "the north door" resolve to the door node.
        """
        if not name:
            return None
        needle = str(name).lower().strip()
        for node in self.graph.nodes.values():
            if (node.name or "").lower() == needle:
                return node
        if game_state is not None:
            try:
                area_id = game_state.get_current_area_id()
            except Exception:
                area_id = None
            if area_id:
                resolver = getattr(game_state, "resolve_exit", None)
                if resolver:
                    try:
                        _, way_node, _ = resolver(area_id, name)
                    except Exception:
                        way_node = None
                    if way_node:
                        return way_node
                matcher = getattr(game_state, "_match_exit_direction", None)
                matched_dir = None
                if matcher:
                    try:
                        matched_dir = matcher(area_id, name)
                    except Exception:
                        matched_dir = None
                if matched_dir:
                    for edge in self.graph.get_edges_for_source(area_id, EDGE_CONNECTION):
                        if edge.properties.get("direction", "") == matched_dir:
                            return self.graph.get_node(edge.target)
        return None

    def _render_template(self, text: str, context: dict) -> str:
        """Replace ``{variable}`` placeholders with values from *context*.

        Supported patterns:

        * ``{variable_name}`` — direct lookup in the context dict.
        * ``{param:<key>}`` — lookup in ``context['item_params']``.
        * ``{prop:<key>}`` — lookup in ``context['item_properties']``.

        Unrecognised variables are left unchanged.
        """
        if not text:
            return text
        item_props = context.get("item_properties", {})
        if item_props:
            text = re.sub(
                r"\{prop:(\w+)\}",
                lambda m: str(item_props.get(m.group(1), m.group(0))),
                text,
            )
        item_params = context.get("item_params", {})
        if item_params:
            text = re.sub(
                r"\{param:(\w+)\}",
                lambda m: str(item_params.get(m.group(1), m.group(0))),
                text,
            )
        for key, value in context.items():
            if key in ("item_params", "item_properties"):
                continue
            text = text.replace("{" + key + "}", str(value))
        return text

    def _get_current_area_id(self, item_node: Node, game_state: Any) -> Optional[str]:
        """Find the area ID for a given item node or game state."""
        if game_state and hasattr(game_state, 'get_current_area_id'):
            area_id = game_state.get_current_area_id()
            if area_id:
                return area_id
        # Fallback: search edges for this item's location
        for edge in self.graph.edges:
            if edge.source == item_node.id and edge.type == EDGE_IN:
                return edge.target
        return None

    def _get_items_by_tag_in_area(self, tag: str, status: Optional[str], area_id: str) -> List[Node]:
        """Get all item nodes in a area matching a tag (and optionally a status)."""
        if status:
            return self.graph.get_items_by_tag_and_status(tag, status, area_id)
        return self.graph.get_items_by_tag(tag, area_id)

    def _player_node_for_name(self, name: str) -> Optional[Node]:
        """Find a character node for a player display name (id may use a
        different separator/case than player_<name>)."""
        candidates = [
            f"player_{name}".replace(" ", "_"),
            f"player_{name}",
        ]
        for cid in candidates:
            node = self.graph.get_node(cid)
            if node:
                return node
        return next((n for n in self.graph.nodes.values()
                     if n.type in ("player", "character") and n.name == name), None)

    def _resolve_effect_targets(self, effect_params: dict, item_node: Node, game_state: Any = None) -> List[Node]:
        """Resolve the set of target nodes for an effect.

        Target spec (all optional, first matching wins):
          target_by: "name" | "tag" | "trait" | "type" | "all_in_area"
          target_value: the name / tag / trait / node type to match
          target_scope: "area" (default) | "world"
          target_tag: legacy tag fan-out (items in area)
          target_name: named target (character / node)

        Returns an empty list when there is no fan-out — the caller then runs
        the effect once against the default target (self / on_use_on target).
        """
        by = effect_params.get("target_by")
        value = effect_params.get("target_value")
        scope = effect_params.get("target_scope", "area")
        area_id = effect_params.get("area_id") or self._get_current_area_id(item_node, game_state)

        # Legacy tag fan-out (items in the area) — keep working.
        if not by:
            tag = effect_params.get("target_tag")
            if tag and area_id:
                require_status = effect_params.get("require_status")
                return self._get_items_by_tag_in_area(tag, require_status, area_id)
            if tag:
                return [n for n in self.graph.nodes.values() if tag in (n.properties.get("tags", []) or [])]
            return []

        if by == "name":
            name = str(value or "").lower()
            for node in self.graph.nodes.values():
                if node.name.lower() == name or node.id.lower() == name:
                    return [node]
            return []

        if by == "tag":
            tag = str(value or "").lower()
            # Characters: match against player.tags (live) — the graph node's
            # properties.tags may lag behind player mutations.
            if game_state is not None:
                players = getattr(game_state, "players", None) or {}
                char_results = []
                for pname, player in players.items():
                    if tag in [str(t).lower() for t in (player.tags or [])]:
                        node = self._player_node_for_name(pname)
                        if node:
                            char_results.append(node)
                if scope == "area" and area_id:
                    area_lower = area_id.lower()
                    char_results = [n for n in char_results
                                    if any(e.type == EDGE_IN and e.source == n.id and e.target.lower() == area_lower
                                           for e in self.graph.edges)]
                return char_results
            # No game state — fall back to graph tag scan.
            if scope == "world":
                return [n for n in self.graph.nodes.values()
                        if tag in [str(t).lower() for t in (n.properties.get("tags", []) or [])]]
            if area_id:
                return self._get_items_by_tag_in_area(tag, None, area_id)
            return []

        if by == "trait":
            trait = str(value or "").lower()
            if game_state is None:
                return []
            players = getattr(game_state, "players", None) or {}
            results = []
            for pname, player in players.items():
                if trait in [str(t).lower() for t in (player.traits or {}).keys()]:
                    node = self._player_node_for_name(pname)
                    if node:
                        results.append(node)
            return results

        if by == "type":
            node_type = str(value or "").lower()
            match_types = {node_type}
            if node_type in ("character", "player"):
                match_types = {"character", "player"}
            if scope == "world":
                return [n for n in self.graph.nodes.values() if n.type in match_types]
            if area_id:
                area_lower = area_id.lower()
                return [n for n in self.graph.nodes.values()
                        if n.type in match_types
                        and any(e.type == EDGE_IN and e.source == n.id and e.target.lower() == area_lower
                                for e in self.graph.edges)]
            return []

        if by == "all_in_area":
            if game_state is None or not area_id:
                return []
            players = getattr(game_state, "players", None) or {}
            area_lower = area_id.lower()
            results = []
            for pname, player in players.items():
                node = self._player_node_for_name(pname)
                if node and any(e.type == EDGE_IN and e.source == node.id and e.target.lower() == area_lower
                                for e in self.graph.edges):
                    results.append(node)
            return results

        return []

    def _execute_triggers(
        self,
        item_node: Node,
        trigger_type: str,
        target_name: Optional[str] = None,
        context: Optional[dict] = None,
        expected_target_state: Optional[str] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Execute all trigger edges from *item_node* matching *trigger_type*.

        Returns a list of output strings to append to the action result.

        Parameters
        ----------
        item_node : Node
            The item or node whose triggers should be evaluated.
        trigger_type : str
            The trigger type to match (e.g. ``"on_take"``, ``"on_use"``).
        target_name : str, optional
            Secondary target name (e.g. the target of ``on_use_on``).
        context : dict, optional
            Template-rendering context.  Auto-populated with default keys
            if not provided.
        expected_target_state : str, optional
            For ``on_state_enter`` / ``on_state_exit`` — the specific
            state to filter on.
        game_state : object, optional
            Duck-typed game state providing access to player data, area
            helpers, and scenario flags (see individual effect handler
            docstrings for requirements).

        *game_state* is consulted for the following when *context* is
        built or ``None``:

        * ``game_state.get_current_time()``
        * ``game_state.time_ticks``
        * ``game_state.turn_number``
        * ``game_state.active_player``
        * ``game_state.current_area``
        * ``game_state.player``
        """
        if item_node is None:
            return []
        outputs = []

        # ── Build template context ──
        if context is None:
            context = {}
        context.setdefault(
            "game_time",
            game_state.get_current_time() if game_state else "",
        )
        context.setdefault(
            "time_ticks", str(game_state.time_ticks) if game_state else ""
        )
        context.setdefault(
            "turn_number", str(game_state.turn_number) if game_state else ""
        )
        context.setdefault(
            "player_name", game_state.active_player if game_state else ""
        )
        context.setdefault(
            "area_name",
            game_state.current_area.name if game_state and game_state.current_area else "",
        )
        context.setdefault("item_name", item_node.name if item_node else "")
        context.setdefault(
            "item_state",
            item_node.properties.get("current_state", "") if item_node else "",
        )
        context.setdefault(
            "item_description",
            item_node.properties.get("description", "") if item_node else "",
        )
        context.setdefault("item_properties", item_node.properties if item_node else {})
        if item_node:
            context.setdefault(
                "item_params", item_node.properties.get("parameters", {})
            )
        if target_name is not None:
            context.setdefault("target_name", target_name)
        if game_state and game_state.player:
            context.setdefault(
                "player_hp", str(game_state.player.vitals.get("HP", 0))
            )
            context.setdefault(
                "player_energy",
                str(game_state.player.vitals.get("Energy", 0)),
            )
            context.setdefault(
                "player_sanity",
                str(game_state.player.vitals.get("Sanity", 0)),
            )
        if game_state and game_state.current_area:
            env = game_state.current_area.environment
            context.setdefault("area_light", str(env.get("light", "")))
            context.setdefault("area_temp", str(env.get("temperature", "")))
            context.setdefault("area_smell", env.get("smell", ""))

        # ── Walk trigger edges ──
        triggers = self.graph.get_edges_for_source(
            item_node.id, EDGE_TRIGGERS
        )
        for trigger_edge in triggers:
            trigger_types_on_edge = trigger_edge.properties.get("trigger_type", "")

            # ── Filter by trigger type ──
            if isinstance(trigger_types_on_edge, list):
                if trigger_type not in trigger_types_on_edge:
                    continue
                if trigger_type == "on_use_on" and target_name:
                    required_target = trigger_edge.properties.get(
                        "target_name", ""
                    ).lower()
                    if required_target and target_name.lower() != required_target:
                        continue
                    required_tag = trigger_edge.properties.get("target_tag", "")
                    if required_tag:
                        target_node = self._find_target_node(target_name, game_state)
                        if not target_node or required_tag not in (target_node.properties.get("tags", []) or []):
                            continue
            else:
                if (
                    trigger_types_on_edge == "on_use_on"
                    and target_name
                ):
                    required_target = trigger_edge.properties.get(
                        "target_name", ""
                    ).lower()
                    if required_target and target_name.lower() != required_target:
                        continue
                    required_tag = trigger_edge.properties.get("target_tag", "")
                    if required_tag:
                        target_node = self._find_target_node(target_name, game_state)
                        if not target_node or required_tag not in (target_node.properties.get("tags", []) or []):
                            continue
                elif trigger_types_on_edge != trigger_type and not (
                    trigger_types_on_edge.startswith("on_use_on")
                    and trigger_type == "on_use_on"
                ):
                    continue

            # ── Filter by expected target state ──
            if expected_target_state is not None:
                all_types = (
                    trigger_types_on_edge
                    if isinstance(trigger_types_on_edge, list)
                    else [trigger_types_on_edge]
                )
                if any(
                    type_name in ("on_state_enter", "on_state_exit")
                    for type_name in all_types
                ):
                    required_state = trigger_edge.properties.get(
                        "target_state", ""
                    )
                    if required_state and required_state != expected_target_state:
                        continue

            # ── Resolve conditions (backward-compatible lookup) ──
            conditions_list = trigger_edge.properties.get("conditions", None)
            if conditions_list is None:
                target_node = self.graph.get_node(trigger_edge.target)
                if target_node:
                    conditions_list = target_node.properties.get(
                        "conditions", None
                    )
            # Fallback: singular condition (legacy library format)
            if conditions_list is None or conditions_list == []:
                single = trigger_edge.properties.get("condition", None)
                if single is None:
                    target_node = self.graph.get_node(trigger_edge.target)
                    if target_node:
                        single = target_node.properties.get("condition", None)
                if single:
                    conditions_list = [single]
            if conditions_list is None:
                conditions_list = []

            # ── Resolve effects (effects[], or legacy effect_type/effect_params) ──
            effects_list = _resolve_trigger_effects(trigger_edge, self.graph)

            # ── Evaluate conditions (unified tree/flat) ──
            conditions_pass = True
            if conditions_list:
                cond_context = dict(context)
                cond_context["item_node"] = item_node
                if game_state is not None:
                    cond_context["game_state"] = game_state
                # Resolve the used-on target (on_use_on) up front so
                # target_has_tag conditions can inspect it. Ways resolve via
                # name or exit-direction; items/areas/characters by name.
                if trigger_type == "on_use_on" and target_name:
                    cond_context["target_node"] = self._find_target_node(
                        target_name, game_state
                    )
                if not isinstance(conditions_list, dict) or "operator" not in conditions_list:
                    # Flat list — apply conditions_logic
                    conditions_logic = trigger_edge.properties.get(
                        "conditions_logic", "and"
                    )
                    cond_tree = {
                        "operator": conditions_logic,
                        "conditions": conditions_list,
                    }
                else:
                    cond_tree = conditions_list

                conditions_pass = self._evaluate_conditions(
                    cond_tree, cond_context, game_state=game_state
                )

                if not conditions_pass:
                    fail_msg = (
                        effects_list[0]
                        .get("params", {})
                        .get("fail_message", "")
                        if effects_list
                        else ""
                    )
                    if fail_msg:
                        fail_msg = self._render_template(fail_msg, context)
                        outputs.append(fail_msg)

            # Surface skill-check / save roll messages
            if self._last_skill_check_msg:
                outputs.append(self._last_skill_check_msg)
                self._last_skill_check_msg = None
            if self._last_save_msg:
                outputs.append(self._last_save_msg)
                self._last_save_msg = None

            if not conditions_pass:
                continue

            # ── Execute all effects in order ──
            for effect in effects_list:
                effect_type = effect.get("type", "message")
                effect_params = effect.get("params", {})
                if not isinstance(effect_params, dict):
                    effect_params = {}

                if effect_params.get("success_message"):
                    effect_params = dict(effect_params)
                    effect_params["message"] = effect_params["success_message"]

                # Check for fan-out targeting (by name/tag/trait/type/all_in_area,
                # or legacy target_tag). When targets resolve, run the effect once
                # per target node; otherwise fall through to the single execution.
                targets = self._resolve_effect_targets(effect_params, item_node, game_state)
                if targets:
                    for target_node in targets:
                        # Build a context that references the target, not the trigger source
                        tag_context = dict(context)
                        tag_context["target_item_name"] = target_node.name
                        tag_context["target_item_state"] = target_node.properties.get("current_state", "")
                        tag_context["target_node"] = target_node
                        # For character targets, effect handlers resolve `target`
                        # against player names — pass the resolved name explicitly.
                        tparams = effect_params
                        if target_node.type in ("player", "character") and isinstance(effect_params, dict):
                            tparams = dict(effect_params)
                            tparams["target"] = tparams.get("target", "self")
                            if tparams["target"] in ("self", "all_in_area"):
                                tparams["target"] = target_node.name
                        outputs.extend(
                            self._effects.execute(
                                effect_type,
                                tparams,
                                tag_context,
                                item_node=target_node,
                                game_state=game_state,
                            )
                        )
                    continue  # skip the default single-item execution

                # For on_use_on, resolve target node for effects that need it
                target_item_node = None
                if trigger_type == "on_use_on" and target_name:
                    target_item_node = self._find_target_node(target_name, game_state)
                outputs.extend(
                    self._effects.execute(
                        effect_type,
                        effect_params,
                        context,
                        item_node=item_node,
                        target_item_node=target_item_node,
                        game_state=game_state,
                    )
                )

        return outputs
