"""Area tag predicates — one home per fact.

An area being **under the open sky** was decided four separate ways:

- ``lighting.LightingSystem.is_outdoor_area`` — ``"outdoor" in tags``
- ``area_description._is_open_sky`` — either spelling
- ``environment_propagation`` (twice) — ``"exterior" in tags``
- ``tick_manager`` — ``"exterior" in tags``

One fact, four readers, and the spellings disagreeing. That is why a painted
WorldPainter world could have weather prose in one subsystem and none at all in
another: it was *tagged* ``outdoor`` by the biome record, and the forecast and
the heat reservoirs were only looking for ``exterior``.

Both spellings are accepted here rather than unified on disk, because neither is
cheap to retire: ``data/worldpainter/biomes.json`` authors write ``outdoor``,
and a few hundred hand-authored library areas carry ``exterior`` by hand. The
*writer* side gets the question closed (the compiler emits one tag); the *reader*
side accepts both, so every existing world keeps working either way.
"""

from typing import Any, Iterable

#: The two spellings of "under the open sky". Both are read; see the module note.
OPEN_SKY_TAGS = frozenset({"outdoor", "exterior"})


def is_open_sky(tags: Any) -> bool:
    """True when an area's tags say it is under the open sky.

    Accepts a list of tags, a comma-joined string, or ``None`` — call sites pass
    whatever their area node happens to hold, and a missing key must mean
    "indoors" rather than raise.
    """
    if not tags:
        return False
    if isinstance(tags, str):
        tags = tags.split(",")
    if not isinstance(tags, Iterable):
        return False
    return bool(OPEN_SKY_TAGS & {str(t).strip().lower() for t in tags})
