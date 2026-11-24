"""Python Turn Queue scheduler (Phase 3, task-1003).

Mirrors ``static/js/agent/turn-queue.ts``: runtime-derived turn order
(``sequential``, ``random``, or ``initiative`` = d20 + DEX mod).
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional


class TurnQueue:
    def __init__(self, order_mode: str = "sequential") -> None:
        self.order_mode = order_mode
        self.queue: List[str] = []
        self.current_index: int = 0
        self.turn_number: int = 0
        self.initiative_rolls: Dict[str, int] = {}

    def initialize(self, world: Any, *, rng: Optional[random.Random] = None) -> List[str]:
        r = rng or random
        names = [
            name
            for name, p in (getattr(world, "players", None) or {}).items()
            if getattr(p, "state", "awake") != "dead"
        ]
        self.initiative_rolls = {}
        if self.order_mode == "random":
            r.shuffle(names)
        elif self.order_mode == "initiative":
            scored = []
            for n in names:
                p = world.players[n]
                dex = int((getattr(p, "stats", None) or {}).get("DEX", 10) or 10)
                mod = (dex - 10) // 2
                roll = r.randint(1, 20) + mod
                self.initiative_rolls[n] = roll
                scored.append((roll, n))
            scored.sort(key=lambda x: (-x[0], x[1]))
            names = [n for _, n in scored]
        self.queue = names
        self.current_index = 0
        return list(self.queue)

    def current_character(self) -> Optional[str]:
        if not self.queue or self.current_index >= len(self.queue):
            return None
        return self.queue[self.current_index]

    def advance(self) -> Tuple[Optional[str], bool]:
        """Advance to next actor. Returns (next_char, cycle_completed)."""
        if not self.queue:
            return None, False
        self.current_index += 1
        if self.current_index >= len(self.queue):
            self.current_index = 0
            self.turn_number += 1
            return self.current_character(), True
        return self.current_character(), False


from typing import Tuple  # noqa: E402
