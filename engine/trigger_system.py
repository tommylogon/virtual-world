"""Trigger system for the virtual world engine.

Manages trigger registration, condition evaluation, and effect execution
for item interactions, NPC behaviors, and world events.
"""

from typing import Optional

from graph import Node, Edge, EDGE_IN, EDGE_CARRYING, EDGE_EQUIPPED, EDGE_TRIGGERS, EDGE_CONNECTION
from .effects import Effects
from .item_actions import normalize_item_actions

from engine.triggers.behaviors import BehaviorMixin
from engine.triggers.condition_tree import ConditionTreeMixin
from engine.triggers.constants import EFFECT_TYPES, TRIGGER_TYPES, SAFE_EFFECT_TYPES
from engine.triggers.effect_resolution import (
    _effects_list_from_properties,
    _legacy_effects_from_properties,
    _resolve_trigger_effects,
)
from engine.triggers.evaluation import EvaluationMixin
from engine.triggers.execution import ExecutionMixin
from engine.triggers.testing import TestingMixin
from engine.triggers.ui import UiMixin


__all__ = [
    "EFFECT_TYPES",
    "TRIGGER_TYPES",
    "SAFE_EFFECT_TYPES",
    "TriggerSystem",
    "_effects_list_from_properties",
    "_legacy_effects_from_properties",
    "_resolve_trigger_effects",
]


class TriggerSystem(
    BehaviorMixin,
    EvaluationMixin,
    ConditionTreeMixin,
    ExecutionMixin,
    TestingMixin,
    UiMixin,
):
    """Evaluates trigger conditions and executes their effects.

    Depends on a WorldGraph, a skill-check service, and a logging
    callback.  All three are injected via the constructor.

    Most public methods accept a *game_state* object (duck-typed)
    that provides access to the mutable world state -- player data,
    area helpers, scenario flags, etc.
    """

    def __init__(self, graph, skills, logging_events):
        """Initialise the trigger system.

        Parameters
        ----------
        graph : WorldGraph
            The world graph instance.
        skills : object
            An object providing a ``skill_check(skill_name, dc)`` method.
        logging_events : object
            An object providing an ``add_log_entry(text)`` method.
        """
        self.graph = graph
        self.skills = skills
        self.logging_events = logging_events
        self._last_skill_check_msg: Optional[str] = None
        self._last_save_msg: Optional[str] = None
        self._effects = Effects(graph, logging_events)
        self._effects.set_trigger_system(self)

    # ─────────────────── Trigger authoring (task-242) ───────────────────

    def create_trigger(self, node_id, trigger_type, effects=None, conditions=None,
                       conditions_logic="and", target_name="", target_state=""):
        """Create a logic_trigger node + triggers edge on a graph node.

        Used by runtime trigger authoring (agents' `bind` action) and reuses
        the same node/edge shape the human editor writes, so it serializes
        and shows up in the trigger editor/graph like any hand-made trigger.

        Returns the new trigger node id.
        """
        import time as _t
        import random as _r
        effects = effects or [{"type": "message", "params": {}}]
        first_effect = effects[0].get("type", "message") if effects else "message"
        trigger_id = (
            f"trigger_{node_id}_{trigger_type}_"
            f"{int(_t.time() * 1000)}_{_r.randint(0, 999)}"
        )
        props = {
            "trigger_type": trigger_type,
            "conditions": conditions or {},
            "conditions_logic": conditions_logic,
            "effects": effects,
            "target_name": target_name,
            "target_state": target_state,
        }
        self.graph.add_node(Node(id=trigger_id, type="logic_trigger",
                                 name=f"{trigger_type} → {first_effect}",
                                 properties=props))
        # triggers edge (the engine reads edge properties)
        self.graph.add_edge(Edge(
            source=node_id, target=trigger_id, type=EDGE_TRIGGERS,
            properties=dict(props),
        ))
        return trigger_id
