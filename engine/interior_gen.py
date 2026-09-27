"""Interior plans for building types, generated as **paint** (task-567).

A building interior is a lot of cells. Painting an apartment block by hand is
twenty rooms across three storeys; painting the Downtown district is fourteen
buildings. So a building *type* brings its own plan, the author paints one cell
per building, and edits what the generator made.

**The generator paints, it does not mint.** That is the whole design, and it is
what makes every other decision here cheap:

- A recipe's output is a set of ``(layer, x, y, value)`` cells written into the
  child scope's grid, not a parallel world format. The **standard compiler**
  (:mod:`engine.world_compile`) then builds the areas, the doorways, the merge
  rules (task-564), the storey steps (task-562) and the descriptions. There is
  one place that knows how a grid becomes places, and this is not it.
- So "then edited" is free: an author edits paint, in the same painter, with the
  same tools (task-536's rail and marquee included). Nothing about a generated
  interior is a different kind of thing from a hand-drawn one.
- And because the areas carry ``generated`` provenance naming the *child* scope,
  Ungenerate on that child still empties it cleanly, exactly as for a painted one.

**Author edits survive a re-generate, by being detected rather than locked**
(:func:`diverged_cells`). The scope records what the generator wrote, per cell.
On a re-generate, any cell whose current value no longer matches what was
recorded has been *changed by somebody*, and is left alone. No per-cell lock to
set, no divergence list to maintain, and a cell the author happened not to touch
is re-written to exactly what the plan says. The alternative — a manual lock per
cell — would be a second concept for the same fact, and the author would have to
remember to set it.

Templates live in ``data/worldpainter/interiors.json`` as drawn plans (one
character per cell, plus a legend), because a floor plan is a *picture* and
authoring one as nested Python lists makes it unreadable. The fallback template
gives every building type something walkable, so a new building is never a
building you cannot enter.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Tuple

from engine import biomes as biomes_mod
from engine import world_grid as wg
from engine.generation import GenerationPatch, GenerationReport, provenance

#: Where the drawn plans live. Overridable for tests and for a world that ships
#: its own set of buildings.
INTERIORS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "worldpainter", "interiors.json")

#: The recipe id recorded on every generated cell's scope, so a plan change is
#: visible in a save the way a compiler change is.
RECIPE_ID = "interior.v1"

_cache: Dict[str, dict] = {}


def interiors(path: Optional[str] = None) -> dict:
    """The drawn plans, loaded once. ``{}`` when the file is missing or broken."""
    target = path or INTERIORS_PATH
    if target in _cache:
        return _cache[target]
    try:
        with open(target, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        data = {}
    _cache[target] = data if isinstance(data, dict) else {}
    return _cache[target]


def template_for(building_id: str, path: Optional[str] = None) -> Tuple[dict, bool]:
    """``(template, is_fallback)`` for a building type.

    Every building type gets a plan. A type with no drawn plan gets the fallback
    rather than a refusal, because "this building has no interior" is a worse
    answer than "this building has a plain one" — and the caller is told which
    happened, so the report can name it.
    """
    data = interiors(path)
    plans = data.get("plans") or {}
    template = plans.get(str(building_id))
    if isinstance(template, dict) and template.get("plan"):
        return template, False
    fallback = data.get("fallback") or {}
    if not fallback.get("plan"):
        return {}, True
    return fallback, True


def _rectangle(rows: List[str], legend: dict, notes: List[str], key: str
               ) -> List[str]:
    """A plan as a rectangle, padding short rows with the wall token.

    A ragged plan is a typo — one row written a character short — and refusing to
    generate because of it would make a data mistake look like a broken feature.
    So the row is padded and **said in the report**: the author finds out their
    plan has a hole in it from the generate report, not from a crash.
    """
    if not rows:
        return []
    width = max(len(row) for row in rows)
    # The pad has to be something a character cannot walk into. A door token would
    # be the worst possible choice — padding a short row with doors punches holes
    # in the building — so the preference is `solid` first, then any structure
    # cell that is not passable, and only then an empty cell. Note that
    # ``cell_kind`` returns the *kind* (``solid``/``passable``/``see_through``),
    # not the ``not_a_place`` tag, so a predicate written against the tag would
    # silently fall through to the wrong token.
    pad = None
    for token, value in legend.items():
        if isinstance(value, str) and biomes_mod.cell_kind(value) == "solid":
            pad = token
            break
    if pad is None:
        for token, value in legend.items():
            if isinstance(value, str) and biomes_mod.cell_kind(value) not in (
                    "place", "passable", ""):
                pad = token
                break
    if pad is None:
        # A legend with nothing solid in it is a plan with no walls, which is a
        # strange thing to want; padding it with a door is not the answer.
        pad = None
    out = []
    for row in rows:
        if len(row) < width:
            notes.append(f"{key}: a plan row was {width - len(row)} character(s) "
                         f"short and was padded with "
                         + (f"{pad!r}" if pad is not None else "nothing"))
            row = row + (pad or "") * (width - len(row))
        out.append(row)
    return out


def plan_cells(building_id: str, *, storeys: Optional[int] = None,
               path: Optional[str] = None
               ) -> Tuple[Dict[Tuple[int, int, str], str], List[str]]:
    """The cells a building type's plan paints: ``{(x, y, layer): value}``.

    Returns ``(cells, notes)``. Layers are ``biome`` for the rooms and ``floor``
    for the storey index, which is why the key carries one: a cellar is a room
    painted on ``-1``, not a room that happens to be low.

    ``storeys`` overrides the template's height; ``repeat_storeys`` reuses the plan
    on every floor above the first, which is what an apartment block or a keep
    is — the same plan, stacked.
    """
    notes: List[str] = []
    template, is_fallback = template_for(building_id, path)
    if not template:
        return {}, [f"no interior template for {building_id!r} and no fallback"]
    if is_fallback:
        notes.append(f"{building_id!r} has no drawn plan; used the plain interior")

    legend = template.get("legend") or {}
    rows = _rectangle(list(template.get("plan") or []), legend, notes,
                      str(template.get("label") or building_id))
    height = max(1, int(storeys if storeys is not None else template.get("storeys", 1)))
    if template.get("repeat_storeys"):
        floors = list(range(height))
    else:
        # An explicit per-row `floors` list is the common case: a cellar, a ground
        # floor and an attic in one plan. A plan without one is all on one storey.
        listed = template.get("floors")
        floors = [int(f) for f in listed] if isinstance(listed, list) and listed \
            else [0] * len(rows)
        if height > 1 and not template.get("repeat_storeys"):
            notes.append(f"{building_id!r} declares {height} storeys but its plan "
                         f"paints one; the height is ignored")
            height = 1

    cells: Dict[Tuple[int, int, str], str] = {}
    for index, row in enumerate(rows):
        floor = floors[index] if index < len(floors) else floors[-1]
        for x, token in enumerate(row):
            if token not in legend:
                notes.append(f"plan token {token!r} at ({x},{index}) is not in the "
                             f"legend; the cell was left empty")
                continue
            value = legend[token]
            if value is None:
                continue
            cells[(x, index, "biome")] = str(value)
            cells[(x, index, "floor")] = floor
    return cells, notes


def diverged_cells(record: dict, cells: Dict[Tuple[int, int, str], str]
                   ) -> List[Tuple[int, int, str]]:
    """The generated cells whose current value no longer matches what was written.

    **This is the edit protection, and it is derived rather than declared**
    (task-567 asked for a decision here). The scope record keeps
    ``generated_cells`` — what the generator last wrote, per cell. A cell whose
    current paint differs from that has been changed by a person, so a
    re-generate leaves it alone.

    Three things fall out of deriving it instead of storing a lock:

    - nothing extra for the author to maintain or remember;
    - a cell the author did *not* touch is re-written to exactly what the plan
      says, so a plan fix reaches the cells that were never hand-edited;
    - clearing a cell back to unpainted is an edit too, and is respected — an
      author who erased a room gets it to stay erased.

    A cell the generator never wrote is not a divergence, it is a cell the author
    added, and it is left alone for the same reason.
    """
    written = (record.get("generated_cells") or {})
    layers = record.get("layers") or {}
    out: List[Tuple[int, int, str]] = []
    for key, value in cells.items():
        x, y, layer = key
        recorded = written.get(f"{layer}:{x},{y}")
        if recorded is None:
            continue                      # never generated → the author's own
        current = (layers.get(layer) or {}).get(wg.cell_key(x, y))
        current = None if current in (None, "") else str(current)
        if current != str(recorded):
            out.append(key)
    return out


def generate_interior(manifest: Dict[str, dict], scope_id: str, building_id: str,
                      *, storeys: Optional[int] = None, tick: int = 0,
                      seed: Optional[str] = None, path: Optional[str] = None,
                      ) -> GenerationPatch:
    """Paint a building type's interior into a child scope, as a patch.

    **Paint only.** The patch carries no nodes and no edges: it writes the grid
    and marks the scope unmade-so-far, and the author (or the next Generate) runs
    the standard compiler over it. That is deliberate — see the module docstring —
    and it is also why this can be re-run over a partly hand-edited interior
    without the two halves of the world disagreeing about what a room is.

    Author edits are protected by :func:`diverged_cells`, and the cells that were
    kept are named in the report, because a regenerate that quietly did half its
    work would be worse than one that refused.
    """
    if scope_id not in manifest:
        raise ValueError(f"no such scope {scope_id!r}")
    record = manifest[scope_id]
    cells, notes = plan_cells(building_id, storeys=storeys, path=path)
    if not cells:
        return GenerationPatch(nodes=[], edges=[], area_scope_assignments={},
                               generated_manifest_updates={},
                               report=GenerationReport(
                                   scope_id=scope_id, recipe_id=RECIPE_ID,
                                   seed=str(seed or scope_id),
                                   notes=notes or ["nothing to paint"]))

    kept = set(diverged_cells(record, cells))
    painted = {k: v for k, v in cells.items() if k not in kept}
    if kept:
        shown = ", ".join(f"{layer} ({x},{y})" for (x, y, layer) in sorted(kept)[:6])
        notes.append(f"{len(kept)} cell(s) you had changed were left alone: {shown}"
                     + (" …" if len(kept) > 6 else ""))

    if not wg.has_grid(record):
        # A promoted or hand-authored child may have no grid yet; the plan's own
        # bounds are the natural size, and a name-less child is still a room.
        w = max((x for (x, _, _) in cells), default=0) + 1
        h = max((y for (_, y, _) in cells), default=0) + 1
        wg.ensure_grid(record, w, h, mode="interior")
        notes.append(f"gave the scope a {w}x{h} grid to paint the plan into")

    layers = record.setdefault("layers", {})
    biome_layer = layers.setdefault("biome", {})
    floor_layer = layers.setdefault("floor", {})
    for (x, y, layer), value in sorted(painted.items()):
        key = wg.cell_key(x, y)
        if layer == "floor":
            floor_layer[key] = value
        else:
            biome_layer[key] = value

    # What we wrote, so the next run can tell an edit from its own output. Floor
    # cells are recorded as the number they were written as, so a storey change is
    # a divergence like any other.
    written = dict(record.get("generated_cells") or {})
    for (x, y, layer), value in painted.items():
        written[f"{layer}:{x},{y}"] = value
    for (x, y, layer) in kept:
        written.pop(f"{layer}:{x},{y}", None)

    if seed is None:
        seed = f"{scope_id}:{building_id}:{RECIPE_ID}"
    # **The record is this recipe's output.** A paint recipe has no nodes to
    # return, so there is nothing for `apply_patch` to do and the manifest is
    # written here — which is why the route commits the manifest and does not
    # apply a patch. `generated_manifest_updates` still carries the same keys so a
    # caller that *does* apply patches (a test, a future batch) gets the same
    # result, and the two cannot drift: they are the same dict.
    updates: Dict[str, object] = {
        "generated_cells": written,
        "generated_building": str(building_id),
        # Paint is not generation: the scope stays `unmade` until someone runs
        # ⚙ Generate on it, which is what turns paint into areas. Claiming
        # `materialized` here would hand the author a scope with no places in it.
        "state": "unmade",
    }
    record.update(updates)
    report = GenerationReport(
        scope_id=scope_id, recipe_id=RECIPE_ID,
        seed=str(seed),
        notes=[f"painted {len(painted)} interior cell(s) for {building_id!r}"
               + (f"; kept {len(kept)} you had edited" if kept else "")]
        + notes)
    return GenerationPatch(nodes=[], edges=[], area_scope_assignments={},
                           generated_manifest_updates=updates, report=report)
