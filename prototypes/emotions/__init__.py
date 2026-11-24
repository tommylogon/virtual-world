"""VirtualWorld Emotion System Prototypes (A, B, C, and D Unified).

Isolated sandbox package implementing four appraisal/emotion architectures
tested directly against real VirtualWorld worlds, players, vitals,
relationships, and associative memory retrieval without mutating production
engine/emotion.py.
"""
from prototypes.emotions.proto_a_matrix import ProtoAMatrixEngine
from prototypes.emotions.proto_b_semantic import ProtoBSemanticEngine
from prototypes.emotions.proto_c_dual_mind import ProtoCDualMindEngine
from prototypes.emotions.proto_d_unified import ProtoDUnifiedEngine
from prototypes.emotions.schema import (
    AUTONOMIC_CHANNELS,
    DBT_FAMILIES,
    EMOTION_PROFILES,
    FAMILIES,
    CharacterEmotionState,
    EmotionEvent,
    MatrixStepResult,
)

__all__ = [
    "AUTONOMIC_CHANNELS",
    "DBT_FAMILIES",
    "EMOTION_PROFILES",
    "FAMILIES",
    "CharacterEmotionState",
    "EmotionEvent",
    "MatrixStepResult",
    "ProtoAMatrixEngine",
    "ProtoBSemanticEngine",
    "ProtoCDualMindEngine",
    "ProtoDUnifiedEngine",
]
