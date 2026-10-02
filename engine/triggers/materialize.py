"""Runtime compilation of trigger / blueprint definitions into graph nodes (task-442).

A **blueprint** is a saved trigger graph in ``data/library/triggers/*.json``.
The editor compiles that graph to the JSON contract below with
``TriggerGraph.compileToEngine``; this module is the Python side of the same
contract — it turns one definition into an ordinary ``logic_trigger`` node plus
a ``triggers`` edge, exactly the shape the rest of the engine already reads. No
parallel trigger format is introduced.

JSON contract (a *trigger definition*)::

    {
      "trigger_type": "on_use" | ["on_use", "on_eat"],   # TRIGGER_TYPES
      "effects": [{"type": "message", "params": {...}}], # preferred, ordered
      "effect_type": "message", "effect_params": {},     # legacy single-effect
      "conditions": {"operator": "and"|"or"|"not", "conditions": [...]},
      "conditions_logic": "and"|"or",                    # flat-list combiner
      "condition": {...},                                # legacy singular leaf
      "target_name": "", "target_tag": "", "target_state": "",
      "success_message": "", "fail_message": "",
      "once": false
    }

The same property dict is written to **both** the ``logic_trigger`` node and the
``triggers`` edge: ``_execute_triggers`` reads the edge first and falls back to
the node (``engine/triggers/execution.py``), while the inspector and item
library read whichever copy is convenient. Writing both keeps every reader
honest and is what the existing materialisers do.

Condition branching: ``conditions`` may be a tree (the engine evaluates
and/or/not recursively) or a flat list combined with ``conditions_logic``. The
materialiser stores it verbatim, so a blueprint with a condition branch reaches
the engine unchanged — the compile-fidelity half lives in the editor
(task-501/task-502), not here.
"""

from typing import Any, Callable, Dict, List, Optional

from graph import Edge, EDGE_TRIGGERS, Node

#: Top-level definition keys copied onto the node/edge when non-empty.
_PASSTHROUGH = (
    "target_name",
    "target_tag",
    "target_state",
    "success_message",
    "fail_message",
)

#: Factory signature: ``(owner_id, trigger_def, index, props) -> trigger_id``.
IdFactory = Callable[[str, dict, Optional[int], dict], str]


def _nonempty(value: Any) -> bool:
    return value not in (None, "", [], {})


def trigger_properties(trigger_def: dict, extra: Optional[dict] = None) -> Dict[str, Any]:
    """Normalise a trigger definition into the node/edge property dict.

    Empty/absent keys are dropped so a materialised trigger carries only what it
    means — an empty ``conditions`` must not mask the legacy singular
    ``condition`` fallback in ``_execute_triggers``.
    """
    t = dict(trigger_def or {})
    props: Dict[str, Any] = {}

    if _nonempty(t.get("trigger_type")):
        props["trigger_type"] = t["trigger_type"]
    for key in _PASSTHROUGH:
        if _nonempty(t.get(key)):
            props[key] = t[key]

    effects = t.get("effects")
    if isinstance(effects, list) and effects:
        props["effects"] = effects
    elif _nonempty(t.get("effect_type")):
        props["effect_type"] = t["effect_type"]
        props["effect_params"] = t.get("effect_params") or {}

    if _nonempty(t.get("conditions")):
        props["conditions"] = t["conditions"]
        if _nonempty(t.get("conditions_logic")):
            props["conditions_logic"] = t["conditions_logic"]
    if _nonempty(t.get("condition")):
        props["condition"] = t["condition"]

    if t.get("once"):
        props["once"] = True
    if _nonempty(t.get("name")):
        props["name"] = t["name"]
    if extra:
        props.update(extra)
    return props


def _default_name(props: dict) -> str:
    tt = props.get("trigger_type", "on_examine")
    if isinstance(tt, (list, tuple)):
        tt = tt[0] if tt else "on_examine"
    effects = props.get("effects") or []
    first = effects[0].get("type") if effects and isinstance(effects[0], dict) else None
    first = first or props.get("effect_type", "message")
    return f"{tt} → {first}"


def materialize_trigger(
    graph,
    owner_id: str,
    trigger_def: dict,
    *,
    index: Optional[int] = None,
    extra: Optional[dict] = None,
    id_factory: Optional[IdFactory] = None,
) -> str:
    """Create a ``logic_trigger`` node + ``triggers`` edge for *trigger_def*.

    Returns the new trigger node id. ``id_factory`` lets deterministic callers
    (generation recipes, library materialisation) keep their stable ids.
    """
    props = trigger_properties(trigger_def, extra=extra)
    if id_factory is not None:
        trigger_id = id_factory(owner_id, trigger_def, index, props)
    else:
        import random
        import time

        tt = props.get("trigger_type", "on_examine")
        if isinstance(tt, (list, tuple)):
            tt = tt[0] if tt else "on_examine"
        trigger_id = (
            f"trigger_{owner_id}_{tt}_{int(time.time() * 1000)}_{random.randint(0, 999)}"
        )
    graph.add_node(
        Node(id=trigger_id, type="logic_trigger", name=_default_name(props),
             properties=dict(props))
    )
    graph.add_edge(Edge(source=owner_id, target=trigger_id,
                        type=EDGE_TRIGGERS, properties=dict(props)))
    return trigger_id


def materialize_triggers(
    graph,
    owner_id: str,
    trigger_defs: List[dict],
    *,
    extra: Optional[dict] = None,
    id_factory: Optional[IdFactory] = None,
) -> List[str]:
    """Materialise every definition in *trigger_defs*; returns the new ids."""
    ids: List[str] = []
    for i, td in enumerate(trigger_defs or []):
        if not isinstance(td, dict) or not td:
            continue
        ids.append(materialize_trigger(
            graph, owner_id, td, index=i, extra=extra, id_factory=id_factory))
    return ids
