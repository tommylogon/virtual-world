"""Relative facing — ``forward`` / ``left`` / ``right`` / ``back`` as directions.

A character has no orientation of its own. What it has is **the heading of the
last crossing**: stamp the way it came through and the cardinal it travelled,
and that cardinal is its facing. Facing changes only by moving — there is no
turn-in-place verb — which keeps the whole feature to one piece of state.

    coming from the south  -> travelling north -> facing north
    so "right" is east, "left" is west
    coming from the west   -> travelling east  -> facing east
    so "right" is south, "left" is north

The resolved cardinal is then handed to ordinary exit resolution, so the words
**alias** the area's own directions and never replace them: a room keeps the
name of the door you can see, and "go left" is simply "go <cardinal>".

Deliberately NOT handled here, because each is a different decision:

- **Diagonals.** The ring is four long. A diagonal way is never produced by
  rotation, so "left" of a north-east heading is *unresolved* rather than a
  false answer. An eight-way ring is its own change.
- **up / down.** Vertical ways are not on the ring and are never rotated;
  "up" stays literal.
- **Character AT a way.** Walking up to a door to examine it is not the same
  as having arrived through it. Only a crossing sets facing.

This replaces the old ``transit`` machinery, which could never run: the tag was
declared ``applies_to: ["ways"]`` while its only consumer read it off the
*area*, so ``get_transit_roles`` always returned ``None``. It also *replaced*
a way's handle instead of aliasing it, hardcoded exactly two ways, and derived
"back" from the way a character stood at rather than the way it came through.
"""

from typing import Optional, Tuple

#: Clockwise ring. Index +1 is "right", -1 is "left", +2 is "back".
CARDINAL_RING: Tuple[str, ...] = ("north", "east", "south", "west")

#: The words this feature owns. Everything else resolves as it always did.
RELATIVE_WORDS = frozenset({"forward", "left", "right", "back"})

#: Short forms authors write on connection edges, normalised onto the ring.
_CARDINAL_ALIASES = {
    "n": "north", "s": "south", "e": "east", "w": "west",
    "northward": "north", "southward": "south",
    "eastward": "east", "westward": "west",
}


def normalize_cardinal(value) -> Optional[str]:
    """Fold a direction onto the ring, or return ``None`` if it is not on it.

    ``None`` is a real answer, not a failure: diagonals and vertical ways are
    off-ring by design, and a caller that needs to know the difference must not
    be told they are north.
    """
    if not value:
        return None
    text = str(value).strip().lower()
    if text in CARDINAL_RING:
        return text
    return _CARDINAL_ALIASES.get(text)


def cardinal_opposite(cardinal: str) -> Optional[str]:
    """The cardinal across the ring, or ``None`` when off-ring."""
    folded = normalize_cardinal(cardinal)
    if folded is None:
        return None
    return CARDINAL_RING[(CARDINAL_RING.index(folded) + 2) % 4]


def rotate(word: str, facing: str) -> Optional[str]:
    """Resolve a relative word against a facing cardinal.

    Returns the resulting cardinal, or ``None`` when the word is not ours, the
    facing is missing, or the facing is off-ring. Callers distinguish the last
    two cases via :func:`explain_unresolved` so the player gets a real reason.
    """
    if not word or str(word).strip().lower() not in RELATIVE_WORDS:
        return None
    folded = normalize_cardinal(facing)
    if folded is None:
        return None
    index = CARDINAL_RING.index(folded)
    step = {"forward": 0, "right": 1, "left": -1, "back": 2}[str(word).strip().lower()]
    return CARDINAL_RING[(index + step) % 4]


def explain_unresolved(word: str, facing) -> str:
    """A sentence saying *why* a relative word could not be resolved.

    "can't go there" hides the actual problem — the player typed a perfectly
    good word and the answer should tell them what the character is missing.
    """
    clean = str(word or "").strip().lower()
    if not facing:
        return (
            f"You cannot tell '{clean}' — this character has not moved yet, so it "
            "has no facing. Use a direction like north or south."
        )
    if normalize_cardinal(facing) is None:
        return (
            f"You cannot tell '{clean}' — facing '{facing}' is not a cardinal "
            "direction, so there is nothing to turn it from. Use north, south, "
            "east or west."
        )
    resolved = rotate(clean, facing)
    if resolved is None:
        return f"'{clean}' did not resolve to a direction."
    return (
        f"'{clean}' would be {resolved} from here, and there is no {resolved} "
        f"exit. Visible exits are listed above."
    )


def resolve_for_player(word: str, player) -> Tuple[Optional[str], str]:
    """Resolve ``word`` for a player. Returns ``(cardinal, reason_if_none)``.

    The single call site for "which way is that for this character" — the
    resolver and the messaging read the same two facts, so a rotation can never
    succeed in one and fail in the other.
    """
    if not word or str(word).strip().lower() not in RELATIVE_WORDS:
        return None, ""
    facing = getattr(player, "facing", None)
    resolved = rotate(word, facing)
    if resolved is None:
        return None, explain_unresolved(word, facing)
    return resolved, ""


def edge_cardinal(edge) -> Optional[str]:
    """The normalised cardinal a connection edge points along, or ``None``.

    One reader for both sides of this feature — stamping facing on the way in
    and resolving a relative word on the way out — because they must agree
    about which exits are north.

    It reads ``cardinal`` first and falls back to ``direction``, and the
    fallback is load-bearing: the compiled-zone writer
    (``world_compile.create_way``) sets both, but the runtime writers
    (``movement.connect_areas`` and the ``create_way`` effect) set **only**
    ``direction``. Reading ``cardinal`` alone would have made facing work in
    compiled zones and silently fail everywhere else — a mechanic that looks
    wired and is not, which is the failure mode this whole feature exists to
    avoid.

    ``None`` means "not a heading on the ring": a narrative handle ("swinging
    door"), a diagonal, or a vertical way. None of those is rotated, and none of
    them becomes a left/right.
    """
    if edge is None:
        return None
    props = getattr(edge, "properties", None) or {}
    for key in ("cardinal", "direction"):
        value = normalize_cardinal(props.get(key))
        if value:
            return value
    return None

