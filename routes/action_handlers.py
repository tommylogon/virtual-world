import logging
import re
import json
from flask import request, jsonify
from virtual_world_engine import AmbiguousItemError
from graph import EDGE_IN, Edge
from engine.activities import (
    ACTIVITY_BLOCKING, ACTIVITY_INTERRUPTIBLE, activity_description,
)
from engine.vitals import format_vitals_readout, VITAL_POLARITY
from routes.helpers import tokenize_command_detailed

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
            return f"You're {activity_description(activity)} — you can't do that right now."
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
    return "You can't move or act right now — a condition holds you motionless."


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
        state = app.world.to_dict()
        state["scenario_ended"] = getattr(app.world, 'scenario_ended', False)
        state["_restart_requested"] = getattr(app.world, '_restart_requested', False)
        state["vital_polarity"] = VITAL_POLARITY
        # task-330: pending browser-side LLM responses (llm_respond effect).
        state["llm_pending"] = list(getattr(app.world, 'llm_pending_requests', []) or [])
        # task-228/229/227: calendar + sky state for widgets and agents.
        try:
            state["game_day"] = int(app.world.game_day)
            state["game_month"] = int(app.world.game_month)
            state["game_year"] = int(app.world.game_year)
            state["calendar_config"] = dict(getattr(app.world, "calendar_config", {}) or {})
            moon = app.world.current_moon_phase()
            moon["game_day"] = int(app.world.game_day)
            state["moon_phase"] = moon
            state["forecast_schedule"] = dict(getattr(app.world, "forecast_schedule", {}) or {})
            state["forecast_override"] = dict(getattr(app.world, "forecast_override", {}) or {}) \
                if getattr(app.world, "forecast_override", None) else None
        except Exception:
            pass
        return jsonify(state)
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


def handle_take_action(app):
    data = request.get_json()
    if not data or 'command' not in data:
        return jsonify({"error": "Missing 'command' in request body"}), 400

    cmd = data['command'].strip().lower()
    original_cmd = cmd
    world = app.world
    prev_active = world.player_manager.active_player
    if 'character' in data:
        world.player_manager.active_player = data['character']
    output_lines = []
    world._action_time_consumed = False
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

        gate_msg = _activity_gate(cmd, world, add_output)
        if gate_msg:
            raise ValueError(gate_msg)

        cond_block_msg = _action_block_gate(cmd, world, add_output)
        if cond_block_msg:
            raise ValueError(cond_block_msg)

        # T1: movement result handling. An intra-room positioning ("go the
        # booth table") does NOT change areas — the movement line is the whole
        # story, so the full room description only re-dumps on a real
        # transition (the agent already has the room in its context).
        def _move_and_describe(call):
            _prev = world.current_area.name if world.current_area else None
            _msg = call()
            add_output(_msg)
            if world.current_area and _prev != world.current_area.name:
                add_output(world.get_area_description())

        if world.current_area and cmd in [e.lower() for e in world.current_area.exits.keys()]:
            was_movement = True
            _move_and_describe(lambda: world.move_to_area(cmd))

        elif cmd.startswith("go "):
            was_movement = True
            direction = ' '.join(tokens[1:]) if len(tokens) > 1 else cmd[3:].strip()
            _move_and_describe(lambda: world.move_to_area(direction))

        elif cmd.startswith("approach "):
            was_movement = True
            target = ' '.join(tokens[1:]) if len(tokens) > 1 else cmd[9:].strip()
            _move_and_describe(lambda: world.approach(target))

        elif cmd.startswith("dash "):
            was_movement = True
            direction = ' '.join(tokens[1:]) if len(tokens) > 1 else cmd[5:].strip()
            _move_and_describe(lambda: world.dash_to_area(direction))

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
                toilet_found = False
                if world.current_area:
                    area_id = world._get_current_area_id()
                    for edge in list(world.graph.get_edges_for_target(area_id, EDGE_IN)):
                        node = world.graph.get_node(edge.source)
                        if node and node.type == "item":
                            tags = node.properties.get("tags", [])
                            if "toilet" in tags or "bathroom" in tags:
                                toilet_found = True
                                break
                    if not toilet_found:
                        # Some areas are restrooms without a Toilet item — the
                        # area's own tags count too.
                        area_node = world.graph.get_node(area_id)
                        if area_node:
                            atags = [str(t).lower() for t in (area_node.properties.get("tags") or [])]
                            if any(t in atags for t in ("restroom", "bathroom", "toilet")):
                                toilet_found = True
                if toilet_found:
                    add_output("You relieve yourself. Ah, much better.")
                else:
                    area_node = world.graph.get_node(world._get_current_area_id())
                    if area_node:
                        env = area_node.properties.get("environment")
                        if env is not None:
                            existing = env.get("smell", "")
                            env["smell"] = (existing + "; urine" if existing else "urine")
                    # T4: public relieve is a shame event — an internal hit
                    # always (Sanity), a social hit only when someone actually
                    # witnesses it (being alone keeps it between you and the
                    # puddle).
                    try:
                        player.vitals["Sanity"] = max(0, min(100, player.vitals.get("Sanity", 100) - 2))
                        area_name = world.current_area.name if world.current_area else None
                        witnessed = [
                            n for n, o in world.player_manager.players.items()
                            if n != world.active_player
                            and o.current_area == area_name
                            and o.state != "dead"
                        ]
                        if witnessed:
                            player.vitals["Social"] = max(0, min(100, player.vitals.get("Social", 100) - 3))
                    except Exception:
                        pass
                    world.effects.execute(
                        "spawn_item",
                        {"item_id": "puddle"},
                        {},
                        game_state=world,
                    )
                    add_output("You relieve yourself in a corner. That's going to stink up the place.")
            else:
                add_output("You don't feel the need.")
            was_movement = False

        elif cmd.startswith("use "):
            # task-196: "use 2 kindling in fireplace" — quantity on use-on.
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
                if not hidden_found and not success:
                    add_output(
                        "You search the room thoroughly "
                        "but find nothing hidden."
                    )
                world._add_entertainment_gain(5)

        elif cmd.startswith("find"):
            area_id = world._get_current_area_id()
            if not area_id:
                add_output("You look around but can't focus.")
            else:
                explicit_tag = ' '.join(tokens[1:]).strip() if len(tokens) > 1 else None
                if explicit_tag:
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
                        add_output(f"You don't know exactly who that is. Do you mean: {', '.join(candidates)}?")
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

        elif cmd.startswith("grab "):
            target = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
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
                if target_player:
                    if resolved_target == world.active_player:
                        add_output("You can't grab yourself.")
                    elif target_player.current_area == world.current_area.name:
                        add_output(world._grapple_grab(world.active_player, resolved_target))
                    else:
                        add_output(f"{resolved_target} isn't here.")
                else:
                    try:
                        add_output(world.take_item(target))
                    except Exception as grab_err:
                        add_output(str(grab_err))

        elif cmd.startswith("lead "):
            target = ' '.join(tokens[1:]) if len(tokens) > 1 else ""
            resolved_target = target
            target_player = world.players.get(target)
            if target_player is None and target:
                resolved, candidates = world._match_character_name(target)
                if resolved:
                    resolved_target = resolved
                    target_player = world.players[resolved]
            if not target_player:
                add_output(f"Can't lead {target or 'that'} — no one by that name is here.")
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
                            add_output(f"Unknown trigger '{trigger_type}' — allowed: {', '.join(TRIGGER_TYPES)}.")
                        elif effect_type and effect_type not in SAFE_EFFECT_TYPES:
                            add_output(f"Can't bind effect '{effect_type}' — allowed: {', '.join(sorted(SAFE_EFFECT_TYPES))}.")
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
                # RAW command suffix, NOT re-joined tokens — the tokenizer treats
                # apostrophes as quote delimiters and would turn "i'm coming" into
                # "i m coming" (N2 — the mangled text was what got spoken/stored).
                speech = ""
                for _pfx in ("speak ", "say ", "whisper ", "shout ", "scream ", "sing "):
                    if cmd.startswith(_pfx):
                        speech = cmd[len(_pfx):].strip()
                        break
                # Human-typed quoted lines: unwrap ONLY when the whole line is wrapped
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
                    world.broadcast_speech(world.active_player, speech, speech_level=speech_level, whisper_target=whisper_target)
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

        elif cmd.startswith("do "):
            emote_text = cmd[3:].strip()
            if not emote_text:
                add_output("Do what?")
            else:
                result = world.process_emote(world.active_player, emote_text)
                add_output(result)
        else:
            emote_text = cmd.strip()
            if emote_text:
                result = world.process_emote(world.active_player, emote_text)
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
