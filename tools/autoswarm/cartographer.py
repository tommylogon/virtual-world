"""tools/autoswarm/cartographer.py - Spatial and graph authoring for ViWo AutoSwarm.

Constructs areas, ways, and spatial topologies strictly adhering to:
1. Unique display names and node IDs.
2. Complete environment blocks (light, temperature, air, smell, noise).
3. Complete way definitions with pass_message, area_from, area_to.
4. Multi-storey vertical integrity (mode: interior for separate floors, no compass drift).
5. Zero em-dashes in any description.
"""
from __future__ import annotations

import json
from typing import Dict, Any, List, Optional, Tuple


def make_environment(
    light: int = 80,
    temperature: float = 20.0,
    air: str = "faint metallic and chemical aroma",
    smell: str = "antiseptic floor cleaner",
    noise: str = "low mechanical hum of ventilation",
    wind: str = "none",
    humidity: str = "dry",
) -> Dict[str, Any]:
    """Return a complete environment definition block with numeric temperature."""
    return {
        "light": light,
        "temperature": float(temperature),
        "air": air.replace("\u2014", " - "),
        "smell": smell.replace("\u2014", " - "),
        "noise": noise.replace("\u2014", " - "),
        "wind": wind,
        "humidity": humidity,
    }


def make_area_node(
    area_id: str,
    name: str,
    description: str,
    cell: Tuple[int, int] = (0, 0),
    scope_id: Optional[str] = None,
    environment: Optional[Dict[str, str]] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Create a fully compliant area graph node."""
    if environment is None:
        environment = make_environment()

    clean_desc = description.replace("\u2014", " - ")
    clean_name = name.replace("\u2014", " - ")

    props: Dict[str, Any] = {
        "description": clean_desc,
        "environment": environment,
        "cell": list(cell),
        "tags": tags or ["interior", "building"],
    }
    if scope_id:
        props["world_scope_id"] = scope_id

    return {
        "id": area_id,
        "type": "area",
        "name": clean_name,
        "properties": props,
    }


def make_way_node(
    way_id: str,
    name: str,
    area_from: str,
    area_to: str,
    pass_message: str,
    door: bool = True,
    locked: bool = False,
    key_id: Optional[str] = None,
    lock_description: Optional[str] = None,
    direction: str = "east",
    reverse_direction: str = "west",
    tags: Optional[List[str]] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Create a way node and its connection edges with compass directions."""
    clean_name = name.replace("\u2014", " - ")
    clean_pass = pass_message.replace("\u2014", " - ")

    props: Dict[str, Any] = {
        "area_from": area_from,
        "area_to": area_to,
        "pass_message": clean_pass,
        "door": door,
        "locked": locked,
        "tags": tags or ["door", "interior_portal"],
    }
    if locked and key_id:
        props["requires_key"] = key_id
        props["key_id"] = key_id
    if lock_description:
        props["lock_description"] = lock_description.replace("\u2014", " - ")

    node = {
        "id": way_id,
        "type": "way",
        "name": clean_name,
        "properties": props,
    }

    edges = [
        {"source": area_from, "target": way_id, "type": "connection", "properties": {"direction": direction}},
        {"source": way_id, "target": area_to, "type": "connection", "properties": {"direction": direction}},
        {"source": area_to, "target": way_id, "type": "connection", "properties": {"direction": reverse_direction}},
        {"source": way_id, "target": area_from, "type": "connection", "properties": {"direction": reverse_direction}},
    ]
    return node, edges
