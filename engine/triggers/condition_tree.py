"""Condition-tree evaluation for TriggerSystem.

Moved from engine/trigger_system.py.
"""

import random
import re
from typing import Any, Optional

from graph import EDGE_CARRYING, EDGE_EQUIPPED


class ConditionTreeMixin:
    """Tree and flat-list condition evaluation."""

    def _evaluate_conditions(
        self,
        conditions: Any,
        context: dict,
        game_state: Optional[Any] = None,
    ) -> bool:
        """Evaluate a condition tree against the given *context* dict.

        Accepts both tree format (dict with ``operator``/``conditions``)
        and flat list format (treated as AND group). Supports all
        condition types from NPC behavior AND item trigger systems.

        Returns ``True`` if conditions are met (or *conditions* is
        empty/``None``).  Unknown condition types return ``False``
        (fail-safe).
        """
        if not conditions:
            return True

        # Normalise list → AND tree
        if isinstance(conditions, list):
            conditions = {"operator": "and", "conditions": conditions}

        condition_type = conditions.get("type")
        if condition_type:
            item_node = context.get("item_node")
            gs = game_state or context.get("game_state")

            # --- NPC behaviour leaf types ---
            if condition_type == "eq":
                target_key = conditions.get("target")
                expected = conditions.get("value")
                actual = context.get(target_key)
                return actual == expected

            elif condition_type == "in_area":
                area_name = conditions.get("area")
                target = conditions.get("target", "npc")
                area_key = f"{target}_area"
                return context.get(area_key) == area_name

            elif condition_type == "tick_since_state":
                min_ticks = int(conditions.get("min_ticks", 0))
                enter_tick = context.get("state_enter_tick", 0)
                current_tick = context.get("current_tick", 0)
                return (current_tick - enter_tick) >= min_ticks

            elif condition_type == "proximity":
                max_areas = int(conditions.get("max_areas", 0))
                npc_area = context.get("npc_area")
                player_area = context.get("player_area")
                if max_areas == 0:
                    return npc_area == player_area
                if npc_area == player_area:
                    return True
                if max_areas >= 1 and npc_area:
                    npc_exits = (
                        gs._build_exits_for_area(npc_area)
                        if gs
                        else {}
                    )
                    for exit_data in npc_exits.values():
                        if exit_data.get("target") == player_area:
                            return True
                return False

            # --- Shared leaf types (NPC + item triggers) ---
            elif condition_type in ("has_item", "random_chance"):
                if condition_type == "random_chance":
                    chance_val = conditions.get("chance")
                    if chance_val is None:
                        chance_val = conditions.get("value", 0)
                    try:
                        threshold = float(chance_val)
                        # `chance` uses 0.0–1.0 (NPC behaviors); `value` uses 0–100 (item triggers).
                        if chance_val is conditions.get("value"):
                            threshold /= 100.0
                        elif threshold > 1.0:
                            threshold /= 100.0
                        return random.random() < threshold
                    except (ValueError, TypeError):
                        return False

                # has_item — check player inventory via graph
                item_name = (
                    conditions.get("item")
                    or conditions.get("value")
                    or ""
                )
                if not item_name:
                    return False
                # Try NPC-style context inventory first
                target = conditions.get("target", "player")
                inv_key = f"{target}_inventory"
                inventory = context.get(inv_key, [])
                if inventory:
                    return any(
                        item_name in i.get("name", "")
                        or item_name in i.get("id", "")
                        for i in inventory
                    )
                # Fallback to graph-based inventory lookup (item trigger style)
                if gs is None or not hasattr(gs, '_player_node_id'):
                    return False
                player_id = gs._player_node_id(gs.active_player)
                inv_edges = self.graph.get_edges_for_target(
                    player_id, EDGE_CARRYING
                )
                needle = str(item_name).lower()
                return any(
                    (node := self.graph.get_node(edge.source))
                    and node.type == "item"
                    and (needle in node.name.lower() or needle in node.id.lower())
                    for edge in inv_edges
                )

            # --- Item trigger leaf types ---
            elif condition_type == "parameter_reached":
                # Gate on a gauge in the node's `parameters` dict (task-410:
                # plant growth reaching 100). Counters live in `parameters`
                # because `uses` is remaining charges/durability — a gauge that
                # starts at 0 would read as depleted and hit the <=0 removal
                # paths. `op` defaults to gte.
                if item_node is None:
                    return False
                key = str(
                    conditions.get("key") or conditions.get("parameter") or ""
                ).strip()
                if not key:
                    return False
                params_map = item_node.properties.get("parameters") or {}
                if not isinstance(params_map, dict):
                    return False
                try:
                    actual = float(params_map.get(key, 0))
                    threshold = float(conditions.get("value", 0))
                except (TypeError, ValueError):
                    return False
                op = str(conditions.get("op", "gte")).lower()
                if op in ("gt", ">"):
                    return actual > threshold
                if op in ("gte", ">="):
                    return actual >= threshold
                if op in ("lt", "<"):
                    return actual < threshold
                if op in ("lte", "<="):
                    return actual <= threshold
                if op in ("eq", "=="):
                    return actual == threshold
                return False

            elif condition_type == "contains_count":
                # Count what a container holds, optionally filtered to a name/id
                # substring — the produce cap for a plant ("fewer than 10
                # berries"). `op` defaults to gte; `contains_count` with op `lt`
                # is "has room for more".
                if item_node is None:
                    return False
                rel = str(conditions.get("relation", "in")).lower().strip() or "in"
                try:
                    edges = self.graph.get_edges_for_target(item_node.id, rel)
                except Exception:
                    return False
                needle = str(conditions.get("target", "") or "").strip().lower()
                count = 0
                for edge in edges:
                    if needle:
                        other = self.graph.get_node(edge.source)
                        if other is None or not (
                            needle in str(other.name or "").lower()
                            or needle in str(other.id).lower()
                        ):
                            continue
                    count += 1
                try:
                    threshold = float(conditions.get("value", 0))
                except (TypeError, ValueError):
                    return False
                op = str(conditions.get("op", "gte")).lower()
                if op in ("gt", ">"):
                    return count > threshold
                if op in ("gte", ">="):
                    return count >= threshold
                if op in ("lt", "<"):
                    return count < threshold
                if op in ("lte", "<="):
                    return count <= threshold
                if op in ("eq", "=="):
                    return count == threshold
                return False

            elif condition_type == "uses_reached":
                try:
                    target_uses = int(conditions.get("value", 0))
                    current_uses = (
                        int(item_node.properties.get("uses", -1))
                        if item_node
                        else -1
                    )
                    return current_uses <= target_uses
                except (ValueError, TypeError):
                    return False

            elif condition_type == "uses_above":
                try:
                    target_uses = int(conditions.get("value", 0))
                    current_uses = (
                        int(item_node.properties.get("uses", -1))
                        if item_node
                        else -1
                    )
                    return current_uses > target_uses
                except (ValueError, TypeError):
                    return False

            elif condition_type == "sound_heard":
                # Check if character has heard a specific sound pattern recently
                sound_pattern = conditions.get("pattern", "").lower()
                if gs is None or not hasattr(gs, 'players'):
                    return False
                player = gs.players.get(gs.active_player) if gs.active_player else None
                if not player:
                    return False

                # Check recent_hearing for matching sound
                recent_hearing = getattr(player, "recent_hearing", [])
                for entry in recent_hearing:
                    if entry.get("type") == "sound_source":
                        heard_pattern = entry.get("sound_pattern", "").lower()
                        if sound_pattern in heard_pattern or heard_pattern in sound_pattern:
                            return True
                    elif entry.get("type") == "speech":
                        # Also check for speech if pattern matches
                        heard_text = entry.get("text", "").lower()
                        if sound_pattern and sound_pattern in heard_text:
                            return True
                return False

            elif condition_type == "speech_matches":
                # Match the spoken text of an on_speech trigger against a phrase.
                # Reads `speech` from the trigger context (set by broadcast_speech).
                spoken = str(context.get("speech", "")).lower()
                phrase = str(conditions.get("phrase", "") or conditions.get("value", "")).lower()
                mode = str(conditions.get("mode", "contains")).lower()
                if not phrase or not spoken:
                    return False
                if mode == "exact":
                    return spoken.strip() == phrase.strip()
                if mode == "contains":
                    return phrase in spoken
                if mode == "not_contains":
                    return phrase not in spoken
                if mode == "startswith":
                    return spoken.strip().startswith(phrase.strip())
                if mode == "endswith":
                    return spoken.strip().endswith(phrase.strip())
                # word-boundary aware substring ("fuzzy")
                return re.search(rf"\b{re.escape(phrase)}\b", spoken) is not None

            elif condition_type == "has_items":
                items = conditions.get("value", [])
                if not isinstance(items, list) or not items:
                    return False
                if gs is None or not hasattr(gs, '_player_node_id'):
                    return False
                player_id = gs._player_node_id(gs.active_player)
                inv_edges = self.graph.get_edges_for_target(
                    player_id, EDGE_CARRYING
                )
                for item_name in items:
                    needle = str(item_name).lower()
                    found = any(
                        (node := self.graph.get_node(edge.source))
                        and node.type == "item"
                        and (needle in node.name.lower() or needle in node.id.lower())
                        for edge in inv_edges
                    )
                    if not found:
                        return False
                return True

            elif condition_type == "state_equals":
                condition_value = conditions.get("value", "")
                target_name = conditions.get("target", "")
                if target_name:
                    needle = str(target_name).lower()
                    target_node = None
                    for node_id, node in self.graph.nodes.items():
                        if needle in node.name.lower() or needle in node_id.lower():
                            target_node = node
                            break
                    if target_node:
                        expected_state = str(condition_value)
                        return (
                            target_node.properties.get("current_state", "")
                            == expected_state
                        )
                    return False
                if "=" in condition_value:
                    parts = condition_value.split("=", 1)
                    node_id = parts[0].strip()
                    expected_state = parts[1].strip()
                    target_node = self.graph.get_node(node_id) if node_id else None
                    if target_node:
                        return (
                            target_node.properties.get("current_state", "")
                            == expected_state
                        )
                    return False
                if item_node:
                    return (
                        item_node.properties.get("current_state", "")
                        == condition_value
                    )
                return False

            elif condition_type == "skill_check":
                skill = conditions.get("skill", "Athletics")
                dc = int(conditions.get("dc", 10))
                success, total, msg = self.skills.skill_check(skill, dc)
                self._last_skill_check_msg = msg
                return success

            elif condition_type == "save_throw":
                # Unified save condition (task-159) — see the flat-condition
                # branch above for semantics.
                check = conditions.get("stat") or conditions.get("skill") or "DEX"
                dc = int(conditions.get("dc", 12))
                player = self._resolve_save_target(conditions.get("target", "self"), gs)
                if player is None:
                    return False
                success, total, msg = self.skills.saving_throw(player, check, dc)
                self._last_save_msg = msg
                return success

            elif condition_type == "temperature_below":
                try:
                    threshold = int(conditions.get("value", 0))
                    area_id = (
                        gs._get_current_area_id()
                        if gs and hasattr(gs, '_get_current_area_id')
                        else None
                    )
                    if area_id:
                        area_node = self.graph.get_node(area_id)
                        if area_node:
                            current = int(
                                area_node.properties.get("environment", {}).get(
                                    "temperature", 21
                                )
                            )
                            return current < threshold
                except (ValueError, TypeError):
                    pass
                return False

            elif condition_type == "temperature_above":
                try:
                    threshold = int(conditions.get("value", 0))
                    area_id = (
                        gs._get_current_area_id()
                        if gs and hasattr(gs, '_get_current_area_id')
                        else None
                    )
                    if area_id:
                        area_node = self.graph.get_node(area_id)
                        if area_node:
                            current = int(
                                area_node.properties.get("environment", {}).get(
                                    "temperature", 21
                                )
                            )
                            return current > threshold
                except (ValueError, TypeError):
                    pass
                return False

            elif condition_type == "area_temp":
                try:
                    threshold = float(conditions.get("value", 0))
                    operator = conditions.get("operator", "lt")
                    area_id = (
                        gs._get_current_area_id()
                        if gs and hasattr(gs, '_get_current_area_id')
                        else None
                    )
                    if area_id:
                        area_node = self.graph.get_node(area_id)
                        if area_node:
                            current = int(
                                area_node.properties.get("environment", {}).get(
                                    "temperature", 21
                                )
                            )
                            return self._compare(current, threshold, operator)
                except (ValueError, TypeError):
                    pass
                return False

            elif condition_type == "vital":
                try:
                    stat = conditions.get("stat", "HP")
                    threshold = float(conditions.get("value", 0))
                    operator = conditions.get("operator", "lt")
                    player = self._resolve_condition_player(conditions.get("target", "self"), gs)
                    if not player:
                        return False
                    current = player.vitals.get(stat)
                    if current is None:
                        return False
                    return self._compare(current, threshold, operator)
                except (ValueError, TypeError):
                    return False

            elif condition_type == "vital_above":
                try:
                    stat = conditions.get("stat", "HP")
                    threshold = float(conditions.get("value", 0))
                    player = self._resolve_condition_player(conditions.get("target", "self"), gs)
                    if not player:
                        return False
                    current = player.vitals.get(stat)
                    if current is None:
                        return False
                    return self._compare(current, threshold, "gt")
                except (ValueError, TypeError):
                    return False

            elif condition_type == "vital_below":
                try:
                    stat = conditions.get("stat", "HP")
                    threshold = float(conditions.get("value", 0))
                    player = self._resolve_condition_player(conditions.get("target", "self"), gs)
                    if not player:
                        return False
                    current = player.vitals.get(stat)
                    if current is None:
                        return False
                    return self._compare(current, threshold, "lt")
                except (ValueError, TypeError):
                    return False

            elif condition_type == "is_equipped":
                if gs is None:
                    return False
                player = self._resolve_condition_player(conditions.get("target", "self"), gs)
                if not player:
                    return False
                player_id = getattr(gs, "_player_node_id", lambda n: f"player_{n}")(player.name)
                needle = str(conditions.get("item", "")).lower()
                if not needle:
                    return False
                equipped_edges = self.graph.get_edges_for_target(player_id, EDGE_EQUIPPED)
                return any(
                    (node := self.graph.get_node(edge.source))
                    and node.type == "item"
                    and (needle in node.name.lower() or needle in node.id.lower())
                    for edge in equipped_edges
                )

            elif condition_type == "time_of_day":
                target = str(conditions.get("value", "")).strip()
                if not target:
                    return False
                current = None
                if gs is not None and hasattr(gs, "get_current_time"):
                    try:
                        current = str(gs.get_current_time())
                    except Exception:
                        current = None
                if not current:
                    return False
                target_hm = target[:5]
                return current[:5] == target_hm

            elif condition_type == "area_has_status":
                # task-233: does an area carry a dynamic status? Blank target =
                # the area the triggering node sits in / current area.
                status_type = str(conditions.get("status_type") or conditions.get("value") or "").strip()
                if not status_type:
                    return False
                target_area = str(conditions.get("target") or "").strip()
                if not target_area and gs is not None:
                    resolver = getattr(gs, "get_current_area_id", None)
                    if callable(resolver):
                        target_area = resolver() or ""
                system = getattr(gs, "area_statuses", None) if gs is not None else None
                if system is None:
                    return False
                return bool(system.has_status(target_area, status_type))

            elif condition_type == "weather":
                if gs is None:
                    return False
                area_id = (
                    gs._get_current_area_id()
                    if hasattr(gs, '_get_current_area_id')
                    else None
                )
                if not area_id:
                    return False
                area_node = self.graph.get_node(area_id)
                if not area_node:
                    return False
                current = area_node.properties.get("environment", {}).get("weather", "")
                return str(current).lower() == str(conditions.get("value", "")).lower()

            elif condition_type == "has_trait":
                from engine.traits import TraitSystem
                if gs is None:
                    return False
                player = self._resolve_condition_player(conditions.get("target", "self"), gs)
                if not player:
                    return False
                return TraitSystem.has_trait(player, conditions.get("value", ""))

            elif condition_type == "has_tag":
                needle_values = conditions.get("value") or []
                if isinstance(needle_values, str):
                    needle_values = [needle_values]
                needle_values = [str(v).strip().lower() for v in needle_values if str(v).strip()]
                if not needle_values:
                    return False
                target = conditions.get("target", "self")
                if target == "target":
                    # The used-on node of an on_use_on trigger (way/item/area/character)
                    node = context.get("target_node")
                    if node is None:
                        return False
                    tags = node.properties.get("tags", []) if node.properties else []
                else:
                    if gs is None:
                        return False
                    player = self._resolve_condition_player(target, gs)
                    if not player:
                        return False
                    tags = player.tags or []
                if isinstance(tags, str):
                    tags = [t.strip() for t in tags.split(",")]
                return any(str(t).lower() in needle_values for t in tags)

            elif condition_type == "target_has_tag":
                # Backward-compat alias for the unified has_tag (target = used-on node).
                target_node = context.get("target_node")
                if target_node is None:
                    return False
                needle_values = conditions.get("value") or []
                if isinstance(needle_values, str):
                    needle_values = [needle_values]
                needle_values = [str(v).strip().lower() for v in needle_values if str(v).strip()]
                tags = target_node.properties.get("tags", []) if target_node.properties else []
                if isinstance(tags, str):
                    tags = [t.strip() for t in tags.split(",")]
                return any(str(t).lower() in needle_values for t in tags)

            elif condition_type == "item_relationship":
                # True when the triggering item has a spatial/master edge of the
                # given type (task-308: "does this item have anything inside?"
                # → relation "in"). Optionally filtered to a specific target.
                if item_node is None:
                    return False
                rel = str(conditions.get("relation", "in")).lower().strip()
                if not rel:
                    return False
                # "in" reads item-inside-item edges as "things inside me"
                # (edges INTO self); on/under/behind/beside/at read outward.
                default_dir = "target" if rel == "in" else "source"
                outward = str(conditions.get("direction", default_dir)).lower() != "target"
                try:
                    if outward:
                        edges = self.graph.get_edges_for_source(item_node.id, rel)
                    else:
                        edges = self.graph.get_edges_for_target(item_node.id, rel)
                except Exception:
                    return False
                target = str(conditions.get("target", "") or "").strip()
                if not target:
                    return bool(edges)
                low = target.lower()
                for edge in edges:
                    other_id = edge.target if outward else edge.source
                    other = self.graph.get_node(other_id)
                    if other is not None and (
                        low in str(other.name or "").lower() or low in str(other_id).lower()
                    ):
                        return True
                return False

            # --- Phase 1 NPC behavior conditions ---

            elif condition_type == "npc_emotion_is":
                emotion = conditions.get("emotion", "")
                operator = conditions.get("operator", "eq")
                threshold = float(conditions.get("value", 0))
                target = conditions.get("target", "self")
                if gs is None:
                    return False
                player = self._resolve_condition_player(target, gs)
                if not player:
                    return False
                current_name = getattr(player, "emotion", "") or ""
                current_intensity = float(getattr(player, "emotion_intensity", 0) or 0)
                if operator == "eq":
                    return current_name == emotion
                return self._compare(current_intensity, threshold, operator)

            elif condition_type == "npc_is_hidden":
                expect = bool(conditions.get("value", True))
                target = conditions.get("target", "self")
                if gs is None:
                    return expect is False
                player = self._resolve_condition_player(target, gs)
                if not player:
                    return expect is False
                return getattr(player, "hidden", False) is expect

            elif condition_type == "character_has_tag":
                needle = str(conditions.get("tag", "")).strip().lower()
                if not needle:
                    return False
                target = conditions.get("target", "self")
                if target == "triggering":
                    char = context.get("triggering_character")
                    if char is None:
                        return False
                    tags = getattr(char, "tags", []) or []
                elif gs is None:
                    return False
                else:
                    player = self._resolve_condition_player(target, gs)
                    if not player:
                        return False
                    tags = getattr(player, "tags", []) or []
                if isinstance(tags, str):
                    tags = [t.strip() for t in tags.split(",")]
                return any(str(t).lower() == needle for t in tags)

            # --- Phase 2 NPC behavior conditions (task-390) ---

            elif condition_type == "player_has_tag":
                tag = str(conditions.get("tag") or conditions.get("value") or "").strip().lower()
                if not tag or gs is None:
                    return False
                player = self._resolve_condition_player(conditions.get("target", "player"), gs)
                if player is None:
                    return False
                return tag in self._player_item_tags(player, gs)

            elif condition_type == "sight_holds":
                # The NPC can see a tag on the target only when they share an
                # area and the target is not hidden.
                tag = str(conditions.get("tag") or conditions.get("value") or "").strip().lower()
                if not tag or gs is None:
                    return False
                player = self._resolve_condition_player(conditions.get("target", "player"), gs)
                if player is None:
                    return False
                if getattr(player, "hidden", False):
                    return False
                npc_area = context.get("npc_area")
                if npc_area and getattr(player, "current_area", None) != npc_area:
                    return False
                return tag in self._player_item_tags(player, gs)

            elif condition_type == "flag_equals":
                key = str(conditions.get("key", "")).strip()
                if not key or gs is None:
                    return False
                target = conditions.get("target", "self")
                if target == "triggering":
                    char = context.get("triggering_character")
                else:
                    char = self._resolve_condition_player(target, gs)
                if char is None:
                    return False
                flags = getattr(char, "flags", None) or {}
                actual = flags.get(key)
                expected = conditions.get("value", True)
                if isinstance(expected, str):
                    low = expected.strip().lower()
                    if low in ("true", "false"):
                        expected = (low == "true")
                    else:
                        try:
                            expected = float(low) if "." in low else int(low)
                        except ValueError:
                            pass
                return actual == expected

            elif condition_type == "sound_above":
                try:
                    threshold = float(conditions.get("threshold", conditions.get("value", 0.5)))
                except (TypeError, ValueError):
                    threshold = 0.5
                # 0–1 authored threshold maps onto the engine's 0–3 levels.
                raw_needed = threshold * 3.0 if threshold <= 1.0 else threshold
                if gs is None:
                    return False
                player = self._resolve_condition_player(conditions.get("target", "self"), gs)
                if player is None:
                    return False
                for entry in (getattr(player, "recent_hearing", None) or []):
                    if self._recent_sound_strength(entry) >= raw_needed:
                        return True
                return False

            elif condition_type == "smell_detected":
                from engine.room_perception import visible_area_items
                tag = str(conditions.get("tag") or conditions.get("value") or "").strip().lower()
                if not tag:
                    return False
                try:
                    rng = int(conditions.get("range", 0) or 0)
                except (TypeError, ValueError):
                    rng = 0
                area_name = context.get("npc_area")
                if not area_name and gs is not None:
                    area_name = getattr(getattr(gs, "player", None), "current_area", None)
                for area in self._areas_within(gs, area_name, rng):
                    area_id = self._area_id(area)
                    for node in visible_area_items(self.graph, area_id):
                        if tag in self._condition_node_tags(node):
                            return True
                return False

            return False

        operator = conditions.get("operator")
        if operator:
            sub_conditions = conditions.get("conditions", [])
            if operator == "and":
                return all(
                    self._evaluate_conditions(c, context, game_state=game_state)
                    for c in sub_conditions
                )
            elif operator == "or":
                return any(
                    self._evaluate_conditions(c, context, game_state=game_state)
                    for c in sub_conditions
                )
            elif operator == "not":
                return (
                    not self._evaluate_conditions(
                        sub_conditions[0], context, game_state=game_state
                    )
                    if sub_conditions
                    else True
                )
            return False

        return False

    # ────────────────── task-390 condition helpers ──────────────────

    @staticmethod
    def _condition_node_tags(node) -> list:
        """Normalised lowercase tag list for a graph node."""
        if node is None or not getattr(node, "properties", None):
            return []
        tags = node.properties.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        return [str(t).strip().lower() for t in tags if str(t).strip()]

    def _player_item_tags(self, player, game_state) -> list:
        """Tags of everything a character carries or wears (task-390)."""
        if player is None:
            return []
        tags = []
        for stack in (getattr(player, "equipped", None) or {}).values():
            for item_id in stack or []:
                node = self.graph.get_node(item_id) if item_id else None
                tags.extend(self._condition_node_tags(node))
        resolver = getattr(game_state, "_player_node_id", None)
        if not callable(resolver):
            pm = getattr(game_state, "player_manager", None)
            resolver = getattr(pm, "get_player_node_id", None)
        if callable(resolver):
            try:
                node_id = resolver(player.name)
                for edge in self.graph.get_edges_for_target(node_id, EDGE_CARRYING):
                    node = self.graph.get_node(edge.source)
                    if node is not None and node.type == "item":
                        tags.extend(self._condition_node_tags(node))
            except Exception:
                pass
        return tags

    def _area_id(self, area_name):
        """Resolve an area name to its node id (canonical first, then scan)."""
        if not area_name:
            return None
        from engine.node_ids import NodeIDHelper
        candidate = NodeIDHelper.area_node_id(area_name)
        if self.graph.get_node(candidate) is not None:
            return candidate
        for node in self.graph.nodes.values():
            if node.type == "area" and node.name == area_name:
                return node.id
        return None

    def _areas_within(self, game_state, area_name, range_areas: int) -> list:
        """The area plus up to *range_areas* hops of neighbours (task-390 smell)."""
        if not area_name:
            return []
        areas = [area_name]
        seen = {area_name}
        frontier = [area_name]
        for _ in range(max(0, int(range_areas or 0))):
            nxt = []
            for area in frontier:
                if game_state is None or not hasattr(game_state, "_build_exits_for_area"):
                    break
                try:
                    exits = game_state._build_exits_for_area(area) or {}
                except Exception:
                    exits = {}
                for exit_data in exits.values():
                    target = exit_data.get("target")
                    if target and target not in seen:
                        seen.add(target)
                        nxt.append(target)
                        areas.append(target)
            frontier = nxt
            if not frontier:
                break
        return areas

    @staticmethod
    def _recent_sound_strength(entry) -> float:
        """Raw 0–3 sound strength for a ``recent_hearing`` entry (−1 = unknown)."""
        if not isinstance(entry, dict):
            return -1.0
        raw = entry.get("sound_level")
        if raw is None:
            raw = entry.get("strength")
        if raw is None:
            from engine.sound import SPEECH_LEVELS
            raw = SPEECH_LEVELS.get(str(entry.get("speech_level", "")).lower())
        if raw is None:
            return -1.0
        try:
            return float(raw)
        except (TypeError, ValueError):
            return -1.0
