from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set, Tuple

from .world_compile_directions import DIRECTIONS
from engine import biomes as biomes_mod
from engine import world_grid as wg


def _region_authored_name(cells: List[Tuple[int, int]],
                          names: Dict[str, str]) -> Optional[str]:
    """The author name for a whole region (task-560), or None.

    A merged region is one place, and its name should not depend on the author
    knowing that the *anchor* cell is the top-left-most one - naming the middle of
    a High Street is the natural thing to do. So the first named cell in region
    order speaks for the region, exactly as the anchor does for biome and road. Two
    different names in one region is an authoring slip, and the first wins rather
    than the region being left unnamed.
    """
    for cell in cells:
        value = str((names or {}).get(wg.cell_key(*cell), "") or "").strip()
        if value:
            return value
    return None




def _regions(cells: List[Tuple[int, int]], identity, *,
             default_merge: bool = True,
             always_merge: Optional[Set[Tuple[int, int]]] = None,
             never_merge: Optional[Set[Tuple[int, int]]] = None):
    """Flood-fill 8-neighbour cells of the same *identity* into ordered regions.

    ``identity`` maps a cell to what kind of place it is - the road if one is
    painted, else the biome (task-496). Passing the identity function rather
    than a biome map is what lets a run of road cells merge into one road area
    while staying distinct from the forest beside it.

    ``default_merge`` is the scope's own merge switch, and it is the *default*, not
    the rule: ``always_merge`` and ``never_merge`` are per-kind overrides of it
    (task-564), passed as *cells* rather than as rules because the rule is resolved
    by the caller, which has the biome and road layers and the taxonomy.

    Two overrides, and they are resolved in one place on purpose. A region is
    exactly a connected set of like cells, so a cell in ``never_merge`` never joins
    the region of the cell it is scanning from, and a cell in ``always_merge``
    joins it even with the switch off - otherwise turning the switch off to stop a
    terrace of cottages becoming one house would also shred a corridor into ten
    one-cell rooms, which is the other half of the same problem.
    """
    remaining = set(cells)
    always_merge = always_merge or set()
    never_merge = never_merge or set()

    def joins(cell, nb) -> bool:
        """May ``cell`` and its like-identity neighbour ``nb`` be one place?"""
        if identity(nb) != identity(cell):
            return False
        both_forced = cell in always_merge and nb in always_merge
        if both_forced:
            return True
        if cell in never_merge or nb in never_merge:
            return False
        return default_merge

    regions: List[List[Tuple[int, int]]] = []
    for start in sorted(cells, key=lambda c: (c[1], c[0])):
        if start not in remaining:
            continue
        stack = [start]
        remaining.discard(start)
        comp = []
        while stack:
            cell = stack.pop()
            comp.append(cell)
            for dx, dy in DIRECTIONS.values():
                nb = (cell[0] + dx, cell[1] + dy)
                if nb in remaining and joins(cell, nb):
                    remaining.discard(nb)
                    stack.append(nb)
        regions.append(sorted(comp, key=lambda c: (c[1], c[0])))
    return regions




def _region_climate(cells: List[Tuple[int, int]], cell_climate
                    ) -> Tuple[str, bool]:
    """One climate for a region, and whether its cells disagreed (task-557).

    Returns ``(climate, mixed)``.

    **Majority of cells, ties broken by the region's first cell in row-major
    order.** Both halves are there for a reason. A majority is how a real climate
    is summarised - one place is one climate, and a handful of cells painted the
    other way does not make the place two climates. The tie-break makes the
    answer *deterministic*: an even split of a 2-cell region would otherwise
    depend on iteration order, and a grid that compiled differently on two
    machines is the bug this whole task is about.

    Unpainted cells are not votes. They are ``None`` here and simply do not count,
    so a region that is one painted cell of ``arctic`` in a sea of nothing is
    arctic - and a region with nothing painted at all is left for the caller to
    treat as temperate, which is the engine's long-standing 21 °C.
    """
    votes: Dict[str, int] = {}
    first: Dict[str, Tuple[int, int]] = {}
    for cell in sorted(cells, key=lambda c: (c[1], c[0])):
        climate = cell_climate(cell)
        if not climate:
            continue
        votes[climate] = votes.get(climate, 0) + 1
        if climate not in first:
            first[climate] = cell
    if not votes:
        return "", False
    best = max(votes.values())
    tied = [c for c, n in votes.items() if n == best]
    if len(tied) == 1:
        winner = tied[0]
    else:
        winner = min(tied, key=lambda c: (first[c][1], first[c][0]))
    return winner, len(votes) > 1




def _merge_always_cells(cells: List[Tuple[int, int]], cell_biome, cell_road
                        ) -> Set[Tuple[int, int]]:
    """Cells whose kind says "merge me with my like" (task-564)."""
    return {c for c in cells
            if biomes_mod.merge_rule(cell_biome(c) or cell_road(c)) == biomes_mod.MERGE_ALWAYS}




def _merge_never_cells(cells: List[Tuple[int, int]], cell_biome, cell_road
                       ) -> Set[Tuple[int, int]]:
    """Cells whose kind says "never merge me" (task-564) - every building.

    A building cell is a **plot**: the terrace next door is another building, and a
    merged pair would be one house with one door and the wrong number of beds. The
    rule comes from :func:`biomes_mod.merge_rule`, which reads ``merge:never`` off
    the record and reports every building as never-merge without 31 records having
    to say so.
    """
    return {c for c in cells
            if biomes_mod.merge_rule(cell_biome(c) or cell_road(c)) == biomes_mod.MERGE_NEVER}


#: Storeys you may stride between on open ground before the step stops being a
#: walk (task-525). Three is chosen so an ordinary building is free - a house with
#: a cellar is two - and a cliff, a keep wall or the side of a ravine is not.
#: Per-scope overridable; see :func:`_climb_threshold`.
DEFAULT_MAX_STOREY_STEP = 3




def _region_components(n_regions: int,
                       pairs: Set[Tuple[int, int]]) -> List[List[int]]:
    """Union-find of regions joined by ``pairs`` → one list of members each."""
    parent = list(range(n_regions))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in pairs:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    grouped: Dict[int, List[int]] = {}
    for i in range(n_regions):
        grouped.setdefault(find(i), []).append(i)
    return list(grouped.values())


# ───────────────────────────── preflight ───────────────────────────────────

#: Preflight severities. ``block`` is a condition :func:`compile_grid` refuses -
#: or one it starts refusing the moment the author carries out the remedy.
#: ``warn`` is advice: nothing is refused, but the result will not be what the
#: author expected, and a silent result is what made this worth building.
BLOCK = "block"
WARN = "warn"

#: Upper bound on the nodes one area can add, used only to warn *before* the
#: limit is hit. A cell is scanned in four directions (:data:`_SCAN_DIRECTIONS`),
#: so a scope of N areas mints at most ~4N ways on top of its N areas. The real
#: check is in :func:`engine.generation.apply_patch`; this is the early warning
#: that lets the author halve the scope rather than discover it as a 400.
_WAYS_PER_AREA_UPPER = 4




