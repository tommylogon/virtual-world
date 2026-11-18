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
    "languages",
    "domains",
    "tags",
    "interest_tags",
    "fear_tags",
    "dislike_tags",
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
    if getattr(player, "languages", None):
        from engine.character_appearance import normalize_languages
        props["languages"] = normalize_languages(player.languages)
    if getattr(player, "domains", None):
        from engine.character_appearance import normalize_domains
        props["domains"] = normalize_domains(player.domains)
    if getattr(player, "tags", None) is not None:
        props["tags"] = list(player.tags)
    if getattr(player, "interest_tags", None):
        props["interest_tags"] = list(player.interest_tags)
    if getattr(player, "fear_tags", None):
        props["fear_tags"] = list(player.fear_tags)
    if getattr(player, "dislike_tags", None):
        props["dislike_tags"] = list(player.dislike_tags)
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
    world: Any = None,
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

    if props.get("languages") is not None:
        from engine.character_appearance import normalize_languages
        player.languages = normalize_languages(props["languages"])
    elif pdata.get("languages") is not None:
        from engine.character_appearance import normalize_languages
        player.languages = normalize_languages(pdata["languages"])

    persona_cap = (props.get("persona") or {}).get("capabilities") or {}
    if props.get("domains") is not None:
        from engine.character_appearance import normalize_domains
        player.domains = normalize_domains(props["domains"])
    elif pdata.get("domains") is not None:
        from engine.character_appearance import normalize_domains
        player.domains = normalize_domains(pdata["domains"])
    elif persona_cap.get("domains") is not None:
        from engine.character_appearance import normalize_domains
        player.domains = normalize_domains(persona_cap["domains"])

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

    if props.get("dislike_tags") is not None:
        player.dislike_tags = list(props["dislike_tags"])
    elif pdata.get("dislike_tags") is not None:
        player.dislike_tags = list(pdata["dislike_tags"])

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

    # task-922 / task-849: translate narrative media, biography, and secrets into backstory memories
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
                when = str(item.get("when") or "").strip()
                opinion = str(item.get("opinion") or "").strip()
                when_bit = f" ({when})" if when else ""
                text = f"Knows {medium} '{title}'{when_bit}" + (f": {opinion}" if opinion else "")
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

    # task-849: translate narrative biography and secrets into semantic memories
    bio = narrative.get("biography") or {}
    if isinstance(bio, dict) and hasattr(player, "add_memory") and hasattr(player, "memories"):
        existing_texts = {m.get("text", "") for m in (player.memories or [])}
        for stage, prefix in [("early_life", "Early life"), ("adulthood", "Adulthood"), ("current_situation", "Current situation")]:
            prose = str(bio.get(stage) or "").strip()
            full_text = f"{prefix}: {prose}"
            if prose and full_text not in existing_texts:
                player.add_memory(
                    text=full_text,
                    tick=0,
                    importance=3,
                    memory_type="semantic",
                    tags=["biography", stage],
                    source="backstory",
                    category="semantic",
                    kind="semantic",
                )
                existing_texts.add(full_text)

    # task-968: hydrate tagged semantic school/family/hobby/trade backstory seeds
    knowledge_seeds = narrative.get("knowledge_seeds") or props.get("knowledge_seeds") or []
    if isinstance(knowledge_seeds, list) and knowledge_seeds and hasattr(player, "add_memory") and hasattr(player, "memories"):
        existing_texts = {m.get("text", "") for m in (player.memories or [])}
        for seed in knowledge_seeds:
            if isinstance(seed, dict):
                text = str(seed.get("text") or "").strip()
                raw_tags = list(seed.get("tags") or [])
                if seed.get("source_kind"):
                    raw_tags.append(str(seed["source_kind"]).strip().lower())
                if seed.get("domain"):
                    raw_tags.append(str(seed["domain"]).strip().lower())
                tags = list(dict.fromkeys(["knowledge_seed"] + [str(t).strip().lower() for t in raw_tags if str(t).strip()]))
                importance = int(seed.get("importance") or 5)
            else:
                text = str(seed or "").strip()
                tags = ["knowledge_seed", "life"]
                importance = 5
            if text and text not in existing_texts:
                player.add_memory(
                    text=text,
                    tick=0,
                    importance=importance,
                    memory_type="semantic",
                    tags=tags,
                    source="backstory",
                    category="semantic",
                    kind="semantic",
                )
                existing_texts.add(text)

    secrets = narrative.get("secrets") or {}
    if isinstance(secrets, dict) and hasattr(player, "add_memory") and hasattr(player, "memories"):
        existing_texts = {m.get("text", "") for m in (player.memories or [])}
        deepest = str(secrets.get("deepest_secret") or "").strip()
        full_deepest = f"Deepest secret: {deepest}"
        if deepest and full_deepest not in existing_texts:
            player.add_memory(
                text=full_deepest,
                tick=0,
                importance=5,
                memory_type="semantic",
                tags=["secret", "internal_pressure"],
                source="backstory",
                category="semantic",
            )
            existing_texts.add(full_deepest)
        if world is not None and deepest:
            players_map = getattr(world, "players", None) or {}
            for knower_raw in (secrets.get("known_by") or []):
                knower_name = str(knower_raw).strip()
                if not knower_name:
                    continue
                knower = players_map.get(knower_name)
                if knower is None or knower is player:
                    continue
                if hasattr(knower, "add_memory") and hasattr(knower, "memories"):
                    knower_texts = {m.get("text", "") for m in (knower.memories or [])}
                    shared_text = f"Knows {player.name}'s secret: {deepest}"
                    if shared_text not in knower_texts:
                        knower.add_memory(
                            text=shared_text,
                            tick=0,
                            importance=4,
                            memory_type="semantic",
                            tags=["secret", "shared_secret"],
                            source="backstory",
                            category="semantic",
                        )
        for hf in (secrets.get("hidden_facts") or []):
            hf_str = str(hf).strip()
            full_hf = f"Secret fact: {hf_str}"
            if hf_str and full_hf not in existing_texts:
                player.add_memory(
                    text=full_hf,
                    tick=0,
                    importance=4,
                    memory_type="semantic",
                    tags=["secret"],
                    source="backstory",
                    category="semantic",
                )
                existing_texts.add(full_hf)

    # task-849: translate persona aspirations and arc into player.goals
    personality = persona.get("personality") or props.get("personality") or {}
    aspirations = []
    if isinstance(personality, dict):
        aspirations = personality.get("aspirations") or []
    arc = str(narrative.get("arc") or "").strip()
    if (aspirations or arc) and hasattr(player, "goals"):
        from engine import goals as goals_engine
        existing_whats = {str(g.get("what") or "").strip().lower() for g in (player.goals or []) if isinstance(g, dict)}
        for asp in aspirations:
            asp_str = str(asp).strip()
            if asp_str and asp_str.lower() not in existing_whats:
                new_goals, _ = goals_engine.set_goal(
                    player.goals,
                    what=asp_str,
                    motivation=arc or "aspiration",
                    intention="active",
                )
                player.goals = new_goals
                existing_whats.add(asp_str.lower())


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
