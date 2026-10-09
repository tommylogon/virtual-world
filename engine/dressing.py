"""Auto-dressing from interest tags (task-325, LLM selection task-660).

Given a character's ``interest_tags``, scan the item library for wearable
pieces (non-empty ``equip_slots``, not intrinsic abilities) whose tags
intersect those interests, then equip them through the normal equipment
stacking rules — innermost→outermost, slot depth respected, one instance
per name. Weather-aware: in a hot area, heavy-insulation pieces are skipped;
in a cold area, insulated pieces are preferred.

Idempotent by construction: ``equip_item`` refuses already-worn names and
full slots, so re-running dresses only what's missing. Seeds are optional
for reproducible runs.

**Two selection paths, one equip loop.** The engine cannot call an LLM — the
keys live in the browser (``routes/action_handlers.py:195``), so the inspector
runs the model and posts the picks back. This module owns the candidate list
(``dress_candidates``) and the equip step (``auto_dress`` with
``library_ids``), and the deterministic tag intersection stays the fallback
when no model is configured or the call fails.

The tag intersection alone is a weak selector: it picks anything sharing a tag,
so a blacksmith whose interests are ``metal, tools, iron, temper`` matches
nothing wearable and falls to the generic clothing branch, which shuffles the
whole wardrobe pool. That is how a 41-year-old smith ends up in a Guiding Cane.
The LLM path sees a *wider* pool than the tag filter accepts and judges it
against the character.
"""

import json
import os
import random

from graph import Edge, EDGE_CARRYING, EDGE_EQUIPPED, EDGE_IN

_INTRINSIC = {"spell", "ability", "innate", "intrinsic", "power"}


def _norm_name(name) -> str:
    """Compare item names the way ``equip_item`` does (task-450)."""
    return str(name or "").lower().replace('_', ' ').replace('-', ' ').strip()


def _wearable_entries():
    """Every library item that could be worn, as raw entries.

    Split out from the tag filter so the LLM path can offer a *wider* pool than
    the deterministic filter accepts -- see :func:`dress_candidates`.
    """
    lib_dir = _library_dir()
    if not os.path.isdir(lib_dir):
        return []
    out = []
    for fname in os.listdir(lib_dir):
        if not fname.endswith('.json'):
            continue
        try:
            with open(os.path.join(lib_dir, fname), 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        slots = data.get("equip_slots", [])
        if isinstance(slots, str):
            slots = [s.strip() for s in slots.split(",")]
        if not slots:
            continue
        tags = {str(t).lower().strip() for t in (data.get("tags", []) or [])}
        if tags & _INTRINSIC:
            continue
        out.append({
            "lib_id": fname[:-5],
            "name": data.get("name", fname[:-5]),
            "slots": list(slots),
            "tags": sorted(tags),
            "insulation": int(data.get("insulation", 0) or 0),
            # task-660: adult wearables (a restraint/gag) are marked `mature` in
            # the library, the same flag `_filter_mature_entries` honours.
            "mature": bool(data.get("mature")),
        })
    return out


def _apply_mature_gate(gs, entries):
    """Drop `mature`-flagged wearables unless the world has opted in (task-660).

    The inspector's Auto-Dress button is general-purpose, so a mature item must
    not reach the model — or the deterministic pool — while `mature_content` is
    off. Definitions stay functional for a character already wearing one.
    """
    if getattr(gs, "mature_content", False):
        return entries
    return [e for e in entries if not e.get("mature")]


def _library_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'library', 'items')


def _player_area_env(gs, player):
    try:
        area_id = gs._get_current_area_id()
        node = gs.graph.get_node(area_id) if area_id else None
        env = (node.properties or {}).get("environment", {}) if node else {}
        return float(env.get("temperature", 21) or 21)
    except Exception:
        return 21.0


def _weather_ok(entry, hot, cold):
    """Weather gate. Kept identical to the original inline check."""
    if hot and entry["insulation"] >= 15:
        return False
    if cold and entry["insulation"] <= 0:
        return False
    return True


def _tag_matched(entries, interest):
    """The deterministic selector: tag intersection, or basics when no interests.

    Unchanged from task-325 so the existing tests keep measuring the same thing.
    """
    if interest:
        return [e for e in entries if set(e["tags"]) & interest]
    basics = {"clothing", "armor", "wear", "wearable"}
    return [e for e in entries if set(e["tags"]) & basics]


def dress_candidates(gs, player_name=None, limit=30):
    """Candidate gear for a character, for the inspector's LLM to choose from.

    Returns the character context plus two lists:

    ``matched``
        What the deterministic path would consider -- the tag intersection.
    ``pool``
        A wider, ranked set for the model to judge. Interest-matched entries
        come first, then remaining wearables by name, capped at *limit*. The
        model is deliberately shown more than ``matched`` contains: the tag
        filter is why a smith's wardrobe came out arbitrary, and offering it
        only the tag-matched subset would reproduce that.

    The caller posts back library ids; :func:`auto_dress` re-validates them
    against ``pool``, so a hallucinated id equips nothing.
    """
    pm = gs.player_manager
    name = player_name or pm.active_player
    player = pm.players.get(name)
    if not player:
        raise ValueError(f"No character '{name}'.")

    interest = {str(t).lower().strip() for t in (player.interest_tags or [])}
    temp = _player_area_env(gs, player)
    hot, cold = temp >= 30, temp <= 5

    entries = [e for e in _wearable_entries() if _weather_ok(e, hot, cold)]
    entries = _apply_mature_gate(gs, entries)
    matched = _tag_matched(entries, interest)

    matched_ids = {e["lib_id"] for e in matched}
    rest = sorted((e for e in entries if e["lib_id"] not in matched_ids),
                  key=lambda e: e["name"].lower())
    pool = matched + rest

    return {
        "character": name,
        "interest_tags": sorted(interest),
        "personality": (player.personality or '')[:1200],
        # Deliberately base_description and never `description`. `description` is
        # regenerated FROM the equipped items on every wear/remove
        # (`engine/equipment.py::_update_equipment_description`, plus the
        # frontend call in `static/js/api.js`), so handing it to a prompt whose
        # job is choosing equipment is circular -- the model would read an
        # outfit to pick an outfit. Named `base_description` so the reason
        # survives the next reader.
        "base_description": (player.base_description or '')[:400],
        "temperature": temp,
        "matched": [_public(e) for e in matched[:limit]],
        "pool": [_public(e) for e in pool[:limit]],
    }


def _public(entry):
    """The shape the browser sees. ``lib_id`` is the only key the engine trusts."""
    return {
        "lib_id": entry["lib_id"],
        "name": entry["name"],
        "tags": entry["tags"],
        "slots": entry["slots"],
        "insulation": entry["insulation"],
    }


def auto_dress(gs, player_name=None, seed=None, library_ids=None):
    """Dress a character. Returns a report.

    ``library_ids`` selects an explicit list (the LLM path, task-660); ids that
    are not wearable candidates are dropped. ``None`` runs the original
    deterministic shuffle over the tag-matched set.
    """
    pm = gs.player_manager
    name = player_name or pm.active_player
    player = pm.players.get(name)
    if not player:
        raise ValueError(f"No character '{name}'.")

    interest = {str(t).lower().strip() for t in (player.interest_tags or [])}
    temp = _player_area_env(gs, player)
    hot, cold = temp >= 30, temp <= 5

    entries = [e for e in _wearable_entries() if _weather_ok(e, hot, cold)]
    entries = _apply_mature_gate(gs, entries)
    by_id = {e["lib_id"]: e for e in entries}

    if library_ids is None:
        candidates = _tag_matched(entries, interest)
        rng = random.Random(seed)
        rng.shuffle(candidates)
    else:
        candidates = []
        seen_ids = set()
        for lib_id in library_ids:
            entry = by_id.get(str(lib_id))
            # De-duplicate here, not only in the browser. This function is the
            # engine's re-validation boundary and has other callers, and
            # _hydrate_item(always_fresh=True) mints a NEW node per call -- so a
            # repeated id silently produced two instances of the same item, two
            # of them in one slot. The browser validator already drops repeats;
            # a boundary that trusts its caller is not a boundary.
            if entry is not None and entry["lib_id"] not in seen_ids:
                seen_ids.add(entry["lib_id"])
                candidates.append(entry)
        # Model order is meaningful (best choice first); do not shuffle it away.

    player_id = pm.get_player_node_id(name)
    # task-450: a piece the character already wears must not be hydrated at all.
    # Equipping it would raise ("already wearing") and the except block would
    # drop the freshly-minted duplicate node into the room -- so dressing a
    # character twice left a second same-named item on the floor.
    worn_names = set()
    for edge in gs.graph.get_edges_for_target(player_id, EDGE_EQUIPPED):
        worn_node = gs.graph.get_node(edge.source)
        if worn_node is not None:
            worn_names.add(_norm_name(worn_node.name))

    dressed = []
    skipped = []
    for cand in candidates:
        # Bound before the try: if _hydrate_item raises, the except block below
        # references `node`, and an unbound name there raises NameError which the
        # inner except swallows -- so the candidate silently vanished with no
        # reason recorded.
        node = None
        if _norm_name(cand["name"]) in worn_names:
            skipped.append((cand["name"], "already worn"))
            continue
        try:
            node, _lib = gs.effects._hydrate_item(cand["lib_id"], {}, always_fresh=True)
            if node is None:
                skipped.append((cand["name"], "no library data"))
                continue
            gs.graph.add_edge(Edge(source=node.id, target=player_id, type=EDGE_CARRYING))
            msg = gs.equipment.equip_item(cand["name"], slot=cand["slots"][0])
            dressed.append(cand["name"])
            worn_names.add(_norm_name(cand["name"]))
        except Exception as e:
            # Undress the failed candidate: back to carrying, then into the room.
            if node is not None:
                try:
                    for edge in list(gs.graph.edges):
                        if edge.source == node.id and edge.type in (EDGE_CARRYING,):
                            gs.graph.edges.remove(edge)
                    area_id = gs._get_current_area_id()
                    if area_id:
                        gs.graph.add_edge(Edge(source=node.id, target=area_id, type=EDGE_IN))
                except Exception:
                    pass
            skipped.append((cand["name"], str(e)[:60]))

    lines = [f"Auto-dress for {name}: {len(dressed)} item(s) equipped."]
    for n in dressed:
        lines.append(f"- {n}")
    return "\n".join(lines)
