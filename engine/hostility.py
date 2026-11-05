"""Faction-scoped hostility and group-aware fear (task-742).

Hostility is a relation between groups, not a per-character boolean trait.
A creature declares the groups it hunts (via ``hunts:<group>`` tags or traits
like ``slasher`` and ``hostile``).

Key simulation invariants:
1. Same-faction creatures ignore each other: two ``faction:lich_a`` zombies do
   not target each other, while ``lich_a`` and ``lich_b`` undead fight.
2. Fear is group-aware and independent of hostility: a character does not fear
   a source in its own group (undead do not fear undead), separate from the
   hostility exemption.
3. The ``hostile`` trait is wired to the relation: creatures marked with
   ``hostile`` consider targets outside their faction as hostile prey.

@module engine/hostility
@contributes is_hostile_to: group/faction-scoped hostility relation
@contributes hunted_groups: extract targeted groups for a character
@docs docs/virtualWorld/Characters/NPC Behavior System.md
"""

from __future__ import annotations

from typing import Any, Iterable, Optional, Set

from engine.ownership import FACTION_PREFIX, factions_of

HUNTS_PREFIX = "hunts:"
HOSTILE_TO_PREFIX = "hostile_to:"

WILDCARD_HUNTS = {"*", "all", "all_except_faction", "others"}


def _normalise(tags: Iterable[Any]) -> Set[str]:
    return {str(t).lower().strip() for t in (tags or ()) if str(t).strip()}


def _character_tags(gs: Any, character: Any) -> Set[str]:
    """Return all behavioral tags and traits of a character."""
    tags = _normalise(getattr(character, "tags", None))
    tags |= _normalise((getattr(character, "traits", None) or {}).keys())

    # Include factions as bare tags and prefixed tags
    for f in factions_of(character):
        tags.add(f)
        tags.add(f"{FACTION_PREFIX}{f}")

    graph = getattr(gs, "graph", None)
    if graph is not None:
        try:
            player_id_fn = getattr(gs, "_player_node_id", None) or getattr(gs, "player_node_id", None)
            if player_id_fn:
                node = graph.get_node(player_id_fn(getattr(character, "name", "")))
                if node is not None:
                    node_props = getattr(node, "properties", {}) or {}
                    tags |= _normalise(node_props.get("tags"))
        except Exception:
            pass

    return tags


def hunted_groups(character: Any) -> Set[str]:
    """Extract groups this character actively hunts."""
    raw_tags = getattr(character, "tags", None) or ()
    groups: Set[str] = set()
    for tag in raw_tags:
        text = str(tag).strip().lower()
        if text.startswith(HUNTS_PREFIX) and len(text) > len(HUNTS_PREFIX):
            groups.add(text[len(HUNTS_PREFIX):].strip())
        elif text.startswith(HOSTILE_TO_PREFIX) and len(text) > len(HOSTILE_TO_PREFIX):
            groups.add(text[len(HOSTILE_TO_PREFIX):].strip())
    return groups


def is_hostile_to(hunter: Any, target: Any, gs: Any = None) -> bool:
    """Determine whether *hunter* considers *target* hostile / valid prey.

    Rules:
    - Never hostile to self or dead targets.
    - Same-faction creatures ignore each other (two faction:lich_a creatures do not fight).
    - If hunter specifies hunts:<group> tags, matches if target belongs to any of those groups.
    - If hunter has is_slasher or hostile trait, hunts everyone outside its own faction.
    - Slasher regression: two unaligned slashers (no faction) do not hunt each other.
    """
    if hunter is None or target is None or hunter is target:
        return False

    if getattr(target, "state", None) == "dead":
        return False

    hunter_factions = factions_of(hunter)
    target_factions = factions_of(target)

    # Same-faction creatures ignore each other
    if hunter_factions and target_factions and bool(hunter_factions & target_factions):
        return False

    hunted = hunted_groups(hunter)
    if hunted:
        if bool(hunted & WILDCARD_HUNTS):
            return True
        target_tags = _character_tags(gs, target)
        if bool(hunted & target_tags):
            return True
        return False

    # Check slasher / hostile traits
    try:
        from engine.traits import TraitSystem
        has_slasher = TraitSystem.has_effect(hunter, "is_slasher")
        has_hostile = TraitSystem.has_effect(hunter, "hostile")
    except Exception:
        has_slasher = False
        has_hostile = False

    if has_slasher or has_hostile:
        # Mansion regression: unaligned slashers do not hunt each other
        if has_slasher and not hunter_factions and not target_factions:
            try:
                from engine.traits import TraitSystem
                if TraitSystem.has_effect(target, "is_slasher"):
                    return False
            except Exception:
                pass
        return True

    return False
