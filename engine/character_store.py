"""Single source of truth for character definition and graph node mapping.

@module character_store
@contributes to_node_properties, apply_node_properties, hydrate_player_from_node, sync_player_to_node
@powers character definition persistence on graph nodes and player model hydration
@relates engine/serialization.py, engine/player_manager.py, player.py
@docs docs/design/character-entity-refactor-plan.md
"""
from typing import Any, Dict, Optional
from graph import Node
from player import Player

AUTHORED_DEFINITION_KEYS = (
    "personality",
    "base_description",
    "description",
    "traits",
    "tags",
    "interest_tags",
    "fear_tags",
    "flags",
    "appearance",
    "triggers",
    "library_id",
)


def to_node_properties(player: Player, existing_props: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Extract authored definition from Player to persist on Node.properties."""
    props = dict(existing_props or {})
    for key in ("personality", "base_description", "description"):
        val = getattr(player, key, None)
        if val:
            props[key] = val
    if getattr(player, "traits", None):
        props["traits"] = dict(player.traits)
    if getattr(player, "tags", None) is not None:
        props["tags"] = list(player.tags)
    if getattr(player, "interest_tags", None):
        props["interest_tags"] = list(player.interest_tags)
    if getattr(player, "fear_tags", None):
        props["fear_tags"] = list(player.fear_tags)
    if getattr(player, "flags", None):
        props["flags"] = dict(player.flags)
    if getattr(player, "appearance", None):
        props["appearance"] = player.appearance
    if getattr(player, "triggers", None):
        props["triggers"] = list(player.triggers)
    return props


def apply_node_properties(
    player: Player,
    props: Optional[Dict[str, Any]],
    pdata: Optional[Dict[str, Any]] = None,
) -> None:
    """Apply authored definition from Node.properties to a Player instance."""
    props = props or {}
    pdata = pdata or {}

    player.personality = props.get("personality") or pdata.get("personality", "") or player.personality
    player.base_description = props.get("base_description") or pdata.get("base_description", "") or player.base_description
    player.description = pdata.get("description", "") or props.get("description", "") or player.description

    if props.get("traits"):
        player.traits = dict(props["traits"])
    elif pdata.get("traits"):
        player.traits = dict(pdata["traits"])

    if props.get("tags") is not None:
        player.tags = list(props["tags"])
        player.sync_vitals_with_tags()
    elif pdata.get("tags") is not None:
        player.tags = list(pdata["tags"])
        player.sync_vitals_with_tags()

    if props.get("interest_tags") is not None:
        player.interest_tags = list(props["interest_tags"])
    elif pdata.get("interest_tags") is not None:
        player.interest_tags = list(pdata["interest_tags"])

    if props.get("fear_tags") is not None:
        player.fear_tags = list(props["fear_tags"])
    elif pdata.get("fear_tags") is not None:
        player.fear_tags = list(pdata["fear_tags"])

    if props.get("flags") is not None:
        player.flags = dict(props["flags"])
    elif pdata.get("flags") is not None:
        player.flags = dict(pdata["flags"])

    if props.get("appearance") is not None:
        player.appearance = props["appearance"]
    elif pdata.get("appearance") is not None:
        player.appearance = pdata["appearance"]

    if props.get("triggers") is not None:
        player.triggers = list(props["triggers"])

    # task-922: translate narrative.media items into backstory semantic memories
    persona = props.get("persona") or {}
    narrative = persona.get("narrative") or props.get("narrative") or {}
    media = narrative.get("media") or []
    if media and hasattr(player, "add_memory") and hasattr(player, "memories"):
        existing_texts = {m.get("text", "") for m in (player.memories or [])}
        for item in media:
            if isinstance(item, dict):
                title = str(item.get("title") or "").strip()
                if not title:
                    continue
                medium = str(item.get("medium") or "work").strip()
                opinion = str(item.get("opinion") or "").strip()
                text = f"Knows {medium} '{title}'" + (f": {opinion}" if opinion else "")
                tags = ["media", medium]
            else:
                title = str(item).strip()
                if not title:
                    continue
                text = f"Knows media '{title}'"
                tags = ["media"]
            if text and text not in existing_texts:
                player.add_memory(
                    text=text,
                    tick=0,
                    importance=4,
                    memory_type="semantic",
                    tags=tags,
                    source="backstory",
                    category="semantic",
                )
                existing_texts.add(text)


def hydrate_player_from_node(node: Node, pdata: Optional[Dict[str, Any]] = None) -> Player:
    """Hydrate a Player model from a character graph node."""
    name = node.name or node.id
    player = Player(name=name)
    props = node.properties or {}
    apply_node_properties(player, props, pdata)
    return player


def sync_player_to_node(player: Player, node: Node) -> None:
    """Sync a Player's authored definition onto its Node.properties."""
    node.properties = to_node_properties(player, node.properties)
