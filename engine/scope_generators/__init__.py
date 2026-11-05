"""Child scope procedural generators package (task-884).

Provides pluggable generators for settlements, subterranean ruins/dungeons,
and wilderness river reaches conforming to WorldPainter grid layer contracts.

@module __init__
@contributes get_generator
@docs none - package initialization
"""

from __future__ import annotations

from typing import Dict, Type
from .base import GenerationConfig, GenerationResult, ScopeGenerator
from .settlement import SettlementGenerator
from .ruin import RuinDungeonGenerator
from .wilderness import WildernessGenerator

GENERATORS: Dict[str, Type[ScopeGenerator]] = {
    "settlement": SettlementGenerator,
    "town": SettlementGenerator,
    "village": SettlementGenerator,
    "ruin": RuinDungeonGenerator,
    "dungeon": RuinDungeonGenerator,
    "cave": RuinDungeonGenerator,
    "wilderness": WildernessGenerator,
    "river": WildernessGenerator,
    "valley": WildernessGenerator,
}


def get_generator(kind: str) -> ScopeGenerator:
    """Retrieve an instantiated scope generator for the requested archetype."""
    normalized = str(kind or "settlement").strip().lower()
    cls = GENERATORS.get(normalized, SettlementGenerator)
    return cls()
