"""What a character *is*, as a list — the audit half of task-457.

task-457 wants the character graph node to be the single source of truth for a
character's full definition, with the :class:`Player` as a runtime view synced
from it. That migration is two-sided: somebody has to **write** the definition
onto the node at creation and at load, and that write lives in
``engine/serialization.py`` and ``engine/player_manager.py``, which are hub
files. This module is the part that does not.

So it is deliberately **read-only**. It answers two questions:

1. *What is the list?* :data:`DEFINITION_FIELDS`, grouped, each field tagged
   with where it lives today.
2. *How far is a given character from canonical?* :func:`definition_drift`,
   which compares a Player against its node and reports every defining field
   that is missing from or disagrees with the node.

No projector. A function that writes a definition onto a node, called from
nowhere, does not make the node canonical — it makes a **second** source of truth
and invites the exact drift the task is trying to remove. Whoever wires the
write path into the hubs gets the drift reader to verify the result.

Nothing here mutates a Player or a node, so it is safe to call from anywhere,
including a test, a route, or a one-off audit.
"""

from __future__ import annotations

from typing import Dict, List, NamedTuple

#: Where a defining field lives today, and therefore who has to move it.
#:
#: ``player``      — only on the :class:`Player`; the node has never seen it.
#: ``node``        — already on the node's properties.
#: ``edges``       — already represented as graph edges, so projecting it onto
#:                    the node as well would duplicate the record.
#: ``derived``     — computed from the above (``Player.state`` reads the
#:                    condition hierarchy, ``emotions_map`` is a lazy baseline);
#:                    storing it would cache a value that can go stale.
ON_PLAYER = "player"
ON_NODE = "node"
ON_EDGES = "edges"
DERIVED = "derived"


class DefinitionField(NamedTuple):
    """One defining field of a character."""

    name: str
    group: str
    #: Where the value lives today — see the module-level constants.
    lives_on: str
    #: True when the task's scope says the node must carry it. False for fields
    #: that are genuinely runtime bookkeeping and should stay off the node even
    #: once the migration lands.
    canonical: bool
    note: str = ""


#: Group -> the fields in it, in the order they read like a character sheet.
_GROUPS: Dict[str, List[DefinitionField]] = {
    "identity": [
        DefinitionField("name", "identity", ON_NODE, True,
                        "the node's own name; the one field already canonical"),
        DefinitionField("unknown_name", "identity", ON_PLAYER, True,
                        "what the character is called before they are introduced"),
        DefinitionField("description", "identity", ON_PLAYER, True),
        DefinitionField("base_description", "identity", ON_PLAYER, True,
                        "the authored look, before any state modifies it"),
        DefinitionField("personality", "identity", ON_PLAYER, True),
        DefinitionField("flags", "identity", ON_PLAYER, True),
    ],
    "capability": [
        DefinitionField("stats", "capability", ON_PLAYER, True),
        DefinitionField("skills", "capability", ON_PLAYER, True),
        DefinitionField("proficiency", "capability", ON_PLAYER, True),
        DefinitionField("skill_progress", "capability", ON_PLAYER, True),
        DefinitionField("crafting_known", "capability", ON_PLAYER, True),
        DefinitionField("traits", "capability", ON_PLAYER, True),
    ],
    "state": [
        DefinitionField("vitals", "state", ON_PLAYER, True,
                        "the task lists vitals in scope, though they are runtime "
                        "state rather than definition — see the module docstring"),
        DefinitionField("decay_rates", "state", ON_PLAYER, True),
        DefinitionField("body_state", "state", ON_PLAYER, True),
        DefinitionField("emotion", "state", ON_PLAYER, True),
        DefinitionField("emotion_intensity", "state", ON_PLAYER, True),
        DefinitionField("conditions", "state", ON_PLAYER, True),
        DefinitionField("hidden", "state", ON_PLAYER, True),
        DefinitionField("manifested", "state", ON_PLAYER, True),
    ],
    "social": [
        DefinitionField("relationships", "social", ON_PLAYER, True),
        DefinitionField("memories", "social", ON_PLAYER, True),
        DefinitionField("memory_index", "social", ON_PLAYER, False,
                        "an index into memories, not a definition; deriving it "
                        "from the canonical memories is enough"),
        DefinitionField("lived_log", "social", ON_PLAYER, True),
    ],
    "tier": [
        DefinitionField("simple_npc", "tier", ON_PLAYER, True,
                        "the field that separates a simple NPC from an agent or "
                        "a human — the task's uniformity requirement turns on it"),
        DefinitionField("autonomy", "tier", ON_PLAYER, True),
        DefinitionField("npc_behavior", "tier", ON_PLAYER, True),
        DefinitionField("npc_action_interval", "tier", ON_PLAYER, True),
        DefinitionField("npc_state", "tier", ON_PLAYER, False,
                        "the behaviour state machine's current node; runtime"),
        DefinitionField("state_enter_tick", "tier", ON_PLAYER, False, "runtime"),
        DefinitionField("behaviors", "tier", ON_PLAYER, True),
        DefinitionField("patrol_route", "tier", ON_PLAYER, True),
        DefinitionField("simulation_mode", "tier", ON_PLAYER, True,
                        "background vs active; decides which runner owns them"),
    ],
    "knowledge": [
        DefinitionField("tags", "knowledge", ON_PLAYER, True,
                        "the list every shipped character actually fills "
                        "(\"goblin\", \"teen\") — see task-552"),
        DefinitionField("interest_tags", "knowledge", ON_PLAYER, True),
        DefinitionField("fear_tags", "knowledge", ON_PLAYER, True),
        DefinitionField("known", "knowledge", ON_PLAYER, True),
        DefinitionField("discovered_exits", "knowledge", ON_PLAYER, False,
                        "a set; runtime accumulation"),
        DefinitionField("known_way_aspects", "knowledge", ON_PLAYER, True),
        DefinitionField("visited_areas", "knowledge", ON_PLAYER, False,
                        "a set; runtime accumulation"),
        DefinitionField("discovered_items", "knowledge", ON_PLAYER, False,
                        "a set; runtime accumulation"),
    ],
    "inventory": [
        DefinitionField("equipped", "inventory", ON_EDGES, True,
                        "already carried by EDGE_EQUIPPED edges; the node must "
                        "not also hold the list or there are two records"),
        DefinitionField("carcass_item", "inventory", ON_PLAYER, True),
    ],
    "spatial": [
        DefinitionField("current_area", "spatial", ON_EDGES, True,
                        "already carried by the 'in' / spatial edges"),
        DefinitionField("facing", "spatial", ON_PLAYER, False,
                        "cardinal heading of the last crossing (task-313); the "
                        "only thing 'left'/'right'/'forward'/'back' read, and None "
                        "until the character has moved — runtime, but durable "
                        "across a save so a reload does not silently forget it"),
        DefinitionField("entered_from_way", "spatial", ON_PLAYER, False,
                        "the way that crossing used, so the heading can be "
                        "explained rather than asserted (task-313)"),
        DefinitionField("node_id", "spatial", ON_NODE, True),
        DefinitionField("id", "spatial", ON_PLAYER, True),
    ],
    "runtime": [
        DefinitionField("activity", "runtime", ON_PLAYER, False,
                        "an in-flight duration that owns the rest of the turn"),
        DefinitionField("recent_hearing", "runtime", ON_PLAYER, False,
                        "bounded perception buffer, rebuilt every turn"),
        DefinitionField("soak_order", "runtime", ON_PLAYER, False,
                        "transient; not part of a save's durable state"),
        DefinitionField("next_due_tick", "runtime", ON_PLAYER, False),
        DefinitionField("last_offload_tick", "runtime", ON_PLAYER, False),
        DefinitionField("background_consolidated_through",
                        "runtime", ON_PLAYER, False),
        DefinitionField("minutes_per_tick", "runtime", ON_PLAYER, False,
                        "a world clock, not a character fact"),
        DefinitionField("state", "runtime", DERIVED, False,
                        "derived from the condition hierarchy, not a field"),
    ],
}

#: Every defining field, flattened.
DEFINITION_FIELDS: List[DefinitionField] = [
    field for fields in _GROUPS.values() for field in fields
]

#: The fields the task requires the node to carry, as bare names.
CANONICAL_FIELDS: List[str] = [f.name for f in DEFINITION_FIELDS if f.canonical]

#: Canonical fields that live ONLY on the Player today — the migration's work
#: list, and the thing `definition_drift` is expected to shrink to zero.
PLAYER_ONLY_FIELDS: List[str] = [
    f.name for f in DEFINITION_FIELDS if f.canonical and f.lives_on == ON_PLAYER
]

#: Fields the edges already carry, so the migration must not duplicate them.
EDGE_BACKED_FIELDS: List[str] = [
    f.name for f in DEFINITION_FIELDS if f.lives_on == ON_EDGES
]


def groups() -> Dict[str, List[DefinitionField]]:
    """Group -> fields, in character-sheet order."""
    return {name: list(fields) for name, fields in _GROUPS.items()}


def field(name: str) -> DefinitionField | None:
    """The :class:`DefinitionField` for *name*, or None."""
    for candidate in DEFINITION_FIELDS:
        if candidate.name == name:
            return candidate
    return None


def node_definition(node) -> Dict[str, object]:
    """The definition a character node currently carries.

    Everything except the keys the graph itself owns (``name``, ``type``), which
    are node metadata rather than definition.
    """
    if node is None:
        return {}
    props = dict(getattr(node, "properties", None) or {})
    props.pop("name", None)
    props.pop("type", None)
    return props


def _comparable(value):
    """Normalise the types that are structurally equal but unequal by ``==``."""
    if isinstance(value, set):
        return sorted(str(v) for v in value)
    return value


def definition_drift(player, node) -> Dict[str, List[str]]:
    """Which defining fields the Player holds alone.

    Returns ``{"missing": [...], "differs": [...]}``, considering only fields
    that are **canonical** and live **only on the Player** — which is the
    migration's work list by construction, so the two cannot drift apart.

    Two kinds of field are deliberately excluded:

    * *Edge-backed* ones (``equipped``, ``current_area``). The graph already holds
      them as edges; putting them on the node as well would duplicate the record
      rather than centralise it.
    * *Already-on-node* ones (``name``, ``node_id``). The node **is** the record
      for these — ``node_definition`` strips the graph's own metadata, so
      checking them would report them missing forever.

    ``missing`` means the node has never heard of the field. ``differs`` means
    the node has a value and the Player has a different one, which is the
    dangerous case: two records, two answers, no way to tell which is right.
    """
    have = node_definition(node)
    missing: List[str] = []
    differs: List[str] = []
    for name in PLAYER_ONLY_FIELDS:
        if not hasattr(player, name):
            # A subclass or an older save may not have it. A field this
            # character does not have is not drift.
            continue
        if name not in have:
            missing.append(name)
            continue
        if _comparable(getattr(player, name)) != _comparable(have[name]):
            differs.append(name)
    return {"missing": missing, "differs": differs}


def is_canonical(player, node) -> bool:
    """True when this character has no definitional drift from its node."""
    drift = definition_drift(player, node)
    return not drift["missing"] and not drift["differs"]


def audit(world) -> Dict[str, object]:
    """Drift for every character in *world*, plus the totals.

    ``{"characters": {name: drift}, "totally_canonical": [...],
    "with_drift": [...]}`` — the one call that answers "how far along is
    task-457?" against a running world instead of against a plan.
    """
    characters: Dict[str, Dict[str, List[str]]] = {}
    players = getattr(getattr(world, "player_manager", None), "players", None) or {}
    graph = getattr(world, "graph", None)
    for key, player in players.items():
        node = None
        if graph is not None:
            try:
                node = graph.get_node(world._player_node_id(key))
            except Exception:
                node = None
        characters[key] = definition_drift(player, node)
    return {
        "characters": characters,
        "with_drift": [k for k, d in characters.items()
                       if d["missing"] or d["differs"]],
        "totally_canonical": [k for k, d in characters.items()
                              if not d["missing"] and not d["differs"]],
    }
