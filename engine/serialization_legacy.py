# engine/serialization_legacy.py — Load from legacy areas/items/players dictionary format.

from typing import Optional

from area import Area
from graph import EDGE_IN, EDGE_CARRYING, EDGE_TRIGGERS, Edge, Node
from engine.item_actions import normalize_item_actions


class LegacyLoader:
    """Converts legacy areas/items/players dictionary into graph nodes and edges."""

    def __init__(self, graph, player_manager, legacy):
        self.graph = graph
        self.player_manager = player_manager
        self.legacy = legacy

    def load(self, data: dict):
        self.graph.clear()

        for area_name, area_data in data.get("areas", {}).items():
            env = area_data.get("environment", {})
            if "light" not in env:
                env["light"] = 80
            area = Area(
                name=area_name,
                description=area_data.get("description", ""),
                items=[],
                exits={},
                environment=env
            )
            self.legacy.add_area(area)

        connected_pairs = set()
        for area_name, area_data in data.get("areas", {}).items():
            for exit_dir, exit_info in area_data.get("exits", {}).items():
                target_area = exit_info.get("target")
                if not target_area:
                    continue
                pair = tuple(sorted([area_name, target_area]))
                if pair in connected_pairs:
                    continue
                connected_pairs.add(pair)
                opposites = {
                    "north": "south", "south": "north",
                    "east": "west", "west": "east",
                    "up": "down", "down": "up"
                }
                dir2 = exit_info.get("return_dir", opposites.get(exit_dir, exit_dir + "_back"))

                state = exit_info.get("state", "open")
                if exit_info.get("hidden", False):
                    state = "hidden"
                description = exit_info.get("description", f"A door {exit_dir}")
                cost = exit_info.get("cost", {})

                try:
                    self.legacy.connect_areas(
                        area_name, target_area,
                        exit_dir, dir2,
                        state=state,
                        desc=description,
                        cost=cost
                    )
                except Exception as e:
                    print(f"Warning: could not connect {area_name} -> {target_area}: {e}")

        for area_name, area_data in data.get("areas", {}).items():
            area_node_id = self.player_manager.area_node_id(area_name)
            for item_data in area_data.get("items", []):
                item_name = item_data.get("name")
                if not item_name:
                    continue
                item_node_id = self.player_manager.item_node_id(item_name)
                item_node = Node(
                    id=item_node_id,
                    type="item",
                    name=item_name,
                    properties={
                        "description": item_data.get("description", ""),
                        "actions": normalize_item_actions(item_data.get("actions", [])),
                        "uses": item_data.get("uses", -1),
                        "weight": item_data.get("weight", 0.1),
                        "effect_target": item_data.get("effect_target"),
                        "effect_stat": item_data.get("effect_stat"),
                        "effect_amount": item_data.get("effect_amount", 0),
                        "action_costs": item_data.get("action_costs", {}),
                        "current_state": "hidden" if item_data.get("hidden", False) else "normal",
                        "skill_check": item_data.get("skill_check", {}),
                        "tags": item_data.get("tags", [])
                    }
                )
                self.graph.add_node(item_node)
                actual_item_id = item_node.id
                self.graph.add_edge(Edge(source=actual_item_id, target=area_node_id, type=EDGE_IN))
                for trigger_data in item_data.get("triggers", []):
                    trigger_type = trigger_data.get("trigger_type", "on_use")
                    effect_type = trigger_data.get("effect_type", trigger_data.get("type", "message"))
                    effect_params = trigger_data.get("effect_params", trigger_data.get("params", {}))
                    target_name = trigger_data.get("target_name", "")
                    condition = trigger_data.get("condition", "")
                    trigger_node_id = f"trigger_{actual_item_id}_{trigger_type}_{len(self.graph.get_edges_for_source(actual_item_id, EDGE_TRIGGERS))}"
                    trigger_properties = {"trigger_type": trigger_type, "effect_type": effect_type, "effect_params": effect_params, "target_name": target_name}
                    if condition:
                        trigger_properties["condition"] = condition
                    trigger_node = Node(id=trigger_node_id, type="logic_trigger", name=f"{item_name}:{trigger_type}", properties=trigger_properties)
                    self.graph.add_node(trigger_node)
                    self.graph.add_edge(Edge(source=actual_item_id, target=trigger_node_id, type=EDGE_TRIGGERS, properties=trigger_properties))

        for player_name, player_data in data.get("players", {}).items():
            pnode_id = self.player_manager.player_node_id(player_name)
            if not self.graph.get_node(pnode_id):
                self.graph.add_node(Node(id=pnode_id, type="character", name=player_name))
            current_area = player_data.get("current_area")
            if current_area:
                self.player_manager.set_player_area(player_name, current_area)

            for inv_item in player_data.get("inventory", []):
                item_name = inv_item.get("name")
                if not item_name:
                    continue
                inv_item_id = f"inv_{player_name}_{item_name}"
                item_node = Node(
                    id=inv_item_id,
                    type="item",
                    name=item_name,
                    properties=inv_item
                )
                self.graph.add_node(item_node)
                actual_inv_id = item_node.id
                self.graph.add_edge(Edge(source=actual_inv_id, target=pnode_id, type=EDGE_CARRYING))
                for trigger_data in inv_item.get("triggers", []):
                    trigger_type = trigger_data.get("trigger_type", "on_use")
                    effect_type = trigger_data.get("effect_type", trigger_data.get("type", "message"))
                    effect_params = trigger_data.get("effect_params", trigger_data.get("params", {}))
                    target_name = trigger_data.get("target_name", "")
                    condition = trigger_data.get("condition", "")
                    trigger_node_id = f"trigger_{actual_inv_id}_{trigger_type}_{len(self.graph.get_edges_for_source(actual_inv_id, EDGE_TRIGGERS))}"
                    trigger_properties = {"trigger_type": trigger_type, "effect_type": effect_type, "effect_params": effect_params, "target_name": target_name}
                    if condition:
                        trigger_properties["condition"] = condition
                    trigger_node = Node(id=trigger_node_id, type="logic_trigger", name=f"{item_name}:{trigger_type}", properties=trigger_properties)
                    self.graph.add_node(trigger_node)
                    self.graph.add_edge(Edge(source=actual_inv_id, target=trigger_node_id, type=EDGE_TRIGGERS, properties=trigger_properties))

        if "ways" in data:
            for way_id, way_data in data["ways"].items():
                node = Node(
                    id=way_id,
                    type="way",
                    name=way_data.get("display_name", way_id),
                    properties=way_data
                )
                self.graph.add_node(node)

        self.legacy._create_locked_with_unlocks()