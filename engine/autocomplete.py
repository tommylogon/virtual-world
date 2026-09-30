# engine/autocomplete.py — UI input helpers extracted from VirtualWorld facade.
#
# These helpers take a VirtualWorld-like object (anything exposing
# `.graph`, `.player_manager`, and `_get_area_id_for_player`) so the
# facade stays thin. They have no knowledge of VirtualWorld internals.

from typing import Optional, List

from graph import EDGE_IN, EDGE_KNOWN


def get_autocomplete_options(vw, verb: str, prefix: str = "", character_name: str = None) -> list:
    """Get candidate target names for a given verb and prefix."""
    player_name = character_name or vw.player_manager.active_player
    if not player_name or player_name not in vw.player_manager.players:
        return []

    verb = (verb or "").strip().lower()
    raw_prefix = (prefix or "").strip().lower()
    prefix = raw_prefix
    if not prefix and verb:
        # A bare trailing marker ("belne on") is stripped above, which hides the
        # region branch. Re-attach it so the region list still opens.
        for marker in (" on ", " where ", " in the ", " in "):
            if verb.endswith(marker.strip()):
                prefix = marker.strip() + " "
                break

    current_area_id = vw._get_area_id_for_player(player_name)

    room_items = []
    if current_area_id:
        in_edges = vw.graph.get_edges_for_target(current_area_id, 'in')
        for e in in_edges:
            n = vw.graph.get_node(e.source)
            if n and n.type == 'item':
                room_items.append(n)

    player_id = vw.player_manager.get_player_node_id(player_name)
    carried_edges = (
        vw.graph.get_edges_for_target(player_id, 'carrying') +
        vw.graph.get_edges_for_target(player_id, 'equipped')
    )
    carried_items = [
        vw.graph.get_node(e.source) for e in carried_edges
        if vw.graph.get_node(e.source)
    ]

    known_edges = vw.graph.get_edges_for_target(player_id, EDGE_KNOWN)
    known_items = [
        vw.graph.get_node(e.source) for e in known_edges
        if vw.graph.get_node(e.source)
    ]

    room_ways = []
    way_directions = []
    if current_area_id:
        edges = vw.graph.get_edges_for_source(current_area_id) + vw.graph.get_edges_for_target(current_area_id)
        for e in edges:
            if e.type in ('way', 'connection'):
                other_id = e.target if e.source.lower() == current_area_id else e.source
                other_node = vw.graph.get_node(other_id)
                if other_node and other_node.type in ('way', 'door'):
                    room_ways.append(other_node)
                dir_name = e.properties.get('direction')
                if dir_name:
                    way_directions.append(dir_name)

    area_chars = [
        getattr(p, "name", pname) for pname, p in vw.player_manager.players.items()
        if pname != player_name
        and getattr(p, "name", pname) != player_name
        and vw._get_area_id_for_player(pname) == current_area_id
    ]

    candidates = []

    # task-630: a body-region phrase ("attack belne on the hea") never matched a
    # candidate, because the target list holds names, not regions. Offer the
    # region vocabulary once a region marker is typed. Without this the region
    # fix in resolve_region is undiscoverable -- the UI never shows that
    # "head" is a legal thing to aim at.
    region_marker = None
    region_start = -1
    for marker in (" on ", " where ", " in the ", " in "):
        idx = raw_prefix.rfind(marker) if raw_prefix else -1
        if idx > region_start:
            region_start = idx
            region_marker = marker
    if region_marker is None and raw_prefix:
        # Prefix ends on the marker itself ("belne on") -- rfind of " on " misses
        # it because there is no trailing space.
        for marker in (" on", " where", " in the", " in"):
            if raw_prefix.endswith(marker) and len(raw_prefix) > len(marker):
                region_start = len(raw_prefix) - len(marker)
                region_marker = marker + " "
                break
    if region_marker is not None and region_start >= 0:
        from engine.body_parts import BODY_REGIONS
        region_prefix = prefix[region_start + len(region_marker):].strip()
        head = prefix[:region_start].strip()
        # Mirror resolve_region: an article belongs to the phrase, not the
        # region id, so match on the bare id but emit the phrase the user typed.
        article = ""
        for art in ("the ", "a ", "an "):
            if region_prefix.startswith(art):
                article = art
                region_prefix = region_prefix[len(art):].strip()
                break
        seen = set()
        out = []
        for region_id in BODY_REGIONS:
            if region_prefix and not region_id.startswith(region_prefix):
                continue
            if region_id in seen:
                continue
            seen.add(region_id)
            out.append(f"{head}{region_marker}{article}{region_id}")
        return out

    def _add(name):
        if name and isinstance(name, str) and name not in candidates:
            candidates.append(name)

    def _get_actions(node):
        acts = node.properties.get('actions', [])
        if isinstance(acts, str):
            acts = [a.strip().lower() for a in acts.split(',')]
        elif isinstance(acts, list):
            acts = [str(a).strip().lower() for a in acts]
        return acts

    def _get_tags(node):
        tags = node.properties.get('tags', [])
        if isinstance(tags, str):
            tags = [t.strip().lower() for t in tags.split(',')]
        elif isinstance(tags, list):
            tags = [str(t).strip().lower() for t in tags]
        return tags

    if verb in ('take', 'get', 'grab'):
        for item in room_items:
            acts = _get_actions(item)
            takeable = item.properties.get('takeable', True)
            if 'take' in acts or verb in acts or takeable:
                _add(item.properties.get('name') or item.id)

    elif verb in ('examine', 'search', 'inspect', 'check', 'x', 'read'):
        for item in room_items + carried_items + known_items + room_ways:
            _add(item.properties.get('name') or item.id)
        for cname in area_chars:
            _add(cname)

    elif verb in ('use',):
        for item in carried_items + room_items + known_items:
            acts = _get_actions(item)
            if 'use' in acts or verb in acts or item in carried_items or item in known_items:
                _add(item.properties.get('name') or item.id)

    elif verb in ('open', 'close', 'unlock', 'lock'):
        for way in room_ways:
            _add(way.properties.get('name') or way.id)
        for d in way_directions:
            _add(d)

    elif verb in ('drop', 'stow', 'put'):
        for item in carried_items:
            _add(item.properties.get('name') or item.id)

    elif verb in ('combine',):
        for item in carried_items:
            _add(item.properties.get('name') or item.id)

    elif verb in ('split',):
        for item in carried_items:
            props = item.properties or {}
            attempts = 0
            try:
                attempts = int(props.get('uses', -1) or 0)
            except (TypeError, ValueError):
                attempts = 0
            if attempts >= 2:
                _add(item.properties.get('name') or item.id)

    elif verb in ('craft', 'make'):
        for recipe in vw._recipe_known_names(player_name):
            _add(recipe)

    elif verb in ('eat', 'drink'):
        for item in carried_items + room_items + known_items:
            acts = _get_actions(item)
            tags = _get_tags(item)
            if verb in acts or any(t in ('food', 'drink', 'consumable', 'edible') for t in tags):
                _add(item.properties.get('name') or item.id)

    elif verb in ('toggle',):
        for item in room_items + carried_items + known_items:
            acts = _get_actions(item)
            tags = _get_tags(item)
            if 'toggleable' in tags or 'toggle' in acts:
                _add(item.properties.get('name') or item.id)

    elif verb in ('attack', 'kill', 'speak', 'say', 'talk', 'whisper', 'shout'):
        for cname in area_chars:
            _add(cname)

    elif verb in ('name', 'label'):
        for cname in area_chars:
            _add(cname)
        for item in room_items + carried_items:
            _add(item.properties.get('name') or item.id)

    elif verb in ('go', 'walk', 'move', 'enter'):
        for way in room_ways:
            _add(way.properties.get('name') or way.id)
        for d in way_directions:
            _add(d)

    elif verb in ('find', 'forage'):
        # `find <skill>` (task-471/483): suggest the search skills by name so the
        # affordance is discoverable, not something a player has to guess.
        from engine import foraging
        for key in sorted(foraging.SKILL_TABLES):
            _add(foraging.SKILL_DISPLAY.get(key, key.title()))

    else:
        for item in room_items + carried_items + known_items:
            _add(item.properties.get('name') or item.id)

    if prefix:
        candidates = [c for c in candidates if c.lower().startswith(prefix.lower())]

    return candidates