"""Faction and ownership as tags: a camp's water is the camp's (task-550).

Areas carried `tags` but no owner, so the Kraktooth goblin camp's single water
source and its single waste pile were a shared resource with no claimant. The
measured consequence was that 4 of the 5 humans in the camp start in Eldenford
and, after a 3-day run, all 5 end up living in the goblin camp: when nothing has
a claimant, the only place that satisfies survival wins outright.

Ownership is therefore **two tags**, symmetric and explicit, with no new field
and no migration:

* a character carries ``faction:<name>``
* an area carries ``held_by:<name>`` (once per holding faction)

Three decisions this module makes, and why:

**1. Ownership is a tag, not a derivation from the area's scope.** A scope is a
containment construct — the WorldPainter grid hierarchy of task-397 — and it
does not track who lives where: the camp's own scope ``deep_woods_2`` also holds
the Human Road and the Abandoned Farm, so deriving ownership from scope would
make the goblin tribe the owner of a human farm. Scope answers "where is this",
never "whose is this".

**2. An unheld area is a commons, not an error.** Roads, the wilderness and any
area nobody has claimed carry no ``held_by`` tag and belong to everyone. An area
held by two factions carries both tags and is a shared, visibly contested
holding. This is why the vocabulary is a *set*: a binary "owner" field could not
express a border market without a third concept.

**3. A contested use records an event; it does not cost a vital and it does not
refuse.** Same reasoning as `engine/relief.py` (task-551), which measured that
turning a preference into a permission gate makes characters stop going and
concentrates them instead. Drinking somebody else's water is *observed*, not
*punished*: the character still gets their Thirst, and a fact lands in the lived
log so "someone took mine" stops being silence. Whether that should cost a
relationship is task-552's fear model and `engine/background_social.py`'s, not
this module's.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set

#: A character declares what it belongs to with ``faction:<name>``.
FACTION_PREFIX = "faction:"

#: An area declares who holds it with ``held_by:<name>`` (one per holder).
HELD_BY_PREFIX = "held_by:"

#: Lived-log reason layer for "used something somebody else holds". The `why`
#: field is a ``layer:reason`` tag (see `engine/lived_log.record`), so the
#: ownership layer joins `needs:`, `goal:` and `plan:` as a named decider.
CONTESTED_WHY = "ownership:use"

#: Lived-log entry kind. `act` because the character did something; the `why` is
#: what makes it more than an ordinary drink.
CONTESTED_KIND = "act"


def _tags(source: Any) -> List[str]:
    """The tag list of a node, a properties dict, or a player.

    A graph node keeps its tags in ``properties["tags"]``; a ``Player`` exposes
    them as ``.tags``. Both shapes reach this module, so read both rather than
    making every caller unwrap first — and a caller that passed the *wrong* one
    would otherwise silently read zero tags and conclude nothing is owned.
    """
    if source is None:
        return []
    if isinstance(source, dict):
        tags = source.get("tags")
    else:
        tags = getattr(source, "tags", None)
        if tags is None:
            props = getattr(source, "properties", None)
            if isinstance(props, dict):
                tags = props.get("tags")
    if isinstance(tags, str):
        tags = [tags]
    return [str(t) for t in (tags or [])]


def _bare(name: Any) -> str:
    """A faction name with either known prefix stripped, lowercased.

    The comparison helpers take bare names, but a description builder that has a
    tag list in hand will hand them ``held_by:goblin``. Accepting both means a
    caller cannot silently treat a prefixed tag as an unknown faction — which
    would report every area as unheld rather than as held.
    """
    text = str(name or "").strip().lower()
    for prefix in (FACTION_PREFIX, HELD_BY_PREFIX):
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    return text.strip()


def _prefixed(tags: Iterable[str], prefix: str) -> Set[str]:
    out = set()
    for tag in tags:
        text = str(tag).strip()
        if text.lower().startswith(prefix) and len(text) > len(prefix):
            name = text[len(prefix):].strip().lower()
            if name:
                out.add(name)
    return out


def factions_of(source: Any) -> Set[str]:
    """Faction names a character/node claims membership of."""
    return _prefixed(_tags(source), FACTION_PREFIX)


def holders_of(source: Any) -> Set[str]:
    """Faction names that hold an area (or a node standing in for one)."""
    return _prefixed(_tags(source), HELD_BY_PREFIX)


def is_owned_by(source: Any, faction: str) -> bool:
    """True when *faction* holds this area. Accepts a bare name or a tag."""
    return _bare(faction) in holders_of(source)


def owns_any(factions: Iterable[str], holders: Iterable[str]) -> bool:
    """True when the two faction sets intersect. Accepts bare names or tags."""
    mine = {_bare(f) for f in factions}
    mine.discard("")
    theirs = {_bare(h) for h in holders}
    theirs.discard("")
    return bool(mine & theirs)


def unowned_need_areas(graph, need_tags: Iterable[str]) -> List[str]:
    """Areas satisfying *need_tags* that nobody holds.

    This is the diagnostic the task asks for: a shared resource with no claimant
    is a hole in the world, and it should be visible as one rather than only in a
    dashboard. Sorted by area name so the report is stable.
    """
    want = {str(t).strip().lower() for t in need_tags if str(t).strip()}
    if not need_tags:
        return []
    out = []
    for node in (getattr(graph, "nodes", {}) or {}).values():
        if getattr(node, "type", None) != "area":
            continue
        if not (want & {str(t).strip().lower() for t in _tags(node)}):
            continue
        if not holders_of(node):
            out.append(getattr(node, "name", "") or getattr(node, "id", ""))
    return sorted(out)


def ownership_map(graph, factions: Iterable[str]) -> Dict[str, List[str]]:
    """``faction -> [area names it holds]`` over a whole graph.

    The whole-cast map, so "nobody owns the water" is one dict entry rather than
    something a reader has to assemble.
    """
    out: Dict[str, List[str]] = {}
    for faction in factions:
        name = _bare(faction)
        if name:
            out.setdefault(name, [])
    for node in (getattr(graph, "nodes", {}) or {}).values():
        if getattr(node, "type", None) != "area":
            continue
        area_name = getattr(node, "name", "") or getattr(node, "id", "")
        for holder in holders_of(node):
            out.setdefault(holder, []).append(area_name)
    return {k: sorted(v) for k, v in out.items()}


def describe_standing_on(factions: Iterable[str], holders: Iterable[str]) -> str:
    """One clause a description can carry, or ``""`` when nothing is contested.

    Empty string rather than a neutral phrase so a caller can concatenate
    unconditionally and get no dead punctuation.
    """
    mine = {_bare(f) for f in factions}
    mine.discard("")
    theirs = {_bare(h) for h in holders}
    theirs.discard("")
    if not theirs or (mine & theirs):
        return ""
    names = sorted(theirs)
    if len(names) == 1:
        return f"held by the {names[0]}"
    if len(names) == 2:
        return f"held by the {names[0]} and the {names[1]}"
    return f"held by the {names[0]} and {len(names) - 1} others"


def note_contested_use(player, area_node, need: str, gs=None) -> Optional[dict]:
    """Record a non-owner using a held need-resource. Returns the entry, or None.

    Called when a character satisfies a need from an area somebody else holds —
    drank from the goblin camp's water, ate from Eldenford's stores. The need is
    satisfied either way; what changes is that the fact exists.

    Writes two places, because they answer different questions: the player's
    ``lived_log`` (what happened to this character) and the game log (what
    happened in the world). Both are best-effort — a bookkeeping failure must
    never abort a survival action, so every failure is swallowed.
    """
    if player is None or area_node is None:
        return None
    need = str(need or "").strip() or "need"
    holders = holders_of(area_node)
    mine = factions_of(player)
    if not mine:
        # No declared faction means no claim to have been violated. The wild
        # animals in and around the camp carry no `faction:` tag, and reading
        # that as "not a goblin" would accuse a wolf of stealing goblin water.
        # Unknown is not the same as foreign.
        return None
    if not holders or owns_any(mine, holders):
        return None

    area_name = getattr(area_node, "name", "") or getattr(area_node, "id", "")
    what = f"{getattr(player, 'name', 'someone')} used the {need} here"
    entry = None
    try:
        from engine.lived_log import record

        entry = record(
            player,
            getattr(gs, "time_ticks", 0) or 0,
            CONTESTED_KIND,
            what,
            why=f"{CONTESTED_WHY}:{need}",
            area=area_name,
            tags=["need", "ownership"],
            salient=True,
        )
    except Exception:  # noqa: BLE001 - bookkeeping must not break survival
        entry = None
    try:
        if gs is not None:
            holder_text = describe_standing_on(mine, holders)
            gs.add_log_entry(
                f"[{getattr(player, 'name', 'Someone')}] takes {need} at "
                f"{area_name} — {holder_text}."
            )
    except Exception:  # noqa: BLE001
        pass
    return entry
