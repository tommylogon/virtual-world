"""Skill-driven search finds (task-471).

An area need not be hand-stocked to be worth searching. What a search turns up
depends on the *skill* it is made with — Survival finds herbs, fruit, roots and
grubs; History finds old things; Religion finds relics — and the **area** tilts
both the chance and the flavour: a forest favours Survival, a ruin favours
History and Religion, and an item already present (an old religious statue in a
forest) raises the weight of the matching kind of find.

Light in the same way the rest of the soak tier is: no LLM, weighted tables, a
single Perception-style check, and a per-area daily cap so a long soak cannot
turn one wood into a loot piñata. Finds are ordinary library items, spawned as
fresh copies, so they can be taken, eaten, given away or ignored by every other
system.

Tag convention (additive — an item keeps every tag that is true of it):
``forage`` is a **mechanics** tag meaning "this can turn up when someone
searches the wilds". Tables name type tags (``fruit``, ``tool``, ``coin``,
``relic`` …) and, when any candidate carries ``forage``, only tagged items are
eligible — so a search draws from a curated pool instead of matching a cauldron
or a nail-polish kit just because both say ``food``/``tool``. Biome preference
lives in the tables (:data:`AREA_SKILL_BONUS`), not on the items.
"""

from __future__ import annotations

import json
import logging
import os
import random

from graph import Edge, EDGE_IN, EDGE_CARRYING

logger = logging.getLogger(__name__)

#: Base difficulty of a search; area/item affinity lowers it (never below MIN_DC).
SEARCH_DC = 10
MIN_DC = 6
#: Finds one area can yield per in-game day, across all searchers.
MAX_FINDS_PER_AREA_PER_DAY = 3

#: Area property marking that a Perception notice has spotted something worth
#: searching for here (task-478). Set by :func:`notice`; required by a hidden
#: search, so a character cannot find what they never noticed.
NOTICE_PROPERTY = "search_noticed"

#: Built-in defaults (task-483). The shipped tables live in
#: ``data/library/foraging.json`` and are authoritative; these are the fallback
#: used when that file is missing or malformed, so search still works unpackaged.
_DEFAULT_SKILL_TABLES = {
    "survival": [
        {"tags": ["herb", "medicinal"], "weight": 3},
        {"tags": ["berry", "fruit", "food"], "weight": 4},
        {"tags": ["root", "food"], "weight": 3},
        {"tags": ["grub", "bait", "bug"], "weight": 2},
    ],
    "perception": [
        {"tags": ["scrap", "junk"], "weight": 3},
        {"tags": ["tool"], "weight": 2},
        {"tags": ["coin", "currency"], "weight": 1},
    ],
    "history": [
        {"tags": ["antique"], "weight": 3},
        {"tags": ["coin", "currency"], "weight": 2},
        {"tags": ["tool", "old"], "weight": 2},
    ],
    "religion": [
        {"tags": ["relic", "religious"], "weight": 3},
        {"tags": ["idol", "religious"], "weight": 2},
    ],
    "nature": [
        {"tags": ["plant"], "weight": 3},
        {"tags": ["herb", "medicinal"], "weight": 2},
        {"tags": ["bug", "grub"], "weight": 2},
        {"tags": ["bait"], "weight": 1},
    ],
    "investigation": [
        {"tags": ["tool", "old"], "weight": 3},
        {"tags": ["metal"], "weight": 2},
        {"tags": ["scrap", "junk"], "weight": 2},
        {"tags": ["antique"], "weight": 1},
    ],
    "arcana": [
        {"tags": ["relic", "religious"], "weight": 3},
        {"tags": ["idol", "religious"], "weight": 2},
        {"tags": ["antique"], "weight": 2},
    ],
    "medicine": [
        {"tags": ["herb", "medicinal"], "weight": 4},
        {"tags": ["plant"], "weight": 2},
        {"tags": ["root"], "weight": 1},
    ],
}

#: The name the skill system knows (skills are case-sensitive in the sheet).
_DEFAULT_SKILL_DISPLAY = {
    "survival": "Survival",
    "perception": "Perception",
    "history": "History",
    "religion": "Religion",
    "nature": "Nature",
    "investigation": "Investigation",
    "arcana": "Arcana",
    "medicine": "Medicine",
}

#: area tag -> {skill key: weight multiplier bonus}. Also raises the check.
_DEFAULT_AREA_SKILL_BONUS = {
    "forest": {"survival": 2, "nature": 2, "medicine": 1},
    "woods": {"survival": 2, "nature": 2, "medicine": 1},
    "woodland": {"survival": 2, "nature": 2, "medicine": 1},
    "shore": {"survival": 1, "nature": 1},
    "ruin": {"history": 2, "religion": 1, "investigation": 2, "arcana": 1},
    "ruins": {"history": 2, "religion": 1, "investigation": 2, "arcana": 1},
    "temple": {"religion": 3, "arcana": 2},
    "shrine": {"religion": 2, "arcana": 2},
    "road": {"perception": 1, "history": 1, "investigation": 1},
    "battlefield": {"history": 2, "investigation": 1},
    "hill": {"survival": 1},
    "hills": {"survival": 1},
    "mountain": {"survival": 1},
    "mountains": {"survival": 1},
    "rocky": {"history": 1},
    "cliff": {"survival": 1},
    "ravine": {"survival": 1},
    "chasm": {"survival": 1},
    "beach": {"survival": 1},
    "lake": {"survival": 1},
    "river": {"survival": 1},
    "stream": {"survival": 1},
    "spring": {"survival": 1},
    "ocean": {"survival": 1},
    "deep_water": {"survival": 1},
    "farmland": {"survival": 1, "nature": 1, "medicine": 1},
    "field": {"survival": 1, "nature": 1},
}

#: Where the JSON table surface lives (task-483).
FORAGE_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "library", "foraging.json",
)

#: Area property naming a per-area override: ``{skill_key: [entries]}``. Its
#: entries are added to the global table for that area, and its presence makes
#: the area searchable even when its tags are not otherwise recognised.
AREA_TABLES_PROPERTY = "forage_tables"


def _load_forage_data(path=None) -> dict:
    try:
        with open(path or FORAGE_DATA_PATH, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception as e:
        logger.warning("[foraging] table data not loaded, using defaults: %s", e)
        return {}
    return data if isinstance(data, dict) else {}


_FORAGE_DATA = _load_forage_data()

#: The shipped tables are authoritative; the built-ins cover a missing file.
SKILL_TABLES = (dict(_FORAGE_DATA["skill_tables"])
                if _FORAGE_DATA.get("skill_tables")
                else _DEFAULT_SKILL_TABLES)
SKILL_DISPLAY = {**_DEFAULT_SKILL_DISPLAY,
                 **(_FORAGE_DATA.get("skill_display") or {})}
AREA_SKILL_BONUS = (dict(_FORAGE_DATA["area_skill_bonus"])
                    if _FORAGE_DATA.get("area_skill_bonus")
                    else _DEFAULT_AREA_SKILL_BONUS)

_LIBRARY_INDEX = None

#: Mechanics tag: "findable by searching the wilds". Our own loot tables prefer
#: tagged items when any exist (see _pick_item), so the pool stays curated.
FORAGE_TAG = "forage"

#: Anything useless a search can also turn up — the wilds are not a pantry.
JUNK_ENTRY = {"tags": ["junk", "scrap", "debris"], "weight": 2}


def is_loot_skill(name: str) -> bool:
    return str(name or "").strip().lower() in SKILL_TABLES


def _library_items_by_tag() -> dict:
    """tag -> [item_id] over data/library/items (built once)."""
    global _LIBRARY_INDEX
    if _LIBRARY_INDEX is not None:
        return _LIBRARY_INDEX
    index = {}
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "library", "items")
    try:
        names = os.listdir(base)
    except OSError:
        names = []
    for fname in names:
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(base, fname), "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception:
            continue
        item_id = fname[:-5]
        for tag in (data.get("tags") or []):
            index.setdefault(str(tag).lower(), []).append(item_id)
    _LIBRARY_INDEX = index
    return index


def _area_node(gs, area_name):
    try:
        area_id = gs.area_node_id(area_name)
    except Exception:
        area_id = None
    if not area_id:
        return None, None
    return area_id, gs.graph.get_node(area_id)


def _area_tags(area_node) -> set:
    props = getattr(area_node, "properties", {}) or {}
    return {str(t).lower() for t in (props.get("tags") or [])}


def _area_noticed(area_node) -> bool:
    """True once Perception has spotted something worth searching for here."""
    props = getattr(area_node, "properties", {}) or {}
    return bool(props.get(NOTICE_PROPERTY))


def _area_tables(area_node) -> dict:
    """A per-area table override (task-483): ``{skill_key: [entries]}`` or ``{}``."""
    props = getattr(area_node, "properties", {}) or {}
    raw = props.get(AREA_TABLES_PROPERTY)
    return raw if isinstance(raw, dict) else {}


def _present_tags(gs, area_id) -> set:
    tags = set()
    try:
        for tag in gs.graph.get_tagged_items_in_area(area_id).keys():
            tags.add(str(tag).lower())
    except Exception:
        pass
    return tags


def _day(gs) -> int:
    try:
        per = max(0.001, float(getattr(gs, "time_per_tick_minutes", 1) or 1))
    except (TypeError, ValueError):
        per = 1.0
    ticks_per_day = max(1, int(round(1440 / per)))
    return int(getattr(gs, "time_ticks", 0)) // ticks_per_day


def _cap_ok(area_node, gs) -> bool:
    state = (area_node.properties or {}).get("search_finds")
    if not isinstance(state, dict) or state.get("day") != _day(gs):
        return True
    return int(state.get("count", 0)) < MAX_FINDS_PER_AREA_PER_DAY


def _bump_cap(area_node, gs) -> None:
    state = (area_node.properties or {}).get("search_finds")
    if not isinstance(state, dict) or state.get("day") != _day(gs):
        state = {"day": _day(gs), "count": 0}
        area_node.properties["search_finds"] = state
    state["count"] = int(state.get("count", 0)) + 1


def _search_check(gs, player, skill_key: str, dc: int):
    """One skill check for the searcher. Returns ``(success, total)``.

    Fails open (a strong pass) if there is no skill system, so going hungry is
    the exception rather than the default.
    """
    display = SKILL_DISPLAY.get(skill_key, str(skill_key).title())
    active = getattr(gs, "active_player", None)
    try:
        gs.active_player = player.name
        success, total, _msg = gs.skill_check(display, dc)
    except Exception:
        return True, dc + 100
    finally:
        try:
            gs.active_player = active
        except Exception:
            pass
    return bool(success), int(total)


def best_skill_for(gs, player, want_tags) -> str:
    """The searcher's best skill whose table covers *want_tags* (or perception)."""
    want = {str(t).lower() for t in (want_tags or [])}
    best_key, best_value = None, None
    for key, entries in SKILL_TABLES.items():
        covered = any(want & {str(t).lower() for t in e.get("tags", [])}
                      for e in entries) if want else False
        if want and not covered:
            continue
        value = int((getattr(player, "skills", {}) or {}).get(SKILL_DISPLAY[key], 0))
        if best_value is None or value > best_value:
            best_key, best_value = key, value
    return best_key or "perception"


def _candidate_entries(skill_key, want_tags, strong: bool = False,
                       extra_entries=()):
    """What a search can turn up.

    A **strong** result (margin ≥ 5) delivers what was asked for: if a need is
    given, only entries satisfying it. A bare success delivers the skill's
    table plus junk — the wilds are not a pantry, and an unskilled searcher
    mostly finds sticks. This is what makes a Survival-trained goblin eat where
    a child goes hungry (task-471/472).

    ``extra_entries`` are appended to the skill's table, which is how a per-area
    override (task-483) adds local finds without touching the global table.
    """
    want = {str(t).lower() for t in (want_tags or [])}

    def tags_of(entry):
        return {str(t).lower() for t in entry.get("tags", [])}

    seen, out = set(), []

    def add(entry):
        key = tuple(sorted(tags_of(entry)))
        if key not in seen:
            seen.add(key)
            out.append(entry)

    tables = [list(SKILL_TABLES.get(skill_key or "", [])) + list(extra_entries)]
    if want:
        tables += list(SKILL_TABLES.values())

    if want and strong:
        for entries in tables:
            for entry in entries:
                if want & tags_of(entry):
                    add(entry)
        if out:
            return out
        # Nothing in any table satisfies the need: fall through to a normal result.

    for entries in tables:
        for entry in entries:
            if want and not strong and not (want & tags_of(entry)):
                continue
            add(entry)
    if not (want and strong):
        add(JUNK_ENTRY)
    return out


def _weight(entry, skill_key, area_tags, present_tags, want_tags=()):
    tags = {str(t).lower() for t in entry.get("tags", [])}
    want = {str(t).lower() for t in (want_tags or [])}
    weight = float(entry.get("weight", 1) or 1)
    for area_tag in area_tags:
        bonus = AREA_SKILL_BONUS.get(area_tag, {}).get(skill_key, 0)
        weight += float(bonus)
        if area_tag in tags:
            weight += 1.0
    # What the searcher actually needs is much more likely to be what they spot.
    if want & tags:
        weight += 3.0
    # Something already here — an old religious statue in a forest — makes the
    # matching kind of find more likely.
    weight += float(len(tags & present_tags))
    return max(0.0, weight)


def _pick_item(entry_tags, present_tags, rng):
    """A library item whose tags best match the entry (deterministic given rng).

    Items tagged :data:`FORAGE_TAG` win whenever any candidate has it, so the
    tables draw from a curated wild pool; a library with nothing tagged yet
    still works (falls back to the plain tag match).
    """
    index = _library_items_by_tag()
    scores = {}
    for tag in entry_tags:
        for item_id in index.get(str(tag).lower(), []):
            scores[item_id] = scores.get(item_id, 0) + 1
    curated = {item: score for item, score in scores.items()
               if item in set(index.get(FORAGE_TAG, []))}
    if curated:
        scores = curated
    if not scores:
        return None
    best = max(scores.values())
    top = sorted(item_id for item_id, score in scores.items() if score == best)
    return rng.choice(top)


def find_or_spawn(gs, player, area_name, *, skill=None, want_tags=(), rng=None,
                  require_notice=False):
    """Search *area_name* with *skill*; spawn and return a find, or None.

    Returns None when the area is capped for the day, the check fails, or the
    library has nothing matching — an empty-handed search is a normal result.

    ``require_notice`` makes this the *second* half of notice-then-search
    (task-478): the area must first have been noticed by :func:`notice`, or the
    search finds nothing because the searcher never spotted there was anything
    to look for. Plain searches leave it False.
    """
    rng = rng or random
    area_id, area_node = _area_node(gs, area_name)
    if area_node is None or not _cap_ok(area_node, gs):
        return None
    if require_notice and not _area_noticed(area_node):
        return None

    # Only an area that can plausibly *hold* a find yields one: a forest, shore,
    # ruin, road, battlefield. A bare interior with no such tag stays barren, so
    # this never turns every room into a resource dispenser — unless the area
    # authors its own table override (task-483), which is explicit intent.
    area_tags = _area_tags(area_node)
    area_tables = _area_tables(area_node)
    if not (area_tags & set(AREA_SKILL_BONUS)) and not area_tables:
        return None

    skill_key = (skill or "perception").strip().lower()
    extra_entries = list(area_tables.get(skill_key, []) or [])
    present = _present_tags(gs, area_id)

    affinity = sum(AREA_SKILL_BONUS.get(t, {}).get(skill_key, 0) for t in area_tags)
    table_entries = list(SKILL_TABLES.get(skill_key, [])) + extra_entries
    check_bonus = min(4, affinity + min(3, len({t for t in present if any(
        t in {str(x).lower() for x in e.get("tags", [])} for e in table_entries)})))
    dc = max(MIN_DC, SEARCH_DC - check_bonus)

    ok, total = _search_check(gs, player, skill_key, dc)
    if not ok:
        _trace(gs, player, area_name, why="forage:fail",
               text=f"searched {area_name} ({skill_key}) and found nothing")
        return None

    # A strong result delivers what was asked for; a bare success may be junk.
    strong = (total - dc) >= 5
    entries = _candidate_entries(skill_key, want_tags, strong=strong,
                                 extra_entries=extra_entries)
    if not entries:
        return None

    weighted = [(_weight(e, skill_key, area_tags, present, want_tags), e)
                for e in entries]
    total_weight = sum(w for w, _ in weighted)
    if total_weight <= 0:
        return None
    roll = rng.uniform(0, total_weight)
    chosen = weighted[-1][1]
    upto = 0.0
    for weight, entry in weighted:
        upto += weight
        if roll <= upto:
            chosen = entry
            break

    item_id = _pick_item(chosen.get("tags", []), present, rng)
    if not item_id:
        return None

    node = _spawn_into_area(gs, item_id, area_id)
    if node is None:
        return None
    _bump_cap(area_node, gs)
    _trace(gs, player, area_name, why="forage:found",
           text=f"found {node.name} searching {area_name} ({skill_key})",
           tags=["forage", "found"])
    try:
        gs.add_log_entry(f"[{player.name}] finds {node.name}.")
    except Exception:
        pass
    return node


def notice(gs, player, area_name, *, dc: int = SEARCH_DC) -> bool:
    """Perception: spot that there is something worth searching for (task-478).

    The *first* half of notice-then-search. Returns True when something is
    noticed (and remembers it on the area), False when the searcher walks past.
    Perception is the **gate**; the search skill (Investigation, ...) is the
    *find* — so a perceptive but untrained character notices the cache and still
    cannot open it, and a trained but unobservant one never sees it at all.

    Fails open when there is no skill system, matching `_search_check`.
    """
    area_id, area_node = _area_node(gs, area_name)
    if area_node is None:
        return False
    if _area_noticed(area_node):
        return True
    ok, _total = _search_check(gs, player, "perception", dc)
    if not ok:
        return False
    try:
        area_node.properties[NOTICE_PROPERTY] = True
    except Exception:
        return False
    _trace(gs, player, area_name, why="search:notice",
           text=f"noticed something worth searching in {area_name}",
           tags=["forage", "notice"])
    return True


def search_hidden(gs, player, area_name, *, skill="investigation", want_tags=(),
                  rng=None):
    """Two-step hidden search (task-478): Perception notices, *skill* finds.

    A failed notice means no search happens at all — the character did not see
    there was anything to look for. A success is remembered on the area, so
    coming back later does not pay for the notice again. Returns the find or None.
    """
    area_id, area_node = _area_node(gs, area_name)
    if area_node is None:
        return None
    if not _area_noticed(area_node) and not notice(gs, player, area_name):
        return None
    return find_or_spawn(gs, player, area_name, skill=skill,
                         want_tags=want_tags, rng=rng, require_notice=True)


def findable_here(gs, area_name) -> list:
    """The skills that could turn something up in *area_name* (task-483).

    Derived from the area's tags and any per-area override, so the UI can tell a
    player what is worth searching for before they burn a turn guessing. Ordered
    and side-effect free; returns ``[{"key", "skill"}, ...]``.
    """
    area_id, area_node = _area_node(gs, area_name)
    if area_node is None:
        return []
    keys = set()
    for tag in _area_tags(area_node):
        keys.update((AREA_SKILL_BONUS.get(tag) or {}).keys())
    keys.update((_area_tables(area_node) or {}).keys())
    return [{"key": key, "skill": SKILL_DISPLAY.get(key, key.title())}
            for key in sorted(keys)]


def findable_hint(gs, area_name) -> str:
    """One-line "what could be found here" hint for the HUD (task-483)."""
    skills = [entry["skill"] for entry in findable_here(gs, area_name)]
    if not skills:
        return "Nothing about this place looks worth searching."
    if len(skills) == 1:
        return f"Something here could be found with {skills[0]}."
    return "Could be searched for: " + ", ".join(skills) + "."


def _spawn_into_area(gs, item_id, area_id):
    node = None
    try:
        node, _lib = gs.effects._hydrate_item(item_id, {}, always_fresh=True)
    except Exception:
        node = None
    if node is None:
        return None
    try:
        for edge in gs.graph.edges[:]:
            if edge.source == node.id and edge.type in (EDGE_IN, EDGE_CARRYING):
                gs.graph.edges.remove(edge)
        gs.graph.add_edge(Edge(source=node.id, target=area_id, type=EDGE_IN))
    except Exception as e:
        logger.warning("[foraging] could not place %s: %s", item_id, e)
        return None
    return node


def _trace(gs, player, area_name, *, why, text, tags=None):
    try:
        from engine.trace import record
        record(player, getattr(gs, "time_ticks", 0), "act", text, why=why,
               area=area_name, tags=tags or ["forage"])
    except Exception:
        pass
