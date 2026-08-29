"""Speech broadcasting — extracted from narration.py (task-322 R1/R2).

Owns everything about delivering a line of speech to listeners:
same-area hearing entries, directed whispers (task-248), cross-area
sound propagation, social vital bumps, closeness hooks (task-94),
spoken-name learning (task-339), log/turn-event recording, and
simple-NPC hearing notification.

NarrationSystem.broadcast_speech is a thin delegate to this module.
"""
import re
import time
from typing import Optional


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
    ):
        self.graph = graph
        self.player_manager = player_manager
        self.logging_events = logging_events
        self.npc_behaviors = npc_behaviors
        self.name_matcher = name_matcher

    # ──────────────────────── Directed-whisper target ──────────────────

    def _resolve_whisper_target(self, speaker_name: str, target_area: str,
                                whisper_target: str) -> Optional[str]:
        """Resolve a directed-whisper recipient among SAME-AREA characters.

        The shared NameMatching resolver maps aliases/partial names to a
        canonical character name first (task-322 R2); the same-area scan
        then enforces the privacy constraint — you can only whisper to
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

    # ──────────────────── Spoken-name learning (task-339) ────────────────

    def _teach_names_from_speech(self, speaker_name: str, speech_text: str,
                                 target_area: str, tick: int) -> None:
        """A name spoken aloud in earshot teaches that name (task-339).

        Scans the line for the real names/aliases of same-area characters;
        every listener who doesn't know a matched character's name yet
        learns it. One mechanism covers self-intros ("hi, I'm rosa"),
        direct address ("hey Miki, look here"), and third-party mentions
        ("order up for rosa!"). Same-area only — muffled speech through a
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
        # candidates = EVERYONE present, speaker included — a self-intro
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

    # ──────────────────────── Broadcasting ─────────────────────────────

    def broadcast_speech(
        self,
        speaker_name: str,
        speech_text: str,
        area_name: Optional[str] = None,
        speech_level: str = "normal",
        whisper_target: Optional[str] = None,
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

        resolved_target = None
        if speech_level == "whisper" and whisper_target:
            resolved_target = self._resolve_whisper_target(
                speaker_name, target_area, whisper_target)

        is_directed_whisper = speech_level == "whisper" and resolved_target is not None

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
        if is_directed_whisper:
            event["whisper_target"] = resolved_target
            # A private aside is an intimate exchange — both parties warm
            # slightly toward each other (task-94: closeness gate).
            tick = event.get("tick", 0) or 0
            if speaker is not None and hasattr(speaker, "update_relationship"):
                speaker.update_relationship(resolved_target, tick, 2)
            target_obj = self.player_manager.get_player(resolved_target)
            if target_obj is not None and hasattr(target_obj, "update_relationship"):
                target_obj.update_relationship(speaker_name, tick, 2)

        # Social gain from conversation
        if speaker_name in self.player_manager.players:
            speaker_obj = self.player_manager.players[speaker_name]
            if getattr(speaker_obj, "current_area", None) == target_area:
                speaker_obj.vitals["Social"] = min(
                    100, speaker_obj.vitals.get("Social", 50) + 5
                )

        for pname, player_obj in self.player_manager.players.items():
            if getattr(player_obj, "current_area", None) != target_area:
                continue
            if pname != speaker_name:
                player_obj.vitals["Social"] = min(
                    100, player_obj.vitals.get("Social", 50) + 3
                )

        # Append to speech log
        self.logging_events.speech_log.append(event)

        # Store in each listener's recent_hearing (same area)
        for pname, player_obj in self.player_manager.players.items():
            if getattr(player_obj, "current_area", None) != target_area:
                continue
            if not hasattr(player_obj, "recent_hearing"):
                player_obj.recent_hearing = []
            # Directed whisper (task-248): only the target hears the words.
            if is_directed_whisper and pname != resolved_target:
                continue
            hearing_entry = dict(event)
            if is_ghost_speech and player_obj.state != "dead":
                hearing_entry["is_ghost"] = True
            player_obj.recent_hearing.append(hearing_entry)
            if len(player_obj.recent_hearing) > 20:
                player_obj.recent_hearing.pop(0)

        # Spoken-name learning (task-339): same-area listeners learn the
        # names of present characters that appear in the line. Never for a
        # directed whisper (the content was private to its target).
        if not is_directed_whisper:
            self._teach_names_from_speech(
                speaker_name, speech_text, target_area, event.get("tick", 0) or 0
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

                        # Add to their recent hearing
                        if not hasattr(player_obj, "recent_hearing"):
                            player_obj.recent_hearing = []

                        hearing_entry = dict(event)
                        hearing_entry["heard_from"] = direction
                        hearing_entry["distance"] = 3 - remaining_pen  # rough distance indicator
                        player_obj.recent_hearing.append(hearing_entry)
                        if len(player_obj.recent_hearing) > 20:
                            player_obj.recent_hearing.pop(0)

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
            self.logging_events.record_turn_event(
                speaker_name, "speak", f'said: "{speech_text}"', area_name=target_area
            )

        # Trigger NPC behaviors for hearing speech. A directed whisper's
        # content is private to its target, so room-wide simple-NPC hearing
        # is skipped for it.
        if target_area and self.npc_behaviors and not is_directed_whisper:
            self.npc_behaviors.process_simple_npcs(
                "on_speech_heard",
                {"spoken_text": speech_text, "speaker": speaker_name},
            )
