"""Speech broadcasting - extracted from narration.py (task-322 R1/R2).

Owns everything about delivering a line of speech to listeners:
same-area hearing entries, directed whispers (task-248), cross-area
sound propagation, social vital bumps, closeness hooks (task-94),
spoken-name learning (task-339), log/turn-event recording, and
simple-NPC hearing notification.

NarrationSystem.broadcast_speech is a thin delegate to this module.

@module speech
@contributes SpeechBroadcaster
@docs docs/virtualWorld/Gameplay/Turn Queue & Human Turns.md
"""
import re
import time
from typing import Optional, Set

from graph import EDGE_CARRYING, EDGE_EQUIPPED, EDGE_IN


#: How close a bystander must stand to a speaker to catch a directed whisper.
#: "Nearby" is the same area - the whisper's sound penetration is already 0, so
#: nothing crosses a wall. What decides it is the RELATIONSHIP: the people close
#: enough to be leaned toward are the ones close to you, so a whisper is heard by
#: its recipient plus anyone in the room at least this friendly with the speaker.
#: A stranger at the same table hears nothing, which is what makes a whisper worth
#: choosing over a line of talk. Uses the shared band ladder from
#: ``engine.relationships`` so this cannot drift from how the rest of the engine
#: bands closeness.
WHISPER_EAVESDROP_BAND = "friend"


#: Words that make a named place a *direction* rather than an idle mention
#: (task-467). Hearsay should teach where something is, not hand out every place
#: a conversation happens to name.
_DIRECTION_CONTEXT = re.compile(
    r"\b(?:north|south|east|west|northeast|northwest|southeast|southwest|"
    r"up|down|left|right|beyond|past|toward|towards|through|across|along)\b",
    re.IGNORECASE,
)


class SpeechBroadcaster:
    """Delivers speech events to hearers and records them.

    Parameters
    ----------
    graph:
        WorldGraph instance (used for cross-area sound propagation).
    player_manager:
        Must provide ``players``, ``get_player(name)``, ``current_area``.
    logging_events:
        Must provide ``add_log_entry(text)``, ``record_turn_event(...)``,
        and the public ``speech_log`` deque attribute.
    npc_behaviors:
        Optional callable ``(trigger_type, extra_context)`` used to
        notify simple NPCs of room-wide speech.
    name_matcher:
        Optional NameMatching instance used to resolve directed-whisper
        targets leniently (aliases/partial names) before the same-area
        privacy filter applies.
    """

    def __init__(
        self,
        graph,
        player_manager,
        logging_events,
        npc_behaviors=None,
        name_matcher=None,
        trigger_fn=None,
    ):
        self.graph = graph
        self.player_manager = player_manager
        self.logging_events = logging_events
        self.npc_behaviors = npc_behaviors
        self.name_matcher = name_matcher
        self.trigger_fn = trigger_fn  # optional: fires on_speech item triggers
        self.game_state = None        # set by the owning world (trigger game_state)

    # ──────────────────────── Directed-whisper target ──────────────────

    def _resolve_whisper_target(self, speaker_name: str, target_area: str,
                                whisper_target: str) -> Optional[str]:
        """Resolve a directed-whisper recipient among SAME-AREA characters.

        The shared NameMatching resolver maps aliases/partial names to a
        canonical character name first (task-322 R2); the same-area scan
        then enforces the privacy constraint - you can only whisper to
        someone present. Returns the canonical player name or None.
        """
        wanted = str(whisper_target).strip()
        if not wanted:
            return None
        if self.name_matcher is not None and hasattr(self.name_matcher, "_match_character_name"):
            try:
                resolved, _candidates = self.name_matcher._match_character_name(wanted)
            except Exception:
                resolved = None
            if resolved:
                wanted = resolved
        wanted_lower = wanted.lower()
        for pname in self.player_manager.players:
            if pname == speaker_name:
                continue
            p_obj = self.player_manager.players[pname]
            if getattr(p_obj, "current_area", None) != target_area:
                continue
            if pname.lower() == wanted_lower or wanted_lower in pname.lower():
                return pname
        return None

    # ──────────────────── Whisper audience ──────────────────────────

    def _whisper_audience(self, speaker_name: str, target_area: str,
                          resolved_target: str) -> set:
        """Names (besides the speaker) who hear a directed whisper's words.

        The recipient always does. So does anyone standing in the same area who
        is at least ``WHISPER_EAVESDROP_BAND`` friendly with the speaker - the
        people close enough to be "at" them. A stranger at the same table hears
        nothing (they only see the gesture), which is what makes a whisper worth
        choosing over talking to the room.
        """
        from engine.relationships import band_at_least, get_relationship

        audience = {resolved_target}
        for pname, player_obj in self.player_manager.players.items():
            if pname == speaker_name or pname in audience:
                continue
            if getattr(player_obj, "current_area", None) != target_area:
                continue
            rel = get_relationship(player_obj, speaker_name)
            if not rel:
                continue
            if band_at_least(rel.get("closeness", 0), WHISPER_EAVESDROP_BAND):
                audience.add(pname)
        return audience

    # ──────────────────── Spoken-name learning (task-339) ────────────────

    def _teach_names_from_speech(self, speaker_name: str, speech_text: str,
                                 target_area: str, tick: int) -> None:
        """A name spoken aloud in earshot teaches that name (task-339).

        Scans the line for the real names/aliases of same-area characters;
        every listener who doesn't know a matched character's name yet
        learns it. One mechanism covers self-intros ("hi, I'm rosa"),
        direct address ("hey Miki, look here"), and third-party mentions
        ("order up for rosa!"). Same-area only - muffled speech through a
        wall teaches nothing.
        """
        from engine.matching import node_aliases

        present = [
            pname for pname, p_obj in self.player_manager.players.items()
            if getattr(p_obj, "current_area", None) == target_area
        ]
        if speaker_name not in present:
            return

        text_lower = speech_text.lower()
        # candidates = EVERYONE present, speaker included - a self-intro
        # ("hi, I'm rosa") is the speaker's own name in their own line.
        for candidate in present:
            candidate_node = None
            getter = getattr(self.player_manager, "_player_node_id", None)
            if callable(getter):
                try:
                    candidate_node = self.graph.get_node(getter(candidate)) if self.graph else None
                except Exception:
                    candidate_node = None
            patterns = {candidate.lower()}
            if candidate_node is not None:
                for alias in node_aliases(candidate_node):
                    if alias:
                        patterns.add(str(alias).lower())
            matched = None
            for pattern in patterns:
                if re.search(r'(?<!\w)' + re.escape(pattern) + r'(?!\w)', text_lower):
                    matched = candidate
                    break
            if not matched:
                continue

            for listener_name in present:
                if listener_name in (speaker_name, matched):
                    continue
                listener = self.player_manager.players.get(listener_name)
                if listener is None or not hasattr(listener, "learn_name"):
                    continue
                label = None
                try:
                    label = listener.unknown_display_name() if not listener.has_met(matched) else matched
                except Exception:
                    label = matched
                if listener.learn_name(matched, tick):
                    self.logging_events.add_log_entry(
                        f'[{listener_name}] learns that {label} is called "{matched}".'
                    )

    # ──────────────────── Spoken-place learning (task-467) ───────────────

    def _teach_places_from_speech(self, speaker_name: str, speech_text: str,
                                  target_area: str,
                                  audience: Optional[Set[str]] = None) -> None:
        """A direction spoken aloud teaches the place it names (task-467).

        Hearsay is the same operation as a map: a named place enters the
        listener's ``known`` store. The direction gate keeps an idle mention
        ("I like the old mill") from handing out the map; the line has to say
        *where* the place is, not merely name it. Only same-area listeners hear
        it, and the speaker is not taught by their own line.
        """
        if not self.graph or not _DIRECTION_CONTEXT.search(str(speech_text or "")):
            return
        present = [
            pname for pname, p_obj in self.player_manager.players.items()
            if getattr(p_obj, "current_area", None) == target_area
        ]
        if speaker_name not in present:
            return

        from engine.fog import reveal_area

        text_lower = str(speech_text).lower()
        for node in list(self.graph.nodes.values()):
            if getattr(node, "type", "") != "area":
                continue
            name = str(getattr(node, "name", "") or "")
            if not name or name.lower() == str(target_area).lower():
                continue
            if not re.search(r'(?<!\w)' + re.escape(name.lower()) + r'(?!\w)', text_lower):
                continue
            for listener_name in present:
                if listener_name == speaker_name:
                    continue
                if audience is not None and listener_name not in audience:
                    continue
                listener = self.player_manager.players.get(listener_name)
                if listener is None:
                    continue
                if reveal_area(listener, node):
                    self.logging_events.add_log_entry(
                        f'[{listener_name}] learns of the place called "{name}".'
                    )

    # ──────────────────────── Broadcasting ─────────────────────────────

    def _append_hearing_entry(
        self,
        player_obj,
        event: dict,
        *,
        heard_from: Optional[str] = None,
        distance: Optional[int] = None,
        is_ghost_speech: bool = False,
    ) -> dict:
        """Append a listener-filtered hearing entry to *player_obj.recent_hearing*."""
        if not hasattr(player_obj, "recent_hearing"):
            player_obj.recent_hearing = []

        hearing_entry = dict(event)
        if heard_from is not None:
            hearing_entry["heard_from"] = heard_from
        if distance is not None:
            hearing_entry["distance"] = distance
        if is_ghost_speech and getattr(player_obj, "state", None) != "dead":
            hearing_entry["is_ghost"] = True

        utterance_lang = event.get("lang")
        speaker_name = event.get("speaker")
        if utterance_lang and getattr(player_obj, "name", None) != speaker_name:
            from engine.language_barrier import (
                extract_known_names_for_listener,
                mask_text_for_listener,
            )

            known = extract_known_names_for_listener(player_obj)
            masked_text, was_masked = mask_text_for_listener(
                str(event.get("text", "")),
                utterance_lang,
                player_obj,
                graph=self.graph,
                known_names=known,
            )
            if was_masked:
                hearing_entry["text"] = masked_text
                hearing_entry["comprehension_masked"] = True

        # Subjective listener-side tone perception (task-994, task-996): filter speaker
        # intended delivery through speaker body strain, listener mood, closeness,
        # Insight, and spatial proximity (same_area, distance, intra-room hops).
        intended_tone = event.get("tone")
        if intended_tone and getattr(player_obj, "name", None) != speaker_name:
            from engine.speech_tone import perceive_speech_tone

            speaker_obj = self.player_manager.get_player(speaker_name) if speaker_name else None
            same_area = distance is None
            prox_hops = None
            prox_checked = False
            if same_area and self.graph and speaker_name and hasattr(self.player_manager, "get_player_node_id"):
                try:
                    from engine.character_spatial import proximity_hops
                    from graph import EDGE_AT, EDGE_BEHIND, EDGE_BESIDE, EDGE_ON, EDGE_UNDER

                    listener_nid = self.player_manager.get_player_node_id(getattr(player_obj, "name", None))
                    speaker_nid = self.player_manager.get_player_node_id(speaker_name)
                    if listener_nid and speaker_nid:
                        spatial_edges = (EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT)
                        has_anchor = any(
                            e.type in spatial_edges
                            for e in (
                                list(self.graph.get_edges_for_source(listener_nid))
                                + list(self.graph.get_edges_for_source(speaker_nid))
                            )
                        )
                        if has_anchor:
                            prox_checked = True
                            prox_hops = proximity_hops(self.graph, listener_nid, speaker_nid)
                except Exception:
                    prox_hops = None
                    prox_checked = False

            tone_res = perceive_speech_tone(
                intended_tone,
                speaker=speaker_obj,
                listener=player_obj,
                speaker_name=speaker_name,
                same_area=same_area,
                distance=distance,
                proximity_hops=prox_hops,
                proximity_checked=prox_checked,
            )
            hearing_entry["intended_tone"] = tone_res["intended_tone"]
            hearing_entry["perceived_tone"] = tone_res["perceived_tone"]
            if tone_res["strained_leak"]:
                hearing_entry["tone_strained"] = True
            if tone_res["misread_reason"]:
                hearing_entry["tone_misread_reason"] = tone_res["misread_reason"]
            if tone_res["adverb"]:
                hearing_entry["tone_adverb"] = tone_res["adverb"]

        player_obj.recent_hearing.append(hearing_entry)
        if len(player_obj.recent_hearing) > 20:
            player_obj.recent_hearing.pop(0)

        # Live Coupled Emotional Matrix + optional CPU GoEmotions appraisal (task-1001).
        # Runs for non-speaker listeners when the CPU classifier is enabled or the
        # listener already has an active emotion matrix state.
        if (
            getattr(player_obj, "name", None) != speaker_name
            and not hearing_entry.get("comprehension_masked")
            and str(hearing_entry.get("text", "") or "").strip()
        ):
            try:
                from engine.emotion_classifier import appraise_event, get_configured_backend
                from engine.emotion_matrix.schema import EmotionEvent
                from engine.relationships import get_relationship

                backend = get_configured_backend()
                if backend is not None or getattr(player_obj, "_emotion_matrix", None) is not None:
                    rel = get_relationship(player_obj, speaker_name) if speaker_name else None
                    mems = list(getattr(player_obj, "memories", []) or [])[-3:]
                    ev = EmotionEvent(
                        kind="speech",
                        summary=f"{speaker_name or 'Someone'} spoke.",
                        source_name=speaker_name,
                        speech_text=str(hearing_entry.get("text", "")),
                        speech_tone=intended_tone,
                        perceived_tone=hearing_entry.get("perceived_tone") or intended_tone,
                        tone_strained=bool(hearing_entry.get("tone_strained", False)),
                        tick=int(hearing_entry.get("tick", 0) or 0),
                    )
                    appraise_event(
                        player_obj,
                        ev,
                        recalled_memories=mems,
                        rel_profile=rel,
                        force_backend=backend,
                    )
            except Exception:
                pass

        return hearing_entry

    def broadcast_speech(
        self,
        speaker_name: str,
        speech_text: str,
        area_name: Optional[str] = None,
        speech_level: str = "normal",
        whisper_target: Optional[str] = None,
        lang: Optional[str] = None,
        tone: Optional[str] = None,
    ):
        """Broadcast a line of speech to everyone in hearing range.

        Mutates the speaker's and listeners' ``Social`` vital and
        appends hearing entries to each player's ``recent_hearing``
        list.  Also triggers ``on_speech_heard`` NPC behaviors if a
        callback was provided.

        Args:
            speaker_name: Name of the character speaking
            speech_text: The text being spoken
            area_name: Optional area override
            speech_level: "whisper", "normal", "shout", or "scream"
            whisper_target: Optional character name for a DIRECTED whisper
                (task-248). Only that character hears the words; everyone
                else in the area sees the gesture ("X whispers something
                to Y") without the content. Directed whispers do not
                propagate to adjacent areas and do not fire on_speech
                triggers (a door cannot eavesdrop on an aside).
        """
        if not speaker_name or not speech_text:
            return

        from engine.sound import get_areas_hearing_speech, format_heard_narration

        speaker = self.player_manager.get_player(speaker_name)

        # Determine the area
        target_area = None
        if speaker and getattr(speaker, "current_area", None):
            target_area = speaker.current_area
        elif area_name:
            target_area = area_name
        elif self.player_manager.current_area:
            target_area = self.player_manager.current_area.name

        if not target_area:
            return

        # Involuntary flustered volume slip (task-1001): when a speaker with an
        # active emotion matrix tries to whisper while heavily flustered/aroused,
        # their voice can accidentally come out at normal room volume.
        volume_slipped = False
        if speech_level == "whisper" and speaker is not None and getattr(speaker, "_emotion_matrix", None) is not None:
            try:
                from engine.emotion_matrix import compute_involuntary_volume_slip
                st = speaker._emotion_matrix
                slip = compute_involuntary_volume_slip(
                    st.autonomic, st.families, intended_volume=speech_level, player=speaker
                )
                if slip.get("slipped") and slip.get("effective_volume"):
                    speech_level = slip["effective_volume"]
                    volume_slipped = True
            except Exception:
                pass

        resolved_target = None
        if speech_level == "whisper" and whisper_target:
            resolved_target = self._resolve_whisper_target(
                speaker_name, target_area, whisper_target)

        is_directed_whisper = speech_level == "whisper" and resolved_target is not None

        # A directed whisper is heard by its recipient plus same-area friends of
        # the speaker (see _whisper_audience); everyone else sees only the gesture.
        whisper_audience = (
            self._whisper_audience(speaker_name, target_area, resolved_target)
            if is_directed_whisper else None
        )

        from engine.language_barrier import resolve_speaker_language
        from engine.speech_tone import normalize_speech_tone

        utterance_lang = resolve_speaker_language(speaker, explicit_lang=lang, graph=self.graph)
        normalized_tone = normalize_speech_tone(tone)
        is_ghost_speech = speaker and speaker.state == "dead"

        event = {
            "speaker": speaker_name,
            "text": speech_text,
            "area": target_area,
            "tick": int(getattr(self.player_manager, "time_ticks", 0) or 0),
            "timestamp": time.time(),
            "ghost_speech": is_ghost_speech,
            "speech_level": speech_level,
        }
        if volume_slipped:
            event["volume_slipped"] = True
        if utterance_lang:
            event["lang"] = utterance_lang
        if normalized_tone:
            event["tone"] = normalized_tone
        if is_directed_whisper:
            event["whisper_target"] = resolved_target
            event["whisper_audience"] = sorted(whisper_audience - {resolved_target})
            # A private aside is an intimate exchange - both parties warm
            # slightly toward each other (task-94: closeness gate).
            tick = event.get("tick", 0) or 0
            if speaker is not None and hasattr(speaker, "update_relationship"):
                speaker.update_relationship(resolved_target, tick, 2)
            target_obj = self.player_manager.get_player(resolved_target)
            if target_obj is not None and hasattr(target_obj, "update_relationship"):
                target_obj.update_relationship(speaker_name, tick, 2)

        # Social gain from conversation (task-353).
        # chatty gives +2 extra per exchange: speaker +7, listeners +5
        # (instead of the default +5/+3). A speaker with no living listeners
        # gets a small +1 self-talk gain instead of a full +5.
        def _chatty_extra(player_obj) -> int:
            return 2 if player_obj is not None and "chatty" in (getattr(player_obj, "traits", None) or {}) else 0

        living_listeners = [
            pname for pname, player_obj in self.player_manager.players.items()
            if getattr(player_obj, "current_area", None) == target_area
            and pname != speaker_name
            and getattr(player_obj, "state", None) != "dead"
        ]

        if speaker_name in self.player_manager.players:
            speaker_obj = self.player_manager.players[speaker_name]
            if getattr(speaker_obj, "current_area", None) == target_area:
                if living_listeners:
                    gain = 5 + _chatty_extra(speaker_obj)
                else:
                    gain = 1  # talking to yourself still beats total silence
                speaker_obj.vitals["Social"] = min(
                    100, speaker_obj.vitals.get("Social", 50) + gain
                )

        for pname, player_obj in self.player_manager.players.items():
            if getattr(player_obj, "current_area", None) != target_area:
                continue
            if pname != speaker_name:
                player_obj.vitals["Social"] = min(
                    100, player_obj.vitals.get("Social", 50) + 3 + _chatty_extra(player_obj)
                )

        # Append to speech log
        self.logging_events.speech_log.append(event)

        # Store in each listener's recent_hearing (same area)
        for pname, player_obj in self.player_manager.players.items():
            if getattr(player_obj, "current_area", None) != target_area:
                continue
            # Directed whisper: the words reach its audience (recipient + the
            # speaker's same-area friends); everyone else sees only the gesture.
            if is_directed_whisper and pname not in whisper_audience:
                continue
            self._append_hearing_entry(player_obj, event, is_ghost_speech=bool(is_ghost_speech))

        # Spoken-name learning (task-339): same-area listeners learn the
        # names of present characters that appear in the line. Never for a
        # directed whisper (the content was private to its target).
        if not is_directed_whisper:
            self._teach_names_from_speech(
                speaker_name, speech_text, target_area, event.get("tick", 0) or 0
            )
            self._teach_places_from_speech(speaker_name, speech_text, target_area)
        elif whisper_audience:
            self._teach_places_from_speech(
                speaker_name, speech_text, target_area, audience=whisper_audience
            )

        # Propagate sound to adjacent areas (never for a directed whisper)
        if self.graph and not is_directed_whisper:
            areas_dict = {}
            for node in self.graph.nodes.values():
                if node.type == "area":
                    areas_dict[node.id] = node

            # Get area ID from area name
            origin_area_id = None
            for area_id, area_node in areas_dict.items():
                if area_node.name == target_area:
                    origin_area_id = area_id
                    break

            if origin_area_id:
                hearing_areas = get_areas_hearing_speech(
                    origin_area_id, speech_level, self.graph, areas_dict
                )

                # Notify characters in hearing areas
                for area_id, (remaining_pen, direction) in hearing_areas.items():
                    area_node = areas_dict.get(area_id)
                    if not area_node:
                        continue

                    # Find characters in this area
                    for pname, player_obj in self.player_manager.players.items():
                        if getattr(player_obj, "current_area", None) != area_node.name:
                            continue

                        self._append_hearing_entry(
                            player_obj,
                            event,
                            heard_from=direction,
                            distance=3 - remaining_pen,
                        )

                        # Log narration for distant speech
                        narration = format_heard_narration(
                            f'"{speech_text}"', direction, is_speech=True
                        )
                        self.logging_events.add_log_entry(narration)

        if is_directed_whisper:
            # Witnesses see the gesture without the content (task-248).
            self.logging_events.add_log_entry(
                f'[{speaker_name}] whispers to {resolved_target}: "{speech_text}"'
            )
            self.logging_events.record_turn_event(
                speaker_name,
                "speak",
                f'whispers something to {resolved_target}',
                area_name=target_area,
            )
        else:
            self.logging_events.add_log_entry(
                f'[{speaker_name}] says: "{speech_text}"'
            )
            turn_extra = {}
            if utterance_lang:
                turn_extra["lang"] = utterance_lang
            if normalized_tone:
                turn_extra["tone"] = normalized_tone
            self.logging_events.record_turn_event(
                speaker_name,
                "speak",
                f'said: "{speech_text}"',
                area_name=target_area,
                extra=turn_extra or None,
            )

        # Long-distance comms relay (task-299): radios, walkie-talkies, phones.
        if self.graph and not is_directed_whisper:
            try:
                from engine.long_distance_comms import relay_comms_speech
                relay_comms_speech(self, speaker_name, speech_text, event, target_area)
            except Exception:
                import logging as _logging
                _logging.getLogger("speech").exception("comms relay failed")

        # Trigger NPC behaviors for hearing speech. A directed whisper's
        # content is private to its target, so room-wide simple-NPC hearing
        # is skipped for it.
        if target_area and self.npc_behaviors and not is_directed_whisper:
            self.npc_behaviors.process_simple_npcs(
                "on_speech_heard",
                {"spoken_text": speech_text, "speaker": speaker_name},
            )

        # item on_speech triggers (objects that talk back - magic mirrors,
        # radios, doors with opinions). Fired for every item/way/area node
        # in the same area whose trigger system is wired. A directed whisper
        # is private to its target and never fires them.
        if not is_directed_whisper and self.graph and self.trigger_fn:
            try:
                speech_ctx = {
                    "speech": speech_text,
                    "speaker": speaker_name,
                    "area": target_area,
                    "tick": int(getattr(self.player_manager, "time_ticks", 0) or 0),
                }
                target_id = None
                for area_node in self.graph.nodes.values():
                    if area_node.type == "area" and area_node.name == target_area:
                        target_id = area_node.id
                        break
                if target_id:
                    # items placed in the area (in/spatial edges to the area)
                    for edge in self.graph.get_edges_for_target(target_id, EDGE_IN):
                        node = self.graph.get_node(edge.source)
                        if node is not None and node.type == "item":
                            if self.game_state is not None:
                                self.trigger_fn(node, "on_speech", None, speech_ctx, None, self.game_state)
                            else:
                                self.trigger_fn(node, "on_speech", None, speech_ctx)

                    # task-299: on_speech relay extended to carried items
                    for pname, player_obj in self.player_manager.players.items():
                        if getattr(player_obj, "current_area", None) == target_area:
                            pid = self.player_manager.get_player_node_id(pname)
                            if pid:
                                for edge in self.graph.get_edges_for_target(pid, (EDGE_CARRYING, EDGE_EQUIPPED)):
                                    node = self.graph.get_node(edge.source)
                                    if node is not None and node.type == "item":
                                        if self.game_state is not None:
                                            self.trigger_fn(node, "on_speech", None, speech_ctx, None, self.game_state)
                                        else:
                                            self.trigger_fn(node, "on_speech", None, speech_ctx)
            except Exception:
                import logging as _logging
                _logging.getLogger("speech").exception("on_speech trigger fire failed")
