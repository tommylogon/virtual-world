"""Character size resolution.

Size started as a selectable trait (``size_tiny`` ... ``size_titanic``, task-187)
and is now a first-class character **property** (task-605), because a prefixed
trait key is invisible in the graph editor and cannot be filtered or sorted on.
The trait is still read, so nothing that already sets one breaks.

Two things now consume the tier rather than one: way ``max_size`` passage
gating, and per-area occupancy (task-653), which is why it is worth being able to
see and set. There is no height property — the tiers are the whole model.
"""

SIZE_TIERS = ["tiny", "small", "normal", "huge", "giant", "titanic"]
SIZE_TIER_INDEX = {name: i for i, name in enumerate(SIZE_TIERS)}
SIZE_DEFAULT = "normal"


def size_name(player) -> str:
    """The player's size as a tier name.

    Prefers the ``size`` property (task-605), falls back to a ``size_*`` trait
    (task-187, and anything hand-authored before the property existed), and
    finally to ``normal``. The property wins when both are present: it is the
    one the graph editor writes, so it is the one the author last touched.
    """
    if player is None:
        return SIZE_DEFAULT
    prop = getattr(player, "size", None)
    if prop and str(prop).strip().lower() in SIZE_TIER_INDEX:
        return str(prop).strip().lower()
    traits = getattr(player, "traits", None) or {}
    for trait_id in traits:
        if trait_id.startswith("size_"):
            name = trait_id[len("size_"):]
            if name in SIZE_TIER_INDEX:
                return name
    return SIZE_DEFAULT


def size_tier(player) -> int:
    """Tier index for a player (default normal)."""
    return SIZE_TIER_INDEX[size_name(player)]


def size_tier_from_name(name) -> int:
    """Tier index for a size name; unknown/empty resolves to normal."""
    return SIZE_TIER_INDEX.get((name or "").strip().lower(), SIZE_TIER_INDEX[SIZE_DEFAULT])
