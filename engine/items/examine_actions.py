"""Examine / inventory actions for ItemActions.

Moved verbatim from engine/item_actions.py as part of the task-314
action-family split. Methods hang off the ItemActions context (graph,
matching, trigger_system, equipment, world) via the mixin.

@module examine_actions
@contributes ExamineActionsMixin
@docs docs/virtualWorld/Rules Engine/Triggers & Effects.md
"""

import re
from typing import Any, Dict, List, Optional

from graph import (
    EDGE_AT,
    EDGE_BEHIND,
    EDGE_BESIDE,
    EDGE_CARRYING,
    EDGE_CONNECTION,
    EDGE_EQUIPPED,
    EDGE_IN,
    EDGE_ON,
    EDGE_UNDER,
    EDGE_KNOWN,
    Node,
)
from engine.beyond_visibility import build_beyond_suffix

DOMAIN_LEVEL_RANKS: Dict[str, int] = {
    "ignorant": 0,
    "novice": 1,
    "familiar": 2,
    "expert": 3,
}
_ORDERED_DOMAIN_LEVELS = ("expert", "familiar", "novice", "ignorant")


def _viewer_domain_level(viewer: Any, domain: str) -> Optional[str]:
    target = str(domain or "").strip().lower()
    if not target or viewer is None:
        return None
    if hasattr(viewer, "get_domain_level"):
        return viewer.get_domain_level(target)
    for entry in getattr(viewer, "domains", None) or []:
        if isinstance(entry, dict) and str(entry.get("domain") or "").strip().lower() == target:
            return str(entry.get("level") or "familiar").strip().lower()
    return None


def mask_jargon_for_listener(
    text: str,
    jargon_terms: Optional[List[str]],
    listener: Any = None,
    domain: str = "",
    min_level: str = "familiar",
) -> str:
    """Mask specialist `jargon_terms` when `listener` lacks competence in `domain` (task-968)."""
    if not text or not jargon_terms:
        return text
    min_rank = DOMAIN_LEVEL_RANKS.get(str(min_level or "familiar").strip().lower(), 2)
    if domain:
        lvl = _viewer_domain_level(listener, domain)
        rank = DOMAIN_LEVEL_RANKS.get(lvl or "ignorant", 0)
        if rank >= min_rank:
            return text
    else:
        domains_list = getattr(listener, "domains", None) or []
        for entry in domains_list:
            if not isinstance(entry, dict):
                continue
            rank = DOMAIN_LEVEL_RANKS.get(str(entry.get("level") or "").strip().lower(), 0)
            entry_terms = {str(t).strip().lower() for t in (entry.get("jargon_terms") or []) if str(t).strip()}
            if rank >= min_rank and any(str(t).strip().lower() in entry_terms for t in jargon_terms):
                return text
    masked = text
    for term in sorted({str(t).strip() for t in jargon_terms if str(t).strip()}, key=len, reverse=True):
        pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
        masked = pattern.sub("[unfamiliar jargon]", masked)
    return masked


def resolve_domain_examine_note(item_props: Optional[Dict[str, Any]], viewer: Any) -> str:
    """Resolve domain-gated inspection note for `viewer` from item `domain_notes` (task-968)."""
    if not isinstance(item_props, dict):
        return ""
    domain_notes = item_props.get("domain_notes")
    if not domain_notes:
        return ""
    default_min_level = str(item_props.get("domain_min_level") or "familiar").strip().lower()
    fallback_note = str(item_props.get("domain_fallback_note") or "").strip()

    if isinstance(domain_notes, str):
        dom = str(item_props.get("domain") or "").strip().lower()
        lvl = _viewer_domain_level(viewer, dom) if dom else None
        rank = DOMAIN_LEVEL_RANKS.get(lvl or "ignorant", 0)
        min_rank = DOMAIN_LEVEL_RANKS.get(default_min_level, 2)
        return domain_notes.strip() if rank >= min_rank else fallback_note

    if not isinstance(domain_notes, dict):
        return ""

    notes_out: List[str] = []
    for dom_key, spec in domain_notes.items():
        dom = str(dom_key or "").strip().lower()
        if not dom:
            continue
        lvl = _viewer_domain_level(viewer, dom)
        rank = DOMAIN_LEVEL_RANKS.get(lvl or "ignorant", 0)
        if isinstance(spec, str):
            min_rank = DOMAIN_LEVEL_RANKS.get(default_min_level, 2)
            if rank >= min_rank and spec.strip():
                notes_out.append(spec.strip())
            elif fallback_note:
                notes_out.append(fallback_note)
        elif isinstance(spec, dict):
            min_lvl = str(spec.get("min_level") or spec.get("domain_min_level") or default_min_level).strip().lower()
            min_rank = DOMAIN_LEVEL_RANKS.get(min_lvl, 2)
            if rank < min_rank:
                fb = str(spec.get("ignorant") or spec.get("fallback") or fallback_note).strip()
                if fb:
                    notes_out.append(fb)
                continue
            chosen = ""
            for tier in _ORDERED_DOMAIN_LEVELS:
                if DOMAIN_LEVEL_RANKS[tier] <= rank and spec.get(tier):
                    chosen = str(spec[tier]).strip()
                    break
            if not chosen and spec.get("note"):
                chosen = str(spec["note"]).strip()
            if chosen:
                notes_out.append(chosen)
    return "\n".join(notes_out)


class ExamineActionsMixin:
    """get_item_desc / _describe_flavor_target / get_inventory / node rendering."""

    def _wears_nametag(self, player_manager, char_name: str) -> bool:
        """True when *char_name* wears an item tagged 'nametag' (task-339):
        examining them reveals their name."""
        getter = getattr(player_manager, "_player_node_id", None)
        node_id = getter(char_name) if callable(getter) else None
        if not node_id:
            return False
        for edge in self.graph.get_edges_for_target(node_id, EDGE_EQUIPPED):
            item_node = self.graph.get_node(edge.source)
            if item_node and "nametag" in [str(t).lower() for t in item_node.properties.get("tags", []) or []]:
                return True
        return False

    def _mask_character_name_for_viewer(self, player_manager, char_name: str, text: str) -> str:
        """Mask a character's real name (and aliases) out of examine prose
        when the viewer doesn't know their name yet (task-339). A worn
        nametag bypasses the mask and appends the reveal."""
        viewer = player_manager.players.get(player_manager.active_player)
        if viewer is not None and hasattr(viewer, "knows_name") and viewer.knows_name(char_name):
            return text
        if self._wears_nametag(player_manager, char_name):
            return f"{text}\nA name tag reads \"{char_name}\".".strip()
        import re as _re
        from engine.matching import node_aliases
        patterns = {char_name.lower()}
        getter = getattr(player_manager, "_player_node_id", None)
        node_id = getter(char_name) if callable(getter) else None
        char_node = self.graph.get_node(node_id) if node_id else None
        if char_node is not None:
            for alias in node_aliases(char_node):
                if alias:
                    patterns.add(str(alias).lower())
        label = "the stranger"
        target = player_manager.players.get(char_name)
        if target is not None and hasattr(target, "unknown_display_name"):
            try:
                candidate = target.unknown_display_name()
                if isinstance(candidate, str) and candidate.strip() \
                        and char_name.lower() not in candidate.lower():
                    label = candidate
            except Exception:
                label = "the stranger"
        for pattern in sorted(patterns, key=len, reverse=True):
            text = _re.sub(r'(?<!\w)' + _re.escape(pattern) + r'(?!\w)', label, text, flags=_re.IGNORECASE)
        return text

    def _render_node_desc(self, node):
        """Render a node's description template, seeding its own parameters.

        Lets ``{param:<key>}`` resolve from ``node.properties["parameters"]`` in
        item/way/area/character descriptions.
        """
        if node is None:
            return ""
        from engine.items.provenance import render_provenance

        provenance_line = render_provenance(node.properties.get("provenance"))

        def _with_provenance(text):
            if provenance_line:
                return f"{text}\n{provenance_line}".strip() if text else provenance_line
            return text

        desc = node.properties.get("description", "")
        # task-191: freshness state joins the treated description naturally -
        # no numbers, just what senses tell you.
        if node.properties.get("perishable"):
            fstate = node.properties.get("freshness_state", "")
            if fstate == "cooked":
                desc = (desc + " It's been cooked - still good.").strip()
            elif fstate == "spoiled":
                desc = (desc + " It has gone bad.").strip()
        # task-10: proximity tools read their surroundings on examine.
        if node.properties.get("proximity_effect") and self.world is not None:
            try:
                from engine.proximity import proximity_report
                reading = proximity_report(
                    self.world.player_manager, node, self.graph, game_state=self.world
                )
                if reading:
                    desc = (desc + " " + reading).strip()
            except Exception:
                pass
        if not desc or not self.trigger_system:
            return _with_provenance(desc)
        from engine.trigger_system import TriggerSystem
        if not isinstance(self.trigger_system, TriggerSystem):
            return _with_provenance(desc)
        context = {
            "item_params": node.properties.get("parameters", {}) or {},
            "item_properties": node.properties or {},
            "item_name": node.name or "",
            "item_state": node.properties.get("current_state", ""),
        }
        try:
            return _with_provenance(self.trigger_system._render_template(desc, context))
        except Exception:
            return _with_provenance(desc)

    def get_item_desc(self, player_manager, target_name: str) -> str:
        """Describe an item or exit by name. Items checked first (with fuzzy match),
        then exits (with fuzzy match). Raises ValueError if neither is found."""
        if not player_manager.current_area:
            raise ValueError("You are in an empty void.")

        player_is_dead = False
        p = player_manager.players.get(player_manager.active_player)
        if p:
            player_is_dead = p.state == "dead"

        area_id = player_manager._get_current_area_id()
        is_dark = False
        if not player_manager.lighting.can_see_in_dark(player_manager, player_manager.active_player):
            cur_area = player_manager.current_area
            cur_env = getattr(cur_area, 'environment', None) or (cur_area.properties.get('environment') if hasattr(cur_area, 'properties') else None)
            ambient = player_manager.lighting.get_ambient_light(area_id, cur_env) if area_id else 80
            if ambient < 20:
                is_dark = True

        target_lower = target_name.strip().lower()
        examine_self = target_lower in ("self", "me", "myself")
        target_pname = None
        if examine_self:
            target_pname = player_manager.active_player
        else:
            for pn in player_manager.players:
                if pn.lower() != player_manager.active_player.lower() and pn.lower() == target_lower:
                    target_pname = pn
                    break
            if target_pname is None and len(target_lower) >= 2:
                for pn in player_manager.players:
                    if pn.lower() != player_manager.active_player.lower() and target_lower in pn.lower():
                        target_pname = pn
                        break

        from engine.triggers.behaviors import is_character_hidden
        target_p = player_manager.players.get(target_pname)
        if target_p and not (examine_self or target_pname == player_manager.active_player):
            if (
                getattr(target_p, "hidden", False)
                or getattr(target_p, "state", "") in ("hidden", "stealthed")
                or is_character_hidden(player_manager, target_pname, self.graph, player=target_p)
                or (hasattr(player_manager, "is_visible") and not player_manager.is_visible(target_pname))
            ):
                target_p = None
                target_pname = None
        if target_p:
            is_self = examine_self or target_pname == player_manager.active_player
            desc_parts = []
            base_desc = getattr(target_p, 'base_description', '') or getattr(target_p, 'description', '')
            if base_desc and not is_self:
                base_desc = self._mask_character_name_for_viewer(player_manager, target_pname, base_desc)
            if base_desc:
                desc_parts.append(base_desc)
            equip_narrative = self.equipment.get_equipment_narrative(player_name=target_pname, viewer_name=player_manager.active_player if not is_self else None)
            if equip_narrative:
                desc_parts.append(equip_narrative)
            if not is_self:
                emotion_nl = target_p.get_emotion_nl() if hasattr(target_p, 'get_emotion_nl') else ''
                if emotion_nl:
                    desc_parts.append(f"Their mood: {emotion_nl}")
            if not desc_parts:
                desc_parts.append("They are wearing nothing.")
            from engine.character_spatial import (
                approach_character,
                set_position_examining_character,
            )
            if not is_self:
                # task-783: walk up to them before describing them, the way
                # grab, give, steal and use-on already do.
                approach_character(self.graph, player_manager, target_pname)
                set_position_examining_character(self.graph, player_manager, target_pname)
            if is_dark:
                if is_self:
                    return "You feel around yourself in the dark. You are unhurt and your clothing is intact."
                return "You feel around blindly in the dark. Your hands brush against a person - you can feel warm skin and breathing, but it is too dark to make out their features or identity."
            return "\n".join(desc_parts)

        # Task-154: the target isn't a known name - try resolving by description
        # ("examine the tall man in the corner") before falling through to items.
        if target_pname is None and self.matching is not None and hasattr(self.matching, "_match_character_name"):
            resolved, candidates = self.matching._match_character_name(target_name)
            if resolved:
                target_pname = resolved
                target_p = player_manager.players.get(resolved)
                if target_p and (
                    getattr(target_p, "hidden", False)
                    or getattr(target_p, "state", "") in ("hidden", "stealthed")
                    or is_character_hidden(player_manager, resolved, self.graph, player=target_p)
                    or (hasattr(player_manager, "is_visible") and not player_manager.is_visible(resolved))
                ):
                    target_p = None
                    target_pname = None
                if target_p:
                    base_desc = getattr(target_p, 'base_description', '') or getattr(target_p, 'description', '')
                    base_desc = self._mask_character_name_for_viewer(player_manager, resolved, base_desc)
                    equip_narrative = self.equipment.get_equipment_narrative(
                        player_name=resolved,
                        viewer_name=player_manager.active_player,
                    )
                    parts = []
                    if base_desc:
                        parts.append(base_desc)
                    if equip_narrative:
                        parts.append(equip_narrative)
                    if not parts:
                        parts.append("They are wearing nothing.")
                    from engine.character_spatial import (
                        approach_character,
                        set_position_examining_character,
                    )
                    approach_character(self.graph, player_manager, resolved)
                    set_position_examining_character(self.graph, player_manager, resolved)
                    if is_dark:
                        return "You feel around blindly in the dark. Your hands brush against a person - you can feel warm skin and breathing, but it is too dark to make out their features or identity."
                    return "\n".join(parts)
            elif candidates:
                return f"You don't know exactly who that is. Do you mean: {', '.join(candidates)}?"

        # Area examine: "examine the room" / "examine this area" - resolve the
        # current area by name (or id), describe it and fire its on_examine
        # triggers. Falls through to items when no area matches.
        current_area_node = self.graph.get_node(area_id) if area_id else None

        # task-499: examining anything teaches the room you are in. The walk path
        # writes the same registry; this is the second writer the fog gate needs.
        viewer_obj = player_manager.get_active_player_obj()
        if viewer_obj is not None and current_area_node is not None:
            try:
                from engine.fog import reveal_area
                reveal_area(viewer_obj, current_area_node)
            except Exception:
                pass

        area_phrases = {"room", "area", "here", "surroundings", "the room",
                        "the area", "current room", "current area"}
        if current_area_node and (
            target_lower in area_phrases
            or target_lower in str(current_area_node.name).lower()
            or target_lower in str(current_area_node.id).lower()
        ):
            from engine.character_spatial import clear_character_position_edges
            if player_manager.active_player:
                pid = player_manager._player_node_id(player_manager.active_player)
                clear_character_position_edges(self.graph, pid)
            if is_dark:
                return "You feel around blindly in the dark. It is pitch black - hands outstretched, you find only empty air and shadows. You cannot see your surroundings without a light source."
            area_desc = self._render_node_desc(current_area_node)
            state = current_area_node.properties.get("current_state", "")
            desc = f"You take a closer look at the {current_area_node.name}."
            if area_desc:
                desc += f" {area_desc}"
            if state and state not in ("normal", ""):
                desc += f" It is currently {state}."
            trigger_outputs = self._exec_triggers(current_area_node, "on_examine")
            if trigger_outputs:
                desc += "\n" + "\n".join(trigger_outputs)
            return desc

        matched_item = self.matching._match_item_name(target_name)
        if not matched_item and is_dark and target_lower in ("something", "an object", "object", "shape", "the shape", "item"):
            for edge in self.graph.get_edges_for_target(area_id, EDGE_IN):
                cand = self.graph.get_node(edge.source)
                if cand and cand.type == "item":
                    matched_item = cand.name
                    break

        if matched_item:
            item_node = None
            player_id = player_manager._player_node_id(player_manager.active_player)
            for edge in list(self.graph.get_edges_for_target(area_id, EDGE_IN)) + list(self.graph.get_edges_for_target(player_id, EDGE_CARRYING)) + list(self.graph.get_edges_for_target(player_id, EDGE_EQUIPPED)) + list(self.graph.get_edges_for_target(player_id, EDGE_KNOWN)):
                node = self.graph.get_node(edge.source)
                if node and node.type == "item" and node.name == matched_item:
                    item_node = node
                    break
            if item_node:
                self._register_item_discovery(player_manager, item_node)
                from engine.character_spatial import (
                    approach_item,
                    set_position_examining_item,
                )
                # task-783: walk to it before describing it. `approach_item` is
                # a no-op for anything not in the current area, so an item in
                # hand, worn, or inside a carried container is left alone.
                approach_item(self.graph, player_manager, target_name, item_node)
                set_position_examining_item(self.graph, player_manager, target_name, item_node)
                if is_dark:
                    return self._get_dark_tactile_impression(item_node)
                # task-499: examining an item teaches the item, and a map with a
                # chart teaches the places it charts ("read" aliases examine).
                # Gated on an authored chart: a map with no chart is a prop, and
                # `teach_from_map` without a list would teach the whole world.
                try:
                    from engine.fog import reveal_examined, teach_from_map
                    if viewer_obj is not None:
                        reveal_examined(viewer_obj, item_node, graph=self.graph)
                        if "charted_areas" in (item_node.properties or {}):
                            teach_from_map(viewer_obj, item_node, graph=self.graph)
                except Exception:
                    pass
                # Phase 3 - see_item save_on hook (e.g. hemophobic + blood/corpse)
                try:
                    player_manager._emit_save_on(
                        player_manager.active_player, "see_item",
                        {"item_tags": item_node.properties.get("tags", []),
                         "source": item_node.name, "source_type": "item"},
                    )
                except Exception:
                    pass
                desc = self._render_node_desc(item_node)

                # task-433 / task-967: surface structured inscriptions gated on
                # reader literacy and language competence.
                inscriptions = item_node.properties.get("inscriptions")
                if isinstance(inscriptions, list) and inscriptions:
                    from engine.language_barrier import (
                        extract_known_names_for_listener,
                        mask_text_for_listener,
                    )

                    known_names = extract_known_names_for_listener(viewer_obj)
                    default_lang = item_node.properties.get("lang")
                    lines = []
                    for record in inscriptions:
                        if not isinstance(record, dict):
                            continue
                        text = str(record.get("text", "")).strip()
                        if not text:
                            continue
                        insc_lang = record.get("lang") or default_lang
                        shown_text, was_masked = mask_text_for_listener(
                            text,
                            insc_lang,
                            viewer_obj,
                            graph=self.graph,
                            known_names=known_names,
                            for_reading=True,
                        )
                        author = record.get("by") or "someone"
                        tick = record.get("tick")
                        stamp = f" (tick {tick})" if tick else ""
                        lang_note = f" [{insc_lang}]" if (was_masked and insc_lang) else ""
                        lines.append(f"  {author}{stamp}{lang_note}: \"{shown_text}\"")
                    if lines:
                        desc += "\nWritten here:\n" + "\n".join(lines)

                if item_node.properties.get("current_state") == "locked":
                    locked_msg = item_node.properties.get("locked_message", "It's locked.")
                    desc += f"\n{locked_msg}"

                skill_check_config = item_node.properties.get("skill_check", {})
                if skill_check_config and skill_check_config.get("skill"):
                    skill_name = skill_check_config["skill"]
                    dc = skill_check_config.get("dc", 10)
                    success, total, message = player_manager.skill_check(skill_name, dc)
                    if not success:
                        desc += f"\n{message} You fail to discern anything more."
                        return desc
                    knowledge = skill_check_config.get("grants_knowledge", "")
                    if knowledge:
                        desc += f"\n{message} You notice something: [{knowledge}]"

                domain_note = resolve_domain_examine_note(item_node.properties, viewer_obj)
                if domain_note:
                    desc += f"\n{domain_note}"

                try:
                    from engine.time_perception import describe_timepiece_reading
                    area_node_for_tp = self.graph.get_node(current_area_id) if current_area_id else None
                    tp_reading = describe_timepiece_reading(
                        player_manager, item_node, area_node=area_node_for_tp, viewer=viewer_obj
                    )
                    if tp_reading:
                        desc += f"\n{tp_reading}"
                except Exception:
                    pass

                trigger_outputs = self._exec_triggers(item_node, "on_examine")
                if trigger_outputs:
                    desc += "\n" + "\n".join(trigger_outputs)

                uses = item_node.properties.get("uses", -1)
                try:
                    uses = int(uses)
                except (TypeError, ValueError):
                    uses = -1
                if uses > 0:
                    minutes_per_tick = getattr(player_manager, "time_per_tick_minutes", 5)
                    minutes = uses * minutes_per_tick
                    desc += f"\n{uses} uses left (~{minutes} minutes of warmth/light)."

                if item_node.properties.get("current_state") != "locked":
                    related: dict = {}
                    for ce in self.graph.get_edges_for_target(item_node.id, EDGE_IN):
                        cn = self.graph.get_node(ce.source)
                        if cn and cn.type == "item":
                            related.setdefault(ce.type, []).append(cn)
                    if related:
                        relation_labels = {
                            EDGE_IN: "Inside you see: {names}.",
                            EDGE_ON: "On the {target}: {names}.",
                            EDGE_UNDER: "Under the {target}: {names}.",
                            EDGE_BEHIND: "Behind the {target}: {names}.",
                            EDGE_BESIDE: "Beside the {target}: {names}.",
                            EDGE_AT: "At the {target}: {names}.",
                        }
                        target_name = item_node.name or item_node.id
                        lines = []
                        revealed = 0
                        for etype in (EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT, EDGE_IN):
                            if etype not in related:
                                continue
                            for cn in related[etype]:
                                if cn.properties.get("current_state") == "hidden":
                                    cn.properties["current_state"] = "normal"
                                # task-494: un-hiding a node is a *global* change, so the
                                # first character to look in a chest revealed the loot to
                                # everyone forever, while the character who actually did
                                # the looking was never credited with meeting it. Both
                                # halves are needed and they are different: the state flip
                                # above is about what the world shows, this is about what
                                # *this* character has seen. The readers that
                                # render "known" (contextual-actions.js, room-context.js,
                                # memory-context.js) all read observation memories via
                                # memory_index / has_seen, so the stamp is what makes the
                                # reveal mean anything to the player. Idempotent: a second
                                # examine of the same chest refreshes the observation in
                                # place and grants no further novelty.
                                if self._register_item_discovery(player_manager, cn):
                                    revealed += 1
                            names = ', '.join(cn.name for cn in related[etype])
                            lines.append(relation_labels[etype].format(target=target_name, names=names))
                        if lines:
                            desc += "\n" + "\n".join(lines)
                        if revealed:
                            # Only narrate when something was genuinely new, so a
                            # re-look at a known chest does not read as a discovery.
                            desc += f"\nTaking in {revealed} new thing{'s' if revealed != 1 else ''}."

                actions = self.trigger_system._get_available_actions(item_node)
                if actions:
                    desc += "\n\nAvailable actions:"
                    for a in actions:
                        status = "" if a["enabled"] else f" ({a['reason']})"
                        desc += f"\n  [{a['action']}] {a['label']}{status}"
                return desc

        matched_edge, way_node, matched_handle = self.matching.resolve_exit(area_id, target_name)
        if matched_edge and way_node:
            direction = matched_handle
            from engine.character_spatial import approach_way
            if player_manager.active_player:
                pid = player_manager._player_node_id(player_manager.active_player)
                approach_way(self.graph, pid, way_node.id)
            if is_dark:
                state = way_node.properties.get("current_state", "closed")
                if state == "open":
                    return "You feel along the opening in the dark. Your fingers find an open passage with cool air drifting through, though the darkness prevents you from seeing beyond."
                elif state == "locked":
                    return "You feel along the opening in the dark. Your hands find a locked barrier, firmly held in place by a rigid latch."
                elif state == "blocked":
                    return "You feel along the opening in the dark. Your hands feel a blocked passage, obstructed by obstacles."
                else:
                    return "You feel along the opening in the dark. Your hands press against a closed barrier. You can feel the solid edges and a handle." 
            # task-499: a way is described by where it goes, so examining it
            # teaches the area on the far side.
            try:
                from engine.fog import reveal_examined
                if viewer_obj is not None:
                    reveal_examined(viewer_obj, way_node, graph=self.graph,
                                    from_area_id=area_id)
            except Exception:
                pass
            desc = self._render_node_desc(way_node)
            if not desc:
                desc = f"It's a {direction}."
            state = way_node.properties.get("current_state", "closed")
            # Examining a way reveals its hidden state (task-333 discovery):
            # the panel/scene only shows lock/jam once this flag is set.
            active_obj = player_manager.get_active_player_obj()
            cur_area = getattr(player_manager, "current_area", None)
            if active_obj is not None and cur_area is not None and hasattr(active_obj, "learn_way_aspect"):
                if state == "locked":
                    active_obj.learn_way_aspect(cur_area.name, direction, "locked")
                elif state == "blocked":
                    active_obj.learn_way_aspect(cur_area.name, direction, "blocked")
                needs_open = way_node.properties.get("needs_open", {})
                if isinstance(needs_open, dict) and needs_open.get("enabled", False):
                    active_obj.learn_way_aspect(cur_area.name, direction, "needs_force")
            target_area = None
            for e2 in self.graph.get_edges_for_source(way_node.id, EDGE_CONNECTION):
                if e2.target != area_id:
                    target_area = self.graph.get_node(e2.target)
                    break
            active_player_obj = player_manager.get_active_player_obj()
            beyond_suffix = ""
            if target_area and (state == "open" or way_node.properties.get("see_through")):
                beyond_suffix = build_beyond_suffix(
                    self.graph,
                    player_manager,
                    target_area.id,
                    target_area.name,
                    matched_edge.properties,
                    active_player_obj,
                )
            if state == "open":
                if target_area:
                    desc += f" It leads to the {target_area.name}."
            else:
                desc += f" It is currently {state}."
                # Peephole/see-through: a glimpse into the next
                # room without opening the door (see_through +
                # visible_in_direction on the area→way edge).
                if way_node.properties.get("see_through"):
                    vid = matched_edge.properties.get("visible_in_direction", "")
                    if vid:
                        desc += f" Through it you can see: {vid}"
            if beyond_suffix:
                desc += beyond_suffix
            trigger_outputs = self._exec_triggers(way_node, "on_examine")
            if trigger_outputs:
                desc += "\n" + "\n".join(trigger_outputs)
            return desc

        items: List[str] = []
        people: List[str] = []
        paths: List[str] = []
        carried: List[str] = []
        seen = set()
        active_p = player_manager.players.get(player_manager.active_player)
        known = set(str(k) for k in (getattr(active_p, "known", []) or []))
        active_node_id = player_manager._player_node_id(player_manager.active_player)
        if area_id:
            for edge in self.graph.get_edges_for_target(area_id, EDGE_IN):
                node = self.graph.get_node(edge.source)
                if not node or node.id in seen:
                    continue
                if node.type == "character":
                    # Don't list yourself; unmet characters keep their
                    # appearance label, never their database name (task-154).
                    if node.id == active_node_id:
                        continue
                    pname = node.name
                    if pname and str(pname).lower() == str(player_manager.active_player or "").lower():
                        continue
                    p = player_manager.players.get(pname)
                    if p is None:
                        continue
                    if (
                        getattr(p, "hidden", False)
                        or getattr(p, "state", "") in ("hidden", "stealthed")
                        or is_character_hidden(player_manager, pname, self.graph, player=p)
                        or (hasattr(player_manager, "is_visible") and not player_manager.is_visible(pname))
                    ):
                        continue
                    seen.add(node.id)
                    if active_p is not None and active_p.has_met(pname):
                        people.append(pname)
                    else:
                        people.append(p.unknown_display_name())
                else:
                    # Hidden things are discovered by exploring, never offered
                    # by a failed-lookup fallback. An authored `known` entry
                    # means the character already knows where it is.
                    if node.properties.get("current_state") == "hidden" and str(node.id) not in known:
                        continue
                    seen.add(node.id)
                    items.append(node.name)
        player_id = active_node_id
        for edge in self.graph.get_edges_for_target(player_id, EDGE_CARRYING):
            node = self.graph.get_node(edge.source)
            if node and node.id not in seen:
                seen.add(node.id)
                carried.append(f"{node.name} (carried)")
        area_name = player_manager.current_area.name if player_manager.current_area else ""
        for edge in self.graph.get_edges_for_source(area_id, EDGE_CONNECTION):
            way_node = self.graph.get_node(edge.target)
            if not way_node or way_node.id in seen:
                continue
            way_state = way_node.properties.get("current_state") or ""
            if way_state == "hidden":
                continue
            seen.add(way_node.id)
            d = self.matching.way_handle(
                way_node, edge.properties.get("direction", ""),
                area_name,
            ) or (edge.properties.get("direction") or "door")
            paths.append(f"{d} ({way_state})" if way_state else d)

        # Descriptive fallback: target isn't a real item/exit but appears in area
        # or item descriptions - describe it as flavor text instead of erroring.
        descriptive = self._describe_flavor_target(player_manager, target_name, area_id)
        if descriptive:
            return descriptive

        groups = []
        if items:
            groups.append("items: " + ", ".join(items))
        if people:
            groups.append("people: " + ", ".join(people))
        if paths:
            groups.append("paths: " + ", ".join(paths))
        if carried:
            groups.append("carried: " + ", ".join(carried))
        if is_dark:
            raise ValueError(f"You grope around in the dark, but find no '{target_name}' nearby.")
        raise ValueError(
            f"You look for '{target_name}' but don't see it here. "
            f"Things you can examine right now: {'; '.join(groups) if groups else 'nothing specific'}."
        )

    def _get_dark_tactile_impression(self, item_node) -> str:
        """Produce a partial, unnamed sensory impression (shape, texture, temperature).

        Used when examining an item in darkness (ambient < 20). Never reveals
        the item's name or visual details.
        """
        props = item_node.properties or {}
        desc_text = str(props.get("description", "")).lower()
        tags = [str(t).lower() for t in props.get("tags", [])]

        # 1. Temperature cue
        temp_val = props.get("temperature")
        temp_str = ""
        if isinstance(temp_val, (int, float)):
            if temp_val > 25:
                temp_str = "radiating warmth"
            elif temp_val < 15:
                temp_str = "cold to the touch"
        elif isinstance(temp_val, str) and temp_val.strip():
            temp_str = f"{temp_val.strip()} to the touch"
        elif "cold to the touch" in desc_text or "cold" in desc_text or "chilled" in desc_text:
            temp_str = "cold to the touch"
        elif "warm against" in desc_text or "warm" in desc_text or "heating" in desc_text:
            temp_str = "warm against your hands"
        elif "burning" in desc_text or "hot" in desc_text:
            temp_str = "hot to the touch"

        # 2. Texture / Material cue
        texture = str(props.get("texture", "")).strip().lower()
        material = str(props.get("material", "")).strip().lower()
        surface = str(props.get("surface", "")).strip().lower()

        if not material:
            for mat in ("metal", "wood", "stone", "iron", "steel", "brass", "bronze", "glass", "cloth", "leather", "ceramic", "paper", "clay", "wax"):
                if mat in tags or mat in desc_text:
                    material = mat
                    break

        if not texture:
            for tex in ("rough", "smooth", "coarse", "dusty", "slimy", "sticky", "carved", "serrated", "sharp", "soft", "silky", "stiff", "cracked", "scuffed"):
                if tex in desc_text:
                    texture = tex
                    break

        texture_str = ""
        if texture and material:
            texture_str = f"a {texture}, {material} surface"
        elif texture:
            texture_str = f"a {texture} surface"
        elif material:
            texture_str = f"a {material} surface"
        elif surface:
            texture_str = f"a {surface} surface"

        # 3. Shape / Size / Form cue
        shape = str(props.get("shape", "")).strip().lower()
        size = str(props.get("size", "")).strip().lower()

        if not shape:
            for shp in ("cylindrical", "rectangular", "spherical", "round", "flat", "curved", "bell-shaped", "elongated", "narrow", "hollow", "pointed"):
                if shp in desc_text:
                    shape = shp
                    break

        if not size:
            for sz in ("tiny", "small", "large", "heavy", "bulky", "massive", "lightweight", "slender"):
                if sz in desc_text:
                    size = sz
                    break

        shape_str = ""
        if size and shape:
            shape_str = f"a {size}, {shape} shape"
        elif shape:
            shape_str = f"a {shape} shape"
        elif size:
            shape_str = f"a {size} form"
        else:
            shape_str = "a distinct form"

        details = []
        if texture_str:
            details.append(f"you feel {texture_str}")
        if shape_str:
            details.append(f"outlining {shape_str}")
        if temp_str:
            details.append(f"it is {temp_str}")

        if details:
            body = ", ".join(details)
            return f"You feel around blindly in the dark. Touching the object, {body}."
        return "You feel around blindly in the dark. Your fingers trace a solid shape, but the pitch darkness obscures any finer details."

    def _describe_flavor_target(self, player_manager, target_name: str, area_id: str) -> Optional[str]:
        """Return a narrative description when the examined target appears only
        in descriptive text (area or item descriptions) but isn't a real object.

        Pulls the surrounding sentence and returns it as flavor text so the
        player gets an in-character response instead of a technical error.
        Returns None if no descriptive match exists.
        """
        if not target_name:
            return None
        target_lower = target_name.lower().strip()
        target_words = [w for w in target_lower.split() if len(w) >= 3]
        if not target_words:
            return None

        area_node = self.graph.get_node(area_id) if area_id else None
        area_desc = (area_node.properties.get("description", "") if area_node else "")
        descriptive_sentences = []
        if area_desc:
            descriptive_sentences.append(area_desc)
        for edge in self.graph.get_edges_for_target(area_id, EDGE_IN):
            node = self.graph.get_node(edge.source)
            if node and node.type == "item" and node.properties.get("current_state") != "hidden" and node.properties.get("description"):
                descriptive_sentences.append(str(node.properties["description"]))
        for edge in self.graph.get_edges_for_source(area_id, EDGE_CONNECTION):
            way_node = self.graph.get_node(edge.target)
            if way_node and way_node.properties.get("current_state") != "hidden" and way_node.properties.get("description"):
                descriptive_sentences.append(str(way_node.properties["description"]))

        import re as _re
        for text in descriptive_sentences:
            text_lower = text.lower()
            if target_lower not in text_lower:
                continue
            # Extract the sentence containing the target phrase
            sentences = _re.split(r'(?<=[.!?])\s+', text)
            for sentence in sentences:
                if target_lower in sentence.lower():
                    cleaned = sentence.strip().lstrip("0123456789.- ")
                    if cleaned:
                        return (
                            f"You examine {target_name}. {cleaned} "
                            "It does not seem to be of any use."
                        )
        return None

    def get_inventory(self, player_manager) -> List[str]:
        player_id = player_manager._player_node_id(player_manager.active_player)
        seen = set()
        items = []
        for edge in self.graph.get_edges_for_target(player_id, EDGE_CARRYING):
            node = self.graph.get_node(edge.source)
            if node and node.type == "item" and node.name not in seen:
                seen.add(node.name)
                items.append(node.name)
        return items
