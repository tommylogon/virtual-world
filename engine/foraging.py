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

#: skill key (lowercase, also the search verb) -> weighted candidate entries.
#: An entry's tags select the library item; weight is relative.
SKILL_TABLES = {
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
}

#: The name the skill system knows (skills are case-sensitive in the sheet).
SKILL_DISPLAY = {
    "survival": "Survival",
    "perception": "Perception",
    "history": "History",
    "religion": "Religion",
}

#: area tag -> {skill key: weight multiplier bonus}. Also raises the check.
AREA_SKILL_BONUS = {
    "forest": {"survival": 2},
    "woods": {"survival": 2},
    "woodland": {"survival": 2},
    "shore": {"survival": 1},
    "ruin": {"history": 2, "religion": 1},
    "ruins": {"history": 2, "religion": 1},
    "temple": {"religion": 3},
    "shrine": {"religion": 2},
    "road": {"perception": 1, "history": 1},
    "battlefield": {"history": 2},
}

_LIBRARY_INDEX = None

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


def _candidate_entries(skill_key, want_tags, strong: bool = False):
    """What a search can turn up.

    A **strong** result (margin ≥ 5) delivers what was asked for: if a need is
    given, only entries satisfying it. A bare success delivers the skill's
    table plus junk — the wilds are not a pantry, and an unskilled searcher
    mostly finds sticks. This is what makes a Survival-trained goblin eat where
    a child goes hungry (task-471/472).
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

    tables = [SKILL_TABLES.get(skill_key or "", [])]
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
    """A library item whose tags best match the entry (deterministic given rng)."""
    index = _library_items_by_tag()
    scores = {}
    for tag in entry_tags:
        for item_id in index.get(str(tag).lower(), []):
            scores[item_id] = scores.get(item_id, 0) + 1
    if not scores:
        return None
    best = max(scores.values())
    top = sorted(item_id for item_id, score in scores.items() if score == best)
    return rng.choice(top)


def find_or_spawn(gs, player, area_name, *, skill=None, want_tags=(), rng=None):
    """Search *area_name* with *skill*; spawn and return a find, or None.

    Returns None when the area is capped for the day, the check fails, or the
    library has nothing matching — an empty-handed search is a normal result.
    """
    rng = rng or random
    area_id, area_node = _area_node(gs, area_name)
    if area_node is None or not _cap_ok(area_node, gs):
        return None

    # Only an area that can plausibly *hold* a find yields one: a forest, shore,
    # ruin, road, battlefield. A bare interior with no such tag stays barren, so
    # this never turns every room into a resource dispenser.
    area_tags = _area_tags(area_node)
    if not (area_tags & set(AREA_SKILL_BONUS)):
        return None

    skill_key = (skill or "perception").strip().lower()
    present = _present_tags(gs, area_id)

    affinity = sum(AREA_SKILL_BONUS.get(t, {}).get(skill_key, 0) for t in area_tags)
    table_entries = SKILL_TABLES.get(skill_key, [])
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
    entries = _candidate_entries(skill_key, want_tags, strong=strong)
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
