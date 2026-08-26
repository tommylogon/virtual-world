"""Temperature propagation and heat source management.

Propagates heat through open doors/ways each tick, creating emergent
behavior: fireplaces warm adjacent rooms, open doors let cold in,
closing doors traps heat.

Also handles heat_source items: lit items with the heat_source tag
push room temperature toward their target_temperature at their
heating_rate per tick.
"""

from typing import Any, Optional

from graph import EDGE_CONNECTION, EDGE_IN
from engine.runtime_config import config as _config

#: Base heat exchange rate per tick, calibrated for 5-minute ticks.
#: Backward-compat default; runtime_config may override (tunable in Engine Config).
BASE_RATE = 0.05

#: Maximum temperature change per tick per connection to prevent
#: extreme single-tick swings.
MAX_DELTA = 2.0


def _heat_base_rate() -> float:
    value = _config.get("heat.base_rate", BASE_RATE)
    try:
        return float(value)
    except (ValueError, TypeError):
        return BASE_RATE


def _heat_max_delta() -> float:
    value = _config.get("heat.max_delta", MAX_DELTA)
    try:
        return float(value)
    except (ValueError, TypeError):
        return MAX_DELTA


def propagate_temperature(graph) -> None:
    """Spread temperature between areas connected by open ways.

    Skips areas marked ``is_exterior: True`` (infinite reservoirs).
    Only propagates through ways whose ``current_state`` is ``"open"``.
    """
    if not graph:
        return

    # Group connected areas by way node
    # connection edges: way -> area
    way_to_areas: dict[str, set[str]] = {}
    for edge in graph.edges:
        if edge.type == EDGE_CONNECTION:
            src_node = graph.get_node(edge.source)
            if src_node and src_node.type == "way":
                way_to_areas.setdefault(edge.source, set()).add(edge.target)

    processed_pairs: set[tuple[str, str]] = set()

    for way_id, area_ids in way_to_areas.items():
        area_list = list(area_ids)
        if len(area_list) < 2:
            continue

        way_node = graph.get_node(way_id)
        if not way_node:
            continue

        # Only propagate through open ways
        if way_node.properties.get("current_state") != "open":
            continue

        way_insulation = float(way_node.properties.get("insulation", 1.0))
        rate = _heat_base_rate() * way_insulation

        for i in range(len(area_list)):
            for j in range(i + 1, len(area_list)):
                pair = tuple(sorted([area_list[i], area_list[j]]))
                if pair in processed_pairs:
                    continue
                processed_pairs.add(pair)

                _transfer_heat(
                    graph, area_list[i], area_list[j], rate
                )


def _transfer_heat(
    graph, area_id_a: str, area_id_b: str, rate: float
) -> None:
    """Transfer heat between two area nodes."""
    area_a = graph.get_node(area_id_a)
    area_b = graph.get_node(area_id_b)
    if not area_a or not area_b:
        return

    env_a = area_a.properties.setdefault("environment", {})
    env_b = area_b.properties.setdefault("environment", {})

    temp_a = float(env_a.get("temperature", 21))
    temp_b = float(env_b.get("temperature", 21))

    diff = temp_a - temp_b
    if abs(diff) < 0.5:
        return

    area_ins_a = float(area_a.properties.get("insulation", 1.0))
    area_ins_b = float(area_b.properties.get("insulation", 1.0))
    combined_insulation = min(area_ins_a, area_ins_b)

    transfer = diff * rate * combined_insulation
    transfer = max(-_heat_max_delta(), min(_heat_max_delta(), transfer))

    if transfer == 0:
        return

    tags_a = area_a.properties.get("tags", [])
    if not (isinstance(tags_a, list) and "exterior" in tags_a):
        env_a["temperature"] = temp_a - transfer

    tags_b = area_b.properties.get("tags", [])
    if not (isinstance(tags_b, list) and "exterior" in tags_b):
        env_b["temperature"] = temp_b + transfer


def apply_heat_sources(graph) -> None:
    """Scan all areas for lit items with the heat_source tag and apply their heat.

    Each heat_source item pushes the area's temperature toward its
    ``target_temperature`` at its ``heating_rate`` per tick.

    Defaults:
        target_temperature: 30°C
        heating_rate: 0.5°C per tick
    """
    if not graph:
        return

    for node in graph.nodes.values():
        if node.type != "area":
            continue

        area_id = node.id
        env = node.properties.setdefault("environment", {})
        area_temp = float(env.get("temperature", 21))

        for edge in graph.get_edges_for_target(area_id, EDGE_IN):
            item_node = graph.get_node(edge.source)
            if not item_node or item_node.type != "item":
                continue
            if item_node.properties.get("current_state") not in ("lit", "on"):
                continue
            tags = item_node.properties.get("tags", [])
            if "heat_source" not in tags:
                continue

            target_temp = float(item_node.properties.get("target_temperature", 30))
            heating_rate = float(item_node.properties.get("heating_rate", 0.5))

            if area_temp < target_temp:
                area_temp = min(target_temp, area_temp + heating_rate)
            elif area_temp > target_temp:
                area_temp = max(target_temp, area_temp - heating_rate)

        env["temperature"] = area_temp
