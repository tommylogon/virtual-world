import random
import time
import uuid
from typing import Optional

from graph import EDGE_CONNECTION, EDGE_IN, EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT, EDGE_CARRYING, EDGE_TRIGGERS, EDGE_EQUIPPED, Edge, Node, WorldGraph
from player import Player
from area import Area
from engine.conditions import perceived_conditions
from engine.traits import TraitSystem, TRAIT_DEFINITIONS
from engine.item_actions import get_carry_load_ratio, sum_carry_weight, normalize_item_actions
from engine.beyond_visibility import normalize_visible_items
from engine.character_spatial import get_character_at_way, get_spatial_position_data


def _body_region_catalog():
    """Lazy-import the body-region catalog to avoid a hard import cycle."""
    from engine.body_parts import BODY_REGIONS
    return BODY_REGIONS


def _region_exposure_map(player, graph):
    """Computed per-region exposure for a player (single source of truth).

    Derived in Python from the real catalog so the frontend never re-implements
    coverage logic. Returns ``{region_id: bool}`` for every region.
    """
    from engine.body_parts import BODY_REGIONS, is_exposed
    return {
        region_id: is_exposed(player, region_id, graph)
        for region_id in BODY_REGIONS
    }


def _connection_edge_props(direction, exit_data):
    """Build area→way edge properties from scenario exit data."""
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


class WorldSerializer:
    """Handles serialization of the full world state (to_dict, to_scenario_dict)
    and deserialization (load_from_dict, _load_from_template_format, _build_graph_from_legacy)."""

    def __init__(self, graph, player_manager, legacy_compat):
        self.graph = graph
        self.player_manager = player_manager
        self.legacy = legacy_compat

    def _compute_feels_like(self, player) -> int:
        """Compute equipment-adjusted feels_like temperature for a player."""
        from engine.equipment_bonuses import aggregate_bonuses, effective_temperature
        if not player or not player.current_area:
            return 21
        for node in self.graph.nodes.values():
            if node.type == "area" and node.name == player.current_area:
                env = node.properties.get("environment", {})
                equip_bonuses = aggregate_bonuses(player, self.graph)
                return int(effective_temperature(float(env.get("temperature", 21)), equip_bonuses))
        return 21

    def _normalize_item_node_actions(self):
        """Expire action inverses on loaded item nodes.

        The graph-node load path stores ``actions`` verbatim, so freshly loaded
        scenarios (e.g. ``world_template.json``) can carry ``take`` without
        ``drop``, ``equip`` without ``unequip``, ``open`` without ``close``.
        Running ``normalize_item_actions`` here makes the in-memory catalog
        canonical (take→drop, equip→unequip, etc.) so the prompt/UI see one
        consistent contract regardless of how the file was authored.
        """
        for node in self.graph.nodes.values():
            if node.type != "item":
                continue
            raw = node.properties.get("actions")
            if raw is None:
                continue
            node.properties["actions"] = normalize_item_actions(raw)

    def _grappled_by(self, player_name: str) -> Optional[str]:
        """Resolve who holds *player_name* from the grappled edge (if any)."""
        pnode = self.player_manager.player_node_id(player_name)
        for edge in self.graph.get_edges_for_target(pnode, "grappled"):
            node = self.graph.get_node(edge.source)
            if node and node.type == "character":
                return node.name
        return None

    def to_dict(self):
        players_serialized = {}
        for pname, p in self.player_manager.players.items():
            players_serialized[pname] = {
                "name": p.name,
                "personality": getattr(p, 'personality', ""),
                "description": getattr(p, 'description', ""),
                "base_description": getattr(p, 'base_description', ""),
                "equipped": dict(p.equipped),
                "stats": p.stats,
                "vitals": p.vitals,
                "skills": p.skills,
                "state": p.state,
                "perceived_conditions": perceived_conditions(p),
                "trait_behavior": [
                    TRAIT_DEFINITIONS.get(tid, {}).get("behavior_prompt")
                    for tid in (getattr(p, "traits", {}) or {})
                    if TRAIT_DEFINITIONS.get(tid, {}).get("behavior_prompt")
                ],
                "conditions": {
                    cid: [dict(inst) for inst in instances]
                    for cid, instances in (getattr(p, 'conditions', {}) or {}).items()
                },
                "grappled_by": self._grappled_by(pname),
                "state_timer": getattr(p, 'state_timer', 0),
                "traits": getattr(p, 'traits', {}),
                "tags": getattr(p, 'tags', []),
                "interest_tags": getattr(p, 'interest_tags', []),
                "discovered_items": list(getattr(p, 'discovered_items', []) or []),
                "decay_rates": getattr(p, 'decay_rates', {}),
                "body_state": getattr(p, 'body_state', {}),
                "body_region_names": {
                    rid: meta["name"] for rid, meta in _body_region_catalog().items()
                },
                "region_exposed": _region_exposure_map(p, self.graph),
                "current_area": p.current_area,
                "recent_hearing": getattr(p, 'recent_hearing', []),
                "emotion": {
                    "current": getattr(p, 'emotion', 'neutral'),
                    "intensity": getattr(p, 'emotion_intensity', 0.0),
                    "description": p.get_emotion_nl() if hasattr(p, 'get_emotion_nl') else ""
                },
                "emotions": p.emotions_map() if hasattr(p, 'emotions_map') else {},
                "emotions_description": (
                    p.emotions_description()
                    if hasattr(p, 'emotions_description') else ""
                ),
                "relationships": getattr(p, 'relationships', {}),
                "activity": getattr(p, 'activity', None),
                "memories": getattr(p, 'memories', []),
                "simple_npc": getattr(p, 'simple_npc', False),
                "autonomy": getattr(p, 'autonomy', True),
                "npc_behavior": getattr(p, 'npc_behavior', 'wander'),
                "npc_action_interval": getattr(p, 'npc_action_interval', 3),
                "npc_state": getattr(p, 'npc_state', 'idle'),
                "state_enter_tick": getattr(p, 'state_enter_tick', 0),
                "behaviors": getattr(p, 'behaviors', []),
                "patrol_route": getattr(p, 'patrol_route', []),
                "patrol_index": getattr(p, 'patrol_index', 0),
                "feels_like": self._compute_feels_like(p),
                "current_carry_weight": sum_carry_weight(self.graph, self.player_manager._player_node_id(pname)),
                "max_carry_capacity": get_carry_load_ratio(self.graph, self.player_manager, player_name=pname)["capacity"],
                "at_way_id": get_character_at_way(self.graph, self.player_manager.player_node_id(pname)),
                "spatial_position": get_spatial_position_data(
                    self.graph,
                    self.player_manager.player_node_id(pname),
                    self.player_manager,
                    self.player_manager.active_player or "",
                ),
            }

        rooms_serialized = {}
        for node in self.graph.nodes.values():
            if node.type == "area":
                env = node.properties.get("environment", {})
                ambient = self.player_manager.lighting.get_ambient_light(node.id, env)
                rooms_serialized[node.name] = {
                    "name": node.name,
                    "description": node.properties.get("description", ""),
                    "environment": env,
                    "ambient_light": ambient,
                    "light_description": self.player_manager.lighting.light_to_level(ambient),
                    "exits": self.player_manager.build_exits_for_area(node.name),
                    "items": [],
                    "floor": node.properties.get("floor", 0),
                    "properties": node.properties
                }

        return {
            "current_area": self.legacy.current_area.name if self.legacy.current_area else None,
            "players_in_area": self.player_manager.get_players_in_area(),
            "players": players_serialized,
            "active_player": self.player_manager.active_player,
            "game_log": self.legacy.game_log,
            "log_revision": self.legacy.log_revision,
            "game_time": self.legacy.get_current_time(),
            "time_ticks": self.legacy.time_ticks,
            "time_per_tick_minutes": self.legacy.time_per_tick_minutes,
            "clock_start_hour": self.legacy.clock_start_hour,
            "clock_start_minute": self.legacy.clock_start_minute,
            "areas": rooms_serialized,
            "rooms": rooms_serialized,
            "graph": self.graph.to_dict(),
            "ways": getattr(self.legacy, 'ways', {}),
            "item_registry": getattr(self.legacy, 'item_registry', {}),
            "turn_events": self.legacy.turn_events,
            "turn_number": self.legacy.turn_number,
            "narration_mode": self.legacy.narration_mode,
            "ghost_mode": self.legacy.ghost_mode,
            "world_lore": self.legacy.world_lore,
            "delayed_events": self.legacy.delayed_events.to_dict()
        }

    def to_scenario_dict(self):
        """Return authorial content only — strips play artifacts for scenario saving."""
        data = self.to_dict()
        data.pop("game_log", None)
        data.pop("turn_events", None)
        data.pop("log_revision", None)
        data.pop("delayed_events", None)
        for pdata in data.get("players", {}).values():
            pdata.pop("recent_hearing", None)
        return data

    def load_from_dict(self, data):
        if "player" in data and "players" not in data:
            self._load_from_template_format(data)
            return

        if "graph" in data:
            self.graph.load_from_dict(data["graph"])
            self._normalize_item_node_actions()
        else:
            self._build_graph_from_legacy(data)

        self.legacy.time_ticks = data.get("time_ticks", 0)
        self.legacy.time_per_tick_minutes = data.get("time_per_tick_minutes", 5)
        self.legacy.clock_start_hour = data.get("clock_start_hour", 8)
        self.legacy.clock_start_minute = data.get("clock_start_minute", 0)
        self.legacy.turn_number = data.get("turn_number", 0)
        self.legacy.turn_events = list(data.get("turn_events", []))
        self.legacy.game_log = list(data.get("game_log", []))
        self.legacy.log_revision = data.get("log_revision", 0)
        self.legacy.narration_mode = data.get("narration_mode", "none")
        self.legacy.ghost_mode = data.get("ghost_mode", False)
        self.legacy.speech_log.clear()

        temp_players = {}
        for pname, pdata in data.get("players", {}).items():
            p = Player(pname)
            p.personality = pdata.get("personality", "")
            p.description = pdata.get("description", "")
            p.base_description = pdata.get("base_description", "")
            p.equipped = pdata.get("equipped", dict(p.equipped))
            p.stats = pdata.get("stats", {})
            p.vitals = {**p.vitals, **pdata.get("vitals", {})}
            if "Max_HP" not in p.vitals:
                p.vitals["Max_HP"] = 100
            if "HP" in p.vitals:
                p.vitals["HP"] = max(0, min(p.vitals["Max_HP"], p.vitals["HP"]))
            if "Energy" in p.vitals:
                p.vitals["Energy"] = max(0, min(100, p.vitals["Energy"]))
            p.decay_rates = pdata.get("decay_rates", p.decay_rates)
            p.body_state = pdata.get("body_state", p.body_state)
            p.skills = pdata.get("skills", {})
            p.state = pdata.get("state", "awake")
            p.load_conditions(pdata.get("conditions"))
            # Legacy saves carried one global state_timer for timed conditions;
            # apply it to those conditions only when it was actually set.
            legacy_timer = pdata.get("state_timer") or 0
            if legacy_timer > 0:
                from player import CONDITION_DEFAULT_TIMERS
                timed = [c for c in p.conditions if c in CONDITION_DEFAULT_TIMERS]
                for c in (timed or [p.state]):
                    instances = p.conditions.setdefault(c, [])
                    if not instances:
                        instances.append({"duration": None, "source": None, "level": 0})
                    instances[0]["duration"] = legacy_timer
            p.traits = pdata.get("traits", {})
            p.tags = list(pdata.get("tags", []))
            p.interest_tags = list(pdata.get("interest_tags", []))
            p.current_area = pdata.get("current_area") or data.get("current_area") or data.get("current_room")
            p.recent_hearing = pdata.get("recent_hearing", [])
            pdata_memory = pdata.get("memory", {})
            if pdata_memory:
                pass  # legacy _memory kv dict no longer persisted
            emotion_data = pdata.get("emotion", {})
            if isinstance(emotion_data, dict):
                p.emotion = emotion_data.get("current", "neutral")
                p.emotion_intensity = emotion_data.get("intensity", 0.0)
            if isinstance(pdata.get("emotions"), dict):
                p.load_emotions(pdata["emotions"])
            rel_data = pdata.get("relationships", {})
            if isinstance(rel_data, dict):
                p.relationships = dict(rel_data)
            mem_data = pdata.get("memories", [])
            if isinstance(mem_data, list):
                for m in mem_data:
                    if not m.get("id"):
                        m["id"] = str(uuid.uuid4())[:8]
                    if "entity_ids" not in m:
                        m["entity_ids"] = []
                    if "source" not in m:
                        m["source"] = "auto"
                p.memories = list(mem_data)
            p.simple_npc = pdata.get("simple_npc", False)
            p.autonomy = pdata.get("autonomy", True)
            p.npc_behavior = pdata.get("npc_behavior", "wander")
            p.npc_action_interval = pdata.get("npc_action_interval", 3)
            p.npc_state = pdata.get("npc_state", "idle")
            p.state_enter_tick = pdata.get("state_enter_tick", 0)
            p.behaviors = pdata.get("behaviors", [])
            p.patrol_route = pdata.get("patrol_route", [])
            p.patrol_index = pdata.get("patrol_index", 0)
            p.activity = pdata.get("activity", None) or None
            p.exhaustion_count = pdata.get("exhaustion_count", 0)
            temp_players[pname] = p

        self.player_manager.players = temp_players
        self.player_manager.active_player = data.get("active_player") or (next(iter(temp_players.keys())) if temp_players else None)

        for pname, p in self.player_manager.players.items():
            pnode_id = self.player_manager.player_node_id(pname)
            if not self.graph.get_node(pnode_id):
                self.graph.add_node(Node(id=pnode_id, type="character", name=pname))
            if p.current_area:
                self.player_manager.set_player_area(pname, p.current_area)
            for slot_name, stack in (p.equipped or {}).items():
                for item_id in stack:
                    if isinstance(item_id, str) and not item_id.startswith("__"):
                        if self.graph.get_node(item_id):
                            self.graph.add_edge(Edge(
                                source=item_id,
                                target=pnode_id,
                                type=EDGE_EQUIPPED,
                                properties={"slot": slot_name}
                            ))

        # Rebuild player.equipped from graph edges to ensure consistency
        for pname, p in self.player_manager.players.items():
            pnode_id = self.player_manager.player_node_id(pname)
            self.legacy.equipment._sync_equipped_from_graph(p, pnode_id)

        self.legacy.ways = data.get("ways", {})
        self.legacy.item_registry = data.get("item_registry", {})
        self.legacy.world_lore = data.get("world_lore", [])
        from engine.event_queue import DelayedEventQueue
        self.legacy.delayed_events = DelayedEventQueue.from_dict(data.get("delayed_events", []))

    def _load_from_template_format(self, data):
        """Load from world_template.json format (single player, areas with items/exits)."""
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
                }
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
                        trigger_node = Node(id=trigger_id, type="logic_trigger", name=f"{trigger_type} → {effect_type}", properties=trigger_properties)
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
                        content_trigger_node = Node(id=content_trigger_node_id, type="logic_trigger", name=f"{content_trigger_type} → {content_trigger_effect}", properties=content_trigger_properties)
                        self.graph.add_node(content_trigger_node)
                        self.graph.add_edge(Edge(source=content_id, target=content_trigger_node_id, type="triggers", properties=content_trigger_properties))

        start_area = data.get("current_area", list(rooms_data.keys())[0] if rooms_data else "Living Area")
        p.current_area = start_area
        player_node_id = self.player_manager.player_node_id(p.name)
        area_node_id = self.player_manager.area_node_id(start_area)
        if self.graph.get_node(player_node_id) and self.graph.get_node(area_node_id):
            self.graph.add_edge(Edge(source=player_node_id, target=area_node_id, type=EDGE_IN))

        self.legacy._create_locked_with_unlocks()
        self.legacy.world_lore = data.get("world_lore", [])

    def _build_graph_from_legacy(self, data: dict):
        """Convert legacy areas/items/players dictionary into graph nodes and edges."""
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
