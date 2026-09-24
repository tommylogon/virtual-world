"""WorldPainter scope grids and feature placements (task-495).

A world scope owns a bounded grid at its own resolution. The grid is the
authoring substrate for a painted world (task-495); the grid→graph compiler
(task-496) later turns it into areas + ways via task-398's ``GenerationPatch``.
Nothing here is engine behaviour yet — these are pure helpers over the scope
manifest, so the editor, the compiler, and the tests can agree on one shape.

Data model
----------
Grid state lives on the *scope record* inside the world-scope manifest
(``engine/world_scopes.py``; persisted as ``world.world_scopes``), under three
keys, so a scope with no grid costs nothing and older saves load unchanged::

    record["mode"]       = "world" | "town" | "interior"   (optional)
    record["grid"]       = {"w": int, "h": int, "cell_scale": float}
    record["layers"]     = {"biome": {"<x>,<y>": value},   # value is a biome id
                            "road":  {"<x>,<y>": value},   # road/surface id
                            "elevation": {"<x>,<y>": number}}
    record["placements"] = {child_scope_id: {"x": int, "y": int}}

Features — a village inside a forest — are **child scopes placed at a cell**, so
they live in ``placements`` rather than a separate paint layer;
:func:`feature_layer` derives the ``feature`` paint view the editor draws.

Coordinates are integer ``(x, y)`` with ``(0, 0)`` at the top-left and ``y``
increasing downward, matching a normal image grid. A cell's **stable identity**
is :func:`cell_id` (``"<scope_id>:<x>,<y>"``), which the compiler uses as the
area id so a reference survives edits elsewhere on the grid.

Overlap rule (task-495 acceptance)
----------------------------------
Placing or moving a feature onto an occupied cell is **forbidden by default**:
the caller must move or delete the occupant first, so a placement can never
silently clobber another child. Passing ``on_overlap="displace"`` opts a call
into replacing the occupant. "Merge" is deliberately *not* implemented here — it
would have to redefine child-scope identity, and the design note
(``docs/design/worldpainter-knowledge-and-fog.md``) leaves grid-canonical vs
baked handling to the compiler (task-496).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

#: The three editor modes (task-495). A world grid paints zones as cells, a town
#: grid paints walls/gates/roads/buildings, an interior grid paints rooms/doors.
MODES = ("world", "town", "interior")

#: Paint layers a grid may carry. ``feature`` is *derived* from placements, not
#: stored, so it is not listed here.
PAINT_LAYERS = ("biome", "road", "elevation")

ON_OVERLAP = ("forbid", "displace")


# ───────────────────────────── identities ─────────────────────────────────


def cell_id(scope_id: str, x: int, y: int) -> str:
    """Stable global id for a grid cell — the compiler's future area id.

    Stable under unrelated edits: moving a feature or painting another cell does
    not change this string, so a save that referenced the cell still resolves.
    """
    return f"{scope_id}:{int(x)},{int(y)}"


def parse_cell_id(value: str) -> Optional[Tuple[str, int, int]]:
    """Inverse of :func:`cell_id` — ``(scope_id, x, y)``, or ``None`` if malformed."""
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
    untouched — no empty containers are added, so manifests stay small and
    older saves load byte-identically. Values that cannot be parsed are dropped
    rather than raising, so one bad save cannot make the whole manifest
    unloadable.
    """
    if not isinstance(record, dict):
        return record
    if not any(key in record for key in ("grid", "layers", "placements", "mode")):
        return record

    grid = record.get("grid")
    if isinstance(grid, dict):
        w, h = _as_int(grid.get("w")), _as_int(grid.get("h"))
        if w and h and w > 0 and h > 0:
            record["grid"] = {
                "w": w,
                "h": h,
                "cell_scale": _as_float(grid.get("cell_scale"), 1.0),
            }
        else:
            record.pop("grid", None)
    elif "grid" in record:
        record.pop("grid", None)

    if "layers" in record:
        layers = record.get("layers")
        clean_layers: Dict[str, dict] = {}
        if isinstance(layers, dict):
            for layer in PAINT_LAYERS:
                values = layers.get(layer)
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

    mode = record.get("mode")
    if mode is not None and str(mode) not in MODES:
        record.pop("mode", None)
    return record


def _as_int(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ─────────────────────────────── grid ─────────────────────────────────────


def has_grid(record: dict) -> bool:
    grid = (record or {}).get("grid")
    return bool(isinstance(grid, dict) and grid.get("w") and grid.get("h"))


def ensure_grid(record: dict, w: int, h: int, cell_scale: float = 1.0,
                mode: Optional[str] = None) -> dict:
    """Create or resize a scope's grid. Resizing keeps paint that stays in bounds.

    Raises ``ValueError`` for a non-positive size or an unknown mode so the
    editor/compiler never operate on a degenerate grid.
    """
    w, h = int(w), int(h)
    if w <= 0 or h <= 0:
        raise ValueError("grid must be at least 1x1")
    if mode is not None and mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}; expected one of {MODES}")
    record["grid"] = {"w": w, "h": h, "cell_scale": float(cell_scale or 1.0)}
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


# ─────────────────────────────── painting ─────────────────────────────────


def paint(record: dict, layer: str, x: int, y: int, value) -> dict:
    """Set a cell's value on *layer*. ``value`` of ``None``/``""`` erases it.

    Raises ``ValueError`` for an unknown layer, a grid-less scope, or a cell
    outside the grid — painting off-grid would create a cell the compiler cannot
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
    half-paint a route — the same "reject before mutating" rule ``apply_patch``
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
    return ((record or {}).get("layers") or {}).get(layer, {}).get(cell_key(x, y))


# ────────────────────────── reference image ───────────────────────────────

#: Faint by default so painted cells read over the art underneath.
REFERENCE_OPACITY_DEFAULT = 0.5


def reference(record: dict) -> Optional[dict]:
    """The scope's authoring reference image, or ``None``."""
    ref = (record or {}).get("reference")
    return dict(ref) if isinstance(ref, dict) and ref.get("image") else None


def set_reference(record: dict, image, opacity=None, visible=None) -> Optional[dict]:
    """Set or clear a scope's reference image (a picture to paint over).

    Reference-only: it is never compiled into areas/ways, so a huge or stale
    image cannot affect the world — it just helps the author place cells over
    known art. ``image`` of ``None``/``""`` clears it.
    """
    if image in (None, ""):
        record.pop("reference", None)
        return None
    if not has_grid(record):
        raise ValueError("scope has no grid")
    try:
        value = float(REFERENCE_OPACITY_DEFAULT if opacity is None else opacity)
    except (TypeError, ValueError):
        value = REFERENCE_OPACITY_DEFAULT
    record["reference"] = {
        "image": str(image),
        "opacity": max(0.0, min(1.0, value)),
        "visible": True if visible is None else bool(visible),
    }
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


def place(manifest: Dict[str, dict], parent_id: str, child_id: str,
          x: int, y: int, *, on_overlap: str = "forbid") -> str:
    """Place child scope *child_id* at a cell of *parent_id*'s grid.

    Returns ``"placed"``, ``"moved"`` or ``"displaced"``. Raises ``ValueError``
    for a missing parent/child, a grid-less parent, an out-of-bounds cell, an
    unknown overlap policy, or a forbidden overlap.
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
    if current.get(child_id) is not None:
        outcome = "moved"
    current[child_id] = {"x": int(x), "y": int(y)}
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
