"""Use verbs (use / use on) for ItemActions.

Moved verbatim from engine/item_actions.py as part of the task-314
verb-family split. Methods hang off the ItemActions context (graph,
matching, trigger_system, world) via the mixin.
"""

import random
import time
from typing import Optional

from graph import (
    EDGE_CARRYING,
    EDGE_CONNECTION,
    EDGE_IN,
    EDGE_TRIGGERS,
    EDGE_UNLOCKS,
)


class UseActionsMixin:
    """use_item / use_item_on plus the descriptive-target failure fallback."""

    def use_item(self, player_manager, item_name: str, trigger_type: str = "on_use") -> str:
        ghost_block = self.ghost_system.check_ghost_action(player_manager, "use", item_name)
        if ghost_block:
            raise ValueError(ghost_block)

        item_node = player_manager.find_item_node(item_name)
        if not item_node:
            # Not carried — anything reachable counts (room fixtures,
            # surfaces, open containers, equipped backpack contents).
            from engine.item_reach import find_reachable
            item_node = find_reachable(self.graph, self.matching, player_manager, item_name)
        if not item_node:
            raise ValueError(f"You don't have '{item_name}'.")

        # Frightened (item source): won't touch the item they fear
        if player_manager.player.has_condition("frightened"):
            from engine.conditions import frightened_block
            block = frightened_block(
                player_manager.player, "item",
                source_id=item_node.id, source_name=item_node.name,
            )
            if block:
                raise ValueError(block)

        tags = item_node.properties.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        if "toggleable" in tags:
            if hasattr(player_manager, 'toggle_item_status'):
                return player_manager.toggle_item_status(item_name)

        if player_manager.player.state in ["sleeping", "unconscious", "bound"]:
            raise ValueError(f"You can't use items while {player_manager.player.state}.")
        if player_manager.player.state == "dead" and not player_manager.ghost_mode:
            raise ValueError("Your body lies still. You can do nothing.")

        item_actions = item_node.properties.get("actions", [])
        if isinstance(item_actions, str):
            item_actions = [a.strip() for a in item_actions.split(",")]
        trigger_edges = self.graph.get_edges_for_source(item_node.id, EDGE_TRIGGERS)
        has_any_trigger = len(trigger_edges) > 0

        contextual_verb = "use"
        if trigger_type == "on_eat":
            contextual_verb = "eat"
        elif trigger_type == "on_drink":
            contextual_verb = "drink"

        is_valid = contextual_verb == "use" and ("use" in item_actions or has_any_trigger)
        if not is_valid:
            available = self.trigger_system._get_available_actions(item_node)
            raise ValueError(self.trigger_system._contextual_failure(contextual_verb, item_node.name, available))

        result = f"You use the {item_name}."
        if hasattr(player_manager.player, 'exhaustion_count') and player_manager.player.exhaustion_count > 0:
            player_manager.player.exhaustion_count = 0

        area_id = player_manager._get_current_area_id()
        area_node = self.graph.get_node(area_id) if area_id else None
        old_light = area_node.properties.get("environment", {}).get("light", 80) if area_node else None

        trigger_outputs = self._exec_triggers(item_node, trigger_type)
        if trigger_type != "on_use":
            use_outputs = self._exec_triggers(item_node, "on_use")
            trigger_outputs = use_outputs + trigger_outputs
        # Fallback: if using item with no on_use triggers, try on_drink/on_eat/on_read
        if not trigger_outputs and trigger_type == "on_use":
            for fallback_type in ["on_drink", "on_eat", "on_read"]:
                fallback_outputs = self._exec_triggers(item_node, fallback_type)
                if fallback_outputs:
                    trigger_outputs = fallback_outputs
                    break
        if trigger_outputs:
            result += "\n" + "\n".join(trigger_outputs)

        # #6: system-visible light change feedback
        if old_light is not None and area_node and self.graph.get_node(area_node.id):
            new_light = area_node.properties.get("environment", {}).get("light", 80)
            if old_light != new_light:
                old_level = self.world.lighting.light_to_level(old_light)
                new_level = self.world.lighting.light_to_level(new_light)
                change_text = "brightens" if new_light > old_light else "darkens"
                result += f" The {area_node.name} {change_text}."
                self.world.add_log_entry(
                    f"[System] {player_manager.active_player} used {item_name} in {area_node.name}, "
                    f"light changed from {old_level} to {new_level}"
                )

        if not self.graph.get_node(item_node.id):
            return result

        skill_check_config = item_node.properties.get("skill_check", {})
        if skill_check_config and skill_check_config.get("skill"):
            skill_name = skill_check_config["skill"]
            dc = skill_check_config.get("dc", 10)
            success, total, message = player_manager.skill_check(skill_name, dc)
            result += " " + message
            if not success:
                result += f" You fail to use the {item_name} properly."
                return result

        p_check = player_manager.players.get(player_manager.active_player)
        if not (p_check and p_check.state == "dead"):
            item_cost = item_node.properties.get("action_costs", {}).get("use", {})
            player_manager.apply_action("use", item_cost, player=player_manager.player)

        effect_target = item_node.properties.get("effect_target")
        effect_stat = item_node.properties.get("effect_stat")
        effect_amount = item_node.properties.get("effect_amount")
        if effect_target and effect_stat:
            try:
                amt = int(effect_amount)
            except (ValueError, TypeError):
                amt = 0
            if effect_target == "self":
                if effect_stat in player_manager.player.vitals:
                    old = player_manager.player.vitals[effect_stat]
                    new_val = max(0, min(100, old + amt))
                    player_manager.player.vitals[effect_stat] = new_val
                    result += f" Your {effect_stat} changes to {new_val}."
            elif effect_target == "player" and effect_stat in player_manager.player.vitals:
                old = player_manager.player.vitals[effect_stat]
                new_val = max(0, min(100, old + amt))
                player_manager.player.vitals[effect_stat] = new_val
                result += f" Your {effect_stat} changes to {new_val}%."

        uses = item_node.properties.get("uses", -1)
        if uses > 0:
            uses -= 1
            item_node.properties["uses"] = uses
            if uses == 0:
                loc_edges = self.graph.edges.copy()
                for e in loc_edges:
                    if e.source == item_node.id and e.type == EDGE_IN:
                        self.graph.edges.remove(e)
                        result += " The item is used up!"
                        break

        area_name = player_manager.current_area.name if player_manager.current_area else None
        player_manager.record_turn_event(player_manager.active_player, "use", f"used the {item_name}", area_name=area_name)

        # #12: return item to its last known location after use (if in inventory, not equipped)
        if uses != 0 and self.graph.get_node(item_node.id):
            player_id = player_manager._player_node_id(player_manager.active_player)
            is_carrying = any(e.source == item_node.id and e.target == player_id and e.type == EDGE_CARRYING
                              for e in self.graph.edges)
            if is_carrying:
                restored = self._restore_last_relation(item_node, player_manager, area_id)
                if restored:
                    result += f" You set the {item_name} back down."

        return result

    def use_item_on(self, player_manager, item_name: str, target_name: str = None, params: str = None) -> str:
        if not target_name:
            return self.use_item(player_manager, item_name)

        ghost_block = self.ghost_system.check_ghost_action(player_manager, "use", item_name)
        if ghost_block:
            raise ValueError(ghost_block)

        if not player_manager.current_area:
            raise ValueError("You are in an empty void.")

        if not player_manager.lighting.can_see_in_dark(player_manager, player_manager.active_player):
            area_id = player_manager._get_current_area_id()
            ambient = player_manager.lighting.get_ambient_light(area_id, player_manager.current_area.environment)
            if ambient < 20:
                raise ValueError("It's too dark to see what you're doing.")

        if player_manager.player.state in ["sleeping", "unconscious", "bound"]:
            raise ValueError(f"You can't use items while {player_manager.player.state}.")
        if player_manager.player.state == "dead" and not player_manager.ghost_mode:
            raise ValueError("Your body lies still. You can do nothing.")

        item_node = player_manager.find_item_node(item_name)
        if not item_node:
            # Tool doesn't have to be in hand — reachable counts
            # ("use the crowbar on the crate" with it lying on the floor).
            from engine.item_reach import find_reachable
            item_node = find_reachable(self.graph, self.matching, player_manager, item_name)
        if not item_node:
            raise ValueError(f"You don't have '{item_name}'.")

        # Frightened (item source): won't touch the item they fear
        if player_manager.player.has_condition("frightened"):
            from engine.conditions import frightened_block
            block = frightened_block(
                player_manager.player, "item",
                source_id=item_node.id, source_name=item_node.name,
            )
            if block:
                raise ValueError(block)

        item_actions = item_node.properties.get("actions", [])
        if isinstance(item_actions, str):
            item_actions = [a.strip() for a in item_actions.split(",")]
        trigger_edges = self.graph.get_edges_for_source(item_node.id, EDGE_TRIGGERS)
        has_on_use_on = False
        for te in trigger_edges:
            trigger_node = self.graph.get_node(te.target)
            if trigger_node:
                tt = trigger_node.properties.get("trigger_type", "")
                if isinstance(tt, list):
                    if "on_use_on" in tt:
                        has_on_use_on = True
                        break
                elif tt == "on_use_on":
                    has_on_use_on = True
                    break
        if "use" not in item_actions and not has_on_use_on:
            available = self.trigger_system._get_available_actions(item_node)
            raise ValueError(self.trigger_system._contextual_failure("use", item_node.name, available))

        if params:
            target_node = player_manager.find_item_node(target_name)
            if not target_node:
                from engine.item_reach import find_reachable
                target_node = find_reachable(self.graph, self.matching, player_manager, target_name)
            if target_node:
                old_desc = target_node.properties.get("description", "")
                target_node.properties["description"] = old_desc + f"\n[Inscribed: \"{params}\"]"
                target_node.updated = time.time()
                area_name = player_manager.current_area.name if player_manager.current_area else None
                player_manager.record_turn_event(player_manager.active_player, "use", f"wrote on the {target_name}: \"{params}\"", area_name=area_name)
                return f"You use the {item_name} on the {target_name}, inscribing: \"{params}\"."

        area_id = player_manager._get_current_area_id()
        area_node = self.graph.get_node(area_id) if area_id else None
        old_light = area_node.properties.get("environment", {}).get("light", 80) if area_node else None

        trigger_context = {"params": params or ""}
        trigger_outputs = self._exec_triggers(item_node, "on_use_on", target_name=target_name, context=trigger_context)

        if trigger_outputs:
            result = "\n".join(trigger_outputs)
        else:
            result = ""

        # #6: system-visible light change feedback
        if old_light is not None and area_node and self.graph.get_node(area_node.id):
            new_light = area_node.properties.get("environment", {}).get("light", 80)
            if old_light != new_light:
                old_level = self.world.lighting.light_to_level(old_light)
                new_level = self.world.lighting.light_to_level(new_light)
                change_text = "brightens" if new_light > old_light else "darkens"
                result += f" The {area_node.name} {change_text}."
                self.world.add_log_entry(
                    f"[System] {player_manager.active_player} used {item_name} on {target_name} in {area_node.name}, "
                    f"light changed from {old_level} to {new_level}"
                )

        if trigger_outputs:
            if not self.graph.get_node(item_node.id):
                return result
            return result

        skill_check_config = item_node.properties.get("skill_check", {})
        if skill_check_config and skill_check_config.get("skill"):
            skill_name = skill_check_config["skill"]
            dc = skill_check_config.get("dc", 10)
            success, total, message = player_manager.skill_check(skill_name, dc)
            if not success:
                return f"You try to use the {item_name} on the {target_name} but fail. {message}"

        area_id = player_manager._get_current_area_id()

        matched_edge, way_node, matched_handle = self.matching.resolve_exit(area_id, target_name)
        if way_node:
            from engine.character_spatial import approach_way
            if player_manager.active_player:
                pid = player_manager._player_node_id(player_manager.active_player)
                approach_way(self.graph, pid, way_node.id)
            # The used-on way fires its own on_use triggers (e.g. a door
            # that reacts to being used on). The source item's on_use_on
            # already ran above and returns early if it produced output, so
            # this is the target's on_use response — same semantic as the
            # item-target fallback below (use_item on the matched item).
            way_use_outputs = self._exec_triggers(
                way_node, "on_use", context={"params": params or ""},
            )
            if way_use_outputs:
                return "\n".join(way_use_outputs)

            unlock_edges = [e for e in self.graph.edges if e.source == item_node.id and e.target == way_node.id and e.type == EDGE_UNLOCKS]
            if unlock_edges:
                way_node.properties["current_state"] = "closed"
                self.graph.nodes[way_node.id] = way_node
                area_name = player_manager.current_area.name if player_manager.current_area else None
                player_manager.record_turn_event(player_manager.active_player, "use", f"used the {item_name} on the {target_name} — unlocked it!", area_name=area_name)
                return f"You use the {item_name} on the {target_name}. The lock clicks open!"

            effect_target = item_node.properties.get("effect_target")
            if effect_target == "connection":
                new_state = item_node.properties.get("effect_stat", "open")
                way_node.properties["current_state"] = new_state
                self.graph.nodes[way_node.id] = way_node
                area_name = player_manager.current_area.name if player_manager.current_area else None
                player_manager.record_turn_event(player_manager.active_player, "use", f"used the {item_name} on the {target_name} — changed to {new_state}", area_name=area_name)
                return f"You use the {item_name} on the {target_name}. It changes to {new_state}."

            raise ValueError(f"You try using the {item_name} on the {target_name}, but nothing happens.")

        matched_item = self.matching._match_item_name(target_name)
        if matched_item:
            from engine.character_spatial import approach_item
            for edge in list(self.graph.get_edges_for_target(area_id, EDGE_IN)):
                node = self.graph.get_node(edge.source)
                if node and node.type == "item" and node.name == matched_item:
                    approach_item(self.graph, player_manager, target_name, node)
                    break
            try:
                target_use_result = self.use_item(player_manager, matched_item)
                if target_use_result and "nothing happens" not in target_use_result.lower():
                    return target_use_result
            except ValueError:
                pass
            raise ValueError(f"You use the {item_name} on the {matched_item}, but nothing happens.")

        for pname, p in player_manager.players.items():
            if pname != player_manager.active_player and p.current_area == player_manager.current_area.name and target_name.lower() in pname.lower():
                from engine.character_spatial import approach_character
                approach_character(self.graph, player_manager, pname)
                weapon_keywords = ["cleaver", "knife", "letter_opener", "hatchet", "axe", "blade", "sword", "dagger", "machete", "club", "hammer", "spear", "shiv", "chainsaw", "crowbar"]
                is_weapon = item_node.properties.get("action") == "attack" or any(kw in item_name.lower() for kw in weapon_keywords)
                if is_weapon:
                    result = self.world.player_attack(player_manager.active_player, pname, weapon_node=item_node)
                    area_name = player_manager.current_area.name if player_manager.current_area else None
                    player_manager.record_turn_event(player_manager.active_player, "combat", f"used {item_name} on {pname}: {result}", area_name=area_name)
                    return result
                return f"You use the {item_name} on {pname}, but it's not very effective as a weapon."

        available = [e.properties.get("direction", "") for e in self.graph.get_edges_for_source(area_id, EDGE_CONNECTION)]
        available += [self.graph.get_node(e.source).name for e in self.graph.get_edges_for_target(area_id, EDGE_IN)]
        contextual = self._descriptive_target_failure(player_manager, item_name, target_name, area_id, item_node)
        if contextual:
            return contextual
        return f"I don't see a '{target_name}' to use that on. Available: {', '.join(available) if available else 'none'}"

    # ────────────────────── Descriptive-target fallback ──────────────────────

    def _descriptive_target_failure(self, player_manager, item_name: str, target_name: str, area_id: str, item_node=None) -> Optional[str]:
        """Generate a contextual narrative failure when a target isn't a real
        item/exit but appears in descriptive text.

        Scans the area description, visible item descriptions, and way
        descriptions for the target phrase (word-boundary aware). If found,
        returns an in-character failure message explaining why the attempt
        didn't work, and logs the attempt as a turn event so others can
        witness it. Returns None if no descriptive match exists.
        """
        if not target_name:
            return None
        target_lower = target_name.lower().strip()
        # Multi-word partial match: check if every word appears in some description
        target_words = [w for w in target_lower.split() if len(w) >= 3]
        if not target_words:
            return None

        area_node = self.graph.get_node(area_id) if area_id else None
        area_desc = (area_node.properties.get("description", "") if area_node else "").lower()

        # Collect descriptive text: area description + item descriptions + way descriptions
        descriptive_parts = []
        if area_desc:
            descriptive_parts.append(area_desc)
        for edge in self.graph.get_edges_for_target(area_id, EDGE_IN):
            node = self.graph.get_node(edge.source)
            if node and node.properties.get("description"):
                descriptive_parts.append(str(node.properties["description"]).lower())
        for edge in self.graph.get_edges_for_source(area_id, EDGE_CONNECTION):
            way_node = self.graph.get_node(edge.target)
            if way_node and way_node.properties.get("description"):
                descriptive_parts.append(str(way_node.properties["description"]).lower())

        def _phrase_matches(text: str) -> bool:
            if not text:
                return False
            if target_lower in text:
                return True
            # All target words must appear (in order) to avoid false positives
            if len(target_words) > 1:
                return all(w in text for w in target_words)
            return False

        matched_phrase = None
        for part in descriptive_parts:
            if _phrase_matches(part):
                matched_phrase = part
                break
        if not matched_phrase:
            return None

        # Fire-tagged items (flames, heat sources) aimed at scenery get
        # fire-appropriate failure text instead of furniture reasons like
        # "it's not movable".
        fire_reasons = [
            f"but the {target_name} are too cold and damp to catch",
            f"but the {target_name} smolder briefly and go out — nothing dry enough to burn",
            f"but the {target_name} refuse to ignite; the cold is too deep here",
        ]
        generic_reasons = [
            f"but it doesn't budge — it's part of the scenery, not something you can interact with",
            f"but nothing happens. It's just {target_name}, fixed in place",
            f"but it doesn't seem to be loose or movable at all",
            f"but there's no purchase on it — it's purely decorative",
        ]
        reasons = generic_reasons
        if item_node is not None:
            item_tags = item_node.properties.get("tags", [])
            if isinstance(item_tags, str):
                item_tags = [t.strip() for t in item_tags.split(",")]
            if "fire" in item_tags or "heat_source" in item_tags:
                reasons = fire_reasons
        reason = random.choice(reasons)
        area_name = player_manager.current_area.name if player_manager.current_area else None
        player_manager.record_turn_event(
            player_manager.active_player,
            "use",
            f"tried to use the {item_name} on {target_name}, {reason}",
            area_name=area_name,
        )
        raise ValueError(f"You try to use the {item_name} on {target_name}, {reason}.")
