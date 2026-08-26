from typing import Any, Dict, List, Optional

from graph import EDGE_CONNECTION, EDGE_IN, EDGE_CARRYING, EDGE_EQUIPPED
from engine.equipment import INTRINSIC_ABILITY_TAGS
from engine.equipment_bonuses import aggregate_bonuses, effective_temperature
from engine.activities import activity_description
from engine.beyond_visibility import build_beyond_suffix, normalize_visible_items
from engine.room_perception import resolve_area_node, visible_area_items, way_visible_to


def _is_intrinsic_ability(node) -> bool:
    """True when an item is an intrinsic ability (spell/talent) rather than a
    physical object — these never appear in what others see."""
    if node is None:
        return False
    tags = node.properties.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    return bool(INTRINSIC_ABILITY_TAGS.intersection(tags))


# ── Authoritative temperature description tables ──

TEMPERATURE_BANDS = [
    (60, "The heat is infernal — you can't breathe.", "You are burning! Seek shelter or die!"),
    (50, "Blazing heat — the air shimmers.", "The heat is cooking you alive!"),
    (40, "Scorching hot.", "The intense heat is draining your energy!"),
    (35, "Very hot.", "You're overheating — find shade or water."),
    (30, "Hot.", "It's quite hot; you're feeling thirsty."),
    (25, "Warm.", ""),
    (18, "Pleasant.", ""),
    (12, "Cool.", ""),
    (5, "Chilly.", ""),
    (0, "Cold.", "The cold is biting."),
    (-10, "Freezing.", "It's freezing! You need to warm up."),
    (-25, "Bitterly cold.", "The cold is sapping your strength."),
    (-50, "Arctic — the cold is lethal.", "Hypothermia is imminent — find warmth now!"),
]


def temperature_description(feels_like: int) -> str:
    """Return a single-sentence description of the feels_like temperature."""
    for threshold, desc, _ in TEMPERATURE_BANDS:
        if feels_like >= threshold:
            return desc
    return "Deadly cold — nothing survives."


def temperature_warning(feels_like: int) -> str:
    """Return a warning string for the feels_like temperature, or empty string."""
    for threshold, _, warn in TEMPERATURE_BANDS:
        if feels_like >= threshold:
            return warn
    return "You are freezing to death!"


LIGHT_BANDS = [
    (90, "blinding"),
    (70, "bright"),
    (40, "normal"),
    (20, "dim"),
]


def light_description(ambient_light: int) -> str:
    """Return a light level label given an ambient light value (0-100)."""
    for threshold, label in LIGHT_BANDS:
        if ambient_light >= threshold:
            return label
    return "pitch_black"


class AreaDescription:
    """Builds area descriptions with lighting, items, environment, players,
    exits, and environmental warnings."""

    def __init__(self, graph, lighting, player_manager, item_actions):
        self.graph = graph
        self.lighting = lighting
        self.player_manager = player_manager
        self.item_actions = item_actions

    def get_current_area_id(self) -> Optional[str]:
        player = self.player_manager.players.get(self.player_manager.active_player)
        if player and player.current_area:
            node = resolve_area_node(self.graph, player.current_area)
            if node is not None:
                return node.id
            return self.player_manager.area_node_id(player.current_area)
        return None

    def _render_node(self, node) -> str:
        """Render a node's description (seeding its ``parameters``) if a real
        ItemActions is wired in; otherwise fall back to the raw description."""
        from engine.item_actions import ItemActions
        if isinstance(self.item_actions, ItemActions):
            return self.item_actions._render_node_desc(node)
        return node.properties.get("description", "") if node else ""

    def get_area_items(self, include_hidden=False) -> List[str]:
        area_id = self.get_current_area_id()
        return [node.name for node in visible_area_items(
            self.graph, area_id, include_hidden=include_hidden)]

    def build_exits_for_area(self, area_name: str) -> Dict[str, Any]:
        """Reconstruct the exits dict for a area from graph connections.
        Filters out hidden exits (undiscovered). Hides back-link directions."""
        area_node = resolve_area_node(self.graph, area_name)
        area_id = area_node.id if area_node is not None else None
        if not area_id:
            area_id = self.player_manager.area_node_id(area_name)
        exits = {}
        from engine.matching import NameMatching
        for edge in self.graph.get_edges_for_source(area_id, EDGE_CONNECTION):
            way_node = self.graph.get_node(edge.target)
            if way_node and way_node.type == "way":
                direction = edge.properties.get("direction", "")
                # A way always has a reference handle: the direction label when
                # set, else a short name derived from the way node's name
                # (e.g. "Task 18 - final door" → "final door"), else "door".
                label = NameMatching.way_handle(
                    way_node, direction, area_name,
                )

                if not way_visible_to(
                        self.player_manager.players.get(self.player_manager.active_player),
                        self.player_manager,
                        self.player_manager.active_player,
                        way_node, area_name, direction):
                    continue

                for conn in self.graph.get_edges_for_source(way_node.id, EDGE_CONNECTION):
                    if conn.target != area_id:
                        target_area_node = self.graph.get_node(conn.target)
                        if target_area_node:
                            exit_data = {
                                "target": target_area_node.name,
                                "return_dir": conn.properties.get("direction", ""),
                                "state": way_node.properties.get("current_state", "closed"),
                                "description": way_node.properties.get("description", ""),
                                "cost": way_node.properties.get("cost", {}),
                                "way_id": way_node.id,
                                "hidden": way_node.properties.get("current_state") == "hidden",
                                "pass_message": way_node.properties.get("pass_message", ""),
                                "visible_in_direction": edge.properties.get("visible_in_direction", ""),
                                "allow_see_characters": bool(edge.properties.get("allow_see_characters")),
                                "visible_items": normalize_visible_items(edge.properties.get("visible_items")),
                                "label": label,
                            }
                            if "cardinal" in edge.properties:
                                exit_data["cardinal"] = edge.properties["cardinal"]
                            exits[label] = exit_data
                            break
        return exits

    def get_area_description(self) -> str:
        if not self.player_manager.current_area:
            return "You are in an empty void."

        active_player_obj = self.player_manager.get_active_player_obj()
        if not active_player_obj:
            return "You are nowhere."
        can_see_in_dark = self.lighting.can_see_in_dark(self.player_manager, self.player_manager.active_player)
        player_is_dead = active_player_obj and active_player_obj.state == "dead"

        env = self.player_manager.current_area.environment
        area_id = self.get_current_area_id()
        ambient_light = self.lighting.get_ambient_light(area_id, env) if area_id else self.lighting.get_light_int(env, 80)
        light_level = self.lighting.light_to_level(ambient_light)

        # task-133: light level flavors what you PERCEIVE. Pitch black still
        # replaces everything (nothing to see); dim now PREFIXES the room text
        # (shapes visible, details lost) instead of hiding it entirely;
        # bright/blinding add their own flavor for everyone — glare spares
        # not even darkvision.
        light_prefix = ""
        if not can_see_in_dark:
            if light_level == 'pitch_black':
                return "It's pitch black. You can't see anything. You should find a way to illuminate this space."
            elif light_level == 'dim':
                light_prefix = "The light is dim — you can just make out the shapes of things here, details lost in shadow."
        if light_level == 'bright':
            light_prefix = "Bright light floods the area, illuminating every detail."
        elif light_level == 'blinding':
            light_prefix = "The light is blinding — you squint against the glare, eyes watering."

        spill_desc = ""
        if area_id:
            own_light = self.lighting.get_light_int(env, 80)
            if ambient_light > own_light:
                best_source = None
                direction_name = ""
                for edge in self.graph.get_edges_for_source(area_id, EDGE_CONNECTION):
                    door = self.graph.get_node(edge.target)
                    if door and door.type == "way" and door.properties.get("current_state") == "open":
                        for conn in self.graph.get_edges_for_source(door.id, EDGE_CONNECTION):
                            if conn.target != area_id:
                                other = self.graph.get_node(conn.target)
                                if other:
                                    best_source = other.name
                                break
                    if best_source:
                        direction_name = edge.properties.get("direction", "")
                        break
                if best_source:
                    level_str = self.lighting.light_to_level(ambient_light)
                    spill_desc = f"\n{level_str.capitalize()} light spills in from the {best_source} through the open {direction_name}."

        desc = self.player_manager.current_area.description
        if area_id and self.graph.get_node(area_id) is not None:
            desc = self._render_node(self.graph.get_node(area_id))
        if light_prefix:
            desc = light_prefix + "\n" + desc
        if spill_desc:
            desc += spill_desc

        item_descs = []
        for edge in self.graph.get_edges_for_target(area_id, EDGE_IN):
            node = self.graph.get_node(edge.source)
            if node and node.type == "item" and node.properties.get("current_state") != "hidden":
                item_desc = self._render_node(node).strip()
                if item_desc:
                    if not item_desc.endswith('.'):
                        item_desc += '.'
                    item_descs.append(item_desc)
        if item_descs:
            desc += "\n\n" + "\n".join(item_descs)

        env_summary = []
        active_player = self.player_manager.players.get(self.player_manager.active_player)
        equip_bonuses = aggregate_bonuses(active_player, self.graph) if active_player else {}
        feels_like = int(effective_temperature(float(env.get("temperature", 21)), equip_bonuses))
        env_summary.append(temperature_description(feels_like))
        air = env.get("air", "fresh")
        if air == "toxic":
            env_summary.append("The air is toxic and acrid.")
        elif air == "stale":
            env_summary.append("The air feels stale and close.")
        elif air == "humid":
            env_summary.append("The air is humid and heavy.")
        elif air == "smoky":
            env_summary.append("The air is thick with smoke.")
        elif air == "fragrant":
            env_summary.append("A pleasant fragrance fills the air.")
        smell = env.get("smell", "neutral")
        if smell not in ("neutral", "fresh", ""):
            env_summary.append(f"A {smell} smell hangs in the air.")
        noise = env.get("noise", "quiet")
        if noise in ("loud", "chaotic"):
            env_summary.append(f"The area is noisy with {noise} sounds.")
        elif noise not in ("quiet", "silent", ""):
            env_summary.append(f"You hear {noise}.")
        if env_summary:
            desc += "\n" + "\n".join(env_summary)

        players_here = self.player_manager.get_players_in_area()
        if players_here:
            lines = []
            for pdata in players_here:
                pname = pdata["name"]
                pstate = pdata.get("state", "awake")
                carried = []
                worn = []
                player_id = self.player_manager.player_node_id(pname)
                for edge in self.graph.get_edges_for_target(player_id, EDGE_CARRYING):
                    node = self.graph.get_node(edge.source)
                    # Intrinsic abilities (spells, talents) never show as "holding"
                    # to other characters (task-171 follow-up).
                    if node and node.type == "item" and not _is_intrinsic_ability(node):
                        carried.append(node.name)
                for edge in self.graph.get_edges_for_target(player_id, EDGE_EQUIPPED):
                    node = self.graph.get_node(edge.source)
                    # Equipped items are worn, not held — shown as "wearing".
                    # If an item is on both edges, only count it as worn.
                    if node and node.type == "item" and not _is_intrinsic_ability(node):
                        worn.append(node.name)
                        if node.name in carried:
                            carried.remove(node.name)
                # Task-154: strangers are presented by appearance, not real name.
                # Task-339: seeing someone again is RECOGNITION, not name
                # knowledge — the name reveals only once heard spoken (or a
                # name tag is read). `first_sighting` now means "name unknown".
                known = active_player_obj is not None and active_player_obj.has_met(pname)
                name_known = False
                if known:
                    rel = active_player_obj.relationships.get(pname) or {}
                    name_known = not rel.get("first_sighting")
                if name_known:
                    line = pname
                else:
                    target_player = self.player_manager.players.get(pname)
                    line = target_player.unknown_display_name() if target_player else pname
                if pstate in ("dead", "ghost"):
                    line += " (ghost)"
                # Task-131: show ongoing activities ("sleeping in the bed")
                activity = getattr(self.player_manager.players.get(pname), 'activity', None)
                if activity and activity.get("visible", True):
                    act_text = activity_description(activity)
                    if act_text:
                        line += f" ({act_text})"
                pdata_desc = pdata.get("description", "") or ""
                # First impression: the first sentence is what you see at a
                # glance, met or not — strangers get it too, so the room reads
                # "the woman — A tall figure in a green cloak" instead of just
                # "the woman". The FULL description (which may name them in
                # prose) is reserved for characters whose name you know.
                if pdata_desc:
                    first_sentence = pdata_desc.split('.')[0].strip() + ('.' if '.' in pdata_desc else '')
                    if name_known:
                        line += f" — {pdata_desc}"
                    else:
                        line += f" — {first_sentence}"
                if worn:
                    line += f" [wearing: {', '.join(worn)}]"
                if carried:
                    line += f" [holding: {', '.join(carried)}]"
                from engine.character_spatial import spatial_position_phrase
                area_name = self.player_manager.current_area.name if self.player_manager.current_area else ""
                viewer = self.player_manager.active_player or ""
                line += spatial_position_phrase(
                    self.graph, player_id, area_id, area_name, viewer, self.player_manager,
                )
                lines.append(line)
                # First time the active character sees this person → register
                # the relationship (recognition: stable masked label, closeness
                # anchor). Registered AFTER the line is built; the NAME is
                # never revealed here — only speech / name tags teach names
                # (task-339).
                if (
                    active_player_obj
                    and pname != self.player_manager.active_player
                    and pstate not in ("dead", "ghost")
                    and hasattr(active_player_obj, "register_first_meeting")
                ):
                    active_player_obj.register_first_meeting(pname, getattr(self.player_manager, "time_ticks", 0) or 0)
            desc += f"\n\n" + "\n".join(lines) + " is here."

        warnings = []
        if not player_is_dead:
            warn_text = temperature_warning(feels_like)
            if warn_text:
                warnings.append(warn_text)
            air = env.get("air", "fresh")
            if air == "toxic":
                warnings.append("WARNING: The air is toxic! You're being damaged.")
            elif air == "stale":
                warnings.append("The air is stale and making you tired.")
            elif air == "humid":
                warnings.append("The humid air is uncomfortable.")
            noise = env.get("noise", "quiet")
            if noise in ["loud", "scratches", "dripping"] and active_player_obj and active_player_obj.state == "sleeping":
                warnings.append("The noise is preventing restful sleep.")
            smell = env.get("smell", "neutral")
            if smell in ["mold", "rot", "rotting food", "urine"]:
                warnings.append("The foul smell is affecting your hygiene.")
        else:
            warnings.append("(You perceive the world as a spirit — the physical sensations of temperature and smell no longer affect you.)")
        if warnings:
            desc += "\n[!] " + " ".join(warnings)

        exits_desc = []
        seen_ways = set()
        area_name = self.player_manager.current_area.name if self.player_manager.current_area else ""
        transit_roles = None
        if area_id and self.player_manager.active_player:
            from engine.character_spatial import get_transit_roles
            pid = self.player_manager.player_node_id(self.player_manager.active_player)
            transit_roles = get_transit_roles(self.graph, area_id, pid, area_name)
        for edge in self.graph.get_edges_for_source(area_id, EDGE_CONNECTION):
            way_id = edge.target
            if way_id in seen_ways:
                continue

            direction = edge.properties.get("direction", "")
            way_node = self.graph.get_node(way_id)
            if way_node and way_node.type == "way":
                from engine.matching import NameMatching
                handle = NameMatching.way_handle(
                    way_node, direction,
                    self.player_manager.current_area.name
                    if self.player_manager.current_area else area_id,
                )
                if transit_roles:
                    if way_id.lower() == transit_roles["back_way"].id.lower():
                        handle = "back"
                    elif way_id.lower() == transit_roles["forward_way"].id.lower():
                        handle = "forward"
                state = way_node.properties.get("current_state", "closed")
                target_name = ""

                is_hidden = way_node.properties.get("current_state") == "hidden"
                if is_hidden:
                    if self.player_manager.active_player and self.player_manager.is_slasher(self.player_manager.active_player):
                        pass
                    elif active_player and hasattr(active_player, 'discovered_exits'):
                        exit_key = (self.player_manager.current_area.name, direction)
                        if exit_key not in active_player.discovered_exits:
                            continue
                    else:
                        continue

                target_area_node = None
                for e2 in self.graph.get_edges_for_source(way_id, EDGE_CONNECTION):
                    if e2.target != area_id:
                        target_area_node = self.graph.get_node(e2.target)
                        if target_area_node:
                            target_name = target_area_node.name
                            break

                beyond_suffix = ""
                if target_area_node and (state == "open" or way_node.properties.get("see_through")):
                    beyond_suffix = build_beyond_suffix(
                        self.graph,
                        self.player_manager,
                        target_area_node.id,
                        target_name,
                        edge.properties,
                        active_player_obj,
                    )

                if state == "open" and target_name:
                    vid = edge.properties.get("visible_in_direction", "") or ""
                    way_tags = {str(t).lower().strip() for t in way_node.properties.get("tags", []) or []}
                    open_word = "is clear" if ("exterior" in way_tags or "natural" in way_tags) else "is open"
                    if vid:
                        exits_desc.append(f"[{handle}] {open_word} — on the other side you can see {vid}{beyond_suffix}")
                    else:
                        target_area = target_area_node
                        if not target_area:
                            for n in self.graph.nodes.values():
                                if n.type == "area" and n.name == target_name:
                                    target_area = n
                                    break
                            if not target_area:
                                target_area = self.graph.get_node(self.player_manager.area_node_id(target_name))
                        env_clues = []
                        if target_area:
                            tenv = target_area.properties.get("environment", {})
                            lv = self.lighting.get_ambient_light(target_area.id, tenv)
                            if lv <= 20:
                                env_clues.append("pitch dark")
                            elif lv <= 40:
                                env_clues.append("dimly lit")
                            elif lv >= 90:
                                env_clues.append("brightly lit")
                            noise = tenv.get("noise", "")
                            if noise and noise not in ("quiet", "silence", "silent"):
                                env_clues.append(f"{noise} audible")
                            target_feels = int(effective_temperature(float(tenv.get("temperature", 21)), equip_bonuses))
                            env_clues.append(temperature_description(target_feels).lower())
                        clue_str = f" ({', '.join(env_clues)})" if env_clues else ""
                        exits_desc.append(f"To the {handle}, the {target_name} is visible beyond{clue_str}.{beyond_suffix}")
                else:
                    vid = edge.properties.get("visible_in_direction", "") or ""
                    if vid and way_node.properties.get("see_through"):
                        exits_desc.append(f"[{handle}] is closed — through it you can see {vid}{beyond_suffix}")
                    elif beyond_suffix and way_node.properties.get("see_through"):
                        desc_text = self._render_node(way_node) or "A door here."
                        exits_desc.append(f"[{handle}] {desc_text} It is currently closed.{beyond_suffix}")
                    else:
                        desc_text = self._render_node(way_node) or "A door here."
                        if state != "open":
                            # A closed door reads as closed at a glance — locked/
                            # blocked/jammed are only learned by examining it.
                            exits_desc.append(f"[{handle}] {desc_text} It is currently closed.")
                        else:
                            exits_desc.append(f"[{handle}] {desc_text}")
                seen_ways.add(way_id)
        if exits_desc:
            desc += "\n" + "\n".join(exits_desc)

        if not player_is_dead and active_player_obj:
            self.player_manager.apply_action("look", player=active_player_obj)
        return desc
