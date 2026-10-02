import random
import time
import uuid
import logging
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
from engine.character_identity import collapse_character_identity, rewrite_known

logger = logging.getLogger(__name__)


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
        """Compute equipment-adjusted feels_like temperature for a player.

        task-439: resolve ``current_area`` by id first, then unambiguously by
        display name (``engine.room_perception.resolve_area``), instead of the
        first name match in iteration order. Two areas sharing a display name
        used to give a character the wrong area's temperature silently.
        """
        from engine.equipment_bonuses import aggregate_bonuses, effective_temperature
        from engine.room_perception import resolve_area_node
        if not player or not player.current_area:
            return 21
        node = resolve_area_node(self.graph, player.current_area)
        if node is None:
            return 21
        env = node.properties.get("environment", {})
        equip_bonuses = aggregate_bonuses(player, self.graph)
        return int(effective_temperature(float(env.get("temperature", 21)), equip_bonuses,
                                         wind_level=env.get("wind", "none"),
                                         humidity=env.get("humidity", "dry")))

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
            "id": getattr(p, 'id', ''),
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
            # task-605: size is a property, not a trait, so it needs its own key
            # here. The inspector's Size control reads `player.size` from this
            # payload; without it the control can never show a saved value and
            # would silently revert to "not set" on every render.
            "size": getattr(p, 'size', None),
            "tags": getattr(p, 'tags', []),
            "flags": dict(getattr(p, 'flags', {})),
            "hidden": bool(getattr(p, 'hidden', False)),
            # Transient soak order (task-481) for the initiative list; not part of
            # the save's durable state (there is nothing to restore).
            "soak": (
                {"intent": (getattr(p, "soak_order", None) or {}).get("intent"),
                 "remaining_minutes": round(float(
                     (getattr(p, "soak_order", None) or {}).get("remaining_minutes", 0) or 0), 1)}
                if getattr(p, "soak_order", None) else None
            ),
            "manifested": bool(getattr(p, 'manifested', False)),
            "known": list(getattr(p, 'known', []) or []),
            "crafting_known": list(getattr(p, 'crafting_known', []) or []),
            "discovered_exits": list(getattr(p, 'discovered_exits', []) or []),
            "interest_tags": getattr(p, 'interest_tags', []),
            "fear_tags": getattr(p, 'fear_tags', []),
            "carcass_item": getattr(p, 'carcass_item', None),
            "discovered_items": list(getattr(p, 'discovered_items', []) or []),
            "decay_rates": getattr(p, 'decay_rates', {}),
            "body_state": getattr(p, 'body_state', {}),
            "body_region_names": {
                rid: meta["name"] for rid, meta in _body_region_catalog().items()
            },
            "region_exposed": _region_exposure_map(p, self.graph),
            "current_area": p.current_area,
            # task-581: the canonical id of the authoritative location record
            # (the character's `in` edge). The display name above is a
            # resolution layer over it; a consumer that can hold an id should
            # use this, so a duplicate display name can never re-home them.
            "current_area_id": self.graph.area_of(
                self.player_manager._player_node_id(pname)),
            "recent_hearing": getattr(p, 'recent_hearing', []),
            "emotion": {
                "current": getattr(p, 'emotion', 'neutral'),
                "intensity": getattr(p, 'emotion_intensity', 0.0),
                # Canonical expression-portrait key derived from the affect map
                # (the state events/decisions produced), so the node/chip/examine
                # art follows the mood rather than the legacy free-text label.
                "expression": (
                    p.dominant_expression() if hasattr(p, 'dominant_expression') else "neutral"
                ),
                "description": p.get_emotion_nl() if hasattr(p, 'get_emotion_nl') else ""
            },
            "emotions": p.emotions_map() if hasattr(p, 'emotions_map') else {},
            "emotions_description": (
                p.emotions_description()
                if hasattr(p, 'emotions_description') else ""
            ),
            "relationships": getattr(p, 'relationships', {}),
            "activity": getattr(p, 'activity', None),
            # The bounded objective record of what this character lived
            # (engine/lived_log.py). Serialized here as of task-542: the reader
            # below has always accepted a "trace" key, but nothing ever *wrote*
            # it, so the whole store was silently lost on every reload. A scenario
            # payload drops it again in to_scenario_dict — it is runtime history,
            # not authored content.
            "lived_log": [dict(e) for e in (getattr(p, 'lived_log', []) or [])],
            "memories": getattr(p, 'memories', []),
            "memory_index": dict(getattr(p, 'memory_index', {}) or {}),
            "schedule": list(getattr(p, 'schedule', []) or []),
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
            # task-313: the heading of the last crossing. The agent prompt reads
            # this to tell a character which relative words will work for it, so
            # without it here "left"/"right" would resolve in the engine and never
            # be used by anyone — a mechanic wired to nothing.
            "facing": getattr(p, "facing", None),
            "entered_from_way": getattr(p, "entered_from_way", None),
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
        # task-439: the canonical, id-keyed area projection. The id is the
        # stable handle; a display name may repeat (Deep Forest has many
        # "Hollow"s), and a name-keyed map silently collapses them. Every
        # consumer that can address an area by id should read this map.
        areas_by_id = {}
        for node in self.graph.nodes.values():
            if node.type == "area":
                env = node.properties.get("environment", {})
                ambient = self.player_manager.lighting.get_ambient_light(node.id, env)
                record = {
                    "id": node.id,
                    "name": node.name,
                    "description": node.properties.get("description", ""),
                    "environment": env,
                    "ambient_light": ambient,
                    "light_description": self.player_manager.lighting.light_to_level(ambient),
                    # Pass the id: exits are the graph's (task-439 resolves it),
                    # and a duplicate display name cannot pick the wrong area.
                    "exits": self.player_manager.build_exits_for_area(node.id),
                    "exits_authoring": self.player_manager.build_exits_for_area(node.id, include_hidden=True),
                    "items": [],
                    # `floor` is the area's STOREY index (0 ground, 1 up, -1 down,
                    # unbounded); `surface` is the ground material. They are two
                    # different facts — see engine/world_grid.PAINT_LAYERS.
                    "floor": node.properties.get("floor", 0),
                    "surface": node.properties.get("surface", ""),
                    "properties": node.properties
                }
                areas_by_id[node.id] = record
                # The name-keyed map stays because the live frontend reads
                # worldState.areas[<area name>] / [player.current_area] (40+
                # sites) and `player.current_area` is still a display name — the
                # string→id refactor is task-581. It is a convenience view, not
                # the canonical one: on a duplicate name the *last* writer wins
                # here, while areas_by_id keeps both.
                rooms_serialized[node.name] = record

        return {
            "current_area": self.legacy.current_area.name if self.legacy.current_area else None,
            "players_in_area": self.player_manager.get_players_in_area(),
            "area_presence": getattr(self.legacy, 'area_presence', {}) or {},
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
            # task-439: canonical id-keyed projection (see _serialize_world).
            "areas_by_id": areas_by_id,
            "graph": self.graph.to_dict(),
            "ways": getattr(self.legacy, 'ways', {}),
            "item_registry": getattr(self.legacy, 'item_registry', {}),
            "turn_events": self.legacy.turn_events,
            "turn_number": self.legacy.turn_number,
            "narration_mode": self.legacy.narration_mode,
            "ghost_mode": self.legacy.ghost_mode,
            "mature_content": getattr(self.legacy, "mature_content", False),
            # The scenario's own name. Without this a saved file cannot be
            # identified on reload (routes fall back to "unnamed"), and the
            # frontend's _scenarioIdentity() — which gates the local
            # background-map cache — always sees null.
            "_scenario_name": getattr(self.legacy, "_scenario_name", None),
            "world_lore": self.legacy.world_lore,
            # task-397: hierarchy manifest (authored), not a projection. Optional.
            "world_scopes": getattr(self.legacy, "world_scopes", {}) or {},
            # task-583: the resident scope index (ownership, location, gateways,
            # due work). A derived cache of the loaded graph, but saved so an
            # unloaded scope's ownership and gateways survive a round trip.
            "world_index": (
                self.legacy.world_index.to_dict()
                if getattr(self.legacy, "world_index", None) is not None else {}
            ),
            "calendar_config": getattr(self.legacy, "calendar_config", None),
            "forecast_schedule": getattr(self.legacy, "forecast_schedule", None),
            "forecast_override": getattr(self.legacy, "forecast_override", None),
            "graph_background": getattr(self.legacy, "graph_background", None),
            "delayed_events": self.legacy.delayed_events.to_dict()
        }

    def _deserialize_player(self, pname, pdata):
        p = Player(pname)
        # task-446: the registry key may be an id (duplicate display names), so
        # the authoritative display name comes from the payload.
        if pdata.get("name"):
            p.name = pdata["name"]
        # task-316: restore the stable identity (fall back to a fresh id for
        # legacy saves that never had one).
        p.id = pdata.get("id") or p.id
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
        from engine.lived_log import load as _lived_log_load
        # Task-542 renamed the save key "trace" -> "lived_log". Both are read, in
        # this order, so a save written before the rename still loads; engine/
        # lived_log.load() likewise accepts the old per-entry "t" tick key.
        _lived_log_load(p, pdata.get("lived_log", pdata.get("trace")))
        p.simulation_mode = pdata.get("simulation_mode", "active")
        try:
            p.next_due_tick = int(pdata.get("next_due_tick", 0) or 0)
        except (TypeError, ValueError):
            p.next_due_tick = 0
        try:
            p.last_offload_tick = int(pdata.get("last_offload_tick", 0) or 0)
        except (TypeError, ValueError):
            p.last_offload_tick = 0
        try:
            p.background_consolidated_through = int(
                pdata.get("background_consolidated_through", 0) or 0)
        except (TypeError, ValueError):
            p.background_consolidated_through = 0
        p.body_state = pdata.get("body_state", p.body_state)
        # Merge over the defaults so a save from before the full skill list
        # (task-474) still ends up with every skill on the sheet.
        _skills = dict(p.skills or {})
        _skills.update(pdata.get("skills", {}) or {})
        p.skills = _skills
        try:
            p.proficiency = int(pdata.get("proficiency", 0) or 0)
        except (TypeError, ValueError):
            p.proficiency = 0
        p.skill_progress = dict(pdata.get("skill_progress", {}) or {})
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
        p.sync_vitals_with_tags()
        p.flags = dict(pdata.get("flags", {}))
        p.hidden = bool(pdata.get("hidden", False))
        p.manifested = bool(pdata.get("manifested", False))
        p.known = list(pdata.get("known", []) or [])
        p.crafting_known = list(pdata.get("crafting_known", []) or [])
        p.discovered_exits = {
            tuple(x) for x in (pdata.get("discovered_exits", []) or []) if isinstance(x, (list, tuple)) and len(x) == 2
        }
        p.interest_tags = list(pdata.get("interest_tags", []))
        p.fear_tags = list(pdata.get("fear_tags", []))
        p.carcass_item = pdata.get("carcass_item")
        p.current_area = pdata.get("current_area") or pdata.get("current_area") or pdata.get("current_room")
        # task-313 facing. Old saves and scenarios predate the field, so both
        # keys are read with a None default: a character loaded from one simply
        # has no facing and the relative words explain that, rather than the
        # load inventing a heading nobody travelled.
        p.facing = pdata.get("facing") or None
        p.entered_from_way = pdata.get("entered_from_way") or None
        p.recent_hearing = pdata.get("recent_hearing", [])
        pdata_memory = pdata.get("memory", {})
        if pdata_memory:
            pass
        emotion_data = pdata.get("emotion", {})
        if isinstance(pdata.get("emotions"), dict) and pdata["emotions"]:
            p.load_emotions(pdata["emotions"])
        elif isinstance(emotion_data, dict):
            # **One-time migration for a save written before the affect map was
            # the state** (task-652). The legacy `{current, intensity}` pair is
            # folded into the map here and nowhere else, so a world saved by any
            # earlier build comes back feeling what it was saved feeling rather
            # than blank. Once a save carries `emotions`, the legacy pair is
            # ignored on load — it is a cache of the map now, not a second
            # opinion, and letting it win would be the duplication this task
            # exists to remove.
            p.emotion = emotion_data.get("current", "neutral")
            try:
                p.emotion_intensity = emotion_data.get("intensity", 0.0)
            except (TypeError, ValueError):
                pass
        rel_data = pdata.get("relationships", {})
        if isinstance(rel_data, dict):
            p.relationships = dict(rel_data)
        # Authored daily schedule (task-409). Normalised on load so a
        # hand-edited or legacy file cannot put a malformed step into the day.
        from engine.schedule import normalize as _normalize_schedule
        p.schedule = _normalize_schedule(pdata.get("schedule"))
        # Authored multi-step plan (task-426). A stored plan is resumed as-is;
        # completed_plans is what stops a non-repeating plan from restarting.
        p.plan = pdata.get("plan") or None
        p.completed_plans = list(pdata.get("completed_plans", []) or [])

        mem_data = pdata.get("memories", [])
        if isinstance(mem_data, list):
            for m in mem_data:
                if not m.get("id"):
                    m["id"] = str(uuid.uuid4())[:8]
                if "entity_ids" not in m:
                    m["entity_ids"] = []
                if "source" not in m:
                    m["source"] = "auto"
                m.setdefault("location", "")
            p.memories = list(mem_data)
        # The observation index is derived, so rebuild it from the memories
        # rather than trusting a stored copy: an older save has no index at all,
        # and a hand-edited one could point at a memory that no longer exists.
        p.memory_index = {}
        stored_index = pdata.get("memory_index")
        if isinstance(stored_index, dict):
            p.memory_index = {str(k): str(v) for k, v in stored_index.items()}
        by_id = {m.get("id"): m for m in p.memories}
        for subject, entry_id in list(p.memory_index.items()):
            entry = by_id.get(entry_id)
            if entry is None or entry.get("superseded_by"):
                p.memory_index.pop(subject, None)
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
        # task-403: authored starting knowledge. Idempotent by memory text, so a
        # re-loaded save never duplicates it, and absent keys mean a no-op.
        if (pdata.get("preconceived_knowledge") or pdata.get("known_areas")
                or pdata.get("known_ways")):
            from engine.agent_memory import AgentMind
            AgentMind(p, self.graph).load_preconceived(pdata)
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
            # A character does not *author* their lived history, so it is runtime
            # state in the same way recent_hearing is (task-542). Keeping it would
            # grow a scenario file by 200 entries per character on the first save.
            pdata.pop("lived_log", None)
            # task-403/425: a scenario is authored content, so it carries no
            # runtime *perception*. Merely loading a scenario observes every
            # character's starting area (engine/observation.py), and saving it
            # back would otherwise bake that into the file — 23 characters'
            # worth of "you have been in Blackmarsh" written into the scenario
            # and growing it by ~60KB on the first save, for state the loader
            # regenerates anyway. `memory_index` is derived and goes with them;
            # authored memories (`source: manual`, i.e. preconceived knowledge)
            # stay. A savegame uses `to_dict()` and keeps everything.
            pdata["memories"] = [
                m for m in (pdata.get("memories") or [])
                if m.get("source") != "observation"
            ]
            pdata.pop("memory_index", None)
        # task-222, continued: a saved world is graph-only, so nothing here is
        # a second copy of data already carried by `graph.nodes`:
        #   - `areas` / `rooms` are projections the loader never reads
        #     (LegacyCompat rebuilds them from the graph), and `rooms` was the
        #     same dict written twice — 13% of the file, byte for byte.
        #   - `ways` / `item_registry` were legacy attrs only the loader
        #     populated and nothing consumed.
        # Every field of an `areas` entry that mattered already lives on the
        # node (`name`, `description`, `environment`, `floor`, `surface`,
        # `properties`); `ambient_light`/`light_description` are recomputed each
        # tick and `items` was always empty (placement is the graph's `in` edges).
        #
        # The LIVE payload (to_dict) keeps all of them: the frontend reads
        # worldState.areas / .ways (agent-engine, agent-lens, inspector,
        # item-library/placement, graph/layout-engine).
        data.pop("areas", None)
        data.pop("rooms", None)
        data.pop("areas_by_id", None)
        # The scope index is derived from the authored graph + manifest, so a
        # scenario re-derives it on load rather than carrying a second copy.
        data.pop("world_index", None)
        data.pop("ways", None)
        data.pop("item_registry", None)
        # Omit an empty name rather than writing "": the load path tests
        # `data.get('_scenario_name') or data.get('name')`, so an empty string
        # reads as "unnamed" and silently outranks a real name.
        if not data.get("_scenario_name"):
            data.pop("_scenario_name", None)
        self.strip_redundant_exits(data)
        return data

    @staticmethod
    def strip_redundant_exits(data):
        """task-222: saved worlds are graph-only — the per-room ``exits`` /
        ``exits_authoring`` copies are always recomputed at runtime
        (build_exits_for_area), so writing them is redundant data that can
        drift. Keep the live /api/state payload intact (to_dict is separate);
        only FILE payloads pass through here.
        """
        for key in ("areas", "rooms"):
            rooms = data.get(key, {}) or {}
            for room in rooms.values():
                if isinstance(room, dict):
                    room.pop("exits", None)
                    room.pop("exits_authoring", None)

    def load_from_dict(self, data):
        if "player" in data and "players" not in data:
            self._template_loader.load(data)
            return

        # task-463: collapse the authored character_<slug> node and the runtime
        # player_<Name> anchor into one canonical node before the graph is built,
        # and keep every retired id resolvable through the alias index.
        aliases = {}
        if "graph" in data:
            report = collapse_character_identity(data["graph"], data.get("players") or {})
            aliases = report.get("aliases") or {}
            self.graph.load_from_dict(data["graph"])
            self.graph.register_aliases(aliases)
            self._normalize_item_node_actions()
        else:
            self._legacy_loader.load(data)

        # task-439: a duplicate area display name is legal (ids are the identity)
        # but makes a name-only lookup ambiguous, so surface it at load rather
        # than let the first iteration-order match silently win.
        from engine.room_perception import duplicate_area_names
        duplicate_areas = duplicate_area_names(self.graph)
        if duplicate_areas:
            logger.warning(
                "[load] duplicate area display name(s) — resolve these by id: %s",
                duplicate_areas)

        self.legacy.time_ticks = data.get("time_ticks", 0)
        self.legacy.time_per_tick_minutes = data.get("time_per_tick_minutes", 5)
        self.legacy.clock_start_hour = data.get("clock_start_hour", 8)
        self.legacy.clock_start_minute = data.get("clock_start_minute", 0)
        self.legacy.turn_number = data.get("turn_number", 0)
        self.legacy.turn_events = list(data.get("turn_events", []))
        self.legacy.game_log = list(data.get("game_log", []))
        # task-360 presence ledger (per-area {char: entry_tick}) — restore as-is.
        try:
            raw_presence = data.get("area_presence", {}) or {}
            self.legacy.area_presence = {
                str(aid): {str(c): int(t) for c, t in (list(present.items()) if isinstance(present, dict) else [])}
                for aid, present in raw_presence.items()
            }
        except Exception:
            self.legacy.area_presence = {}
        self.legacy.log_revision = data.get("log_revision", 0)
        self.legacy.narration_mode = data.get("narration_mode", "none")
        # Round-trip the scenario's name so a saved file stays identifiable
        # without the load route having to re-derive it.
        self.legacy._scenario_name = (
            data.get("_scenario_name")
            or getattr(self.legacy, "_scenario_name", None)
            or ""
        )
        self.legacy.ghost_mode = data.get("ghost_mode", False)
        self.legacy.mature_content = data.get("mature_content", False)
        self.legacy.speech_log.clear()

        temp_players = {}
        for pname, pdata in data.get("players", {}).items():
            p = self._deserialize_player(pname, pdata)
            temp_players[pname] = p

        self.player_manager.players = temp_players
        # task-463: an authored `known` list may name a retired character id
        # ("character_arix"); move it onto the surviving identity.
        if aliases:
            for p in temp_players.values():
                if getattr(p, "known", None):
                    known, changed = rewrite_known(p.known, aliases)
                    if changed:
                        p.known = known
        # task-446: rebuild the id→key index and give duplicate-keyed players a
        # unique anchor after a bulk load. (self.player_manager here is the
        # world; the real manager hangs off it.)
        _pm = getattr(self.player_manager, "player_manager", None)
        if _pm is not None and hasattr(_pm, "reindex"):
            _pm.reindex()
        self.player_manager.active_player = data.get("active_player") or (next(iter(temp_players.keys())) if temp_players else None)

        for pname, p in self.player_manager.players.items():
            pnode_id = self.player_manager.player_node_id(pname)
            if not self.graph.get_node(pnode_id):
                self.graph.add_node(Node(id=pnode_id, type="character", name=pname))
            # task-581: the character's `in` edge is the authoritative location
            # record; the saved `current_area` display name is a resolution layer
            # over it. Prefer the edge, so a hand-edit to the string that
            # disagrees with the graph cannot re-home a character on load.
            edge_area_id = self.graph.area_of(pnode_id)
            edge_area = self.graph.get_node(edge_area_id) if edge_area_id else None
            if edge_area is not None:
                p.current_area = edge_area.name
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
        # task-397: optional hierarchy manifest; absent in legacy scenarios.
        raw_scopes = data.get("world_scopes")
        self.legacy.world_scopes = raw_scopes if isinstance(raw_scopes, dict) else {}
        # task-583: restore the resident scope index. A save may carry entries
        # for scopes it did not load (ownership, gateways, due work); when it
        # does not, derive them from the graph so a legacy world gets an index.
        index = getattr(self.legacy, "world_index", None)
        if index is not None:
            from engine.world.index import GlobalScopeIndex
            raw_index = data.get("world_index")
            if isinstance(raw_index, dict) and raw_index:
                restored = GlobalScopeIndex.from_dict(raw_index)
                self.legacy.world_index = restored
                restored.augment_from_graph(self.graph, self.legacy.world_scopes)
            else:
                index.reindex(self.graph, self.legacy.world_scopes)
        # Graph background map: image path + transform (presentation only).
        background = data.get("graph_background")
        self.legacy.graph_background = background if isinstance(background, dict) else {}
        # task-228/227: calendar + forecast persist through saves.
        if isinstance(data.get("calendar_config"), dict):
            defaults = getattr(self.legacy, "calendar_config", None) or {}
            combined = dict(defaults)
            combined.update(data["calendar_config"])
            self.legacy.calendar_config = combined
        if isinstance(data.get("forecast_schedule"), dict):
            self.legacy.forecast_schedule = data["forecast_schedule"]
        self.legacy.forecast_override = data.get("forecast_override")
        self.legacy._forecast_sched_obj = None
        from engine.event_queue import DelayedEventQueue
        self.legacy.delayed_events = DelayedEventQueue.from_dict(data.get("delayed_events", []))

        # Perception at load (task-403): a character knows the room it is
        # standing in from the moment it is there. Observations are otherwise
        # written on arrival, so without this pass the one area a character
        # could never remember would be the one it started in — and task-425's
        # novelty would pay for it again on the first re-entry.
        try:
            from engine.observation import observe_area
            for p in self.player_manager.players.values():
                observe_area(p, self.legacy)
        except Exception as e:
            logger.warning("[observation] initial pass failed: %s", e)
