# engine/serialization_template.py — Load from world_template.json format.
# (Single-player, areas with items/exits — authorial content.)

import random
import time
from typing import Optional

from graph import EDGE_CONNECTION, EDGE_IN, EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT, Edge, Node
from player import Player
from engine.item_actions import normalize_item_actions
from engine.beyond_visibility import normalize_visible_items


def _normalize_str_list(value):
    """Accept a comma-separated string or a list; return a clean string list."""
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if str(v).strip()]
    return []


def _connection_edge_props(direction, exit_data):
    """Build area->way edge properties from scenario exit data."""
    if not isinstance(exit_data, dict):
        exit_data = {}
    props = {
        "direction": direction,
        "visible_in_direction": exit_data.get("visible_in_direction", ""),
    }
    if exit_data.get("allow_see_characters"):
        props["allow_see_characters"] = True
    visible_items = normalize_visible_items(exit_data.get("visible_items"))
    if visible_items:
        props["visible_items"] = visible_items
    return props


class TemplateLoader:
    """Loads world_template.json — authorial content with areas/items/exits."""

    def __init__(self, graph, player_manager, legacy):
        self.graph = graph
        self.player_manager = player_manager
        self.legacy = legacy

    def load(self, data):
        self.graph.clear()
        self.player_manager.players = {}
        self.legacy.time_ticks = 0
        self.legacy.turn_number = 0
        self.legacy.turn_events = []
        self.legacy.game_log = []
        self.legacy.speech_log.clear()
        from engine.event_queue import DelayedEventQueue
        self.legacy.delayed_events = DelayedEventQueue()
        self.legacy.add_log_entry("[System] World loaded from template.")

        player_data = data.get("player", {})
        player_name = player_data.get("name", "Traveler")
        p = Player(player_name)
        p.personality = player_data.get("personality", "")
        p.stats = {**p.stats, **(player_data.get("stats", {}))}
        p.vitals = {**p.vitals, **(player_data.get("vitals", {}))}
        if "Max_HP" not in p.vitals:
            p.vitals["Max_HP"] = 100
        if "HP" in p.vitals:
            p.vitals["HP"] = max(0, min(p.vitals["Max_HP"], p.vitals["HP"]))
        if "Energy" in p.vitals:
            p.vitals["Energy"] = max(0, min(100, p.vitals["Energy"]))
        p.skills = {**p.skills, **(player_data.get("skills", {}))}
        p.exhaustion_count = player_data.get("exhaustion_count", 0)
        self.player_manager.add_player(p)
        self.player_manager.active_player = p.name

        rooms_data = data.get("areas", {})

        for area_name, area_data in rooms_data.items():
            env = area_data.get("environment", {})
            area_node = Node(
                id=self.player_manager.area_node_id(area_name),
                type="area",
                name=area_name,
                properties={
                    "description": area_data.get("description", ""),
                    "environment": {
                        "light": env.get("light", 80),
                        "temperature": env.get("temperature", 21),
                        "air": env.get("air", "fresh"),
                        "smell": env.get("smell", "neutral"),
                        "noise": env.get("noise", "quiet")
                    }
                }
            )
            self.graph.add_node(area_node)

        for area_name, area_data in rooms_data.items():
            for direction, exit_data in area_data.get("exits", {}).items():
                target_name = exit_data.get("target", "") if isinstance(exit_data, dict) else exit_data
                if isinstance(exit_data, str):
                    target_name = exit_data
                    exit_data = {"target": target_name, "state": "open", "description": f"A path to the {target_name}."}
                if target_name and target_name in rooms_data:
                    way_id = f"way_{area_name}_{direction}"
                    if not self.graph.get_node(way_id):
                        way_node = Node(
                            id=way_id,
                            type="way",
                            name=f"{area_name}-{direction}",
                            properties={
                                "current_state": "hidden" if exit_data.get("hidden", False) else exit_data.get("state", "open"),
                                "description": exit_data.get("description", f"A door to the {target_name}."),
                                "pass_message": exit_data.get("pass_message", ""),
                                "cost": exit_data.get("cost", {}),
                                "area_from": area_name,
                                "area_to": target_name
                            }
                        )
                        self.graph.add_node(way_node)
                        way_id = way_node.id
                        self.graph.add_edge(Edge(source=self.player_manager.area_node_id(area_name), target=way_id,
                                                 type=EDGE_CONNECTION, properties=_connection_edge_props(direction, exit_data)))
                        self.graph.add_edge(Edge(source=way_id, target=self.player_manager.area_node_id(target_name),
                                                 type=EDGE_CONNECTION, properties={"direction": "enter"}))
                        reverse_data = rooms_data.get(target_name, {}).get("exits", {})
                        rev_dir = None
                        for rd, rev_exit in reverse_data.items():
                            rev_target = rev_exit.get("target", "") if isinstance(rev_exit, dict) else rev_exit
                            if rev_target == area_name:
                                rev_dir = rd
                                break
                        if rev_dir:
                            rev_vid = ""
                            if isinstance(rev_exit, dict):
                                rev_vid = rev_exit.get("visible_in_direction", "")
                            self.graph.add_edge(Edge(source=self.player_manager.area_node_id(target_name), target=way_id,
                                                     type=EDGE_CONNECTION, properties=_connection_edge_props(rev_dir, rev_exit if isinstance(rev_exit, dict) else {"visible_in_direction": rev_vid})))
                            self.graph.add_edge(Edge(source=way_id, target=self.player_manager.area_node_id(area_name),
                                                     type=EDGE_CONNECTION, properties={"direction": rev_dir}))

        for area_name, area_data in rooms_data.items():
            area_id = self.player_manager.area_node_id(area_name)
            for item_data in area_data.get("items", []):
                item_name = item_data.get("name", "unknown_item")
                node_id = f"item_{item_name}"
                actions = item_data.get("actions", ["examine"])
                if isinstance(actions, str):
                    actions = [a.strip() for a in actions.split(",")]
                actions = normalize_item_actions(actions)
                props = {
                    "description": item_data.get("description", ""),
                    "actions": actions,
                    "uses": int(item_data.get("uses", -1)),
                    "weight": float(item_data.get("weight", 0.1)),
                    "current_state": "hidden" if item_data.get("hidden", False) else item_data.get("current_state", "normal"),
                    "action_costs": item_data.get("action_costs", {}),
                    "skill_check": item_data.get("skill_check", {}),
                    "effect_target": item_data.get("effect_target"),
                    "effect_stat": item_data.get("effect_stat"),
                    "effect_amount": item_data.get("effect_amount", 0),
                    "contents": item_data.get("contents", []),
                    "aliases": item_data.get("aliases", []),
                    "tags": _normalize_str_list(item_data.get("tags", [])),
                }
                # Mechanical props the engine reads, when the draft carries them
                # (light_source→light_level, heat_source→target/heating, ...).
                for _prop in ("light_level", "target_temperature", "heating_rate",
                              "sound_level", "sound_pattern"):
                    if _prop in item_data:
                        props[_prop] = item_data[_prop]
                existing = self.graph.get_node(node_id)
                if existing:
                    existing.properties.update(props)
                else:
                    item_node = Node(id=node_id, type="item", name=item_name, properties=props)
                    self.graph.add_node(item_node)
                    self.graph.add_edge(Edge(source=node_id, target=area_id, type=EDGE_IN))
                triggers = item_data.get("triggers", [])
                if not triggers and item_data.get("trigger_type"):
                    triggers = [{"trigger_type": item_data["trigger_type"], "effect_type": item_data.get("effect_type", "message"), "effect_params": item_data.get("effect_params", {}), "target_name": item_data.get("target_name", "")}]
                for trigger_data in triggers:
                    trigger_type = trigger_data.get("trigger_type", "on_examine")
                    effect_type = trigger_data.get("effect_type", trigger_data.get("type", "message"))
                    effect_params = trigger_data.get("effect_params", trigger_data.get("params", {}))
                    target_name = trigger_data.get("target_name", "")
                    condition = trigger_data.get("condition")
                    trigger_id = f"trigger_{node_id}_{trigger_type}_{int(time.time()*1000)}_{random.randint(0,999)}"
                    trigger_properties = {"trigger_type": trigger_type, "effect_type": effect_type, "effect_params": effect_params, "target_name": target_name}
                    if condition:
                        trigger_properties["condition"] = condition
                    already_exists = False
                    for edge in self.graph.edges:
                        if edge.source == node_id and edge.type == "triggers":
                            target_node = self.graph.get_node(edge.target)
                            if target_node and target_node.properties.get("trigger_type") == trigger_type and target_node.properties.get("effect_type") == effect_type and target_node.properties.get("target_name") == target_name:
                                already_exists = True
                                break
                    if not already_exists:
                        trigger_node = Node(id=trigger_id, type="logic_trigger", name=f"{trigger_type} -> {effect_type}", properties=trigger_properties)
                        self.graph.add_node(trigger_node)
                        self.graph.add_edge(Edge(source=node_id, target=trigger_id, type="triggers", properties=trigger_properties))

                contents = item_data.get("contents", [])
                for content_entry in contents:
                    content_id = content_entry.get("id", "")
                    if not content_id:
                        continue
                    content_name = content_entry.get("name", content_id)
                    content_node = self.graph.get_node(content_id)
                    if not content_node:
                        content_props = {
                            "description": content_entry.get("description", ""),
                            "actions": normalize_item_actions(content_entry.get("actions", ["examine", "take"])),
                            "uses": int(content_entry.get("uses", -1)),
                            "weight": float(content_entry.get("weight", 0.1)),
                            "current_state": "hidden",
                        }
                        content_node = Node(id=content_id, type="item", name=content_name, properties=content_props)
                        self.graph.add_node(content_node)
                    relation_key = (content_entry.get("relation", "") or "").strip().lower()
                    content_edge_type = {
                        "on": EDGE_ON,
                        "under": EDGE_UNDER,
                        "behind": EDGE_BEHIND,
                        "beside": EDGE_BESIDE,
                        "at": EDGE_AT,
                    }.get(relation_key, EDGE_IN)
                    self.graph.add_edge(Edge(source=content_id, target=node_id, type=content_edge_type))
                    content_triggers = content_entry.get("triggers", [])
                    for content_trigger in content_triggers:
                        content_trigger_type = content_trigger.get("trigger_type", "on_use_on")
                        content_trigger_effect = content_trigger.get("effect_type", "message")
                        content_trigger_params = content_trigger.get("effect_params", {})
                        content_trigger_target = content_trigger.get("target_name", "")
                        content_trigger_node_id = f"trigger_{content_id}_{content_trigger_type}_{int(time.time()*1000)}_{random.randint(0,999)}"
                        content_trigger_properties = {"trigger_type": content_trigger_type, "effect_type": content_trigger_effect, "effect_params": content_trigger_params, "target_name": content_trigger_target}
                        content_trigger_node = Node(id=content_trigger_node_id, type="logic_trigger", name=f"{content_trigger_type} -> {content_trigger_effect}", properties=content_trigger_properties)
                        self.graph.add_node(content_trigger_node)
                        self.graph.add_edge(Edge(source=content_id, target=content_trigger_node_id, type="triggers", properties=content_trigger_properties))

        start_area = data.get("current_area", list(rooms_data.keys())[0] if rooms_data else "Living Area")
        p.current_area = start_area
        player_node_id = self.player_manager.player_node_id(p.name)
        area_node_id = self.player_manager.area_node_id(start_area)
        if self.graph.get_node(player_node_id) and self.graph.get_node(area_node_id):
            self.graph.add_edge(Edge(source=player_node_id, target=area_node_id, type=EDGE_IN))

        # Supporting cast (scenario-from-text): extra players beyond the
        # protagonist, each optionally rooted in a room of their own. The
        # protagonist stays active even when the cast list declares someone
        # last in the roster.
        for char_data in data.get("characters", []) or []:
            if not isinstance(char_data, dict):
                continue
            cname = str(char_data.get("name", "")).strip()
            if not cname or cname in self.player_manager.players:
                continue
            c = Player(cname)
            c.description = str(char_data.get("description", "") or "")
            c.base_description = str(char_data.get("base_description") or c.description)
            c.personality = str(char_data.get("personality", "") or "")
            c.tags = _normalize_str_list(char_data.get("tags"))
            c.stats = {**c.stats, **(char_data.get("stats") or {})}
            c.skills = {**c.skills, **(char_data.get("skills") or {})}
            c.current_area = str(char_data.get("area") or char_data.get("current_area") or start_area)
            self.player_manager.add_player(c)
        self.player_manager.active_player = p.name

        self.legacy._create_locked_with_unlocks()
        self.legacy.world_lore = data.get("world_lore", [])