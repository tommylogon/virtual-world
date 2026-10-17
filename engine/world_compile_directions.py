"""Direction helpers extracted from engine/world_compile.py.

Compass deltas, opposite mapping, and small direction helpers used by the
world compiler. Re-exported by engine/world_compile.py to keep the API stable.
"""

from typing import Dict, Tuple


#: Compass deltas. ``y`` increases downward, so north is ``(0, -1)``.
DIRECTIONS: Dict[str, Tuple[int, int]] = {
    "north": (0, -1),
    "south": (0, 1),
    "east": (1, 0),
    "west": (-1, 0),
    "northeast": (1, -1),
    "northwest": (-1, -1),
    "southeast": (1, 1),
    "southwest": (-1, 1),
}
OPPOSITE = {
    "north": "south", "south": "north", "east": "west", "west": "east",
    "northeast": "southwest", "southwest": "northeast",
    "northwest": "southeast", "southeast": "northwest",
}


def _direction_between(a: Tuple[int, int], b: Tuple[int, int]) -> str:
    for name, (dx, dy) in DIRECTIONS.items():
        if (a[0] + dx, a[1] + dy) == b:
            return name
    return "across"


#: 8-wind compass keyed by the sign of (dx, dy).
_COMPASS_BY_SIGN: Dict[Tuple[int, int], str] = {
    (0, -1): "north", (0, 1): "south", (1, 0): "east", (-1, 0): "west",
    (1, -1): "northeast", (-1, -1): "northwest",
    (1, 1): "southeast", (-1, 1): "southwest",
}


def _compass_direction(dx: int, dy: int) -> str:
    """The compass name for an arbitrary delta, for long auto-link ways.

    ``_direction_between`` only names single-cell steps; an island link can span
    many cells, so the sign of the delta picks the 8-wind direction instead.
    """
    sx = (dx > 0) - (dx < 0)
    sy = (dy > 0) - (dy < 0)
    return _COMPASS_BY_SIGN.get((sx, sy), "across")
