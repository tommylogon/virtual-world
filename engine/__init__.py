"""__init__ module.

@module __init__
@contributes module initialization and namespace exports
@docs none - package initialization
"""

from .equipment import EquipmentSystem
from .combat import CombatSystem
from .player_manager import PlayerManager
from .matching import NameMatching
from .npc_behaviors import NPCBehaviorSystem
from .movement import MovementSystem
from .node_ids import NodeIDHelper
from .logging_events import GameLogger
from .skills import SkillSystem
from .legacy_compat import LegacyCompat
from .narration import NarrationSystem
from .spatial_memory import SpatialMemory

__all__ = [
    "EquipmentSystem",
    "CombatSystem",
    "PlayerManager",
    "NameMatching",
    "NPCBehaviorSystem",
    "MovementSystem",
    "NodeIDHelper",
    "GameLogger",
    "SkillSystem",
    "LegacyCompat",
    "NarrationSystem",
    "SpatialMemory",
]
