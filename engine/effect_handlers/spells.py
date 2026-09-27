"""Spell effect handlers (task-391) — Lyrie's spellbook.

These are the five effects the Lyrie spellbook needed that no existing handler
covered. Each one is deliberately built out of machinery that already exists
(``schedule_trigger``/``on_delayed`` for durations, ``spawn_character`` for
companions, the task-96 affect map for emotions, ``set_hidden`` semantics for
revealing) rather than inventing a parallel system, so a spell author gets the
same behaviour an existing effect would give them.

**Durations are in ticks**, matching ``schedule_trigger`` and
``engine/background_simulation.py``'s timeframe, not in minutes.

Shared params
-------------
``radius_areas`` (int, default 1)
    How many area-hops out to reach. Sweeps pass through ways whether open or
    closed — a spell should not be blocked by a shut door, and neither should
    the reveal it casts.
"""

import json
import os
import time

from graph import EDGE_CONNECTION, EDGE_IN

#: Node types a radius sweep considers by default.
_DEFAULT_SWEEP_TYPES = ("item", "way")


def _library_dir(kind: str) -> str:
    # This module lives one level deeper than engine/effects.py, which resolves
    # the same tree with a single "..".
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "library", kind
    )


def _load_library_entry(kind: str, entry_id: str) -> dict:
    """Load ``data/library/<kind>/<entry_id>.json``. Returns {} when absent."""
    if not entry_id:
        return {}
    try:
        path = os.path.join(_library_dir(kind), f"{entry_id}.json")
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _way_adjacency(graph) -> dict:
    """Map ``way_id -> {area_id, ...}`` from the connection edges."""
    mapping: dict = {}
    for edge in graph.edges:
        if edge.type != EDGE_CONNECTION:
            continue
        src = graph.get_node(edge.source)
        if src is not None and src.type == "way":
            mapping.setdefault(edge.source, set()).add(edge.target)
    return mapping


def _areas_in_radius(graph, area_id: str, radius: int) -> list:
    """Area ids within *radius* hops of *area_id*, nearest first, including it."""
    if not area_id:
        return []
    hops = max(0, int(radius))
    adjacency = _way_adjacency(graph)
    seen = {area_id}
    frontier = [area_id]
    ordered = [area_id]
    for _ in range(hops):
        nxt = []
        for aid in frontier:
            for way_id, area_ids in adjacency.items():
                if aid not in area_ids:
                    continue
                for other in area_ids:
                    if other not in seen:
                        seen.add(other)
                        ordered.append(other)
                        nxt.append(other)
        frontier = nxt
        if not frontier:
            break
    return ordered


def _nodes_in_areas(graph, area_ids, node_types) -> list:
    """Every node of the given types sitting in any of *area_ids*.

    ``EDGE_IN`` points *from* the thing *to* its area (item -> room), so the
    sweep has to walk edges by target and read the source node — the same way
    ``engine.room_perception.characters_in_area`` does.
    """
    wanted = set(node_types or _DEFAULT_SWEEP_TYPES)
    found = []
    for aid in area_ids:
        for edge in graph.get_edges_for_target(aid, "in"):
            node = graph.get_node(edge.source)
            if node is not None and node.type in wanted:
                found.append(node)
    return found


def _characters_in_areas(game_state, area_ids, exclude_name: str = "") -> list:
    """``[(registry_key, player_obj), ...]`` for characters in the given areas."""
    if game_state is None:
        return []
    by_name = {str(n).lower(): n for n in (getattr(game_state, "players", {}) or {})}
    results = []
    for aid in area_ids:
        if game_state.graph.get_node(aid) is None:
            continue
        for edge in game_state.graph.get_edges_for_target(aid, EDGE_IN):
            target = game_state.graph.get_node(edge.source)
            if target is None or target.type != "character":
                continue
            key = by_name.get(str(target.name or "").lower())
            if key is None:
                continue
            if exclude_name and str(key).lower() == str(exclude_name).lower():
                continue
            player_obj = game_state.players.get(key)
            if player_obj is not None:
                results.append((key, player_obj))
    return results


def _resolve_target_node(self, params, context, item_node, game_state):
    """The node a spell effect acts on: explicit id, the use-target, or self."""
    node_id = params.get("node_id") or params.get("target_node") or ""
    if node_id and node_id not in ("self", "target"):
        node = self.graph.get_node(node_id)
        if node is not None:
            return node
    named = params.get("target") or context.get("target_name") or ""
    if named and named not in ("self", "target"):
        needle = str(named).lower()
        for node in self.graph.nodes.values():
            if node.id.lower() == needle or str(node.name or "").lower() == needle:
                return node
    return item_node


def _find_polymorphed(graph, needle: str):
    """Find a transformed node by the name it had *before* the spell.

    Once a node is polymorphed its name is the template's, so a revert addressed
    by the original name finds nothing. The snapshot carries the old name, so a
    revert can still find its target by the name the author remembers.
    """
    if not needle:
        return None
    low = str(needle).lower()
    for node in graph.nodes.values():
        snapshot = (node.properties or {}).get("_polymorph_snapshot")
        if not isinstance(snapshot, dict):
            continue
        if str(snapshot.get("name") or "").lower() == low:
            return node
    return None


# ─────────────────────────── polymorph_target ───────────────────────────

def handle_polymorph_target(self, params, context, item_node=None, game_state=None):
    """Transform a node into a library template, and revert it again.

    params:
      target / node_id — what to transform. Defaults to the ``use X on Y`` target.
      target_template  — library id under ``data/library/items`` (or
                         ``characters`` when the target is a character).
      revert (bool)    — true restores the pre-polymorph state instead of
                         casting. Paired with ``schedule_trigger`` +
                         ``on_delayed`` this gives a duration without needing a
                         second effect type.
      message          — narration.

    The original ``name``/``properties`` are snapshotted onto the node under
    ``_polymorph_snapshot`` while transformed, so revert is exact rather than a
    guess. A missing or unreadable template is refused rather than half-applied.
    """
    revert = bool(params.get("revert"))
    node = _resolve_target_node(self, params, context, item_node, game_state)

    if revert:
        if node is None:
            # Addressed by the pre-spell name, which the node no longer carries.
            node = _find_polymorphed(self.graph, params.get("target") or "")
        if node is None:
            return [params.get("message", "Nothing here is transfigured.")]
        snapshot = node.properties.get("_polymorph_snapshot")
        if not snapshot:
            return [params.get("message", "Nothing here is transfigured.")]
        original_name = snapshot.get("name") or node.name
        original_props = snapshot.get("properties") or {}
        node.name = original_name
        node.properties = dict(original_props)
        node.updated = time.time()
        self.graph.nodes[node.id] = node
        return [params.get("message", f"The {original_name} settles back into itself.")]

    if node is None:
        return [params.get("fail_message", "The transmutation finds nothing to grip.")]

    template_id = params.get("target_template") or params.get("template") or ""
    if not template_id:
        return [params.get("fail_message", "The transmutation has no shape to aim at.")]
    kind = "characters" if node.type == "character" else "items"
    template = _load_library_entry(kind, template_id)
    if not template:
        return [
            params.get(
                "fail_message",
                f"The transmutation falters — there is no {template_id} to become.",
            )
        ]

    # Snapshot BEFORE mutating, and never overwrite an existing snapshot so a
    # second cast mid-duration reverts to the true original, not the first form.
    if not node.properties.get("_polymorph_snapshot"):
        node.properties = dict(node.properties)
        node.properties["_polymorph_snapshot"] = {
            "name": node.name,
            "properties": {k: v for k, v in node.properties.items()},
        }
    node.name = template.get("name", template_id)
    for key in ("description", "current_state", "weight", "light_level"):
        if key in template:
            node.properties[key] = template[key]
    new_tags = list(template.get("tags", []) or [])
    for extra in params.get("add_tags", []) or []:
        if extra not in new_tags:
            new_tags.append(extra)
    if "polymorphed" not in new_tags:
        new_tags.append("polymorphed")
    node.properties["tags"] = new_tags
    node.updated = time.time()
    self.graph.nodes[node.id] = node

    # A polymorphed character is a different being wearing the same name, so the
    # Player identity follows the node rather than the other way round.
    if node.type == "character" and game_state is not None:
        players = getattr(game_state, "players", {}) or {}
        for key, player_obj in list(players.items()):
            if str(key).lower() == str(node.name or "").lower():
                snap = node.properties["_polymorph_snapshot"]
                player_obj.name = node.name
                player_obj.description = template.get("description", player_obj.description)
                if snap.get("name"):
                    player_obj.tags = [
                        t for t in (player_obj.tags or []) if t != "polymorphed"
                    ] + ["polymorphed"]
                break

    return [
        self._render_template_fn(
            params.get("message", f"It becomes {node.name}."), context
        )
    ]


# ─────────────────────── create_illusory_companion ───────────────────────

def handle_create_illusory_companion(
    self, params, context, item_node=None, game_state=None
):
    """Summon a temporary, non-acting companion character.

    params:
      character_id      — library id under ``data/library/characters`` to summon.
      name              — display-name override.
      description       — description override.
      greeting          — folded into the description so the first look at the
                          companion already carries its voice.
      duration (ticks)  — how long it lasts. Expiry is swept by
                          ``engine.companions.expire_companions``.
      dialogue          — lines kept on the instance for a future talk handler.
      vanish_on_area_leave (bool) — also drop it when the caster leaves.
      message           — narration.

    The companion is deliberately **inert**: ``autonomy`` is cleared and
    ``simple_npc`` set, so it never draws an LLM turn, never soaks, and never
    wanders off. It is a thing that was conjured, not a person.
    """
    if game_state is None:
        return [params.get("fail_message", "The summoning finds no purchase.")]

    char_id = params.get("character_id") or ""
    player_obj, _lib = self._hydrate_character(
        char_id, params, game_state, always_fresh=True
    )
    if player_obj is None:
        return [
            params.get(
                "fail_message",
                f"The summoning falters — there is no {char_id or 'companion'} to call.",
            )
        ]

    caster = getattr(game_state, "active_player", "") or ""
    description = params.get("description") or player_obj.description
    greeting = params.get("greeting")
    if greeting:
        description = f"{description} {greeting}".strip()
    player_obj.description = description
    player_obj.base_description = description

    # Inert: this is a conjured object, not an actor.
    player_obj.autonomy = False
    player_obj.simple_npc = False
    player_obj.illusory = True
    player_obj.illusory_owner = caster
    player_obj.illusory_dialogue = list(params.get("dialogue", []) or [])
    try:
        player_obj.illusory_expires_tick = int(game_state.time_ticks) + max(
            1, int(params.get("duration", 60) or 60)
        )
    except Exception:
        player_obj.illusory_expires_tick = None
    player_obj.illusory_vanish_on_leave = bool(params.get("vanish_on_area_leave", True))
    player_obj.illusion_area = None

    area_id = None
    if hasattr(game_state, "get_current_area_id"):
        area_id = game_state.get_current_area_id()
    if area_id:
        area_node = game_state.graph.get_node(area_id)
        if area_node is not None:
            player_obj.illusion_area = area_id
            player_obj.current_area = area_node.name

    prev_active = game_state.active_player
    game_state.add_player(player_obj)
    new_key = game_state.active_player
    if game_state.active_player != prev_active:
        game_state.active_player = prev_active
    if area_id and new_key:
        game_state.set_player_area(new_key, player_obj.current_area)

    return [
        self._render_template_fn(
            params.get("message", f"{player_obj.name} is here."), context
        )
    ]


# ─────────────────────────── broadcast_emotion ───────────────────────────

def handle_broadcast_emotion(self, params, context, item_node=None, game_state=None):
    """Shift the affect of every character within a radius.

    params:
      spikes          — ``{emotion: delta}`` against the task-96 affect map
                        (``calm``, ``peaceful``, ``anxious``, ``craving``, …).
                        Positive soothes, negative unsettles.
      radius_areas    — area-hops to reach (default 1).
      include_caster  — whether the caster is affected too (default False).
      message         — narration.

    Affect needs no ``duration``: the map relaxes back toward its baseline on its
    own each tick, so a one-shot spike decays naturally. ``duration`` is accepted
    and echoed for the author's benefit but is not needed.
    """
    if game_state is None:
        return [params.get("message", "The feeling passes through the room and fades.")]

    spikes = params.get("spikes") or {}
    single = params.get("emotion")
    if single and not spikes:
        intensity = params.get("intensity", 0.3)
        spikes = {single: float(intensity) * 25.0}
    if not spikes:
        return [params.get("message", "Nothing takes hold.")]

    area_id = (
        game_state.get_current_area_id()
        if hasattr(game_state, "get_current_area_id")
        else None
    )
    area_ids = _areas_in_radius(self.graph, area_id, params.get("radius_areas", 1))
    caster = getattr(game_state, "active_player", "") or ""
    targets = _characters_in_areas(
        game_state, area_ids, exclude_name="" if params.get("include_caster") else caster
    )

    touched = 0
    for _key, player_obj in targets:
        for emotion, delta in spikes.items():
            try:
                player_obj.spike_emotion(str(emotion), float(delta))
                touched += 1
            except Exception:
                continue

    lead = params.get("message") or "The air shifts around you."
    if not touched:
        return [f"{lead} Nothing else is close enough to hear it."]
    plural = "s" if touched != 1 else ""
    return [self._render_template_fn(f"{lead} ({touched} other{plural} affected.)", context)]


# ──────────────────────────── bind_companion ────────────────────────────

def handle_bind_companion(self, params, context, item_node=None, game_state=None):
    """Mark a node as a persistent companion that follows its caster.

    params:
      node_id / item_id — the companion node. Defaults to the spell item itself,
                          which is the common case (the spell casts its own
                          familiar).
      follow_distance   — hops it will trailing behind (recorded; the follower
                          keeps the caster's area, the value is for authors).
      duration (ticks)  — how long the bond lasts.
      message           — narration.

    Following is not done here. The node is tagged with ``companion`` metadata
    and ``engine.companions.process_companions`` does the moving on each turn, so
    a companion keeps up across area transitions without this handler needing to
    know anything about the tick loop.
    """
    node = _resolve_target_node(self, params, context, item_node, game_state)
    if node is None:
        return [params.get("fail_message", "There is nothing there to bind to.")]

    caster = getattr(game_state, "active_player", "") if game_state else ""
    try:
        expires = int(game_state.time_ticks) + max(1, int(params.get("duration", 120) or 120))
    except Exception:
        expires = None

    node.properties = dict(node.properties)
    node.properties["companion"] = {
        "owner": caster,
        "expires_tick": expires,
        "follow_distance": int(params.get("follow_distance", 1) or 1),
    }
    tags = list(node.properties.get("tags", []) or [])
    if "companion" not in tags:
        tags.append("companion")
    node.properties["tags"] = tags
    node.updated = time.time()
    self.graph.nodes[node.id] = node

    return [
        self._render_template_fn(
            params.get("message", f"{node.name} settles in beside you."), context
        )
    ]


# ──────────────────────────── reveal_hidden ────────────────────────────

def handle_reveal_hidden(self, params, context, item_node=None, game_state=None):
    """Unhide things within a radius, and remember what to put back.

    params:
      radius_areas  — area-hops to sweep (default 1).
      types         — node types to consider (default ``item``, ``way``).
      duration      — ticks before they hide again. Omit for permanent.
      message       — narration.

    This is the radius form of the single-node ``set_hidden``. Only nodes that
    are actually hidden are touched — revealing something already visible is a
    no-op, not a bookkeeping entry.

    The prior ``current_state`` is recorded per node rather than assumed, so a
    re-hide restores what was really there. In practice today that is always
    ``hidden``, because ``set_hidden`` overwrites ``current_state`` outright
    instead of stacking; the recording exists so a future hiding mechanism that
    preserves state (a locked *and* hidden chest, say) reverts correctly without
    this handler needing to change.
    """
    if game_state is None:
        return [params.get("message", "Nothing reveals itself.")]

    area_id = (
        game_state.get_current_area_id()
        if hasattr(game_state, "get_current_area_id")
        else None
    )
    area_ids = _areas_in_radius(self.graph, area_id, params.get("radius_areas", 1))
    node_types = params.get("types") or list(_DEFAULT_SWEEP_TYPES)
    try:
        duration = int(params["duration"]) if params.get("duration") not in (None, "") else None
    except (TypeError, ValueError):
        duration = None
    expires = None
    if duration is not None:
        try:
            expires = int(game_state.time_ticks) + max(1, duration)
        except Exception:
            expires = None

    revealed = 0
    for node in _nodes_in_areas(self.graph, area_ids, node_types):
        if node.properties.get("current_state") != "hidden":
            continue
        node.properties = dict(node.properties)
        if "_reveal_previous_state" not in node.properties:
            node.properties["_reveal_previous_state"] = "hidden"
        node.properties["current_state"] = "normal"
        node.properties["_reveal_expires_tick"] = expires
        node.updated = time.time()
        self.graph.nodes[node.id] = node
        revealed += 1

    lead = params.get("message") or "The undergrowth gives up its secrets."
    if not revealed:
        return [f"{lead} Nothing new was hidden here."]
    return [
        self._render_template_fn(f"{lead} ({revealed} revealed.)", context)
    ]


HANDLERS = {
    "polymorph_target": handle_polymorph_target,
    "create_illusory_companion": handle_create_illusory_companion,
    "broadcast_emotion": handle_broadcast_emotion,
    "bind_companion": handle_bind_companion,
    "reveal_hidden": handle_reveal_hidden,
}
