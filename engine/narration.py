"""Narration system for the virtual world engine.

Handles LLM-powered emote parsing, speech broadcasting, fumbling in
darkness, and building structured narration context for player-facing
descriptions.
"""

import random
import re
from typing import Optional

from graph import EDGE_IN, EDGE_CONNECTION, EDGE_CARRYING, EDGE_EQUIPPED


#: Reflexive/possessive pronouns from the 1st ("myself") and 2nd ("yourself")
#: persona voices that survive into emotes but read wrong under the narrator's
#: name stamp ("Lyrie hugs yourself tightly."). Rewritten to the ACTOR's
#: pronoun set (identity tags → she/her, he/him, neutral they/them). Word-
#: boundary, ordered so the longer forms win ("yourself" before "your",
#: "myself" before "my").
_PRONOUN_PATTERNS = [
    r"\byourself\b",
    r"\byourselves\b",
    r"\bmyself\b",
    r"\bmeself\b",
    r"\byours\b",
    r"\bmine\b",
    r"\bmy\b",
    r"\byour\b",
]

#: Base-form verbs that arrive un-conjugated when the model writes in first
#: person ("I hug my knees" → "hug my knees"). After the narrator adds the
#: name the leading verb must be third-person singular ("Lyrie hugs...").
_BASE_VERBS = frozenset({
    "hug", "shiver", "sink", "lean", "glance", "run", "reach", "sit", "stand",
    "smile", "sigh", "step", "pull", "tuck", "wrap", "fold", "breathe", "kick",
    "tap", "drum", "shake", "hold", "press", "stretch", "curl", "cry", "laugh",
    "yawn", "nod", "shrug", "wave", "gaze", "stare", "look", "whisper",
    "murmur", "mutter", "peer", "squint", "tremble", "shudder", "flinch",
    "exhale", "inhale", "settle", "crouch", "kneel", "hop", "skip", "dance",
    "twirl", "sway", "wobble", "stumble", "bow", "kiss", "nuzzle", "pat",
    "stroke", "brush", "dig", "push", "nudge", "creep", "pad", "tip",
})


def normalize_emote_person(text: str, pronouns: Optional[dict] = None) -> str:
    """Coerce an emote phrase into the THIRD person the narrator stamps.

    ``process_emote`` prints ``"{actor_name} {text}."``, so ``text`` must never
    carry first/second-person pronouns ("hugs yourself", "hug myself"). Rewrites
    them to the actor's pronoun set (from identity tags; neutral fallback) and
    fixes an un-conjugated leading base-verb ("hug my knees" → "hugs her knees").
    """
    if not text:
        return text
    from engine.pronouns import PRONOUN_SETS, pronouns_for
    p = pronouns or PRONOUN_SETS["neutral"]
    values = [
        p["reflexive"], p["reflexive"], p["reflexive"], p["reflexive"],
        p["possessive_pronoun"], p["possessive_pronoun"],
        p["possessive"], p["possessive"],
    ]
    out = text
    for pattern, repl in zip(_PRONOUN_PATTERNS, values):
        out = re.sub(pattern, repl, out)
    match = re.match(r"^([A-Za-z]+)(\b.*)$", out)
    if match and match.group(1).lower() in _BASE_VERBS:
        out = match.group(1) + "s" + match.group(2)
    return out


class NarrationSystem:
    """Builds and injects narrative descriptions into the game world.

    Most methods mutate player state (vitals, recent hearing) and
    record turn events via injected subsystem references.

    Parameters
    ----------
    graph:
        WorldGraph instance.
    player_manager:
        Must provide ``players``, ``active_player``, ``ghost_mode``,
        ``get_player(name)``, ``get_active_player_obj()``,
        ``current_area``, and ``is_slasher(name)``.
    area_description:
        Must provide ``get_current_area_id()``, ``get_area_items()``,
        and ``build_exits_for_area(area_name)``.
    lighting:
        Must provide ``can_see_in_dark(player_manager, name)``,
        ``get_ambient_light(area_id, env)``, and
        ``light_to_level(value)``.
    tick_manager:
        Must provide ``get_current_time()`` and
        ``apply_action(action_name, override_cost, player)``.
    logging_events:
        Must provide ``add_log_entry(text)``,
        ``record_turn_event(...)``, and
        ``get_turn_events_for_area(area_name, exclude_actor)``,
        as well as the public ``speech_log`` deque attribute.
    skills:
        Must provide ``roll_dice(num_dice, sides, modifier)``,
        ``skill_check(skill_name, dc)``, and
        ``log_llm_call(label, prompt, response, player_name)``.
    node_ids:
        Must provide ``area_node_id(name)`` and
        ``player_node_id(name)`` (see ``NodeIDHelper``).
    npc_behaviors:
        Optional callable ``(trigger_type, extra_context)`` used to
        notify NPCs of speech events.  Typically a bound method on
        the owning VirtualWorld.
    """

    def __init__(
        self,
        graph,
        player_manager,
        area_description,
        lighting,
        tick_manager,
        logging_events,
        skills,
        node_ids,
        npc_behaviors=None,
    ):
        self.graph = graph
        self.player_manager = player_manager
        self.area_description = area_description
        self.lighting = lighting
        self.tick_manager = tick_manager
        self.logging_events = logging_events
        self.skills = skills
        self.node_ids = node_ids
        self.npc_behaviors = npc_behaviors
        # Speech broadcasting lives in engine/speech.py (task-322 R1); the
        # name matcher is injected later via set_name_matcher() when the
        # engine wires it (task-322 R2).
        from engine.speech import SpeechBroadcaster
        self.speech = SpeechBroadcaster(graph, player_manager, logging_events, npc_behaviors)

    def set_name_matcher(self, name_matcher):
        """Inject the shared NameMatching resolver into the speech broadcaster."""
        self.speech.name_matcher = name_matcher

    # ──────────────────────── Emote processing ────────────────────────

    def process_emote(self, actor_name: str, emote_text: str) -> str:
        """Parse a narrative emote via LLM and record it as a area event.

        The LLM receives the actor name, action text, and a list of
        other characters present, and is asked to return a JSON object
        with a ``description`` field.  If the LLM is unreachable the
        raw emote text is used as a fallback.

        Returns the final narrative description string.
        """
        player = self.player_manager.get_player(actor_name)
        area_name = player.current_area if player else None
        clean = emote_text.strip()
        name_lower = actor_name.lower()
        if clean.lower().startswith(name_lower):
            clean = clean[len(actor_name):].strip().lstrip(',.:; ')
        # The emote is printed as "{actor_name} {clean}." — force the phrase
        # into the third person (with the actor's pronoun set from identity
        # tags: she/her, he/him, neutral they/them) so "hugs yourself"/
        # "hug myself" never survive the name stamp.
        from engine.pronouns import pronouns_for
        clean = normalize_emote_person(clean, pronouns_for(player))
        description = f"{actor_name} {clean}." if clean else f"{actor_name} acts."

        self.logging_events.record_turn_event(
            actor_name, "emote", description, area_name=area_name
        )
        return description

    # ──────────────────────── Speech broadcasting ─────────────────────
    # Extracted to engine/speech.py (task-322 R1/R2). Thin delegate kept so
    # existing call sites (VirtualWorld facade, tests) keep working.

    def broadcast_speech(
        self,
        speaker_name: str,
        speech_text: str,
        area_name: Optional[str] = None,
        speech_level: str = "normal",
        whisper_target: Optional[str] = None,
    ):
        """@deprecated delegate — see engine/speech.py SpeechBroadcaster."""
        return self.speech.broadcast_speech(
            speaker_name, speech_text, area_name, speech_level, whisper_target
        )
    # ──────────────────────── Fumble in darkness ──────────────────────

    def _sensory_aid_bonus(self, player_name) -> int:
        """Sum a helper item's bonus from carried/equipped items tagged ``sensory_aid``.

        Items like a guiding cane carry a ``sensory_bonus`` (default 2). The bonus
        raises the chance of ``fumble``/``search`` succeeding and helps a blind
        character navigate. Returns 0 if the character has no such aid.
        """
        try:
            pid = self.player_manager.get_player_node_id(player_name)
        except Exception:
            return 0
        if not pid:
            return 0
        total = 0
        for edge in (list(self.graph.get_edges_for_target(pid, EDGE_CARRYING))
                     + list(self.graph.get_edges_for_target(pid, EDGE_EQUIPPED))):
            node = self.graph.get_node(edge.source)
            if not node:
                continue
            tags = [str(t).lower() for t in (node.properties.get("tags", []) or [])]
            if "sensory_aid" in tags:
                total += int(node.properties.get("sensory_bonus", 2) or 2)
        return total

    def fumble_around(self) -> str:
        """Blindly search in darkness using a Perception check.

        Characters with dark vision or ghost sight skip the check.
        On success (DC 12) a hidden exit or item may be discovered.

        A **blind** character always fumbles (they're in pitch black regardless
        of light) and gains a bonus from any carried `sensory_aid` (e.g. a cane).

        Returns a flavour text string describing the outcome.
        """
        current_area_obj = self.player_manager.current_area
        if not current_area_obj:
            return "You're in an empty void."

        active_player = self.player_manager.active_player
        player_obj = self.player_manager.get_active_player_obj()
        is_blind = bool(player_obj and player_obj.has_condition("blind"))

        # Characters with dark vision / ghosts don't need to fumble — unless blind,
        # for whom the world is pitch black regardless of light or dark vision.
        if not is_blind and self.lighting.can_see_in_dark(self.player_manager, active_player):
            player_check = self.player_manager.get_player(active_player)
            if player_check and player_check.state == "dead":
                return "As a spirit, you perceive the world clearly regardless of light. You can see everything in this area."
            return "Your eyes pierce the darkness with ease. You don't need to fumble."

        if not player_obj or player_obj.state in ("sleeping", "unconscious", "bound", "dead"):
            state = player_obj.state if player_obj else "unknown"
            raise ValueError(f"You can't do that while {state}.")

        area_id = self.area_description.get_current_area_id()
        light = self.lighting.get_ambient_light(
            area_id, current_area_obj.environment
        )
        if not is_blind and light > 40:
            return "You don't need to fumble around — you can see fine."

        self.tick_manager.apply_action(
            "look", {"time": 2, "energy": 3}, player=player_obj
        )

        roll1 = self.skills.roll_dice(1, 20, 0)
        roll2 = self.skills.roll_dice(1, 20, 0)
        roll = min(roll1, roll2)
        perception_mod = player_obj.skills.get("Perception", 0)
        # A guiding cane (sensory_aid) lifts the roll — easier to find the way.
        sensory_bonus = self._sensory_aid_bonus(active_player)
        total = roll + perception_mod + sensory_bonus

        area_node = self.graph.get_node(area_id) if area_id else None
        if not area_node:
            return "You are nowhere."

        # Find undiscovered hidden exits
        undiscovered_exits = []
        for edge in self.graph.get_edges_for_source(area_id, EDGE_CONNECTION):
            direction = edge.properties.get("direction", "")
            way_node = self.graph.get_node(edge.target)
            if not way_node:
                continue
            exit_key = (area_node.name, direction)
            if (
                exit_key not in player_obj.discovered_exits
                and way_node.properties.get("current_state") == "hidden"
            ):
                if not self.player_manager.is_slasher(active_player):
                    undiscovered_exits.append((direction, way_node))

        visible_items = self.area_description.get_area_items()

        if roll == 1:
            player_obj.vitals["HP"] = max(0, player_obj.vitals["HP"] - 1)
            return "[You stumble in the darkness and bang your shin hard on something. Ouch! -1 HP]"

        if total >= 12:
            if undiscovered_exits:
                direction, way_node = random.choice(undiscovered_exits)
                player_obj.discovered_exits.add((area_node.name, direction))
                way_node.properties["current_state"] = "locked"
                self.graph.nodes[way_node.id] = way_node
                self.logging_events.add_log_entry(
                    f"[Discovery] You found a hidden exit: {direction}!"
                )
                return f"[You fumble through the darkness, feeling along the cold walls. Your hand touches something — a door! You think it might be: {direction}]"
            elif visible_items:
                item_name = visible_items[0]
                return f"[You stumble around in the dark and bump into something solid. It might be: {item_name}]"
            else:
                return "[You fumble through the darkness and feel cold, rough walls. There doesn't seem to be anything here...]"
        elif total >= 5:
            return "[You feel around in the darkness but find only cold air and dust. The walls seem featureless...]"
        else:
            return "[You move blindly in the dark, hands outstretched, but only find emptiness. Your anxiety grows in the silence...]"

    def listen(self) -> str:
        """Focused audio scan of the current area.

        Returns the area's ambient noise plus the actor's recent hearing (speech
        and sound sources, including from adjacent rooms). This is the primary
        way a blind character perceives beyond their immediate touch range.
        """
        active = self.player_manager.active_player
        current_area = self.player_manager.current_area
        if not current_area:
            return "You listen, but there's nothing here."
        lines = []
        noise = (current_area.environment or {}).get("noise") or ""
        if noise and str(noise).lower() not in ("quiet", "silence", "silent"):
            lines.append(f"The {current_area.name} is filled with: {noise}.")
        else:
            lines.append(f"The {current_area.name} is quiet.")

        player = self.player_manager.get_player(active)
        hearing = (player.recent_hearing or []) if player else []
        heard_speech = [h for h in hearing
                        if h.get("type") != "sound_source" and h.get("speaker") != active][-5:]
        heard_sounds = [h for h in hearing if h.get("type") == "sound_source"][-3:]
        for h in heard_speech:
            direction = f" from the {h['heard_from']}" if h.get("heard_from") else ""
            lines.append(f"[Heard{direction}] {h.get('speaker')} said: \"{h.get('text')}\"")
        for h in heard_sounds:
            direction = f" from the {h['heard_from']}" if h.get("heard_from") else ""
            src = f" from the {h['source_item']}" if h.get("source_item") else ""
            lines.append(f"[Heard{direction}{src}] {h.get('sound_pattern') or 'a sound'}.")
        return " ".join(lines) if lines else "You hear nothing but silence."

    # ──────────────────── Narration context builders ──────────────────

    def get_narration_context_for_area(self, area_name: Optional[str] = None) -> Optional[dict]:
        """Build a structured context snapshot for narration about a area.

        Returns a dict with keys:
        ``area_name``, ``description``, ``environment``, ``characters``,
        ``items``, ``recent_events``, ``time``, ``turn``, and
        ``light_level``.  Returns *None* if the area does not exist.
        """
        target_area = area_name or (
            self.player_manager.current_area.name
            if self.player_manager.current_area
            else None
        )
        if not target_area:
            return None

        area_node = self.graph.get_node(self.node_ids.area_node_id(target_area))
        if not area_node:
            return None

        # Characters present (include ghosts in ghost mode)
        characters = []
        for pname, player_obj in self.player_manager.players.items():
            if player_obj.current_area != target_area:
                continue
            if player_obj.state != "dead":
                characters.append(
                    {
                        "name": pname,
                        "state": player_obj.state,
                        "personality": (
                            getattr(player_obj, "personality", "")[:200]
                            if getattr(player_obj, "personality", "")
                            else ""
                        ),
                        "description": (
                            getattr(player_obj, "description", "")[:200]
                            if getattr(player_obj, "description", "")
                            else ""
                        ),
                    }
                )
            elif self.player_manager.ghost_mode:
                characters.append(
                    {
                        "name": pname,
                        "state": "ghost",
                        "personality": (
                            getattr(player_obj, "personality", "")[:200]
                            if getattr(player_obj, "personality", "")
                            else ""
                        ),
                        "description": (
                            getattr(player_obj, "description", "")[:200]
                            if getattr(player_obj, "description", "")
                            else ""
                        ),
                    }
                )

        # Items in area
        items = []
        area_node_id = self.node_ids.area_node_id(target_area)
        for edge in self.graph.get_edges_for_target(area_node_id, EDGE_IN):
            node = self.graph.get_node(edge.source)
            if node and node.type == "item" and node.properties.get("current_state") != "hidden":
                items.append(
                    {
                        "name": node.name,
                        "description": node.properties.get("description", "")[:200],
                    }
                )

        env = area_node.properties.get("environment", {})
        recent_events = self.logging_events.get_turn_events_for_area(target_area)

        return {
            "area_name": target_area,
            "description": area_node.properties.get("description", ""),
            "environment": env,
            "characters": characters,
            "items": items,
            "recent_events": [e["description"] for e in recent_events[-3:]],
            "time": self.tick_manager.get_current_time(),
            "turn": self.logging_events.turn_number,
            "light_level": self.lighting.light_to_level(env.get("light", 80)),
        }

    def get_narration_context_for_action(
        self,
        actor_name: str,
        action_type: str,
        description: str,
        area_name: Optional[str] = None,
    ) -> dict:
        """Build context for narrating a specific action.

        Wraps ``get_narration_context_for_area`` and adds the action's
        own metadata (actor, action type, description) at the top level.
        """
        context = {
            "actor": actor_name,
            "action_type": action_type,
            "description": description,
            "area_name": area_name or (
                self.player_manager.current_area.name
                if self.player_manager.current_area
                else None
            ),
            "time": self.tick_manager.get_current_time(),
            "turn": self.logging_events.turn_number,
        }
        area_context = self.get_narration_context_for_area(context["area_name"])
        if area_context:
            context["area_context"] = area_context
        return context

    # ───────────────────────── Narration injection ────────────────────

    def inject_narration(
        self,
        narration_text: str,
        source: str = "player",
        area_name: Optional[str] = None,
        actor_name: Optional[str] = None,
    ):
        """Inject narration text into the event log and turn events.

        Parameters
        ----------
        narration_text:
            The narrative text to inject.
        source:
            ``"player"`` or ``"ai"`` — controls the label prefix.
        area_name:
            Area where the narration occurs.  Defaults to current area.
        actor_name:
            Who is narrating.  Defaults to active player.
        """
        if not narration_text or not narration_text.strip():
            return

        target_area = area_name or (
            self.player_manager.current_area.name
            if self.player_manager.current_area
            else None
        )
        actor = actor_name or self.player_manager.active_player
        source_label = "🎭 Player Narrates" if source == "player" else "🤖 AI Narrates"

        self.logging_events.add_log_entry(f"[{source_label}] {narration_text}")
        self.logging_events.record_turn_event(
            actor,
            "narration",
            f"[{source_label}] {narration_text}",
            area_name=target_area,
        )
