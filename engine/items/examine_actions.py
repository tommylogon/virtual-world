"""Examine / inventory verbs for ItemActions.

Moved verbatim from engine/item_actions.py as part of the task-314
verb-family split. Methods hang off the ItemActions context (graph,
matching, trigger_system, equipment, world) via the mixin.
"""

from typing import List, Optional

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
    Node,
)
from engine.beyond_visibility import build_beyond_suffix


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
        desc = node.properties.get("description", "")
        # task-191: freshness state joins the treated description naturally —
        # no numbers, just what senses tell you.
        if node.properties.get("perishable"):
            fstate = node.properties.get("freshness_state", "")
            if fstate == "cooked":
                desc = (desc + " It's been cooked — still good.").strip()
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
            return desc
        from engine.trigger_system import TriggerSystem
        if not isinstance(self.trigger_system, TriggerSystem):
            return desc
        context = {
            "item_params": node.properties.get("parameters", {}) or {},
            "item_properties": node.properties or {},
            "item_name": node.name or "",
            "item_state": node.properties.get("current_state", ""),
        }
        try:
            return self.trigger_system._render_template(desc, context)
        except Exception:
            return desc

    def get_item_desc(self, player_manager, target_name: str) -> str:
        """Describe an item or exit by name. Items checked first (with fuzzy match),
        then exits (with fuzzy match). Raises ValueError if neither is found."""
        if not player_manager.current_area:
            raise ValueError("You are in an empty void.")

        player_is_dead = False
        p = player_manager.players.get(player_manager.active_player)
        if p:
            player_is_dead = p.state == "dead"

        if not player_manager.lighting.can_see_in_dark(player_manager, player_manager.active_player):
            area_id = player_manager._get_current_area_id()
            ambient = player_manager.lighting.get_ambient_light(area_id, player_manager.current_area.environment) if area_id else 80
            if ambient < 20:
                raise ValueError("It's too dark to examine anything. maybe you can turn on a light?")

        area_id = player_manager._get_current_area_id()

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

        target_p = player_manager.players.get(target_pname)
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
            from engine.character_spatial import set_position_examining_character
            if not is_self:
                set_position_examining_character(self.graph, player_manager, target_pname)
            return "\n".join(desc_parts)

        # Task-154: the target isn't a known name — try resolving by description
        # ("examine the tall man in the corner") before falling through to items.
        if target_pname is None and self.matching is not None and hasattr(self.matching, "_match_character_name"):
            resolved, candidates = self.matching._match_character_name(target_name)
            if resolved:
                target_pname = resolved
                target_p = player_manager.players.get(resolved)
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
                    from engine.character_spatial import set_position_examining_character
                    set_position_examining_character(self.graph, player_manager, resolved)
                    return "\n".join(parts)
            elif candidates:
                return f"You don't know exactly who that is. Do you mean: {', '.join(candidates)}?"

        # Area examine: "examine the room" / "examine this area" — resolve the
        # current area by name (or id), describe it and fire its on_examine
        # triggers. Falls through to items when no area matches.
        current_area_node = self.graph.get_node(area_id) if area_id else None
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
        if matched_item:
            item_node = None
            player_id = player_manager._player_node_id(player_manager.active_player)
            for edge in list(self.graph.get_edges_for_target(area_id, EDGE_IN)) + list(self.graph.get_edges_for_target(player_id, EDGE_CARRYING)):
                node = self.graph.get_node(edge.source)
                if node and node.name == matched_item:
                    item_node = node
                    break
            if item_node:
                self._register_item_discovery(player_manager, item_node.name)
                from engine.character_spatial import set_position_examining_item
                set_position_examining_item(self.graph, player_manager, target_name, item_node)
                # Phase 3 — see_item save_on hook (e.g. hemophobic + blood/corpse)
                try:
                    player_manager._emit_save_on(
                        player_manager.active_player, "see_item",
                        {"item_tags": item_node.properties.get("tags", []),
                         "source": item_node.name, "source_type": "item"},
                    )
                except Exception:
                    pass
                desc = self._render_node_desc(item_node)

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
                        for etype in (EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT, EDGE_IN):
                            if etype not in related:
                                continue
                            for cn in related[etype]:
                                if cn.properties.get("current_state") == "hidden":
                                    cn.properties["current_state"] = "normal"
                            names = ', '.join(cn.name for cn in related[etype])
                            lines.append(relation_labels[etype].format(target=target_name, names=names))
                        if lines:
                            desc += "\n" + "\n".join(lines)

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
            from engine.character_spatial import set_character_at_way
            if player_manager.active_player:
                pid = player_manager._player_node_id(player_manager.active_player)
                set_character_at_way(self.graph, pid, way_node.id)
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

        visible = []
        if area_id:
            for edge in self.graph.get_edges_for_target(area_id, EDGE_IN):
                node = self.graph.get_node(edge.source)
                if not node:
                    continue
                if node.type == "character":
                    # Don't list yourself; unmet characters keep their
                    # appearance label, never their database name (task-154).
                    pname = node.name
                    if pname == player_manager.active_player:
                        continue
                    p = player_manager.players.get(pname)
                    active_p = player_manager.players.get(player_manager.active_player)
                    if p is not None and active_p is not None and active_p.has_met(pname):
                        visible.append(pname)
                    elif p is not None:
                        visible.append(p.unknown_display_name())
                else:
                    visible.append(node.name)
        player_id = player_manager._player_node_id(player_manager.active_player)
        for edge in self.graph.get_edges_for_target(player_id, EDGE_CARRYING):
            node = self.graph.get_node(edge.source)
            if node:
                visible.append(f"{node.name} (carried)")
        for edge in self.graph.get_edges_for_source(area_id, EDGE_CONNECTION):
            way_node = self.graph.get_node(edge.target)
            d = self.matching.way_handle(
                way_node, edge.properties.get("direction", ""),
                player_manager.current_area.name if player_manager.current_area else "",
            ) if way_node else (edge.properties.get("direction") or "door")
            state = way_node.properties.get("current_state") if way_node else ""
            visible.append(f"{d} ({state})" if state else d)

        # Descriptive fallback: target isn't a real item/exit but appears in area
        # or item descriptions — describe it as flavor text instead of erroring.
        descriptive = self._describe_flavor_target(player_manager, target_name, area_id)
        if descriptive:
            return descriptive

        raise ValueError(
            f"You look for '{target_name}' but don't see it here. "
            f"Things you can examine right now: {', '.join(visible) if visible else 'nothing specific'}."
        )

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
            if node and node.properties.get("description"):
                descriptive_sentences.append(str(node.properties["description"]))
        for edge in self.graph.get_edges_for_source(area_id, EDGE_CONNECTION):
            way_node = self.graph.get_node(edge.target)
            if way_node and way_node.properties.get("description"):
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
