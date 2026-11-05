"""Long-distance communication system for devices, radios, walkie-talkies, and phones.

@module engine/long_distance_comms - communication channels, directed calls, and relays
@contributes comms channel speech relay, phone call state machine, and speakerphone mechanics
@docs docs/virtualWorld/Gameplay/The Commons.md
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from graph import EDGE_CARRYING, EDGE_EQUIPPED, EDGE_IN, Node


def is_device_active(graph, device_node: Node) -> bool:
    """Check if a communication device is functional and has charge.

    Returns False if the device or any child power part is depleted (uses == 0)
    or in an inactive state (unlit, off, dead, spent).
    """
    if device_node is None:
        return False

    props = device_node.properties or {}
    uses = props.get("uses", -1)
    if uses == 0:
        return False

    current_state = str(props.get("current_state", "")).lower()
    if current_state in ("unlit", "off", "dead", "spent"):
        return False

    # Check child parts (connected via EDGE_IN to this device)
    if graph is not None:
        edges = graph.get_edges_for_target(device_node.id, EDGE_IN)
        has_power_source = False
        power_source_depleted = False
        for edge in edges:
            child = graph.get_node(edge.source)
            if not child:
                continue
            cprops = child.properties or {}
            ctags = [str(t).lower() for t in cprops.get("tags", [])]
            if "power_source" in ctags or "battery" in ctags:
                has_power_source = True
                c_uses = cprops.get("uses", -1)
                c_state = str(cprops.get("current_state", "")).lower()
                if c_uses == 0 or c_state in ("unlit", "off", "dead", "spent"):
                    power_source_depleted = True

        if power_source_depleted:
            return False

        # If device requires battery part but none is present
        dtags = [str(t).lower() for t in props.get("tags", [])]
        if ("requires_battery" in dtags or props.get("requires_battery")) and not has_power_source:
            return False

    return True


def get_device_comms_channel(graph, device_node: Node) -> Optional[str]:
    """Retrieve the communication channel declared on the device or its parts."""
    if device_node is None:
        return None

    props = device_node.properties or {}
    if "comms_channel" in props and props["comms_channel"]:
        return str(props["comms_channel"]).strip()
    if "channel" in props and props["channel"]:
        return str(props["channel"]).strip()

    # Check tags on parent device
    for tag in props.get("tags", []):
        tag_str = str(tag).strip()
        if tag_str.startswith("channel:"):
            return tag_str.split(":", 1)[1].strip()
        if tag_str.startswith("comms:"):
            return tag_str.split(":", 1)[1].strip()

    # Check child parts (e.g. channel tuner / radio part)
    if graph is not None:
        for edge in graph.get_edges_for_target(device_node.id, EDGE_IN):
            child = graph.get_node(edge.source)
            if not child:
                continue
            cprops = child.properties or {}
            if "comms_channel" in cprops and cprops["comms_channel"]:
                return str(cprops["comms_channel"]).strip()
            if "channel" in cprops and cprops["channel"]:
                return str(cprops["channel"]).strip()
            for tag in cprops.get("tags", []):
                tag_str = str(tag).strip()
                if tag_str.startswith("channel:"):
                    return tag_str.split(":", 1)[1].strip()
                if tag_str.startswith("comms:"):
                    return tag_str.split(":", 1)[1].strip()

    return None


def get_device_speakerphone(graph, device_node: Node) -> bool:
    """Return whether the device has speakerphone enabled."""
    if device_node is None:
        return False
    props = device_node.properties or {}
    if props.get("speakerphone") is True:
        return True
    if str(props.get("current_state", "")).lower() == "speakerphone":
        return True
    dtags = [str(t).lower() for t in props.get("tags", [])]
    if "speakerphone" in dtags:
        return True

    # Check child parts
    if graph is not None:
        for edge in graph.get_edges_for_target(device_node.id, EDGE_IN):
            child = graph.get_node(edge.source)
            if not child:
                continue
            cprops = child.properties or {}
            if cprops.get("speakerphone") is True or str(cprops.get("current_state", "")).lower() == "speakerphone":
                return True
            ctags = [str(t).lower() for t in cprops.get("tags", [])]
            if "speakerphone" in ctags:
                return True
    return False


def get_carried_devices(graph, player_manager, player_name: str) -> List[Node]:
    """Get all communication-capable devices carried or equipped by a player."""
    if not graph or not player_manager:
        return []
    p_id = getattr(player_manager, "_player_node_id", None)
    if callable(p_id):
        node_id = p_id(player_name)
    else:
        node_id = f"player_{player_name.lower().replace(' ', '_')}"

    devices = []
    if not node_id:
        return devices

    edges = graph.get_edges_for_target(node_id, (EDGE_CARRYING, EDGE_EQUIPPED))
    for edge in edges:
        item = graph.get_node(edge.source)
        if item is not None and item.type == "item":
            devices.append(item)
    return devices


def find_comms_transmitters(
    graph, player_manager, speaker_name: str, target_area: str
) -> List[Tuple[Node, Optional[str], Optional[str]]]:
    """Find all active devices transmitting speech for the speaker or room.

    Returns tuples of (device_node, comms_channel, call_partner).
    """
    transmitters = []
    if not graph or not player_manager:
        return transmitters

    # 1. Carried by speaker
    carried = get_carried_devices(graph, player_manager, speaker_name)
    for dev in carried:
        if not is_device_active(graph, dev):
            continue
        channel = get_device_comms_channel(graph, dev)
        call_partner = dev.properties.get("call_partner") or dev.properties.get("active_call")
        if not call_partner:
            sp = player_manager.get_player(speaker_name)
            if sp and getattr(sp, "call_partner", None):
                call_partner = sp.call_partner
        if channel or call_partner:
            transmitters.append((dev, channel, call_partner))

    # 2. Devices in target_area with speakerphone enabled (capture room audio)
    for node in graph.nodes.values():
        if node.type == "item" and is_device_active(graph, node):
            if get_device_speakerphone(graph, node):
                # Check if located in target_area
                area_edges = graph.get_edges_for_source(node.id, EDGE_IN)
                for ae in area_edges:
                    target_node = graph.get_node(ae.target)
                    if target_node and target_node.type == "area" and target_node.name == target_area:
                        channel = get_device_comms_channel(graph, node)
                        call_partner = node.properties.get("call_partner") or node.properties.get("active_call")
                        if channel or call_partner:
                            if not any(t[0].id == node.id for t in transmitters):
                                transmitters.append((node, channel, call_partner))

    return transmitters


def relay_comms_speech(
    broadcaster,
    speaker_name: str,
    speech_text: str,
    event: Dict[str, Any],
    target_area: str,
) -> bool:
    """Relay spoken dialogue over comms channels or active phone calls.

    Returns True if any long-distance transmission was made.
    """
    graph = broadcaster.graph
    player_manager = broadcaster.player_manager
    if not graph or not player_manager:
        return False

    transmitters = find_comms_transmitters(graph, player_manager, speaker_name, target_area)
    if not transmitters:
        return False

    relayed_any = False

    for tx_dev, channel, call_partner in transmitters:
        # 1. Directed call transmission
        if call_partner:
            partner_obj = player_manager.get_player(call_partner)
            if partner_obj:
                partner_carried = get_carried_devices(graph, player_manager, call_partner)
                active_recv_phone = None
                for dev in partner_carried:
                    if is_device_active(graph, dev):
                        active_recv_phone = dev
                        break
                if active_recv_phone is not None:
                    relayed_any = True
                    hearing_entry = dict(event)
                    hearing_entry["heard_via"] = "call"
                    hearing_entry["device"] = active_recv_phone.name
                    hearing_entry["caller"] = speaker_name
                    if not hasattr(partner_obj, "recent_hearing"):
                        partner_obj.recent_hearing = []
                    partner_obj.recent_hearing.append(hearing_entry)
                    if len(partner_obj.recent_hearing) > 20:
                        partner_obj.recent_hearing.pop(0)

                    # If partner has speakerphone enabled, bystanders hear it
                    if get_device_speakerphone(graph, active_recv_phone):
                        p_area = getattr(partner_obj, "current_area", None)
                        for pname, pobj in player_manager.players.items():
                            if pname != call_partner and pname != speaker_name and getattr(pobj, "current_area", None) == p_area:
                                if not hasattr(pobj, "recent_hearing"):
                                    pobj.recent_hearing = []
                                b_entry = dict(event)
                                b_entry["heard_via"] = "speakerphone"
                                b_entry["device"] = active_recv_phone.name
                                pobj.recent_hearing.append(b_entry)
                                if len(pobj.recent_hearing) > 20:
                                    pobj.recent_hearing.pop(0)
                        broadcaster.logging_events.add_log_entry(
                            f'[{active_recv_phone.name}] [{speaker_name}] says: "{speech_text}"'
                        )

        # 2. Radio / walkie-talkie channel broadcast
        if channel:
            for other_node in graph.nodes.values():
                if other_node.type != "item" or other_node.id == tx_dev.id:
                    continue
                if not is_device_active(graph, other_node):
                    continue
                other_ch = get_device_comms_channel(graph, other_node)
                if other_ch != channel:
                    continue

                # Find carrier or location of other_node
                # Check carrying edges
                carrier_name = None
                for edge in graph.get_edges_for_source(other_node.id):
                    if edge.type in (EDGE_CARRYING, EDGE_EQUIPPED):
                        for pname in player_manager.players:
                            pid = player_manager.get_player_node_id(pname)
                            if (
                                edge.target == pid
                                or edge.target == pname
                                or edge.target == f"player_{pname}"
                                or edge.target == f"player_{pname.lower().replace(' ', '_')}"
                            ):
                                carrier_name = pname
                                break
                        if not carrier_name:
                            target_node = graph.get_node(edge.target)
                            if target_node and target_node.type == "character":
                                carrier_name = target_node.name
                if carrier_name:
                    if carrier_name == speaker_name:
                        continue
                    carrier_obj = player_manager.get_player(carrier_name)
                    if carrier_obj:
                        relayed_any = True
                        recv_entry = dict(event)
                        recv_entry["heard_via"] = "comms"
                        recv_entry["comms_channel"] = channel
                        recv_entry["device"] = other_node.name
                        recv_entry["heard_from"] = "radio"
                        if not hasattr(carrier_obj, "recent_hearing"):
                            carrier_obj.recent_hearing = []
                        carrier_obj.recent_hearing.append(recv_entry)
                        if len(carrier_obj.recent_hearing) > 20:
                            carrier_obj.recent_hearing.pop(0)

                        # Speakerphone on receiving device
                        if get_device_speakerphone(graph, other_node):
                            c_area = getattr(carrier_obj, "current_area", None)
                            for pname, pobj in player_manager.players.items():
                                if pname != carrier_name and pname != speaker_name and getattr(pobj, "current_area", None) == c_area:
                                    if not hasattr(pobj, "recent_hearing"):
                                        pobj.recent_hearing = []
                                    b_entry = dict(event)
                                    b_entry["heard_via"] = "speakerphone"
                                    b_entry["comms_channel"] = channel
                                    b_entry["device"] = other_node.name
                                    pobj.recent_hearing.append(b_entry)
                                    if len(pobj.recent_hearing) > 20:
                                        pobj.recent_hearing.pop(0)
                            broadcaster.logging_events.add_log_entry(
                                f'[{other_node.name}] [{speaker_name}] says: "{speech_text}"'
                            )
                            broadcaster.logging_events.record_turn_event(
                                speaker_name,
                                "speak",
                                f'(over {other_node.name}) said: "{speech_text}"',
                                area_name=c_area,
                            )
                else:
                    # Stationed in an area
                    if get_device_speakerphone(graph, other_node):
                        area_name = None
                        for edge in graph.get_edges_for_source(other_node.id):
                            if edge.type == EDGE_IN:
                                an = graph.get_node(edge.target)
                                if an and an.type == "area":
                                    area_name = an.name
                                    break
                        if area_name:
                            relayed_any = True
                            for pname, pobj in player_manager.players.items():
                                if pname != speaker_name and getattr(pobj, "current_area", None) == area_name:
                                    if not hasattr(pobj, "recent_hearing"):
                                        pobj.recent_hearing = []
                                    recv_entry = dict(event)
                                    recv_entry["heard_via"] = "speakerphone"
                                    recv_entry["comms_channel"] = channel
                                    recv_entry["device"] = other_node.name
                                    recv_entry["heard_from"] = "radio"
                                    pobj.recent_hearing.append(recv_entry)
                                    if len(pobj.recent_hearing) > 20:
                                        pobj.recent_hearing.pop(0)
                            broadcaster.logging_events.add_log_entry(
                                f'[{other_node.name}] [{speaker_name}] says: "{speech_text}"'
                            )
                            broadcaster.logging_events.record_turn_event(
                                speaker_name,
                                "speak",
                                f'(over {other_node.name}) said: "{speech_text}"',
                                area_name=area_name,
                            )

                # Fire on_speech triggers on receiving device if present
                if broadcaster.trigger_fn:
                    speech_ctx = {
                        "speech": speech_text,
                        "speaker": speaker_name,
                        "channel": channel,
                        "device": other_node.name,
                        "tick": int(getattr(player_manager, "time_ticks", 0) or 0),
                    }
                    try:
                        if broadcaster.game_state is not None:
                            broadcaster.trigger_fn(other_node, "on_speech", None, speech_ctx, None, broadcaster.game_state)
                        else:
                            broadcaster.trigger_fn(other_node, "on_speech", None, speech_ctx)
                    except Exception:
                        pass

    return relayed_any


def initiate_call(world, caller_name: str, target_name: str, phone_node: Optional[Node] = None) -> str:
    """Initiate a directed phone call from caller to target."""
    if not caller_name or not target_name:
        raise ValueError("Specify who to call.")
    if caller_name.lower() == target_name.lower():
        raise ValueError("You can't call yourself.")

    caller_player = world.player_manager.get_player(caller_name)
    target_player = world.player_manager.get_player(target_name)
    if not target_player:
        # Lenient match
        matched, _ = world._match_character_name(target_name, exclude_self=True)
        if matched:
            target_name = matched
            target_player = world.player_manager.get_player(target_name)
    if not target_player:
        raise ValueError(f"Could not reach '{target_name}'.")

    # Find caller phone
    if phone_node is None:
        carried = get_carried_devices(world.graph, world.player_manager, caller_name)
        for d in carried:
            dtags = [str(t).lower() for t in (d.properties.get("tags", []) or [])]
            if "phone" in dtags or "phone" in (d.name or "").lower():
                phone_node = d
                break
    if not phone_node:
        raise ValueError("You don't have a phone to place a call.")
    if not is_device_active(world.graph, phone_node):
        raise ValueError(f"The {phone_node.name} is out of power.")

    # Find target phone
    target_carried = get_carried_devices(world.graph, world.player_manager, target_name)
    target_phone = None
    for d in target_carried:
        dtags = [str(t).lower() for t in (d.properties.get("tags", []) or [])]
        if "phone" in dtags or "phone" in (d.name or "").lower():
            target_phone = d
            break
    if not target_phone or not is_device_active(world.graph, target_phone):
        return f"You call {target_name}, but there is no answer (device unreachable or off)."

    # Set up ringing state
    phone_node.properties["call_state"] = "calling"
    phone_node.properties["call_partner"] = target_name
    caller_player.call_partner = target_name

    target_phone.properties["call_state"] = "ringing"
    target_phone.properties["incoming_call_from"] = caller_name
    target_phone.properties["current_state"] = "ringing"
    target_player.incoming_call_from = caller_name

    target_area = getattr(target_player, "current_area", None)
    world.record_turn_event(
        target_name,
        "ring",
        f"phone is ringing with a call from {caller_name}",
        area_name=target_area,
    )
    world.add_log_entry(f"[{target_name}'s phone] rings with a call from {caller_name}.")
    return f"You call {target_name}. The phone is ringing..."


def answer_call(world, player_name: str, phone_node: Optional[Node] = None) -> str:
    """Answer an incoming phone call."""
    player = world.player_manager.get_player(player_name)
    if not player:
        raise ValueError(f"Player {player_name} not found.")

    if phone_node is None:
        carried = get_carried_devices(world.graph, world.player_manager, player_name)
        for d in carried:
            dtags = [str(t).lower() for t in (d.properties.get("tags", []) or [])]
            if "phone" in dtags or "phone" in (d.name or "").lower():
                phone_node = d
                break
    if not phone_node:
        raise ValueError("You don't have a phone.")
    if not is_device_active(world.graph, phone_node):
        raise ValueError(f"The {phone_node.name} is out of power.")

    incoming = phone_node.properties.get("incoming_call_from") or getattr(player, "incoming_call_from", None)
    if not incoming:
        raise ValueError("Your phone is not ringing.")

    caller_name = incoming
    caller_player = world.player_manager.get_player(caller_name)

    # Establish call connection
    phone_node.properties["call_state"] = "connected"
    phone_node.properties["call_partner"] = caller_name
    phone_node.properties["incoming_call_from"] = None
    if phone_node.properties.get("current_state") == "ringing":
        phone_node.properties["current_state"] = "lit"
    player.call_partner = caller_name
    player.incoming_call_from = None
    player.add_condition("on_a_call")

    if caller_player:
        caller_player.add_condition("on_a_call")
        caller_player.call_partner = player_name
        caller_carried = get_carried_devices(world.graph, world.player_manager, caller_name)
        for d in caller_carried:
            if d.properties.get("call_partner") == player_name:
                d.properties["call_state"] = "connected"

    world.add_log_entry(f"[Call] {player_name} answered the call from {caller_name}.")
    return f"You answer the call from {caller_name}. You are now on a call."


def end_call(world, player_name: str, phone_node: Optional[Node] = None) -> str:
    """End an active phone call or dismiss a ringing call."""
    player = world.player_manager.get_player(player_name)
    partner_name = getattr(player, "call_partner", None)

    if phone_node is None:
        carried = get_carried_devices(world.graph, world.player_manager, player_name)
        for d in carried:
            dtags = [str(t).lower() for t in (d.properties.get("tags", []) or [])]
            if "phone" in dtags or "phone" in (d.name or "").lower():
                phone_node = d
                break

    if phone_node:
        if not partner_name:
            partner_name = phone_node.properties.get("call_partner")
        phone_node.properties["call_state"] = "idle"
        phone_node.properties["call_partner"] = None
        phone_node.properties["incoming_call_from"] = None
        if phone_node.properties.get("current_state") == "ringing":
            phone_node.properties["current_state"] = "lit"

    if player:
        player.call_partner = None
        player.incoming_call_from = None
        if hasattr(player, "remove_condition"):
            player.remove_condition("on_a_call")

    if partner_name:
        partner_obj = world.player_manager.get_player(partner_name)
        if partner_obj:
            partner_obj.call_partner = None
            if hasattr(partner_obj, "remove_condition"):
                partner_obj.remove_condition("on_a_call")
            partner_carried = get_carried_devices(world.graph, world.player_manager, partner_name)
            for d in partner_carried:
                d.properties["call_state"] = "idle"
                d.properties["call_partner"] = None
                if d.properties.get("current_state") == "ringing":
                    d.properties["current_state"] = "lit"
            world.add_log_entry(f"[Call] {player_name} hung up the call with {partner_name}.")

    return "You hang up the call."


def toggle_speakerphone(world, player_name: str, device_node: Optional[Node] = None) -> str:
    """Toggle speakerphone on a communication device."""
    if device_node is None:
        carried = get_carried_devices(world.graph, world.player_manager, player_name)
        if carried:
            device_node = carried[0]
    if not device_node:
        raise ValueError("You have no communication device to toggle speakerphone on.")

    current = get_device_speakerphone(world.graph, device_node)
    device_node.properties["speakerphone"] = not current
    state_str = "on" if not current else "off"
    return f"You toggle speakerphone {state_str} on the {device_node.name}."


def tune_channel(world, player_name: str, device_node: Node, channel: str) -> str:
    """Tune a radio or comms part to a specific channel."""
    channel = channel.strip()
    if not channel:
        raise ValueError("Specify a valid channel name.")

    device_node.properties["comms_channel"] = channel
    return f"You tune the {device_node.name} to channel '{channel}'."
