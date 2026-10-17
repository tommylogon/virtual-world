def _climb_threshold(record: Dict[str, dict]) -> int:
    """How many storeys a stride may cross in this scope (task-525).

    **Per scope**, not global and not per biome, because the two scopes that care
    about a storey want different numbers: a wilderness world wants three (a cliff
    is a cliff) and a mountain range wants eight (its whole subject is height). A
    global setting would make one of those two wrong for the other, and a
    per-biome one would mean the answer depends on which *end* you are standing on.

    An interior opts out entirely by being an interior, not by raising the number:
    see the ``mode`` check in :func:`_climb_step`.
    """
    raw = (record.get("climb") or {}).get("max_storey_step")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_MAX_STOREY_STEP
    return max(0, value)


