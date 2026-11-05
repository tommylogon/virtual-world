"""Base protocol and data structures for child scope procedural generators (task-884).

Generators produce painted WorldPainter grid layers (biome, road, floor, hazards)
that the existing world compiler turns into simulation graph nodes and ways.

@module base
@contributes GenerationConfig, GenerationResult, ScopeGenerator
@docs docs/virtualWorld/Gameplay/Turn Queue & Human Turns.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol, Tuple


@dataclass
class GenerationConfig:
    seed: int = 42
    budget: int = 100000
    catastrophe: Optional[str] = None  # "collapse", "chasm", "flood", "rot"
    decay_rate: float = 0.15
    district_weights: Dict[str, float] = field(default_factory=dict)


@dataclass
class GenerationResult:
    layers: Dict[str, Dict[str, object]]  # "biome", "road", "floor", "hazards"
    landmarks_placed: Dict[str, Tuple[int, int]]
    budget_spent: int
    cells_painted: int
    report: Dict[str, object] = field(default_factory=dict)


class ScopeGenerator(Protocol):
    def generate(
        self,
        grid_bounds: Tuple[int, int],
        landmarks: Dict[str, Tuple[int, int]],
        config: GenerationConfig,
    ) -> GenerationResult:
        """Generate sparse grid layers for a child scope within grid_bounds (width, height)."""
        ...
