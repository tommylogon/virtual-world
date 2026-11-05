"""Engine-owned turn order resolution and modes (task-437).

Resolves character turn ordering deterministically by mode:
- 'sequential': stable canonical ordering by character ID
- 'random': deterministic seeded shuffle per round
- 'initiative': deterministic seeded d20 + DEX bonus per round
- 'simultaneous': snapshot evaluation with deterministic commit

@module turn_order
@contributes TurnOrderResolver
@docs docs/virtualWorld/Gameplay/Turn Queue & Human Turns.md
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

MODES = ("sequential", "random", "initiative", "simultaneous")
DEFAULT_MODE = "sequential"


class TurnOrderResolver:
    """Deterministic turn order solver owned by the engine."""

    def __init__(self, mode: str = DEFAULT_MODE, seed: Optional[int] = 42):
        self.mode = mode if mode in MODES else DEFAULT_MODE
        self.seed = seed or 42
        self._current_order: List[str] = []
        self._initiative_rolls: Dict[str, int] = {}
        self._round_number: int = 0

    def set_mode(self, mode: str):
        if mode in MODES:
            self.mode = mode

    def resolve(
        self,
        characters: Dict[str, Any],
        round_number: int = 0,
        ghost_mode: bool = False,
    ) -> List[str]:
        """Resolve character turn order for round_number by character ID.

        Returns a list of character IDs.
        """
        self._round_number = round_number
        valid_ids = []
        for cid, char in characters.items():
            state = getattr(char, "state", None) or (char.get("state") if isinstance(char, dict) else "")
            if not ghost_mode and state == "dead":
                continue
            valid_ids.append(cid)

        # Canonical base ordering by ID ensures invariance to input dict order
        valid_ids.sort()

        if not valid_ids:
            self._current_order = []
            self._initiative_rolls = {}
            return []

        # Derive round-specific seed
        round_seed = (self.seed + round_number * 31337) & 0xFFFFFFFF
        rng = random.Random(round_seed)

        if self.mode == "sequential":
            self._current_order = list(valid_ids)
            self._initiative_rolls = {}
        elif self.mode == "random":
            shuffled = list(valid_ids)
            rng.shuffle(shuffled)
            self._current_order = shuffled
            self._initiative_rolls = {}
        elif self.mode == "initiative":
            rolls: Dict[str, int] = {}
            for cid in valid_ids:
                char = characters[cid]
                stats = getattr(char, "stats", None) or (char.get("stats") if isinstance(char, dict) else {}) or {}
                dex = stats.get("DEX", 10) if isinstance(stats, dict) else 10
                bonus = (dex - 10) // 2
                d20 = rng.randint(1, 20)
                rolls[cid] = d20 + bonus
            self._initiative_rolls = rolls
            self._current_order = sorted(valid_ids, key=lambda c: (-rolls.get(c, 0), c))
        elif self.mode == "simultaneous":
            # Simultaneous: execution is order-invariant, commit is deterministic
            self._current_order = list(valid_ids)
            self._initiative_rolls = {}

        return list(self._current_order)

    @property
    def current_order(self) -> List[str]:
        return list(self._current_order)

    @property
    def initiative_rolls(self) -> Dict[str, int]:
        return dict(self._initiative_rolls)

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "round": self._round_number,
            "order": list(self._current_order),
            "initiative_rolls": dict(self._initiative_rolls),
        }
