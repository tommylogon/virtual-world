"""VirtualWorld runtime adapter for testing all 3 emotion prototypes as if part of ViWo.

Loads real VirtualWorld scenarios via app.create_app() + WorldSerializer.load_from_dict(),
reads real Player objects, vitals, conditions, traits, goals, derived relationship
profiles (engine/derive.py), and calls real 7-channel associative memory retrieval
(engine/memory_retrieval.py). Never mutates production engine/emotion.py.
"""
from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from prototypes.emotions.coupling import apply_observer_social_influence, dominant_family_and_expression
from prototypes.emotions.proto_a_matrix import ProtoAMatrixEngine
from prototypes.emotions.proto_b_semantic import ProtoBSemanticEngine
from prototypes.emotions.proto_c_dual_mind import ProtoCDualMindEngine
from prototypes.emotions.schema import (
    DIM_TO_FAMILY,
    FAMILIES,
    FAMILY_BASELINES,
    CharacterEmotionState,
    EmotionEvent,
    EmotionPrototype,
    MatrixStepResult,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCENARIOS_DIR = REPO_ROOT / "data" / "scenarios"


def load_real_viwo_world(scenario_name: str = "taco_bell_date") -> Any:
    """Create a real Flask/VirtualWorld instance and load a scenario from data/scenarios/."""
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    from app import create_app

    app = create_app({"TESTING": True})
    world = app.world

    fname = scenario_name if scenario_name.endswith(".json") else f"{scenario_name}.json"
    path = SCENARIOS_DIR / fname
    if not path.exists():
        raise FileNotFoundError(f"Scenario not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    if hasattr(world, "serializer") and hasattr(world.serializer, "load_from_dict"):
        world.serializer.load_from_dict(data)
    elif hasattr(world, "load_from_dict"):
        world.load_from_dict(data)
    else:
        raise RuntimeError("Could not find load_from_dict on VirtualWorld instance")
    return world


def extract_relationship_profile(player: Any, other_name: Optional[str]) -> Dict[str, Any]:
    """Read real closeness + engine.derive.derive_person_profile for (player, other_name)."""
    if not other_name:
        return {}
    out: Dict[str, Any] = {"closeness": 0.0, "trust": 0.0, "fear": 0.0, "disgust": 0.0, "role": "stranger", "summary": ""}
    try:
        from engine.relationships import get_relationship
        rel = get_relationship(player, other_name) or {}
        if "closeness" in rel:
            out["closeness"] = float(rel.get("closeness") or 0.0)
        if rel.get("label"):
            out["label"] = str(rel["label"])
            out["role"] = str(rel["label"])
    except Exception:
        pass
    try:
        from engine.derive import derive_person_profile
        prof = derive_person_profile(player, other_name) or {}
        for key in ("trust", "fear", "disgust", "attraction", "respect", "familiarity", "consent"):
            if key in prof:
                out[key] = float(prof[key] or 0.0)
        if prof.get("role") and str(prof["role"]).lower() != "stranger":
            out["role"] = str(prof["role"])
        elif prof.get("role") and not out.get("label"):
            out["role"] = str(prof["role"])
        if prof.get("summary"):
            out["summary"] = str(prof["summary"])
    except Exception:
        pass
    return out


def retrieve_real_memories(
    player: Any,
    event: EmotionEvent,
    state: CharacterEmotionState,
    world: Any = None,
    max_results: int = 4,
) -> List[Dict[str, Any]]:
    """Query VirtualWorld's real 7-channel memory_retrieval.retrieve_associative_memories."""
    from engine.memory_retrieval import retrieve_associative_memories

    dom_fam, _ = dominant_family_and_expression(state.families)
    people = [p for p in ([event.source_name] + list(event.witnesses)) if p]
    dialogue = []
    if event.speech_text:
        dialogue.append({"speaker": event.source_name or "", "text": event.speech_text})
    payload = {
        "query": f"{event.summary} {event.speech_text}".strip(),
        "people": people,
        "area": getattr(player, "current_area", "") or "",
        "dialogue": dialogue,
        "emotion": {"current": dom_fam},
        "emotions": state.to_36_dim_map(),
        "tags": list(event.tags),
    }
    res = retrieve_associative_memories(
        player,
        payload,
        world=world,
        tick=event.tick or getattr(world, "time_ticks", 0),
        max_results=max_results,
        min_score=0.5,
        do_reinforce=False,
    )
    items = list(res.get("memories") or [])
    # Ensure each item exposes a readable dict with text + memory_emotions + _score.
    normalized: List[Dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict):
            normalized.append(item)
    return normalized


def add_emotional_memory(
    player: Any,
    text: str,
    *,
    tick: int,
    importance: int = 7,
    tags: Optional[List[str]] = None,
    emotion: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Add a memory via Player.add_memory and attach real ViWo emotion metadata.

    engine/memory_retrieval.py:_mem_emotion_entries reads both entry['emotion']
    and entry['memory_emotions']. Player.add_memory does not take an emotion
    kwarg, so we attach it onto the returned entry dict without altering player.py.
    """
    entry = player.add_memory(
        text,
        tick=tick,
        importance=importance,
        tags=list(tags or []),
    )
    if emotion:
        emo = dict(emotion)
        entry["emotion"] = emo
        entry["memory_emotions"] = [emo]
    return entry


def sync_state_to_viwo_player(player: Any, state: CharacterEmotionState) -> None:
    """Write the prototype's projected 36-dim map back onto the live ViWo Player."""
    if hasattr(player, "load_emotions"):
        player.load_emotions(state.to_36_dim_map())


def seed_state_from_viwo_player(player: Any) -> CharacterEmotionState:
    """Initialize a CharacterEmotionState from an existing ViWo Player's affect map.

    Compares each 36-dim value against its actual ViWo engine.emotion.BASELINES
    value so default non-zero dimensions (like curious=35 or admiring=30) do not
    falsely seed elevated arousal or love above FAMILY_BASELINES.
    """
    from engine.emotion import BASELINES

    st = CharacterEmotionState()
    raw_map = player.emotions_map() if hasattr(player, "emotions_map") else {}
    best_delta: Dict[str, float] = {}
    for dim, val in (raw_map or {}).items():
        fam = DIM_TO_FAMILY.get(dim)
        if not fam:
            continue
        try:
            fval = float(val)
        except (TypeError, ValueError):
            continue
        dim_base = float(BASELINES.get(dim, FAMILY_BASELINES[fam]))
        delta = fval - dim_base
        if fam not in best_delta or abs(delta) > abs(best_delta[fam]):
            best_delta[fam] = delta
    for fam, delta in best_delta.items():
        if abs(delta) >= 1.0:
            st.families[fam] = max(0.0, min(100.0, FAMILY_BASELINES[fam] + delta))
    return st


class ViwoEmotionHarness:
    """Runs any of Prototypes A, B, or C against a real VirtualWorld instance."""

    def __init__(
        self,
        world: Any,
        engine: EmotionPrototype,
        *,
        sync_to_player: bool = True,
    ):
        self.world = world
        self.engine = engine
        self.sync_to_player = sync_to_player
        self.states: Dict[str, CharacterEmotionState] = {}
        self.history: List[Dict[str, Any]] = []

    def get_state(self, char_name: str) -> CharacterEmotionState:
        if char_name not in self.states:
            player = self.world.players.get(char_name)
            self.states[char_name] = (
                seed_state_from_viwo_player(player) if player is not None else CharacterEmotionState()
            )
        return self.states[char_name]

    def set_human_override_mode(self, char_name: str, enabled: bool) -> None:
        self.get_state(char_name).human_override_mode = bool(enabled)

    def apply_human_override(self, char_name: str, adjustments: Dict[str, float]) -> Dict[str, float]:
        """Director/Adjustable mode only: adjust family levels if human_override_mode is on."""
        st = self.get_state(char_name)
        if not st.human_override_mode:
            raise PermissionError(
                f"{char_name} is in Embodied mode; enable human_override_mode (Director override) to manually adjust emotions."
            )
        for fam, val in adjustments.items():
            if fam in st.families:
                st.families[fam] = max(0.0, min(100.0, float(val)))
        player = self.world.players.get(char_name)
        if player is not None and self.sync_to_player:
            sync_state_to_viwo_player(player, st)
        return dict(st.families)

    def step_event(
        self,
        char_name: str,
        event: EmotionEvent,
        *,
        override_rel: Optional[Dict[str, Any]] = None,
        extra_memories: Optional[List[Dict[str, Any]]] = None,
    ) -> MatrixStepResult:
        player = self.world.players[char_name]
        st = self.get_state(char_name)

        # Auto-discover co-located witnesses from real ViWo room occupancy when not explicitly supplied.
        if not event.witnesses:
            area = getattr(player, "current_area", None)
            if area:
                witnesses = [
                    other_name
                    for other_name, other_p in self.world.players.items()
                    if other_name != char_name
                    and other_name != event.source_name
                    and getattr(other_p, "current_area", None) == area
                ]
                if witnesses:
                    event = copy.copy(event)
                    event.witnesses = witnesses

        recalled = retrieve_real_memories(player, event, st, world=self.world)
        if extra_memories:
            seen = {m.get("id") or m.get("text") for m in recalled}
            for em in extra_memories:
                key = em.get("id") or em.get("text")
                if key not in seen:
                    recalled.append(em)

        rel_profile = override_rel if override_rel is not None else extract_relationship_profile(player, event.source_name)

        # Subjective listener-side speech tone perception (task-994):
        # filter speaker's intended speech_tone through speaker involuntary body strain,
        # listener prior moodiness, closeness, and Insight.
        tone_info: Optional[Dict[str, Any]] = None
        if event.speech_tone and event.perceived_tone is None:
            from engine.speech_tone import perceive_speech_tone

            speaker_obj = self.world.players.get(event.source_name) if event.source_name else None
            speaker_st = self.states.get(event.source_name) if event.source_name else None
            spk_auto = event.speaker_autonomic if event.speaker_autonomic is not None else (
                speaker_st.autonomic if speaker_st is not None else None
            )
            spk_over = bool(event.speaker_overloaded or (speaker_st is not None and speaker_st.overload_streak > 0))
            tone_info = perceive_speech_tone(
                event.speech_tone,
                speaker=speaker_obj,
                listener=player,
                speaker_name=event.source_name,
                speaker_autonomic=spk_auto,
                speaker_overloaded=spk_over,
                listener_families=st.families,
                closeness=float(rel_profile.get("closeness", 0.0) or 0.0),
                same_area=event.same_area,
                distance=event.distance,
                proximity_hops=event.proximity_hops,
                proximity_checked=event.proximity_checked,
            )
            event = copy.copy(event)
            event.perceived_tone = tone_info["perceived_tone"]
            event.tone_strained = bool(tone_info["strained_leak"])
            event.tone_perception_note = str(tone_info["perception_note"] or "")

        result = self.engine.process_event(
            st, event, player, self.world, recalled, rel_profile=rel_profile
        )
        if tone_info is not None:
            result.metadata["speech_tone"] = tone_info
        elif event.speech_tone or event.perceived_tone:
            result.metadata["speech_tone"] = {
                "intended_tone": event.speech_tone,
                "perceived_tone": event.perceived_tone,
                "strained_leak": event.tone_strained,
                "perception_note": event.tone_perception_note,
            }
        if self.sync_to_player:
            sync_state_to_viwo_player(player, st)

        self.history.append(
            {
                "character": char_name,
                "event": {"kind": event.kind, "summary": event.summary, "speech": event.speech_text},
                "result": result.to_dict(),
            }
        )
        return result

    def tick_all(self, ticks: int = 1) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for char_name, st in self.states.items():
            player = self.world.players.get(char_name)
            if player is None:
                continue
            out[char_name] = self.engine.tick(st, player, self.world, ticks=ticks)
            if self.sync_to_player:
                sync_state_to_viwo_player(player, st)
        return out

    def propagate_observer_influence(
        self,
        observer_name: str,
        target_name: str,
        *,
        tick: int = 0,
    ) -> Dict[str, float]:
        obs_p = self.world.players[observer_name]
        tgt_p = self.world.players[target_name]
        obs_st = self.get_state(observer_name)
        tgt_st = self.get_state(target_name)
        rel = extract_relationship_profile(obs_p, target_name)
        deltas = apply_observer_social_influence(
            obs_st,
            obs_p,
            tgt_st,
            tgt_p,
            closeness=float(rel.get("closeness", 0.0) or 0.0),
            tick=tick,
        )
        if self.sync_to_player and deltas:
            sync_state_to_viwo_player(obs_p, obs_st)
        return deltas


def build_engine(
    key: str,
    *,
    offline: bool = False,
    limbic_model: str = "qwen3.5-2b",
    embedding_model: str = "text-embedding-qwen3-embedding-0.6b",
) -> EmotionPrototype:
    k = key.strip().lower()
    if k in ("a", "proto_a", "matrix"):
        return ProtoAMatrixEngine()
    if k in ("b", "proto_b", "semantic"):
        return ProtoBSemanticEngine(model_id=embedding_model, offline=offline)
    if k in ("c", "proto_c", "dual", "dual_mind"):
        return ProtoCDualMindEngine(limbic_model=limbic_model, offline=offline)
    raise ValueError(f"Unknown prototype key: {key!r} (expected 'a', 'b', or 'c')")
