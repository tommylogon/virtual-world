"""tools/autoswarm/lore.py - Item, key, lock, and character authoring for ViWo AutoSwarm.

Constructs items and character definitions adhering to:
1. Physical containment edges ("in" edges).
2. Key and lock matching (item.properties.key_id == way.properties.requires_key).
3. Authored character definition placed on character node properties.
4. Zero em-dashes across all descriptions.
"""
from __future__ import annotations

import json
from typing import Dict, Any, List, Optional, Tuple


def make_item_node(
    item_id: str,
    name: str,
    description: str,
    location_id: str,
    weight: float = 0.5,
    key_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    properties_extra: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Create an item node and its 'in' containment edge."""
    clean_desc = description.replace("\u2014", " - ")
    clean_name = name.replace("\u2014", " - ")

    props: Dict[str, Any] = {
        "description": clean_desc,
        "weight": weight,
        "tags": tags or ["prop"],
    }
    if key_id:
        props["key_id"] = key_id
        props["tags"].append("key")
    if properties_extra:
        props.update(properties_extra)

    node = {
        "id": item_id,
        "type": "item",
        "name": clean_name,
        "properties": props,
    }
    edge = {
        "source": item_id,
        "target": location_id,
        "type": "location",
        "properties": {},
    }
    return node, edge


def make_character_definition(
    char_id: str,
    name: str,
    base_description: str,
    persona_prompt: str,
    location_id: str,
    inventory: Optional[List[str]] = None,
    traits: Optional[Any] = None,
    tags: Optional[List[str]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Create character node, location edge, and player runtime model."""
    clean_desc = base_description.replace("\u2014", " - ")
    clean_persona = persona_prompt.replace("\u2014", " - ")
    clean_name = name.replace("\u2014", " - ")

    if isinstance(traits, dict):
        traits_dict = traits
    elif isinstance(traits, list):
        traits_dict = {t: 1 for t in traits}
    else:
        traits_dict = {"analytical": 1, "curious": 1}

    # Persistent definition on character node properties
    props: Dict[str, Any] = {
        "base_description": clean_desc,
        "description": clean_desc,
        "persona_prompt": clean_persona,
        "traits": traits_dict,
        "tags": tags or ["student", "investigator"],
    }

    char_node = {
        "id": char_id,
        "type": "character",
        "name": clean_name,
        "properties": props,
    }

    location_edge = {
        "source": char_id,
        "target": location_id,
        "type": "location",
        "properties": {},
    }

    # Player runtime block
    player_model = {
        "id": char_id,
        "name": clean_name,
        "current_area": location_id,
        "inventory": inventory or [],
        "traits": traits_dict,
        "tags": tags or ["student", "investigator"],
        "vitals": {
            "health": 100,
            "stamina": 100,
            "energy": 90,
            "hunger": 20,
            "thirst": 20,
        },
        "emotion": {
            "primary": "focused",
            "intensity": 0.6,
        },
        "memories": [],
    }

    return char_node, location_edge, player_model
