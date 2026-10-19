"""WorldPainter scope grids and feature placements (task-495).

A world scope owns a bounded grid at its own resolution. The grid is the
authoring substrate for a painted world (task-495); the grid→graph compiler
(task-496) later turns it into areas + ways via task-398's ``GenerationPatch``.
Nothing here is engine behaviour yet - these are pure helpers over the scope
manifest, so the editor, the compiler, and the tests can agree on one shape.

**A compiled cell IS an area.** This is the fact that makes the two layers one
model rather than two, and it is worth stating here because the grid is an
*authoring* surface and nothing in this module says what it becomes:

* the compiler mints the area id from the cell - ``area_<scope_id>_<x>_<y>``
  (``world_compile._area_id``);
* the area's name is derived from the cell - the biome or road label plus the
  scope and coordinate, e.g. ``Sparse Forest (West woods 10, 14)``, unless the
  author named the cell (``_place_name``, task-560);
* the area carries ``properties.cell`` and ``properties.world_scope_id``, so the
  cell stays a **stable frame** for it across edits elsewhere on the grid.

So a biome cell, a road cell, a feature placement and a hand-placed room are all
the same kind of thing at runtime: **an area node that knows which cell it is**.
There is no separate "cell" concept in the graph, and nothing that walks the
graph needs to know which of those four it is looking at. Measured on
``kraktooth_goblin_camp``: 205 of 206 areas carry a cell, and coverage against
the manifest is exact for the compiled scopes (``eldenford_interior`` 70 cells →
70 areas, ``world`` 61 → 61, ``goblin_camp`` 21 → 21).

Two places the one-cell-one-area correspondence does **not** hold, both by
design:

* a run of painted cells is **merged into one region** and the area records only
  the region's **anchor** cell, so a merged area's ``cell`` is where it was
  minted, not its footprint (``west_woods``: 81 painted cells → 53 areas);
* a cell occupied by a hand-placed area is **skipped**, so a painted cell can
  legitimately hold an author-written area instead of a compiled one (``world``
  18,6 is ``area_human_road``).

And one scope can have a grid that was never compiled at all (``deep_woods``:
404 painted cells, 0 areas), so a cell in the manifest is not guaranteed to be an
area anywhere. Anything that walks areas rather than cells inherits both
consequences for free.

Data model
----------
Grid state lives on the *scope record* inside the world-scope manifest
(``engine/world_scopes.py``; persisted as ``world.world_scopes``), under three
keys, so a scope with no grid costs nothing and older saves load unchanged::

    record["mode"]       = "world" | "town" | "interior"   (optional)
    record["grid"]       = {"w": int, "h": int}
    record["layers"]     = {"biome": {"<x>,<y>": value},   # value is a biome id
                            "road":  {"<x>,<y>": value},   # road/surface id
                            "floor": {"<x>,<y>": int}}     # storey index
    record["placements"] = {child_scope_id: {"x": int, "y": int}}
    record["area_placements"] = {area_id: {"x": int, "y": int}}   (task-528)
    record["boundary_overrides"] = {way_id: {"action": ..., ...}}  (task-528)

The ``floor`` layer is a **storey index**, not a height or a material: 0 is the
ground plane, 1 one storey up, -1 one down, and the scale is *unbounded* - three
rooms stacked over each other, the bottom of a lake at -2, an 80-storey tower, a
hole to hell at -900. It is deliberately not a 0..1 fraction, because the engine
compares *whole storeys* (a two-storey step reads as a cliff, task-525) and
because a save has to be able to say "eighty floors up" without a legend. An
unpainted cell is *ground* (0) rather than "unknown", so an author marking a
cliff does not also have to number every plain cell around it. Ground *material*
is a separate fact and lives in the biome/road record's ``surface``
(``engine/biomes.ground_surface``).

Features - a village inside a forest - are **child scopes placed at a cell**, so
they live in ``placements`` rather than a separate paint layer;
:func:`feature_layer` derives the ``feature`` paint view the editor draws.
An area the author wrote by hand can also be placed on a cell (task-528); those
live in ``area_placements``, keyed by area node id, and the compiler skips an
occupied cell so the two never collide. Note the asymmetry, because it is the
whole difference between the two: a cell with **no** hand-placed area is
*painted* and compiles to an area (``area_<scope>_<x>_<y>``), while a cell **with**
one is skipped and the author's area stands. Either way the runtime node is an
area; only where its name and id came from differs.

Coordinates are integer ``(x, y)`` with ``(0, 0)`` at the top-left and ``y``
increasing downward, matching a normal image grid. A cell's **stable identity**
is :func:`cell_id` (``"<scope_id>:<x>,<y>"``), which the compiler uses as the
area id so a reference survives edits elsewhere on the grid.

Overlap rule (task-495 acceptance)
----------------------------------
Placing or moving a feature onto an occupied cell is **forbidden by default**:
the caller must move or delete the occupant first, so a placement can never
silently clobber another child. Passing ``on_overlap="displace"`` opts a call
into replacing the occupant. "Merge" is deliberately *not* implemented here - it
would have to redefine child-scope identity, and the design note
(``docs/design/worldpainter-knowledge-and-fog.md``) leaves grid-canonical vs
baked handling to the compiler (task-496).

The two placement kinds do not share a cell. A feature is read by the compiler as
a **region** on that cell, while a hand-placed area *removes* the cell from the
compile set (task-528), so a cell holding both would be in neither and the feature
gateway would be skipped in silence. :func:`place` therefore refuses an
area-occupied cell even under ``displace``; the author unplaces the area first.

Boundary overrides
------------------
The compiler mints a way from a hand-placed area to every painted cell touching
it, so a placed area is walkable from the road rather than an island in the graph.
Those ways are the compiler's *first draft*, not the last word: the author owns
them once minted, and :func:`set_boundary_override` records the decision on the
scope so a later Generate respects it. ``suppress`` means "I deleted this and do
not want it back"; ``hand`` means "I wrote my own way for this seam" and names it.
Both stop the compiler re-minting the pair. Keyed by the generated way id, which
is stable across runs because it is derived from the two area ids.

@module world_grid
@contributes the painted scope grid record: layers, paint, place, floor
@docs docs/virtualWorld/World Building/WorldPainter.md
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Set, Tuple

#: The three editor modes (task-495, task-883). A world grid paints zones as cells, a settlement
#: grid paints walls/gates/roads/buildings, an interior grid paints rooms/doors.
MODES = ("world", "settlement", "interior")

#: Paint layers a grid may carry. ``feature`` is *derived* from placements, not
#: stored, so it is not listed here.
#:
#: ``floor`` holds a **storey index** (see the module docstring), not a height
#: fraction and not a ground material.
#:
#: ``climate`` is a **coarse enum** - arctic / temperate / arid / tropical /
#: alpine - that compiles to a per-area ``base_temperature`` (task-557). It is an
#: enum rather than a continuous value for three reasons, each of which cost
#: something last time: an enum is one brush instead of a value-and-falloff
#: control, it survives save/reload without a float to drift, and the per-region
#: aggregation ("which climate is this area, when its cells disagree?") stays a
#: majority vote instead of a mean that invents a climate nobody painted. It is
#: **not** part of a region's identity - a climate change across a road does not
#: split the area, the way a road change does.
#:
#: The deleted ``elevation`` layer lived here once and warns against the obvious
#: mistake: one word must not mean two things. ``floor`` is a storey index, and
#: elevation as a painted *height* is gone because "elevation" said both.
PAINT_LAYERS = ("biome", "road", "floor", "climate", "current")

#: One storey step on the floor layer equals 3 metres (task-877).
#:
#: Stored values on the ``floor`` layer are whole integer storeys (0 ground, 1 one
#: up, -1 one down). Metres are never stored directly in the scenario. When
#: importing or exporting a greyscale heightmap, metres are converted to storeys
#: via ``round(metres / METRES_PER_STOREY)``, with boundaries at 1.5m, 4.5m, etc.
METRES_PER_STOREY: int = 3

#: The coarse climates a grid may be painted with, and the °C each compiles to
#: (task-557). The numbers are the **base** - the year's average for a place -
#: and the diurnal and seasonal curve is added on top by task-553's model, so a
#: temperate world is 21 °C on an average day and genuinely colder at 04:00 in
#: winter. Values are the mid-point of each band's real range rather than its
#: extreme, so a painted arctic is cold without being the coldest thing on earth.
#:
#: The key is the taxonomy's, and an unpainted cell is **temperate** (21.0) - the
#: value the engine has always used - rather than "unknown". A world with no
#: climate layer must not compile differently from one that paints everything.
CLIMATE_BASE_C = {
    "arctic": -8.0,
    "alpine": 2.0,
    "temperate": 21.0,
    "arid": 31.0,
    "tropical": 27.0,
}

#: The climate an unpainted cell reads as. Temperate on purpose: it is the
#: engine's long-standing 21 °C default, so "no climate painted" and "temperate
#: painted" are the same world, and a scope that never chose a climate is not
#: silently arctic.
DEFAULT_CLIMATE = "temperate"

#: Layer keys accepted when *reading* a record, mapped to the layer they now
#: belong to. The ``elevation`` layer was a 0..1 height the author never agreed
#: to; it was renamed to ``floor`` and re-based on storeys (2026-09-27). Reads
#: stay tolerant so a save painted under the old name keeps its numbers instead
#: of being silently dropped by :func:`normalise_grid`; writes only ever use
#: :data:`PAINT_LAYERS`.
LEGACY_LAYER_KEYS = {"elevation": "floor"}

ON_OVERLAP = ("forbid", "displace", "gateway")

#: What an author can decide about a compiler-minted boundary way (see the module
#: docstring). ``suppress`` - deleted, do not re-mint. ``hand`` - replaced by the
#: author's own way, named in the entry; the compiler must not mint the pair again
#: or it would duplicate the seam. There is deliberately no ``force``: handing the
#: seam *back* to the compiler is "clear the entry", not a third action, because
#: "auto again" is what an absent record already means.
OVERRIDE_ACTIONS = ("suppress", "hand")


# ───────────────────────────── identities ─────────────────────────────────


def cell_id(scope_id: str, x: int, y: int) -> str:
    """Stable global id for a grid cell - the compiler's future area id.

    Stable under unrelated edits: moving a feature or painting another cell does
    not change this string, so a save that referenced the cell still resolves.
    """
    return f"{scope_id}:{int(x)},{int(y)}"


def parse_cell_id(value: str) -> Optional[Tuple[str, int, int]]:
    """Inverse of :func:`cell_id` - ``(scope_id, x, y)``, or ``None`` if malformed."""
    try:
        scope_id, coords = str(value).rsplit(":", 1)
        sx, sy = coords.split(",", 1)
        return scope_id, int(sx), int(sy)
    except (ValueError, AttributeError):
        return None


def cell_key(x: int, y: int) -> str:
    """Layer-dict key for a cell."""
    return f"{int(x)},{int(y)}"


def parse_cell_key(value: str) -> Optional[Tuple[int, int]]:
    try:
        sx, sy = str(value).split(",", 1)
        return int(sx), int(sy)
    except (ValueError, AttributeError):
        return None


# ───────────────────────────── normalisation ──────────────────────────────


def normalise_grid(record: dict) -> dict:
    """Coerce a scope record's grid fields into the canonical shape (in place).

    Tolerates missing/legacy data and leaves a scope that never had a grid
    untouched - no empty containers are added, so manifests stay small and
    older saves load byte-identically. Values that cannot be parsed are dropped
    rather than raising, so one bad save cannot make the whole manifest
    unloadable.
    """
    if not isinstance(record, dict):
        return record
    if not any(key in record for key in ("grid", "layers", "placements",
                                         "area_placements", "boundary_overrides",
                                         "mode", "map_offset", "names",
                                         "sibling_traversal")):
        return record

    grid = record.get("grid")
    if isinstance(grid, dict):
        w, h = _as_int(grid.get("w")), _as_int(grid.get("h"))
        if w and h and w > 0 and h > 0:
            record["grid"] = {"w": w, "h": h}
        else:
            record.pop("grid", None)
    elif "grid" in record:
        record.pop("grid", None)

    if "layers" in record:
        layers = record.get("layers")
        clean_layers: Dict[str, dict] = {}
        if isinstance(layers, dict):
            # A record painted under the old ``elevation`` name keeps its cells:
            # the numbers become storeys, which is what that layer was reaching
            # for. Merging (rather than taking one dict) means a half-migrated
            # record loses nothing.
            merged: Dict[str, dict] = {}
            for key, values in layers.items():
                if not isinstance(values, dict):
                    continue
                merged.setdefault(LEGACY_LAYER_KEYS.get(key, key), {}).update(values)
            for layer in PAINT_LAYERS:
                values = merged.get(layer)
                if not isinstance(values, dict):
                    continue
                kept = {}
                for key, value in values.items():
                    if parse_cell_key(key) is not None and value not in (None, ""):
                        kept[str(key)] = value
                if kept:
                    clean_layers[layer] = kept
        record["layers"] = clean_layers

    if "placements" in record:
        placements = record.get("placements")
        clean_placements: Dict[str, dict] = {}
        if isinstance(placements, dict):
            for child_id, pos in placements.items():
                if not isinstance(pos, dict):
                    continue
                x, y = _as_int(pos.get("x")), _as_int(pos.get("y"))
                if x is None or y is None:
                    continue
                clean = {"x": x, "y": y}
                # Compiled-link fields (task-496): a generated parent records the
                # area its placed cell compiled to, so a child generated later can
                # still find its gateway. Keep them across a load.
                if pos.get("area_id"):
                    clean["area_id"] = str(pos["area_id"])
                if pos.get("area_name"):
                    clean["area_name"] = str(pos["area_name"])
                clean_placements[str(child_id)] = clean
        record["placements"] = clean_placements

    if "area_placements" in record:
        # Hand-placed *areas* on cells (task-528) - the mirror of `placements`,
        # keyed by area node id instead of child scope id, because the thing being
        # placed already exists in the graph. Same shape, same leniency.
        record["area_placements"] = _clean_placement_map(record.get("area_placements"))

    if "boundary_overrides" in record:
        record["boundary_overrides"] = _clean_override_map(
            record.get("boundary_overrides"))

    if "names" in record:
        record["names"] = _clean_name_map(record.get("names"))

    if "map_offset" in record:
        clean_offset = _clean_offset(record.get("map_offset"))
        if clean_offset and (clean_offset["x"] or clean_offset["y"]):
            record["map_offset"] = clean_offset
        else:
            record.pop("map_offset", None)

    if "sibling_traversal" in record:
        if bool(record.get("sibling_traversal")):
            record["sibling_traversal"] = True
        else:
            record.pop("sibling_traversal", None)

    mode = record.get("mode")
    if mode == "town":
        mode = "settlement"
        record["mode"] = "settlement"
    elif mode is not None and str(mode) not in MODES:
        record.pop("mode", None)
    return record


def _as_int(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):        return None


def _finite(value) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return number == number and number not in (float("inf"), float("-inf"))


def _clean_placement_map(raw) -> Dict[str, dict]:
    """Coerce a ``{key: {"x","y"}}`` map, dropping anything unusable.

    Shared by ``placements`` and ``area_placements`` (task-528) so a hand-edited or
    legacy record cannot crash a load; a key without two integer coordinates is
    simply not a placement.
    """
    clean: Dict[str, dict] = {}
    if isinstance(raw, dict):
        for key, pos in raw.items():
            if not isinstance(pos, dict):
                continue
            x, y = _as_int(pos.get("x")), _as_int(pos.get("y"))
            if x is None or y is None:
                continue
            clean[str(key)] = {"x": x, "y": y}
    return clean


def _clean_name_map(raw) -> Dict[str, str]:
    """The author-named cells of a scope (task-560), minus anything unusable.

    A name is *metadata about* a cell, not paint on it, so it lives beside
    ``layers`` rather than on one: there is no name vocabulary, and a name is not
    something you paint over. An empty or whitespace-only name is dropped, and so
    is a name on an unparseable cell key, so a bad save costs one name rather than
    the whole map.
    """
    clean: Dict[str, str] = {}
    if isinstance(raw, dict):
        for key, name in raw.items():
            if parse_cell_key(str(key)) is None:
                continue
            text = str(name or "").strip()
            if text:
                clean[str(key)] = text
    return clean


def _clean_override_map(raw) -> Dict[str, dict]:
    """Coerce ``{way_id: {"action": ...}}``, dropping anything unusable.

    The key is a generated way id, so an override is meaningless without one: a
    bare string, or an entry naming an unknown action, is not a decision the
    compiler can act on, and keeping it would silently suppress nothing while
    looking like it did.
    """
    clean: Dict[str, dict] = {}
    if isinstance(raw, dict):
        for way_id, decision in raw.items():
            if not isinstance(decision, dict):
                continue
            action = str(decision.get("action") or "")
            if action not in OVERRIDE_ACTIONS:
                continue
            entry: Dict[str, object] = {"action": action}
            custom = decision.get("way_id")
            if custom:
                entry["way_id"] = str(custom)
            clean[str(way_id)] = entry
    return clean


# ─────────────────────────────── grid ─────────────────────────────────────


def has_grid(record: dict) -> bool:
    grid = (record or {}).get("grid")
    return bool(isinstance(grid, dict) and grid.get("w") and grid.get("h"))


def ensure_grid(record: dict, w: int, h: int,
                mode: Optional[str] = None) -> dict:
    """Create or resize a scope's grid. Resizing keeps paint that stays in bounds.

    Raises ``ValueError`` for a non-positive size or an unknown mode so the
    editor/compiler never operate on a degenerate grid.
    """
    w, h = int(w), int(h)
    if w <= 0 or h <= 0:
        raise ValueError("grid must be at least 1x1")
    if mode == "town":
        mode = "settlement"
    if mode is not None and mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}; expected one of {MODES}")
    record["grid"] = {"w": w, "h": h}
    if mode is not None:
        record["mode"] = mode
    record.setdefault("layers", {})
    record.setdefault("placements", {})

    # Drop paint/placements that fall outside the new bounds, so a shrink can
    # never leave a reference to a cell that no longer exists.
    for layer, values in list(record["layers"].items()):
        record["layers"][layer] = {
            key: value for key, value in values.items()
            if _key_in_bounds(key, w, h)
        }
        if not record["layers"][layer]:
            record["layers"].pop(layer)
    record["placements"] = {
        child: pos for child, pos in record["placements"].items()
        if 0 <= pos["x"] < w and 0 <= pos["y"] < h
    }
    return record


def in_bounds(record: dict, x: int, y: int) -> bool:
    grid = (record or {}).get("grid") or {}
    w, h = _as_int(grid.get("w")), _as_int(grid.get("h"))
    if not w or not h:
        return False
    return 0 <= int(x) < w and 0 <= int(y) < h


def grid_size(record: dict) -> Tuple[int, int]:
    grid = (record or {}).get("grid") or {}
    return _as_int(grid.get("w")) or 0, _as_int(grid.get("h")) or 0


def _key_in_bounds(key: str, w: int, h: int) -> bool:
    pos = parse_cell_key(key)
    return bool(pos) and 0 <= pos[0] < w and 0 <= pos[1] < h


# ─────────────────────── map layout offset (task-523) ─────────────────────

#: A zone is nudged by dragging the graph canvas, so a value past this is a
#: corrupt record (or a drag gone wild), not a real position.
MAP_OFFSET_LIMIT = 100000.0


def _clean_offset(offset) -> Optional[Dict[str, float]]:
    """Validate a stored map offset (cell units) or return ``None``."""
    if not isinstance(offset, dict):
        return None
    try:
        x, y = float(offset.get("x", 0.0)), float(offset.get("y", 0.0))
    except (TypeError, ValueError):
        return None
    if not _finite(x) or not _finite(y):
        return None
    if abs(x) > MAP_OFFSET_LIMIT or abs(y) > MAP_OFFSET_LIMIT:
        return None
    return {"x": x, "y": y}


def map_offset(record: dict) -> Dict[str, float]:
    """A scope's **map-layout offset** in cell units; ``(0, 0)`` by default.

    The WorldPainter paints each scope on its own local grid anchored at
    ``(0, 0)``. The graph map layout adds this offset to every node of the scope
    (task-523), so the author can arrange zones relative to each other without
    baking the move into the painter's cell coords - a paint edit must never
    shift the world under it.
    """
    return _clean_offset((record or {}).get("map_offset")) or {"x": 0.0, "y": 0.0}


def set_map_offset(record: dict, x=None, y=None, reset: bool = False) -> dict:
    """Set a scope's map-layout offset (cell units); ``reset`` clears it.

    A zero offset is stored as *absence*, so a scope that was never moved keeps
    a minimal manifest and older saves load byte-identically. Raises
    ``ValueError`` for a missing/non-numeric/non-finite value or one past
    :data:`MAP_OFFSET_LIMIT`.
    """
    if reset:
        record.pop("map_offset", None)
        return record
    try:
        clean = {"x": float(x), "y": float(y)}
    except (TypeError, ValueError):
        raise ValueError("map offset needs numeric x and y")
    if not _finite(clean["x"]) or not _finite(clean["y"]):
        raise ValueError("map offset must be finite")
    if abs(clean["x"]) > MAP_OFFSET_LIMIT or abs(clean["y"]) > MAP_OFFSET_LIMIT:
        raise ValueError(f"map offset must be within ±{MAP_OFFSET_LIMIT:g} cells")
    if clean["x"] == 0.0 and clean["y"] == 0.0:
        record.pop("map_offset", None)
    else:
        record["map_offset"] = clean
    return record


# ─────────────────────────────── painting ─────────────────────────────────


def paint(record: dict, layer: str, x: int, y: int, value) -> dict:
    """Set a cell's value on *layer*. ``value`` of ``None``/``""`` erases it.

    Raises ``ValueError`` for an unknown layer, a grid-less scope, or a cell
    outside the grid - painting off-grid would create a cell the compiler cannot
    place, which is exactly the silent-corruption class the schema is for.
    """
    if layer not in PAINT_LAYERS:
        raise ValueError(f"unknown paint layer {layer!r}; expected {PAINT_LAYERS}")
    if not has_grid(record):
        raise ValueError("scope has no grid")
    if not in_bounds(record, x, y):
        raise ValueError(f"cell ({x},{y}) is outside the grid")
    layers = record.setdefault("layers", {})
    values = layers.setdefault(layer, {})
    if value in (None, ""):
        values.pop(cell_key(x, y), None)
        if not values:
            layers.pop(layer, None)
    else:
        values[cell_key(x, y)] = value
    return record


def paint_many(record: dict, edits: List[dict]) -> int:
    """Apply many :func:`paint` edits in one all-or-nothing pass.

    A route/trail tool paints hundreds of cells at once (a 240-cell road is 240
    edits). Every edit is validated *before* the first write so a bad edit cannot
    half-paint a route - the same "reject before mutating" rule ``apply_patch``
    uses for generation. Each edit is ``{"layer", "x", "y", "value"}``; a
    ``None``/``""`` value erases, exactly like :func:`paint`.
    """
    edits = list(edits or [])
    if not has_grid(record):
        raise ValueError("scope has no grid")
    validated: List[Tuple[str, int, int, object]] = []
    for edit in edits:
        layer = (edit or {}).get("layer")
        if layer not in PAINT_LAYERS:
            raise ValueError(f"unknown paint layer {layer!r}; expected {PAINT_LAYERS}")
        try:
            x, y = int(edit.get("x")), int(edit.get("y"))
        except (TypeError, ValueError):
            raise ValueError("each edit needs integer x and y")
        if not in_bounds(record, x, y):
            raise ValueError(f"cell ({x},{y}) is outside the grid")
        validated.append((layer, x, y, edit.get("value")))
    for layer, x, y, value in validated:
        paint(record, layer, x, y, value)
    return len(validated)


def painter_at(record: dict, layer: str, x: int, y: int):
    """The value painted at a cell, or ``None``."""
    return layer_cells(record, layer).get(cell_key(x, y))


def climate_base_c(climate: str) -> float:
    """The base °C for a climate name, defaulting to temperate."""
    return CLIMATE_BASE_C.get(str(climate or "").strip().lower(),
                              CLIMATE_BASE_C[DEFAULT_CLIMATE])


def name_at(record: dict, x: int, y: int) -> Optional[str]:
    """The author's name for a cell, or ``None`` (task-560).

    A name is optional and orthogonal to paint: a named cell may be unpainted, and
    a painted cell may be unnamed (it then compiles to a generated name). Nothing
    else in the grid depends on it - the compiler prefers it for the *display
    name* only, and ids stay the authoritative key.
    """
    value = ((record or {}).get("names") or {}).get(cell_key(x, y))
    text = str(value or "").strip()
    return text or None


def set_name(record: dict, x: int, y: int, name: Optional[str]) -> Optional[str]:
    """Set (or clear) the author's name for one cell. Returns the name now in force.

    An empty name *removes* the entry rather than storing "", so a scope that is
    unnamed again loads byte-identically to one that never had names.
    """
    names = record.setdefault("names", {})
    key = cell_key(x, y)
    text = str(name or "").strip()
    if text:
        names[key] = text
    else:
        names.pop(key, None)
    if not names:
        record.pop("names", None)
    return text or None


def layer_cells(record: dict, layer: str) -> dict:
    """The ``{"<x>,<y>": value}`` map for *layer*, or ``{}``.

    Reads a legacy layer name (:data:`LEGACY_LAYER_KEYS`) so a record saved
    before the ``elevation`` → ``floor`` rename still yields its cells.
    """
    layers = (record or {}).get("layers") or {}
    values = layers.get(LEGACY_LAYER_KEYS.get(layer, layer))
    return values if isinstance(values, dict) else {}


def floor_paint_at(record: dict, x: int, y: int) -> Optional[int]:
    """The cell's painted **storey index**, or ``None`` when it is unpainted.

    The value is rounded to a whole storey: the engine reasons in storeys
    (a two-storey step is a cliff, task-525) and a save has to be able to say
    "eighty floors up" in one plain integer. Unreadable paint reads as
    ``None`` - the caller decides whether that means ground.
    """
    value = layer_cells(record, "floor").get(cell_key(x, y))
    if value in (None, ""):
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def floor_at(record: dict, x: int, y: int) -> int:
    """:func:`floor_paint_at` with unpainted/unreadable counting as ground (0).

    The single most useful read: an author marking a cliff should not also have
    to number every plain cell around it.
    """
    painted = floor_paint_at(record, x, y)
    return 0 if painted is None else painted


# ────────────────────────── reference image ───────────────────────────────

#: Faint by default so painted cells read over the art underneath.
REFERENCE_OPACITY_DEFAULT = 0.5

#: Default crop window: the whole image.
REFERENCE_CROP_DEFAULT = {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}


def _clean_rect(rect) -> Optional[Dict[str, float]]:
    """Validate a reference destination rect (cell units) or return ``None``."""
    if not isinstance(rect, dict):
        return None
    try:
        out = {key: float(rect[key]) for key in ("x", "y", "w", "h")}
    except (KeyError, TypeError, ValueError):
        return None
    if not all(_finite(value) for value in out.values()):
        return None
    if out["w"] <= 0 or out["h"] <= 0:
        return None
    return out


def _clean_crop(crop) -> Optional[Dict[str, float]]:
    """Validate a normalized source window (0..1) or return ``None``."""
    if not isinstance(crop, dict):
        return None
    try:
        out = {key: float(crop[key]) for key in ("x", "y", "w", "h")}
    except (KeyError, TypeError, ValueError):
        return None
    if not all(_finite(value) for value in out.values()):
        return None
    if out["w"] <= 0 or out["h"] <= 0:
        return None
    return {
        "x": max(0.0, min(1.0, out["x"])),
        "y": max(0.0, min(1.0, out["y"])),
        "w": max(0.001, min(1.0, out["w"])),
        "h": max(0.001, min(1.0, out["h"])),
    }


def reference(record: dict) -> Optional[dict]:
    """The scope's authoring reference image, or ``None``."""
    ref = (record or {}).get("reference")
    return dict(ref) if isinstance(ref, dict) and ref.get("image") else None


def reference_rect(record: dict) -> Optional[Dict[str, float]]:
    """The reference's destination rect in **cell** units, or ``None`` for auto-fit.

    Stored in cells (not pixels) so the WorldPainter (22px/cell) and the graph
    map layout (``mapSpacing`` px/cell) can each draw the art in their own space
    and still agree; ``None`` means "fit the whole image to the grid".
    """
    return _clean_rect((reference(record) or {}).get("rect"))


def reference_crop(record: dict) -> Dict[str, float]:
    """The reference's normalized source window (0..1); the whole image by default."""
    return _clean_crop((reference(record) or {}).get("crop")) or dict(REFERENCE_CROP_DEFAULT)


def set_reference(record: dict, image, opacity=None, visible=None,
                  rect=None, crop=None, reset: bool = False) -> Optional[dict]:
    """Set or clear a scope's reference image (a picture to paint over).

    Reference-only: it is never compiled into areas/ways, so a huge or stale
    image cannot affect the world - it just helps the author place cells over
    known art. ``image`` of ``None``/``""`` clears it.

    ``rect`` (cell units) and ``crop`` (normalized source window) are the
    author's move/resize/crop of the picture: omit them to keep what is stored,
    pass ``reset=True`` to drop them back to auto-fit. A *changed* image also
    auto-fits, since a rect tuned for the old picture rarely suits the new one.
    """
    if image in (None, ""):
        record.pop("reference", None)
        return None
    if not has_grid(record):
        raise ValueError("scope has no grid")
    existing = reference(record) or {}
    try:
        value = float(REFERENCE_OPACITY_DEFAULT if opacity is None else opacity)
    except (TypeError, ValueError):
        value = REFERENCE_OPACITY_DEFAULT
    stored = {
        "image": str(image),
        "opacity": max(0.0, min(1.0, value)),
        "visible": True if visible is None else bool(visible),
    }
    new_image = str(image) != str(existing.get("image") or "")
    if not reset:
        keep_rect = _clean_rect(rect) if rect is not None else (
            None if new_image else _clean_rect(existing.get("rect")))
        keep_crop = _clean_crop(crop) if crop is not None else (
            None if new_image else _clean_crop(existing.get("crop")))
        if keep_rect:
            stored["rect"] = keep_rect
        if keep_crop:
            stored["crop"] = keep_crop
    record["reference"] = stored
    return dict(record["reference"])


# ─────────────────────────────── features ─────────────────────────────────


def placements(record: dict) -> Dict[str, dict]:
    """A copy of ``{child_scope_id: {"x","y"}}`` for a scope."""
    return dict((record or {}).get("placements") or {})


def feature_layer(record: dict) -> Dict[str, str]:
    """The derived ``feature`` paint view: ``{cell_key: child_scope_id}``."""
    return {cell_key(pos["x"], pos["y"]): child
            for child, pos in placements(record).items()}


def cell_of(record: dict, child_id: str) -> Optional[Tuple[int, int]]:
    pos = placements(record).get(str(child_id))
    if not pos:
        return None
    return pos["x"], pos["y"]


def occupant_at(record: dict, x: int, y: int) -> Optional[str]:
    """The child scope placed at a cell, if any."""
    for child, pos in placements(record).items():
        if pos["x"] == int(x) and pos["y"] == int(y):
            return child
    return None


def sibling_traversal(record: dict) -> bool:
    """Whether *record* explicitly turns on sibling-scope border seams (task-775)."""
    return bool((record or {}).get("sibling_traversal"))


def set_sibling_traversal(record: dict, enabled: bool) -> bool:
    """Set or clear the sibling-traversal switch on a scope record (task-775).

    Absent when False so existing saves stay byte-identical.
    """
    if bool(enabled):
        record["sibling_traversal"] = True
        return True
    record.pop("sibling_traversal", None)
    return False


def sibling_traversal_enabled(manifest: Dict[str, dict], scope_id: str) -> bool:
    """True when *scope_id* (or the parent grid it sits on) allows sibling seams (task-775).

    Toggling ``sibling_traversal`` on a parent chunk grid (e.g. ``world``) enables
    border stitching for every child chunk placed on it; toggling it on an
    individual child scope enables it for that scope's borders with its siblings.
    """
    rec = (manifest or {}).get(str(scope_id))
    if not isinstance(rec, dict):
        return False
    if sibling_traversal(rec):
        return True
    parent_id = rec.get("parent_id")
    if parent_id and parent_id in (manifest or {}):
        return sibling_traversal(manifest[parent_id])
    return False


# ─────────────────────── placed areas (task-528) ───────────────────────────
#
# A *placed area* is an area node the author wrote by hand, parked on a cell of a
# painted grid. It is the mirror of `placements`, keyed by area node id rather than
# by child scope id, because the thing being placed already exists in the graph.
#
# Why it lives on the scope record and not only on the node: the node's
# `properties.cell` says where the area *is*, but only the record can answer "is
# this cell already taken?" - which is what keeps a hand-placed area and a
# compiled one from landing on top of each other when the grid is generated.


def area_placements(record: dict) -> Dict[str, dict]:
    """A copy of ``{area_id: {"x","y"}}`` for a scope (task-528)."""
    return dict((record or {}).get("area_placements") or {})


def area_placement_of(record: dict, area_id: str) -> Optional[Tuple[int, int]]:
    """The cell an area is placed on in this scope, or ``None``."""
    pos = area_placements(record).get(str(area_id))
    if not pos:
        return None
    return pos["x"], pos["y"]


def area_placement_at(record: dict, x: int, y: int) -> Optional[str]:
    """The area placed at a cell, if any (task-528)."""
    for area_id, pos in area_placements(record).items():
        if pos["x"] == int(x) and pos["y"] == int(y):
            return area_id
    return None


def place_area(manifest: Dict[str, dict], scope_id: str, area_id: str,
               x: int, y: int, *, on_overlap: str = "forbid") -> str:
    """Park area *area_id* on a cell of *scope_id*'s grid (task-528).

    Returns ``"placed"``, ``"moved"`` or ``"displaced"``, matching :func:`place`:
    a cell that already holds a *placed area* is refused unless the caller opts
    into ``on_overlap="displace"``. A cell holding a child-scope placement is left
    alone - that is a different kind of occupant and the compiler already knows
    how to tag a cell with a child.

    This only records the reservation; the caller owns the graph side (the node's
    ``world_scope_id`` / ``cell`` / ``x`` / ``y``), because only it knows whether
    the area is hand-authored enough to place.
    """
    if on_overlap not in ON_OVERLAP:
        raise ValueError(f"unknown on_overlap {on_overlap!r}; expected {ON_OVERLAP}")
    scope = manifest.get(scope_id)
    if scope is None:
        raise ValueError(f"no such scope {scope_id!r}")
    if not has_grid(scope):
        raise ValueError(f"scope {scope_id!r} has no grid")
    if not in_bounds(scope, x, y):
        raise ValueError(f"cell ({x},{y}) is outside the grid")

    current = scope.setdefault("area_placements", {})
    occupant = area_placement_at(scope, x, y)
    outcome = "placed"
    if occupant is not None and occupant != str(area_id):
        if on_overlap == "forbid":
            raise ValueError(
                f"cell ({x},{y}) already holds area {occupant!r}; move or unplace it first")
        current.pop(occupant, None)
        outcome = "displaced"
    if current.get(str(area_id)) is not None:
        outcome = "moved"
    current[str(area_id)] = {"x": int(x), "y": int(y)}
    return outcome


def unplace_area(manifest: Dict[str, dict], scope_id: str, area_id: str) -> None:
    """Free the cell an area occupies in this scope (task-528). A no-op otherwise."""
    scope = manifest.get(scope_id)
    if scope is None:
        raise ValueError(f"no such scope {scope_id!r}")
    current = scope.get("area_placements") or {}
    if str(area_id) in current:
        current.pop(str(area_id), None)
        if not current:
            scope.pop("area_placements", None)


# ────────────────────── boundary ways (task-528) ───────────────────────────
#
# The compiler mints a way from a hand-placed area to every painted cell touching
# it. Those ways are a draft the author then owns, and this is how the author's
# decision outlives a Generate - see the module docstring.


def boundary_overrides(record: dict) -> Dict[str, dict]:
    """A copy of ``{generated way id: decision}`` for a scope."""
    return dict((record or {}).get("boundary_overrides") or {})


def boundary_override(record: dict, way_id: str) -> Optional[dict]:
    """The author's decision about one boundary way, or ``None``."""
    return boundary_overrides(record).get(str(way_id))


def is_boundary_overridden(record: dict, way_id: str) -> bool:
    """True when a Generate must **not** mint this way (deleted or hand-replaced)."""
    return str(way_id) in boundary_overrides(record)


def set_boundary_override(record: dict, way_id: str, action: str, *,
                          hand_way_id: Optional[str] = None) -> dict:
    """Record the author's decision about a boundary way; returns the entry.

    ``action`` is one of :data:`OVERRIDE_ACTIONS`. ``hand`` requires
    ``hand_way_id``: "I wrote my own way" is not actionable without saying which,
    because the point of the record is that the compiler leaves that seam alone
    and an unnamed substitute would leave the reader unable to tell a replaced
    seam from a merely deleted one.

    Passing ``action=None`` clears the entry - the way back to "Generate decides",
    which is also what an absent record means.
    """
    if action is None:
        current = record.get("boundary_overrides") or {}
        current.pop(str(way_id), None)
        if not current:
            record.pop("boundary_overrides", None)
        return {}
    action = str(action)
    if action not in OVERRIDE_ACTIONS:
        raise ValueError(
            f"unknown boundary override {action!r}; expected one of "
            f"{', '.join(OVERRIDE_ACTIONS)}")
    entry: Dict[str, object] = {"action": action}
    if action == "hand":
        if not hand_way_id:
            raise ValueError("a 'hand' override needs the author's way_id")
        entry["way_id"] = str(hand_way_id)
    elif hand_way_id:
        raise ValueError(
            f"a {action!r} override takes no way_id; only 'hand' names a way")
    record.setdefault("boundary_overrides", {})[str(way_id)] = entry
    return entry


def place(manifest: Dict[str, dict], parent_id: str, child_id: str,
          x: int, y: int, *, on_overlap: str = "forbid") -> str:
    """Place child scope *child_id* at a cell of *parent_id*'s grid.

    Returns ``"placed"``, ``"moved"``, ``"displaced"`` or ``"gated"``. Raises
    ``ValueError`` for a missing parent/child, a grid-less parent, an out-of-bounds
    cell, an unknown overlap policy, or a forbidden overlap.

    ``on_overlap="gateway"`` is the one policy that shares a cell with a
    hand-placed *area*, and it is the only way to do so: the area becomes the
    **doorstep** and the child's gateway is the author's own (see the body, and
    task-535's promote). The other two refuse, because a cell holding both kinds
    is a cell the compiler has to choose over and it would choose neither.
    """
    if on_overlap not in ON_OVERLAP:
        raise ValueError(f"unknown on_overlap {on_overlap!r}; expected {ON_OVERLAP}")
    parent = manifest.get(parent_id)
    if parent is None:
        raise ValueError(f"no such scope {parent_id!r}")
    if child_id not in manifest:
        raise ValueError(f"no such child scope {child_id!r}")
    if not has_grid(parent):
        raise ValueError(f"scope {parent_id!r} has no grid")
    if not in_bounds(parent, x, y):
        raise ValueError(f"cell ({x},{y}) is outside the grid")

    current = parent.setdefault("placements", {})
    occupant = occupant_at(parent, x, y)
    outcome = "placed"
    if occupant is not None and occupant != child_id:
        if on_overlap == "forbid":
            raise ValueError(
                f"cell ({x},{y}) already holds {occupant!r}; move or remove it first")
        current.pop(occupant, None)
        outcome = "displaced"
    # A hand-placed *area* (task-528) and a feature cannot share a cell by
    # accident: the compiler has to choose. A feature placement is read as a
    # **region** (``compile_grid`` looks the cell up in ``cell_region``), and an area
    # placement deletes that cell from the compile set - so a cell holding both
    # would be in neither, and the gateway would be skipped in silence. Unlike a
    # displaced feature (a record entry), evicting an area also has to clear the
    # *node's* ``cell``/``x``/``y``, which the route owns and this layer does not.
    placed_area = area_placement_at(parent, x, y)
    doorstep = None
    if placed_area is not None:
        if on_overlap != "gateway":
            raise ValueError(
                f"cell ({x},{y}) already holds the hand-placed area {placed_area!r}; "
                f"unplace it before placing a feature here")
        # …unless sharing the cell is the *point* (task-535). Promoting a selection
        # into a scope and putting the scope where the entrance already stands means
        # the hand-placed area becomes the **doorstep** the new gateway opens from.
        # That is a different seam, not a colliding one: the cell is not a region,
        # so the compiler mints no gateway and the author's own way is the only one -
        # which is exactly right, because the author wired it. The occupant is
        # recorded so the generate report can say so rather than leave the author
        # wondering why no gateway appeared.
        doorstep = placed_area
    if current.get(child_id) is not None:
        outcome = "moved"
    entry: Dict[str, object] = {"x": int(x), "y": int(y)}
    if doorstep:
        entry["gateway_from"] = doorstep
        outcome = "gated" if outcome == "placed" else outcome
    current[child_id] = entry
    return outcome


def move(manifest: Dict[str, dict], parent_id: str, child_id: str,
         x: int, y: int, *, on_overlap: str = "forbid") -> str:
    """Move an already-placed child. Same rules as :func:`place`."""
    parent = manifest.get(parent_id)
    if parent is None or child_id not in placements(parent):
        raise ValueError(f"{child_id!r} is not placed in {parent_id!r}")
    return place(manifest, parent_id, child_id, x, y, on_overlap=on_overlap)


def remove(manifest: Dict[str, dict], parent_id: str, child_id: str) -> bool:
    """Remove a placement. Returns True when something was removed."""
    parent = manifest.get(parent_id)
    if parent is None:
        return False
    return parent.setdefault("placements", {}).pop(str(child_id), None) is not None


# ────────────────────────────── validation ────────────────────────────────


def validate(manifest: Dict[str, dict]) -> List[str]:
    """Human-readable problems with the manifest's grids; ``[]`` when clean."""
    problems: List[str] = []
    if not isinstance(manifest, dict):
        return ["manifest is not a mapping"]

    for scope_id, record in manifest.items():
        if not isinstance(record, dict):
            problems.append(f"{scope_id}: scope record is not an object")
            continue
        grid = record.get("grid")
        if grid is None:
            if record.get("layers") or record.get("placements"):
                problems.append(f"{scope_id}: has paint/placements but no grid")
            continue
        w, h = _as_int(grid.get("w")), _as_int(grid.get("h"))
        if not w or not h or w <= 0 or h <= 0:
            problems.append(f"{scope_id}: grid size must be positive")
            continue
        for layer, values in (record.get("layers") or {}).items():
            if layer not in PAINT_LAYERS:
                problems.append(f"{scope_id}: unknown paint layer {layer!r}")
            for key in values:
                if not _key_in_bounds(key, w, h):
                    problems.append(f"{scope_id}/{layer}: cell {key} is out of bounds")
        seen_cells = {}
        for child_id, pos in (record.get("placements") or {}).items():
            if child_id not in manifest:
                problems.append(f"{scope_id}: placed child {child_id!r} is not a scope")
            x, y = _as_int(pos.get("x")), _as_int(pos.get("y"))
            if x is None or y is None:
                problems.append(f"{scope_id}: placement {child_id!r} has no cell")
                continue
            if not (0 <= x < w and 0 <= y < h):
                problems.append(
                    f"{scope_id}: placement {child_id!r} at ({x},{y}) is out of bounds")
            cell = cell_key(x, y)
            if cell in seen_cells:
                problems.append(
                    f"{scope_id}: cell {cell} holds both {seen_cells[cell]!r} "
                    f"and {child_id!r}")
            else:
                seen_cells[cell] = child_id
    return problems


# ─────────────────────────── line of sight ────────────────────────────────

EYE_HEIGHT_FLOORS: float = 0.5
MAX_SIGHT_RANGE: int = 60
#: Past this many cells every top drops by HORIZON_DROP_PER_CELL floors per cell.
#: It must sit below MAX_SIGHT_RANGE or the drop can never apply.
HORIZON_CURVATURE_START: int = 40
HORIZON_DROP_PER_CELL: float = 1.0
#: Floors of obstacle height that still show in the peripheral arc.
PERIPHERAL_LANDMARK_HEIGHT: float = 5.0
#: Slope comparison slack, so a grazing line is decided the same way each run.
VISIBILITY_EPS: float = 1e-9

FACING_ANGLES: Dict[str, float] = {
    "east": 0.0,
    "e": 0.0,
    "southeast": 45.0,
    "se": 45.0,
    "south": 90.0,
    "s": 90.0,
    "southwest": 135.0,
    "sw": 135.0,
    "west": 180.0,
    "w": 180.0,
    "northwest": -135.0,
    "nw": -135.0,
    "north": -90.0,
    "n": -90.0,
    "northeast": -45.0,
    "ne": -45.0,
}


def supercover_line(x0: int, y0: int, x1: int, y1: int) -> List[Tuple[int, int]]:
    """Conservative supercover line rasterization from (x0, y0) to (x1, y1).

    Unlike basic Bresenham which only yields N cells, conservative supercover
    visits every cell a ray passes through. Crucially, when stepping diagonally
    across a corner joint (e.g. between (10, 10) and (11, 11)), both orthogonal
    cells (11, 10) and (10, 11) are visited, preventing sightlines from leaking
    through diagonally adjacent walls or cliffs (task-882).
    """
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    dx = x1 - x0
    dy = y1 - y0
    nx = abs(dx)
    ny = abs(dy)
    sign_x = 1 if dx > 0 else -1 if dx < 0 else 0
    sign_y = 1 if dy > 0 else -1 if dy < 0 else 0

    p_x, p_y = x0, y0
    points: List[Tuple[int, int]] = [(p_x, p_y)]
    if nx == 0 and ny == 0:
        return points

    ix = 0
    iy = 0
    while ix < nx or iy < ny:
        decision = (1 + 2 * ix) * ny - (1 + 2 * iy) * nx
        if decision == 0:
            # Corner transit: add both orthogonal cells to seal diagonal wall joints
            points.append((p_x + sign_x, p_y))
            points.append((p_x, p_y + sign_y))
            p_x += sign_x
            p_y += sign_y
            ix += 1
            iy += 1
        elif decision < 0:
            p_x += sign_x
            ix += 1
        else:
            p_y += sign_y
            iy += 1
        points.append((p_x, p_y))
    return points


def cell_elevation(record: dict, x: int, y: int) -> float:
    """The floor elevation of cell (x, y) as a float (default 0.0)."""
    val = (record.get("layers", {}).get("floor", {}) or {}).get(cell_key(x, y), 0)
    try:
        return float(val or 0)
    except (TypeError, ValueError):
        return 0.0


def cell_biome(record: dict, x: int, y: int) -> str:
    """The biome id painted at cell (x, y), or empty string."""
    return str((record.get("layers", {}).get("biome", {}) or {}).get(cell_key(x, y), "") or "")


def cell_obstacle_properties(record: dict, x: int, y: int, world: Optional[object] = None) -> Tuple[float, float, float]:
    """Returns (floor_elevation, obstacle_height, obscurity) for cell (x, y).

    Reads the floor layer, biome properties from taxonomy, and any Area node
    properties that occupy this cell (task-882).
    """
    from engine import biomes as biomes_mod
    floor_elev = cell_elevation(record, x, y)
    b_id = cell_biome(record, x, y)
    obs_h = biomes_mod.biome_height(b_id) if b_id else 0.0
    obs_val = biomes_mod.biome_obscurity(b_id) if b_id else 0.0

    # Area node dynamic property override if world graph is available
    if world is not None and hasattr(world, "graph"):
        area_placements = record.get("area_placements") or {}
        for node_id, pos in area_placements.items():
            if isinstance(pos, dict) and pos.get("x") == x and pos.get("y") == y:
                node = world.graph.get_node(node_id)
                if node and getattr(node, "properties", None):
                    p = node.properties
                    if "height" in p:
                        try:
                            obs_h = float(p["height"])
                        except (TypeError, ValueError):
                            pass
                    if "obscurity" in p:
                        try:
                            obs_val = float(p["obscurity"])
                        except (TypeError, ValueError):
                            pass
                break

    return floor_elev, obs_h, obs_val


def cast_sight_ray(
    record: dict,
    origin: Tuple[int, int] | Tuple[int, int, float],
    target: Tuple[int, int] | Tuple[int, int, float],
    eye_height: float = EYE_HEIGHT_FLOORS,
    max_range: int = MAX_SIGHT_RANGE,
    world: Optional[object] = None,
) -> dict:
    """Cast a 2.5D line-of-sight ray from origin to target (task-882).

    The target is the top of its cell (floor plus obstacle height), so a tall
    landmark can be seen over lower cover. A cell is seen when its top is not
    hidden by anything in front of it: ground and fully opaque cover hide
    everything whose silhouette is at or below theirs, and translucent cover
    (forest) adds its obscurity until the total reaches 1.0.

    An explicit target z replaces the target cell's floor elevation.

    Returns:
      - visible: bool
      - blocked_by: (x, y) of the cell doing the hiding, or None
      - blocked_elevation: top of that cell, when blocked
      - obscurity: obscurity accumulated in front of the target
      - cells: every (x, y) the ray crosses
      - steps: one dict per crossed cell (x, y, top, height, obscurity, seen, blocked)
      - reason: a short sentence for a debugger, empty when clear
    """
    x0, y0 = int(origin[0]), int(origin[1])
    z0 = float(origin[2]) if len(origin) > 2 else cell_elevation(record, x0, y0)
    z_eye = z0 + float(eye_height)

    x1, y1 = int(target[0]), int(target[1])
    explicit_z1 = float(target[2]) if len(target) > 2 else None

    if x0 == x1 and y0 == y1:
        return {"visible": True, "blocked_by": None, "obscurity": 0.0,
                "cells": [(x0, y0)], "steps": [], "reason": ""}

    dist_total = math.hypot(x1 - x0, y1 - y0)
    if dist_total > max_range:
        return {"visible": False, "blocked_by": None, "obscurity": 1.0,
                "cells": [], "steps": [],
                "reason": "out of range (%.1f > %d cells)" % (dist_total, max_range)}

    def props(cx: int, cy: int) -> Tuple[float, float, float]:
        floor_e, obs_h, obs_v = cell_obstacle_properties(record, cx, cy, world)
        if explicit_z1 is not None and cx == x1 and cy == y1:
            floor_e = explicit_z1
        return floor_e, obs_h, obs_v

    cells = supercover_line(x0, y0, x1, y1)
    steps: List[dict] = []
    result_visible = True
    blocked_by: Optional[Tuple[int, int]] = None
    obscurity = 0.0
    for cx, cy, d, seen, hidden, blocker in _scan_ray(cells, x0, y0, z_eye, max_range, props):
        floor_e, obs_h, obs_v = props(cx, cy)
        steps.append({"x": cx, "y": cy, "top": floor_e + obs_h, "height": obs_h,
                      "obscurity": obs_v, "seen": seen, "blocked": False})
        if cx == x1 and cy == y1:
            result_visible = seen
            obscurity = hidden
            if not seen:
                blocked_by = blocker
    if blocked_by is not None:
        blocked_top = None
        for st in steps:
            if (st["x"], st["y"]) == blocked_by:
                st["blocked"] = True
                blocked_top = st["top"]
        reason = "hidden behind (%d,%d): its top (%.1f) is above your sight line" % (
            blocked_by[0], blocked_by[1], blocked_top if blocked_top is not None else 0.0)
        return {"visible": False, "blocked_by": blocked_by,
                "blocked_elevation": blocked_top,
                "obscurity": obscurity, "cells": cells, "steps": steps, "reason": reason}
    return {"visible": result_visible, "blocked_by": None, "obscurity": obscurity,
            "cells": cells, "steps": steps, "reason": ""}


def _scan_ray(cells, x0, y0, z_eye, max_range, props):
    """Walk a supercover line outward from the observer (task-882).

    Yields ``(x, y, distance, seen, hidden, blocker)`` per cell. Each cell is
    judged by what stands in front of it only, so an obstacle is itself seen
    (its front face) while the cells in its shadow are not.

    This is a slope sweep, not a ray aimed at one height. A cell's top has a
    slope ``(top - eye) / distance`` from the observer, and a nearer occluder
    hides every farther top whose slope is not higher than its own. That is what
    lets a tower show above a hedge and a ridge hide a valley, with one pass
    per ray instead of one ray per target.

    Ground is opaque: terrain at floor N hides what is behind it. Cover adds its
    obscurity (translucent) or, at 1.0, hides outright. Past
    HORIZON_CURVATURE_START cells every top drops 1 floor per cell.
    """
    opaque_slope: Optional[float] = None
    opaque_cell: Optional[Tuple[int, int]] = None
    partial: List[Tuple[float, float, Tuple[int, int]]] = []
    for cx, cy in cells:
        if cx == x0 and cy == y0:
            continue
        d = math.hypot(cx - x0, cy - y0)
        if d > max_range:
            return
        floor_e, obs_h, obs_v = props(cx, cy)
        drop = max(0.0, d - HORIZON_CURVATURE_START) * HORIZON_DROP_PER_CELL
        slope = (floor_e + obs_h - drop - z_eye) / d

        hidden = 0.0
        blocker: Optional[Tuple[int, int]] = None
        if opaque_slope is not None and opaque_slope >= slope - VISIBILITY_EPS:
            hidden, blocker = 1.0, opaque_cell
        else:
            for s_o, o_v, o_cell in partial:
                if s_o >= slope - VISIBILITY_EPS:
                    hidden += o_v
                    blocker = o_cell
            if hidden < 1.0:
                blocker = None
        yield cx, cy, d, hidden < 1.0, hidden, blocker

        ground_slope = (floor_e - drop - z_eye) / d
        if opaque_slope is None or ground_slope > opaque_slope:
            opaque_slope, opaque_cell = ground_slope, (cx, cy)
        if obs_h > 0 and obs_v > 0:
            if obs_v >= 1.0:
                if slope > opaque_slope:
                    opaque_slope, opaque_cell = slope, (cx, cy)
            else:
                partial.append((slope, obs_v, (cx, cy)))


def compute_visible_cells(
    record: dict,
    origin: Tuple[int, int] | Tuple[int, int, float],
    max_range: int = MAX_SIGHT_RANGE,
    facing: Optional[str] = None,
    arc_degrees: float = 360.0,
    world: Optional[object] = None,
    peripheral_range: int = 3,
) -> Set[Tuple[int, int]]:
    """Compute the full set of grid cells visible from origin (task-882).

    Fires one slope sweep (see ``_scan_ray``) along a supercover line to every
    cell on the perimeter of the sight box.

    If facing is provided and arc_degrees < 360, respects the directional cone:
      - Primary cone: full max_range.
      - Peripheral arc: limited to peripheral_range, except tall landmarks
        (obstacle height >= PERIPHERAL_LANDMARK_HEIGHT), which still show.
    A cell outside the cone still occludes; it is only left out of the result.
    """
    x0, y0 = int(origin[0]), int(origin[1])
    grid = record.get("grid") or {}
    w, h = _as_int(grid.get("w")), _as_int(grid.get("h"))
    if not w or not h:
        return {(x0, y0)}

    visible: Set[Tuple[int, int]] = {(x0, y0)}
    heading_angle: Optional[float] = None
    if facing and arc_degrees < 360.0:
        heading_angle = FACING_ANGLES.get(str(facing).lower())

    half_arc = float(arc_degrees) / 2.0 if heading_angle is not None else 180.0
    r = min(int(max_range), max(w, h))

    min_x = max(0, x0 - r)
    max_x = min(w - 1, x0 + r)
    min_y = max(0, y0 - r)
    max_y = min(h - 1, y0 + r)

    perimeter_targets: Set[Tuple[int, int]] = set()
    for x in range(min_x, max_x + 1):
        perimeter_targets.add((x, min_y))
        perimeter_targets.add((x, max_y))
    for y in range(min_y, max_y + 1):
        perimeter_targets.add((min_x, y))
        perimeter_targets.add((max_x, y))

    z0 = float(origin[2]) if len(origin) > 2 else cell_elevation(record, x0, y0)
    z_eye = z0 + EYE_HEIGHT_FLOORS

    # Rays overlap heavily near the observer, so each cell is read once.
    memo: Dict[Tuple[int, int], Tuple[float, float, float]] = {}

    def props(cx: int, cy: int) -> Tuple[float, float, float]:
        got = memo.get((cx, cy))
        if got is None:
            got = cell_obstacle_properties(record, cx, cy, world)
            memo[(cx, cy)] = got
        return got

    for tx, ty in perimeter_targets:
        if tx == x0 and ty == y0:
            continue
        ray_cells = supercover_line(x0, y0, tx, ty)
        # Stop at the grid edge: the sweep must not read cells that do not exist.
        inside = []
        for c in ray_cells:
            if not (0 <= c[0] < w and 0 <= c[1] < h):
                break
            inside.append(c)
        for cx, cy, d, seen, _hidden, _blocker in _scan_ray(inside, x0, y0, z_eye, max_range, props):
            if not seen:
                continue
            if heading_angle is not None:
                cell_angle = math.degrees(math.atan2(cy - y0, cx - x0))
                angle_diff = abs((cell_angle - heading_angle + 180.0) % 360.0 - 180.0)
                if angle_diff > half_arc:
                    _, obs_h, _ = props(cx, cy)
                    if d > peripheral_range and obs_h < PERIPHERAL_LANDMARK_HEIGHT:
                        continue
            visible.add((cx, cy))

    return visible


# ───────────────────────── Hydrology & Gradient Flow (task-745) ─────────────

COMPASS_8_OFFSETS = [
    (1, 0),    # 0: East
    (1, 1),    # 1: Southeast
    (0, 1),    # 2: South
    (-1, 1),   # 3: Southwest
    (-1, 0),   # 4: West
    (-1, -1),  # 5: Northwest
    (0, -1),   # 6: North
    (1, -1),   # 7: Northeast
]
COMPASS_8_BEARINGS = ("e", "se", "s", "sw", "w", "nw", "n", "ne")

CELL_WALK_METRES: float = 80.0    # 1 cell = 1 minute walk ≈ 80m across
STOREY_DROP_METRES: float = 3.0  # 1 storey = 3m vertical drop


def is_water_cell(record: dict, x: int, y: int) -> bool:
    """Check if cell (x, y) carries a water biome, surface, or tag."""
    b_id = cell_biome(record, x, y)
    if not b_id:
        return False
    b_str = str(b_id).lower()
    if any(w in b_str for w in ("river", "water", "lake", "ocean", "stream", "rapids", "waterfall", "sea")):
        return True
    from engine import biomes as biomes_mod
    rec = biomes_mod.biome(b_id) or {}
    if rec.get("terrain") == "water":
        return True
    if rec.get("surface") in ("shallow_water", "deep_water"):
        return True
    tags = [str(t).lower() for t in (rec.get("tags") or [])]
    return any(t in ("water", "river", "stream", "lake", "ocean", "rapids", "waterfall") for t in tags)


def slope_to_current_strength(drop_storeys: int) -> int:
    """Map storey elevation drop across contiguous cells to current strength ladder (1-20).

    Calibrated Hydrology Model (task-745):
      - 0 storeys drop (0% slope): calm meander -> strength 1 (routine, DC 8)
      - 1 storey drop (~1.9-3.7% slope): swift current / riffle -> strength 5 (DC 10-12)
      - 2-3 storeys drop (~7.5-11% slope): whitewater rapids -> strength 10 (DC 15-18)
      - 4+ storeys drop (>15% slope): waterfall / cataract -> strength 20 (DC 20-25)
    """
    if drop_storeys <= 0:
        return 1
    if drop_storeys == 1:
        return 5
    if drop_storeys in (2, 3):
        return 10
    return 20


def derive_water_current(
    record: dict,
    x: int,
    y: int,
    world: Optional[object] = None,
) -> Optional[dict]:
    """Derive flow direction, velocity strength, and hazard for a water cell.

    Water flows downhill. Derives flow vector and velocity from the gradient of the
    floor storey layer across contiguous water cells using the calibrated slope model:
      - 0 storeys drop: calm meander (strength 1)
      - 1 storey drop (3m over 80-160m, ~1.9-3.7% slope): swift current (strength 5)
      - 2-3 storeys drop (6-9m over 80m, ~7.5-11% slope): rapids (strength 10)
      - 4+ storeys drop (>=12m over 80m, >15% slope): waterfall / cataract (strength 20)

    A manual 'current' paint layer override takes precedence (used for whirlpools,
    conduits, surges).

    Returns None if cell is not water; otherwise returns dict:
      - direction: int (0-7 compass index: 0=E, 1=SE, 2=S, 3=SW, 4=W, 5=NW, 6=N, 7=NE)
      - bearing: str ("e", "se", "s", "sw", "w", "nw", "n", "ne")
      - strength: int (1-20)
      - drop: int (elevation drop in storeys to downstream neighbor)
      - hazard_id: Optional[str] (e.g. "river", "rapids", "fall")
      - slope_percent: float
      - manual_override: bool
    """
    if not is_water_cell(record, x, y):
        return None

    layers = record.get("layers") or {}
    current_layer = layers.get("current") or {}
    key = f"{x},{y}"
    manual = None
    if key in current_layer:
        manual_val = current_layer[key]
        if isinstance(manual_val, dict):
            manual = manual_val
        elif isinstance(manual_val, (int, float)):
            manual = {"strength": int(manual_val), "direction": 0}

    from engine import biomes as biomes_mod
    b_id = cell_biome(record, x, y)
    b_hazard = biomes_mod.biome_hazard(b_id) if b_id else None

    if manual is not None:
        str_val = max(1, min(20, int(manual.get("strength", 5))))
        dir_val = int(manual.get("direction", 0)) % 8
        bearing_val = COMPASS_8_BEARINGS[dir_val]
        return {
            "direction": dir_val,
            "bearing": bearing_val,
            "strength": str_val,
            "drop": 0,
            "hazard_id": manual.get("hazard_id") or b_hazard or "river",
            "slope_percent": 0.0,
            "manual_override": True,
        }

    z0 = cell_elevation(record, x, y)
    best_drop = -999999
    best_idx = 0
    best_dist = CELL_WALK_METRES
    downstream_found = False

    for idx, (dx, dy) in enumerate(COMPASS_8_OFFSETS):
        nx, ny = x + dx, y + dy
        if not is_water_cell(record, nx, ny):
            continue
        nz = cell_elevation(record, nx, ny)
        drop = z0 - nz
        dist = CELL_WALK_METRES if (dx == 0 or dy == 0) else (CELL_WALK_METRES * 1.41421356)
        if drop > 0:
            downstream_found = True
            grad = drop / dist
            best_grad = best_drop / best_dist if best_drop > 0 else -1.0
            if grad > best_grad:
                best_drop = drop
                best_idx = idx
                best_dist = dist
        elif not downstream_found and drop == 0 and best_drop < 0:
            best_drop = 0
            best_idx = idx
            best_dist = dist

    if best_drop < 0:
        best_drop = 0
        best_idx = 0
        best_dist = CELL_WALK_METRES

    strength = slope_to_current_strength(best_drop)
    slope_pct = (best_drop * STOREY_DROP_METRES / best_dist) * 100.0 if best_drop > 0 else 0.0

    if best_drop >= 4 or b_id == "waterfall":
        hazard_id = "fall"
    elif best_drop in (2, 3) or b_id == "river_rapids":
        hazard_id = "rapids"
    elif b_hazard:
        hazard_id = b_hazard
    elif best_drop == 1 or b_id in ("river_swift", "river"):
        hazard_id = "river"
    else:
        hazard_id = None

    return {
        "direction": best_idx,
        "bearing": COMPASS_8_BEARINGS[best_idx],
        "strength": strength,
        "drop": max(0, best_drop),
        "hazard_id": hazard_id,
        "slope_percent": round(slope_pct, 2),
        "manual_override": False,
    }
