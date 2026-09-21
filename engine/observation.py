"""Observation memories — what a character has seen (task-403).

One *live* observation memory per subject: the area the character is standing
in, each item it can see there, and each character standing there. The memory
carries who/what/where/when, and the subject's graph id in ``entity_ids``.

Re-seeing a subject refreshes that memory **in place**
(``Player.record_observation``) rather than appending another one, so the store
is bounded by *subjects*, not by visits — a week of wandering does not become
thousands of observations. ``player.memory_index`` then takes "which memory is
about this subject?" out of the memory list, so a subject is never found by
scanning for it. The trace remains the history; the memory holds the current
belief.

Perception is deliberately **not** re-implemented here. The subject list comes
from ``engine.room_perception``, the single source of truth shared by the prompt
(``area_description``) and the panel (``scene_snapshot``); ``get_edges_for_target``
already expands spatial edges, so an item on a bush or under a bench counts. The
only rule added on top is visibility, because a character in a dark room without
darkvision is not observing its contents.

This is the foundation task-425 needs: novelty/Entertainment reads
``observation_tick`` per subject instead of the ``visited_areas`` /
``discovered_items`` sets, and task-423 reuses the character observations.

``observe_area`` reports each subject's **freshness** (task-425's novelty curve)
and it is measured *before* the refresh. That is the whole reason it is reported
from here rather than recomputed by the caller: an entry both refreshes the
observation and earns novelty, and reading the tick afterwards would report
every arrival as stale.
"""

from __future__ import annotations

from engine.novelty import freshness
from engine.room_perception import (
    characters_in_area,
    resolve_area_node,
    visible_area_items,
)

AREA = "area"
ITEM = "item"
CHARACTER = "character"

#: Importance by subject kind. Meeting somebody matters more than seeing a mug.
IMPORTANCE = {AREA: 4, ITEM: 3, CHARACTER: 5}


def can_perceive(player, gs, area_node=None) -> bool:
    """Whether *player* can take in the contents of their area right now.

    Excludes the states where a character plainly is not looking: dead,
    unconscious, or asleep. Light is checked through the engine's lighting
    system when it is reachable, and assumed sufficient when it is not — a
    missing lighting object must not silently blind the whole world.
    """
    if player is None:
        return False
    if getattr(player, "state", "") in ("dead", "unconscious"):
        return False
    if (getattr(player, "activity", None) or {}).get("type") == "sleeping":
        return False

    player_manager = getattr(gs, "player_manager", None)
    lighting = getattr(player_manager, "lighting", None)
    if lighting is None or area_node is None:
        return True
    try:
        if lighting.can_see_in_dark(player_manager, player.name):
            return True
        env = area_node.properties.get("environment", {}) or {}
        return int(lighting.get_ambient_light(area_node.id, env) or 0) > 0
    except Exception:
        return True


def _item_tags(node) -> list:
    """The item's own tags, so an observation of bread is recallable by "food".

    The observation carries the tags of the thing observed, not just the fact
    that it was observed.
    """
    props = getattr(node, "properties", None) or {}
    return [str(t) for t in (props.get("tags", []) or [])]


def perceivable_subjects(player, gs, area_node):
    """Yield ``(subject_id, kind, text, tags)`` for everything perceptible.

    The area itself is yielded by the caller: a character always knows which
    room it is standing in, even in the dark.
    """
    area_name = area_node.name
    for node in visible_area_items(gs.graph, area_node.id, player=player):
        yield (
            node.id, ITEM,
            f"You have seen {node.name} in the {area_name}.",
            _item_tags(node),
        )
    for node in characters_in_area(gs.graph, area_node.id, exclude_name=player.name):
        yield (
            node.id, CHARACTER,
            f"You have met {node.name} in the {area_name}.",
            [],
        )


def observe_area(player, gs, tick=None) -> dict:
    """Record what *player* currently perceives. Returns a small summary.

    ``{"seen": int, "novel": [subject_id, ...], "freshness": {subject_id: float}}``
    — ``novel`` lists the subjects this character had no observation of at all,
    and ``freshness`` is each subject's novelty (task-425) **as it was before the
    refresh**, so a caller can pay for the experience without the refresh having
    already wiped the evidence.
    """
    result = {"seen": 0, "novel": [], "freshness": {}}
    if player is None or gs is None:
        return result
    area_name = getattr(player, "current_area", None)
    if not area_name:
        return result
    area_node = resolve_area_node(gs.graph, area_name)
    if area_node is None:
        return result

    now = gs.time_ticks if tick is None else tick
    area_id = area_node.id

    # The area itself is unconditional: you know which room you are in even
    # with the lights out, and this is the subject novelty/Entertainment uses.
    if not player.has_seen(area_id):
        result["novel"].append(area_id)
    result["freshness"][area_id] = freshness(player, area_id, now)
    player.record_observation(
        area_id, f"You have been in the {area_node.name}.", now,
        kind=AREA, location=area_node.name, importance=IMPORTANCE[AREA],
    )
    result["seen"] += 1

    if not can_perceive(player, gs, area_node):
        return result

    for subject_id, kind, text, tags in perceivable_subjects(player, gs, area_node):
        if not player.has_seen(subject_id):
            result["novel"].append(subject_id)
        result["freshness"][subject_id] = freshness(player, subject_id, now)
        player.record_observation(
            subject_id, text, now, kind=kind, tags=tags,
            location=area_node.name, importance=IMPORTANCE.get(kind, 3),
        )
        result["seen"] += 1
    return result
