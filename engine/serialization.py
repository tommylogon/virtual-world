import random
import time
import uuid
from typing import Optional

from graph import EDGE_CONNECTION, EDGE_IN, EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT, Edge, Node, WorldGraph
from player import Player
from area import Area
from engine.conditions import perceived_conditions
from engine.traits import TraitSystem, TRAIT_DEFINITIONS
from engine.item_actions import get_carry_load_ratio, sum_carry_weight, normalize_item_actions
from engine.beyond_visibility import normalize_visible_items
from engine.character_spatial import get_character_at_way, get_spatial_position_data
from engine.serialization_template import TemplateLoader
from engine.serialization_legacy import LegacyLoader


def _body_region_catalog():
    """Lazy-import the body-region catalog to avoid a hard import cycle."""
    from engine.body_parts import BODY_REGIONS
    return BODY_REGIONS


#: Lowercase keys that need a non-trivial canonical form (not just capitalize).
_VITAL_KEY_ALIASES = {"hp": "HP", "max_hp": "Max_HP", "mp": "Mana", "max_mp": "Max_Mana"}


def canonical_vitals(vitals) -> dict:
    """Fold mixed-case vital keys into their canonical form.

    Library character files have historically carried BOTH cases ("Social"
    and "social") — the lowercase duplicates leak into the runtime vitals
    dict, where lowercase readers (talkinessHint reads ``vitals.social``)
    pick them up and misread character state. Capitalized/aliased wins.
    """
    if not isinstance(vitals, dict):
        return dict(vitals or {})
    out = {}
    for k, v in vitals.items():
        key = str(k)
        if key in _VITAL_KEY_ALIASES:
            key = _VITAL_KEY_ALIASES[key]
        elif key and key[0].islower():
            key = key[0].upper() + key[1:]
        out[key] = v
    return out


def _region_exposure_map(player, graph):
    """Computed per-region exposure for a player (single source of truth)."""
    from engine.body_parts import BODY_REGIONS, is_exposed
    return {
        region_id: is_exposed(player, region_id, graph)
        for region_id in BODY_REGIONS
    }


class WorldSerializer:
    """Facade that delegates serialization to format-specific loaders."""

    def __init__(self, graph, player_manager, legacy_compat):
        self.graph = graph
        self.player_manager = player_manager
        self.legacy = legacy_compat
        self._template_loader = TemplateLoader(graph, player_manager, legacy_compat)
        self._legacy_loader = LegacyLoader(graph, player_manager, legacy_compat)

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

    def _grappled_by(self, player_name: str) -> Optional[str]:
        """Resolve who holds *player_name* from the grappled edge (if any)."""
        pnode = self.player_manager.player_node_id(player_name)
        for edge in self.graph.get_edges_for_target(pnode, "grappled"):
            node = self.graph.get_node(edge.source)
            if node and node.type == "character":
                return node.name
        return None

    def _normalize_item_node_actions(self):
        """Expire action inverses on loaded item nodes."""
        for node in self.graph.nodes.values():
            if node.type != "item":
                continue
            raw = node.properties.get("actions")
            if raw is None:
                continue
            node.properties["actions"] = normalize_item_actions(raw)

    def _serialize_player(self, pname, p):
        return {
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
            "known": list(getattr(p, 'known', []) or []),
            "discovered_exits": list(getattr(p, 'discovered_exits', []) or []),
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

    def _serialize_world(self):
        players_serialized = {}
        for pname, p in self.player_manager.players.items():
            players_serialized[pname] = self._serialize_player(pname, p)

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
                    "exits_authoring": self.player_manager.build_exits_for_area(node.name, include_hidden=True),
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

    def _deserialize_player(self, pname, pdata):
        p = Player(pname)
        p.personality = pdata.get("personality", "")
        p.description = pdata.get("description", "")
        p.base_description = pdata.get("base_description", "")
        p.equipped = pdata.get("equipped", dict(p.equipped))
        p.stats = pdata.get("stats", {})
        p.vitals = {**p.vitals, **canonical_vitals(pdata.get("vitals", {}))}
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
        p.known = list(pdata.get("known", []) or [])
        p.discovered_exits = {
            tuple(x) for x in (pdata.get("discovered_exits", []) or []) if isinstance(x, (list, tuple)) and len(x) == 2
        }
        p.interest_tags = list(pdata.get("interest_tags", []))
        p.current_area = pdata.get("current_area") or pdata.get("current_area") or pdata.get("current_room")
        p.recent_hearing = pdata.get("recent_hearing", [])
        pdata_memory = pdata.get("memory", {})
        if pdata_memory:
            pass
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
        return p

    def to_dict(self):
        return self._serialize_world()

    def to_scenario_dict(self):
        data = self._serialize_world()
        data.pop("game_log", None)
        data.pop("turn_events", None)
        data.pop("log_revision", None)
        data.pop("delayed_events", None)
        for pdata in data.get("players", {}).values():
            pdata.pop("recent_hearing", None)
        return data

    def load_from_dict(self, data):
        if "player" in data and "players" not in data:
            self._template_loader.load(data)
            return

        if "graph" in data:
            self.graph.load_from_dict(data["graph"])
            self._normalize_item_node_actions()
        else:
            self._legacy_loader.load(data)

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
            p = self._deserialize_player(pname, pdata)
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
                                type=EDGE_CONNECTION,
                                properties={"slot": slot_name}
                            ))

        for pname, p in self.player_manager.players.items():
            pnode_id = self.player_manager.player_node_id(pname)
            self.legacy.equipment._sync_equipped_from_graph(p, pnode_id)

        self.legacy.ways = data.get("ways", {})
        self.legacy.item_registry = data.get("item_registry", {})
        self.legacy.world_lore = data.get("world_lore", [])
        from engine.event_queue import DelayedEventQueue
        self.legacy.delayed_events = DelayedEventQueue.from_dict(data.get("delayed_events", []))