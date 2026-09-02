"""NPC behavior action execution for TriggerSystem.

Moved from engine/trigger_system.py.
"""

import time
from typing import Any, List, Optional

from graph import EDGE_IN


class BehaviorMixin:
    """NPC behavior action execution."""

    def _execute_behavior_actions(
        self,
        char_name: str,
        actions: List[dict],
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Execute a list of action dicts for an NPC behaviour.

        Returns a list of output strings describing what happened.

        *game_state* must provide:

        * ``game_state.players`` — dict of all Player objects
        * ``game_state.active_player`` — current active player name (rw)
        * ``game_state.graph`` — the WorldGraph
        * ``game_state.broadcast_speech(speaker, text)``
        * ``game_state.time_ticks`` — current tick count
        * ``game_state._get_current_area_id()``
        * ``game_state.player`` — active Player object
        * ``game_state.current_area`` — Area object for current area
        """
        outputs = []
        if game_state is None:
            return outputs
        player = game_state.players.get(char_name)
        if player is None:
            return outputs
        old_active = game_state.active_player
        game_state.active_player = char_name
        try:
            for action in actions:
                action_type = action.get("type", "message")

                if action_type == "message":
                    text = action.get("text", "")
                    if not text.strip():
                        continue
                    outputs.append(f"[{char_name}] {text}")

                elif action_type == "llm_respond":
                    # task-331: queue a browser-side LLM response (same request
                    # shape + queue as the item llm_respond effect, task-330).
                    # The browser generates the line and posts it back via
                    # /api/llm_respond; the engine broadcasts it as speech.
                    if not hasattr(game_state, "queue_llm_respond"):
                        continue
                    speaker = action.get("name", char_name)
                    try:
                        max_words = max(1, int(action.get("max_words", 40)))
                    except (TypeError, ValueError):
                        max_words = 40
                    node_id = ""
                    try:
                        getter = getattr(game_state, "_player_node_id", None) or getattr(game_state, "get_player_node_id", None)
                        node_id = getter(char_name) if getter else ""
                    except Exception:
                        node_id = ""
                    request = {
                        "id": f"llm_req_{int(time.time() * 1000)}_{id(player)}",
                        "speaker": speaker,
                        "node_id": node_id,
                        "instructions": action.get("instructions", "") or action.get("llm_instructions", ""),
                        "fallback_message": action.get("fallback_message", "") or action.get("llm_fallback", ""),
                        "max_words": max_words,
                        "heard": action.get("heard", ""),
                        "tick": getattr(game_state, "time_ticks", 0),
                        "ts": time.time(),
                        "cooldown": max(1, int(action.get("cooldown", 30))),
                    }
                    accepted = game_state.queue_llm_respond(request)
                    if accepted:
                        outputs.append(f"[{char_name}] pauses, as if listening to something inside.")
                    elif request["fallback_message"]:
                        outputs.append(request["fallback_message"])

                elif action_type == "speak":
                    text = action.get("text", "...")
                    game_state.broadcast_speech(char_name, text)
                    outputs.append(f'{char_name} says: "{text}"')

                elif action_type == "set_npc_state":
                    new_state = action.get("state", "idle")
                    if new_state != player.npc_state:
                        old_state = player.npc_state
                        player.npc_state = new_state
                        player.state_enter_tick = game_state.time_ticks
                        outputs.append(
                            f"[{char_name}] state: {old_state} -> {new_state}"
                        )

                elif action_type == "damage":
                    amount = int(action.get("amount", 5))
                    target = action.get("target", "player")
                    if target == "player":
                        target_player = (
                            game_state.players.get(game_state.active_player)
                            if game_state.active_player
                            else None
                        )
                        if target_player:
                            target_player.vitals["HP"] = max(
                                0,
                                target_player.vitals.get("HP", 100) - amount,
                            )
                            outputs.append(
                                f"{game_state.active_player} takes {amount} damage!"
                            )
                    elif target == "self" and player:
                        player.vitals["HP"] = max(
                            0, player.vitals.get("HP", 100) - amount
                        )
                        outputs.append(f"{char_name} takes {amount} damage!")

                elif action_type == "heal":
                    amount = int(action.get("amount", 10))
                    stat = action.get("stat", "HP")
                    target_name = action.get("target", "self")
                    target_player = (
                        game_state.players.get(target_name)
                        if target_name in game_state.players
                        else player
                    )
                    if target_player and stat in target_player.vitals:
                        target_player.vitals[stat] = min(
                            100,
                            target_player.vitals.get(stat, 100) + amount,
                        )

                elif action_type == "set_environment":
                    stat = action.get("stat", "temperature")
                    amount = int(action.get("amount", 0))
                    target_area_name = action.get("area", player.current_area)
                    target_area_node = None
                    for node in game_state.graph.nodes.values():
                        if node.type == "area" and node.name == target_area_name:
                            target_area_node = node
                            break
                    if target_area_node:
                        env = target_area_node.properties.setdefault(
                            "environment", {}
                        )
                        env[stat] = env.get(stat, 20) + amount
                        outputs.append(
                            f"The {stat} in {target_area_name} changes by {amount}."
                        )

                elif action_type == "spawn_item":
                    item_id = action.get("item_id", "")
                    if item_id and player.current_area:
                        area_id = game_state._get_current_area_id()
                        if area_id:
                            spawn_node = game_state.graph.get_node(item_id)
                            if spawn_node is None:
                                try:
                                    import os, json
                                    lib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'library', 'items')
                                    lib_path = os.path.join(lib_dir, f"{item_id}.json")
                                    if os.path.exists(lib_path):
                                        with open(lib_path, 'r', encoding='utf-8-sig') as f:
                                            lib_data = json.load(f)
                                except Exception:
                                    lib_data = {}

                                display_name = action.get("display_name") or action.get("name") or lib_data.get("name", item_id)
                                desc = action.get("description") or lib_data.get("description", "")
                                tags = lib_data.get("tags", [])
                                uses = lib_data.get("uses", -1)
                                weight = lib_data.get("weight", 0.1)

                                spawn_node = Node(
                                    id=item_id,
                                    type="item",
                                    name=display_name,
                                    properties={
                                        "description": desc,
                                        "tags": tags,
                                        "uses": uses,
                                        "weight": weight,
                                    },
                                )
                                game_state.graph.add_node(spawn_node)
                            for edge in game_state.graph.edges[:]:
                                if (
                                    edge.source == item_id
                                    and edge.type == EDGE_IN
                                ):
                                    game_state.graph.edges.remove(edge)
                            game_state.graph.add_edge(
                                Edge(
                                    source=item_id,
                                    target=area_id,
                                    type=EDGE_IN,
                                )
                            )

                elif action_type == "teleport":
                    target_area = action.get("area", "")
                    target_char = action.get("target", "player")
                    target_name = (
                        game_state.active_player
                        if target_char == "player"
                        else action.get("character_name", char_name)
                    )
                    target_player = game_state.players.get(target_name)
                    if target_player and target_area:
                        for node in game_state.graph.nodes.values():
                            if (
                                node.type == "area"
                                and node.name == target_area
                            ):
                                target_player.current_area = target_area
                                outputs.append(
                                    f"{target_name} vanishes and reappears elsewhere!"
                                )
                                break

                elif action_type == "go":
                    if hasattr(game_state, "npc_behaviors"):
                        msg = game_state.npc_behaviors.execute_go_action(
                            char_name, action
                        )
                        if msg:
                            outputs.append(msg)
                    else:
                        target_area = action.get("area") or action.get("room", "")
                        if target_area and player.current_area:
                            area_exists = any(
                                node.type == "area" and node.name == target_area
                                for node in game_state.graph.nodes.values()
                            )
                            if area_exists:
                                player.current_area = target_area
                                outputs.append(
                                    f"[{char_name}] moves to {target_area}."
                                )
                            else:
                                outputs.append(
                                    f"[{char_name}] cannot find area '{target_area}'."
                                )

                elif action_type == "add_memory":
                    text = action.get("text", "")
                    if text:
                        importance = int(action.get("importance", 5))
                        tags = action.get("tags", [])
                        memory = {
                            "text": text,
                            "importance": importance,
                            "tags": tags,
                            "tick": getattr(game_state, "time_ticks", 0),
                        }
                        player.memories.append(memory)
                        outputs.append(f"[{char_name}] will remember: {text}")

                elif action_type == "set_emotion":
                    emotion = action.get("emotion", "calm")
                    intensity = float(action.get("intensity", 0.5))
                    player.set_emotion(emotion, intensity)
                    outputs.append(f"[{char_name}] feels {emotion} (intensity {intensity}).")

                elif action_type == "set_flag":
                    key = action.get("key", "")
                    value = action.get("value", True)
                    if key:
                        player.flags[key] = value
                        outputs.append(f"[{char_name}] flag set: {key} = {value}")

                elif action_type == "hide_in":
                    target_id = action.get("target", "")
                    target_node = game_state.graph.get_node(target_id)
                    if target_node and "hideable" in (target_node.properties.get("tags", []) or []):
                        game_state.graph.add_edge(
                            Edge(
                                source=char_name,
                                target=target_id,
                                type="hidden",
                                properties={"relation": "in"},
                            )
                        )
                        player.hidden = True
                        outputs.append(f"[{char_name}] hides inside {target_node.name}.")
                    else:
                        outputs.append(f"[{char_name}] cannot hide in '{target_id}' (not hideable).")

                elif action_type == "hide_behind":
                    target_id = action.get("target", "")
                    target_node = game_state.graph.get_node(target_id)
                    if target_node and "hideable" in (target_node.properties.get("tags", []) or []):
                        game_state.graph.add_edge(
                            Edge(
                                source=char_name,
                                target=target_id,
                                type="hidden",
                                properties={"relation": "behind"},
                            )
                        )
                        player.hidden = True
                        outputs.append(f"[{char_name}] hides behind {target_node.name}.")
                    else:
                        outputs.append(f"[{char_name}] cannot hide behind '{target_id}' (not hideable).")

                elif action_type == "hide_under":
                    target_id = action.get("target", "")
                    target_node = game_state.graph.get_node(target_id)
                    if target_node and "hideable" in (target_node.properties.get("tags", []) or []):
                        game_state.graph.add_edge(
                            Edge(
                                source=char_name,
                                target=target_id,
                                type="hidden",
                                properties={"relation": "under"},
                            )
                        )
                        player.hidden = True
                        outputs.append(f"[{char_name}] hides under {target_node.name}.")
                    else:
                        outputs.append(f"[{char_name}] cannot hide under '{target_id}' (not hideable).")

                elif action_type == "unhide":
                    edges_to_remove = [
                        e for e in game_state.graph.edges
                        if e.source == char_name and e.type == "hidden"
                    ]
                    for e in edges_to_remove:
                        game_state.graph.edges.remove(e)
                    player.hidden = False
                    outputs.append(f"[{char_name}] steps out of hiding.")

                # ── Combat ──────────────────────────────────────────────
                elif action_type == "attack":
                    target_name = action.get("target", "")
                    weapon = action.get("weapon", "")
                    where = action.get("where", None)
                    if target_name:
                        weapon_node = None
                        if weapon:
                            try:
                                weapon_node = game_state.find_weapon_in_inventory(char_name, weapon)
                            except Exception:
                                weapon_node = None
                        try:
                            msg = game_state.combat.player_attack(
                                char_name, target_name, weapon_node=weapon_node, where=where
                            )
                            if msg:
                                outputs.append(msg)
                        except Exception as e:
                            outputs.append(f"[{char_name}] attacks {target_name} — but something goes wrong.")

                elif action_type == "throw":
                    # task-NPC: throw item at target. Simplified: drop item in target's area.
                    item_name = action.get("item", "")
                    target_name = action.get("target", "")
                    if item_name and target_name:
                        try:
                            result = game_state.drop_item(item_name)
                            outputs.append(f"[{char_name}] throws {item_name} at {target_name}! {result}")
                        except Exception:
                            outputs.append(f"[{char_name}] fumbles the throw.")

                elif action_type == "break":
                    item_name = action.get("item", "")
                    if item_name:
                        try:
                            item_node = None
                            for node in game_state.graph.nodes.values():
                                if node.type == "item" and (node.id == item_name or (node.name or "").lower() == item_name.lower()):
                                    item_node = node
                                    break
                            if item_node:
                                old_uses = item_node.properties.get("uses", -1)
                                item_node.properties["uses"] = 0
                                outputs.append(f"[{char_name}] breaks {item_node.name}.")
                            else:
                                outputs.append(f"[{char_name}] can't find {item_name} to break.")
                        except Exception:
                            outputs.append(f"[{char_name}] tries to break {item_name} but fails.")

                # ── Items ───────────────────────────────────────────────
                elif action_type == "take":
                    item_name = action.get("item", "")
                    if item_name:
                        try:
                            result = game_state.take_item(item_name)
                            outputs.append(result or f"[{char_name}] takes {item_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't take {item_name}.")

                elif action_type == "drop":
                    item_name = action.get("item", "")
                    if item_name:
                        try:
                            result = game_state.drop_item(item_name)
                            outputs.append(result or f"[{char_name}] drops {item_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't drop {item_name}.")

                elif action_type == "put_in":
                    item_name = action.get("item", "")
                    container_name = action.get("container", "")
                    if item_name and container_name:
                        try:
                            result = game_state.put_item_in_container(item_name, container_name)
                            outputs.append(result or f"[{char_name}] puts {item_name} in {container_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't put {item_name} in {container_name}.")

                elif action_type == "equip":
                    item_name = action.get("item", "")
                    slot = action.get("slot", None)
                    if item_name:
                        try:
                            result = game_state.equip_item(item_name, slot=slot)
                            outputs.append(result or f"[{char_name}] equips {item_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't equip {item_name}.")

                elif action_type == "unequip":
                    item_name = action.get("item", "")
                    slot = action.get("slot", None)
                    try:
                        result = game_state.unequip_item(slot=slot, item_name=item_name or None)
                        outputs.append(result or f"[{char_name}] unequips {item_name or slot}.")
                    except Exception:
                        outputs.append(f"[{char_name}] can't unequip {item_name or slot}.")

                elif action_type == "use":
                    item_name = action.get("item", "")
                    target_name = action.get("target", "")
                    if item_name:
                        try:
                            if target_name:
                                result = game_state.use_item_on(item_name, target_name)
                            else:
                                result = game_state.use_item(item_name)
                            outputs.append(result or f"[{char_name}] uses {item_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't use {item_name}.")

                elif action_type == "eat":
                    item_name = action.get("item", "")
                    if item_name:
                        try:
                            result = game_state.eat_item(item_name)
                            outputs.append(result or f"[{char_name}] eats {item_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't eat {item_name}.")

                elif action_type == "drink":
                    item_name = action.get("item", "")
                    if item_name:
                        try:
                            result = game_state.drink_item(item_name)
                            outputs.append(result or f"[{char_name}] drinks {item_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't drink {item_name}.")

                elif action_type == "craft":
                    recipe = action.get("recipe", "")
                    if recipe:
                        try:
                            result = game_state.crafting.craft(game_state, recipe)
                            outputs.append(result or f"[{char_name}] crafts {recipe}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't craft {recipe}.")

                elif action_type == "combine":
                    source = action.get("source", "")
                    target = action.get("target", "")
                    if source and target:
                        try:
                            result = game_state.combine_items(source, target)
                            outputs.append(result or f"[{char_name}] combines {source} with {target}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't combine {source} and {target}.")

                elif action_type == "repair":
                    item_name = action.get("item", "")
                    kit_name = action.get("kit", "")
                    if item_name:
                        try:
                            if hasattr(game_state, "item_actions") and hasattr(game_state.item_actions, "repair_item"):
                                result = game_state.item_actions.repair_item(game_state, item_name, kit_name)
                                outputs.append(result or f"[{char_name}] repairs {item_name}.")
                            else:
                                outputs.append(f"[{char_name}] doesn't know how to repair {item_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] fails to repair {item_name}.")

                elif action_type == "read":
                    item_name = action.get("item", "")
                    if item_name:
                        try:
                            result = game_state.get_item_desc(item_name)
                            outputs.append(f"[{char_name}] reads {item_name}: {result[:200]}")
                        except Exception:
                            outputs.append(f"[{char_name}] can't read {item_name}.")

                # ── Environment ─────────────────────────────────────────
                elif action_type == "open":
                    target_name = action.get("target", "")
                    if target_name:
                        try:
                            result = game_state.item_actions.open_item(game_state, target_name)
                            outputs.append(result or f"[{char_name}] opens {target_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't open {target_name}.")

                elif action_type == "close":
                    target_name = action.get("target", "")
                    if target_name:
                        try:
                            result = game_state.item_actions.close_item(game_state, target_name)
                            outputs.append(result or f"[{char_name}] closes {target_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't close {target_name}.")

                elif action_type == "lock":
                    target_name = action.get("target", "")
                    if target_name:
                        try:
                            result = game_state.item_actions.lock_item(game_state, target_name)
                            outputs.append(result or f"[{char_name}] locks {target_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't lock {target_name}.")

                elif action_type == "unlock":
                    target_name = action.get("target", "")
                    if target_name:
                        try:
                            result = game_state.item_actions.lock_item(game_state, target_name, unlock=True)
                            outputs.append(result or f"[{char_name}] unlocks {target_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't unlock {target_name}.")

                elif action_type == "push":
                    target_name = action.get("target", "")
                    direction = action.get("direction", "")
                    if target_name:
                        try:
                            result = game_state.item_actions.push_pull(game_state, target_name, direction)
                            outputs.append(result or f"[{char_name}] pushes {target_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't push {target_name}.")

                elif action_type == "turn":
                    target_name = action.get("target", "")
                    if target_name:
                        try:
                            result = game_state.item_actions.turn_item(game_state, target_name)
                            outputs.append(result or f"[{char_name}] turns {target_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't turn {target_name}.")

                elif action_type == "search":
                    target_name = action.get("target", "")
                    if target_name:
                        try:
                            result = game_state.item_actions.search(game_state, target_name)
                            outputs.append(result or f"[{char_name}] searches {target_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] searches {target_name} but finds nothing.")

                # ── Social / Transfer ────────────────────────────────────
                elif action_type == "give":
                    item_name = action.get("item", "")
                    target_name = action.get("target", "")
                    if item_name and target_name:
                        try:
                            result = game_state.give_item(item_name, target_name)
                            outputs.append(result or f"[{char_name}] gives {item_name} to {target_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't give {item_name}.")

                elif action_type == "steal":
                    item_name = action.get("item", "")
                    target_name = action.get("target", "")
                    if item_name and target_name:
                        try:
                            result = game_state.steal_item(item_name, target_name)
                            outputs.append(result or f"[{char_name}] steals {item_name} from {target_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] fails to steal {item_name}.")

                elif action_type == "follow":
                    target_name = action.get("target", "")
                    if target_name:
                        outputs.append(f"[{char_name}] starts following {target_name}.")

                elif action_type == "wait":
                    outputs.append(f"[{char_name}] waits.")

                elif action_type == "approach":
                    target_name = action.get("target", "")
                    if target_name and hasattr(game_state, "approach"):
                        try:
                            result = game_state.approach(target_name)
                            outputs.append(result or f"[{char_name}] approaches {target_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't approach {target_name}.")

                elif action_type == "traverse":
                    direction = action.get("target", "") or action.get("direction", "")
                    if direction:
                        try:
                            result = game_state.move_to_area(direction)
                            outputs.append(result or f"[{char_name}] traverses {direction}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't traverse {direction}.")

                elif action_type == "emote":
                    text = action.get("text", "")
                    if text and hasattr(game_state, "process_emote"):
                        try:
                            result = game_state.process_emote(char_name, text)
                            outputs.append(result or f"[{char_name}] {text}.")
                        except Exception:
                            outputs.append(f"[{char_name}] {text}.")

                elif action_type == "carve":
                    target_name = action.get("target", "")
                    text = action.get("text", "")
                    if target_name:
                        try:
                            result = game_state.combine_items(text, target_name)
                            outputs.append(result or f"[{char_name}] carves '{text}' into {target_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't carve {target_name}.")

                elif action_type == "gulp_down":
                    item_name = action.get("item", "")
                    if item_name:
                        try:
                            if hasattr(game_state.item_actions, "_consume_item"):
                                result = game_state.item_actions._consume_item(game_state.player_manager, item_name, "on_eat", "gulp down")
                            else:
                                result = game_state.eat_item(item_name)
                            outputs.append(result or f"[{char_name}] gulps down {item_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't gulp down {item_name}.")

                elif action_type == "pinch":
                    target_name = action.get("target", "")
                    where = action.get("where", "")
                    if target_name:
                        outputs.append(f"[{char_name}] pinches {target_name} {where and f'on the {where}' or ''}.")

                elif action_type == "drop_all":
                    try:
                        dropped = game_state.item_actions.drop_held_items(game_state.player_manager, char_name)
                        if dropped:
                            outputs.append(f"[{char_name}] drops {', '.join(dropped)}.")
                        else:
                            outputs.append(f"[{char_name}] has nothing to drop.")
                    except Exception:
                        outputs.append(f"[{char_name}] drops everything.")

                elif action_type == "take_all":
                    try:
                        from engine.item_reach import reachable_items
                        items = reachable_items(game_state.graph, game_state.player_manager)
                        taken = []
                        for node in items:
                            try:
                                game_state.take_item(node.name)
                                taken.append(node.name)
                            except Exception:
                                pass
                        if taken:
                            outputs.append(f"[{char_name}] takes {', '.join(taken)}.")
                        else:
                            outputs.append(f"[{char_name}] finds nothing to take.")
                    except Exception:
                        outputs.append(f"[{char_name}] takes everything.")

                elif action_type == "lie_down":
                    if hasattr(game_state, "lie_down"):
                        try:
                            result = game_state.lie_down()
                            outputs.append(result or f"[{char_name}] lies down.")
                        except Exception:
                            outputs.append(f"[{char_name}] lies down.")

                # ── Movement Variants ────────────────────────────────────
                elif action_type == "dash":
                    direction = action.get("direction", "")
                    if direction and hasattr(game_state, "dash_to_area"):
                        try:
                            result = game_state.dash_to_area(direction)
                            outputs.append(result or f"[{char_name}] dashes {direction}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't dash {direction}.")

                elif action_type == "crawl":
                    direction = action.get("direction", "")
                    if direction and hasattr(game_state, "crawl_to_area"):
                        try:
                            result = game_state.crawl_to_area(direction)
                            outputs.append(result or f"[{char_name}] crawls {direction}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't crawl {direction}.")

                elif action_type == "climb":
                    direction = action.get("direction", "")
                    if direction and hasattr(game_state, "climb_to_area"):
                        try:
                            result = game_state.climb_to_area(direction)
                            outputs.append(result or f"[{char_name}] climbs {direction}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't climb {direction}.")

                elif action_type == "jump":
                    direction = action.get("direction", "")
                    if direction and hasattr(game_state, "jump_to_area"):
                        try:
                            result = game_state.jump_to_area(direction)
                            outputs.append(result or f"[{char_name}] jumps {direction}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't jump {direction}.")

                elif action_type == "toggle_way":
                    direction = action.get("direction", "")
                    way_action = action.get("way_action", "open")
                    if direction and hasattr(game_state, "toggle_way"):
                        try:
                            result = game_state.toggle_way(direction, way_action)
                            outputs.append(result or f"[{char_name}] {way_action}s the way {direction}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't toggle the way {direction}.")

                # ── Grappling ───────────────────────────────────────────
                elif action_type == "grab":
                    target_name = action.get("target", "")
                    if target_name and hasattr(game_state, "_grapple_grab"):
                        try:
                            result = game_state._grapple_grab(char_name, target_name)
                            outputs.append(result or f"[{char_name}] grabs {target_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't grab {target_name}.")

                elif action_type == "drag":
                    target_name = action.get("target", "")
                    direction = action.get("direction", "")
                    if target_name and hasattr(game_state, "_grapple_drag"):
                        try:
                            result = game_state._grapple_drag(char_name, target_name, direction)
                            outputs.append(result or f"[{char_name}] drags {target_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't drag {target_name}.")

                elif action_type == "pin":
                    target_name = action.get("target", "")
                    if target_name:
                        try:
                            result = game_state.grapple.grab(char_name, target_name)
                            target_player = game_state.players.get(target_name)
                            if target_player:
                                target_player.add_condition("pinned")
                            outputs.append(result or f"[{char_name}] pins {target_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't pin {target_name}.")

                elif action_type == "struggle":
                    if hasattr(game_state, "_grapple_escape"):
                        try:
                            result = game_state._grapple_escape(char_name)
                            outputs.append(result or f"[{char_name}] struggles.")
                        except Exception:
                            outputs.append(f"[{char_name}] struggles but fails.")

                elif action_type == "escape":
                    if hasattr(game_state, "_grapple_escape"):
                        try:
                            result = game_state._grapple_escape(char_name)
                            outputs.append(result or f"[{char_name}] escapes.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't escape.")

                elif action_type == "release":
                    target_name = action.get("target", "")
                    if hasattr(game_state, "_grapple_release"):
                        try:
                            result = game_state._grapple_release(char_name, target_name)
                            outputs.append(result or f"[{char_name}] releases {target_name or 'everyone'}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't release.")

                # ── Examine / Look / Search Variants ────────────────────
                elif action_type == "look":
                    if hasattr(game_state, "get_area_description"):
                        try:
                            result = game_state.get_area_description()
                            outputs.append(result or f"[{char_name}] looks around.")
                        except Exception:
                            outputs.append(f"[{char_name}] looks around.")

                elif action_type == "examine":
                    target_name = action.get("target", "")
                    if target_name:
                        try:
                            result = game_state.get_item_desc(target_name)
                            outputs.append(f"[{char_name}] examines {target_name}: {result[:200]}")
                        except Exception:
                            outputs.append(f"[{char_name}] can't examine {target_name}.")

                # ── Item Interactions ───────────────────────────────────
                elif action_type == "activate":
                    item_name = action.get("item", "")
                    if item_name:
                        try:
                            result = game_state.item_actions.activate(game_state, item_name)
                            outputs.append(result or f"[{char_name}] activates {item_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't activate {item_name}.")

                elif action_type == "light":
                    item_name = action.get("item", "")
                    if item_name:
                        try:
                            result = game_state.item_actions.light(game_state, item_name)
                            outputs.append(result or f"[{char_name}] lights {item_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't light {item_name}.")

                elif action_type == "toggle":
                    item_name = action.get("item", "")
                    if item_name:
                        try:
                            result = game_state.toggle_item_status(item_name)
                            outputs.append(result or f"[{char_name}] toggles {item_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't toggle {item_name}.")

                elif action_type == "place":
                    item_name = action.get("item", "")
                    target_name = action.get("target", "")
                    relation = action.get("relation", "on")
                    if item_name and target_name:
                        try:
                            result = game_state.place_item(item_name, target_name, relation)
                            outputs.append(result or f"[{char_name}] places {item_name} {relation} {target_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't place {item_name}.")

                elif action_type == "stow":
                    item_name = action.get("item", "")
                    if item_name:
                        try:
                            result = game_state.stow_item(item_name)
                            outputs.append(result or f"[{char_name}] stows {item_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't stow {item_name}.")

                elif action_type == "remove":
                    item_name = action.get("item", "")
                    if item_name:
                        try:
                            result = game_state.unequip_item(item_name=item_name)
                            outputs.append(result or f"[{char_name}] removes {item_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't remove {item_name}.")

                elif action_type == "hold":
                    item_name = action.get("item", "")
                    if item_name:
                        outputs.append(f"[{char_name}] holds {item_name}.")

                elif action_type == "weigh":
                    outputs.append(f"[{char_name}] checks their pack weight.")

                elif action_type == "inventory":
                    if hasattr(game_state, "get_inventory"):
                        try:
                            result = game_state.get_inventory()
                            outputs.append(f"[{char_name}] checks inventory: {result[:200]}")
                        except Exception:
                            outputs.append(f"[{char_name}] checks their inventory.")

                elif action_type == "carry":
                    item_name = action.get("item", "")
                    if item_name:
                        try:
                            result = game_state.take_item(item_name)
                            outputs.append(result or f"[{char_name}] picks up {item_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't pick up {item_name}.")

                # ── Equipment ───────────────────────────────────────────
                elif action_type == "dress":
                    if hasattr(game_state, "dress"):
                        try:
                            result = game_state.dress()
                            outputs.append(result or f"[{char_name}] gets dressed.")
                        except Exception:
                            outputs.append(f"[{char_name}] gets dressed.")

                elif action_type == "strip":
                    if hasattr(game_state, "strip"):
                        try:
                            result = game_state.strip()
                            outputs.append(result or f"[{char_name}] strips.")
                        except Exception:
                            outputs.append(f"[{char_name}] strips.")

                elif action_type == "swap":
                    item_name = action.get("item", "")
                    target_name = action.get("target", "")
                    if item_name and target_name:
                        try:
                            result = game_state.equip_item(item_name)
                            outputs.append(result or f"[{char_name}] swaps to {item_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't swap to {item_name}.")

                elif action_type == "adorn":
                    item_name = action.get("item", "")
                    target_name = action.get("target", "")
                    if item_name and target_name:
                        try:
                            result = game_state.combine_items(item_name, target_name)
                            outputs.append(result or f"[{char_name}] adorns {target_name} with {item_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't adorn {target_name}.")

                # ── Activities ──────────────────────────────────────────
                elif action_type == "rest":
                    minutes = action.get("minutes", 10)
                    try:
                        result = game_state.rest(minutes)
                        outputs.append(result or f"[{char_name}] rests for {minutes} minutes.")
                    except Exception:
                        outputs.append(f"[{char_name}] rests.")

                elif action_type == "sleep":
                    minutes = action.get("minutes", 60)
                    try:
                        result = game_state.sleep(minutes)
                        outputs.append(result or f"[{char_name}] sleeps for {minutes} minutes.")
                    except Exception:
                        outputs.append(f"[{char_name}] sleeps.")

                elif action_type == "meditate":
                    minutes = action.get("minutes", 10)
                    try:
                        result = game_state.meditate(minutes)
                        outputs.append(result or f"[{char_name}] meditates for {minutes} minutes.")
                    except Exception:
                        outputs.append(f"[{char_name}] meditates.")

                elif action_type == "bathe":
                    target_name = action.get("target", "")
                    minutes = action.get("minutes", 10)
                    try:
                        result = game_state.bathe(target_name or None, minutes)
                        outputs.append(result or f"[{char_name}] bathes.")
                    except Exception:
                        outputs.append(f"[{char_name}] bathes.")

                elif action_type == "sit":
                    if hasattr(game_state, "sit"):
                        try:
                            result = game_state.sit()
                            outputs.append(result or f"[{char_name}] sits down.")
                        except Exception:
                            outputs.append(f"[{char_name}] sits down.")

                elif action_type == "stand":
                    if hasattr(game_state, "stand"):
                        try:
                            result = game_state.stand()
                            outputs.append(result or f"[{char_name}] stands up.")
                        except Exception:
                            outputs.append(f"[{char_name}] stands up.")

                elif action_type == "stop":
                    if hasattr(game_state, "stop_activity"):
                        try:
                            result = game_state.stop_activity()
                            outputs.append(result or f"[{char_name}] stops what they're doing.")
                        except Exception:
                            outputs.append(f"[{char_name}] stops.")

                elif action_type == "wake":
                    target_name = action.get("target", "")
                    try:
                        result = game_state.wake(target_name or None)
                        outputs.append(result or f"[{char_name}] wakes {target_name or 'up'}.")
                    except Exception:
                        outputs.append(f"[{char_name}] wakes up.")

                elif action_type == "relieve":
                    if hasattr(game_state, "relieve_self"):
                        try:
                            result = game_state.relieve_self()
                            outputs.append(result or f"[{char_name}] relieves themselves.")
                        except Exception:
                            outputs.append(f"[{char_name}] relieves themselves.")

                elif action_type == "listen":
                    if hasattr(game_state, "listen"):
                        try:
                            result = game_state.listen()
                            outputs.append(result or f"[{char_name}] listens.")
                        except Exception:
                            outputs.append(f"[{char_name}] listens.")

                # ── Social ──────────────────────────────────────────────
                elif action_type == "introduce":
                    target_name = action.get("target", "")
                    if target_name:
                        outputs.append(f"[{char_name}] introduces themselves to {target_name}.")

                elif action_type == "beg":
                    target_name = action.get("target", "")
                    if target_name:
                        outputs.append(f"[{char_name}] begs {target_name}.")

                elif action_type == "demand":
                    target_name = action.get("target", "")
                    if target_name:
                        outputs.append(f"[{char_name}] demands something from {target_name}.")

                elif action_type == "bribe":
                    target_name = action.get("target", "")
                    item_name = action.get("item", "")
                    if target_name:
                        outputs.append(f"[{char_name}] tries to bribe {target_name} with {item_name or 'something'}.")

                elif action_type == "trade":
                    item_name = action.get("item", "")
                    target_name = action.get("target", "")
                    if item_name and target_name:
                        try:
                            result = game_state.give_item(item_name, target_name)
                            outputs.append(result or f"[{char_name}] trades {item_name} to {target_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't trade {item_name}.")

                # ── Intimacy ────────────────────────────────────────────
                elif action_type in ("kiss", "caress", "lick", "suck", "bite", "tickle", "embrace"):
                    target_name = action.get("target", "")
                    where = action.get("where", "")
                    intensity = action.get("intensity", "normal")
                    if target_name and hasattr(game_state, "mature_content") and game_state.mature_content:
                        outputs.append(f"[{char_name}] {action_type}s {target_name} {where and f'on the {where}' or ''} ({intensity}).")
                    elif target_name:
                        outputs.append(f"[{char_name}] attempts to {action_type} {target_name}, but this world isn't mature.")

                # ── Ghost ───────────────────────────────────────────────
                elif action_type == "possess":
                    target_name = action.get("target", "")
                    if target_name:
                        outputs.append(f"[{char_name}] attempts to possess {target_name}.")

                elif action_type == "wraith_form":
                    outputs.append(f"[{char_name}] shifts into wraith form.")

                elif action_type == "spawn_body_item":
                    outputs.append(f"[{char_name}] spawns a body item.")

                # ── Crafting ────────────────────────────────────────────
                elif action_type == "teach":
                    target_name = action.get("target", "")
                    subject = action.get("subject", "")
                    if target_name and subject:
                        try:
                            result = game_state.teach_item(subject, target_name)
                            outputs.append(result or f"[{char_name}] teaches {subject} to {target_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't teach {subject} to {target_name}.")

                elif action_type == "cook":
                    recipe = action.get("recipe", "")
                    if recipe:
                        try:
                            result = game_state.craft_item(recipe)
                            outputs.append(result or f"[{char_name}] cooks {recipe}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't cook {recipe}.")

                # ── Environment ─────────────────────────────────────────
                elif action_type == "drag":
                    target_name = action.get("target", "")
                    direction = action.get("direction", "")
                    if target_name:
                        try:
                            result = game_state.item_actions.push_pull(game_state, target_name, direction)
                            outputs.append(result or f"[{char_name}] drags {target_name}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't drag {target_name}.")

                elif action_type == "push_through":
                    direction = action.get("direction", "")
                    if direction:
                        try:
                            result = game_state.move_to_area(direction)
                            outputs.append(result or f"[{char_name}] pushes through {direction}.")
                        except Exception:
                            outputs.append(f"[{char_name}] can't push through {direction}.")

                elif action_type == "block":
                    target_name = action.get("target", "")
                    if target_name:
                        outputs.append(f"[{char_name}] blocks {target_name}.")

                # ── System / Info ───────────────────────────────────────
                elif action_type == "help":
                    outputs.append(f"[{char_name}] checks available commands.")

                elif action_type == "commands":
                    outputs.append(f"[{char_name}] checks available commands.")

                elif action_type == "who":
                    outputs.append(f"[{char_name}] checks who is here.")

                elif action_type == "time":
                    if hasattr(game_state, "get_current_time"):
                        try:
                            result = game_state.get_current_time()
                            outputs.append(f"[{char_name}] checks the time: {result}")
                        except Exception:
                            outputs.append(f"[{char_name}] checks the time.")

                elif action_type == "score":
                    outputs.append(f"[{char_name}] checks their status.")

                elif action_type == "map":
                    outputs.append(f"[{char_name}] checks their map.")

                elif action_type == "save":
                    outputs.append(f"[{char_name}] saves the game.")

                elif action_type == "quit":
                    outputs.append(f"[{char_name}] quits.")

                elif action_type == "version":
                    outputs.append(f"[{char_name}] checks the version.")

        finally:
            game_state.active_player = old_active
        return outputs
