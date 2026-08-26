"""Character size trait resolution (task-187).

Size is a selectable trait (``size_tiny`` ... ``size_titanic``); the engine
resolves a tier index for comparisons against way ``max_size``. No height
property — the tiers are the whole model.
"""

SIZE_TIERS = ["tiny", "small", "normal", "huge", "giant", "titanic"]
SIZE_TIER_INDEX = {name: i for i, name in enumerate(SIZE_TIERS)}
SIZE_DEFAULT = "normal"


def size_tier(player) -> int:
    """Tier index for a player from their ``size_*`` trait (default normal)."""
    traits = (player.traits or {}) if player else {}
    for trait_id in traits:
        if trait_id.startswith("size_"):
            name = trait_id[len("size_"):]
            if name in SIZE_TIER_INDEX:
                return SIZE_TIER_INDEX[name]
    return SIZE_TIER_INDEX[SIZE_DEFAULT]


def size_tier_from_name(name) -> int:
    """Tier index for a size name; unknown/empty resolves to normal."""
    return SIZE_TIER_INDEX.get(name or "", SIZE_TIER_INDEX[SIZE_DEFAULT])
