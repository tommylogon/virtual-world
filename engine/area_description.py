from typing import Any, Dict, List, Optional

from graph import EDGE_CONNECTION, EDGE_IN, EDGE_CARRYING, EDGE_EQUIPPED
from engine.equipment import INTRINSIC_ABILITY_TAGS
from engine.equipment_bonuses import aggregate_bonuses, effective_temperature
from engine.activities import activity_description
from engine.beyond_visibility import build_beyond_suffix, normalize_visible_items
from engine.name_masking import mask_name_in_text
from engine.room_perception import (
    describe_item_quantity,
    resolve_area_node,
    visible_area_items,
    way_visible_to,
)


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


# ── Outdoor sky tables (task-559) ──
#
# Before this, `env["weather"]` was mechanically live (it drove the light
# multiplier and the guess-time DC) but never narrated: a character standing in
# a thunderstorm got a temperature sentence, an air sentence and a light level,
# and not one word about the rain. The sun was worse — daylight was a light
# curve plus an hour comparison, so nothing ever said it was dawn.

#: One sentence per canonical weather state. An empty string means "say
#: nothing": a clear sky needs no announcement, and ``windy`` is narrated from
#: the ``wind`` magnitude instead (see :data:`WIND_PROSE`) so a gale does not
# produce two sentences about wind. ``tests/test_weather_narration.py`` asserts
# every value in ``WEATHER_STATES`` has an entry here — a state with no
# sentence is exactly the bug this table fixes, and the forecast may write any
# value in that list.
WEATHER_PROSE = {
    "clear": "",
    "cloudy": "A flat grey lid of cloud sits over the place.",
    "windy": "",
    "rainy": "Rain is falling, cold and steady.",
    "stormy": "The storm is breaking overhead — rain lashes sideways and the wind screams.",
    "foggy": "Fog has swallowed the place; shapes fade a short way off.",
    "snowy": "Snow is falling, and it muffles every sound.",
}

#: Wind prose, keyed by the ``wind`` magnitude the forecast writes. ``none`` and
#: an unset key say nothing.
WIND_PROSE = {
    "breeze": "A light breeze moves through.",
    "wind": "The wind is steady and searching.",
    "gale": "The gale tugs at everything not bolted down.",
    "storm": "The wind screams past you.",
    "hurricane": "The wind is a maelstrom — it is hard to stand.",
}

#: Time-of-day bands for **outdoor** prose, as ``(start_hour, sentence)``; the
#: first band at or below the hour wins. The day/night split is deliberately
#: 05:00 / 19:00 — the same boundary the moon text and the guess-time action
#: already use. A third split here would let the sky disagree with itself
#: ("the sun is down" while the moon is still being narrated).
TIME_OF_DAY_BANDS = [
    (0, "The night is deep and still."),
    (3, "The small hours of the night."),
    (5, "First light is greying the horizon."),
    (7, "The sun is up, and the morning is cool and new."),
    (11, "The sun stands high overhead."),
    (15, "The afternoon light lies long across the place."),
    (17, "The light is going golden; the day is winding down."),
    (19, "The sun is down and the sky is darkening."),
    (22, "Night has settled over the place."),
]


def time_of_day_prose(hour) -> str:
    """Outdoor time-of-day sentence for an hour (0-23), ``""`` if unknown."""
    try:
        hour = int(hour)
    except (TypeError, ValueError):
        return ""
    if hour < 0 or hour > 23:
        return ""
    text = TIME_OF_DAY_BANDS[0][1]
    for start, sentence in TIME_OF_DAY_BANDS:
        if hour >= start:
            text = sentence
        else:
            break
    return text


from engine.area_tags import is_open_sky as _is_open_sky  # canonical: see engine/area_tags.py


def weather_description(weather, wind_level, noise) -> List[str]:
    """Sentences for the sky above an outdoor area, in reading order.

    ``weather`` and ``wind_level`` are the canonicalised values (see
    ``engine.weather_forecast.normalize_weather``); ``noise`` is the area's raw
    noise descriptor, kept only to avoid saying the same thing twice.
    """
    from engine.weather_forecast import normalize_weather

    lines: List[str] = []
    weather = normalize_weather(weather)
    # ``WEATHER_PROSE["windy"]`` is deliberately empty: a wind-ish *weather*
    # state is narrated from the ``wind`` magnitude below, which is strictly
    # more informative, so no suppression logic is needed here. A ``stormy``
    # state keeps its own sentence — rain breaking overhead is news the wind
    # sentence does not carry.
    sentence = WEATHER_PROSE.get(weather, "")
    if sentence:
        lines.append(sentence)

    wind_line = WIND_PROSE.get(str(wind_level or "").strip().lower(), "")
    if wind_line and str(noise or "").strip().lower() not in ("windy", "howling"):
        lines.append(wind_line)
    return lines


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
        """What is lying about here, AGENT-path wording.

        Counts come from the shared helper (task-504) so a pooled node reads
        "40 berries" here and on the panel path identically.
        """
        area_id = self.get_current_area_id()
        return [describe_item_quantity(node) for node in visible_area_items(
            self.graph, area_id, include_hidden=include_hidden,
            player=self.player_manager.get_active_player_obj())]

    def build_exits_for_area(self, area_name: str, include_hidden: bool = False) -> Dict[str, Any]:
        """Reconstruct the exits dict for a area from graph connections.
        Filters out hidden exits (undiscovered). Hides back-link directions.

        ``include_hidden=True`` is for AUTHORING views (the area inspector) —
        it returns every way regardless of the active player's discoveries,
        so the author sees their own hidden passages. Game-facing callers
        (prompts, look, scene) must keep the default filtered view.
        """
        # task-439: accept an area id or a display name. Resolve once, then use
        # the canonical node's *name* for visibility/handle logic (discovered
        # exits and known-maps are keyed by display name) and its *id* for graph
        # edges. A caller passing an id previously got the id's way-handle and
        # lost hidden-exit discovery; a caller passing a duplicate name got
        # whichever area iteration order hit first.
        area_node = resolve_area_node(self.graph, area_name)
        if area_node is not None:
            area_name = area_node.name
            area_id = area_node.id
        else:
            area_id = None
        if not area_id:
            area_id = self.player_manager.area_node_id(area_name)

        # task-407: authoring exits (include_hidden=True) are purely
        # graph-derived, so they are safe to cache and invalidate on graph
        # revision. The game-facing view depends on per-player discovery
        # state and is deliberately NOT cached. Keyed by the canonical id so an
        # id and a name for the same area share one entry.
        cache = None
        cache_key = None
        if include_hidden:
            rev = self.graph.get_revision()
            if getattr(self, "_exits_cache_rev", None) != rev:
                self._exits_cache = {}
                self._exits_cache_rev = rev
            cache = self._exits_cache
            cache_key = str(area_id).lower()
            hit = cache.get(cache_key)
            if hit is not None:
                return dict(hit)
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

                if not include_hidden and not way_visible_to(
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
                                "direction": direction,
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
        if cache is not None:
            cache[cache_key] = dict(exits)
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
        ambient_light = self.lighting.get_ambient_light(area_id) if area_id else self.lighting.get_light_int(env, 80)
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

        # task-229: moonlight adds flavor to outdoor night areas.
        #
        # This block used to read an undefined local ``node``. Python resolves
        # ``node`` as a local because it is assigned *later* in this method
        # (in the item/people loops), so line 1 of the block raised
        # UnboundLocalError — and the bare ``except Exception: pass`` below
        # swallowed it. The moon has therefore never been narrated anywhere,
        # at any hour, in any world (task-559). The node is looked up properly
        # now, and the except is narrowed to the provider errors it was written
        # for so the next real failure is not invisible.
        moon_desc = ""
        area_node = self.graph.get_node(area_id) if area_id else None
        if _is_open_sky(area_node.properties.get("tags", []) if area_node else []):
            hour = self.lighting.hour_provider() if self.lighting.hour_provider else None
            if hour is not None and (hour >= 19 or hour < 5):
                if self.lighting.moon_provider is not None:
                    try:
                        mp = self.lighting.moon_provider()
                    except (AttributeError, KeyError, TypeError, ValueError):
                        mp = None
                    if isinstance(mp, dict):
                        mname = mp.get("name", "")
                        micon = mp.get("icon", "🌑")
                        if mname == "full_moon":
                            moon_desc = f" {micon} The full moon hangs bright overhead, casting silver light across the scene."
                        elif mname == "blood_moon":
                            moon_desc = f" {micon} An eerie red moon stains the sky — the world is bathed in crimson."
                        elif mname in ("gibbous", "waning"):
                            moon_desc = f" {micon} Moonlight filters through the night sky, softening the shadows."

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
        if moon_desc:
            desc += moon_desc
        if spill_desc:
            desc += spill_desc

        # task-233: dynamic area statuses read through in the description.
        status_area = self.graph.get_node(area_id) if area_id else None
        if status_area is not None:
            for st in (status_area.properties.get("statuses", []) or []):
                stype = str(st.get("type", ""))
                severity = int(st.get("severity", 1))
                if stype == "on_fire":
                    desc += "\n🔥 Flames" + (" rage through here — the heat is oppressive!" if severity >= 3 else " flicker through here.")
                elif stype == "flooded":
                    desc += "\n💧 Water stands" + (" deep" if severity >= 3 else " in puddles") + " across the floor."
                elif stype == "poison_gas":
                    desc += "\n☠️ A sickly" + (", thick" if severity >= 3 else "") + " haze hangs in the air."
                elif stype == "smoke":
                    desc += "\n💨 Smoke curls through the room."
                elif stype == "blessed":
                    desc += "\n✨ A quiet sense of blessing rests on this place."
                elif stype == "darkness_magic":
                    desc += "\n🌑 Shadows cling here unnaturally, swallowing the light."

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
        feels_like = int(effective_temperature(float(env.get("temperature", 21)), equip_bonuses,
                                               wind_level=env.get("wind", "none"),
                                               humidity=env.get("humidity", "dry")))
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
            # N9: raw descriptor values ("windy") read as grammar errors in
            # prose — map the common ones to real sentences.
            noise_prose = {
                "windy": "The wind howls outside.",
                "howling": "The wind howls.",
                "dripping": "Water drips somewhere nearby.",
                "creaking": "Wood creaks around you.",
                "scratching": "Something scrapes nearby.",
                "rustling": "Something rustles in the dark.",
                "crackling": "Something crackles nearby.",
            }
            env_summary.append(noise_prose.get(noise, f"You hear {noise}."))
        # task-559: the sky, if there is one. The weather a forecast writes is
        # only audible/visible outdoors, so this is gated on the same open-sky
        # test the moon text uses — a storm is not something you hear through a
        # stone wall, and an indoor room has no dawn.
        if _is_open_sky(area_node.properties.get("tags", []) if area_node else []):
            env_summary.extend(weather_description(
                env.get("weather", ""), env.get("wind", ""), env.get("noise", "")))
            hour = self.lighting.hour_provider() if self.lighting.hour_provider else None
            tod = time_of_day_prose(hour)
            if tod:
                env_summary.append(tod)
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
                # Authored `known` registry wins over both: a flagged person is
                # never masked to whoever knows them.
                known = active_player_obj is not None and active_player_obj.has_met(pname)
                name_known = False
                if known:
                    from engine.relationships import get_relationship
                    rel = get_relationship(active_player_obj, pname) or {}
                    name_known = not rel.get("first_sighting")
                if not name_known and active_player_obj is not None:
                    try:
                        viewer_known = {
                            str(entry) for entry in (getattr(active_player_obj, "known", None) or [])
                        }
                        viewer_known_lower = {entry.lower() for entry in viewer_known}
                        canonical_id = str(self.player_manager.player_node_id(pname))
                        if pname in viewer_known or canonical_id.lower() in viewer_known_lower:
                            name_known = True
                    except Exception:
                        name_known = False
                if name_known:
                    line = pname
                else:
                    target_player = self.player_manager.players.get(pname)
                    line = target_player.unknown_display_name() if target_player else pname
                if pstate in ("dead", "ghost"):
                    line += " (ghost)"
                # Task-131: show ongoing activities ("sleeping on the bed")
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
                        # task-339: scrub the real name (and aliases) out of the
                        # appearance handle — descriptions may open with the name.
                        try:
                            from engine.matching import node_aliases

                            p_node_id = None
                            _getter = getattr(self.player_manager, "_player_node_id", None)
                            if callable(_getter):
                                p_node_id = _getter(pname)
                            p_node = self.graph.get_node(p_node_id) if p_node_id else None
                            _aliases = node_aliases(p_node) if p_node is not None else ()
                        except Exception:
                            _aliases = ()
                        masked = mask_name_in_text(first_sentence, pname, line, _aliases)
                        line += f" — {masked}"
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

        # task-653: how full the room is, as a function of the SIZE of what is
        # standing in it rather than a headcount. A throne room holding a dwarf
        # and a hill giant reads differently from one holding four dwarves, and
        # the names above already say who — this says whether they fit. Empty
        # rooms say nothing, deliberately.
        try:
            from engine.occupancy import describe_occupancy, occupancy_report
            _report = occupancy_report(
                area_id,
                players=self.player_manager.players,
                graph=self.graph,
            )
            _crowd = describe_occupancy(_report)
            if _crowd:
                desc += "\n" + _crowd
        except Exception:
            # A missing occupancy line is a missing sentence, not a broken
            # description; the rest of the room still reads.
            pass

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
        # task-313: the exits list shows the AUTHORED handle, always. The old
        # transit branch rewrote a way's handle to the literal "back"/"forward"
        # here, which is exactly the behaviour relative facing must not have —
        # the words alias a direction, they never rename the door. So "left"
        # now resolves to the north exit while the room still calls it what the
        # author called it.
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
                    # A seam that owns its own phrase is a **move**, not another
                    # bearing: "you could go down the tunnel" is what a player
                    # reading the room wants, where `[go down the tunnel] is clear`
                    # reads as a fourth compass exit and hides the fact that this
                    # one is somewhere you choose to go rather than a wall you walk
                    # into. Only the phrase-carrying seams are worded this way, so
                    # the compass list stays a compass list (task-529).
                    entry_phrase = str(way_node.properties.get("entry_phrase") or "")
                    if entry_phrase:
                        detail = ""
                        if not way_node.properties.get("see_through"):
                            detail = f" — {target_name} is on the other side"
                        exits_desc.append(f"You could {entry_phrase}{detail}.")
                        seen_ways.add(way_id)
                        continue
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
                            target_feels = int(effective_temperature(float(tenv.get("temperature", 21)), equip_bonuses,
                                                                    wind_level=tenv.get("wind", "none"),
                                                                    humidity=tenv.get("humidity", "dry")))
                            # N11: temperature_description ends with a period —
                            # trim it so the joined clue doesn't read "…cold)."
                            env_clues.append(temperature_description(target_feels).lower().rstrip('.'))
                        clue_str = f" ({', '.join(env_clues)})" if env_clues else ""
                        exits_desc.append(f"[{handle}] {target_name} is visible beyond{clue_str}.{beyond_suffix}")
                else:
                    # A shut seam is worded as an offer too, because that is how a
                    # closed door reads on a street: the way exists, and it does not
                    # open yet. A refusal message is the author's own line, so it is
                    # used verbatim rather than re-described.
                    entry_phrase = str(way_node.properties.get("entry_phrase") or "")
                    if entry_phrase:
                        refusal = str(way_node.properties.get("refusal_message") or "").strip()
                        if refusal:
                            exits_desc.append(f"You could {entry_phrase}, but {refusal[0].lower()}{refusal[1:]}")
                        else:
                            exits_desc.append(f"You could {entry_phrase}, but it is closed.")
                        seen_ways.add(way_id)
                        continue
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
