"""Way barriers: one place sound and light agree on what a door does (task-421).

The world had two propagation systems with different barrier semantics. Sound
consulted the way's state; light did not consult it at all, so a lit room bled
light into neighbours regardless of what stood between them.

The numbers for the two systems are **not** the same, and forcing them to be
would be wrong:

* sound's barrier is a **cost** — the quietest route is the sum of its barriers,
  and higher means worse;
* light's is a **transmission** — the fraction of a lit neighbour that reaches
  you, and higher means better.

So this module holds two named tables side by side, as the task allows, over one
shared **state ladder** and one shared resolution order. What cannot drift
anymore is the part that actually had drifted: *which* states exist, and the rule
that a see-through way is not an open way. Light used to treat `see_through` as
fully open, so a window leaked as much as a missing door while sound rated a
window *worse* than an open doorway — the two systems disagreed about the very
thing a window is.

Per-door overrides: ``sound_barrier`` and ``light_barrier`` float properties,
applied while the way is solid, exactly as ``sound_barrier`` already was.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Tuple

from engine.runtime_config import config as _config

#: Every state a way can be in, in increasing obstruction. The ORDER is the
#: shared contract: both tables are non-increasing along it, and a test asserts
#: that, so a new state cannot be added to one system and forgotten in the other.
WAY_STATES: Tuple[str, ...] = (
    "open", "see_through", "closed", "locked", "blocked", "hidden",
)

#: Default sound COST per state. Unchanged from `engine/sound.py`, which this
#: table replaces: a public module-level snapshot it still exposes.
DEFAULT_SOUND_COSTS: Dict[str, float] = {
    "open": 0.5,
    "see_through": 0.75,
    "closed": 1.0,
    "locked": 1.0,
    "blocked": 1.0,
    "hidden": 2.0,
}

#: Default light TRANSMISSION per state — the fraction of a lit neighbour's light
#: that crosses the way. The ladder is the same as sound's, the sign is not.
#:
#: - open passes everything;
#: - a window passes three quarters, so a room is dimmer when its only opening is
#:   glazed (the old code passed a window exactly as much as a missing door);
#: - a shut door leaks a little around the frame;
#: - a locked door is thick and has a lock in it;
#: - a blocked passage and a hidden panel admit nothing until they are opened.
DEFAULT_LIGHT_TRANSMISSION: Dict[str, float] = {
    "open": 1.0,
    "see_through": 0.75,
    "closed": 0.25,
    "locked": 0.1,
    "blocked": 0.0,
    "hidden": 0.0,
}

#: A state that is not in a table resolves as this, so an unrecognised
#: ``current_state`` is treated as passable rather than as opaque.
UNKNOWN_STATE_FALLBACK = "open"

#: States a per-door override applies to. All three are solid: a door you can
#: see through is one you are not walking through, so there is nothing for an
#: author to be specific about.
#:
#: ``see_through`` is not here even though a window is shut: sound has always
#: let ``see_through`` outrank the state, and an override on an open window is
#: meaningless anyway.
SOLID_STATES = ("closed", "locked", "blocked")

_CONFIG_PREFIX = {"sound": "sound.way_", "light": "light.way_"}


def _config_float(key: str, default: float) -> float:
    value = _config.get(key, default)
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def sound_cost(state: str) -> float:
    """The sound cost of *state*, honouring a live Engine Config override."""
    name = _normalise_state(state)
    return _config_float(
        f"{_CONFIG_PREFIX['sound']}{name}", DEFAULT_SOUND_COSTS[name]
    )


def light_transmission(state: str) -> float:
    """The fraction of a neighbour's light that crosses a way in *state*."""
    name = _normalise_state(state)
    return _config_float(
        f"{_CONFIG_PREFIX['light']}{name}", DEFAULT_LIGHT_TRANSMISSION[name]
    )


def _normalise_state(state: Any) -> str:
    text = str(state or "").strip().lower()
    if text in DEFAULT_SOUND_COSTS:
        return text
    if text == "open" or text == "":
        return UNKNOWN_STATE_FALLBACK
    # Aliases the world already spells differently, folded onto one state so the
    # ladder stays short. A typo in a scenario is a passable way, not a crash.
    if text in ("shut", "ajar_closed"):
        return "closed"
    if text in ("barred", "secured"):
        return "locked"
    if text in ("secret", "concealed"):
        return "hidden"
    return UNKNOWN_STATE_FALLBACK


def _props(way_node: Any) -> Dict:
    props = getattr(way_node, "properties", None)
    if props is None and isinstance(way_node, dict):
        props = way_node
    return props if isinstance(props, dict) else {}


def declared_state(way_node: Any) -> str:
    """The way's ``current_state``, normalised. Never ``see_through``."""
    return _normalise_state(_props(way_node).get("current_state", UNKNOWN_STATE_FALLBACK))


def way_state(way_node: Any) -> str:
    """The state the barrier TABLES are indexed by.

    ``see_through`` outranks ``current_state``, which is the order
    ``engine/sound.py`` already used: a window is a window whether or not
    somebody also called the way open. Keeping that order is what makes the two
    systems comparable — the bug was never that light had a different rule, it
    was that light had a *binary* one.
    """
    props = _props(way_node)
    if props.get("see_through"):
        return "see_through"
    return declared_state(way_node)


def _override(way_node: Any, property_name: str) -> Optional[float]:
    try:
        return float(_props(way_node).get(property_name))
    except (TypeError, ValueError):
        return None


def get_sound_cost(way_node: Any) -> float:
    """Sound's cost for a way, in the order ``engine/sound.py`` always used.

    1. a way whose *declared* state is solid takes its ``sound_barrier`` — a shut
       window is still a shut door, and the author said how heavy it is;
    2. otherwise a see-through way is a window (0.75);
    3. otherwise the per-state table.
    """
    if declared_state(way_node) in SOLID_STATES:
        custom = _override(way_node, "sound_barrier")
        if custom is not None:
            return custom
    return sound_cost(way_state(way_node))


def get_light_transmission(way_node: Any) -> float:
    """Light's transmission for a way, in sound's order (task-421).

    The per-door ``light_barrier`` override is a **transmission**, not a cost, so
    an author writing ``light_barrier: 0.1`` on a closed door means "a tenth of
    the light gets through" — the same direction as the word suggests, which is
    the opposite of what copying the sound number would have meant.
    """
    if declared_state(way_node) in SOLID_STATES:
        custom = _override(way_node, "light_barrier")
        if custom is not None:
            return custom
    return light_transmission(way_state(way_node))


def signature(ways: Iterable[Any]) -> str:
    """A cheap fingerprint of every way's barrier behaviour.

    Used as the second half of the lighting cache key: the graph revision covers
    nodes and edges being added or removed, but mutating a way's
    ``current_state`` in place does not bump it, and a stale light stamp would
    report a sealed room as still spilling. Only the properties that change the
    answer are read, and the result is compared, never parsed.
    """
    parts = []
    for way in ways:
        props = _props(way)
        if not props:
            continue
        parts.append("|".join((
            str(getattr(way, "id", "")),
            str(props.get("current_state", "")),
            "1" if props.get("see_through") else "0",
            str(props.get("light_barrier", "")),
            str(props.get("sound_barrier", "")),
        )))
    parts.sort()
    return ";".join(parts)
