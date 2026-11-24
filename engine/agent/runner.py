"""Headless Python AgentRunner (Phase 3, task-1003).

Runs think-decide -> action/speech execution -> optional react phase directly
against ``VirtualWorld`` using ``LLMClient``, ``prompt_builder``, and
``parse_turn_response``. Enables 2-second multi-actor ``pytest`` runs and
server-side SSE turn execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from engine.agent.involuntary import apply_involuntary_emote, apply_involuntary_speech
from engine.agent.json_schemas import AGENT_ACTION, AGENT_REACT
from engine.agent.llm_client import LLMClient
from engine.agent.memory_manager import MemoryManager
from engine.agent.plan_manager import PlanManager
from engine.agent.prompt_builder import (
    build_result_reaction_messages,
    build_think_decide_messages,
)
from engine.agent.response_parser import ParsedTurn, parse_turn_response
from engine.agent.turn_queue import TurnQueue


@dataclass
class StepOutcome:
    character: str
    parsed: ParsedTurn
    action_result: str = ""
    react_parsed: Optional[ParsedTurn] = None
    cycle_completed: bool = False


class AgentRunner:
    """Server-side multi-actor turn runner."""

    def __init__(self, world: Any, llm: LLMClient, *, order_mode: str = "sequential") -> None:
        self.world = world
        self.llm = llm
        self.turn_queue = TurnQueue(order_mode=order_mode)
        self.plan_manager = PlanManager()
        self.memory_manager = MemoryManager()
        self.last_results: Dict[str, str] = {}

    def _format_command(self, parsed: ParsedTurn) -> str:
        if not parsed.action or parsed.action.lower() == "wait":
            return ""
        parts = [parsed.action]
        if parsed.item:
            parts.append(parsed.item)
        if parsed.target:
            if parsed.action.lower() == "use_on":
                parts.append("on")
            parts.append(parsed.target)
        return " ".join(parts)

    def step_character(self, char_name: str, *, run_react: bool = False) -> StepOutcome:
        """Execute one full turn for ``char_name`` directly on ``self.world``."""
        msgs = build_think_decide_messages(
            self.world,
            char_name,
            last_result=self.last_results.get(char_name, ""),
        )
        llm_res = self.llm.chat(msgs, response_format=AGENT_ACTION)
        parsed = parse_turn_response(llm_res.content, allow_action=True)

        # Broadcast speech (with delivery tone + involuntary flavor!) if present
        if parsed.speech and hasattr(self.world, "broadcast_speech"):
            player_obj = self.world.players.get(char_name)
            spoken = apply_involuntary_speech(parsed.speech, player_obj) if player_obj else parsed.speech
            if player_obj and parsed.emote:
                parsed.emote = apply_involuntary_emote(parsed.emote, player_obj)
            self.world.broadcast_speech(
                char_name,
                spoken,
                speech_level=parsed.speech_volume or "normal",
                whisper_target=parsed.speech_target,
                tone=parsed.speech_tone,
            )

        # Execute physical action or agentic plan
        action_result = ""
        if parsed.action and parsed.action.lower() in ("plan", "replan"):
            intent = parsed.item or parsed.target or parsed.inner or ""
            steps = self.plan_manager.generate(
                self.llm,
                char_name,
                msgs[1]["content"],
                intent=intent,
                turn_number=self.turn_queue.turn_number,
            )
            action_result = (
                "Plan formed: " + " -> ".join(steps)
                if steps
                else "You pause to gather your thoughts."
            )
        else:
            cmd = self._format_command(parsed)
            if cmd and hasattr(self.world, "process_command"):
                prev = getattr(self.world, "active_player", None)
                self.world.active_player = char_name
                try:
                    action_result = str(self.world.process_command(cmd) or "")
                finally:
                    if prev is not None:
                        self.world.active_player = prev
                self.plan_manager.advance_if_matched(char_name, cmd, bool(action_result))

        self.last_results[char_name] = action_result

        react_parsed = None
        if run_react and action_result:
            r_msgs = build_result_reaction_messages(
                self.world, char_name, what_happened=action_result
            )
            r_res = self.llm.chat(r_msgs, response_format=AGENT_REACT)
            react_parsed = parse_turn_response(r_res.content, allow_action=False)

        return StepOutcome(
            character=char_name,
            parsed=parsed,
            action_result=action_result,
            react_parsed=react_parsed,
        )

    def step_next(self, *, run_react: bool = False) -> Optional[StepOutcome]:
        """Run the next character in the turn queue and advance."""
        if not self.turn_queue.queue:
            self.turn_queue.initialize(self.world)
        char_name = self.turn_queue.current_character()
        if not char_name:
            return None
        outcome = self.step_character(char_name, run_react=run_react)
        _, cycle_done = self.turn_queue.advance()
        outcome.cycle_completed = cycle_done
        if cycle_done and hasattr(self.world, "tick_turn"):
            self.world.tick_turn()
        return outcome
