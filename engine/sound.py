"""Sound propagation system for the virtual world engine.

Handles speech levels, sound source propagation, and ambient noise dampening
using graph-scan approach similar to the lighting system.
"""
from typing import List, Dict, Optional, Set, Tuple
from collections import deque
from graph import WorldGraph, Node, Edge, EDGE_CONNECTION
from engine.runtime_config import config as _config


# Speech levels with penetration values. These are the engine's own defaults;
# runtime_config may override them at load, so lookups go through the config
# singleton. The module-level dicts below derive from config.get() on each
# access so a live "Engine Config" save takes effect immediately.
def _speech_levels() -> Dict[str, int]:
    return {
        "whisper": _config_get_int("sound.speech_whisper", 0),
        "normal": _config_get_int("sound.speech_normal", 1),
        "sing": _config_get_int("sound.speech_sing", 1),
        "shout": _config_get_int("sound.speech_shout", 2),
        "scream": _config_get_int("sound.speech_scream", 3),
    }


def _way_barriers() -> Dict[str, float]:
    return {
        "open": _config_get_float("sound.way_open", 0.5),
        "closed": _config_get_float("sound.way_closed", 1),
        "locked": _config_get_float("sound.way_locked", 2),
        "blocked": _config_get_float("sound.way_blocked", 2),
        "hidden": _config_get_float("sound.way_hidden", 2),
    }


def _noise_levels() -> Dict[str, int]:
    return {
        "silent": _config_get_int("sound.noise_silent", 0),
        "quiet": _config_get_int("sound.noise_quiet", 0),
        "normal": _config_get_int("sound.noise_normal", 1),
        "loud": _config_get_int("sound.noise_loud", 2),
        "chaotic": _config_get_int("sound.noise_chaotic", 2),
    }


def _config_get_int(key: str, default: int) -> int:
    value = _config.get(key, default)
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _config_get_float(key: str, default: float) -> float:
    value = _config.get(key, default)
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# Backward-compat module names. Old importers (and tests) read these dicts /
# constants directly; they now delegate to the config-backed helpers so values
# stay live after an "Engine Config" save.
SPEECH_LEVELS = _speech_levels()
WAY_BARRIERS = _way_barriers()
NOISE_LEVELS = _noise_levels()
WAY_BARRIER_SEE_THROUGH = _config_get_float("sound.way_see_through", 0.75)


def get_way_barrier(way_node: Node) -> float:
    """Get the sound barrier value for a way (door/connection).

    Per-door override: an optional ``sound_barrier`` float property applies while
    the way is in a solid state (closed/blocked/locked) — one value covers all
    three. Without it, per-state Engine Config defaults apply (task-304 chain).

    Args:
        way_node: The way node to check

    Returns:
        Barrier value: custom property (solid states), else 0.5 (open),
        0.75 (see-through), 1 (closed), 2 (locked/blocked/hidden)
    """
    current_state = way_node.properties.get("current_state", "open")

    # Author-set acoustic mass wins for solid doors, regardless of which of the
    # three solid states it's currently in.
    if current_state in ("closed", "blocked", "locked"):
        custom = way_node.properties.get("sound_barrier")
        try:
            return float(custom)
        except (TypeError, ValueError):
            pass

    # See-through ways (windows, grates) have partial obstruction — cost more
    # than an open doorway but less than a solid closed door
    if way_node.properties.get("see_through", False):
        return _config_get_float("sound.way_see_through", 0.75)

    return _way_barriers().get(current_state, _config_get_float("sound.way_open", 0.5))


def get_area_noise_level(area_node: Node, graph: WorldGraph) -> int:
    """Get the effective noise level for an area.
    
    Combines base environment noise with sound-absorbing items.
    
    Args:
        area_node: The area node
        graph: The graph to search for items
        
    Returns:
        Effective noise level (0-2)
    """
    env = area_node.properties.get("environment", {})
    base_noise_str = env.get("noise", "quiet")
    base_noise = _noise_levels().get(base_noise_str, 0)
    
    # Calculate sound absorption from items in area
    absorption = 0
    for edge in graph.edges:
        if edge.target == area_node.id and edge.type == "in":
            item_node = graph.get_node(edge.source)
            if item_node and item_node.type == "item":
                tags = [t.lower() for t in item_node.properties.get("tags", [])]
                if "sound_absorbing" in tags:
                    absorption += item_node.properties.get("sound_absorption", 1)
    
    # Absorption reduces noise (minimum 0)
    return max(0, base_noise - absorption)


def get_effective_penetration(speech_level: int, ambient_noise: int) -> int:
    """Calculate effective penetration after noise dampening.
    
    Args:
        speech_level: Base penetration value (0-3)
        ambient_noise: Area noise level (0-2)
        
    Returns:
        Effective penetration (reduced by noise)
    """
    return max(0, speech_level - ambient_noise)


def propagate_sound(
    origin_area_id: str,
    penetration: int,
    graph: WorldGraph,
    areas: Dict[str, Node]
) -> Dict[str, Tuple[int, str]]:
    """Propagate sound through the graph from origin area.

    Uses BFS to find all areas that can hear the sound, tracking
    accumulated barriers along each path.

    The graph uses bidirectional ``EDGE_CONNECTION`` edges between
    areas and way (door) nodes:
        area -- connection --> way
        way  -- connection --> area
    Direction info lives on the connection edge, not on the way node.

    Args:
        origin_area_id: ID of the area where sound originates
        penetration: Sound penetration value (speech level or sound_level)
        graph: The world graph
        areas: Dict of area_id -> area_node

    Returns:
        Dict of area_id -> (remaining_penetration, direction_from_origin)
        Only includes areas that can hear the sound (remaining_pen > 0)
    """
    if origin_area_id not in areas:
        return {}

    # BFS: track (area_id, accumulated_barriers, direction)
    queue = deque([(origin_area_id, 0, None)])
    visited = {origin_area_id}
    hearing_areas = {}

    while queue:
        current_id, accumulated, direction = queue.popleft()

        # Find ways connected to the current area
        for edge in graph.get_edges_for_source(current_id, EDGE_CONNECTION):
            way_id = edge.target
            way_node = graph.get_node(way_id)
            if not way_node or way_node.type != "way":
                continue

            # Find the neighbor area on the other side of this way
            neighbor_id = None
            neighbor_direction = None
            for conn in graph.get_edges_for_source(way_id, EDGE_CONNECTION):
                if conn.target == current_id:
                    continue
                neighbor_id = conn.target
                neighbor_direction = edge.properties.get("direction", "")

            if not neighbor_id or neighbor_id in visited:
                continue

            # Calculate barrier for this way
            barrier = get_way_barrier(way_node)
            new_accumulated = accumulated + barrier

            # Sound can reach this area if penetration > accumulated barriers
            remaining_pen = penetration - new_accumulated

            if remaining_pen > 0:
                # Store the direction from origin (first hop direction)
                final_direction = direction if direction else neighbor_direction

                hearing_areas[neighbor_id] = (remaining_pen, final_direction)
                visited.add(neighbor_id)

                # Continue propagating if sound still has penetration
                queue.append((neighbor_id, new_accumulated, final_direction))

    return hearing_areas


def get_areas_hearing_speech(
    origin_area_id: str,
    speech_level: str,
    graph: WorldGraph,
    areas: Dict[str, Node]
) -> Dict[str, Tuple[int, str]]:
    """Get areas that can hear speech at a given level.
    
    Args:
        origin_area_id: ID of the area where speech originates
        speech_level: "whisper", "normal", "shout", or "scream"
        graph: The world graph
        areas: Dict of area_id -> area_node
        
    Returns:
        Dict of area_id -> (remaining_penetration, direction)
    """
    base_pen = _speech_levels().get(speech_level, 1)
    origin_area = areas.get(origin_area_id)
    
    if not origin_area:
        return {}
    
    # Apply ambient noise dampening in origin area
    ambient_noise = get_area_noise_level(origin_area, graph)
    effective_pen = get_effective_penetration(base_pen, ambient_noise)
    
    if effective_pen <= 0:
        # Sound doesn't even leave the origin area
        return {}
    
    return propagate_sound(origin_area_id, effective_pen, graph, areas)


def get_areas_hearing_sound_source(
    origin_area_id: str,
    sound_level: int,
    graph: WorldGraph,
    areas: Dict[str, Node]
) -> Dict[str, Tuple[int, str]]:
    """Get areas that can hear a sound source item.
    
    Args:
        origin_area_id: ID of the area where sound source is located
        sound_level: Sound penetration value (1-3)
        graph: The world graph
        areas: Dict of area_id -> area_node
        
    Returns:
        Dict of area_id -> (remaining_penetration, direction)
    """
    origin_area = areas.get(origin_area_id)
    
    if not origin_area:
        return {}
    
    # Apply ambient noise dampening in origin area
    ambient_noise = get_area_noise_level(origin_area, graph)
    effective_pen = get_effective_penetration(sound_level, ambient_noise)
    
    if effective_pen <= 0:
        return {}
    
    return propagate_sound(origin_area_id, effective_pen, graph, areas)


def get_sound_sources_in_area(area_id: str, graph: WorldGraph) -> List[Tuple[Node, int, str]]:
    """Find all active sound sources in an area.
    
    Args:
        area_id: ID of the area to check
        graph: The world graph
        
    Returns:
        List of (item_node, sound_level, sound_pattern) tuples
    """
    sources = []
    
    for edge in graph.edges:
        if edge.target == area_id and edge.type == "in":
            item_node = graph.get_node(edge.source)
            if not item_node or item_node.type != "item":
                continue
            
            tags = [t.lower() for t in item_node.properties.get("tags", [])]
            if "sound_source" not in tags:
                continue
            
            # Check if item is active (current_state == "lit" or "on")
            current_state = item_node.properties.get("current_state", "")
            if current_state not in ("lit", "on", "active", "ringing", "playing"):
                continue
            
            sound_level = item_node.properties.get("sound_level", 1)
            sound_pattern = item_node.properties.get("sound_pattern", "noise")
            
            sources.append((item_node, sound_level, sound_pattern))
    
    return sources


def format_heard_narration(sound_pattern: str, direction: str, is_speech: bool = False) -> str:
    """Format narration for sound heard from another area.
    
    Args:
        sound_pattern: Description of the sound
        direction: Direction the sound came from
        is_speech: Whether this is speech (vs item sound)
        
    Returns:
        Formatted narration string
    """
    if is_speech:
        if direction:
            return f"You hear someone speaking from the {direction}."
        return "You hear someone speaking nearby."
    else:
        if direction:
            return f"You hear {sound_pattern} from the {direction}."
        return f"You hear {sound_pattern}."
