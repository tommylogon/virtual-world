"""Server-side Plan Manager & Tracker (Phase 3, task-1003).

Replaces ``static/js/agent/plan-manager.ts`` + ``plan-tracker.ts`` on the
Python server so plans are generated via ``engine/agent/llm_client.py`` with
the strict ``PLAN`` JSON schema, grounded, tracked across steps, and rendered
directly into ``=== YOUR PLAN ===``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from engine.agent.json_schemas import PLAN
from engine.agent.llm_client import LLMClient
from engine.agent.response_parser import repair_json


@dataclass
class ActivePlan:
    steps: List[str] = field(default_factory=list)
    current_index: int = 0
    created_turn: int = 0


def format_plan_step(step: Dict[str, Any]) -> str:
    """Format a structured PLAN_STEP dict into a concise readable step string."""
    action = str(step.get("action") or "").strip()
    if not action:
        return ""
    parts = [action]
    item = str(step.get("item") or "").strip()
    target = str(step.get("target") or "").strip()
    text = str(step.get("text") or "").strip()
    area = str(step.get("area") or "").strip()
    until = str(step.get("until") or "").strip()
    if item:
        parts.append(item)
    if target and target != item:
        parts.append(target)
    elif action == "speak" and text:
        parts.append(f'"{text}"')
    out = " ".join(parts)
    if area:
        out += f" (in {area})"
    if until:
        out += f" until {until}"
    return out


class PlanManager:
    """Tracks and generates multi-step grounded plans per character."""

    def __init__(self) -> None:
        self._plans: Dict[str, ActivePlan] = {}

    def get_plan(self, char_name: str) -> Optional[ActivePlan]:
        return self._plans.get(char_name)

    def set_plan(self, char_name: str, steps: List[str], turn_number: int = 0) -> ActivePlan:
        cleaned = [s.strip() for s in steps if s and s.strip()][:5]
        plan = ActivePlan(steps=cleaned, current_index=0, created_turn=turn_number)
        self._plans[char_name] = plan
        return plan

    def clear_plan(self, char_name: str) -> None:
        self._plans.pop(char_name, None)

    def advance_if_matched(self, char_name: str, action: str, succeeded: bool) -> None:
        """Advance current step index when the character completes the current step."""
        if not succeeded or not action:
            return
        plan = self._plans.get(char_name)
        if not plan or plan.current_index >= len(plan.steps):
            return
        cur = plan.steps[plan.current_index].lower()
        act_word = action.strip().lower().split()[0]
        if cur.startswith(act_word):
            plan.current_index += 1
            if plan.current_index >= len(plan.steps):
                self._plans.pop(char_name, None)

    def render_plan_block(self, char_name: str) -> str:
        """Render === YOUR PLAN === for prompt inclusion."""
        plan = self._plans.get(char_name)
        if not plan or not plan.steps:
            return (
                "=== YOUR PLAN ===\n"
                "(No active plan - use free action `plan <intent>` to form a grounded multi-step plan, or act directly.)"
            )
        lines: List[str] = []
        for idx, step in enumerate(plan.steps):
            marker = " (CURRENT)" if idx == plan.current_index else (" (DONE)" if idx < plan.current_index else "")
            lines.append(f"{idx + 1}. {step}{marker}")
        return "=== YOUR PLAN ===\n" + "\n".join(lines)

    def generate(
        self,
        llm: LLMClient,
        char_name: str,
        context_prompt: str,
        *,
        intent: str = "",
        turn_number: int = 0,
    ) -> List[str]:
        """Generate a 3-5 step structured plan via LLMClient using strict PLAN schema."""
        intent_line = f"\nGoal / intent: {intent.strip()}" if intent.strip() else ""
        prompt = (
            f"{context_prompt}{intent_line}\n\n"
            "Create a practical 3-5 step plan based ONLY on the items, paths, and people above.\n"
            'Respond ONLY with JSON matching {"steps": [{"action": "...", "item": null, "target": null, "text": null, "note": null, "area": null, "until": null, "duration": null}]}.'
        )
        res = llm.chat([{"role": "user", "content": prompt}], response_format=PLAN)
        obj, _ = repair_json(res.content)
        if not isinstance(obj, dict) or not isinstance(obj.get("steps"), list):
            return []
        formatted = [format_plan_step(s) for s in obj["steps"] if isinstance(s, dict)]
        steps = [s for s in formatted if s][:5]
        if steps:
            self.set_plan(char_name, steps, turn_number=turn_number)
        return steps
