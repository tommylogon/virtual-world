"""WorldPainter biome/feature taxonomy (task-497).

Data-first definition of the tiles a painted world is drawn from: each biome maps
to the engine **area tags** an area gets and the **forage skills** that work
there, with deterministic description fragments; features (road, bridge, town,
ruin, ...) name where they may appear; and resource/hostile distribution tables
say what a painted area is likely to hold.

The taxonomy is *data*: :func:`validate` is generic, so adding a biome is a JSON
edit that reuses existing area tags and forage skills - no code change. The
foraging layer already recognises the biome tags (``engine/foraging.py``
``AREA_SKILL_BONUS``) and the resource tags come from its ``SKILL_TABLES``
vocabulary, so a painted area forages with the machinery that already exists.

Two nouns that are easy to confuse, so they are kept apart on purpose:

- ``surface`` (this module, :func:`ground_surface`) - the ground *material*: dirt,
  grass, stone, sand, pine needles. What your feet are on.
- ``floor`` (``engine/world_grid.py``, area ``properties.floor``) - the *storey
  index*: 0 is ground, 1 one up, -1 one down, unbounded. Which deck of the
  skyscraper, which room of the stacked house, how far under the lake surface.
  An earlier revision of this taxonomy put the material under ``floor``, which
  made "floor" mean two unrelated things; the material moved to ``surface``.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from engine import foraging

#: The shipped taxonomy.
DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "worldpainter", "biomes.json",
)

#: Hostiles the distribution tables may name.
HOSTILE_KINDS = ("predator", "bandit", "monster")

#: Ground material used when a record declares none. This is the *material* you
#: stand on, not a storey - see :func:`ground_surface`.
DEFAULT_SURFACE = "dirt"

#: How a painted cell is *traversable* (task-562).
#:
#: A cell used to be either a place or nothing, which is enough for wilderness and
#: not enough for a floor plan: a Japanese high-school plan needs blanks you cannot
#: walk through, windows you can see through but not through, and a door you can.
#: So a biome record may declare what its cell *is to movement*, and the vocabulary
#: decides - the compiler asks this, rather than knowing that `wall` and `void` are
#: special, so a modder can add a `hedge` or a `turnstile` the same way.
#:
#: - ``place`` - a place. Compiles to an area, as before.
#: - ``solid`` - not a place, and nothing crosses it (a wall, a blank between
#:   rooms, a cliff face). It is also *not* something you can see through.
#: - ``see_through`` - not a place, and nothing walks through it, but you can
#:   *see* through it: a shut window. The adjacent place records it, so the
#:   description can say there is a window there and the map can draw one.
#: - ``passable`` - not a place, but a way may cross it: a door or a gateway
#:   between the two places it stands between.
CELL_KINDS = ("place", "solid", "see_through", "passable")

#: The tag a record uses to say it is not a place at all, and the prefix its cell
#: kind is declared with (``cell_kind:solid``). Kept as tags rather than a new
#: field so a record stays the same shape as every other biome, and so
#: `area_tags()` reports it to the editor.
NOT_A_PLACE_TAG = "not_a_place"
CELL_KIND_TAG_PREFIX = "cell_kind:"

#: The kind to read when a record does not declare one we know. A *place*, on
#: purpose: the alternative (solid) means a misspelled or renamed biome id quietly
#: deletes the author's cells from the map - a wall where their classroom was. An
#: unknown id still compiles to an area and still carries the "no area tag foraging
#: recognises" warning, and `compile_grid` lists unknown ids in its report, so a
#: typo is visible rather than destructive.
DEFAULT_UNKNOWN_CELL_KIND = "place"

#: How a *kind* merges with its like neighbours (task-564), declared as a tag on
#: the record (``merge:always``) for the same reason ``cell_kind:`` is: a modder
#: adding a ``cellar`` or a ``subway`` gets the behaviour without a code change.
#:
#: - ``always`` - same-kind cells always become one place, whatever the scope's
#:   merge switch says. A hallway is a *shape*, not a count: ten cells of corridor
#:   are one corridor, and with the switch off a plan would otherwise be a row of
#:   anonymous one-cell rooms.
#: - ``never`` - same-kind neighbours are always separate places. A building cell
#:   is a *plot*: two adjacent cottages are two cottages, and merging them would
#:   quietly make a terrace one enormous house with one door.
#: - ``""`` (the default) - the scope's own switch decides, which is what every
#:   terrain cell, road and room wants.
MERGE_ALWAYS = "always"
MERGE_NEVER = "never"
MERGE_TAG_PREFIX = "merge:"
MERGE_RULES = (MERGE_ALWAYS, MERGE_NEVER)

#: The tag that says a passable cell is a *stair* (task-568). A passable cell
#: between two storeys already mints a stairway, because the storey is the strongest
#: signal about what crossing it does; this tag lets the author make the same claim
#: directly, and the two produce one kind of way.
STAIR_TAG = "stair"

#: Marks a record as an **indoor room** (task-568). Rooms are exempt from the
#: wild-country contract for the same reason buildings are: nobody forages
#: mushrooms in a latrine, and no wildlife spawns in a corridor. Read as a tag, so
#: a modder adding a room gets the exemption by being one.
INDOOR_TAG = "indoor"

#: Marks a record as a specialized **den, lair, or nest** (feature biomes).
#: Like rooms and buildings, dens have custom authored descriptions and contents
#: rather than generic regional wilderness foraging.
DEN_TAG = "den"

_cache: Dict[str, dict] = {}


# ───────────────────────────── loading ────────────────────────────────────

def load(path: Optional[str] = None, *, fresh: bool = False) -> dict:
    """Load and cache the taxonomy. ``fresh`` bypasses the cache (tests)."""
    key = os.path.abspath(path or DATA_PATH)
    if fresh or key not in _cache:
        with open(key, "r", encoding="utf-8-sig") as f:
            _cache[key] = json.load(f)
    return _cache[key]


def clear_cache() -> None:
    """Drop every cached taxonomy and library-dir read.

    Called from the save/commit path so a hand edit to a biome JSON is visible
    without a server restart. It clears both the bundled ``biomes.json`` cache
    (``_cache``) and the per-file library cache (``_lib_cache``) - the two are
    separate because one is a single file and the other is 106 files, but a
    taxonomy edit is a taxonomy edit and both have to go together.
    """
    _cache.clear()
    _lib_cache.clear()


def biomes(path: Optional[str] = None) -> Dict[str, dict]:
    return load(path).get("biomes") or {}


def features(path: Optional[str] = None) -> Dict[str, dict]:
    return load(path).get("features") or {}


_resource_dir = os.path.join(os.path.dirname(DATA_PATH), "..", "library", "resource_distribution")
_hostile_dir = os.path.join(os.path.dirname(DATA_PATH), "..", "library", "hostile_distribution")
_biome_dir = os.path.join(os.path.dirname(DATA_PATH), "..", "library", "biomes")
_feature_dir = os.path.join(os.path.dirname(DATA_PATH), "..", "library", "features")


def _load_id_dir(directory: str) -> Dict[str, dict]:
    """Load one-file-per-entry JSON files from a library subdirectory."""
    out: Dict[str, dict] = {}
    if not os.path.isdir(directory):
        return out
    for entry in os.listdir(directory):
        if not entry.endswith(".json"):
            continue
        path = os.path.join(directory, entry)
        with open(path, "r", encoding="utf-8-sig") as f:
            out[entry[:-5]] = json.load(f)
    return out


_lib_cache: Dict[str, Dict[str, dict]] = {}


def _load_id_dir_cached(directory: str) -> Dict[str, dict]:
    """Like :func:`_load_id_dir`, but cached for the life of the process.

    The library dirs are static, and preflight reads every biome record once
    per painted cell (task-716): ``cell_kind`` / ``merge_rule`` / ``is_building``
    are called from the per-cell identity and merge passes, and each one
    re-scanned all 106 biome JSON files from disk. A 160x100 grid took ~7
    minutes for a grid read that should take a second - 2.3 million file
    opens for one ``GET /grid``. The directory contents do not change at
    runtime, so caching the parsed result is correct, not a shortcut.
    """
    out = _lib_cache.get(directory)
    if out is None:
        out = _load_id_dir(directory)
        _lib_cache[directory] = out
    return out


_load_library_dir = _load_id_dir_cached


def biomes(path: Optional[str] = None) -> Dict[str, dict]:
    library = _load_id_dir_cached(_biome_dir)
    if library:
        return library
    return load(path).get("biomes") or {}


def features(path: Optional[str] = None) -> Dict[str, dict]:
    library = _load_id_dir_cached(_feature_dir)
    if library:
        return library
    return load(path).get("features") or {}


def resource_distribution(path: Optional[str] = None) -> Dict[str, list]:
    data = load(path)
    bundled = data.get("resource_distribution") or {}
    if bundled:
        return bundled
    library = _load_library_dir(_resource_dir)
    return _library_to_per_biome(library)


def hostile_distribution(path: Optional[str] = None) -> Dict[str, list]:
    data = load(path)
    bundled = data.get("hostile_distribution") or {}
    if bundled:
        return bundled
    library = _load_library_dir(_hostile_dir)
    return _library_to_per_biome_hostile(library)


def resource_library(path: Optional[str] = None) -> Dict[str, dict]:
    """Return raw resource loot table entries from the library dirs.

    Each entry carries ``id``, ``name``, ``biome_tags``, ``location_tags``,
    ``item_tags``, ``weight``, and ``conditions``. The fishing Activity resolver
    (task-716) uses this when it needs the richer schema.
    """
    data = load(path)
    if data.get("resource_distribution"):
        return {}
    return _load_library_dir(_resource_dir)


def hostile_library(path: Optional[str] = None) -> Dict[str, dict]:
    """Return raw hostile loot table entries from the library dirs."""
    data = load(path)
    if data.get("hostile_distribution"):
        return {}
    return _load_library_dir(_hostile_dir)


def _library_to_per_biome(library: Dict[str, dict]) -> Dict[str, list]:
    out: Dict[str, list] = {}
    for entry in library.values():
        for tag in (entry.get("biome_tags") or []):
            out.setdefault(str(tag), []).append({
                "tags": [str(t) for t in (entry.get("item_tags") or [])],
                "weight": entry.get("weight", 1),
            })
    return out


def _library_to_per_biome_hostile(library: Dict[str, dict]) -> Dict[str, list]:
    out: Dict[str, list] = {}
    for entry in library.values():
        out.setdefault(str(entry.get("biome_tags", [None])[0] or ""), []).append({
            "kind": str(entry.get("kind") or ""),
            "base_chance": entry.get("base_chance", 0.0),
            "per_area_from_settlement": entry.get("per_area_from_settlement", 0.0),
            "max_chance": entry.get("max_chance", 1.0),
        })
    return out


def biome(biome_id, path: Optional[str] = None) -> Optional[dict]:
    return biomes(path).get(str(biome_id))


def cell_kind(biome_id, path: Optional[str] = None) -> str:
    """How a cell painted with this biome is *traversable* (task-562).

    One of :data:`CELL_KINDS`. A record with no ``not_a_place`` tag is a place,
    which is every biome that shipped before edge semantics - so this reads as
    "a place" for the whole existing wilderness taxonomy without touching it.

    A cell painted with an id the taxonomy does not know is a *place*, not a hole:
    see :data:`DEFAULT_UNKNOWN_CELL_KIND` for why a typo compiles loudly (a warning
    in the generate report) rather than destructively. The editor's dropdown makes
    typos unlikely, but a hand-edited taxonomy or a renamed record is not a
    hypothetical.
    """
    rec = biome(biome_id, path)
    if rec is None:
        return DEFAULT_UNKNOWN_CELL_KIND
    tags = [str(t).lower() for t in (rec.get("tags") or [])]
    if NOT_A_PLACE_TAG not in tags:
        return "place"
    # The kind is a namespaced tag (``cell_kind:solid``) rather than a field, so a
    # record keeps the same shape as every other biome and `area_tags()` reports it
    # to the editor for free.
    for tag in tags:
        if tag.startswith(CELL_KIND_TAG_PREFIX):
            kind = tag.split(":", 1)[1].strip()
            return kind if kind in CELL_KINDS else DEFAULT_UNKNOWN_CELL_KIND
    return DEFAULT_UNKNOWN_CELL_KIND


def area_tags(biome_id, path: Optional[str] = None) -> List[str]:
    """The engine area tags a painted area of *biome_id* carries."""
    rec = biome(biome_id, path) or {}
    return [str(t).lower() for t in (rec.get("tags") or [])]


#: The tag that makes a record a *building* (task-561/563). A building cell is a
#: thing you **go into** with ``in`` rather than a place you step sideways onto,
#: so the tag is what the compiler asks - vocabulary-driven like
#: :func:`cell_kind`, so a modder's ``watermill`` joins without a code change.
BUILDING_TAG = "building"


def is_building(biome_id, path: Optional[str] = None) -> bool:
    """Whether this biome paints a *building* (task-563).

    True for the 31 building types of task-561 and false for terrain, road
    features and structure. Read from the tag rather than a list of ids, so the
    taxonomy stays the single source of truth for what a cell is.
    """
    return BUILDING_TAG in area_tags(biome_id, path)


def merge_rule(biome_id, path: Optional[str] = None) -> str:
    """How cells of this kind merge (task-564): ``"always"``, ``"never"`` or ``""``.

    ``""`` means "the scope's merge switch decides", which is every biome that
    shipped before per-kind rules. A **building** is ``"never"`` without having to
    say so in 31 records: a plot is a building, so two adjacent building cells are
    two buildings whatever the taxonomy says. Everything else reads its tag.
    """
    if is_building(biome_id, path):
        return MERGE_NEVER
    for tag in area_tags(biome_id, path):
        if tag.startswith(MERGE_TAG_PREFIX):
            rule = tag.split(":", 1)[1].strip()
            if rule in MERGE_RULES:
                return rule
    return ""


def is_stair(biome_id, path: Optional[str] = None) -> bool:
    """Whether this cell is a *stairway* (task-568).

    A passable cell between two storeys mints a stairway on its own - the storey
    step is the strongest signal about what crossing it does. This is the author
    making the same claim directly, so a plan can have a stair between two rooms
    drawn on one storey (a loft stair, a cellar stair) where the floor layer says
    nothing. Both spellings produce the same ``kind: "stairs"`` way.
    """
    return STAIR_TAG in area_tags(biome_id, path)


def biome_height(biome_id, path: Optional[str] = None) -> float:
    """Physical height of this biome in floors / storeys (task-882)."""
    rec = biome(biome_id, path) or {}
    if "height" in rec:
        try:
            return float(rec["height"])
        except (TypeError, ValueError):
            pass
    tags = [str(t).lower() for t in (rec.get("tags") or [])]
    b_id = str(biome_id).lower()
    if "mountain" in tags or "peak" in tags or "cliff" in tags or "mountain" in b_id or "peak" in b_id:
        return 20.0
    if "hill" in tags or "hills" in tags or "hill" in b_id:
        return 5.0
    if is_building(biome_id, path) or "building" in tags:
        return 2.0
    if "wall" in tags or "wall" in b_id:
        return 2.0
    if "dense_forest" in b_id or "jungle" in tags or "dense" in tags:
        return 3.0
    if "sparse_forest" in b_id or "forest" in tags or "wood" in tags or "grove" in tags or "orchard" in tags:
        return 2.0
    if "marsh" in tags or "swamp" in tags or "scrub" in tags:
        return 1.0
    return 0.0


def biome_obscurity(biome_id, path: Optional[str] = None) -> float:
    """Visual obscurity (0.0 to 1.0) accumulated per cell transit (task-882)."""
    rec = biome(biome_id, path) or {}
    if "obscurity" in rec:
        try:
            val = float(rec["obscurity"])
            return max(0.0, min(1.0, val))
        except (TypeError, ValueError):
            pass
    tags = [str(t).lower() for t in (rec.get("tags") or [])]
    b_id = str(biome_id).lower()
    if "mountain" in tags or "peak" in tags or "cliff" in tags or "mountain" in b_id:
        return 1.0
    if is_building(biome_id, path) or "building" in tags or "wall" in tags or "wall" in b_id:
        return 1.0
    if "dense_forest" in b_id or "jungle" in tags or "dense" in tags:
        return 0.8
    if "sparse_forest" in b_id or "forest" in tags or "woods" in tags or "grove" in tags:
        return 0.4
    if "marsh" in tags or "swamp" in tags or "scrub" in tags:
        return 0.2
    if "hill" in tags or "hills" in tags or "hill" in b_id:
        return 0.3
    return 0.0


def biome_hazard(biome_id, path: Optional[str] = None) -> Optional[str]:
    """Return default hazard_id registered on this biome, or None (task-745)."""
    rec = biome(biome_id, path) or {}
    hid = rec.get("hazard_id")
    return str(hid).strip() if hid else None


def entry_phrases(record_id, path: Optional[str] = None) -> Optional[dict]:
    """The narrative move a record asks for when you enter it (task-529).

    Returns ``{"in": ..., "out": ..., "aliases": [...]}`` when the record declares
    an entry, and ``None`` when it does not - which is the signal to fall back to
    deriving one from the placement (see ``world_compile._entry_phrases``).

    Three sources, most specific first, and the reason they are checked in that
    order is that they are three different authors:

    - the **record** (a `tunnel` says "go down the tunnel") - the vocabulary,
      shared by every world, and what a modder edits;
    - the **placement** (`placements[child].entry_phrase`) - *this* mouth of *this*
      tunnel, because a mine with two adits has two ways in and only the author
      knows which is which;
    - the derived phrase - the last resort, and the only one that can be wrong
      without anybody noticing.

    The pair is read together: a record that declares only ``entry_phrase`` still
    gets a sensible way back out, and vice versa.
    """
    rec = features(path).get(str(record_id)) or biomes(path).get(str(record_id))
    if not rec:
        return None
    inward = str(rec.get("entry_phrase") or "").strip()
    outward = str(rec.get("exit_phrase") or "").strip()
    if not inward and not outward:
        return None
    aliases = [str(a).strip().lower() for a in (rec.get("entry_aliases") or [])
               if str(a).strip()]
    return {"in": inward, "out": outward, "aliases": aliases or None}


def forage_skill_bonus(biome_id, path: Optional[str] = None) -> Dict[str, int]:
    """``foraging.AREA_SKILL_BONUS`` merged over a biome's tags (max per skill).

    This is the concrete "usable by engine/foraging.py": a painted forest area is
    foragable exactly as a hand-authored one is, with no extra wiring.
    """
    out: Dict[str, int] = {}
    for tag in area_tags(biome_id, path):
        for skill, bonus in foraging.AREA_SKILL_BONUS.get(tag, {}).items():
            out[skill] = max(out.get(skill, 0), int(bonus))
    return out


def ground_surface(record: Optional[dict],
                   fallback: Optional[dict] = None) -> str:
    """The ground **material** a biome/road record declares (dirt, stone, ...).

    Deliberately *not* called ``floor``. A floor is a **storey index** - 0 is
    ground, 1 is one storey up, -1 one down, and it is unbounded (three stacked
    rooms, a lake bottom at -2, an 80-storey tower, -900 in a hole to hell).
    The material underfoot is a different fact and lives under ``surface``, so
    the two can never be confused for one another.

    *fallback* is consulted when *record* declares no material: a road painted
    over a forest stands on the forest's ground unless the road says otherwise.
    The ``floor`` reads are compatibility fallbacks for taxonomy files written
    before the rename (2026-09-27); the shipped ``biomes.json`` uses ``surface``.
    """
    for source in (record, fallback):
        if not isinstance(source, dict):
            continue
        value = source.get("surface")
        if value in (None, ""):
            value = source.get("floor")       # legacy pre-rename key
        if value not in (None, ""):
            return str(value)
    return DEFAULT_SURFACE


def _forage_vocabulary() -> set:
    """The tag vocabulary the foraging tables draw from (task-497 reuse)."""
    vocab = set()
    for entries in foraging.SKILL_TABLES.values():
        for entry in entries:
            for t in (entry.get("tags") or []):
                vocab.add(str(t).lower())
    return vocab


# ──────────────────────────── validation ──────────────────────────────────

def _num(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


#: Descriptive climate fields a biome MAY carry (task-758). These are for the
#: palette's detail panel, not the painted `climate` layer - which is a 5-value
#: enum (task-557) and must stay an enum, not ranges. Absent = unknown, never
#: guessed.
_CLIMATE_FIELDS = ("temperature", "rainfall", "elevation")
#: Adjacency lists (task-758): a biome id or a documented soft noun.
_NEIGHBOUR_FIELDS = ("natural_neighbors", "unlikely_neighbors", "transition_biomes")


def _climate_problems(bid: str, rec: dict) -> List[str]:
    """Validate a biome's optional ``climate`` block (task-758).

    Absent is valid - the palette shows "unknown". Present must be an object
    whose ``temperature``/``rainfall``/``elevation`` are ``[min, max]`` numbers
    with ``min <= max``.
    """
    climate = rec.get("climate")
    if climate is None:
        return []
    if not isinstance(climate, dict):
        return [f"biome {bid}: climate must be an object"]
    out: List[str] = []
    for field in _CLIMATE_FIELDS:
        rng = climate.get(field)
        if rng is None:
            continue
        if (not isinstance(rng, (list, tuple)) or len(rng) != 2
                or _num(rng[0]) is None or _num(rng[1]) is None):
            out.append(f"biome {bid}: climate.{field} must be [min, max] numbers")
        elif _num(rng[1]) < _num(rng[0]):
            out.append(f"biome {bid}: climate.{field} max < min")
    return out


def _neighbour_problems(bid: str, rec: dict) -> List[str]:
    """Validate a biome's optional adjacency lists (task-758).

    A neighbour is a biome id *or* a documented soft noun ("meadow"), so only the
    shape is checked here - names are not forced into a second vocabulary. The
    compiler-side adjacency rule that consumes them is separate work.
    """
    out: List[str] = []
    for key in _NEIGHBOUR_FIELDS:
        vals = rec.get(key)
        if vals is None:
            continue
        if (not isinstance(vals, list)
                or not all(isinstance(v, str) and v.strip() for v in vals)):
            out.append(f"biome {bid}: {key} must be a list of non-empty strings")
    return out


def _record_tags(rec: dict) -> set:
    return {str(t).lower() for t in (rec.get("tags") or [])}


def is_made_place(rec: dict) -> bool:
    """A *made* place (task-561) - a building or an indoor room, not wild country.

    A building is authored as a biome so it can be a cell with an identity and
    prose, but the wild-country contract does not apply to it: nobody forages
    berries off a smithy's wall, and no wildlife spawns in a bank. So the forage
    tag and distribution checks are skipped - deliberately, not by omission. An
    **indoor room** (task-568) is made in the same sense; it is read from the
    `indoor` tag, so a modder adding a `cellar` is exempt without saying so.
    """
    tags = _record_tags(rec)
    return "building" in tags or INDOOR_TAG in tags


def is_structure(rec: dict) -> bool:
    """Not a place at all (task-562) - a wall, a window, a door, a void.

    A structure cell never compiles to an area, so it has no ground and nothing
    to forage: the checks that ask those questions do not apply.
    """
    return NOT_A_PLACE_TAG in _record_tags(rec)


def record_problems(bid: str, rec: dict) -> List[str]:
    """Per-record taxonomy problems, without cluster-wide coverage checks.

    Shared by :func:`validate` (whole taxonomy) and the vocabulary save route
    (task-589), so a save refuses exactly what ``validate()`` would reject for
    that record. Coverage checks (a wild biome needs resource/hostile rules) are
    cluster-level and stay in :func:`validate`.
    """
    if not isinstance(rec, dict):
        return [f"biome {bid}: not an object"]
    recognized = {str(t).lower() for t in foraging.AREA_SKILL_BONUS}
    skills = set(foraging.SKILL_TABLES)
    out: List[str] = []
    if not rec.get("name"):
        out.append(f"biome {bid}: missing name")
    if not rec.get("terrain"):
        out.append(f"biome {bid}: missing terrain")
    tags = [str(t).lower() for t in (rec.get("tags") or [])]
    if not tags:
        out.append(f"biome {bid}: no area tags")
    elif not (set(tags) & recognized) and not is_made_place(rec) and not is_structure(rec):
        out.append(f"biome {bid}: no area tag foraging recognises "
                   f"({sorted(recognized)}); areas would be barren")
    for skill in (rec.get("forage_skills") or []):
        if str(skill).lower() not in skills:
            out.append(f"biome {bid}: unknown forage skill '{skill}'")
    if not rec.get("surface") and not rec.get("floor") and not is_structure(rec):
        # `floor` on a record used to mean the ground material; it is now the
        # storey index (engine/world_grid.PAINT_LAYERS), so a taxonomy that only
        # has the old key is accepted but flagged by being unrenamed.
        out.append(f"biome {bid}: missing surface (ground material)")
    if not [d for d in (rec.get("descriptions") or []) if str(d).strip()]:
        out.append(f"biome {bid}: no description fragments")
    hazard_id = rec.get("hazard_id")
    if hazard_id is not None:
        from engine import hazards
        if not isinstance(hazard_id, str) or not hazard_id.strip():
            out.append(f"biome {bid}: empty or invalid hazard_id")
        elif hazard_id not in hazards.hazards():
            out.append(f"biome {bid}: unknown hazard_id '{hazard_id}'")
    out.extend(_climate_problems(bid, rec))
    out.extend(_neighbour_problems(bid, rec))
    return out


def feature_problems(fid: str, rec: dict) -> List[str]:
    """Per-feature problems (task-589), without the biome-reference check.

    Shared by :func:`validate` and the vocabulary save route, so a feature save
    refuses exactly what ``validate()`` would for that record. Whether the
    ``biomes`` a feature names exist is cluster-level and stays in ``validate()``.
    """
    if not isinstance(rec, dict):
        return [f"feature {fid}: not an object"]
    out: List[str] = []
    if not rec.get("name"):
        out.append(f"feature {fid}: missing name")
    if not (rec.get("tags") or []):
        out.append(f"feature {fid}: no tags")
    if not [d for d in (rec.get("descriptions") or []) if str(d).strip()]:
        out.append(f"feature {fid}: no description fragments")
    return out


def resource_table_problems(entry_id: str, rec: dict) -> List[str]:
    """Validate one raw resource loot-table entry (task-718/589).

    The raw shape (`id`, `biome_tags`, `item_tags`, `weight`, `conditions`) as the
    file stores it - distinct from the per-biome shape `validate()` checks, which
    `_library_to_per_biome` derives from this.
    """
    if not isinstance(rec, dict):
        return [f"resource_distribution[{entry_id}]: not an object"]
    out: List[str] = []
    if not (rec.get("biome_tags") or []):
        out.append(f"resource_distribution[{entry_id}]: no biome_tags")
    item_tags = {str(t).lower() for t in (rec.get("item_tags") or [])}
    if not item_tags:
        out.append(f"resource_distribution[{entry_id}]: no item_tags")
    else:
        unknown = item_tags - _forage_vocabulary()
        if unknown:
            out.append(f"resource_distribution[{entry_id}]: item_tags not in the "
                       f"foraging vocabulary {sorted(unknown)}")
    weight = _num(rec.get("weight"), 0)
    if weight is None or weight <= 0:
        out.append(f"resource_distribution[{entry_id}]: non-positive weight")
    return out


def hostile_table_problems(entry_id: str, rec: dict) -> List[str]:
    """Validate one raw hostile loot-table entry (task-718/589)."""
    if not isinstance(rec, dict):
        return [f"hostile_distribution[{entry_id}]: not an object"]
    out: List[str] = []
    if not (rec.get("biome_tags") or []):
        out.append(f"hostile_distribution[{entry_id}]: no biome_tags")
    kind = str(rec.get("kind") or "")
    if kind not in HOSTILE_KINDS:
        out.append(f"hostile_distribution[{entry_id}]: unknown kind '{kind}' "
                   f"({list(HOSTILE_KINDS)})")
    base = _num(rec.get("base_chance"))
    per = _num(rec.get("per_area_from_settlement"))
    cap = _num(rec.get("max_chance"))
    if base is None or not (0 <= base <= 1):
        out.append(f"hostile_distribution[{entry_id}]: base_chance out of [0,1]")
    if per is None or per < 0:
        out.append(f"hostile_distribution[{entry_id}]: per_area_from_settlement "
                   f"must be >= 0")
    if base is not None and cap is not None and cap < base:
        out.append(f"hostile_distribution[{entry_id}]: max_chance < base_chance")
    return out


def validate(data: Optional[dict] = None, path: Optional[str] = None) -> List[str]:
    """Return human-readable problems with the taxonomy; ``[]`` when clean."""
    problems: List[str] = []
    if data is None:
        data = load(path)
    bios = data.get("biomes")
    feats = data.get("features")
    if not isinstance(bios, dict) or not bios:
        return ["no biomes defined"]

    vocab = _forage_vocabulary()

    for bid, rec in bios.items():
        problems.extend(record_problems(bid, rec))

    for fid, rec in (feats or {}).items():
        problems.extend(feature_problems(fid, rec))
        if isinstance(rec, dict):
            for ref in (rec.get("biomes") or []):
                if ref not in bios:
                    problems.append(f"feature {fid}: unknown biome '{ref}'")

    bundled_resources = data.get("resource_distribution") or {}
    lib_resources = _load_library_dir(_resource_dir)
    lib_per_biome = _library_to_per_biome(lib_resources)
    resources = {**lib_per_biome, **bundled_resources}
    for bid, entries in resources.items():
        if bid not in bios:
            problems.append(f"resource_distribution: unknown biome '{bid}'")
        for entry in entries:
            etags = {str(t).lower() for t in (entry.get("tags") or [])}
            if not etags:
                problems.append(f"resource_distribution[{bid}]: entry with no tags")
                continue
            unknown = etags - vocab
            if unknown:
                problems.append(
                    f"resource_distribution[{bid}]: tags not in the foraging "
                    f"vocabulary {sorted(unknown)}")
            weight = _num(entry.get("weight"), 0)
            if weight is None or weight <= 0:
                problems.append(f"resource_distribution[{bid}]: non-positive weight")
    for bid in bios:
        if bid not in resources and not (is_made_place(bios[bid]) or is_structure(bios[bid])):
            problems.append(f"resource_distribution: biome '{bid}' has no rules")

    bundled_hostiles = data.get("hostile_distribution") or {}
    lib_hostiles = _load_library_dir(_hostile_dir)
    lib_hostile_per_biome = _library_to_per_biome_hostile(lib_hostiles)
    hostiles = {**lib_hostile_per_biome, **bundled_hostiles}
    for bid, entries in hostiles.items():
        if bid not in bios:
            problems.append(f"hostile_distribution: unknown biome '{bid}'")
        for entry in entries:
            kind = str(entry.get("kind") or "")
            if kind not in HOSTILE_KINDS:
                problems.append(
                    f"hostile_distribution[{bid}]: unknown kind '{kind}' "
                    f"({list(HOSTILE_KINDS)})")
            base = _num(entry.get("base_chance"))
            per = _num(entry.get("per_area_from_settlement"))
            cap = _num(entry.get("max_chance"))
            if base is None or not (0 <= base <= 1):
                problems.append(f"hostile_distribution[{bid}]: base_chance out of [0,1]")
            if per is None or per < 0:
                problems.append(f"hostile_distribution[{bid}]: per_area_from_settlement must be >= 0")
            if base is not None and cap is not None and cap < base:
                problems.append(f"hostile_distribution[{bid}]: max_chance < base_chance")
    for bid in bios:
        if bid not in hostiles and not (is_made_place(bios[bid]) or is_structure(bios[bid])):
            problems.append(f"hostile_distribution: biome '{bid}' has no rules")

    return problems
