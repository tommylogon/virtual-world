"""Game logging and event recording for the virtual world engine.

Stores the game log, speech log, and per-turn event stream used by
the narration system, NPC awareness, and debug output.
"""

import os
import datetime
from collections import deque
from typing import Optional


class GameLogger:
    """Owns the game event log, speech history, and per-turn event buffer.

    This is pure engine state — no dependencies beyond the Python
    standard library.  External subsystems inject their references
    when they need to log or query events.
    """

    def __init__(self):
        # ── Game log (recent text entries shown in the UI) ────────────
        self.game_log: list[str] = []
        """Rolling list of recent log entries (max ~50)."""

        self.log_revision: int = 0
        """Incremented on every ``add_log_entry`` call so the UI can
        cheaply detect new entries."""

        # ── Speech log (circular buffer) ──────────────────────────────
        self.speech_log: deque = deque(maxlen=100)
        """Most recent speech events.  Each entry is a dict with keys
        ``speaker``, ``text``, ``area``, ``tick``, ``timestamp``,
        and ``ghost_speech``."""

        # ── Per-turn event stream ─────────────────────────────────────
        self.turn_events: list[dict] = []
        """Events that occurred during the current turn.  Filtered at the
        start of each new turn to keep only current-turn entries."""

        self.turn_number: int = 0
        """Monotonically increasing turn counter."""

    # ──────────────────────────── Game log ────────────────────────────

    def add_log_entry(self, text: str):
        """Append a line to the game log and bump the revision counter.

        Keeps at most the last 50 entries so the list doesn't grow
        without bound.
        """
        if not text:
            return
        self.game_log.append(text)
        if len(self.game_log) > 50:
            self.game_log.pop(0)
        self.log_revision += 1

    # ───────────────────────── Turn events ────────────────────────────

    def record_turn_event(
        self,
        actor_name: str,
        action_type: str,
        description: str,
        area_name: Optional[str] = None,
        tick: int = 0,
        turn: Optional[int] = None,
    ):
        """Record an event that happened during this turn.

        Parameters
        ----------
        actor_name:
            Name of the player/NPC who performed the action.
        action_type:
            Category label (e.g. ``"move"``, ``"speak"``, ``"emote"``).
        description:
            Human-readable description of the event.
        area_name:
            Area where the event occurred.  If *None*, caller should
            fill it in later.
        tick:
            Current world time tick (from TickManager).
        turn:
            Current turn number.  Defaults to ``self.turn_number``.
        """
        event = {
            "tick": tick,
            "turn": turn or self.turn_number,
            "actor": actor_name,
            "action": action_type,
            "description": description,
            "area": area_name,
        }
        self.turn_events.append(event)
        # Prune events from prior turns
        self.turn_events = [e for e in self.turn_events if e["turn"] == (turn or self.turn_number)]

    def clear_turn_events(self):
        """Clear the event buffer and advance the turn counter."""
        self.turn_events.clear()
        self.turn_number += 1

    def get_turn_events_for_area(
        self,
        area_name: str,
        exclude_actor: Optional[str] = None,
    ) -> list[dict]:
        """Return all turn events that happened in *area_name*.

        If *exclude_actor* is given, events from that actor are omitted
        (useful to avoid an NPC 'seeing' their own actions).
        """
        events = []
        for event in self.turn_events:
            if event.get("area") != area_name:
                continue
            if exclude_actor and event.get("actor") == exclude_actor:
                continue
            events.append(event)
        return events

    # ──────────────────────────── LLM logging ─────────────────────────

    def log_llm_call(
        self,
        label: str,
        prompt: str,
        response: Optional[str] = None,
        player_name: Optional[str] = None,
        active_player: Optional[str] = None,
    ):
        """Log an LLM request/response to the turn event stream.

        Only actually writes when the ``llm_logging`` config flag is
        set.  This method lives here rather than in the skills module
        because it is a pure logging concern consumed by narration,
        combat, and skills alike.

        Parameters
        ----------
        label:
            Short label describing the call site (e.g. ``"process_emote"``).
        prompt:
            The prompt that was sent to the LLM (truncated to 500 chars).
        response:
            The LLM response text (truncated to 500 chars), if any.
        player_name:
            The player who triggered this call.  Falls back to
            *active_player*.
        active_player:
            Current active player name, passed in from the world.
        """
        return

        actor = player_name or active_player or "__system__"
        message = f"[LLM {label}] Prompt: {prompt[:500]}"
        if response is not None:
            message += f"\n[Response] {response[:500]}"

        self.record_turn_event(actor, "llm_log", message)

    # ────────────────────────────── Persist ────────────────────────────

    def save_run_log(
        self,
        players: dict,
        active_player: Optional[str],
        ghost_mode: bool,
        time_ticks: int,
        current_time_str: str,
        graph=None,
        build_exits_fn=None,
        filename: Optional[str] = None,
    ):
        """Save the complete game log and turn events to a file.

        Parameters
        ----------
        players:
            Dict of ``{name: Player}`` — used to render player state.
        active_player:
            Name of the current active player.
        ghost_mode:
            Whether ghost mode is enabled.
        time_ticks:
            Current world tick count.
        current_time_str:
            Human-readable current game time.
        graph:
            Optional WorldGraph.  If provided the areas section is
            rendered with exit information.
        build_exits_fn:
            Optional callable ``(area_name) -> dict`` used together
            with *graph* to render per-area exit info.
        filename:
            Output path; auto-generated if omitted.
        """
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"run_log_{timestamp}.txt"

        with open(filename, "w", encoding="utf-8") as f:
            f.write("=== VIRTUALWORLD RUN LOG ===\n")
            f.write(f"Time: {datetime.datetime.now().isoformat()}\n")
            f.write(f"Ghost Mode: {ghost_mode}\n")
            f.write(f"Active Player: {active_player}\n")
            f.write(f"Turn: {self.turn_number}\n")
            f.write(f"Time Ticks: {time_ticks}\n")
            f.write(f"Game Time: {current_time_str}\n\n")

            f.write("=== PLAYERS ===\n")
            for pname, player_obj in players.items():
                f.write(
                    f"  {pname}: area={player_obj.current_area}, "
                    f"state={player_obj.state}, "
                    f"HP={player_obj.vitals.get('HP', 0)}, "
                    f"Energy={player_obj.vitals.get('Energy', 0)}\n"
                )
            f.write("\n")

            if graph is not None:
                f.write("=== ROOMS ===\n")
                for node in graph.nodes.values():
                    if node.type == "area":
                        exits_info = []
                        if build_exits_fn:
                            exit_dict = build_exits_fn(node.name)
                            for direction, ex in exit_dict.items():
                                exits_info.append(
                                    f"{direction}→{ex['target']}({ex['state']})"
                                )
                        f.write(
                            f"  {node.name}: exits=[{', '.join(exits_info)}]\n"
                        )
                f.write("\n")

            f.write("=== GAME LOG ===\n")
            for entry in self.game_log:
                f.write(f"  {entry}\n")
            f.write("\n")

            f.write("=== TURN EVENTS ===\n")
            for event in self.turn_events:
                f.write(
                    f"  [T{event['tick']}] {event['actor']}: "
                    f"{event['action']} — {event['description']}\n"
                )
            f.write("\n")
            f.write("=== END OF LOG ===\n")

        return filename
