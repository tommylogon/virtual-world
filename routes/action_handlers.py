"""action_handlers module.

@module action_handlers
@contributes _roster, _reachable_items, _activity_cmd_allowed, _activity_gate, _action_block_gate, _parse_activity_args
@docs none - HTTP API route handler
"""

import logging
import re
import json
from flask import request, jsonify, Response
from virtual_world_engine import AmbiguousItemError
from graph import EDGE_IN, Edge
from engine.foraging import is_loot_skill
from engine.activities import (
    ACTIVITY_BLOCKING, ACTIVITY_INTERRUPTIBLE, activity_description,
)
from engine.vitals import format_vitals_readout, VITAL_POLARITY
from routes.helpers import tokenize_command_detailed
from engine.actions import mature_actions as _registry_mature_verbs
_INTIMACY_VERBS = tuple(_registry_mature_verbs())
from engine.pleasure_actions import (
    INTENSITY_ADVERBS as _INTENSITY_ADVERBS,
)

logger = logging.getLogger(__name__)

_ACTIVITY_ALLOWED = {
    "sleeping": {"look", "stats", "status", "inventory", "inv", "i",
                 "examine", "read", "inspect", "check", "wake"},
    "bathing": {"look", "stats", "status", "inventory", "inv", "i",
                "examine", "read", "inspect", "check",
                "speak", "say", "whisper", "shout", "scream", "sing", "do",
                "stop", "stand"},
}

_ACTION_BLOCK_ALLOWED = {
    "look", "stats", "status", "inventory", "inv", "i",
    "examine", "wait",
    "speak", "say", "whisper", "shout", "scream", "sing", "do",
    "escape", "struggle",
}

_ACTIVITY_NON_INTERRUPTING = {
    "look", "stats", "status", "inventory", "inv", "i",
    "examine", "read", "inspect", "check", "wake",
    "speak", "say", "whisper", "shout", "scream", "sing", "do",
    "fumble", "fumble around", "grope", "grope around", "feel around",
    "rest", "sleep", "wait", "meditate", "bathe", "bath", "sit", "sit down",
    "stand", "stand up", "get up", "stop", "dress", "get dressed", "strip", "undress",
    "lie", "lie down", "lay down",
}


def _roster(world):
    """The live character roster, or an empty mapping.

    `PlayerManager.players` is the registry, and `engine/relief.witnesses` reads
    it rather than re-deriving occupancy, so a foreground relieve and a
    background one count the same onlookers.
    """
    manager = getattr(world, "player_manager", None)
    return getattr(manager, "players", None) or {}


def _reachable_items(world, container_id):
    """Item nodes `container_id` holds, by any spatial relation.

    Delegates to the one shared definition of reachability so this handler and
    `BackgroundSimulation` cannot disagree about whether a fixture is "in" the
    room (task-551).
    """
    from engine.world_scopes import spatial_item_nodes
    return spatial_item_nodes(getattr(world, "graph", None), container_id)


def _activity_cmd_allowed(cmd, allowed):
    if cmd in allowed:
        return True
    return any(cmd.startswith(v + " ") for v in (
        "speak", "say", "whisper", "shout", "scream", "sing", "do",
        "examine", "read", "inspect", "check", "wake",
    ))


def _activity_gate(cmd, world, add_output):
    player = getattr(world, "player", None)
    activity = getattr(player, "activity", None)
    if not activity:
        return None
    act_type = activity.get("type")
    if act_type in ACTIVITY_BLOCKING:
        allowed = _ACTIVITY_ALLOWED.get(act_type, set())
        if not _activity_cmd_allowed(cmd, allowed):
            return f"You're {activity_description(activity)}  -  you can't do that right now."
        return None
    if act_type in ACTIVITY_INTERRUPTIBLE:
        if not _activity_cmd_allowed(cmd, _ACTIVITY_NON_INTERRUPTING):
            stopped = world.activities.interrupt_activity(world.active_player)
            if stopped:
                add_output(stopped)
    return None


def _action_block_gate(cmd, world, add_output):
    if world.conditions.can_act(world.active_player):
        return None
    first = cmd.split(" ", 1)[0]
    if first in _ACTION_BLOCK_ALLOWED:
        return None
    return "You can't move or act right now  -  a condition holds you motionless."


def _parse_activity_args(tokens, cmd):
    minutes = None
    target = None
    on_idx = None
    for i in range(1, len(tokens)):
        if tokens[i] == "on":
            on_idx = i
            break
    if on_idx is not None:
        target = ' '.join(tokens[on_idx + 1:]) if on_idx + 1 < len(tokens) else None
        if on_idx > 1 and tokens[1].isdigit():
            minutes = int(tokens[1])
    elif len(tokens) >= 2 and tokens[1].isdigit():
        minutes = int(tokens[1])
    return minutes, target


# task-629: verbs that cannot do anything without a target. The dispatch chain
# tests `cmd.startswith("go ")`, so a bare `go` matched nothing and fell through
# to the emote catch-all, which answered "player_human_explorer go." -- the
# command echoed back with the actor's name glued to it. The intimacy branch
# already answered "Attack whom?"; this gives the rest of the verbs the same
# courtesy. A single word that is NOT one of these is still treated as an emote
# ("smile", "shrug" are legitimate).
_VERBS_NEEDING_TARGET = frozenset({
    "go", "climb", "crawl", "enter", "exit", "swim", "dive",
    "examine", "look", "search", "read",
    "take", "get", "grab", "pick", "drop", "throw", "toss", "release", "stow",
    "put", "place", "give", "steal", "lead", "hand",
    "attack", "disarm", "kill", "hit", "shoot",
    "eat", "drink", "taste", "smell",
    "open", "close", "use", "toggle", "activate", "wear",
    "teach", "name", "wake", "sing", "talk", "speak",
    "combine", "split", "craft", "make", "relieve",
    "mount", "dismount", "ride", "saddle", "hug", "kiss", "caress",
})


def _build_narration_context_for_current_area(world):
    context = world.get_narration_context_for_area()
    if not context:
        return None
    return {
        "type": "area",
        "areaName": context["area_name"],
        "characters": [c["name"] for c in context["characters"]],
        "items": [i["name"] for i in context["items"]],
        "environment": context["environment"],
        "description": context["description"],
        "time": context["time"],
        "recent_events": context["recent_events"]
    }


def handle_get_state(app):
    try:
        # task-XXX: ?lite=1 returns a trimmed payload (graph + essential player
        # state only, no area projections/legacy collections) so the browser can
        # paint the world before the full state arrives. The initial render is
        # built from the lite payload, then a full fetch fills in the rest.
        lite = request.args.get("lite", "").strip().lower() in ("1", "true", "yes")
        full = request.args.get("full", "").strip().lower() in ("1", "true", "yes")
        # task-753: serve the cached payload when the world has not changed since
        # the last build. The revision is bumped on every mutating /api/ call.
        # Disabled under TESTING so a test that mutates the world directly cannot
        # read a stale cache.
        rev = getattr(app, "_state_revision", None)
        if rev is not None:
            etag = f'"{rev}"'
            if_none_match = request.headers.get("If-None-Match")
            if if_none_match and if_none_match.strip() == etag:
                return Response(status=304, headers={"ETag": etag, "Cache-Control": "no-cache"})

        cache = None if app.config.get("TESTING") else getattr(app, "_state_cache", None)
        variant = ("lite" if lite else "std") + ("+full" if full else "")
        if cache is not None and rev is not None:
            entry = cache.get(variant)
            if entry is not None and entry[0] == rev:
                resp = Response(entry[1], mimetype="application/json")
                resp.headers["ETag"] = f'"{rev}"'
                return resp
        state = app.world.to_dict(lite=lite)
        # Conversation privacy is enforced by the The Commons endpoints. Never
        # publish private channel state through the world-wide state payload.
        state.pop("commons", None)
        # Perf: `rooms` is an exact duplicate of `areas` (serialization.py emits
        # the same dict under both keys) and `areas_by_id` has no HTTP consumer  - 
        # the browser reads `worldState.areas`. Together they roughly triple the
        # /api/state encode cost for ~13 MB of payload. Drop them from the wire
        # unless a caller explicitly opts in with ?full=1. `to_dict` itself is
        # unchanged (tests and non-HTTP callers still see areas_by_id).
        if not full:
            state.pop("rooms", None)
            state.pop("areas_by_id", None)
        state["scenario_ended"] = getattr(app.world, 'scenario_ended', False)
        state["_restart_requested"] = getattr(app.world, '_restart_requested', False)
        state["vital_polarity"] = VITAL_POLARITY
        state["is_play_mode"] = bool(getattr(app, 'play_mode', False))
        # task-330: pending browser-side LLM responses (llm_respond effect).
        state["llm_pending"] = list(getattr(app.world, 'llm_pending_requests', []) or [])
        # task-228/229/227: calendar + sky state for widgets and agents.
        try:
            state["game_day"] = int(app.world.game_day)
            state["game_month"] = int(app.world.game_month)
            state["game_year"] = int(app.world.game_year)
            # task-554: the engine's season, shipped with the clock so the sky
            # widget and any agent reading the state agree with the temperature
            # model instead of each carrying their own month→season table.
            state["season"] = app.world.current_season()
            state["calendar_config"] = dict(getattr(app.world, "calendar_config", {}) or {})
            moon = app.world.current_moon_phase()
            moon["game_day"] = int(app.world.game_day)
            state["moon_phase"] = moon
            state["forecast"] = dict(getattr(app.world, "forecast", {}) or getattr(app.world, "forecast_schedule", {}) or {})
            state["forecast_override"] = dict(getattr(app.world, "forecast_override", {}) or {}) \
                if getattr(app.world, "forecast_override", None) else None
        except Exception:
            pass
        resp = jsonify(state)
        if rev is not None:
            resp.headers["ETag"] = f'"{rev}"'
        if cache is not None and rev is not None:
            cache[variant] = (rev, resp.get_data())
        return resp
    except Exception as e:
        logger.exception("Error in /api/state")
        return jsonify({"error": str(e)}), 500


def handle_llm_respond_post(app):
    """Receive a browser-generated LLM line for a pending request (task-330).

    The engine cannot call LLMs (keys live in the browser), so the frontend
    generates the line for a `llm_respond` effect and posts it here. The
    engine logs it as area speech from the object (broadcast_speech), then
    consumes the request. A missing/empty reply uses `fallback_message`.
    """
    data = request.get_json() or {}
    rid = data.get('id', '')
    text = (data.get('text') or '').strip()
    world = app.world

    pending = next((r for r in getattr(world, 'llm_pending_requests', []) if r.get('id') == rid), None)
    if pending is None:
        return jsonify({"error": "No pending request with that id (expired?)."}), 404

    line = text or pending.get("fallback_message", "")
    world.consume_llm_respond(rid)
    if not line:
        return jsonify({"status": "ok", "text": ""})

    speaker = pending.get("speaker", "something")
    # Route the line into the area speech pipeline so nearby agents hear it.
    node_id = pending.get("node_id", "")
    area_name = ''
    if node_id:
        node = world.graph.get_node(node_id)
        if node is not None:
            # the object's parent area: follow its `in`/spatial edges
            for edge in world.graph.get_edges_for_source(node_id, EDGE_IN):
                area_node = world.graph.get_node(edge.target)
                if area_node is not None and area_node.type == 'area':
                    area_name = area_node.name
                    break
    try:
        if area_name:
            world.broadcast_speech(speaker, line, area_name=area_name)
        else:
            world.add_log_entry(f"[{speaker}] {line}")
    except Exception as e:
        logger.exception("llm_respond post: speech broadcast failed")
        return jsonify({"error": str(e)}), 500

    return jsonify({"status": "ok", "text": line, "speaker": speaker, "area": area_name})


def handle_autocomplete(app):
    data = request.get_json() or {}
    verb = data.get('verb', '')
    prefix = data.get('prefix', '')
    character = data.get('character')
    options = app.world.get_autocomplete_options(verb, prefix, character)
    return jsonify({"options": options, "verb": verb, "prefix": prefix})


def _parse_throw_command(rest: str):
    """Split ``<item> to/over/through/at/into <target>`` into ``(item, target)``."""
    text = str(rest or "").strip()
    if not text:
        return "", ""
    lower = text.lower()
    for prep in (" over ", " through ", " into ", " to ", " at "):
        idx = lower.find(prep)
        if idx > 0:
            return text[:idx].strip(), text[idx + len(prep):].strip()
    return text, ""


def validate_action_command(world, char_name, cmd):
    """Dry-run validation of a command string against live world invariants without mutating state."""
    if not cmd or not cmd.strip():
        return {"valid": False, "category": "empty", "detail": "No action specified."}

    raw_cmd = cmd.strip()
    cmd = raw_cmd.lower()
    alias_map = [
        ("read ", "examine "),
        ("inspect ", "examine "),
        ("check ", "examine "),
        ("light ", "use "),
        ("ignite ", "use "),
        ("snatch ", "take "),
        ("collect ", "take "),
        ("hit ", "attack "),
        ("strike ", "attack "),
        ("punch ", "attack "),
        ("yell ", "shout "),
        ("walk ", "go "),
        ("move ", "go "),
        ("head ", "go "),
        ("step ", "go "),
    ]
    for alias_prefix, canonical_prefix in alias_map:
        if cmd.startswith(alias_prefix):
            cmd = canonical_prefix + cmd[len(alias_prefix):].strip()
            break
    if cmd.startswith("pick up "):
        cmd = "take " + cmd[8:].strip()
    elif cmd.startswith("pick "):
        cmd = "take " + cmd[5:].strip()

    tokens, token_quoted = tokenize_command_detailed(cmd)
    if not tokens:
        return {"valid": False, "category": "empty", "detail": "Empty command."}

    # Strip leading intensity adverbs for intimacy verbs ("firmly kiss lydia")
    if len(tokens) > 1 and tokens[0].lower() in _INTENSITY_ADVERBS and tokens[1].lower() in _INTIMACY_VERBS:
        tokens = tokens[1:]
        token_quoted = token_quoted[1:]
        cmd = ' '.join(tokens)

    verb = tokens[0].lower()
    target_str = ' '.join(tokens[1:]).strip() if len(tokens) > 1 else ""
    target_lower = target_str.lower()
    target_cleaned = re.sub(r'^(?:the|a|an)\s+', '', target_lower).strip()

    # 1. Identify player current area and helper matchers
    player_obj = world.players.get(char_name) if hasattr(world, 'players') else None
    area_name = player_obj.current_area if player_obj else (world.current_area.name if world.current_area else None)
    area_id = world._area_node_id(area_name) if hasattr(world, '_area_node_id') and area_name else world._get_current_area_id()
    current_area_node = world.graph.get_node(area_id) if area_id else None

    matcher = getattr(getattr(world, "movement", None), "name_matcher", None)
    exits = matcher._collect_exits(area_id) if (matcher and area_id) else []

    compass_dirs = {
        "north", "south", "east", "west", "northeast", "northwest", "southeast", "southwest",
        "up", "down", "in", "out", "outside", "inside",
        "n", "s", "e", "w", "ne", "nw", "se", "sw", "u", "d"
    }

    def _resolve_item(name_str: str):
        if not name_str:
            return None
        matched = world._match_item_name(name_str)
        if matched:
            return matched
        try:
            from engine.item_reach import find_reachable
            node = find_reachable(world.graph, getattr(world, "name_matcher", None), world, name_str)
            if node and getattr(node, "name", None):
                return node.name
        except Exception:
            pass
        return None

    def _resolve_exit(name_str: str):
        if not name_str:
            return None
        n_low = name_str.lower().strip()
        n_clean = re.sub(r'^(?:the|a|an)\s+', '', n_low).strip()
        if n_low in compass_dirs:
            return n_low
        if n_low.startswith("door:"):
            node = world.graph.get_node(n_low[5:]) if world.graph else None
            if node:
                return getattr(node, "name", None) or n_low
        for _edge, way_node, handle, target_area in exits:
            way_names = [str(handle).lower(), str(target_area).lower()]
            if way_node:
                way_names.extend([str(getattr(way_node, 'name', '')).lower(), str(getattr(way_node, 'id', '')).lower()])
            if any(n_low in wn or n_clean in wn or wn in n_low for wn in way_names if wn):
                return str(handle)
        return None

    def _resolve_char_in_room(name_str: str, allow_self: bool = False):
        if not name_str:
            return None
        n_low = name_str.lower().strip()
        if allow_self and (n_low in ("self", "me", "myself") or (char_name and n_low == char_name.lower())):
            return char_name
        resolved_char, _ = world._match_character_name(name_str)
        if resolved_char:
            target_p = world.players.get(resolved_char) if hasattr(world, "players") else None
            if target_p is None or area_name is None or target_p.current_area == area_name:
                return resolved_char
        return None

    # 2. Check if whole command is an exit/way or compass direction
    if not target_str and (cmd in compass_dirs or any(cmd in (str(h).lower(), str(t).lower()) for _, _, h, t in exits)):
        return {"valid": True, "category": "exit", "resolved_target": cmd, "detail": f"Exit/direction '{cmd}'"}

    # 3. Self-contained and optional-target actions (evaluated BEFORE _VERBS_NEEDING_TARGET,
    # matching handle_take_action dispatch order so bare 'relieve', 'look', 'search' succeed)
    if verb == "relieve":
        try:
            from engine import relief as _relief
            proper = _relief.has_fixture(world.graph, area_id, lambda aid: _reachable_items(world, aid)) if area_id else False
            if proper:
                return {"valid": True, "category": "self", "resolved_target": "relieve", "detail": "Action 'relieve' verified (toilet/latrine present)."}
            return {"valid": True, "category": "self", "resolved_target": "relieve", "detail": "Action 'relieve' verified (no toilet/latrine in room - public/improvised relief penalty applies)."}
        except Exception:
            return {"valid": True, "category": "self", "resolved_target": "relieve", "detail": "Action 'relieve' verified."}

    if verb in ("wait", "nothing", "pause", "stay", "look", "l", "inventory", "inv", "i",
                "stats", "status", "listen", "stand", "sit", "lie", "lay", "fumble", "grope", "feel",
                "meditate", "stop", "dress", "undress", "strip", "unhide", "reveal",
                "escape", "struggle", "manifest", "vanish", "answer", "hangup"):
        return {"valid": True, "category": "self", "detail": f"Action '{verb}' recognized."}

    if verb in ("rest", "sleep", "bathe", "bath"):
        _, bed_target = _parse_activity_args(tokens, cmd)
        if bed_target:
            matched_bed = _resolve_item(bed_target)
            if not matched_bed:
                return {"valid": False, "category": "not_found", "detail": f"Item '{bed_target}' not found in room."}
            return {"valid": True, "category": "item", "resolved_target": matched_bed, "detail": f"Action '{verb}' on '{matched_bed}' verified"}
        return {"valid": True, "category": "self", "detail": f"Action '{verb}' recognized."}

    if verb in ("flee", "disengage", "withdraw", "recall", "plan", "replan", "schedule", "goal", "obligation", "find", "forage", "guess"):
        return {"valid": True, "category": "self", "resolved_target": target_str or verb, "detail": f"Action '{cmd}' recognized."}

    if verb in ("hide", "sneak", "conceal"):
        from engine.triggers.behaviors import parse_hide_command, _resolve_hide_target_node, _is_hideable_node
        _, prop_target = parse_hide_command(target_str)
        if not prop_target:
            return {"valid": True, "category": "self", "detail": f"Action '{verb}' recognized."}
        node = _resolve_hide_target_node(world, char_name, prop_target, player=player_obj)
        if node is not None and _is_hideable_node(node):
            return {"valid": True, "category": "item", "resolved_target": node.name, "detail": f"Cover '{node.name}' verified"}
        return {"valid": False, "category": "not_found", "detail": f"Hideable cover '{prop_target}' not found in room."}

    if verb == "search":
        if not target_str:
            return {"valid": True, "category": "self", "detail": "Action 'search' (room search) recognized."}
        resolved_char = _resolve_char_in_room(target_str)
        if resolved_char:
            return {"valid": True, "category": "character", "resolved_target": resolved_char, "detail": f"Search character '{resolved_char}' verified"}
        matched_item = _resolve_item(target_str)
        if matched_item:
            return {"valid": True, "category": "item", "resolved_target": matched_item, "detail": f"Search item '{matched_item}' verified"}
        verb = "examine"

    if verb in ("wake", "release", "fix", "treat") and not target_str:
        return {"valid": True, "category": "self", "detail": f"Action '{verb}' recognized."}

    # 4. Social / Conversation actions
    if verb in ("speak", "say", "whisper", "shout", "scream", "sing", "do"):
        if not target_str and verb in ("speak", "say", "whisper", "do"):
            return {"valid": False, "category": "missing_target", "detail": f"Action '{verb}' requires text or a target."}
        return {"valid": True, "category": "speech", "detail": "Spoken/emote line verified."}

    # 5. Check bare verbs that strictly require a target
    if not target_str and verb in _VERBS_NEEDING_TARGET and verb not in ("examine", "x"):
        return {"valid": False, "category": "missing_target", "detail": f"Action '{verb}' requires a target."}

    # 6. Examine resolution: bare examine -> current area; otherwise character -> area -> item -> exit/way
    if verb in ("examine", "x"):
        if not target_str:
            if current_area_node:
                return {"valid": True, "category": "area", "resolved_target": current_area_node.name, "detail": f"Bare examine defaults to area '{current_area_node.name}'"}
            return {"valid": False, "category": "missing_target", "detail": f"Action '{verb}' requires a target."}
        resolved_char = _resolve_char_in_room(target_str, allow_self=True)
        if resolved_char:
            return {"valid": True, "category": "character", "resolved_target": resolved_char, "detail": f"Character '{resolved_char}' in room"}

        area_phrases = {"room", "area", "here", "surroundings", "the room", "the area", "current room", "current area"}
        if current_area_node and (
            target_lower in area_phrases
            or target_lower in str(current_area_node.name).lower()
            or target_lower in str(current_area_node.id).lower()
            or target_cleaned == str(current_area_node.name).lower()
            or (area_name and target_lower in area_name.lower())
        ):
            return {"valid": True, "category": "area", "resolved_target": current_area_node.name, "detail": f"Area '{current_area_node.name}'"}

        matched_item = _resolve_item(target_str)
        if matched_item:
            return {"valid": True, "category": "item", "resolved_target": matched_item, "detail": f"Item '{matched_item}' verified in room/inventory"}

        matched_exit = _resolve_exit(target_str)
        if matched_exit:
            return {"valid": True, "category": "exit", "resolved_target": matched_exit, "detail": f"Exit/way '{matched_exit}' verified"}

        return {"valid": False, "category": "not_found", "detail": f"Target '{target_str}' not found in room context, inventory, or exits."}

    # 7. Movement resolution
    if verb in ("go", "enter", "exit", "approach", "dash", "crawl", "climb", "jump", "swim", "dive"):
        if not target_str:
            return {"valid": False, "category": "missing_target", "detail": f"Action '{verb}' requires a destination."}
        matched_exit = _resolve_exit(target_str)
        if matched_exit:
            return {"valid": True, "category": "exit", "resolved_target": matched_exit, "detail": f"Exit '{matched_exit}' verified"}

        matched_item = _resolve_item(target_str)
        if matched_item:
            return {"valid": True, "category": "item", "resolved_target": matched_item, "detail": f"Item '{matched_item}' in room"}

        resolved_char = _resolve_char_in_room(target_str)
        if resolved_char:
            return {"valid": True, "category": "character", "resolved_target": resolved_char, "detail": f"Character '{resolved_char}' in room"}

        return {"valid": False, "category": "not_found", "detail": f"Destination or target '{target_str}' not found in room exits or objects."}

    # 8. Throw / toss resolution
    if verb in ("throw", "toss"):
        item_part, dest_part = _parse_throw_command(target_str)
        matched_item = _resolve_item(item_part) if item_part else None
        if not matched_item:
            return {"valid": False, "category": "not_found", "detail": f"Item '{item_part or target_str}' not found in room or inventory."}
        if dest_part:
            dest_lower = dest_part.lower()
            if dest_lower in compass_dirs or dest_lower in ("ground", "floor", "here"):
                return {"valid": True, "category": "item", "resolved_target": matched_item, "detail": f"Throw '{matched_item}' toward '{dest_part}' verified"}
            matched_exit = _resolve_exit(dest_part)
            if matched_exit:
                return {"valid": True, "category": "item", "resolved_target": matched_item, "detail": f"Throw '{matched_item}' toward '{matched_exit}' verified"}
            resolved_char = _resolve_char_in_room(dest_part)
            if resolved_char:
                return {"valid": True, "category": "item", "resolved_target": matched_item, "detail": f"Throw '{matched_item}' toward '{resolved_char}' verified"}
            if _resolve_item(dest_part):
                return {"valid": True, "category": "item", "resolved_target": matched_item, "detail": f"Throw '{matched_item}' toward '{dest_part}' verified"}
            return {"valid": False, "category": "not_found", "detail": f"Destination or target '{dest_part}' not found in room exits or surroundings."}
        return {"valid": True, "category": "item", "resolved_target": matched_item, "detail": f"Item '{matched_item}' verified"}

    # 9. Use / use_on / write / inscribe (supports quantity and 'on'/'in' target split matching handle_take_action)
    if verb in ("use", "use_on", "write", "inscribe"):
        use_tokens = list(tokens)
        use_quoted = list(token_quoted)
        if len(use_tokens) > 1 and re.match(r'^\d+$', use_tokens[1]):
            use_tokens = [use_tokens[0]] + use_tokens[2:]
            use_quoted = [use_quoted[0]] + use_quoted[2:]
        on_idx = None
        for i in range(1, len(use_tokens)):
            if use_tokens[i] in ("on", "in") and not use_quoted[i]:
                on_idx = i
                break
        if on_idx is not None and on_idx > 1:
            item_part = ' '.join(use_tokens[1:on_idx]).strip()
            target_part = ' '.join(use_tokens[on_idx + 1:]).strip() if on_idx + 1 < len(use_tokens) else ""
            if on_idx + 1 < len(use_tokens):
                quoted_after_on = [i for i in range(on_idx + 1, len(use_tokens)) if use_quoted[i]]
                if quoted_after_on:
                    target_part = use_tokens[quoted_after_on[0]]
            matched_item = _resolve_item(item_part)
            if not matched_item:
                return {"valid": False, "category": "not_found", "detail": f"Item '{item_part}' not found in room or inventory."}
            if target_part:
                matched_target = _resolve_item(target_part) or _resolve_exit(target_part) or _resolve_char_in_room(target_part, allow_self=True)
                if not matched_target:
                    return {"valid": False, "category": "not_found", "detail": f"Target '{target_part}' for '{matched_item}' not found in room or exits."}
                return {"valid": True, "category": "item", "resolved_target": f"{matched_item} on {matched_target}", "detail": f"Use '{matched_item}' on '{matched_target}' verified"}
            return {"valid": True, "category": "item", "resolved_target": matched_item, "detail": f"Item '{matched_item}' verified"}
        else:
            item_part = ' '.join(use_tokens[1:]).strip()
            matched_item = _resolve_item(item_part)
            if matched_item:
                return {"valid": True, "category": "item", "resolved_target": matched_item, "detail": f"Item '{matched_item}' verified"}
            return {"valid": False, "category": "not_found", "detail": f"Item '{item_part or target_str}' not found in room or inventory."}

    # 10. Put / place / stow (splits on relation prepositions matching handle_take_action)
    if verb in ("put", "place", "stow"):
        item_part = target_str
        surface_part = ""
        for prep in (" in ", " on ", " under ", " beside ", " behind ", " at "):
            idx = target_lower.find(prep)
            if idx > 0:
                item_part = target_str[:idx].strip()
                surface_part = target_str[idx + len(prep):].strip()
                break
        if verb in ("put", "place") and not surface_part:
            return {"valid": False, "category": "missing_target", "detail": f"Action '{verb}' requires a destination (e.g. '{verb} <item> on/in <target>')."}
        matched_item = _resolve_item(item_part)
        if not matched_item:
            return {"valid": False, "category": "not_found", "detail": f"Item '{item_part}' not found in room or inventory."}
        if surface_part:
            matched_surface = _resolve_item(surface_part)
            if not matched_surface:
                return {"valid": False, "category": "not_found", "detail": f"Container or surface '{surface_part}' not found in room."}
            return {"valid": True, "category": "item", "resolved_target": f"{matched_item} -> {matched_surface}", "detail": f"Place '{matched_item}' on/in '{matched_surface}' verified"}
        return {"valid": True, "category": "item", "resolved_target": matched_item, "detail": f"Stow '{matched_item}' verified"}

    # 11. Give / hand / steal / teach
    if verb in ("give", "hand"):
        to_idx = target_lower.find(" to ")
        if to_idx <= 0:
            return {"valid": False, "category": "missing_target", "detail": "Action 'give' requires a recipient ('give <item> to <character>')."}
        item_part = target_str[:to_idx].strip()
        recipient_part = target_str[to_idx + 4:].strip()
        matched_item = _resolve_item(item_part)
        if not matched_item:
            return {"valid": False, "category": "not_found", "detail": f"Item '{item_part}' not found in inventory."}
        resolved_char = _resolve_char_in_room(recipient_part)
        if not resolved_char:
            return {"valid": False, "category": "not_found", "detail": f"Recipient '{recipient_part}' not found in room."}
        return {"valid": True, "category": "character", "resolved_target": f"{matched_item} to {resolved_char}", "detail": f"Give '{matched_item}' to '{resolved_char}' verified"}

    if verb == "steal":
        from_idx = target_lower.find(" from ")
        if from_idx > 0:
            item_part = target_str[:from_idx].strip()
            victim_part = target_str[from_idx + 6:].strip()
            resolved_char = _resolve_char_in_room(victim_part)
            if not resolved_char:
                return {"valid": False, "category": "not_found", "detail": f"Target '{victim_part}' not found in room."}
            return {"valid": True, "category": "character", "resolved_target": f"{item_part} from {resolved_char}", "detail": f"Steal '{item_part}' from '{resolved_char}' verified"}
        resolved_char = _resolve_char_in_room(target_str)
        if resolved_char:
            return {"valid": True, "category": "character", "resolved_target": resolved_char, "detail": f"Steal from '{resolved_char}' verified"}
        matched_item = _resolve_item(target_str)
        if matched_item:
            return {"valid": True, "category": "item", "resolved_target": matched_item, "detail": f"Steal '{matched_item}' verified"}
        return {"valid": False, "category": "not_found", "detail": f"Target '{target_str}' not found in room."}

    if verb == "teach":
        to_idx = target_lower.find(" to ")
        if to_idx <= 0:
            return {"valid": False, "category": "missing_target", "detail": "Action 'teach' requires a recipient ('teach <subject> to <character>')."}
        student_part = target_str[to_idx + 4:].strip()
        resolved_char = _resolve_char_in_room(student_part)
        if not resolved_char:
            return {"valid": False, "category": "not_found", "detail": f"Student '{student_part}' not found in room."}
        return {"valid": True, "category": "character", "resolved_target": resolved_char, "detail": f"Teach '{resolved_char}' verified"}

    # 12. Combine / split / craft / make
    if verb == "combine":
        with_idx = target_lower.find(" with ")
        if with_idx > 0:
            src_part = target_str[:with_idx].strip()
            dst_part = target_str[with_idx + 6:].strip()
        else:
            parts = target_str.split()
            src_part = parts[0] if parts else ""
            dst_part = parts[1] if len(parts) > 1 else ""
        m1 = _resolve_item(src_part)
        m2 = _resolve_item(dst_part) if dst_part else None
        if m1 and m2:
            return {"valid": True, "category": "item", "resolved_target": f"{m1} + {m2}", "detail": f"Combine '{m1}' with '{m2}' verified"}
        return {"valid": False, "category": "not_found", "detail": f"Items to combine ('{target_str}') not found in room or inventory."}

    if verb == "split":
        item_part = re.sub(r'\s+into\s+\d+\s*$', '', target_str, flags=re.I).strip()
        matched_item = _resolve_item(item_part)
        if matched_item:
            return {"valid": True, "category": "item", "resolved_target": matched_item, "detail": f"Split '{matched_item}' verified"}
        return {"valid": False, "category": "not_found", "detail": f"Item '{item_part}' not found in room or inventory."}

    if verb in ("craft", "make"):
        crafting = getattr(world, "crafting", None)
        if crafting and hasattr(crafting, "_find_recipe"):
            entry = crafting._find_recipe(target_str)
            if entry:
                rname = entry.get("name") or target_str
                return {"valid": True, "category": "item", "resolved_target": rname, "detail": f"Recipe '{rname}' verified"}
        return {"valid": True, "category": "action", "resolved_target": target_str, "detail": f"Craft '{target_str}' recognized."}

    # 13. Single-item & door actions
    if verb in ("take", "get", "pickup", "drop", "eat", "consume", "drink", "quaff", "wear", "equip", "remove", "unequip", "open", "close", "unlock", "lock", "toggle", "fix", "treat"):
        item_query = target_str
        if verb in ("take", "get", "pickup") and len(tokens) >= 3 and tokens[-1].isdigit():
            item_query = ' '.join(tokens[1:-1]).strip()
        elif verb in ("wear", "equip") and " under " in target_lower:
            item_query = target_str.split(" under ", 1)[0].strip()
        elif verb in ("remove", "unequip") and hasattr(world, "EQUIP_SLOTS") and target_lower in world.EQUIP_SLOTS:
            return {"valid": True, "category": "item", "resolved_target": target_lower, "detail": f"Equipment slot '{target_lower}' verified"}

        matched_item = _resolve_item(item_query)
        if matched_item:
            return {"valid": True, "category": "item", "resolved_target": matched_item, "detail": f"Item '{matched_item}' verified"}
        if verb in ("open", "close", "unlock", "lock"):
            matched_exit = _resolve_exit(target_str)
            if matched_exit:
                return {"valid": True, "category": "exit", "resolved_target": matched_exit, "detail": f"Door/way '{matched_exit}' verified"}
        if verb in ("fix", "treat"):
            resolved_char = _resolve_char_in_room(target_str, allow_self=True)
            if resolved_char:
                return {"valid": True, "category": "character", "resolved_target": resolved_char, "detail": f"Character '{resolved_char}' verified"}
        return {"valid": False, "category": "not_found", "detail": f"Item '{target_str}' not found in room or inventory."}

    # 14. Combat, grapple, social & intimacy character actions
    if verb in ("attack", "kill", "hit", "disarm", "grab", "release", "lead", "wake", "frisk", "talk", "hug") or verb in _INTIMACY_VERBS:
        if verb in _INTIMACY_VERBS and not getattr(world, "mature_content", False):
            return {"valid": False, "category": "mature_disabled", "detail": f"Intimacy action '{verb}' is disabled when mature content is off."}
        char_query = target_str
        if verb in ("attack", "kill", "hit") or verb in _INTIMACY_VERBS:
            for marker in (" on ", " where ", " in the ", " in ", " with "):
                idx = char_query.lower().find(marker)
                if idx > 0:
                    char_query = char_query[:idx].strip()
            try:
                from engine.pleasure_actions import parse_intensity
                _, char_query = parse_intensity(char_query)
            except Exception:
                pass
        elif verb == "disarm":
            if char_query.lower().endswith(" and catch"):
                char_query = char_query[:-10].strip()
            from_idx = char_query.lower().find(" from ")
            if from_idx > 0:
                char_query = char_query[from_idx + 6:].strip()

        resolved_char = _resolve_char_in_room(char_query)
        if resolved_char:
            return {"valid": True, "category": "character", "resolved_target": resolved_char, "detail": f"Character '{resolved_char}' verified"}
        if verb == "grab":
            matched_item = _resolve_item(char_query)
            if matched_item:
                return {"valid": True, "category": "item", "resolved_target": matched_item, "detail": f"Item '{matched_item}' verified"}
        return {"valid": False, "category": "not_found", "detail": f"Character '{char_query}' not found in room."}

    if verb in ("fear", "interest", "name", "label", "call", "text", "message", "offer", "bind", "enchant"):
        if not target_str:
            return {"valid": False, "category": "missing_target", "detail": f"Action '{verb}' requires arguments."}
        return {"valid": True, "category": "action", "resolved_target": target_str, "detail": f"Action '{cmd}' recognized."}

    # 15. Final registry check: reject unknown/invented verbs instead of silently passing them
    try:
        try:
            from engine.actions import is_valid_action as _is_valid_verb
        except ImportError:
            from engine.action_verbs import is_valid_verb as _is_valid_verb
        if not _is_valid_verb(verb, mature=bool(getattr(world, "mature_content", False))):
            return {"valid": False, "category": "unknown_verb", "detail": f"Unknown action '{verb}'."}
    except Exception:
        pass

    return {"valid": True, "category": "action", "detail": f"Action '{cmd}' recognized."}


def handle_validate_action(app):
    data = request.get_json() or {}
    cmd = data.get('action') or ''
    if not cmd.strip():
        return jsonify({"valid": False, "category": "empty", "detail": "No action specified."}), 400

    world = app.world
    prev_active = world.player_manager.active_player
    char_name = data.get('character') or data.get('player') or prev_active
    simulated_area = data.get('area')

    prev_area = None
    player_obj = world.players.get(char_name) if hasattr(world, 'players') else None
    if char_name and char_name in getattr(world.player_manager, 'players', {}):
        world.player_manager.active_player = char_name
    if simulated_area and player_obj and player_obj.current_area != simulated_area:
        prev_area = player_obj.current_area
        player_obj.current_area = simulated_area

    try:
        result = validate_action_command(world, char_name, cmd)
        return jsonify(result), 200
    finally:
        if prev_area and player_obj:
            player_obj.current_area = prev_area
        world.player_manager.active_player = prev_active


def handle_take_action(app):
    data = request.get_json()
    if not data or 'action' not in data:
        return jsonify({"error": "Missing 'action' in request body"}), 400

    cmd = data['action'].strip().lower()
    original_cmd = cmd
    world = app.world
    prev_active = world.player_manager.active_player
    if 'character' in data:
        world.player_manager.active_player = data['character']
    output_lines = []
    was_movement = False
    was_look = False
    failed = False

    alias_map = [
        ("read ", "examine "),
        ("inspect ", "examine "),
        ("check ", "examine "),
        ("light ", "use "),
        ("ignite ", "use "),
        ("snatch ", "take "),
        ("collect ", "take "),
        ("hit ", "attack "),
        ("strike ", "attack "),
        ("punch ", "attack "),
        ("yell ", "shout "),
        ("walk ", "go "),
        ("move ", "go "),
        ("head ", "go "),
        ("step ", "go "),
    ]
    for alias_prefix, canonical_prefix in alias_map:
        if cmd.startswith(alias_prefix):
            cmd = canonical_prefix + cmd[len(alias_prefix):].strip()
            break
    if cmd.startswith("pick up "):
        cmd = "take " + cmd[8:].strip()
    elif cmd.startswith("pick "):
        cmd = "take " + cmd[5:].strip()

    tokens, _TOKEN_QUOTED = tokenize_command_detailed(cmd)

    try:
        def add_output(text):
            if text:
                output_lines.append(text)

        # task-448: when a character target is ambiguous, never auto-pick. Emit a
        # readable list with a distinguishing detail per candidate, and attach a
        # structured chooser the client can render. The pick resolves to the
        # candidate's identity key, which _match_character_name accepts verbatim.
        choice_groups = []

        def note_ambiguity(verb, candidates):
            options = world.character_candidate_details(candidates)
            rendered = [
                f"{o['label']} ({o['detail']})" if o.get('detail') else o['label']
                for o in options
            ]
            add_output("You don't know exactly who that is. Do you mean: "
                       + "; ".join(rendered) + "?")
            choice_groups.append({"verb": verb, "options": options})

        gate_msg = _activity_gate(cmd, world, add_output)
        if gate_msg:
            raise ValueError(gate_msg)

        cond_block_msg = _action_block_gate(cmd, world, add_output)
        if cond_block_msg:
            raise ValueError(cond_block_msg)

        # task-352: action-economy slots. One major / one minor / three free per
        # turn; a higher slot pays for a lower action (a major pays for an
        # approach when the minor is spent). A failed attempt still spends the
        # slot  -  you tried  -  which is the point of a budget.
        #
        # Opt-in via `enforce_slots`: the turn composer and the agent submit set
        # it, so the *turn pipeline* is budgeted. Out-of-band sends  -  the
        # inspector/paperdoll buttons, the interjection lane, "Speak as guest"  - 
        # do not, because they are authoring/override actions, not the character's
        # turn.
        _slot_player = world.player_manager.players.get(world.player_manager.active_player)
        _arm_dash = False
        if _slot_player is not None and data.get("enforce_slots"):
            from engine import action_tiers as _at
            _slots = getattr(_slot_player, "turn_slots", None)
            if not _slots:
                _slot_player.turn_slots = _slots = {}
                _at.reset_slots(_slots)
            _verb = (cmd.split(" ", 1)[0] if cmd else "").lower()
            # task-784: one rule for every budgeted actor  -  a dash is a two-hop
            # burst (initiate major + finish minor); while it is armed the finish
            # is the only valid action; an abort (wait) clears it. See
            # engine.action_tiers.apply_action_gate.
            _err, _burst = _at.apply_action_gate(
                _slots, _verb, getattr(_slot_player, "burst_pending", 0))
            if _err:
                raise ValueError(_err)
            if _burst == "clear":
                _slot_player.burst_pending = 0
            _arm_dash = _burst == "arm"

        # T1: movement result handling. An intra-room positioning ("go the
        # booth table") does NOT change areas  -  the movement line is the whole
        # story, so the full room description only re-dumps on a real
        # transition (the agent already has the room in its context).
        def _move_and_describe(call):
            _prev = world.current_area.name if world.current_area else None
            _msg = call()
            add_output(_msg)
            if world.current_area and _prev != world.current_area.name:
                try:
                    from engine import fear as _fear
                    _fear.react_in_area(world, world.current_area.name)
                except Exception as e:
                    logger.warning("[action] fear react_in_area: %s", e)
                add_output(world.get_area_description())

        if world.current_area and cmd in [e.lower() for e in world.current_area.exits.keys()]:
            was_movement = True
            _move_and_describe(lambda: world.move_to_area(cmd))

        elif cmd.startswith("go "):
            was_movement = True
            direction = ' '.join(tokens[1:]) if len(tokens) > 1 else cmd[3:].strip()
            _hm = re.match(r'^([a-z]+)\s+(\d+)\s*(h|hr|hrs|hour|hours|m|min|mins|minute|minutes)$', direction, re.I)
            from engine import timeskip as _ts
            if _hm and _hm.group(1).lower() in _ts.HEADING_WORDS:
                _hdg = _hm.group(1).lower()
                _num = int(_hm.group(2))
                _unit = _hm.group(3).lower()
                _mins = _num * 60 if _unit.startswith('h') else _num
                _prev = world.current_area.name if world.current_area else None
                _res = _ts.advance(world, _mins, intent='travel', heading=_hdg)
                if not _res.ok:
                    add_output(_res.reason or 'You cannot travel that way right now.')
                else:
                    for _line in (_res.lines or []):
                        add_output(_line)
                    if _res.interrupted and _res.interrupt and _res.interrupt.get('detail'):
                        add_output(_res.interrupt['detail'])
                    if world.current_area and _prev != world.current_area.name:
                        try:
                            from engine import fear as _fear
                            _fear.react_in_area(world, world.current_area.name)
                        except Exception as e:
                            logger.warning("[action] fear react_in_area: %s", e)
                        add_output(world.get_area_description())
            else:
                _move_and_describe(lambda: world.move_to_area(direction))

        elif cmd.startswith("move_to ") or cmd.startswith("moveto "):
            was_movement = True
            rest = cmd.split(" ", 1)[1].strip()
            coord_m = re.match(r'^\(?\s*(\d+)\s*[, ]\s*(\d+)\s*\)?$', rest)
            if coord_m:
                x, y = int(coord_m.group(1)), int(coord_m.group(2))
                try:
                    res = world.move_to_coord(world.active_player, x, y)
                    add_output(res.get("message", f"You moved to ({x}, {y})."))
                except Exception as e:
                    add_output(str(e))
            else:
                try:
                    res = world.move_to_item(world.active_player, rest)
                    add_output(res.get("message", f"You moved to {rest}."))
                except Exception as e:
                    add_output(str(e))

        elif cmd.startswith("approach "):
            was_movement = True
            target = ' '.join(tokens[1:]) if len(tokens) > 1 else cmd[9:].strip()
            _move_and_describe(lambda: world.approach(target))

        elif cmd.startswith("dash "):
            was_movement = True
            direction = ' '.join(tokens[1:]) if len(tokens) > 1 else cmd[5:].strip()
            _move_and_describe(lambda: world.dash_to_area(direction))
            # task-784: arm the burst only once the hop actually happened. A block
            # (winded/encumbered/locked) raises out of `_move_and_describe`, so the
            # dash is left unarmed with its major already spent  -  the try's cost.
            if _arm_dash and _slot_player is not None:
                _slot_player.burst_pending = 1

        elif cmd.startswith("crawl "):
            was_movement = True
            direction = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
            _move_and_describe(lambda: world.crawl_to_area(direction))
        elif cmd.startswith("climb "):
            was_movement = True
            direction = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
            _move_and_describe(lambda: world.climb_to_area(direction))
        elif cmd.startswith("jump "):
            was_movement = True
            direction = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
            _move_and_describe(lambda: world.jump_to_area(direction))
        elif cmd.startswith("swim "):
            was_movement = True
            direction = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
            _move_and_describe(lambda: world.swim_to_area(direction))
        elif cmd.startswith("dive "):
            was_movement = True
            direction = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
            _move_and_describe(lambda: world.dive_to_area(direction))

        elif cmd in ("dismount",) or cmd.startswith("dismount "):
            actor_obj = world.players.get(world.active_player)
            mounted_on = getattr(actor_obj, "mounted_on", None) if actor_obj else None
            if not mounted_on:
                add_output("You are not mounted on anything.")
                failed = True
            else:
                actor_obj.mounted_on = None
                world.record_turn_event(world.active_player, "dismount", f"dismounted from {mounted_on}", area_name=world.current_area.name if world.current_area else None)
                add_output(f"You dismount from {mounted_on}.")

        elif cmd.startswith(("mount ", "ride ", "saddle ")):
            verb_word = cmd.split(" ", 1)[0]
            target_ref = cmd.split(" ", 1)[1].strip()
            actor_obj = world.players.get(world.active_player)
            area_name = world.current_area.name if world.current_area else ""
            if not target_ref:
                add_output(f"{verb_word.capitalize()} what?")
                failed = True
            else:
                mount_tags = {"mount", "mountable", "rideable", "vehicle", "horse", "pony", "mule", "donkey", "camel", "worg", "wolf", "boar", "bear", "beast", "animal"}
                matched_mount = None
                for pname, pobj in (world.players or {}).items():
                    if pname == world.active_player or getattr(pobj, "current_area", None) != area_name:
                        continue
                    if target_ref in pname.lower() or pname.lower() in target_ref:
                        pnode = world.graph.get_node(world._player_node_id(pname)) if hasattr(world, "graph") else None
                        ptags = {str(t).lower() for t in ((getattr(pobj, "tags", None) or []) + ((pnode.properties.get("tags") if pnode else None) or []))}
                        if ptags & mount_tags or (pnode and pnode.properties.get("mountable")):
                            matched_mount = pname
                            break
                if not matched_mount and hasattr(world, "graph") and world.current_area:
                    for item_node in world.get_items_in_area(area_name):
                        iname = str(getattr(item_node, "name", "") or "")
                        itags = {str(t).lower() for t in (item_node.properties.get("tags") or [])}
                        if (target_ref in iname.lower() or iname.lower() in target_ref) and (itags & mount_tags or item_node.properties.get("mountable")):
                            matched_mount = iname
                            break
                if not matched_mount:
                    add_output(f"There is no '{target_ref}' here that you can {verb_word}.")
                    failed = True
                elif verb_word == "saddle":
                    if actor_obj is not None:
                        saddled = set(getattr(actor_obj, "saddled_mounts", None) or [])
                        saddled.add(matched_mount)
                        actor_obj.saddled_mounts = sorted(saddled)
                    world.record_turn_event(world.active_player, "saddle", f"saddled {matched_mount}", area_name=area_name)
                    add_output(f"You saddle {matched_mount}.")
                else:
                    if actor_obj is not None:
                        actor_obj.mounted_on = matched_mount
                    world.record_turn_event(world.active_player, verb_word, f"mounted {matched_mount}", area_name=area_name)
                    add_output(f"You {verb_word} {matched_mount}.")

        elif cmd in ("rest", "sleep", "wait", "meditate", "bathe", "bath",
                     "sit", "sit down", "lie", "lie down", "lay down"):
            activity_type = {
                "rest": "resting",
                "sleep": "sleeping",
                "wait": "waiting",
                "meditate": "meditating",
                "bathe": "bathing",
                "bath": "bathing",
                "sit": "sitting",
                "sit down": "sitting",
                "lie": "lying_down",
                "lie down": "lying_down",
                "lay down": "lying_down",
            }[cmd]
            add_output(world.activities.start_activity(world.active_player, activity_type))

        elif cmd.startswith("open "):
            target = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
            if target.startswith("door:"):
                add_output(world.toggle_way_by_id(target[5:], "open"))
            else:
                add_output(world.toggle_way(target, "open"))
        elif cmd.startswith("close "):
            target = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
            if target.startswith("door:"):
                add_output(world.toggle_way_by_id(target[5:], "close"))
            else:
                add_output(world.toggle_way(target, "close"))

        elif cmd == "eat" or cmd.startswith("eat "):
            item_name = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
            result = world.eat_item(item_name)
            add_output(result)
        elif cmd == "drink" or cmd.startswith("drink "):
            item_name = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
            result = world.drink_item(item_name)
            add_output(result)

        elif cmd.startswith("relieve"):
            player = world.player
            if player and "Bladder" in player.vitals:
                player.vitals["Bladder"] = 0
                # task-551: permission is universal, so there is no branch here
                # that can refuse. What is left is the *comfort* distinction, and
                # it is scored by the same helper the background tier reads  -  which
                # also fixes the two tiers disagreeing: this used to test only
                # `toilet`/`bathroom`/`restroom` here, so a room tagged `latrine`
                # or `privy` was a restroom to the engine and a corner to the
                # player.
                from engine import relief as _relief
                area_id = world._get_current_area_id()
                proper = _relief.has_fixture(
                    world.graph, area_id, lambda aid: _reachable_items(world, aid))
                if proper:
                    add_output("You relieve yourself. Ah, much better.")
                else:
                    _relief.mark_smell(world.graph, area_id)
                    # T4: public relieve is a shame event  -  an internal hit
                    # always (Sanity), a social hit only when someone actually
                    # witnesses it (being alone keeps it between you and the
                    # puddle).
                    onlookers = _relief.witnesses(
                        world.graph, area_id, _roster(world),
                        exclude_name=world.active_player)
                    _relief.apply_dignity_cost(player, onlookers > 0)
                    world.effects.execute(
                        "spawn_item",
                        {"item_id": "puddle"},
                        {},
                        game_state=world,
                    )
                    if onlookers:
                        add_output(
                            f"You relieve yourself where {onlookers} others can see. "
                            "That is going to stink up the place.")
                    else:
                        add_output(
                            "You relieve yourself in a corner. That's going to "
                            "stink up the place.")
            else:
                add_output("You don't feel the need.")
            was_movement = False

        elif cmd.startswith("use "):
            # task-196: "use 2 kindling in fireplace"  -  quantity on use-on.
            amount = 1
            if len(tokens) > 1 and re.match(r'^\d+$', tokens[1]):
                amount = max(1, int(tokens[1]))
                tokens = [tokens[0]] + tokens[2:]
            on_idx = None
            for i in range(1, len(tokens)):
                if tokens[i] in ("on", "in"):
                    on_idx = i
                    break
            if on_idx is not None and on_idx > 1:
                item_name = ' '.join(tokens[1:on_idx])
                target_name = ' '.join(tokens[on_idx + 1:]) if on_idx + 1 < len(tokens) else ""
                params = None
                if on_idx + 1 < len(tokens):
                    quoted_after_on = [
                        i for i in range(on_idx + 1, len(tokens))
                        if _TOKEN_QUOTED[i]
                    ]
                    if quoted_after_on:
                        target_name = tokens[quoted_after_on[0]]
                        rest_quoted = [tokens[i] for i in quoted_after_on[1:]]
                        params = ' '.join(rest_quoted) if rest_quoted else None
                if params:
                    add_output(world.use_item_on(item_name, target_name, params=params, amount=amount))
                elif target_name:
                    add_output(world.use_item_on(item_name, target_name, amount=amount))
                else:
                    add_output(world.use_item_on(item_name, amount=amount))
            else:
                item_name = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
                add_output(world.use_item_on(item_name, amount=amount))
            world._add_entertainment_gain(3)

        elif cmd.startswith("examine "):
            target_name = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
            add_output(world.get_item_desc(target_name))
            world._add_entertainment_gain(5)

        elif cmd == "listen":
            add_output(world.listen())

        elif cmd.startswith("search ") or cmd.startswith("frisk "):
            # task-516: search a person, not the room, to reveal concealed items.
            person = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
            if person:
                try:
                    add_output(world.search_character(person))
                except ValueError as exc:
                    add_output(str(exc))
            else:
                add_output("Search whom?")

        elif cmd == "search":
            area_id = world._get_current_area_id()
            if not area_id:
                add_output("You look around but can't focus.")
            else:
                perception_dc = 12
                skill = "Perception"
                success, total, message = world.skills.skill_check(
                    skill, perception_dc
                )
                if world._last_skill_check_msg:
                    add_output(world._last_skill_check_msg)
                    world._last_skill_check_msg = None
                hidden_found = False
                for edge in world.graph.get_edges_for_target(
                    area_id, EDGE_IN
                ):
                    node = world.graph.get_node(edge.source)
                    if not (node and node.type == "item"):
                        continue
                    if node.properties.get("current_state") == "hidden":
                        if success:
                            node.properties["current_state"] = "normal"
                            add_output(
                                f"You found {node.name}! "
                                f"{message}"
                            )
                            hidden_found = True
                        else:
                            add_output(
                                f"You search near {node.name} "
                                f"but find nothing hidden."
                            )
                        trigger_outputs = world.item_actions._exec_triggers(
                            node, "on_search"
                        )
                        for out in trigger_outputs:
                            add_output(out)
                from engine.triggers.behaviors import search_hidden_characters_in_area
                spotted_chars = search_hidden_characters_in_area(
                    world, world.active_player, area_id, total, success
                )
                for spotted_msg in spotted_chars:
                    add_output(spotted_msg)
                    hidden_found = True
                if not hidden_found and not success:
                    add_output(
                        "You search the room thoroughly "
                        "but find nothing hidden."
                    )
                world._add_entertainment_gain(5)

        elif cmd == "guess" or cmd.startswith("guess time"):
            from engine.time_perception import resolve_guess_time
            for line in resolve_guess_time(world):
                add_output(line)

        elif cmd.startswith("find"):
            area_id = world._get_current_area_id()
            if not area_id:
                add_output("You look around but can't focus.")
            else:
                explicit_tag = ' '.join(tokens[1:]).strip() if len(tokens) > 1 else None
                if explicit_tag and is_loot_skill(explicit_tag):
                    # Skill-driven search (task-471): Survival finds plants and
                    # game, History finds old things, Religion finds relics.
                    from engine.foraging import find_or_spawn
                    area_name = getattr(world.player, 'current_area', None)
                    node = find_or_spawn(world, world.player, area_name,
                                         skill=explicit_tag)
                    if node is not None:
                        add_output(f"You search with {explicit_tag} and find {node.name}.")
                    else:
                        add_output(f"You search with {explicit_tag} but find nothing new.")
                    tags_to_search = []
                elif explicit_tag:
                    tags_to_search = [explicit_tag]
                    tag_label = f"'{explicit_tag}'"
                else:
                    interest_tags = getattr(world.player, 'interest_tags', []) or []
                    if interest_tags:
                        tags_to_search = interest_tags
                        tag_label = "your interests (" + ", ".join(tags_to_search) + ")"
                    else:
                        add_output(
                            "But what should I find? I don't really have any particular "
                            "interests right now. Maybe I should look for something specific, "
                            "or get a hobby..."
                        )
                        tags_to_search = []
                if tags_to_search:
                    tagged = world.graph.get_tagged_items_in_area(area_id)
                    seen = set()
                    matched = []
                    for tag in tags_to_search:
                        for item in tagged.get(tag.lower(), []):
                            if item.id not in seen:
                                seen.add(item.id)
                                matched.append(item)
                    if not matched:
                        add_output(f"You don't sense any items with {tag_label} here.")
                    else:
                        names = ", ".join(item.name for item in matched)
                        add_output(
                            f"You sense {len(matched)} item(s) matching {tag_label}: {names}"
                        )
                world._add_entertainment_gain(3)

        elif cmd.startswith(("take ", "get ", "pickup ")):
            if len(tokens) >= 3 and tokens[-1].isdigit():
                item_name = ' '.join(tokens[1:-1])
            else:
                item_name = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
            selected_by_id = False
            if len(tokens) >= 3 and tokens[-1].isdigit():
                index = int(tokens[-1]) - 1
                area_id = world._get_current_area_id()
                matching_nodes = []
                for edge in world.graph.get_edges_for_target(area_id, EDGE_IN):
                    node = world.graph.get_node(edge.source)
                    if node and node.name.lower() == item_name.lower():
                        matching_nodes.append(node)
                if not matching_nodes:
                    fuzzy_name = world.name_matcher._match_item_name(item_name)
                    if fuzzy_name:
                        for edge in world.graph.get_edges_for_target(area_id, EDGE_IN):
                            node = world.graph.get_node(edge.source)
                            if node and node.name.lower() == fuzzy_name.lower():
                                matching_nodes.append(node)
                if 0 <= index < len(matching_nodes):
                    try:
                        add_output(world.take_item(item_name, item_id=matching_nodes[index].id))
                        selected_by_id = True
                    except Exception as take_err:
                        add_output(str(take_err))
                else:
                    add_output(f"Invalid selection. Found {len(matching_nodes)} items named '{item_name}'.")

            if not selected_by_id:
                try:
                    add_output(world.take_item(item_name))
                except AmbiguousItemError as e:
                    options = e.options
                    option_text = "\n".join([f"{i+1}. {o['name']}{' - '+o['description'] if o.get('description') else ''}" for i, o in enumerate(options)])
                    add_output(f"{str(e)}\n{option_text}\n\nType 'take {item_name} <number>' to pick a specific one, or use the item ID.")
                    return jsonify({
                        "output": "\n".join(output_lines),
                        "ambiguous_items": options,
                        "needs_selection": True
                    })
        elif cmd.startswith("drop "):
            item_name = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
            add_output(world.drop_item(item_name))
        elif cmd.startswith("throw ") or cmd.startswith("toss "):
            rest = cmd.split(None, 1)[1].strip() if " " in cmd else ""
            item_name, target_ref = _parse_throw_command(rest)
            if item_name and target_ref:
                add_output(world.throw_item(item_name, target_ref))
            elif rest:
                add_output(f"Throw '{rest}' where? Use: throw <item> to/over <way|area>")
            else:
                add_output("Throw what? Use: throw <item> to/over <way|area>")
        elif cmd.startswith("stow "):
            # task-146: `stow <item>` = hand → carrying; `stow <item> in
            # <container>` mirrors put. (autocomplete already advertised stow.)
            rest = cmd[5:].strip()
            in_idx = rest.find(" in ")
            if in_idx > 0:
                item_name = rest[:in_idx].strip()
                container_name = rest[in_idx + 4:].strip()
                add_output(world.put_item_in_container(item_name, container_name))
            elif rest:
                add_output(world.stow_item(rest))
            else:
                add_output("Stow what? Use: stow <item>, or stow <item> in <container>")
        elif cmd.startswith("put "):
            rest = cmd[4:].strip()
            in_idx = rest.find(" in ")
            if in_idx > 0:
                item_name = rest[:in_idx].strip()
                container_name = rest[in_idx + 4:].strip()
                add_output(world.put_item_in_container(item_name, container_name))
            else:
                relation = None
                for prep in (" on ", " under ", " beside ", " behind ", " at "):
                    idx = rest.find(prep)
                    if idx > 0:
                        relation = prep.strip()
                        item_name = rest[:idx].strip()
                        target_name = rest[idx + len(prep):].strip()
                        break
                if relation:
                    add_output(world.place_item(item_name, target_name, relation))
                else:
                    add_output("Put what where? Use: put <item> in <container>, or put <item> on/under/beside/behind/at <target>")
        elif cmd.startswith("place "):
            rest = cmd[6:].strip()
            relation = None
            for prep in (" on ", " under ", " beside ", " behind ", " at ", " in "):
                idx = rest.find(prep)
                if idx > 0:
                    relation = prep.strip()
                    item_name = rest[:idx].strip()
                    target_name = rest[idx + len(prep):].strip()
                    break
            if relation:
                add_output(world.place_item(item_name, target_name, relation))
            else:
                add_output("Place what where? Use: place <item> on/under/beside/behind/at/in <target>")
        elif cmd.startswith("combine "):
            # task-155: combine <source> with <target> (or "combine a b")
            rest = cmd[8:].strip()
            with_idx = rest.find(" with ")
            if with_idx > 0:
                source_name = rest[:with_idx].strip()
                target_name = rest[with_idx + 6:].strip()
            else:
                parts_split = rest.split()
                if len(parts_split) >= 2:
                    source_name = parts_split[0]
                    target_name = parts_split[1]
                else:
                    source_name = target_name = rest
            add_output(world.combine_items(source_name, target_name))
        elif cmd.startswith("split "):
            # split <item> [into N]
            rest = cmd[6:].strip()
            parts = 2
            import re as _re
            m = _re.search(r'into\s+(\d+)', rest)
            if m:
                parts = int(m.group(1))
                rest = rest[:m.start()].strip()
            item_name = rest.strip()
            if not item_name:
                add_output("Split what? Use: split <item> [into N]")
            else:
                add_output(world.split_item(item_name, parts))
        elif cmd.startswith("craft ") or cmd.startswith("make "):
            recipe_name = ' '.join(tokens[1:]) if len(tokens) > 1 else (
                cmd[6:].strip() if cmd.startswith("craft ") else cmd[5:].strip()
            )
            if not recipe_name:
                add_output("Craft what? Use: craft <recipe name>")
            else:
                # Task-840: timed recipes start a cooking Activity (same
                # verb, three doors); untimed resolve instantly.
                entry = world.crafting._find_recipe(recipe_name)
                if entry is not None and int(entry.get("duration_min", 0) or 0) > 0:
                    try:
                        add_output(world.crafting.start_cooking(world, recipe_name))
                    except ValueError as e:
                        add_output(str(e))
                else:
                    add_output(world.craft_item(recipe_name))
        elif cmd.startswith("teach "):
            # task-197: teach <recipe | skill:NAME> to <character>
            rest = cmd[6:].strip()
            to_idx = rest.find(" to ")
            if to_idx <= 0:
                add_output("Teach what to who? Use: teach <recipe name | skill:NAME> to <character>")
            else:
                subject = rest[:to_idx].strip()
                student = rest[to_idx + 4:].strip()
                add_output(world.teach_item(subject, student))
        elif cmd.startswith("give "):
            rest = cmd[5:].strip()
            to_idx = rest.find(" to ")
            if to_idx > 0:
                item_name = rest[:to_idx].strip()
                target_name = rest[to_idx + 4:].strip()
                add_output(world.give_item(item_name, target_name))
            else:
                add_output("Give what to who? Use: give <item> to <character>")
        elif cmd.startswith("steal "):
            rest = cmd[6:].strip()
            from_idx = rest.find(" from ")
            if from_idx > 0:
                item_name = rest[:from_idx].strip()
                target_name = rest[from_idx + 6:].strip()
                add_output(world.steal_item(item_name, target_name))
            else:
                add_output("Steal what from who? Use: steal <item> from <target>")
        elif cmd.startswith("fear "):
            add_output(world.fear_target(cmd[5:].strip()))
        elif cmd.startswith("interest "):
            add_output(world.interest_target(cmd[9:].strip()))
        elif cmd in ("i", "inv", "inventory"):
            inv = world.get_inventory()
            equipped = world.get_full_equipment()
            lines = []
            if equipped:
                for slot, items in equipped.items():
                    label = world.EQUIP_SLOTS.get(slot, {}).get("label", slot)
                    lines.append(f"  [{label}] {' > '.join(items)} [WORN]")
            lines.append("")
            if inv:
                carried = [n for n in inv if not any(n in stack for stack in equipped.values())]
                if carried:
                    lines.append(f"You are carrying: {', '.join(carried)}")
                else:
                    lines.append("You are not carrying anything.")
            else:
                lines.append("You are not carrying anything.")
            add_output("\n".join(lines))

        elif cmd.startswith(("wear ", "equip ")):
            rest = ' '.join(tokens[1:])
            if " under " in rest:
                parts = rest.split(" under ", 1)
                item_name = parts[0].strip()
                under_item = parts[1].strip()
                add_output(world.equip_item(item_name, under=under_item))
            else:
                add_output(world.equip_item(rest))

        elif cmd.startswith(("remove ", "unequip ")):
            rest = ' '.join(tokens[1:])
            slot_names = list(world.EQUIP_SLOTS.keys())
            if rest in slot_names:
                add_output(world.unequip_item(slot=rest))
            else:
                add_output(world.unequip_item(item_name=rest))

        elif cmd in ("undress", "strip"):
            add_output(world.strip())

        elif cmd.startswith(("rest", "sleep")):
            minutes, target = _parse_activity_args(tokens, cmd)
            if cmd.startswith("sleep"):
                add_output(world.sleep(minutes, target))
            else:
                add_output(world.rest(minutes, target))
        elif cmd.startswith("wait"):
            minutes, _ = _parse_activity_args(tokens, cmd)
            add_output(world.wait(minutes))
        elif cmd.startswith(("flee", "disengage", "withdraw")):
            # task-611: `flee` had no handler at all, so it fell through to the
            # emote catch-all and answered "Belne flee."  -  the same gibberish
            # task-629 removed everywhere else. `retreat` only ever appeared to
            # work because the *waiting* state string-matched the word to cancel
            # itself; on its own it was also an emote.
            #
            # DESIGN ASSUMPTION, flagged rather than assumed silently: fleeing
            # costs the turn and moves you ONE step along an exit, preferring an
            # exit whose handle does NOT contain the word you typed (so
            # `flee north` steps away from the north). There is no threat model
            # in the engine, so this is "get out of here", not "evade this
            # attacker"  -  real evasion is grapple-side and lives in
            # engine/grapple.py. If this should behave differently, the rule to
            # change is the choice below and nothing else.
            away = cmd.split(" ", 1)[1].strip().lower() if " " in cmd else ""
            area_id = world._get_current_area_id()
            matcher = getattr(getattr(world, "movement", None), "name_matcher", None)
            exits = matcher._collect_exits(area_id) if matcher else []
            if not exits:
                add_output("There's nowhere to run to.")
            else:
                def _try_exit():
                    for _edge, _way, handle, _target in exits:
                        if away and away in str(handle).lower():
                            continue          # that is the way they came from
                        return world.move_to_area(handle)
                    # Every exit matched the word: take the first one anyway
                    # rather than refuse to move.
                    return world.move_to_area(exits[0][2])
                was_movement = True
                _move_and_describe(_try_exit)
        elif cmd.startswith("meditate"):
            minutes, _ = _parse_activity_args(tokens, cmd)
            add_output(world.meditate(minutes))
        elif cmd.startswith(("bathe", "bath")):
            minutes, target = _parse_activity_args(tokens, cmd)
            add_output(world.bathe(target, minutes))
        elif cmd in ("sit", "sit down"):
            add_output(world.sit())
        elif cmd in ("lie down", "lay down", "lie"):
            add_output(world.lie_down())
        elif cmd in ("stand", "stand up", "get up"):
            add_output(world.stand())
        elif cmd.startswith(("fix", "treat")):
            target = ' '.join(tokens[1:]) if len(tokens) > 1 else None
            add_output(world.fix(target))
        elif cmd in ("stop", "stop doing that"):
            add_output(world.stop_activity())
        elif cmd.startswith("wake"):
            target = ' '.join(tokens[1:]) if len(tokens) > 1 else None
            add_output(world.wake(target))
        elif cmd in ("dress", "get dressed"):
            add_output(world.dress())
        elif cmd in ['fumble', 'fumble around', 'grope', 'grope around', 'feel around']:
            add_output(world.fumble_around())

        elif cmd == "look":
            was_look = True
            add_output(world.get_area_description())
            area_id = world._get_current_area_id()
            if area_id:
                for edge in world.graph.get_edges_for_target(area_id, EDGE_IN):
                    node = world.graph.get_node(edge.source)
                    if node and node.type == "item":
                        trigger_outputs = world.item_actions._exec_triggers(
                            node, "on_look"
                        )
                        for out in trigger_outputs:
                            add_output(out)
        elif cmd in ("stats", "status"):
            player = world.player
            area_name = world.current_area.name if world.current_area else "Nowhere"
            readout = format_vitals_readout(getattr(player, "vitals", {}))
            add_output(
                f"Status for {world.active_player} in {area_name}:\n"
                f"State: {getattr(player, 'state', 'unknown')}\n"
                f"Vitals:\n{readout}"
            )

        elif cmd == "recall" or cmd.startswith("recall "):
            player = world.player
            arg = cmd[7:].strip() if cmd.startswith("recall ") else ""
            if not arg or arg in ("map", "landmarks", "places"):
                curr = world.current_area.name if world.current_area else "nowhere"
                visited = player.visited_area_names(world.graph) if hasattr(player, "visited_area_names") else set()
                charted = getattr(player, "charted_cells", {}) or {}
                total_cells = sum(len(c) for c in charted.values())
                sample = ", ".join(sorted(visited)[:5])
                extra = f" (including {sample})" if sample else ""
                add_output(
                    f"Mental map: you are in {curr}. You have visited {len(visited)} areas{extra} "
                    f"and surveyed {total_cells} grid cells across your travels."
                )
            else:
                is_path_query = arg.startswith(("path ", "path to ", "to "))
                target = arg
                for prefix in ("path to ", "path ", "to "):
                    if target.startswith(prefix):
                        target = target[len(prefix):].strip()
                        break
                curr = world.current_area.name if world.current_area else ""
                # task-467: route through what the character knows, including
                # authored known/known_areas, not only what they walked.
                from engine.spatial_memory import SpatialMemory, known_route_areas
                known = known_route_areas(player, world.graph)
                route = SpatialMemory(world.graph).find_route(curr, target, known)
                if route:
                    steps = [f"go {step['direction']} to {step['to']}" for step in route]
                    add_output(f"Route to {target} ({len(steps)} hops): " + ", then ".join(steps) + ".")
                elif is_path_query:
                    add_output(f"You do not recall a known path from {curr} to {target}.")
                else:
                    add_output(f"You do not recall having charted or visited '{target}'.")

        elif cmd in ("manifest", "vanish"):
            player = world.player
            if player and player.state == "dead" and world.ghost_mode:
                if cmd == "manifest":
                    player.ghost_visible = True
                    add_output("You focus your spirit energy, becoming visible to the living. A faint outline of your form shimmers into view.")
                else:
                    player.ghost_visible = False
                    add_output("You release your concentration, fading back into the spirit realm. You are once again invisible to the living.")
            else:
                add_output("You are not a ghost, or ghost mode is inactive.")

        elif tokens and tokens[0] in ("unhide", "reveal"):
            from engine.triggers.behaviors import unhide_character
            add_output(unhide_character(world, world.active_player))

        elif tokens and tokens[0] in ("hide", "sneak", "conceal"):
            from engine.triggers.behaviors import hide_character, parse_hide_command
            arg_str = cmd.split(" ", 1)[1].strip() if " " in cmd else ""
            rel, target_ref = parse_hide_command(arg_str)
            ok, msg = hide_character(world, world.active_player, target=target_ref, relation=rel)
            if not ok:
                failed = True
            add_output(msg)

        elif cmd.startswith("toggle "):
            item_name = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
            try:
                add_output(world.toggle_item_status(item_name))
            except ValueError as e:
                add_output(str(e))

        elif cmd.startswith("attack "):
            from engine.body_parts import resolve_region
            attack_where = None
            region_markers = (" on ", " where ", " in the ", " in ")
            region_marker_idx = -1
            matched_marker = None
            for marker in region_markers:
                idx = cmd.find(marker)
                if idx > 0 and (region_marker_idx < 0 or idx < region_marker_idx):
                    region_marker_idx = idx
                    matched_marker = marker
            if region_marker_idx > 0:
                region_text = cmd[region_marker_idx + len(matched_marker):].strip()
                if region_text:
                    attack_where = resolve_region(region_text) or region_text
                cmd = cmd[:region_marker_idx].strip()
                tokens, _TOKEN_QUOTED = tokenize_command_detailed(cmd)
            with_idx = None
            for i in range(1, len(tokens)):
                if tokens[i] == "with":
                    with_idx = i
                    break
            if with_idx is not None and with_idx > 1:
                target = ' '.join(tokens[1:with_idx])
                weapon_name = ' '.join(tokens[with_idx + 1:]) if with_idx + 1 < len(tokens) else None
            else:
                target = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
                weapon_name = None
            attacker = world.players.get(world.active_player)
            if not attacker:
                add_output("You can't do that.")
            elif target == world.active_player:
                add_output("You can't attack yourself.")
            else:
                target_player = world.players.get(target)
                ambiguous_target = False
                if target_player is None:
                    resolved, candidates = world._match_character_name(target)
                    if resolved:
                        target = resolved
                        target_player = world.players[resolved]
                    elif candidates:
                        ambiguous_target = True
                        note_ambiguity("attack", candidates)
                if target_player:
                    player_in_same_area = (target_player.current_area == world.current_area.name)
                    if player_in_same_area:
                        weapon_node = None
                        if weapon_name:
                            weapon_node = world._find_weapon_in_inventory(world.active_player, weapon_name)
                            if not weapon_node:
                                add_output(f"You don't have a {weapon_name} to attack with.")
                            else:
                                result = world._player_attack(world.active_player, target, weapon_node, where=attack_where)
                                world.record_turn_event(world.active_player, "combat", f"attacked {target}: {result}", area_name=world.current_area.name if world.current_area else None)
                                add_output(result)
                        else:
                            result = world._player_attack(world.active_player, target, where=attack_where)
                            world.record_turn_event(world.active_player, "combat", f"attacked {target}: {result}", area_name=world.current_area.name if world.current_area else None)
                            add_output(result)
                    else:
                        add_output(f"{target} isn't here.")
                elif not ambiguous_target:
                    add_output(f"You don't see {target}.")

        elif cmd.startswith("disarm "):
            rest = ' '.join(tokens[1:]).strip() if len(tokens) > 1 else ""
            item_name = None
            target = rest
            catch_item = False
            if rest.endswith(" and catch"):
                catch_item = True
                rest = rest[:-10].strip()
                target = rest
            from_idx = rest.find(" from ")
            if from_idx > 0:
                item_name = rest[:from_idx].strip() or None
                target = rest[from_idx + 6:].strip()
            attacker = world.players.get(world.active_player)
            if not attacker:
                add_output("You can't do that.")
            elif not target:
                add_output("Disarm whom?")
            else:
                target_player = world.players.get(target)
                resolved_target = target
                ambiguous_target = False
                if target_player is None:
                    resolved, candidates = world._match_character_name(target)
                    if resolved:
                        resolved_target = resolved
                        target_player = world.players[resolved]
                    elif candidates:
                        ambiguous_target = True
                        note_ambiguity("disarm", candidates)
                if target_player is None and not ambiguous_target and from_idx < 0 and " " in rest:
                    parts = rest.split(" ", 1)
                    cand_target = parts[0].strip()
                    cand_item = parts[1].strip()
                    tp = world.players.get(cand_target)
                    if tp is not None:
                        target_player = tp
                        resolved_target = cand_target
                        item_name = cand_item
                    else:
                        r2, c2 = world._match_character_name(cand_target)
                        if r2:
                            resolved_target = r2
                            target_player = world.players[r2]
                            item_name = cand_item
                        elif c2:
                            ambiguous_target = True
                            note_ambiguity("disarm", c2)
                if target_player:
                    if resolved_target == world.active_player:
                        add_output("You can't disarm yourself.")
                    elif target_player.current_area == world.current_area.name:
                        add_output(world._player_disarm(
                            world.active_player, resolved_target,
                            item_name=item_name, catch=catch_item,
                        ))
                    else:
                        add_output(f"{resolved_target} isn't here.")
                elif not ambiguous_target:
                    add_output(f"You don't see {target}.")

        elif cmd.startswith("grab "):
            target = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
            attacker = world.players.get(world.active_player)
            if not attacker:
                add_output("You can't do that.")
            else:
                target_player = world.players.get(target)
                resolved_target = target
                candidates = []
                if target_player is None:
                    resolved, candidates = world._match_character_name(target)
                    if resolved:
                        resolved_target = resolved
                        target_player = world.players[resolved]
                    elif candidates:
                        note_ambiguity("grab", candidates)
                if target_player:
                    from engine.triggers.behaviors import is_character_hidden, reveal_if_hidden
                    if resolved_target == world.active_player:
                        add_output("You can't grab yourself.")
                    elif target_player.current_area == world.current_area.name:
                        if is_character_hidden(world, resolved_target, player=target_player) or (
                            hasattr(world, "player_manager") and not world.player_manager.is_visible(resolved_target)
                        ):
                            add_output(f"You reach for {resolved_target} - but {resolved_target} is not there to grab.")
                        else:
                            rev_msg = reveal_if_hidden(world, world.active_player, reason=f"grabbing {resolved_target}", player=attacker)
                            if rev_msg:
                                add_output(rev_msg)
                            add_output(world._grapple_grab(world.active_player, resolved_target))
                    else:
                        add_output(f"{resolved_target} isn't here.")
                elif not candidates:
                    try:
                        add_output(world.take_item(target))
                    except Exception as grab_err:
                        add_output(str(grab_err))

        elif cmd.split(' ', 1)[0] in _INTIMACY_VERBS or (
                len(cmd.split()) > 1 and cmd.split()[0] in _INTENSITY_ADVERBS
                and cmd.split()[1] in _INTIMACY_VERBS):
            # task-211: intimacy verbs  -  interact-type (never damages),
            # body-part targeted, gated by the mature content toggle.
            from engine.pleasure_actions import parse_intensity, execute_intimacy_action, INTENSITY_ADVERBS
            if not getattr(world, "mature_content", False):
                add_output("That kind of intimacy isn't part of this world.")
            else:
                words = cmd.split()
                leading = None
                if (len(words) > 1 and words[0] in INTENSITY_ADVERBS
                        and words[1] in _INTIMACY_VERBS):
                    # leading adverb ("firmly kiss lydia")  -  strip it here and
                    # carry the intensity through (parse_intensity only sees
                    # the tail below)
                    leading = INTENSITY_ADVERBS[words[0]]
                    cmd = ' '.join(words[1:])
                # task-629: a bare intimate verb ("kiss") has no target, and the
                # unguarded split below raised a raw
                # "not enough values to unpack (expected 2, got 1)" to the player.
                if " " not in cmd.strip():
                    raise ValueError(f"{cmd.strip().capitalize()} whom?")
                verb, rest = cmd.split(' ', 1)
                intensity, rest = parse_intensity(rest)
                if leading and intensity == "normal":
                    intensity = leading
                # Region phrase parsing (earliest marker wins  -  same as attack).
                from engine.body_parts import resolve_region
                where_text = None
                marker_idx, matched_marker = -1, None
                for marker in (" on ", " where ", " in the ", " in "):
                    idx = rest.find(marker)
                    if idx > 0 and (marker_idx < 0 or idx < marker_idx):
                        marker_idx, matched_marker = idx, marker
                if marker_idx > 0:
                    region_text = rest[marker_idx + len(matched_marker):].strip()
                    if region_text:
                        where_text = region_text
                    rest = rest[:marker_idx].strip()
                target = rest.strip()
                if not target:
                    add_output(f"{verb.capitalize()} whom?")
                else:
                    attacker = world.players.get(world.active_player)
                    if not attacker:
                        add_output("You can't do that.")
                    else:
                        target_player = world.players.get(target)
                        resolved_target = target
                        if target_player is None:
                            resolved, candidates = world._match_character_name(target)
                            if resolved:
                                resolved_target = resolved
                                target_player = world.players[resolved]
                            elif candidates:
                                note_ambiguity(verb, candidates)
                                resolved_target = None
                        if resolved_target is not None:
                            if target_player and target_player.current_area == world.current_area.name:
                                result = execute_intimacy_action(
                                    world, world.active_player, verb,
                                    resolved_target, where_text, intensity)
                                world.record_turn_event(world.active_player, "interact", f"{verb} {resolved_target}: {result}", area_name=world.current_area.name if world.current_area else None)
                                add_output(result)
                            else:
                                add_output(f"{target} isn't here.")

        elif cmd.startswith("lead "):
            target = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
            resolved_target = target
            target_player = world.players.get(target)
            lead_ambiguous = False
            if target_player is None and target:
                resolved, candidates = world._match_character_name(target)
                if resolved:
                    resolved_target = resolved
                    target_player = world.players[resolved]
                elif candidates:
                    note_ambiguity("lead", candidates)
                    lead_ambiguous = True
            if not target_player:
                if not lead_ambiguous:
                    add_output(f"Can't lead {target or 'that'}  -  no one by that name is here.")
            elif resolved_target == world.active_player:
                add_output("You can't lead yourself.")
            elif target_player.current_area != world.current_area.name:
                add_output(f"{resolved_target} isn't here.")
            else:
                add_output(world.grapple.lead(world.active_player, resolved_target))

        elif cmd.startswith(("escape", "struggle")):
            add_output(world._grapple_escape(world.active_player))
        elif cmd.startswith("release"):
            target = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
            if target:
                resolved, candidates = world._match_character_name(target)
                if resolved:
                    target = resolved
            add_output(world._grapple_release(world.active_player, target))

        elif cmd.startswith("name "):
            rest = cmd[5:].strip()
            alias = None
            if " as " in rest:
                target_part, alias = rest.rsplit(" as ", 1)
            else:
                parts = rest.rsplit(" ", 1)
                if len(parts) == 2:
                    target_part, alias = parts
                else:
                    target_part = rest
                    alias = None
            if not target_part or not alias:
                add_output("Usage: name <target> <alias>  (or: name <target> as <alias>)")
            else:
                area_id = world._get_current_area_id()
                if not area_id:
                    add_output("You can't name things in an empty void.")
                else:
                    char_name, _ = world._match_character_name(target_part)
                    if char_name:
                        node_id = world._player_node_id(char_name)
                        node = world.graph.get_node(node_id)
                        if node:
                            aliases = node.properties.get("aliases", [])
                            if isinstance(aliases, str):
                                aliases = [a.strip() for a in aliases.split(",") if a.strip()]
                            low_aliases = [a.lower() for a in aliases]
                            if alias.lower() not in low_aliases:
                                aliases.append(alias)
                                node.properties["aliases"] = aliases
                                add_output(f"You start calling {char_name} '{alias}'.")
                            else:
                                add_output(f"{char_name} is already known as '{alias}'.")
                        else:
                            add_output("You can't name that.")
                    else:
                        item_name = world._match_item_name(target_part)
                        if item_name:
                            found = None
                            for edge in world.graph.get_edges_for_target(area_id, EDGE_IN):
                                node = world.graph.get_node(edge.source)
                                if node and node.type == "item" and node.name == item_name:
                                    found = node
                                    break
                            if found is None:
                                player_id = world._player_node_id(world.active_player)
                                for edge in world.graph.get_edges_for_target(player_id, 'carrying') + world.graph.get_edges_for_target(player_id, 'equipped'):
                                    node = world.graph.get_node(edge.source)
                                    if node and node.type == "item" and node.name == item_name:
                                        found = node
                                        break
                            if found:
                                aliases = found.properties.get("aliases", [])
                                if isinstance(aliases, str):
                                    aliases = [a.strip() for a in aliases.split(",") if a.strip()]
                                low_aliases = [a.lower() for a in aliases]
                                if alias.lower() not in low_aliases:
                                    aliases.append(alias)
                                    found.properties["aliases"] = aliases
                                    add_output(f"You start calling the {item_name} '{alias}'.")
                                else:
                                    add_output(f"The {item_name} is already known as '{alias}'.")
                            else:
                                add_output("You can't name that.")
                        else:
                            add_output("You don't see anyone or anything by that name.")

        elif cmd.startswith("label "):
            rest = cmd[6:].strip()
            parts = rest.rsplit(" ", 1)
            if len(parts) != 2:
                add_output("Usage: label <person> <relationship>")
            else:
                person_part, label = parts
                if not person_part or not label:
                    add_output("Usage: label <person> <relationship>")
                else:
                    area_id = world._get_current_area_id()
                    if not area_id:
                        add_output("You can't label relationships in an empty void.")
                    else:
                        char_name, _ = world._match_character_name(person_part)
                        if char_name:
                            player = world.player_manager.get_active_player_obj()
                            # `label` is a declaration, not a measurement, so it
                            # writes no closeness (task-420)  -  only the record.
                            from engine.relationships import ensure_relationship
                            rel, _ = ensure_relationship(player, char_name, world.time_ticks)
                            rel["label"] = label
                            add_output(f"You now consider {char_name} your {label}.")
                        else:
                            add_output("You don't see anyone by that name.")

        elif cmd == "goal" or cmd.startswith("goal "):
            # task-809: goals are character-private data, created and changed at
            # runtime from a free action. A goal is a want, never a world change,
            # so nothing here needs a target or a check.
            from engine import goals as _goals
            player = world.player_manager.get_active_player_obj()
            # `cmd` is lower-cased by the dispatcher; read the raw command so a
            # runtime goal keeps the player's capitalisation.
            rest = (data.get("action") or "").strip()[4:].strip()
            if not rest:
                add_output(_goals.describe(player.goals))
            else:
                sub, _, arg = rest.partition(" ")
                sub = sub.strip().lower()
                arg = arg.strip()
                if sub in ("set", "add", "want"):
                    if not arg:
                        add_output("Usage: goal set <what you want>")
                    else:
                        new, error = _goals.set_goal(player.goals, arg, tick=world.time_ticks, log=player.goal_log)
                        if error:
                            add_output(error)
                        else:
                            player.goals = new
                            add_output(f"You set a goal: {arg}.")
                elif sub in ("complete", "done", "achieve", "reached"):
                    new, error = _goals.set_status(player.goals, arg, "reached", tick=world.time_ticks, log=player.goal_log)
                    if error:
                        add_output(error)
                    else:
                        player.goals = new
                        add_output(f"Goal reached: {arg}.")
                elif sub in ("drop", "abandon", "forget"):
                    new, error = _goals.set_status(player.goals, arg, "dropped", tick=world.time_ticks, log=player.goal_log)
                    if error:
                        add_output(error)
                    else:
                        player.goals = new
                        add_output(f"You dropped the goal: {arg}.")
                else:
                    add_output("Usage: goal [set <what> | complete <goal> | drop <goal>]")

        elif cmd in ("plan", "replan") or cmd.startswith(("plan ", "replan ")):
            # task-984: planning is a character-initiated free mental verb.
            parts = cmd.split(None, 1)
            intent = parts[1].strip() if len(parts) > 1 else ""
            if intent:
                add_output(f"You pause to gather your thoughts and plan: {intent}.")
            else:
                add_output("You pause to gather your thoughts and form a plan.")

        elif cmd == "schedule" or cmd.startswith("schedule "):
            # task-814: a schedule you cannot change is a script, not a life. The
            # character edits its own routine; the tick picks it up unchanged.
            from engine import schedule as _schedule
            player = world.player_manager.get_active_player_obj()
            rest = (data.get("action") or "").strip()[len("schedule"):].strip()
            if not rest:
                add_output(_schedule.describe(player.schedule))
            else:
                sub, _, arg = rest.partition(" ")
                sub = sub.strip().lower()
                arg = arg.strip()
                if sub in ("add", "set"):
                    if not arg:
                        add_output("Usage: schedule add HH:MM <activity> [at <area>]")
                    else:
                        parts = arg.split(None, 1)
                        start = parts[0]
                        activity = parts[1] if len(parts) > 1 else ""
                        area = ""
                        if " at " in activity:
                            activity, _, area = activity.partition(" at ")
                        steps, error = _schedule.add_step(
                            player.schedule, start, activity.strip(), area=area.strip())
                        if error:
                            add_output(error)
                        else:
                            player.schedule = steps
                            add_output(f"Scheduled: {_schedule.describe(steps)}")
                elif sub in ("remove", "drop", "clear"):
                    steps, error = _schedule.remove_step(player.schedule, arg)
                    if error:
                        add_output(error)
                    else:
                        player.schedule = steps
                        add_output(f"Schedule now: {_schedule.describe(steps)}")
                else:
                    add_output("Usage: schedule [add HH:MM <activity> [at <area>] | remove HH:MM]")

        elif cmd.startswith("offer "):
            # task-896: an explicit, targeted offer. `offer <who>: <charge> [due <tick>]`.
            # The record is written onto the recipient; nothing else creates one.
            from engine import goals as _goals
            rest = (data.get("action") or "").strip()[len("offer"):].strip()
            who, sep, charge = rest.partition(":")
            due = 0
            m_due = re.search(r"\s+due\s+(\d+)\s*$", charge)
            if m_due:
                due = int(m_due.group(1))
                charge = charge[:m_due.start()]
            if not sep or not who.strip() or not charge.strip():
                add_output("Offer what to who? Use: offer <character>: <what you ask> [due <tick>]")
            else:
                record, error = _goals.issue_offer(
                    world, world.active_player, who.strip(), charge.strip(), due=due)
                if error:
                    add_output(error)
                else:
                    world.add_log_entry(
                        f"[Offer] {world.active_player} asks {who.strip()}: {record['charge']}")
                    add_output(f"You offer {who.strip()}: {record['charge']}.")

        elif cmd == "obligation" or cmd.startswith("obligation "):
            # task-813: an obligation is the O of MOSIAC - an input the character
            # answers. Accepting is what spawns a goal.
            from engine import goals as _goals
            player = world.player_manager.get_active_player_obj()
            rest = (data.get("action") or "").strip()[len("obligation"):].strip()
            if not rest:
                add_output(_goals.describe_obligations(player.obligations))
            else:
                sub, _, arg = rest.partition(" ")
                sub = sub.strip().lower()
                arg = arg.strip()
                if sub in ("accept", "refuse", "decline", "forget", "alter", "done", "complete"):
                    obs, goal_list, error = _goals.respond_obligation(
                        player.obligations, arg, sub,
                        goals=player.goals, tick=world.time_ticks, log=player.goal_log)
                    if error:
                        add_output(error)
                    else:
                        player.obligations = obs
                        player.goals = goal_list
                        add_output(f"You {sub} the obligation: {arg}.")
                else:
                    add_output("Usage: obligation [accept|refuse|forget <charge>]")

        elif cmd.startswith(("bind ", "enchant ")):
            # task-242: agents author item triggers at runtime.
            # Schema: bind <item> <trigger_type>:<effect_type> [json params]
            rest = cmd[len(cmd.split()[0] + " "):].strip()
            parts = rest.split(" ", 1)
            item_name = parts[0].strip() if parts else ""
            spec_and_json = parts[1].strip() if len(parts) > 1 else ""
            # parse spec "on_use:message" + optional trailing JSON params
            type_effect = spec_and_json
            params_json = None
            m = re.search(r'(\{.*\})$', spec_and_json, re.DOTALL)
            if m:
                params_json = m.group(1)
                type_effect = spec_and_json[:m.start()].strip()
            parts2 = type_effect.split(":", 1)
            trigger_type = parts2[0].strip() if parts2 else "on_use"
            effect_type = parts2[1].strip() if len(parts2) > 1 else "message"
            if not item_name:
                add_output("Bind what? e.g. bind the locket on_take:message")
            else:
                try:
                    from engine.triggers.constants import TRIGGER_TYPES, SAFE_EFFECT_TYPES
                    item_id = world._match_item_name(item_name)
                    item_node = world.graph.get_node(item_id) if item_id else None
                    if item_node is None:
                        # fall back to id / name substring on graph nodes
                        for n in world.graph.nodes.values():
                            if n.type == 'item' and (n.name or '').lower() == item_name.lower():
                                item_node = n
                                break
                        if item_node is None:
                            for n in world.graph.nodes.values():
                                if n.type == 'item' and item_name.lower() in (n.name or '').lower():
                                    item_node = n
                                    break
                    if item_node is None:
                        add_output(f"'{item_name}' isn't something you can bind.")
                    else:
                        if trigger_type and trigger_type not in TRIGGER_TYPES:
                            add_output(f"Unknown trigger '{trigger_type}'  -  allowed: {', '.join(TRIGGER_TYPES)}.")
                        elif effect_type and effect_type not in SAFE_EFFECT_TYPES:
                            add_output(f"Can't bind effect '{effect_type}'  -  allowed: {', '.join(sorted(SAFE_EFFECT_TYPES))}.")
                        else:
                            params = {}
                            if params_json:
                                try:
                                    params = json.loads(params_json)
                                    if not isinstance(params, dict):
                                        params = {}
                                except Exception:
                                    params = {}
                            trigger_id = world.triggers.create_trigger(
                                item_node.id, trigger_type,
                                effects=[{"type": effect_type, "params": params}],
                            )
                            add_output(f"You bind {item_node.name}: it will {trigger_type.replace('_', ' ')} → {effect_type.replace('_', ' ')}.")
                            world.add_log_entry(f"[{world.active_player}] bound a {trigger_type} trigger on {item_node.name} ({effect_type}).")
                except Exception as bind_err:
                    logger.exception("bind trigger failed")
                    add_output(f"The binding fails: {bind_err}")

        elif cmd.startswith(("speak ", "say ", "whisper ", "shout ", "scream ", "sing ")):
            if not world.conditions.can_speak(world.active_player):
                failed = True
                add_output("You try to speak, but no sound comes out.")
            else:
                whisper_target = None
                # RAW command suffix, NOT re-joined tokens  -  the tokenizer treats
                # apostrophes as quote delimiters and would turn "i'm coming" into
                # "i m coming" (N2  -  the mangled text was what got spoken/stored).
                speech = ""
                for _pfx in ("speak ", "say ", "whisper ", "shout ", "scream ", "sing "):
                    if cmd.startswith(_pfx):
                        speech = cmd[len(_pfx):].strip()
                        break
                # Human-typed quoted lines: unwrap ONLY when the whole line is wrapped
                explicit_lang = None
                lang_match = re.match(r'^\[lang:([^\]]+)\]\s*(.+)$', speech, re.IGNORECASE | re.DOTALL)
                if lang_match:
                    explicit_lang = lang_match.group(1).strip()
                    speech = lang_match.group(2).strip()
                if len(speech) >= 2 and ((speech[0] == '"' and speech[-1] == '"')
                                         or (speech[0] == "'" and speech[-1] == "'")):
                    speech = speech[1:-1].strip()
                if cmd.startswith("whisper "):
                    speech_level = "whisper"
                    target_match = re.match(r'^to\s+([^:]+?)(?:\s*:\s*|\s+)(.+)$', speech, re.DOTALL)
                    if target_match:
                        whisper_target = target_match.group(1).strip()
                        speech = target_match.group(2).strip()
                elif cmd.startswith("shout "):
                    speech_level = "shout"
                elif cmd.startswith("scream "):
                    speech_level = "scream"
                elif cmd.startswith("sing "):
                    speech_level = "sing"
                else:
                    speech_level = "normal"
                if speech:
                    if speech_level in ("shout", "scream", "sing"):
                        from engine.triggers.behaviors import reveal_if_hidden
                        rev_msg = reveal_if_hidden(world, world.active_player, reason=speech_level)
                        if rev_msg:
                            add_output(rev_msg)
                    world.broadcast_speech(
                        world.active_player,
                        speech,
                        speech_level=speech_level,
                        whisper_target=whisper_target,
                        lang=explicit_lang,
                    )
                    if speech_level == "whisper":
                        if whisper_target:
                            add_output(f'[{world.active_player}] whispers to {whisper_target}: "{speech}"')
                        else:
                            add_output(f'[{world.active_player}] whispers: "{speech}"')
                    elif speech_level == "shout":
                        add_output(f'[{world.active_player}] shouts: "{speech}"')
                    elif speech_level == "scream":
                        add_output(f'[{world.active_player}] screams: "{speech}"')
                    elif speech_level == "sing":
                        add_output(f'[{world.active_player}] sings: "{speech}"')
                    else:
                        add_output(f'[{world.active_player}] says: "{speech}"')
                else:
                    add_output("You try to speak, but nothing comes out.")

        elif cmd.startswith("call "):
            target_contact = cmd[5:].strip()
            if not target_contact:
                add_output("Use: call <contact>")
                failed = True
            else:
                try:
                    res = world.initiate_call(world.active_player, target_contact)
                    add_output(res)
                except Exception as e:
                    add_output(str(e))
                    failed = True

        elif cmd in ("answer", "answer phone", "answer call"):
            try:
                res = world.answer_call(world.active_player)
                add_output(res)
            except Exception as e:
                add_output(str(e))
                failed = True

        elif cmd in ("hangup", "hang up", "end call"):
            try:
                res = world.end_call(world.active_player)
                add_output(res)
            except Exception as e:
                add_output(str(e))
                failed = True

        elif cmd.startswith(("text ", "message ")):

            prefix = "text " if cmd.startswith("text ") else "message "
            raw_cmd_unlowered = data.get('action', '').strip()
            raw_body = raw_cmd_unlowered[len(prefix):].strip() if raw_cmd_unlowered.lower().startswith(prefix) else original_cmd[len(prefix):].strip()
            if not raw_body or " " not in raw_body:
                add_output("Use: text <contact|#channel> <message>")
                failed = True
            else:
                actor_name = world.active_player
                from engine.long_distance_comms import deliver_dm_text, find_active_comms_device
                active_device, any_device = find_active_comms_device(world, actor_name)
                if not any_device:
                    add_output("You don't have a phone or communication device to send a message.")
                    failed = True
                elif not active_device:
                    add_output(f"Your {any_device.name} is out of power or turned off.")
                    failed = True
                else:
                    target_token, msg_text = raw_body.split(" ", 1)
                    target_token = target_token.strip()
                    msg_text = msg_text.strip()
                    if len(msg_text) >= 2 and ((msg_text[0] == '"' and msg_text[-1] == '"') or (msg_text[0] == "'" and msg_text[-1] == "'")):
                        msg_text = msg_text[1:-1].strip()

                    commons = getattr(world, "commons", None)
                    if not commons:
                        from engine.commons import Commons
                        world.commons = Commons()
                        commons = world.commons

                    if target_token.startswith("#"):
                        channel_name = target_token[1:]
                        channel_id = None
                        for cid, ch in commons.channels.items():
                            if ch.get("name", "").lower() == channel_name.lower() or cid.lower() == channel_name.lower():
                                channel_id = cid
                                break
                        if not channel_id:
                            other_members = [p for p in world.player_manager.players.keys() if p != actor_name]
                            new_ch = commons.create_group(actor_name, channel_name, other_members or ["Everyone"])
                            channel_id = new_ch["id"]
                        commons.post_message(author=actor_name, text=msg_text, tick=getattr(world, "time_ticks", 0), channel_id=channel_id)
                        add_output(f'You posted to #{channel_name}: "{msg_text}"')
                    else:
                        matched_name, candidates = world._match_character_name(target_token, exclude_self=True)
                        if not matched_name:
                            for p_name in world.player_manager.players:
                                if target_token.lower() in p_name.lower():
                                    matched_name = p_name
                                    break
                        if not matched_name:
                            add_output(f"You cannot find contact '{target_token}'.")
                            failed = True
                        else:
                            dm_res = deliver_dm_text(
                                world,
                                actor_name,
                                matched_name,
                                msg_text,
                                tick=getattr(world, "time_ticks", 0),
                            )
                            if dm_res["delivered"]:
                                add_output(f'You texted {matched_name}: "{msg_text}"')
                            else:
                                add_output(f'You texted {matched_name}: "{msg_text}" (queued; recipient phone is off or unreachable)')

        elif cmd.startswith("do "):
            emote_text = cmd[3:].strip()
            if not emote_text:
                add_output("Do what?")
            else:
                result = world.process_emote(world.active_player, emote_text)
                add_output(result)
        else:
            bare = cmd.strip()
            # task-629: a bare verb wants a target -- say so rather than
            # emote-processing the word and echoing "player_human_explorer go."
            if " " not in bare and bare.lower() in _VERBS_NEEDING_TARGET:
                add_output(f"{bare.capitalize()} what?")
                failed = True
            elif bare:
                result = world.process_emote(world.active_player, bare)
                add_output(result)

    except ValueError as e:
        failed = True
        add_output(str(e))
    except Exception as e:
        logger.exception("Unexpected error in /api/action")
        world.player_manager.active_player = prev_active
        return jsonify({"error": "Internal server error"}), 500

    world.player_manager.active_player = prev_active

    response = {"output": "\n".join(output_lines), "success": not failed}
    if choice_groups:
        # task-448: structured chooser for the client; the readable list is
        # already in the output text.
        response["choices"] = choice_groups
    if hasattr(world, 'scenario_ended') and world.scenario_ended:
        response["scenario_ended"] = True
        if hasattr(world, '_restart_requested') and world._restart_requested:
            response["_restart_requested"] = True
            world._restart_requested = False
        world.scenario_ended = False
    if world._fuzzy_match_note:
        response["system_messages"] = [world._fuzzy_match_note]
        world._fuzzy_match_note = None
    return jsonify(response)


def handle_process_emote(app):
    data = request.get_json()
    if not data or 'emote' not in data:
        return jsonify({"error": "Missing 'emote' in request body"}), 400

    actor = data.get('actor', app.world.active_player)
    emote_text = data['emote'].strip()
    if not emote_text:
        return jsonify({"error": "Emote text is empty"}), 400

    try:
        description = app.world.process_emote(actor, emote_text)
        return jsonify({"description": description})
    except Exception as e:
        logger.exception("Error processing emote")
        return jsonify({"error": str(e)}), 500


def handle_apply_turn_decay(app):
    try:
        app.world.tick_turn()
        return jsonify({"status": "success", "turn_number": app.world.turn_number, "time_ticks": app.world.time_ticks})
    except Exception as e:
        logger.exception("Error in /api/turn/apply")
        return jsonify({"error": str(e)}), 500


def handle_clear_turn_events(app):
    app.world.clear_turn_events()
    return jsonify({"status": "success", "turn_number": app.world.turn_number})
